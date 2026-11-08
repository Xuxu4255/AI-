"""兼容旧阅读地址；写入统一通过知识星海的所有权校验。"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app import security, models
from app.database import get_db
from app.services import spaces
from app.services.indexing import refresh_index

router = APIRouter()


@router.get('/knowledge')
def listing(category_id: int = None, keyword: str = None, status: str = None,
    db: Session = Depends(get_db), user=Depends(security.get_current_user)):
    query = spaces.scoped(db, user, 'public', category_id)
    if keyword: query = query.filter(models.Knowledge.keyword.contains(keyword, autoescape=True))
    if status: query = query.filter(models.Knowledge.status == status)
    items = query.order_by(models.Knowledge.kid.desc()).all()
    return {'count': len(items), 'items': [spaces.serialize(db, k, user) for k in items]}


@router.get('/knowledge/{knowledge_kid}')
def detail(knowledge_kid: int, db: Session = Depends(get_db), user=Depends(security.get_current_user)):
    return spaces.serialize(db, spaces.get_item(db, user, knowledge_kid), user, detail=True)


@router.post('/knowledge')
def legacy_create(db: Session = Depends(get_db), user=Depends(security.get_current_user)):
    raise HTTPException(410, '请使用 /api/knowledge 创建知识并指定个人门类')


@router.put('/knowledge/{knowledge_kid}')
def legacy_update(knowledge_kid: int, db: Session = Depends(get_db), user=Depends(security.get_current_user)):
    spaces.get_item(db, user, knowledge_kid, owner=True)
    raise HTTPException(410, '请使用 /api/knowledge/{kid} 编辑知识')


@router.delete('/knowledge/{knowledge_kid}')
def legacy_delete(knowledge_kid: int, db: Session = Depends(get_db), user=Depends(security.get_current_user)):
    from app.routers.spaces import delete_knowledge
    return delete_knowledge(knowledge_kid, db, user)


@router.patch('/knowledge/{knowledge_id}/publish')
def publish(knowledge_id: int, db: Session = Depends(get_db), user=Depends(security.get_current_user)):
    from app.routers.spaces import share
    from app.space_schemas import VisibilityInput
    return share(knowledge_id, VisibilityInput(visibility='public'), db, user)


@router.patch('/knowledge/{knowledge_id}/review')
def retired_review(knowledge_id: int, db: Session = Depends(get_db), user=Depends(security.get_current_user)):
    raise HTTPException(410, '新版无需审核；请使用作者分享/撤回，或公有内容下架接口')
