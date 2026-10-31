import asyncio
from unittest.mock import patch
from datetime import datetime, timedelta
import httpx
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.database import Base, get_db
from app import crud, models
from app.main import app

engine=create_engine('sqlite://',connect_args={'check_same_thread':False},poolclass=StaticPool)
Base.metadata.create_all(engine)
Session=sessionmaker(bind=engine,expire_on_commit=False)
with Session() as db:
    admin=crud.create_user(db,'testadmin','password123','admin@example.com'); admin.role='admin'
    user=crud.create_user(db,'testuser','password123','user@example.com')
    category=models.Category(name='数据结构');db.add(category);db.flush()
    db.add_all([models.Knowledge(title='已发布知识',content='公开',category_id=category.cid,created_by=admin.uid,status='published'),models.Knowledge(title='待审核知识',content='私密',category_id=category.cid,created_by=admin.uid,status='draft')]);db.commit()
def test_db():
    db=Session()
    try: yield db
    finally: db.close()
app.dependency_overrides[get_db]=test_db
async def main():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://test') as c:
        assert (await c.get('/knowledge')).status_code==401
        assert (await c.patch('/knowledge/2/publish')).status_code==401
        assert (await c.post('/login',json={'username':'testuser','password':'wrong'})).status_code==401
        r=await c.post('/login',json={'username':'testuser','password':'password123'});assert r.status_code==200
        assert 'httponly' in r.headers['set-cookie'].lower()
        assert (await c.get('/auth/me')).json()['role']=='user'
        assert [x['kid'] for x in (await c.get('/knowledge')).json()['items']]==[1]
        assert (await c.get('/knowledge/2')).status_code==404
        assert (await c.get('/search/knowledge?status=draft')).json()['count']==1
        for path in ['/knowledge/2/publish','/qa_pairs/1/review']:
            assert (await c.patch(path)).status_code==403
        assert (await c.get('/tags/1/knowledge')).status_code==403
        assert (await c.get('/knowledge/2/embedding')).status_code==403
        assert (await c.post('/logout',headers={'origin':'http://evil.test'})).status_code==403
        assert (await c.post('/logout')).status_code==200
        assert (await c.get('/auth/me')).status_code==401
        assert (await c.post('/login',json={'username':'testuser','password':'password123'})).status_code==200
        with Session() as db:
            db.query(models.UserSession).update({models.UserSession.expires_at: datetime.utcnow()-timedelta(seconds=1)})
            db.commit()
        assert (await c.get('/auth/me')).status_code==401
        assert (await c.patch('/knowledge/2/publish')).status_code==401
        assert (await c.post('/login',json={'username':'testadmin','password':'password123'})).status_code==200
        assert (await c.get('/auth/me')).json()['role']=='admin'
        assert len((await c.get('/knowledge')).json()['items'])==2
        assert (await c.get('/knowledge/2')).status_code==200
        assert (await c.patch('/knowledge/2/publish')).status_code==200
        assert (await c.post('/logout')).status_code==200
        assert (await c.get('/auth/me')).status_code==401
    print('PASS: login, cookies, user/admin access, draft filtering, cross-origin refusal, publication and logout')
with patch('app.routers.knowledge.refresh_index',return_value='ready'):
    asyncio.run(main())
app.dependency_overrides.clear()
