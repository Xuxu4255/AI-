from fastapi import APIRouter, Depends, HTTPException, status as http_status
from sqlalchemy.orm import Session

from app import crud, schemas
from app.database import get_db

router = APIRouter()


#5.4 知识向量
@router.post("/knowledge/{knowledge_kid}/embedding", status_code=http_status.HTTP_201_CREATED)
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


@router.get("/knowledge/{knowledge_kid}/embedding")
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


@router.put("/embedding/{embedding_id}")
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


@router.delete("/embedding/{embedding_id}")
def delete_embedding_api(embedding_id: int, db: Session = Depends(get_db)):
    is_deleted = crud.delete_embedding(db, embedding_id)
    if not is_deleted:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="向量不存在",
        )
    return {"message": "向量删除成功"}
