from fastapi import APIRouter, Depends, HTTPException, status as http_status
from sqlalchemy.orm import Session

from app import crud, schemas
from app.database import get_db

router = APIRouter()


#4.反馈模块
'''
用户点赞/差评
错误反馈
建议反馈
反馈统计
'''
@router.post("/feedback", status_code=http_status.HTTP_201_CREATED)
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


@router.get("/feedback")
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


@router.get("/feedback/{fid}")
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


@router.put("/feedback/{fid}")
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


@router.delete("/feedback/{fid}")
def delete_feedback_api(fid: int, db: Session = Depends(get_db)):
    is_deleted = crud.delete_feedback(db, fid)
    if not is_deleted:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="反馈不存在",
        )
    return {"message": "反馈删除成功"}
