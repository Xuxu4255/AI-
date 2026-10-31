"""聊天搜索入口：搜索与付费解释分开，所有来源必须已发布。"""
import json
import uuid
from datetime import datetime,timedelta
from urllib.error import HTTPError,URLError
from urllib.request import urlopen
from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session
from app import config,models,schemas,security
from app.database import get_db
from app.services import vector_search,explanation

router=APIRouter()


def save_search(db,user,question,sources,model):
    log=models.QueryLog(user_id=user.uid,question_text=question,model_name=model,retrieval_count=len(sources))
    db.add(log);db.flush()
    context=models.SearchContext(search_id=uuid.uuid4().hex,user_id=user.uid,query_log_id=log.lid,
        sources_json=json.dumps(sources,ensure_ascii=False),expires_at=datetime.utcnow()+timedelta(hours=1))
    db.add(context);db.commit()
    return context


@router.post('/ai/search')
def search(payload:schemas.AiSearch,db:Session=Depends(get_db),user=Depends(security.get_current_user)):
    try:
        sources,model=vector_search.search(db,payload.question,payload.category_id)
    except HTTPError as e:
        if e.code==422:raise HTTPException(422,'问题超过模型支持的长度，请缩短后重试。')
        raise HTTPException(503,'本地 Embedding 服务暂时不可用，请确认模型服务已启动。')
    except (OSError,URLError):
        raise HTTPException(503,'本地 Embedding 服务未启动或连接超时。')
    except ValueError as e:
        raise HTTPException(503,str(e))
    context=save_search(db,user,payload.question,sources,model)
    return {'search_id':context.search_id,'sources':[{k:v for k,v in s.items() if k!='content_hash'} for s in sources],
            'message':'找到相关知识' if sources else '未找到足够相关的已发布知识，请换一种描述。'}


@router.post('/ai/explain')
def explain(payload:schemas.AiExplain,db:Session=Depends(get_db),user=Depends(security.get_current_user)):
    ids=set(payload.knowledge_ids)
    if len(ids)!=len(payload.knowledge_ids):raise HTTPException(422,'知识编号不能重复')
    if payload.search_id:
        context=db.query(models.SearchContext).filter(models.SearchContext.search_id==payload.search_id,models.SearchContext.user_id==user.uid).first()
        if context is None:raise HTTPException(404,'搜索记录不存在')
        log=db.query(models.QueryLog).filter(models.QueryLog.lid==context.query_log_id).first()
        if context.expires_at<=datetime.utcnow() or not log or log.question_text!=payload.question:
            raise HTTPException(409,'搜索记录已过期或问题已改变，请重新搜索。')
        snapshot=json.loads(context.sources_json)
        if not ids.issubset({s['knowledge_id'] for s in snapshot}):raise HTTPException(403,'只能解释本次搜索返回的知识')
        sources=[s for s in snapshot if s['knowledge_id'] in ids]
        for source in sources:
            k=db.query(models.Knowledge).filter(models.Knowledge.kid==source['knowledge_id'],models.Knowledge.status=='published').first()
            if not k or vector_search.fingerprint(k)!=source['content_hash']:
                raise HTTPException(409,'来源知识已更新或撤回，请重新搜索。')
    else:
        # 兼容原关键词搜索入口：重新按同一问题匹配，不能任意指定不相关资料。
        K=models.Knowledge
        records=db.query(K).filter(K.status=='published',K.kid.in_(ids),or_(K.title.contains(payload.question,autoescape=True),K.content.contains(payload.question,autoescape=True),K.summary.contains(payload.question,autoescape=True),K.keyword.contains(payload.question,autoescape=True))).all()
        if {k.kid for k in records}!=ids:raise HTTPException(403,'知识不属于当前可访问的关键词搜索结果')
        sources=[{'knowledge_id':k.kid,'title':k.title,'excerpt':k.content[:1800],'content_hash':vector_search.fingerprint(k)} for k in records]
        context=save_search(db,user,payload.question,sources,'keyword')
        log=db.query(models.QueryLog).filter(models.QueryLog.lid==context.query_log_id).first()
    try:
        result=explanation.explain(payload.question,[{key:value for key,value in s.items() if key!='content_hash'} for s in sources])
    except explanation.ExplanationError as e:raise HTTPException(e.status,str(e))
    log.answer_text=result.answer;log.model_name=config.DEEPSEEK_MODEL;db.commit()
    return {'answer':result.answer,'status':result.status,'search_id':context.search_id,
            'sources':[{'knowledge_id':s['knowledge_id'],'title':s['title']} for s in sources if s['knowledge_id'] in result.source_ids]}


@router.get('/ai/status')
def status(user=Depends(security.get_current_user)):
    info=None
    try:
        with urlopen(config.LOCAL_EMBEDDING_URL.rstrip('/')+'/health',timeout=2) as r:info=json.loads(r.read())
    except (OSError,ValueError):pass
    return {'embedding':{'configured':bool(info),'provider':'local','model':info.get('model') if isinstance(info,dict) else None},
            'deepseek':{'configured':bool(config.DEEPSEEK_API_KEY.strip()),'model':config.DEEPSEEK_MODEL}}
