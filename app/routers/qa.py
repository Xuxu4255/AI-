from fastapi import APIRouter, Depends, HTTPException, status as http_status
from sqlalchemy.orm import Session

from app import crud, schemas
from app.database import get_db

router = APIRouter()


#3.问答模块
'''
创建问答对
查询问答对
审核问答对
处理问答反馈
'''
@router.post("/qa_pairs", status_code=http_status.HTTP_201_CREATED)
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

@router.get("/qa_pairs")
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

@router.patch("/qa_pairs/{qid}/review")
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
