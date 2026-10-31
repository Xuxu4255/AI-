"""小规模混合检索：只读取已发布、同版本模型且正文未变化的向量。"""
import hashlib
import json
import math
from collections import Counter
import jieba
from app import config, models
from app.services.embedding import get_local_embeddings
from app.services.indexing import build_embedding_text

STOP = set('的 了 是 在 和 与 有 一个 什么 怎么 为什么 如何 请 帮我 我们 可以 是否 进行 哪些 这个 那个'.split())

def tokens(text):
    return [t.lower() for t in jieba.lcut(text) if t.strip() and t.isalnum() and t not in STOP]

def fingerprint(knowledge):
    return hashlib.sha256(build_embedding_text(knowledge).encode('utf-8')).hexdigest()

def search(db, question, category_id=None):
    result=get_local_embeddings([question],'query')
    query=result['vectors'][0]
    rows=db.query(models.KnowledgeEmbedding,models.Knowledge).join(models.Knowledge,models.KnowledgeEmbedding.knowledge_id==models.Knowledge.kid).filter(models.Knowledge.status=='published',models.KnowledgeEmbedding.embedding_model==result['model'])
    if category_id is not None:rows=rows.filter(models.Knowledge.category_id==category_id)
    rows=rows.order_by(models.KnowledgeEmbedding.embedding_id.desc()).all()
    candidates=[];seen=set()
    for row,k in rows:
        if k.kid in seen:continue
        seen.add(k.kid)
        if row.embedding_text!=build_embedding_text(k):continue
        try:
            v=json.loads(row.embedding_vector)
            if not isinstance(v,list) or len(v)!=len(query) or any(type(x) not in (int,float) or not math.isfinite(x) for x in v):continue
            norm=math.sqrt(sum(x*x for x in v))
            if norm==0:continue
            dense=sum(a*b for a,b in zip(query,v))/norm
            terms=tokens(k.title+' '+(k.keyword or '')+' '+build_embedding_text(k))
            candidates.append((k,dense,Counter(terms),len(terms)))
        except (TypeError,ValueError):continue
    if not candidates:
        published=db.query(models.Knowledge.kid).filter(models.Knowledge.status=='published')
        if category_id is not None:published=published.filter(models.Knowledge.category_id==category_id)
        if published.first():raise ValueError('已发布知识尚无有效索引，请管理员生成或更新本地向量。')
        return [],result['model']
    qterms=set(tokens(question));n=len(candidates);avg=max(1,sum(c[3] for c in candidates)/n)
    df={t:sum(t in c[2] for c in candidates) for t in qterms}
    scores=[]
    for k,dense,tf,length in candidates:
        lexical=sum(math.log(1+(n-df[t]+0.5)/(df[t]+0.5))*tf[t]*2.2/(tf[t]+1.2*(0.25+0.75*length/avg)) for t in qterms if tf[t])
        scores.append((k,dense,lexical))
    maxlex=max((x[2] for x in scores),default=1) or 1
    ranked=[]
    for k,dense,lexical in scores:
        if dense<config.SEMANTIC_MIN_SCORE:continue
        fused=dense+0.12*lexical/maxlex
        ranked.append((fused,k,dense))
    ranked.sort(key=lambda x:(-x[0],x[1].kid))
    sources=[{'knowledge_id':k.kid,'title':k.title,'excerpt':build_embedding_text(k)[:1800],
              'score':round(score,6),'semantic_score':round(dense,6),'content_hash':fingerprint(k)} for score,k,dense in ranked[:3]]
    return sources,result['model']
