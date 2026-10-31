"""真实本地向量存取与排序验收；只读数据库，不修改知识或向量。"""
import json
import math
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from app.database import SessionLocal
from app.models import Knowledge, KnowledgeEmbedding
from app.services.embedding import get_local_embeddings
from app.services.indexing import build_embedding_text

questions=['最后放进去的东西为什么最先出来？','排队时谁先来谁先得到服务是什么结构？','在有序数组里每次排除一半范围来找数字是什么方法？']
result=get_local_embeddings(questions,'query')
with SessionLocal() as db:
    candidates=[]
    for k in db.query(Knowledge).filter(Knowledge.status=='published').all():
        row=db.query(KnowledgeEmbedding).filter(KnowledgeEmbedding.knowledge_id==k.kid,KnowledgeEmbedding.embedding_model==result['model']).order_by(KnowledgeEmbedding.embedding_id.desc()).first()
        if row is None or row.embedding_text!=build_embedding_text(k):raise AssertionError('Missing or stale index')
        vector=json.loads(row.embedding_vector)
        assert len(vector)==512 and all(math.isfinite(x) for x in vector)
        assert abs(sum(x*x for x in vector)-1)<0.01
        candidates.append((k.kid,k.title,vector))
    reports=[]
    for question,query in zip(questions,result['vectors']):
        ranked=sorted([(sum(a*b for a,b in zip(query,vector)),kid,title) for kid,title,vector in candidates],reverse=True)[:3]
        reports.append({'question':question,'top3':[{'knowledge_id':kid,'title':title,'score':round(score,6)} for score,kid,title in ranked]})
    expected=['栈的后进先出原则','队列的先进先出原则','二分查找的条件与边界']
    for report,title in zip(reports,expected):
        report['expected_title']=title
        report['hit_at_3']=any(x['title']==title for x in report['top3'])
    hits=sum(r['hit_at_3'] for r in reports)
    data={'model':result['model'],'dimension':512,'indexed_knowledge':len(candidates),'queries':reports,'hit_at_3':str(hits)+'/'+str(len(reports))}
    (Path(__file__).resolve().parent.parent/'tests'/'local-index-smoke.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(data,ensure_ascii=True,indent=2))
    print('Storage and vector validation passed; illustrative retrieval hit@3:',data['hit_at_3'])
