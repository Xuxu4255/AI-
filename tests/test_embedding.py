"""Embedding request tests with simulated responses; no external API calls."""
import io
import json
import unittest
from unittest.mock import patch
from app import config
from app.services.embedding import get_embedding, get_local_embeddings

class EmbeddingTests(unittest.TestCase):
    def setUp(self):
        provider=patch.object(config,'EMBEDDING_PROVIDER','aliyun')
        provider.start()
        self.addCleanup(provider.stop)

    def test_local_vector_validation(self):
        data={'model':config.LOCAL_EMBEDDING_MODEL+'@test','dimension':512,'vectors':[[1.0]+[0.0]*511]}
        with patch('app.services.embedding.urlopen',return_value=io.BytesIO(json.dumps(data).encode())):
            self.assertEqual(len(get_local_embeddings(['sample'])['vectors'][0]),512)
        data['vectors']=[[0.0]*512]
        with patch('app.services.embedding.urlopen',return_value=io.BytesIO(json.dumps(data).encode())):
            with self.assertRaises(ValueError):get_local_embeddings(['sample'])

    def test_local_text_type(self):
        with self.assertRaises(ValueError):get_local_embeddings(['sample'],'invalid')

    def test_blank_input(self):
        with self.assertRaises(ValueError):
            get_embedding('   ')

    def test_missing_key(self):
        with patch.object(config,'DASHSCOPE_API_KEY',''):
            with self.assertRaises(ValueError): get_embedding('sample')

    def test_missing_workspace(self):
        with patch.object(config,'DASHSCOPE_API_KEY','fake-key'), patch.object(config,'DASHSCOPE_WORKSPACE_ID',''):
            with self.assertRaises(ValueError): get_embedding('sample')

    def test_request_and_response(self):
        body=json.dumps({'output':{'embeddings':[{'embedding':[0.1,0.2,0.3]}]}}).encode('utf8')
        with patch.object(config,'DASHSCOPE_API_KEY','fake-key'), patch.object(config,'DASHSCOPE_WORKSPACE_ID','test-workspace'), patch('app.services.embedding.urlopen',return_value=io.BytesIO(body)) as mock:
            self.assertEqual(get_embedding('sample question','query'),[0.1,0.2,0.3])
            req=mock.call_args.args[0]
            data=json.loads(req.data)
            self.assertEqual(data['parameters']['text_type'],'query')
            self.assertEqual(data['input']['texts'],['sample question'])
            self.assertEqual(mock.call_args.kwargs['timeout'],30)
            self.assertEqual(req.get_method(),'POST')

if __name__=='__main__': unittest.main()
