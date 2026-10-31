"""为已发布知识生成本地模型向量；相同模型版本和正文不重复写入。"""
import json
import sys
from pathlib import Path
from urllib.request import urlopen
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from app import config
from app.database import SessionLocal
from app.models import Knowledge, KnowledgeEmbedding
from app.services.embedding import get_local_embeddings
from app.services.indexing import build_embedding_text


def main():
    with urlopen(config.LOCAL_EMBEDDING_URL.rstrip('/')+'/health',timeout=10) as response:
        health=json.loads(response.read())
    model_id=health['model']
    if not model_id.startswith(config.LOCAL_EMBEDDING_MODEL+'@') or health['dimension']!=512:
        raise ValueError('Unexpected local model')
    count=skipped=0
    with SessionLocal() as db:
        try:
            records=db.query(Knowledge).filter(Knowledge.status=='published').order_by(Knowledge.kid).all()
            pending=[]
            for item in records:
                text=build_embedding_text(item)
                old=db.query(KnowledgeEmbedding).filter(KnowledgeEmbedding.knowledge_id==item.kid,KnowledgeEmbedding.embedding_model==model_id).order_by(KnowledgeEmbedding.embedding_id.desc()).first()
                if old and old.embedding_text==text:
                    skipped+=1
                else:
                    pending.append((item.kid,text))
            for offset in range(0,len(pending),8):
                batch=pending[offset:offset+8]
                result=get_local_embeddings([text for _,text in batch])
                if result['model']!=model_id:raise ValueError('Model changed during indexing')
                for (kid,text),vector in zip(batch,result['vectors']):
                    db.add(KnowledgeEmbedding(knowledge_id=kid,embedding_model=model_id,embedding_text=text,embedding_vector=json.dumps(vector,separators=(',',':'),allow_nan=False)))
                    count+=1
                print('Encoded:',count,'/',len(pending),flush=True)
            db.commit()
        except Exception:
            db.rollback();raise
    print(json.dumps({'created':count,'skipped':skipped,'model':model_id,'dimension':512}),flush=True)

if __name__=='__main__':main()
