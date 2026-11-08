"""离线 Embedding 服务；默认仅监听本机，Docker 通过参数开放容器内监听。"""
import argparse
import json
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit
from local_embedding import LocalEmbedder, MODEL_ID, MODEL_DIR, QUERY_INSTRUCTION


def create_server(embedder, port=8011, host='127.0.0.1'):
    metadata=json.loads((MODEL_DIR/'MODEL_INFO.json').read_text(encoding='utf-8'))
    model_id=MODEL_ID+'@'+metadata['revision']
    lock=threading.Lock()
    allowed_hosts = {'127.0.0.1:' + str(port), 'localhost:' + str(port)}
    allowed_hosts.update(value.strip() for value in os.getenv('EMBEDDING_ALLOWED_HOSTS', '').split(',') if value.strip())
    class Handler(BaseHTTPRequestHandler):
        def setup(self):
            super().setup();self.connection.settimeout(15)
        def send_json(self,status,data):
            body=json.dumps(data,ensure_ascii=False).encode('utf-8')
            self.send_response(status);self.send_header('Content-Type','application/json; charset=utf-8')
            self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
        def allowed(self):
            if self.headers.get('Host') not in allowed_hosts or self.headers.get('Origin'):
                self.send_json(403,{'detail':'Local backend requests only'});return False
            return True
        def do_GET(self):
            if not self.allowed():return
            if urlsplit(self.path).path!='/health':self.send_json(404,{'detail':'Not found'});return
            self.send_json(200,{'model':model_id,'dimension':512,'device':'cpu','max_tokens':512})
        def do_POST(self):
            if not self.allowed():return
            if self.path!='/embeddings':self.send_json(404,{'detail':'Not found'});return
            if self.headers.get('Content-Type','').split(';')[0]!='application/json':
                self.send_json(415,{'detail':'application/json required'});return
            try:
                size=int(self.headers.get('Content-Length','0'))
                if not 0<size<=65536:raise ValueError('Invalid request size')
                payload=json.loads(self.rfile.read(size))
                if not isinstance(payload,dict):raise ValueError('JSON object required')
                texts=payload.get('texts');kind=payload.get('text_type','document')
                if kind not in ('query','document'):raise ValueError('Invalid text_type')
                if not isinstance(texts,list) or not 1<=len(texts)<=8:raise ValueError('Expected 1 to 8 texts')
                if any(not isinstance(t,str) or not t.strip() or len(t)>5000 for t in texts):raise ValueError('Invalid text')
            except (ValueError,TypeError):
                self.send_json(422,{'detail':'Expected 1-8 nonempty texts and text_type document/query'});return
            if not lock.acquire(timeout=10):self.send_json(503,{'detail':'Embedding service busy'});return
            try:
                prepared=[QUERY_INSTRUCTION+t if kind=='query' else t for t in texts]
                lengths=[len(embedder.tokenizer(t,truncation=False)['input_ids']) for t in prepared]
                if max(lengths)>512:
                    self.send_json(422,{'detail':'Text exceeds 512 tokens; split the document first'});return
                vectors=embedder.encode(texts,query=kind=='query').tolist()
                self.send_json(200,{'model':model_id,'dimension':512,'vectors':vectors})
            except Exception:
                self.send_json(500,{'detail':'Local model inference failed'})
            finally:lock.release()
        def log_message(self,fmt,*args):
            print(fmt%args,flush=True)
    server=ThreadingHTTPServer((host,port),Handler)
    server.daemon_threads=True
    return server


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--port',type=int,default=8011)
    parser.add_argument('--host', default='127.0.0.1')
    args=parser.parse_args()
    model=LocalEmbedder()
    server=create_server(model,args.port,args.host)
    print('Local Embedding ready: http://'+args.host+':'+str(args.port),flush=True)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close()
