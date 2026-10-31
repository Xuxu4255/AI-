"""登录用户的投稿入口；公开搜索和管理员审核沿用知识管理接口。"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional, Literal
from app import crud, schemas, security, models
from app.database import get_db
from app.services import submissions

router = APIRouter(prefix='/submissions', tags=['知识投稿'])


def serialize(item, review_note='', include_content=False):
    source = next((d for d in item.documents if d.source_type == submissions.SOURCE_TYPE), None)
    result = {'kid': item.kid, 'title': item.title, 'summary': item.summary,
              'category_id': item.category_id, 'keyword': item.keyword,
              'created_by': item.created_by, 'status': item.status,
              'review_note': review_note if item.status == 'rejected' else '',
              'source_name': source.source_name if source else '',
              'source_url': source.source_url if source else None}
    if include_content:
        result['content'] = item.content
        result['sources'] = [{'source_type': d.source_type, 'source_name': d.source_name,
                              'source_url': d.source_url} for d in item.documents]
    return result


@router.post('', status_code=201)
def submit(payload: schemas.KnowledgeSubmission, db: Session = Depends(get_db),
           user=Depends(security.get_current_user)):
    try:
        item = submissions.save(db, user, payload)
    except LookupError as error:
        raise HTTPException(400, str(error))
    return {'message': '投稿已提交，等待管理员审核', 'knowledge': serialize(item)}


@router.get('')
def mine(status: Optional[Literal['draft', 'published', 'rejected']] = None,
         db: Session = Depends(get_db), user=Depends(security.get_current_user)):
    query = submissions.own_query(db, user.uid)
    if status:
        query = query.filter(models.Knowledge.status == status)
    items = query.order_by(models.Knowledge.kid.desc()).all()
    notes = crud.get_knowledge_review_notes(db, [item.kid for item in items])
    return {'count': len(items), 'items': [serialize(item, notes.get(item.kid, '')) for item in items]}


@router.get('/{knowledge_id}')
def detail(knowledge_id: int, db: Session = Depends(get_db), user=Depends(security.get_current_user)):
    item = submissions.own_query(db, user.uid).filter(models.Knowledge.kid == knowledge_id).first()
    if item is None:
        raise HTTPException(404, '投稿不存在')
    notes = crud.get_knowledge_review_notes(db, [item.kid])
    return serialize(item, notes.get(item.kid, ''), include_content=True)


@router.put('/{knowledge_id}')
def resubmit(knowledge_id: int, payload: schemas.KnowledgeSubmission,
             db: Session = Depends(get_db), user=Depends(security.get_current_user)):
    try:
        item = submissions.save(db, user, payload, knowledge_id)
    except LookupError as error:
        raise HTTPException(400, str(error))
    except ValueError as error:
        raise HTTPException(409, str(error))
    if item is None:
        raise HTTPException(404, '投稿不存在')
    return {'message': '修改已提交，等待重新审核', 'knowledge': serialize(item)}
