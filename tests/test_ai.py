"""AI endpoints and stale/private index isolation; no real model/API calls."""
import io
import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import httpx
from app import models,config
from app.database import Base,get_db
from app.main import app
from app.security import get_current_user
from app.services.indexing import build_embedding_text

MODEL=config.LOCAL_EMBEDDING_MODEL+'@test'
class AiTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine=create_engine('sqlite://',connect_args={'check_same_thread':False},poolclass=StaticPool)
        Base.metadata.create_all(self.engine)
        self.Session=sessionmaker(bind=self.engine,expire_on_commit=False)
        with self.Session() as db:
            db.add_all([models.User(uid=1,username='reader',email='r@example.com',password_hash='x'),models.User(uid=2,username='other',email='o@example.com',password_hash='x'),models.Category(cid=1,name='Structures')]);db.flush()
            for i,status in [(1,'published'),(2,'draft')]:
                k=models.Knowledge(kid=i,title='Stack basics',content='stack LIFO',keyword='stack',category_id=1,created_by=1,status=status);db.add(k);db.flush()
                db.add(models.KnowledgeEmbedding(knowledge_id=i,embedding_model=MODEL,embedding_text=build_embedding_text(k),embedding_vector=json.dumps([1.]+[0.]*511)))
            db.commit()
        def dependency():
            with self.Session() as db:yield db
        app.dependency_overrides[get_db]=dependency
        app.dependency_overrides[get_current_user]=lambda:SimpleNamespace(uid=1,role='user')
        self.patcher=patch('app.services.vector_search.get_local_embeddings',return_value={'model':MODEL,'dimension':512,'vectors':[[1.]+[0.]*511]});self.patcher.start()
        self.c=httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://test')
    async def asyncTearDown(self):
        await self.c.aclose();self.patcher.stop();app.dependency_overrides.clear();self.engine.dispose()
    async def search(self):
        r=await self.c.post('/ai/search',json={'question':'stack'});self.assertEqual(r.status_code,200,r.text);return r.json()
    async def test_search_draft_isolation_and_empty(self):
        data=await self.search();self.assertEqual([s['knowledge_id'] for s in data['sources']],[1]);self.assertNotIn('content_hash',data['sources'][0])
        with patch('app.services.vector_search.get_local_embeddings',return_value={'model':MODEL,'vectors':[[0.,1.]+[0.]*510]}):
            self.assertEqual((await self.search())['sources'],[])
        self.assertEqual((await self.c.post('/ai/search',json={'question':'  '})).status_code,422)
    async def test_stale_and_corrupt_indexes(self):
        with self.Session() as db:
            db.query(models.Knowledge).filter(models.Knowledge.kid==1).update({'content':'new content'});db.commit()
        self.assertEqual((await self.c.post('/ai/search',json={'question':'stack'})).status_code,503)

    async def test_rejected_knowledge_stays_private_even_with_an_existing_vector(self):
        app.dependency_overrides[get_current_user]=lambda:SimpleNamespace(uid=1,role='admin')
        response=await self.c.patch('/knowledge/2/review',json={'action':'reject','reason':'needs official source'})
        self.assertEqual(response.status_code,200,response.text)
        self.assertEqual(response.json()['status'],'rejected')
        with self.Session() as db:
            log=db.query(models.UpdateLog).filter(models.UpdateLog.knowledge_id==2).one()
            self.assertEqual(log.user_id,1)
            self.assertEqual(json.loads(log.new_value)['reason'],'needs official source')
        app.dependency_overrides[get_current_user]=lambda:SimpleNamespace(uid=1,role='user')
        self.assertEqual([s['knowledge_id'] for s in (await self.search())['sources']],[1])
        self.assertEqual((await self.c.get('/knowledge/2')).status_code,404)
        self.assertEqual((await self.c.get('/knowledge?status=rejected')).json()['count'],0)
        self.assertEqual((await self.c.get('/search/knowledge?keyword=stack')).json()['count'],1)
        self.assertEqual((await self.c.patch('/knowledge/2/review',json={'action':'restore'})).status_code,403)
    async def test_service_unavailable(self):
        with patch('app.services.vector_search.get_local_embeddings',side_effect=OSError()):
            self.assertEqual((await self.c.post('/ai/search',json={'question':'stack'})).status_code,503)
    async def test_missing_key_and_ownership(self):
        data=await self.search();payload={'question':'stack','knowledge_ids':[1],'search_id':data['search_id']}
        with patch.object(config,'DEEPSEEK_API_KEY',''):
            r=await self.c.post('/ai/explain',json=payload);self.assertEqual(r.status_code,503);self.assertIn('API Key',r.json()['detail'])
        app.dependency_overrides[get_current_user]=lambda:SimpleNamespace(uid=2,role='user')
        self.assertEqual((await self.c.post('/ai/explain',json=payload)).status_code,404)
    async def test_changed_sources_and_forged_ids(self):
        data=await self.search();payload={'question':'stack','knowledge_ids':[2],'search_id':data['search_id']}
        self.assertEqual((await self.c.post('/ai/explain',json=payload)).status_code,403)
        payload['knowledge_ids']=[1]
        with self.Session() as db:
            db.query(models.Knowledge).filter(models.Knowledge.kid==1).update({'status':'draft'});db.commit()
        self.assertEqual((await self.c.post('/ai/explain',json=payload)).status_code,409)
    async def test_successful_explanation_and_invalid_citations(self):
        data=await self.search();payload={'question':'stack','knowledge_ids':[1],'search_id':data['search_id']}
        def response(ids):return io.BytesIO(json.dumps({'choices':[{'finish_reason':'stop','message':{'content':json.dumps({'status':'answered','answer':'Stack is LIFO [1]','source_ids':ids})}}]}).encode())
        with patch.object(config,'DEEPSEEK_API_KEY','test-key'),patch('app.services.explanation.urlopen',return_value=response([1])):
            r=await self.c.post('/ai/explain',json=payload);self.assertEqual(r.status_code,200,r.text);self.assertEqual(r.json()['sources'][0]['knowledge_id'],1)
        with patch.object(config,'DEEPSEEK_API_KEY','test-key'),patch('app.services.explanation.urlopen',return_value=response([999])):
            self.assertEqual((await self.c.post('/ai/explain',json=payload)).status_code,502)
    async def test_keyword_fallback_and_status(self):
        with patch.object(config,'DEEPSEEK_API_KEY',''):
            self.assertEqual((await self.c.post('/ai/explain',json={'question':'stack','knowledge_ids':[2]})).status_code,403)
            self.assertEqual((await self.c.post('/ai/explain',json={'question':'stack','knowledge_ids':[1]})).status_code,503)
        with patch('app.routers.ai.urlopen',return_value=io.BytesIO(json.dumps({'model':MODEL}).encode())):
            r=await self.c.get('/ai/status');self.assertEqual(r.status_code,200);self.assertTrue(r.json()['embedding']['configured'])

    async def test_publish_edit_and_pending_index(self):
        app.dependency_overrides[get_current_user]=lambda:SimpleNamespace(uid=1,role='admin')
        data={'model':MODEL,'vectors':[[1.]+[0.]*511]}
        with patch('app.services.embedding.get_local_embeddings',return_value=data):
            r=await self.c.put('/knowledge/1',json={'content':'updated stack content'})
            self.assertEqual(r.status_code,200);self.assertEqual(r.json()['index_status'],'ready')
            r=await self.c.patch('/knowledge/1/publish');self.assertEqual(r.json()['index_status'],'ready')
        with self.Session() as db:
            self.assertEqual(db.query(models.KnowledgeEmbedding).filter(models.KnowledgeEmbedding.knowledge_id==1).count(),2)
        with patch('app.services.embedding.get_local_embeddings',side_effect=OSError()):
            r=await self.c.put('/knowledge/1',json={'content':'another changed content'})
            self.assertEqual(r.status_code,200);self.assertEqual(r.json()['index_status'],'pending')
        self.assertEqual((await self.c.post('/ai/search',json={'question':'stack'})).status_code,503)

if __name__=='__main__':unittest.main()
