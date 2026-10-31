from fastapi import APIRouter, Depends, HTTPException, status as http_status
from sqlalchemy.orm import Session, joinedload
from typing import Literal, Optional

from app import crud, schemas, models, security
from app.database import get_db
from app.services.indexing import refresh_index

router = APIRouter()


#2.知识库crud
'''
创建知识
查询知识列表
查询单条知识
修改知识
删除知识
'''
#payload，前端转来的JSON数据对象

@router.post("/knowledge", status_code=http_status.HTTP_201_CREATED)
def create_knowledge_api(payload: schemas.KnowledgeCreate, db: Session = Depends(get_db), admin=Depends(security.require_admin)):
    knowledge = crud.create_knowledge(
        db=db,
        input_title=payload.title,
        input_content=payload.content,
        input_summary=payload.summary,
        input_category_id=payload.category_id,
        input_created_by=admin.uid,
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



@router.get("/knowledge/{knowledge_kid}")
def get_knowledge_detail_api(knowledge_kid: int, db: Session = Depends(get_db), user=Depends(security.get_current_user)):
    knowledge = crud.get_knowledge_by_id(db, knowledge_kid)
    if knowledge is None or (knowledge.status != "published" and user.role != "admin"):
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
        "review_note": crud.get_knowledge_review_notes(db, [knowledge.kid]).get(knowledge.kid, '') if user.role == 'admin' else '',
        "created_by_name": knowledge.creator.username if user.role == 'admin' else '',
        "sources": [{'source_type': d.source_type, 'source_name': d.source_name,
                     'source_url': d.source_url} for d in knowledge.documents],
    }


@router.put("/knowledge/{knowledge_kid}")
def update_knowledge_api(knowledge_kid: int, payload: schemas.KnowledgeUpdate, db: Session = Depends(get_db), admin=Depends(security.require_admin)):
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
        input_created_by=None,
        input_keyword=payload.keyword,
    )

    if knowledge is None:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="关联的分类或用户不存在",
        )

    index_status = refresh_index(db, knowledge) if knowledge.status == "published" else "draft"
    return {
        "message": "知识更新成功",
        "index_status": index_status,
        "knowledge": {
            "kid": knowledge.kid,
            "title": knowledge.title,
            "category_id": knowledge.category_id,
            "keyword": knowledge.keyword,
        }
    }


@router.delete("/knowledge/{knowledge_kid}")
def delete_knowledge_api(knowledge_kid: int, db: Session = Depends(get_db), admin=Depends(security.require_admin)):
    is_deleted = crud.delete_knowledge(db, knowledge_kid)
    if not is_deleted:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="知识不存在",
        )
    return {"message": "知识删除成功"}


@router.get("/knowledge")
def get_knowledge_list_api(category_id: int = None, keyword: str = None,
    status: Optional[Literal['draft', 'published', 'rejected', 'deleted']] = None,
    db: Session = Depends(get_db), user=Depends(security.get_current_user)):
    query = db.query(models.Knowledge).options(joinedload(models.Knowledge.creator))
    if user.role != "admin":
        query = query.filter(models.Knowledge.status == "published")
    if category_id is not None:
        query = query.filter(models.Knowledge.category_id == category_id)
    if status is not None:
        query = query.filter(models.Knowledge.status == status)
    if keyword:
        query = query.filter(models.Knowledge.keyword.contains(keyword, autoescape=True))
    knowledge_list = query.order_by(models.Knowledge.kid.desc()).all()
    review_notes = crud.get_knowledge_review_notes(db, [k.kid for k in knowledge_list]) if user.role == 'admin' else {}
    submission_ids = {row[0] for row in db.query(models.Document.knowledge_id).filter(
        models.Document.knowledge_id.in_([k.kid for k in knowledge_list]),
        models.Document.source_type == 'student_submission').all()} if user.role == 'admin' else set()
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
                "review_note": review_notes.get(item.kid, ''),
                "created_by_name": item.creator.username if user.role == 'admin' else '',
                "is_submission": item.kid in submission_ids,
            }
            for item in knowledge_list
        ]
    }


@router.patch("/knowledge/{knowledge_id}/publish")
def publish_knowledge_api(
    knowledge_id: int,
    db: Session = Depends(get_db),
    admin=Depends(security.require_admin),
):
    # 1. 调用 CRUD 发布知识
    try:
        knowledge = crud.review_knowledge(db, knowledge_id, 'publish', admin.uid)
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error))
    # 2. 如果返回 None，抛出 404
    if knowledge is None:
        raise HTTPException(
            status_code=404,
            detail="知识不存在",
        )
    # 3. 返回成功信息和知识编号
    else:
        index_status = refresh_index(db, knowledge)
        return {"message": "发布成功",
                "index_status": index_status,
                "knowledge_id": knowledge.kid,
                "status": knowledge.status,
                }


@router.patch('/knowledge/{knowledge_id}/review')
def review_knowledge_api(knowledge_id: int, payload: schemas.KnowledgeReview,
    db: Session = Depends(get_db), admin=Depends(security.require_admin)):
    if payload.action == 'reject' and not payload.reason:
        raise HTTPException(422, '请填写驳回理由')
    try:
        knowledge = crud.review_knowledge(db, knowledge_id, payload.action, admin.uid, payload.reason)
    except ValueError as error:
        raise HTTPException(409, str(error))
    if knowledge is None:
        raise HTTPException(404, '知识不存在')
    return {'knowledge_id': knowledge.kid, 'status': knowledge.status,
            'review_note': payload.reason if payload.action == 'reject' else '',
            'message': {'reject': '已驳回', 'withdraw': '已撤回，公开搜索不再显示', 'restore': '已恢复为待审核'}[payload.action]}
