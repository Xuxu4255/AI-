"""分类管理：登录用户浏览，管理员维护，有知识的分类禁止删除。"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app import crud, models, schemas, security
from app.database import get_db
from app.services.spaces import public_filter

router = APIRouter()


def serialize(category, count=0):
    return {"cid": category.cid, "name": category.name,
            "description": category.description, "knowledge_count": count}


@router.get("/categories")
def list_categories(db: Session = Depends(get_db), user=Depends(security.get_current_user)):
    counts = db.query(models.Knowledge.category_id, func.count(models.Knowledge.kid).label("n")).outerjoin(models.Moderation, models.Moderation.knowledge_id == models.Knowledge.kid).filter(public_filter())
    counts = counts.group_by(models.Knowledge.category_id).subquery()
    rows = db.query(models.Category, func.coalesce(counts.c.n, 0)).outerjoin(
        counts, counts.c.category_id == models.Category.cid).order_by(models.Category.cid).all()
    return {"count": len(rows), "items": [serialize(c, n) for c, n in rows]}


@router.get("/categories/{category_id}")
def get_category(category_id: int, db: Session = Depends(get_db), user=Depends(security.get_current_user)):
    category = crud.get_category_by_id(db, category_id)
    if category is None:
        raise HTTPException(404, "分类不存在")
    query = db.query(models.Knowledge).outerjoin(models.Moderation, models.Moderation.knowledge_id == models.Knowledge.kid).filter(models.Knowledge.category_id == category_id, public_filter())
    return serialize(category, query.count())


@router.post("/categories", status_code=201)
def create_category(payload: schemas.CategoryCreate, db: Session = Depends(get_db), admin=Depends(security.require_admin)):
    try:
        category = crud.create_category(db, payload.name, payload.description)
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "分类名称已存在")
    return {"message": "分类已创建", "category": serialize(category)}


@router.put("/categories/{category_id}")
def update_category(category_id: int, payload: schemas.CategoryUpdate, db: Session = Depends(get_db), admin=Depends(security.require_admin)):
    try:
        category = crud.update_category(db, category_id, payload.name, payload.description)
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "分类名称已存在")
    if category is None:
        raise HTTPException(404, "分类不存在")
    return {"message": "分类已更新", "category": serialize(category)}


@router.delete("/categories/{category_id}")
def delete_category(category_id: int, db: Session = Depends(get_db), admin=Depends(security.require_admin)):
    if crud.get_category_by_id(db, category_id) is None:
        raise HTTPException(404, "分类不存在")
    if db.query(models.Knowledge.kid).filter(models.Knowledge.category_id == category_id).first():
        raise HTTPException(409, "分类下还有知识，请先转移知识后再删除")
    try:
        db.query(models.LibraryShelfAppearance).filter_by(space='public', category_id=category_id).delete()
        db.query(models.PlanetSetting).filter_by(category_id=category_id).delete()
        crud.delete_category(db, category_id)
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "分类仍被引用，无法删除")
    return {"message": "分类已删除"}
