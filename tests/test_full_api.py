"""All existing HTTP routes against an isolated SQLite DB with FK enforcement.
Run: python -m tests.test_full_api. Never accesses the real MySQL data.
"""
import asyncio
import json
import re
import io
from unittest.mock import patch
from collections import Counter
from pathlib import Path
import httpx
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.database import Base, get_db
from app import models, crud
from app.main import app

engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
@event.listens_for(engine, 'connect')
def foreign_keys(connection, record):
    connection.execute('PRAGMA foreign_keys=ON')
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine, expire_on_commit=False)
def test_db():
    with Session() as db:
        yield db

results=[]
covered=set()
async def req(client, method, path, expected=200, data=None, check=None, **kwargs):
    for route in app.routes:
        if method in (getattr(route,'methods',None) or []) and route.path_regex.match(path.split('?')[0]):
            covered.add((method, route.path))
            break
    try:
        r=await client.request(method,path,**({'json':data} if data is not None else {}),**kwargs)
        if r.status_code != expected:
            raise AssertionError('expected %s, got %s: %s'%(expected,r.status_code,r.text[:250]))
        body=r.json() if 'application/json' in r.headers.get('content-type','') else r.text
        if check is not None:
            assert check(body), 'response assertion failed'
        results.append({'case':method+' '+path,'passed':True,'status':r.status_code})
        return body
    except Exception as error:
        results.append({'case':method+' '+path,'passed':False,'error':str(error)[:400]})
        return {}

async def run():
    indexing_mock=patch('app.routers.knowledge.refresh_index',return_value='ready')
    indexing_mock.start()
    app.dependency_overrides[get_db]=test_db
    transport=httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport,base_url='http://test') as c:
        await req(c,'GET','/')
        await req(c,'GET','/static/style.css')
        await req(c,'GET','/static/script.js')
        await req(c,'GET','/docs')
        await req(c,'GET','/openapi.json')
        await req(c,'GET','/auth/me',401)
        await req(c,'GET','/knowledge',401)
        await req(c,'GET','/submissions',401)
        await req(c,'GET','/query_logs',401)
        await req(c,'POST','/register',201,{'username':'admin-test','password':'password123','email':'admin@example.com','role':'admin'},lambda x:x['user']['username']=='admin-test')
        with Session() as db:
            admin=crud.get_user_by_username(db,'admin-test')
            assert admin.role=='user', 'Public registration escalated role!'
            admin.role='admin';db.commit();admin_id=admin.uid
            category=crud.create_category(db,'Data structures','test')
            category_id=category.cid
        await req(c,'POST','/register',409,{'username':'admin-test','password':'password123','email':'new@example.com'})
        await req(c,'POST','/register',422,{'username':'bad','password':'x','email':'not-email'})
        await req(c,'POST','/register',201,{'username':'reader-test','password':'password123','email':'reader@example.com'})
        await req(c,'POST','/login',401,{'username':'admin-test','password':'wrong'})
        await req(c,'POST','/login',200,{'username':'admin-test','password':'password123'})
        await req(c,'GET','/auth/me',check=lambda x:x['role']=='admin')
        await req(c,'GET','/users/admin-test')
        await req(c,'GET','/users/missing',404)
        await req(c,'GET','/categories',check=lambda x:x['count']==1)
        await req(c,'GET','/categories/%s'%category_id)
        temp=await req(c,'POST','/categories',201,{'name':'Temporary','description':'test'})
        temp_id=temp.get('category',{}).get('cid',2)
        await req(c,'POST','/categories',409,{'name':'Temporary'})
        await req(c,'POST','/categories',422,{'name':'   '})
        await req(c,'PUT','/categories/%s'%temp_id,data={'name':'Renamed','description':'changed'})
        await req(c,'PUT','/categories/%s'%temp_id,409,{'name':'Data structures'})
        await req(c,'DELETE','/categories/%s'%temp_id)
        await req(c,'GET','/categories/%s'%temp_id,404)
        await req(c,'DELETE','/categories/%s'%temp_id,404)
        await req(c,'PUT','/categories/99999',404,{'name':'Missing'})
        base={'title':'Stack basics','content':'stack last in first out','summary':'stack summary','category_id':category_id,'created_by':99999,'keyword':'stack'}
        created=await req(c,'POST','/knowledge',201,base)
        k=created.get('knowledge',{}).get('kid',1)
        await req(c,'DELETE','/categories/%s'%category_id,409)
        await req(c,'GET','/knowledge/%s'%k,check=lambda x:x['created_by']==admin_id and x['status']=='draft')
        await req(c,'PUT','/knowledge/%s'%k,data={'summary':'updated summary','created_by':99999})
        await req(c,'PATCH','/knowledge/%s/publish'%k)
        await req(c,'PATCH','/knowledge/%s/review'%k,409,{'action':'reject','reason':'already public'})
        await req(c,'PATCH','/knowledge/%s/review'%k,data={'action':'withdraw'},check=lambda x:x['status']=='draft')
        await req(c,'PATCH','/knowledge/%s/review'%k,422,{'action':'reject','reason':'  '})
        await req(c,'PATCH','/knowledge/%s/review'%k,data={'action':'reject','reason':'source incomplete'},check=lambda x:x['status']=='rejected')
        await req(c,'GET','/knowledge?status=rejected',check=lambda x:x['count']==1 and x['items'][0]['review_note']=='source incomplete')
        await req(c,'GET','/knowledge/%s'%k,check=lambda x:x['review_note']=='source incomplete')
        await req(c,'PATCH','/knowledge/%s/publish'%k,409)
        await req(c,'PATCH','/knowledge/%s/review'%k,data={'action':'restore'},check=lambda x:x['status']=='draft')
        await req(c,'GET','/knowledge?status=draft',check=lambda x:x['count']==1 and x['items'][0]['review_note']=='')
        await req(c,'PATCH','/knowledge/%s/publish'%k)
        await req(c,'PATCH','/knowledge/99999/review',404,{'action':'reject','reason':'missing'})
        await req(c,'PATCH','/knowledge/%s/review'%k,422,{'action':'unknown'})
        from app import config
        from app.services.vector_search import fingerprint
        with Session() as db:
            source={'knowledge_id':k,'title':'Stack basics','excerpt':'stack LIFO','content_hash':fingerprint(db.query(models.Knowledge).filter(models.Knowledge.kid==k).one())}
        with patch('app.services.vector_search.search',return_value=([source],'test-model')):
            ai_result=await req(c,'POST','/ai/search',200,{'question':'stack'},lambda x:len(x['sources'])==1)
        with patch.object(config,'DEEPSEEK_API_KEY',''):
            await req(c,'POST','/ai/explain',503,{'question':'stack','knowledge_ids':[k],'search_id':ai_result['search_id']})
        with patch('app.routers.ai.urlopen',return_value=io.BytesIO(b'{"model":"test-model"}')):
            await req(c,'GET','/ai/status')
        second=await req(c,'POST','/knowledge',201,{**base,'title':'Queue basics','keyword':'queue'})
        k2=second.get('knowledge',{}).get('kid',2)
        await req(c,'GET','/knowledge?category_id=%s&keyword=stack'%category_id,check=lambda x:x['count']==1)
        await req(c,'GET','/knowledge/99999',404)
        await req(c,'PUT','/knowledge/99999',404,{'title':'no knowledge'})
        await req(c,'PATCH','/knowledge/99999/publish',404)
        await req(c,'POST','/knowledge',400,{**base,'category_id':99999})
        await req(c,'POST','/knowledge',422,{**base,'title':'x'})
        tag=await req(c,'POST','/tags',201,{'name':'linear','description':'test'})
        tid=tag.get('tag',{}).get('tid',1)
        await req(c,'POST','/tags',409,{'name':'linear'})
        await req(c,'GET','/tags')
        await req(c,'GET','/tags/%s'%tid)
        await req(c,'PUT','/tags/%s'%tid,data={'description':'updated'})
        await req(c,'POST','/knowledge/%s/tags'%k,201,{'tag_id':tid})
        await req(c,'GET','/knowledge/%s/tags'%k,check=lambda x:x['count']==1)
        await req(c,'GET','/tags/%s/knowledge'%tid,check=lambda x:x['count']==1)
        await req(c,'GET','/search/knowledge?keyword=stack&tag_id=%s&category_id=%s&status=published'%(tid,category_id),check=lambda x:x['count']==1)
        rel=await req(c,'POST','/related_knowledge',201,{'knowledge_id':k,'related_knowledge_id':k2,'relevance_score':0.5})
        rid=rel.get('relation',{}).get('rid',1)
        await req(c,'GET','/related_knowledge/%s'%k,check=lambda x:x['count']==1)
        await req(c,'POST','/related_knowledge',400,{'knowledge_id':k,'related_knowledge_id':k})
        qa=await req(c,'POST','/qa_pairs',201,{'knowledge_id':k,'question_text':'what is stack','answer_text':'LIFO','created_by':admin_id})
        qid=qa.get('qa_pair',{}).get('qid',1)
        await req(c,'GET','/qa_pairs?knowledge_id=%s'%k)
        await req(c,'PATCH','/qa_pairs/%s/review?status=approved'%qid)
        await req(c,'PATCH','/qa_pairs/%s/review?status=invalid'%qid,400)
        feedback=await req(c,'POST','/feedback',201,{'user_id':admin_id,'knowledge_id':k,'qa_id':qid,'feedback_type':'like','content':'test'})
        fid=feedback.get('feedback',{}).get('fid',1)
        await req(c,'GET','/feedback')
        await req(c,'GET','/feedback/%s'%fid)
        await req(c,'PUT','/feedback/%s'%fid,data={'content':'updated'})
        emb=await req(c,'POST','/knowledge/%s/embedding'%k,201,{'embedding_model':'test-only','embedding_text':'stack','embedding_vector':'[0.1,0.2,0.3]'})
        eid=emb.get('embedding',{}).get('embedding_id',1)
        await req(c,'GET','/knowledge/%s/embedding'%k,check=lambda x:x['embedding_vector']=='[0.1,0.2,0.3]')
        await req(c,'PUT','/embedding/%s'%eid,data={'embedding_vector':'[0.2,0.3,0.4]'})
        await req(c,'POST','/knowledge/99999/embedding',404,{'embedding_model':'test','embedding_vector':'[1]'})
        log=await req(c,'POST','/query_logs',201,{'question_text':'question','answer_text':'answer','model_name':'test','retrieval_count':1,'user_id':admin_id})
        lid=log.get('query_log',{}).get('lid',1)
        await req(c,'GET','/query_logs')
        await req(c,'GET','/query_logs/%s'%lid)
        await req(c,'PUT','/query_logs/%s'%lid,data={'feedback_status':'liked'})
        update=await req(c,'POST','/update_logs',201,{'knowledge_id':k,'user_id':admin_id,'action_type':'publish','new_value':'published'})
        uid=update.get('update_log',{}).get('log_id',1)
        await req(c,'GET','/update_logs')
        await req(c,'GET','/update_logs/%s'%uid)
        cookie=c.cookies.get('muzhi_session')
        await req(c,'POST','/logout',403,headers={'origin':'http://evil.test'})
        await req(c,'POST','/logout')
        await req(c,'GET','/auth/me',401,headers={'cookie':'muzhi_session='+cookie})
        await req(c,'POST','/login',200,{'username':'reader-test','password':'password123'})
        await req(c,'GET','/knowledge',check=lambda x:len(x['items'])==1 and x['items'][0]['kid']==k)
        await req(c,'GET','/knowledge/%s'%k2,404)
        submission_payload={'title':'Student campus note','content':'A verified student experience awaiting review.',
            'category_id':category_id,'keyword':'campus','source_name':'student experience','source_url':'https://www.nbu.edu.cn/'}
        submission=await req(c,'POST','/submissions',201,submission_payload,
            check=lambda x:x['knowledge']['status']=='draft')
        submission_id=submission.get('knowledge',{}).get('kid',3)
        await req(c,'GET','/submissions',check=lambda x:x['count']==1)
        await req(c,'GET','/submissions/%s'%submission_id,check=lambda x:x['content']==submission_payload['content'])
        await req(c,'PUT','/submissions/%s'%submission_id,data={**submission_payload,'summary':'updated'})
        await req(c,'GET','/submissions/%s'%k,404)
        await req(c,'PUT','/submissions/%s'%k,404,submission_payload)
        await req(c,'GET','/knowledge/%s'%submission_id,404)
        await req(c,'POST','/submissions',422,{**submission_payload,'created_by':admin_id,'status':'published'})
        await req(c,'POST','/submissions',400,{**submission_payload,'category_id':99999})
        await req(c,'GET','/knowledge?status=draft',check=lambda x:x['count']==0)
        await req(c,'GET','/knowledge?status=rejected',check=lambda x:x['count']==0)
        await req(c,'PATCH','/knowledge/%s/review'%k,403,{'action':'withdraw'})
        await req(c,'GET','/categories',check=lambda x:x['items'][0]['knowledge_count']==1)
        await req(c,'POST','/categories',403,{'name':'No permission'})
        await req(c,'PUT','/categories/1',403,{'name':'No permission'})
        await req(c,'DELETE','/categories/1',403)
        await req(c,'GET','/search/knowledge?status=draft',check=lambda x:all(item['status']=='published' for item in x['items']))
        # Every management endpoint must reject regular users regardless of payload.
        for method,path in [('POST','/knowledge'),('PUT','/knowledge/1'),('DELETE','/knowledge/1'),('PATCH','/knowledge/1/publish'),('GET','/tags'),('GET','/qa_pairs'),('GET','/feedback'),('GET','/query_logs'),('GET','/update_logs'),('GET','/related_knowledge/1'),('GET','/knowledge/1/embedding'),('GET','/users/admin-test')]:
            await req(c,method,path,403)
        await req(c,'POST','/logout')
        await req(c,'POST','/login',200,{'username':'admin-test','password':'password123'})
        await req(c,'GET','/knowledge/%s'%submission_id,check=lambda x:x['sources'][0]['source_url']=='https://www.nbu.edu.cn/')
        await req(c,'DELETE','/knowledge/%s'%submission_id)
        for path in ['/feedback/%s'%fid,'/embedding/%s'%eid,'/related_knowledge/%s'%rid,'/knowledge/%s/tags/%s'%(k,tid),'/tags/%s'%tid,'/query_logs/%s'%lid,'/update_logs/%s'%uid]:
            await req(c,'DELETE',path)
            await req(c,'DELETE',path,404)
        # Deleting knowledge with dependent QA verifies FK-safe cleanup.
        await req(c,'DELETE','/knowledge/%s'%k)
        await req(c,'GET','/knowledge/%s'%k,404)
        await req(c,'DELETE','/knowledge/99999',404)
        await req(c,'GET','/knowledge/%s/embedding'%k2,404)
    app.dependency_overrides.clear()
    indexing_mock.stop()
    expected={(method,r.path) for r in app.routes if hasattr(r,'endpoint') and r.path not in ('/openapi.json','/docs','/docs/oauth2-redirect','/redoc','/') for method in (r.methods or [])}
    missing=sorted(expected-covered)
    report={'passed':sum(x['passed'] for x in results),'failed':sum(not x['passed'] for x in results),'route_methods_covered':len(expected&covered),'route_methods_total':len(expected),'untested_routes':missing,'cases':results}
    Path('tests/full-test-results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='cases'},ensure_ascii=False))
    for item in results:
        if not item['passed']: print('FAIL',item)
    if report['failed'] or missing: raise SystemExit(1)

if __name__=='__main__': asyncio.run(run())
