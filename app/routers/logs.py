from fastapi import APIRouter, Depends, HTTPException, status as http_status
from sqlalchemy.orm import Session

from app import crud, schemas
from app.database import get_db

router = APIRouter()


#6.日志模块
'''
query_logs   用户提问日志
update_logs  知识操作日志
'''

#6.1 查询日志
@router.post("/query_logs", status_code=http_status.HTTP_201_CREATED)
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


@router.get("/query_logs")
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


@router.get("/query_logs/{lid}")
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


@router.put("/query_logs/{lid}")
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


@router.delete("/query_logs/{lid}")
def delete_query_log_api(lid: int, db: Session = Depends(get_db)):
    is_deleted = crud.delete_query_log(db, lid)
    if not is_deleted:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="查询日志不存在",
        )
    return {"message": "查询日志删除成功"}


#6.2 更新日志
@router.post("/update_logs", status_code=http_status.HTTP_201_CREATED)
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


@router.get("/update_logs")
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


@router.get("/update_logs/{log_id}")
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


@router.delete("/update_logs/{log_id}")
def delete_update_log_api(log_id: int, db: Session = Depends(get_db)):
    is_deleted = crud.delete_update_log(db, log_id)
    if not is_deleted:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="更新日志不存在",
        )
    return {"message": "更新日志删除成功"}
