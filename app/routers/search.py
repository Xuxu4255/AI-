"""兼容关键词搜索，仅查询公有范围，管理员也不能绕过。"""
from fastapi import APIRouter, Depends
from sqlalchemy import or_
from sqlalchemy.orm import Session
from app import models, security
from app.database import get_db
from app.services import spaces

router = APIRouter()


@router.get('/search/knowledge')
def search(keyword: str = None, category_id: int = None, tag_id: int = None, status: str = None,
           db: Session = Depends(get_db), user=Depends(security.get_current_user)):
    query = spaces.scoped(db, user, 'public', category_id)
    if keyword:
        query = query.filter(or_(*[c.contains(keyword, autoescape=True) for c in
            [models.Knowledge.title, models.Knowledge.content, models.Knowledge.summary, models.Knowledge.keyword]]))
    if tag_id is not None:
        query = query.filter(db.query(models.KnowledgeTag.knowledge_id).filter(
            models.KnowledgeTag.knowledge_id == models.Knowledge.kid, models.KnowledgeTag.tag_id == tag_id).exists())
    items = query.order_by(models.Knowledge.kid.desc()).all()
    return {'count': len(items), 'items': [spaces.serialize(db, k, user) for k in items]}
