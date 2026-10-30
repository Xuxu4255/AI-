from fastapi import APIRouter, Depends, HTTPException, status as http_status
from sqlalchemy.orm import Session

from app import crud, schemas
from app.database import get_db

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



@router.get("/knowledge/{knowledge_kid}")
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


@router.put("/knowledge/{knowledge_kid}")
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


@router.delete("/knowledge/{knowledge_kid}")
def delete_knowledge_api(knowledge_kid: int, db: Session = Depends(get_db)):
    is_deleted = crud.delete_knowledge(db, knowledge_kid)
    if not is_deleted:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="知识不存在",
        )
    return {"message": "知识删除成功"}


@router.get("/knowledge")
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
