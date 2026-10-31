"""用户投稿权限与审核闭环；隔离数据库，不调用真实模型或修改开发库。"""
import unittest
from types import SimpleNamespace
from unittest.mock import patch
import httpx
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app import models
from app.database import Base, get_db
from app.main import app
from app.security import get_current_user


class SubmissionTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine=create_engine('sqlite://',connect_args={'check_same_thread':False},poolclass=StaticPool)
        @event.listens_for(self.engine,'connect')
        def foreign_keys(connection,record):
            connection.execute('PRAGMA foreign_keys=ON')
        Base.metadata.create_all(self.engine)
        self.Session=sessionmaker(bind=self.engine,expire_on_commit=False)
        with self.Session() as db:
            db.add_all([models.User(uid=i,username=name,role=role,email=name+'@example.test',password_hash='test')
                for i,name,role in [(1,'student','user'),(2,'other','user'),(3,'admin','admin')]])
            db.add(models.Category(cid=1,name='Campus'))
            db.commit()
        def dependency():
            with self.Session() as db:
                yield db
        self.user=SimpleNamespace(uid=1,role='user')
        app.dependency_overrides[get_db]=dependency
        app.dependency_overrides[get_current_user]=lambda:self.user
        self.client=httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://test')
        self.payload={'title':'Campus borrowing guide','content':'Use your own campus card to borrow a book.',
                      'category_id':1,'source_name':'Library website','source_url':'https://www.nbu.edu.cn/'}

    async def asyncTearDown(self):
        await self.client.aclose()
        app.dependency_overrides.clear()
        self.engine.dispose()

    async def submit(self):
        response=await self.client.post('/submissions',json=self.payload)
        self.assertEqual(response.status_code,201,response.text)
        return response.json()['knowledge']['kid']

    async def test_submission_is_private_with_session_author_and_no_vector(self):
        kid=await self.submit()
        with self.Session() as db:
            item=db.query(models.Knowledge).filter_by(kid=kid).one()
            self.assertEqual((item.created_by,item.status),(1,'draft'))
            self.assertEqual(db.query(models.KnowledgeEmbedding).count(),0)
            self.assertEqual(db.query(models.Document).one().source_url,self.payload['source_url'])
        self.assertEqual((await self.client.get('/knowledge')).json()['count'],0)
        self.assertEqual((await self.client.get('/knowledge/'+str(kid))).status_code,404)
        self.assertEqual((await self.client.get('/search/knowledge?keyword=borrowing')).json()['count'],0)
        self.assertEqual((await self.client.get('/submissions')).json()['count'],1)
        own=await self.client.get('/submissions/'+str(kid))
        self.assertEqual(own.json()['content'],self.payload['content'])
        self.user=SimpleNamespace(uid=2,role='user')
        self.assertEqual((await self.client.get('/submissions')).json()['count'],0)
        self.assertEqual((await self.client.get('/submissions/'+str(kid))).status_code,404)
        self.assertEqual((await self.client.put('/submissions/'+str(kid),json=self.payload)).status_code,404)

    async def test_rejection_feedback_resubmission_and_publication(self):
        kid=await self.submit()
        self.user=SimpleNamespace(uid=3,role='admin')
        listing=(await self.client.get('/knowledge')).json()['items'][0]
        self.assertTrue(listing['is_submission'])
        self.assertEqual(listing['created_by_name'],'student')
        detail=(await self.client.get('/knowledge/'+str(kid))).json()
        self.assertEqual(detail['sources'][0]['source_name'],'Library website')
        response=await self.client.patch('/knowledge/{}/review'.format(kid),json={'action':'reject','reason':'Please specify campus and year'})
        self.assertEqual(response.status_code,200,response.text)
        self.user=SimpleNamespace(uid=1,role='user')
        self.assertEqual((await self.client.get('/submissions?status=rejected')).json()['items'][0]['review_note'],'Please specify campus and year')
        self.assertEqual((await self.client.patch('/knowledge/{}/review'.format(kid),json={'action':'restore'})).status_code,403)
        self.assertEqual((await self.client.patch('/knowledge/{}/publish'.format(kid))).status_code,403)
        updated={**self.payload,'content':'Meishan campus: use your own card to borrow books.','source_url':None}
        response=await self.client.put('/submissions/'+str(kid),json=updated)
        self.assertEqual(response.status_code,200,response.text)
        self.assertEqual(response.json()['knowledge']['status'],'draft')
        self.assertEqual(response.json()['knowledge']['review_note'],'')
        self.user=SimpleNamespace(uid=3,role='admin')
        with patch('app.routers.knowledge.refresh_index',return_value='ready'):
            self.assertEqual((await self.client.patch('/knowledge/{}/publish'.format(kid))).status_code,200)
        self.user=SimpleNamespace(uid=1,role='user')
        self.assertEqual((await self.client.get('/submissions?status=published')).json()['count'],1)
        self.assertEqual((await self.client.get('/knowledge/'+str(kid))).status_code,200)
        self.assertEqual((await self.client.put('/submissions/'+str(kid),json=updated)).status_code,409)
        with self.Session() as db:
            self.assertEqual(db.query(models.Knowledge).one().content,updated['content'])
            self.assertEqual(db.query(models.UpdateLog).count(),4)

    async def test_system_fields_invalid_sources_and_blank_content_are_rejected(self):
        for extra in ({'created_by':3},{'status':'published'},{'role':'admin'},
                      {'source_url':'javascript:alert(1)'},{'source_url':'https://user:pass@example.com/'},
                      {'content':'   '},{'title':'   '},{'source_url':'https://example.com/'+('x'*500)}):
            response=await self.client.post('/submissions',json={**self.payload,**extra})
            self.assertEqual(response.status_code,422,response.text)
        response=await self.client.post('/submissions',json={**self.payload,'category_id':99999})
        self.assertEqual(response.status_code,400)
        with self.Session() as db:
            self.assertEqual(db.query(models.Knowledge).count(),0)
        response=await self.client.post('/submissions',json=self.payload,headers={'Origin':'http://evil.test'})
        self.assertEqual(response.status_code,403)

    async def test_own_non_submission_knowledge_cannot_be_modified_through_submission_routes(self):
        with self.Session() as db:
            db.add(models.Knowledge(kid=10,title='Imported material',content='Preserve this original.',
                                   created_by=1,category_id=1,status='draft'))
            db.commit()
        self.assertEqual((await self.client.get('/submissions')).json()['count'],0)
        self.assertEqual((await self.client.get('/submissions/10')).status_code,404)
        self.assertEqual((await self.client.put('/submissions/10',json=self.payload)).status_code,404)


if __name__=='__main__':
    unittest.main()
