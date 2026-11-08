"""聊天搜索入口：搜索与付费解释分开，所有来源必须已发布。"""
import json
import uuid
from datetime import datetime,timedelta
from urllib.error import HTTPError,URLError
from urllib.request import urlopen
from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app import config,models,schemas,security
from app.database import get_db
from app.services import vector_search,explanation,spaces

router=APIRouter()


def save_search(db,user,question,sources,model,space='public'):
    log=models.QueryLog(user_id=user.uid,question_text=question,model_name=model,retrieval_count=len(sources))
    db.add(log);db.flush()
    context=models.SearchContext(search_id=uuid.uuid4().hex,user_id=user.uid,query_log_id=log.lid,
        sources_json=json.dumps([dict(s,space=space) for s in sources],ensure_ascii=False),expires_at=datetime.utcnow()+timedelta(hours=1))
    db.add(context);db.commit()
    return context


@router.post('/ai/search')
def search(payload:schemas.AiSearch,db:Session=Depends(get_db),user=Depends(security.get_current_user)):
    try:
        if payload.knowledge_id is not None:
            # 用户已打开一条知识：直接使用获授权的正文，不依赖 Embedding 再找一次。
            item=spaces.scoped(db,user,payload.space,payload.category_id).filter(
                models.Knowledge.kid==payload.knowledge_id).first()
            if item is None:raise HTTPException(404,'知识不存在或不在当前可访问范围')
            sources=[{'knowledge_id':item.kid,'title':item.title,
                'excerpt':vector_search.build_embedding_text(item)[:8000],
                'content_hash':vector_search.fingerprint(item)}]
            model='selected-knowledge'
        elif payload.mode == 'keyword':
            K=models.Knowledge
            records=spaces.scoped(db,user,payload.space,payload.category_id).filter(or_(*[
                field.contains(payload.question,autoescape=True) for field in [K.title,K.content,K.summary,K.keyword]
            ])).order_by(K.kid.desc()).limit(3).all()
            sources=[{'knowledge_id':k.kid,'title':k.title,'excerpt':vector_search.build_embedding_text(k)[:1800],
                      'content_hash':vector_search.fingerprint(k)} for k in records]
            model='keyword'
        else:
            sources,model=vector_search.search(db,payload.question,payload.category_id,user,payload.space)
    except HTTPError as e:
        if e.code==422:raise HTTPException(422,'问题超过模型支持的长度，请缩短后重试。')
        raise HTTPException(503,'本地 Embedding 服务暂时不可用，请确认模型服务已启动。')
    except (OSError,URLError):
        raise HTTPException(503,'本地 Embedding 服务未启动或连接超时。')
    except ValueError as e:
        raise HTTPException(503,str(e))
    context=save_search(db,user,payload.question,sources,model,payload.space)
    return {'search_id':context.search_id,'sources':[{k:v for k,v in s.items() if k!='content_hash'} for s in sources],
            'message':'找到可供参考的知识' if sources else '当前未找到直接匹配的知识，仍可在聊天框获得谨慎的分析与核实建议。'}


def chat_context(db,user,search_id,current_read=False):
    context=db.query(models.SearchContext).filter_by(search_id=search_id,user_id=user.uid).first()
    if not context:raise HTTPException(404,'搜索记录不存在')
    if context.expires_at<=datetime.utcnow():raise HTTPException(409,'本次对话的资料已过期，请重新搜索后开启新对话。')
    sources=json.loads(context.sources_json)
    ids=[s['knowledge_id'] for s in sources]
    scope=sources[0].get('space','public') if sources else 'public'
    query=spaces.scoped(db,user,scope).filter(models.Knowledge.kid.in_(ids))
    if current_read:query=query.populate_existing().with_for_update()
    records={k.kid:k for k in query.all()}
    if any(s['knowledge_id'] not in records or vector_search.fingerprint(records[s['knowledge_id']])!=s['content_hash'] for s in sources):
        raise HTTPException(409,'参考知识已更新、撤回或下架，请重新搜索后开启新对话。')
    return context,sources


@router.post('/ai/chat')
def chat(payload:schemas.AiChat,db:Session=Depends(get_db),user=Depends(security.get_current_user)):
    context,sources=chat_context(db,user,payload.search_id)
    conversation=db.query(models.AiConversation).filter_by(search_id=context.search_id,user_id=user.uid).with_for_update().first()
    if payload.conversation_id and (not conversation or conversation.conversation_id!=payload.conversation_id):
        raise HTTPException(404,'对话不存在')
    if conversation is None:
        conversation=models.AiConversation(conversation_id=uuid.uuid4().hex,search_id=context.search_id,
            user_id=user.uid,turns=0,messages_json='[]')
        db.add(conversation)
        try:db.flush()
        except IntegrityError:
            db.rollback();raise HTTPException(409,'对话已被另一请求更新，请重新搜索后再试。')
    if conversation.turns!=payload.expected_turns:
        raise HTTPException(409,'对话已更新，请重新搜索后开启新对话，避免重复发送。')
    history=json.loads(conversation.messages_json)
    references=[{k:v for k,v in s.items() if k not in ('content_hash','space')} for s in sources]
    try:result=explanation.explain(payload.message,references,history=history)
    except explanation.ExplanationError as error:
        db.rollback();raise HTTPException(error.status,str(error))
    # 模型等待期间可能发生撤回；再次读取当前记录后才发送答案。
    chat_context(db,user,payload.search_id,current_read=True)
    history.extend([{'role':'user','content':payload.message},
        {'role':'assistant','content':result.answer}])
    # 保留最近六轮，按UTF-8字节控制MySQL TEXT容量。
    while len(history)>12 or (len(history)>2 and len(json.dumps(history,ensure_ascii=False).encode('utf-8'))>56000):
        history=history[2:]
    if len(json.dumps(history,ensure_ascii=False).encode('utf-8'))>56000:
        raise HTTPException(502,'本轮对话内容过长，请缩短问题后重试。')
    conversation.messages_json=json.dumps(history,ensure_ascii=False)
    conversation.turns+=1
    log=db.query(models.QueryLog).filter_by(lid=context.query_log_id).first()
    if log:log.answer_text=result.answer;log.model_name=config.DEEPSEEK_MODEL
    db.commit()
    return dict(conversation_id=conversation.conversation_id,search_id=context.search_id,turns=conversation.turns,
        answer=result.answer,status=result.status,sources=[{'knowledge_id':s['knowledge_id'],'title':s['title']}
        for s in sources if s['knowledge_id'] in result.source_ids],
        available_sources=[{'knowledge_id':s['knowledge_id'],'title':s['title']} for s in sources])


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
            k=spaces.scoped(db,user,source.get('space','public')).filter(models.Knowledge.kid==source['knowledge_id']).first()
            if not k or vector_search.fingerprint(k)!=source['content_hash']:
                raise HTTPException(409,'来源知识已更新或撤回，请重新搜索。')
    else:
        # 兼容原关键词搜索入口：重新按同一问题匹配，不能任意指定不相关资料。
        K=models.Knowledge
        records=spaces.scoped(db,user,payload.space,payload.category_id).filter(K.kid.in_(ids),or_(K.title.contains(payload.question,autoescape=True),K.content.contains(payload.question,autoescape=True),K.summary.contains(payload.question,autoescape=True),K.keyword.contains(payload.question,autoescape=True))).all()
        if {k.kid for k in records}!=ids:raise HTTPException(403,'知识不属于当前可访问的关键词搜索结果')
        sources=[{'knowledge_id':k.kid,'title':k.title,'excerpt':k.content[:1800],'content_hash':vector_search.fingerprint(k)} for k in records]
        context=save_search(db,user,payload.question,sources,'keyword',payload.space)
        log=db.query(models.QueryLog).filter(models.QueryLog.lid==context.query_log_id).first()
    try:
        result=explanation.explain(payload.question,[{key:value for key,value in s.items() if key not in ('content_hash','space')} for s in sources])
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
