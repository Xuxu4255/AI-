from fastapi import APIRouter, Depends, HTTPException, status as http_status
from sqlalchemy.orm import Session

from app import crud, schemas
from app.database import get_db

router = APIRouter()


#5.5 搜索
#多条件搜索：关键词、分类、标签、状态任意组合
@router.get("/search/knowledge")
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
