from fastapi import APIRouter, Depends, HTTPException, status as http_status
from sqlalchemy.orm import Session

from app import crud, schemas
from app.database import get_db

router = APIRouter()


#5.3 相关知识
@router.post("/related_knowledge", status_code=http_status.HTTP_201_CREATED)
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


@router.get("/related_knowledge/{knowledge_kid}")
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


@router.delete("/related_knowledge/{rid}")
def delete_related_knowledge_api(rid: int, db: Session = Depends(get_db)):
    is_deleted = crud.delete_related_knowledge(db, rid)
    if not is_deleted:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="关联关系不存在",
        )
    return {"message": "关联关系删除成功"}
