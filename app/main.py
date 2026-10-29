from fastapi import FastAPI, Depends, HTTPException, status as http_status
from sqlalchemy.orm import Session
from app.database import get_db
from app import crud, schemas

app=FastAPI()

#1.用户认证功能
'''
注册接口
登录接口
密码校验
用户状态管理
'''
@app.post("/register", status_code=http_status.HTTP_201_CREATED)
#post 前端把用户名、密码、邮箱提交给后端,后端处理注册逻辑,保存到数据库
def register(payload: schemas.UserRegister, db: Session = Depends(get_db)):
    user = crud.create_user(db, payload.username, payload.password, payload.email)

    if user is None:
        raise HTTPException(
            status_code=http_status.HTTP_409_CONFLICT,
            detail="用户名或邮箱已存在",
        )

    return{
        "message": "注册成功",
        "user": {
            "uid": user.uid,
            "username": user.username,
            "email": user.email
        }
    }

@app.post("/login")
def login(payload: schemas.UserLogin, db: Session = Depends(get_db)):
    if not crud.login_user(db, payload.username, payload.password):
        raise HTTPException(
            status_code=http_status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
        )

    return {
        "message": "登陆成功！欢迎光临喵。喵喵喵"
    }

@app.get("/users/{input_username}")
#get 前端想拿某个用户的信息,直接访问这个地址,后端返回数据
#FastAPI 会把 URL 里的这个部分自动赋值给函数参数：
def get_user_by_username(input_username: str,db: Session=Depends(get_db)):
    user = crud.get_user_by_username(db, input_username)
    if user is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="用户不存在",
        )
    return {
    "uid": user.uid,
    "username": user.username,
    "email": user.email
    }




#2.知识库crud
'''
创建知识
查询知识列表
查询单条知识
修改知识
删除知识
'''
#payload，前端转来的JSON数据对象

@app.post("/knowledge", status_code=http_status.HTTP_201_CREATED)
def create_knowledge_api(payload: schemas.KnowledgeCreate, db: Session = Depends(get_db)):
    knowledge = crud.create_knowledge(
        db=db,
        input_title=payload.title,
        input_content=payload.content,
        input_summary=payload.summary,
        input_category_id=payload.category_id,
        input_created_by=payload.created_by,
        input_keyword=payload.keyword,
    )

    if knowledge is None:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="分类或用户不存在，知识创建失败",
        )

    return {
        "message": "知识创建成功，感谢你的提交！",
        "knowledge": {
            "kid": knowledge.kid,
            "title": knowledge.title,
            "category_id": knowledge.category_id,
            "created_by": knowledge.created_by,
            "keyword": knowledge.keyword,
        }
    }

#“查询知识列表接口，支持可选的分类筛选和关键词搜索，并把结果按 JSON 返回给前端。



@app.get("/knowledge/{knowledge_kid}")
def get_knowledge_detail_api(knowledge_kid: int, db: Session = Depends(get_db)):
    knowledge = crud.get_knowledge_by_id(db, knowledge_kid)
    if knowledge is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="知识不存在",
        )

    return {
        "kid": knowledge.kid,
        "title": knowledge.title,
        "content": knowledge.content,
        "summary": knowledge.summary,
        "category_id": knowledge.category_id,
        "created_by": knowledge.created_by,
        "keyword": knowledge.keyword,
        "status": knowledge.status,
    }


@app.put("/knowledge/{knowledge_kid}")
def update_knowledge_api(knowledge_kid: int, payload: schemas.KnowledgeUpdate, db: Session = Depends(get_db)):
    if crud.get_knowledge_by_id(db, knowledge_kid) is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="知识不存在",
        )

    knowledge = crud.update_knowledge(
        db=db,
        input_kid=knowledge_kid,
        input_title=payload.title,
        input_content=payload.content,
        input_summary=payload.summary,
        input_category_id=payload.category_id,
        input_created_by=payload.created_by,
        input_keyword=payload.keyword,
    )

    if knowledge is None:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="关联的分类或用户不存在",
        )

    return {
        "message": "知识更新成功",
        "knowledge": {
            "kid": knowledge.kid,
            "title": knowledge.title,
            "category_id": knowledge.category_id,
            "keyword": knowledge.keyword,
        }
    }


@app.delete("/knowledge/{knowledge_kid}")
def delete_knowledge_api(knowledge_kid: int, db: Session = Depends(get_db)):
    is_deleted = crud.delete_knowledge(db, knowledge_kid)
    if not is_deleted:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="知识不存在",
        )
    return {"message": "知识删除成功"}


@app.get("/knowledge")
def get_knowledge_list_api(category_id: int = None, keyword: str = None, db: Session = Depends(get_db)):
    knowledge_list = crud.get_knowledge_list(
        db=db,
        input_category_id=category_id,
        input_keyword=keyword
    )
    return {
        "count": len(knowledge_list),
        "items": [
            {
                "kid": item.kid,
                "title": item.title,
                "summary": item.summary,
                "category_id": item.category_id,
                "created_by": item.created_by,
                "keyword": item.keyword,
                "status": item.status,
            }
            for item in knowledge_list
        ]
    }
#3.问答模块
'''
创建问答对
查询问答对
审核问答对
处理问答反馈
'''
@app.post("/qa_pairs", status_code=http_status.HTTP_201_CREATED)
def create_qapair_api(payload: schemas.QaCreate, db: Session = Depends(get_db)):
    qapair = crud.create_qapair(
        db=db,
        input_question_text=payload.question_text,
        input_answer_text=payload.answer_text,
        input_knowledge_id=payload.knowledge_id,
        input_created_by=payload.created_by
    )

    if qapair is None:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="关联的知识或用户不存在",
        )

    return {
        "message": "问答对已提交，等待审核",
        "qa_pair": {
            "qid": qapair.qid,
            "question_text": qapair.question_text,
            "answer_text": qapair.answer_text,
            "status": qapair.status
        }
    }

@app.get("/qa_pairs")
def get_qapair_api(
    qid: int = None,
    knowledge_id: int = None,
    created_by: int = None,
    status: str = None,
    db: Session = Depends(get_db)
):
    qas = crud.get_qapair_list(
        db=db,
        input_qid=qid,
        input_knowledge_id=knowledge_id,
        input_created_by=created_by,
        input_status=status
    )

    return {
        "count": len(qas),
        "items": [
            {
                "qid": item.qid,
                "question_text": item.question_text,
                "answer_text": item.answer_text,
                "knowledge_id": item.knowledge_id,
                "created_by": item.created_by,
                "status": item.status
            }
            for item in qas
        ]
    }

@app.patch("/qa_pairs/{qid}/review")
def review_qapair_api(qid: int, status: str, db: Session = Depends(get_db)):
    if crud.get_qapair_by_id(db, qid) is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="问答对不存在",
        )

    qapair = crud.review_qapair(db, qid, status)

    if qapair is None:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="审核状态非法，只能是 approved 或 rejected",
        )

    return {
        "message": "审核成功",
        "qid": qapair.qid,
        "status": qapair.status
    }


#4.反馈模块
'''
用户点赞/差评
错误反馈
建议反馈
反馈统计
'''
@app.post("/feedback", status_code=http_status.HTTP_201_CREATED)
def create_feedback_api(payload: schemas.FeedbackCreate, db: Session = Depends(get_db)):
    feedback = crud.create_feedback(
        db=db,
        input_user_id=payload.user_id,
        input_feedback_type=payload.feedback_type,
        input_content=payload.content,
        input_knowledge_id=payload.knowledge_id,
        input_qa_id=payload.qa_id,
    )

    if feedback is None:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="关联的用户、知识或问答对不存在",
        )

    return {
        "message": "反馈提交成功",
        "feedback": {
            "fid": feedback.fid,
            "user_id": feedback.user_id,
            "knowledge_id": feedback.knowledge_id,
            "qa_id": feedback.qa_id,
            "feedback_type": feedback.feedback_type,
            "content": feedback.content,
        }
    }


@app.get("/feedback")
def get_feedback_list_api(
    fid: int = None,
    knowledge_id: int = None,
    qa_id: int = None,
    user_id: int = None,
    feedback_type: str = None,
    db: Session = Depends(get_db)
):
    feedback_list = crud.get_feedback_list(
        db=db,
        input_fid=fid,
        input_knowledge_id=knowledge_id,
        input_qa_id=qa_id,
        input_user_id=user_id,
        input_feedback_type=feedback_type,
    )

    return {
        "count": len(feedback_list),
        "items": [
            {
                "fid": item.fid,
                "knowledge_id": item.knowledge_id,
                "qa_id": item.qa_id,
                "user_id": item.user_id,
                "feedback_type": item.feedback_type,
                "content": item.content,
                "created_at": item.created_at,
            }
            for item in feedback_list
        ]
    }


@app.get("/feedback/{fid}")
def get_feedback_detail_api(fid: int, db: Session = Depends(get_db)):
    feedback = crud.get_feedback_by_id(db, fid)
    if feedback is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="反馈不存在",
        )

    return {
        "fid": feedback.fid,
        "knowledge_id": feedback.knowledge_id,
        "qa_id": feedback.qa_id,
        "user_id": feedback.user_id,
        "feedback_type": feedback.feedback_type,
        "content": feedback.content,
        "created_at": feedback.created_at,
    }


@app.put("/feedback/{fid}")
def update_feedback_api(fid: int, payload: schemas.FeedbackUpdate, db: Session = Depends(get_db)):
    if crud.get_feedback_by_id(db, fid) is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="反馈不存在",
        )

    feedback = crud.update_feedback(
        db=db,
        input_fid=fid,
        input_content=payload.content,
        input_feedback_type=payload.feedback_type,
        input_knowledge_id=payload.knowledge_id,
        input_qa_id=payload.qa_id,
    )

    if feedback is None:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="关联的知识或问答对不存在",
        )

    return {
        "message": "反馈更新成功",
        "feedback": {
            "fid": feedback.fid,
            "knowledge_id": feedback.knowledge_id,
            "qa_id": feedback.qa_id,
            "user_id": feedback.user_id,
            "feedback_type": feedback.feedback_type,
            "content": feedback.content,
        }
    }


@app.delete("/feedback/{fid}")
def delete_feedback_api(fid: int, db: Session = Depends(get_db)):
    is_deleted = crud.delete_feedback(db, fid)
    if not is_deleted:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="反馈不存在",
        )
    return {"message": "反馈删除成功"}



#5.设计与搜索
'''
tags                 标签
knowledge_tags       知识和标签的绑定
related_knowledge    相关知识
knowledge_embedding  知识向量
搜索：按关键词/分类/标签查知识
'''

#5.1 标签
@app.post("/tags", status_code=http_status.HTTP_201_CREATED)
def create_tag_api(payload: schemas.TagCreate, db: Session = Depends(get_db)):
    tag = crud.create_tag(db, payload.name, payload.description)

    if tag is None:
        raise HTTPException(
            status_code=http_status.HTTP_409_CONFLICT,
            detail="标签名已存在",
        )

    return {
        "message": "标签创建成功",
        "tag": {
            "tid": tag.tid,
            "name": tag.name,
            "description": tag.description,
        }
    }


@app.get("/tags")
def get_tag_list_api(db: Session = Depends(get_db)):
    tag_list = crud.get_tag_list(db)

    return {
        "count": len(tag_list),
        "items": [
            {
                "tid": item.tid,
                "name": item.name,
                "description": item.description,
                "created_at": item.created_at,
            }
            for item in tag_list
        ]
    }


@app.get("/tags/{tid}")
def get_tag_detail_api(tid: int, db: Session = Depends(get_db)):
    tag = crud.get_tag_by_id(db, tid)
    if tag is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="标签不存在",
        )

    return {
        "tid": tag.tid,
        "name": tag.name,
        "description": tag.description,
        "created_at": tag.created_at,
    }


@app.put("/tags/{tid}")
def update_tag_api(tid: int, payload: schemas.TagUpdate, db: Session = Depends(get_db)):
    if crud.get_tag_by_id(db, tid) is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="标签不存在",
        )

    tag = crud.update_tag(
        db=db,
        input_tid=tid,
        input_new_name=payload.name,
        input_new_description=payload.description,
    )

    if tag is None:
        raise HTTPException(
            status_code=http_status.HTTP_409_CONFLICT,
            detail="标签名已被其他标签占用",
        )

    return {
        "message": "标签更新成功",
        "tag": {
            "tid": tag.tid,
            "name": tag.name,
            "description": tag.description,
        }
    }


@app.delete("/tags/{tid}")
def delete_tag_api(tid: int, db: Session = Depends(get_db)):
    is_deleted = crud.delete_tag(db, tid)
    if not is_deleted:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="标签不存在",
        )
    return {"message": "标签删除成功"}


#5.2 知识和标签的绑定
@app.post("/knowledge/{knowledge_kid}/tags", status_code=http_status.HTTP_201_CREATED)
def add_knowledge_tag_api(knowledge_kid: int, payload: schemas.KnowledgeTagCreate,
                          db: Session = Depends(get_db)):
    if crud.get_knowledge_by_id(db, knowledge_kid) is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="知识不存在",
        )

    knowledge_tag = crud.add_knowledge_tag(db, knowledge_kid, payload.tag_id)

    if knowledge_tag is None:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="标签不存在，或该知识已经绑定过这个标签",
        )

    return {
        "message": "标签绑定成功",
        "knowledge_id": knowledge_tag.knowledge_id,
        "tag_id": knowledge_tag.tag_id,
    }


@app.get("/knowledge/{knowledge_kid}/tags")
def get_knowledge_tags_api(knowledge_kid: int, db: Session = Depends(get_db)):
    if crud.get_knowledge_by_id(db, knowledge_kid) is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="知识不存在",
        )

    tag_list = crud.get_tags_by_knowledge(db, knowledge_kid)

    return {
        "count": len(tag_list),
        "items": [
            {
                "tid": item.tid,
                "name": item.name,
                "description": item.description,
            }
            for item in tag_list
        ]
    }


@app.delete("/knowledge/{knowledge_kid}/tags/{tag_id}")
def remove_knowledge_tag_api(knowledge_kid: int, tag_id: int, db: Session = Depends(get_db)):
    is_deleted = crud.remove_knowledge_tag(db, knowledge_kid, tag_id)
    if not is_deleted:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="绑定关系不存在",
        )
    return {"message": "标签解绑成功"}


@app.get("/tags/{tid}/knowledge")
def get_knowledge_by_tag_api(tid: int, db: Session = Depends(get_db)):
    if crud.get_tag_by_id(db, tid) is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="标签不存在",
        )

    knowledge_list = crud.get_knowledge_by_tag(db, tid)

    return {
        "count": len(knowledge_list),
        "items": [
            {
                "kid": item.kid,
                "title": item.title,
                "summary": item.summary,
                "category_id": item.category_id,
                "created_by": item.created_by,
                "keyword": item.keyword,
                "status": item.status,
            }
            for item in knowledge_list
        ]
    }


#5.3 相关知识
@app.post("/related_knowledge", status_code=http_status.HTTP_201_CREATED)
def create_related_knowledge_api(payload: schemas.RelatedKnowledgeCreate,
                                 db: Session = Depends(get_db)):
    relation = crud.create_related_knowledge(
        db=db,
        input_knowledge_id=payload.knowledge_id,
        input_related_knowledge_id=payload.related_knowledge_id,
        input_relevance_score=payload.relevance_score,
    )

    if relation is None:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="知识不存在，或和自己关联，或这条关联已经存在",
        )

    return {
        "message": "相关知识关联成功",
        "relation": {
            "rid": relation.rid,
            "knowledge_id": relation.knowledge_id,
            "related_knowledge_id": relation.related_knowledge_id,
            "relevance_score": float(relation.relevance_score),
        }
    }


@app.get("/related_knowledge/{knowledge_kid}")
def get_related_knowledge_api(knowledge_kid: int, db: Session = Depends(get_db)):
    if crud.get_knowledge_by_id(db, knowledge_kid) is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="知识不存在",
        )

    relation_list = crud.get_related_knowledge_list(db, knowledge_kid)

    return {
        "count": len(relation_list),
        "items": [
            {
                "rid": item.rid,
                "knowledge_id": item.knowledge_id,
                "related_knowledge_id": item.related_knowledge_id,
                "related_title": item.related_knowledge.title if item.related_knowledge else None,
                "related_summary": item.related_knowledge.summary if item.related_knowledge else None,
                "relevance_score": float(item.relevance_score),
            }
            for item in relation_list
        ]
    }


@app.delete("/related_knowledge/{rid}")
def delete_related_knowledge_api(rid: int, db: Session = Depends(get_db)):
    is_deleted = crud.delete_related_knowledge(db, rid)
    if not is_deleted:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="关联关系不存在",
        )
    return {"message": "关联关系删除成功"}


#5.4 知识向量
@app.post("/knowledge/{knowledge_kid}/embedding", status_code=http_status.HTTP_201_CREATED)
def create_embedding_api(knowledge_kid: int, payload: schemas.EmbeddingCreate,
                         db: Session = Depends(get_db)):
    embedding = crud.create_embedding(
        db=db,
        input_knowledge_id=knowledge_kid,
        input_embedding_model=payload.embedding_model,
        input_embedding_text=payload.embedding_text,
        input_embedding_vector=payload.embedding_vector,
    )

    if embedding is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="知识不存在，无法生成向量",
        )

    return {
        "message": "向量保存成功",
        "embedding": {
            "embedding_id": embedding.embedding_id,
            "knowledge_id": embedding.knowledge_id,
            "embedding_model": embedding.embedding_model,
        }
    }


@app.get("/knowledge/{knowledge_kid}/embedding")
def get_embedding_api(knowledge_kid: int, db: Session = Depends(get_db)):
    if crud.get_knowledge_by_id(db, knowledge_kid) is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="知识不存在",
        )

    embedding = crud.get_embedding_by_knowledge(db, knowledge_kid)
    if embedding is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="该知识还没有生成向量",
        )

    return {
        "embedding_id": embedding.embedding_id,
        "knowledge_id": embedding.knowledge_id,
        "embedding_model": embedding.embedding_model,
        "embedding_text": embedding.embedding_text,
        "embedding_vector": embedding.embedding_vector,
        "created_at": embedding.created_at,
    }


@app.put("/embedding/{embedding_id}")
def update_embedding_api(embedding_id: int, payload: schemas.EmbeddingUpdate,
                         db: Session = Depends(get_db)):
    if crud.get_embedding_by_id(db, embedding_id) is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="向量不存在",
        )

    embedding = crud.update_embedding(
        db=db,
        input_embedding_id=embedding_id,
        input_embedding_model=payload.embedding_model,
        input_embedding_text=payload.embedding_text,
        input_embedding_vector=payload.embedding_vector,
    )

    return {
        "message": "向量更新成功",
        "embedding": {
            "embedding_id": embedding.embedding_id,
            "knowledge_id": embedding.knowledge_id,
            "embedding_model": embedding.embedding_model,
        }
    }


@app.delete("/embedding/{embedding_id}")
def delete_embedding_api(embedding_id: int, db: Session = Depends(get_db)):
    is_deleted = crud.delete_embedding(db, embedding_id)
    if not is_deleted:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="向量不存在",
        )
    return {"message": "向量删除成功"}


#5.5 搜索
#多条件搜索：关键词、分类、标签、状态任意组合
@app.get("/search/knowledge")
def search_knowledge_api(
    keyword: str = None,
    category_id: int = None,
    tag_id: int = None,
    status: str = None,
    db: Session = Depends(get_db)
):
    knowledge_list = crud.search_knowledge(
        db=db,
        input_keyword=keyword,
        input_category_id=category_id,
        input_tag_id=tag_id,
        input_status=status,
    )

    return {
        "count": len(knowledge_list),
        "items": [
            {
                "kid": item.kid,
                "title": item.title,
                "summary": item.summary,
                "category_id": item.category_id,
                "created_by": item.created_by,
                "keyword": item.keyword,
                "status": item.status,
                "tags": [knowledge_tag.tag.name for knowledge_tag in item.knowledge_tags],
            }
            for item in knowledge_list
        ]
    }




#6.日志模块
'''
query_logs   用户提问日志
update_logs  知识操作日志
'''

#6.1 查询日志
@app.post("/query_logs", status_code=http_status.HTTP_201_CREATED)
def create_query_log_api(payload: schemas.QueryLogCreate, db: Session = Depends(get_db)):
    query_log = crud.create_query_log(
        db=db,
        input_user_id=payload.user_id,
        input_question_text=payload.question_text,
        input_answer_text=payload.answer_text,
        input_model_name=payload.model_name,
        input_retrieval_count=payload.retrieval_count,
        input_feedback_status=payload.feedback_status,
    )

    if query_log is None:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="关联的用户不存在",
        )

    return {
        "message": "查询日志已记录",
        "query_log": {
            "lid": query_log.lid,
            "user_id": query_log.user_id,
            "question_text": query_log.question_text,
            "retrieval_count": query_log.retrieval_count,
            "feedback_status": query_log.feedback_status,
        }
    }


@app.get("/query_logs")
def get_query_log_list_api(
    lid: int = None,
    user_id: int = None,
    feedback_status: str = None,
    db: Session = Depends(get_db)
):
    query_log_list = crud.get_query_log_list(
        db=db,
        input_lid=lid,
        input_user_id=user_id,
        input_feedback_status=feedback_status,
    )

    return {
        "count": len(query_log_list),
        "items": [
            {
                "lid": item.lid,
                "user_id": item.user_id,
                "question_text": item.question_text,
                "answer_text": item.answer_text,
                "model_name": item.model_name,
                "retrieval_count": item.retrieval_count,
                "feedback_status": item.feedback_status,
                "created_at": item.created_at,
            }
            for item in query_log_list
        ]
    }


@app.get("/query_logs/{lid}")
def get_query_log_detail_api(lid: int, db: Session = Depends(get_db)):
    query_log = crud.get_query_log_by_id(db, lid)
    if query_log is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="查询日志不存在",
        )

    return {
        "lid": query_log.lid,
        "user_id": query_log.user_id,
        "question_text": query_log.question_text,
        "answer_text": query_log.answer_text,
        "model_name": query_log.model_name,
        "retrieval_count": query_log.retrieval_count,
        "feedback_status": query_log.feedback_status,
        "created_at": query_log.created_at,
    }


@app.put("/query_logs/{lid}")
def update_query_log_api(lid: int, payload: schemas.QueryLogUpdate, db: Session = Depends(get_db)):
    if crud.get_query_log_by_id(db, lid) is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="查询日志不存在",
        )

    query_log = crud.update_query_log(
        db=db,
        input_lid=lid,
        input_answer_text=payload.answer_text,
        input_model_name=payload.model_name,
        input_retrieval_count=payload.retrieval_count,
        input_feedback_status=payload.feedback_status,
    )

    return {
        "message": "查询日志更新成功",
        "query_log": {
            "lid": query_log.lid,
            "user_id": query_log.user_id,
            "retrieval_count": query_log.retrieval_count,
            "feedback_status": query_log.feedback_status,
        }
    }


@app.delete("/query_logs/{lid}")
def delete_query_log_api(lid: int, db: Session = Depends(get_db)):
    is_deleted = crud.delete_query_log(db, lid)
    if not is_deleted:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="查询日志不存在",
        )
    return {"message": "查询日志删除成功"}


#6.2 更新日志
@app.post("/update_logs", status_code=http_status.HTTP_201_CREATED)
def create_update_log_api(payload: schemas.UpdateLogCreate, db: Session = Depends(get_db)):
    update_log = crud.create_update_log(
        db=db,
        input_knowledge_id=payload.knowledge_id,
        input_user_id=payload.user_id,
        input_action_type=payload.action_type,
        input_old_value=payload.old_value,
        input_new_value=payload.new_value,
    )

    if update_log is None:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="关联的知识或用户不存在，或操作类型非法",
        )

    return {
        "message": "更新日志已记录",
        "update_log": {
            "log_id": update_log.log_id,
            "knowledge_id": update_log.knowledge_id,
            "user_id": update_log.user_id,
            "action_type": update_log.action_type,
        }
    }


@app.get("/update_logs")
def get_update_log_list_api(
    log_id: int = None,
    knowledge_id: int = None,
    user_id: int = None,
    action_type: str = None,
    db: Session = Depends(get_db)
):
    update_log_list = crud.get_update_log_list(
        db=db,
        input_log_id=log_id,
        input_knowledge_id=knowledge_id,
        input_user_id=user_id,
        input_action_type=action_type,
    )

    return {
        "count": len(update_log_list),
        "items": [
            {
                "log_id": item.log_id,
                "knowledge_id": item.knowledge_id,
                "user_id": item.user_id,
                "action_type": item.action_type,
                "old_value": item.old_value,
                "new_value": item.new_value,
                "created_at": item.created_at,
            }
            for item in update_log_list
        ]
    }


@app.get("/update_logs/{log_id}")
def get_update_log_detail_api(log_id: int, db: Session = Depends(get_db)):
    update_log = crud.get_update_log_by_id(db, log_id)
    if update_log is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="更新日志不存在",
        )

    return {
        "log_id": update_log.log_id,
        "knowledge_id": update_log.knowledge_id,
        "user_id": update_log.user_id,
        "action_type": update_log.action_type,
        "old_value": update_log.old_value,
        "new_value": update_log.new_value,
        "created_at": update_log.created_at,
    }


@app.delete("/update_logs/{log_id}")
def delete_update_log_api(log_id: int, db: Session = Depends(get_db)):
    is_deleted = crud.delete_update_log(db, log_id)
    if not is_deleted:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="更新日志不存在",
        )
    return {"message": "更新日志删除成功"}




#7.AI模块
