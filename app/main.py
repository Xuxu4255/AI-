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
tags
knowledge_tags
related_knowledge
knowledge_embedding
'''




#6.日志模块
'''
query_logs
update_logs
'''




#7.AI模块
