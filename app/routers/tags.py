from fastapi import APIRouter, Depends, HTTPException, status as http_status
from sqlalchemy.orm import Session

from app import crud, schemas
from app.database import get_db

router = APIRouter()


#5.设计与搜索
'''
tags                 标签
knowledge_tags       知识和标签的绑定
related_knowledge    相关知识
knowledge_embedding  知识向量
搜索：按关键词/分类/标签查知识
'''

#5.1 标签
@router.post("/tags", status_code=http_status.HTTP_201_CREATED)
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


@router.get("/tags")
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


@router.get("/tags/{tid}")
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


@router.put("/tags/{tid}")
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


@router.delete("/tags/{tid}")
def delete_tag_api(tid: int, db: Session = Depends(get_db)):
    is_deleted = crud.delete_tag(db, tid)
    if not is_deleted:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="标签不存在",
        )
    return {"message": "标签删除成功"}


#5.2 知识和标签的绑定
@router.post("/knowledge/{knowledge_kid}/tags", status_code=http_status.HTTP_201_CREATED)
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


@router.get("/knowledge/{knowledge_kid}/tags")
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


@router.delete("/knowledge/{knowledge_kid}/tags/{tag_id}")
def remove_knowledge_tag_api(knowledge_kid: int, tag_id: int, db: Session = Depends(get_db)):
    is_deleted = crud.remove_knowledge_tag(db, knowledge_kid, tag_id)
    if not is_deleted:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="绑定关系不存在",
        )
    return {"message": "标签解绑成功"}


@router.get("/tags/{tid}/knowledge")
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
