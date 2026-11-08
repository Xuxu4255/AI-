"""双空间、个人整理、天体展示与外观设置。"""
from typing import Literal, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app import models as m, space_schemas as s, security
from app.database import get_db
from app.services import spaces as svc
from app.services.indexing import refresh_index
import json

router = APIRouter(prefix='/api', tags=['知识星海'])
LIBRARY_DEFAULT_STYLES = {'Python': 'oak', 'C++': 'glass', 'Java': 'arch',
    'FastAPI': 'wide', 'MySQL': 'oak', 'Docker': 'wide'}


@router.get('/library/shelves')
def library_shelves(space: Literal['personal', 'public'] = 'public',
    db: Session = Depends(get_db), user=Depends(security.get_current_user)):
    """图书馆分类：收起被替换的数据集门类，保留新建的空书架。"""
    if space == 'personal':
        svc.bootstrap_personal(db, user)
        cats = db.query(m.PersonalCategory).filter_by(user_id=user.uid).order_by(m.PersonalCategory.id).all()
    else:
        cats = db.query(m.Category).order_by(m.Category.cid).all()
    replacement = db.query(m.SpaceEvent).filter_by(action='替换公共知识库').order_by(m.SpaceEvent.id).first()
    legacy_ids = {kid for (kid,) in db.query(m.Document.knowledge_id).join(m.Knowledge).filter(
        m.Document.source_type.in_(['online', 'nbu_official']),
        m.Knowledge.created_at <= replacement.created_at)} if replacement else set()
    styles = {row.category_id: row.style for row in db.query(m.LibraryShelfAppearance).filter_by(space=space)}
    items = []
    for cat in cats:
        cid = cat.id if space == 'personal' else cat.cid
        if space == 'personal':
            member_ids = {kid for (kid,) in db.query(m.PersonalEntry.knowledge_id).filter_by(user_id=user.uid, category_id=cid)}
        else:
            member_ids = {kid for (kid,) in db.query(m.Knowledge.kid).filter_by(category_id=cid)}
            setting = db.get(m.PlanetSetting, cid)
            if setting and not setting.visible:
                continue
        # 不删除个人草稿；历史内容仍可从完整管理界面访问。
        if member_ids and member_ids.issubset(legacy_ids):
            continue
        items.append(dict(id=cid, name=cat.name, count=svc.scoped(db, user, space, cid).count(),
            style=styles.get(cid, LIBRARY_DEFAULT_STYLES.get(cat.name, 'glass'))))
    return dict(items=items, total=sum(cat['count'] for cat in items))


@router.post('/library/shelves', status_code=201)
def create_library_shelf(payload: s.ShelfCreate, db: Session = Depends(get_db), user=Depends(security.get_current_user)):
    if payload.space == 'public' and user.role != 'admin':
        raise HTTPException(403, '只有管理员可以新建公共书架')
    category = (m.PersonalCategory(user_id=user.uid, name=payload.name, color='#96CBAF')
        if payload.space == 'personal' else m.Category(name=payload.name, description='图书馆书架'))
    try:
        db.add(category); db.flush()
        cid = category.id if payload.space == 'personal' else category.cid
        db.add(m.LibraryShelfAppearance(space=payload.space, category_id=cid, style=payload.style))
        db.commit()
    except IntegrityError:
        db.rollback(); raise HTTPException(409, '书架名称已存在')
    return dict(id=cid, name=category.name, style=payload.style, count=0)


@router.patch('/library/shelves/{cid}/style')
def change_shelf_style(cid: int, payload: s.ShelfStyleInput, space: Literal['personal', 'public'] = 'personal',
    db: Session = Depends(get_db), user=Depends(security.get_current_user)):
    if space == 'personal':
        svc.own_category(db, user, cid)
    else:
        if user.role != 'admin': raise HTTPException(403, '只有管理员可以修改公共书架')
        if not db.get(m.Category, cid): raise HTTPException(404, '书架不存在')
    row = db.query(m.LibraryShelfAppearance).filter_by(space=space, category_id=cid).with_for_update().first()
    if row is None:
        row = m.LibraryShelfAppearance(space=space, category_id=cid); db.add(row)
    row.style = payload.style
    try:
        db.commit()
    except IntegrityError:
        db.rollback(); raise HTTPException(409, '书架已被更新，请刷新后重试')
    return dict(id=cid, style=row.style)


@router.get('/universe')
def universe(space: Literal['personal', 'public'] = 'public', db: Session = Depends(get_db), user=Depends(security.get_current_user)):
    if space == 'personal':
        svc.bootstrap_personal(db, user)
        cats = db.query(m.PersonalCategory).filter_by(user_id=user.uid).order_by(m.PersonalCategory.id).all()
    else:
        cats = db.query(m.Category).order_by(m.Category.cid).all()
    nodes = []
    for i, cat in enumerate(cats):
        cid = cat.id if space == 'personal' else cat.cid
        count = svc.scoped(db, user, space, cid).count()
        setting = db.get(m.PlanetSetting, cid) if space == 'public' else None
        if space == 'public' and (not count or (setting and not setting.visible)):
            continue
        nodes.append(dict(id=cid, name=cat.name, count=count,
            color=cat.color if space == 'personal' else '#74DCFF',
            style=setting.style if setting else svc.STYLES[i % len(svc.STYLES)],
            position=setting.position if setting else i))
    nodes.sort(key=lambda n: (n['position'], n['id']))
    edges = []
    if space == 'personal':
        allowed = {k.kid for k in svc.scoped(db, user, 'personal')}
        memberships = {e.knowledge_id: e.category_id for e in db.query(m.PersonalEntry).filter_by(user_id=user.uid)}
        for link in db.query(m.PersonalLink).filter_by(user_id=user.uid):
            a, b = memberships.get(link.source_id), memberships.get(link.target_id)
            if a and b and a != b and link.source_id in allowed and link.target_id in allowed:
                edges.append(dict(source=a, target=b, relation=link.relation))
    return dict(nodes=nodes, edges=edges, total=svc.scoped(db, user, space).count(), space=space)


@router.get('/personal/categories')
def personal_categories(db: Session = Depends(get_db), user=Depends(security.get_current_user)):
    svc.bootstrap_personal(db, user)
    cats = db.query(m.PersonalCategory).filter_by(user_id=user.uid).order_by(m.PersonalCategory.id).all()
    return {'items': [dict(id=c.id, name=c.name, color=c.color) for c in cats]}


@router.post('/personal/categories', status_code=201)
def create_personal_category(payload: s.PersonalCategoryInput, db: Session = Depends(get_db), user=Depends(security.get_current_user)):
    cat = m.PersonalCategory(user_id=user.uid, **payload.model_dump())
    db.add(cat)
    try:
        db.commit()
    except IntegrityError:
        db.rollback(); raise HTTPException(409, '个人门类名称已存在')
    return dict(id=cat.id, name=cat.name, color=cat.color)


@router.put('/personal/categories/{cid}')
def edit_personal_category(cid: int, payload: s.PersonalCategoryInput, db: Session = Depends(get_db), user=Depends(security.get_current_user)):
    cat = svc.own_category(db, user, cid)
    cat.name, cat.color = payload.name, payload.color
    try:
        db.commit()
    except IntegrityError:
        db.rollback(); raise HTTPException(409, '个人门类名称已存在')
    return dict(id=cat.id, name=cat.name, color=cat.color)


@router.delete('/personal/categories/{cid}')
def delete_personal_category(cid: int, move_to: Optional[int] = None, db: Session = Depends(get_db), user=Depends(security.get_current_user)):
    cat = svc.own_category(db, user, cid)
    entries = db.query(m.PersonalEntry).filter_by(user_id=user.uid, category_id=cid)
    visible_ids = svc.accessible(db, user).with_entities(m.Knowledge.kid).subquery()
    if entries.filter(m.PersonalEntry.knowledge_id.in_(db.query(visible_ids.c.kid))).count():
        if move_to is None or move_to == cid:
            raise HTTPException(409, '门类中还有知识，请指定另一个个人门类承接')
        svc.own_category(db, user, move_to)
        entries.update({'category_id': move_to}, synchronize_session=False)
    else:
        entries.delete(synchronize_session=False)
    db.query(m.LibraryShelfAppearance).filter_by(space='personal', category_id=cid).delete()
    db.delete(cat); db.commit()
    return {'message': '门类已删除，知识正文保留'}


@router.get('/knowledge')
def list_knowledge(space: Literal['personal', 'public'] = 'public', category_id: Optional[int] = None,
    q: str = Query(default='', max_length=500), page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100), db: Session = Depends(get_db), user=Depends(security.get_current_user)):
    query = svc.scoped(db, user, space, category_id)
    if q.strip():
        query = query.filter(or_(*[col.contains(q.strip(), autoescape=True) for col in
            [m.Knowledge.title, m.Knowledge.content, m.Knowledge.summary, m.Knowledge.keyword]]))
    total = query.count()
    items = query.order_by(m.Knowledge.updated_at.desc(), m.Knowledge.kid.desc()).offset((page-1)*page_size).limit(page_size).all()
    return dict(count=total, items=[svc.serialize(db, k, user) for k in items], page=page, page_size=page_size)


@router.get('/knowledge/{kid}')
def knowledge_detail(kid: int, db: Session = Depends(get_db), user=Depends(security.get_current_user)):
    return svc.serialize(db, svc.get_item(db, user, kid), user, detail=True)


def save_knowledge(db, user, payload, kid=None):
    svc.own_category(db, user, payload.personal_category_id)
    if not db.get(m.Category, payload.category_id):
        raise HTTPException(404, '公共门类不存在')
    item = svc.get_item(db, user, kid, owner=True) if kid else m.Knowledge(created_by=user.uid)
    for name in ['title', 'content', 'summary', 'keyword', 'category_id']:
        setattr(item, name, getattr(payload, name))
    item.status = 'published' if payload.visibility == 'public' else 'draft'
    db.add(item); db.flush()
    entry = db.query(m.PersonalEntry).filter_by(user_id=user.uid, knowledge_id=item.kid).first()
    if not entry:
        entry = m.PersonalEntry(user_id=user.uid, knowledge_id=item.kid)
        db.add(entry)
    entry.category_id = payload.personal_category_id
    source = db.query(m.Document).filter_by(knowledge_id=item.kid, source_type='star_user').first()
    if not source:
        source = m.Document(knowledge_id=item.kid, source_type='star_user'); db.add(source)
    source.source_name, source.source_url = payload.source_name or '用户分享', payload.source_url
    svc.log(db, user, item, 'update' if kid else 'create', visibility=payload.visibility)
    db.commit()
    index_status = refresh_index(db, item)
    return dict(knowledge=svc.serialize(db, item, user, detail=True), index_status=index_status)


@router.post('/knowledge', status_code=201)
def create_knowledge(payload: s.KnowledgeInput, db: Session = Depends(get_db), user=Depends(security.get_current_user)):
    return save_knowledge(db, user, payload)


@router.put('/knowledge/{kid}')
def edit_knowledge(kid: int, payload: s.KnowledgeInput, db: Session = Depends(get_db), user=Depends(security.get_current_user)):
    return save_knowledge(db, user, payload, kid)


@router.patch('/knowledge/{kid}/visibility')
def share(kid: int, payload: s.VisibilityInput, db: Session = Depends(get_db), user=Depends(security.get_current_user)):
    item = svc.get_item(db, user, kid, owner=True)
    if payload.category_id is not None:
        if not db.get(m.Category, payload.category_id): raise HTTPException(404, '公共门类不存在')
        item.category_id = payload.category_id
    item.status = 'published' if payload.visibility == 'public' else 'draft'
    svc.log(db, user, item, 'publish' if item.status == 'published' else 'update', visibility=payload.visibility)
    db.commit()
    return dict(knowledge=svc.serialize(db, item, user), index_status=refresh_index(db, item))


@router.delete('/knowledge/{kid}')
def delete_knowledge(kid: int, db: Session = Depends(get_db), user=Depends(security.get_current_user)):
    item = svc.get_item(db, user, kid, owner=True)
    item.status = 'deleted'
    db.query(m.PersonalEntry).filter_by(user_id=user.uid, knowledge_id=kid).delete()
    svc.log(db, user, item, 'delete', event='soft_delete')
    db.commit()
    return {'message': '知识已删除'}


@router.put('/knowledge/{kid}/organize')
def organize(kid: int, payload: s.EntryInput, db: Session = Depends(get_db), user=Depends(security.get_current_user)):
    svc.get_item(db, user, kid)
    svc.own_category(db, user, payload.personal_category_id)
    entry = db.query(m.PersonalEntry).filter_by(user_id=user.uid, knowledge_id=kid).first()
    if entry is None:
        entry = m.PersonalEntry(user_id=user.uid, knowledge_id=kid); db.add(entry)
    entry.category_id = payload.personal_category_id
    db.commit()
    return {'message': '已整理到个人门类'}


@router.delete('/knowledge/{kid}/bookmark')
def unbookmark(kid: int, db: Session = Depends(get_db), user=Depends(security.get_current_user)):
    item = db.get(m.Knowledge, kid)
    if item and item.created_by == user.uid:
        raise HTTPException(409, '自己的知识请使用移动门类或删除')
    db.query(m.PersonalEntry).filter_by(user_id=user.uid, knowledge_id=kid).delete()
    db.commit(); return {'message': '已取消收藏'}


@router.get('/unavailable-bookmarks')
def unavailable_bookmarks(db: Session = Depends(get_db), user=Depends(security.get_current_user)):
    ids = {k.kid for k in svc.accessible(db, user)}
    entries = db.query(m.PersonalEntry).filter_by(user_id=user.uid).all()
    return {'items': [dict(kid=e.knowledge_id, personal_category_id=e.category_id,
        title='原文已不可用') for e in entries if e.knowledge_id not in ids]}


@router.get('/links')
def links(db: Session = Depends(get_db), user=Depends(security.get_current_user)):
    allowed = {k.kid: k for k in svc.accessible(db, user)}
    records = db.query(m.PersonalLink).filter_by(user_id=user.uid).all()
    return {'items': [dict(id=r.id, source_id=r.source_id, target_id=r.target_id,
        source_title=allowed[r.source_id].title, target_title=allowed[r.target_id].title, relation=r.relation)
        for r in records if r.source_id in allowed and r.target_id in allowed]}


@router.post('/links', status_code=201)
def add_link(payload: s.LinkInput, db: Session = Depends(get_db), user=Depends(security.get_current_user)):
    if payload.source_id == payload.target_id: raise HTTPException(422, '不能关联自身')
    for kid in [payload.source_id, payload.target_id]: svc.get_item(db, user, kid)
    relation = db.query(m.PersonalLink).filter_by(user_id=user.uid, source_id=payload.source_id, target_id=payload.target_id).first()
    if not relation:
        relation = m.PersonalLink(user_id=user.uid, **payload.model_dump()); db.add(relation)
    else: relation.relation = payload.relation
    db.commit(); return dict(id=relation.id)


@router.delete('/links/{lid}')
def delete_link(lid: int, db: Session = Depends(get_db), user=Depends(security.get_current_user)):
    count = db.query(m.PersonalLink).filter_by(id=lid, user_id=user.uid).delete()
    if not count: raise HTTPException(404, '关联不存在')
    db.commit(); return {'message': '关联已删除'}


@router.get('/appearance')
def get_appearance(db: Session = Depends(get_db), user=Depends(security.get_current_user)):
    row = db.get(m.Appearance, user.uid)
    return s.AppearanceInput.model_validate({k: getattr(row, k) for k in s.AppearanceInput.model_fields} if row else {}).model_dump()


@router.put('/appearance')
def appearance(payload: s.AppearanceInput, db: Session = Depends(get_db), user=Depends(security.get_current_user)):
    row = db.get(m.Appearance, user.uid)
    if row is None: row = m.Appearance(user_id=user.uid); db.add(row)
    for key, value in payload.model_dump().items(): setattr(row, key, value)
    db.commit(); return payload.model_dump()


@router.get('/admin/categories')
def admin_categories(db: Session = Depends(get_db), user=Depends(security.get_current_user)):
    # 名称列表对普通用户也可用，包含未放到首页的公共门类。
    records = db.query(m.Category).order_by(m.Category.cid).all()
    items = []
    for i, c in enumerate(records):
        setting = db.get(m.PlanetSetting, c.cid)
        items.append(dict(id=c.cid, name=c.name, description=c.description or '',
            count=svc.scoped(db, user, 'public', c.cid).count(),
            visible=setting.visible if setting else True,
            style=setting.style if setting else svc.STYLES[i % len(svc.STYLES)],
            position=setting.position if setting else i))
    return {'items': items}


@router.put('/admin/categories/{cid}/planet')
def planet(cid: int, payload: s.PlanetInput, db: Session = Depends(get_db), admin=Depends(security.require_admin)):
    if not db.get(m.Category, cid): raise HTTPException(404, '公共门类不存在')
    row = db.get(m.PlanetSetting, cid)
    if row is None: row = m.PlanetSetting(category_id=cid); db.add(row)
    for key, value in payload.model_dump().items(): setattr(row, key, value)
    db.add(m.SpaceEvent(user_id=admin.uid, action='行星展示设置', detail=json.dumps(dict(category_id=cid, **payload.model_dump()), ensure_ascii=False)))
    db.commit(); return payload.model_dump()


@router.put('/admin/planets')
def batch_planets(payload: s.PlanetBatchInput, db: Session = Depends(get_db), admin=Depends(security.require_admin)):
    cats = db.query(m.Category).order_by(m.Category.cid).all()
    for i, cat in enumerate(cats):
        row = db.get(m.PlanetSetting, cat.cid)
        if row is None:
            row = m.PlanetSetting(category_id=cat.cid, style=svc.STYLES[i % len(svc.STYLES)], position=i); db.add(row)
        row.visible = payload.visible
    db.add(m.SpaceEvent(user_id=admin.uid, action='批量行星展示', detail=json.dumps(payload.model_dump())))
    db.commit()
    return dict(count=len(cats), visible=payload.visible)


@router.get('/admin/events')
def events(db: Session = Depends(get_db), admin=Depends(security.require_admin)):
    rows = db.query(m.SpaceEvent, m.User.username).join(m.User, m.SpaceEvent.user_id == m.User.uid).order_by(m.SpaceEvent.id.desc()).limit(100).all()
    return {'items': [dict(id=e.id, actor=name, action=e.action, detail=e.detail,
        created_at=e.created_at.isoformat()) for e, name in rows]}


@router.get('/admin/knowledge')
def admin_knowledge(state: Literal['all', 'active', 'hidden'] = 'all', q: str = Query(default='', max_length=500),
    db: Session = Depends(get_db), admin=Depends(security.require_admin)):
    query = svc.base_query(db).filter(m.Knowledge.status == 'published')
    if state == 'active': query = query.filter(svc.public_filter())
    if state == 'hidden': query = query.filter(m.Moderation.hidden.is_(True))
    if q: query = query.filter(m.Knowledge.title.contains(q, autoescape=True))
    records = query.order_by(m.Knowledge.kid.desc()).all()
    return {'items': [svc.serialize(db, k, admin) for k in records]}


@router.post('/admin/knowledge/{kid}/moderation')
def moderate(kid: int, payload: s.ModerationInput, db: Session = Depends(get_db), admin=Depends(security.require_admin)):
    item = db.query(m.Knowledge).filter_by(kid=kid, status='published').first()
    if not item: raise HTTPException(404, '公有知识不存在')
    if payload.hidden and not payload.reason: raise HTTPException(422, '请填写下架原因')
    row = db.get(m.Moderation, kid)
    if row is None: row = m.Moderation(knowledge_id=kid); db.add(row)
    row.hidden, row.reason = payload.hidden, payload.reason
    svc.log(db, admin, item, 'update', event='moderation', **payload.model_dump())
    db.add(m.SpaceEvent(user_id=admin.uid, action='下架公有知识' if payload.hidden else '恢复公有知识',
        detail=json.dumps(dict(knowledge_id=kid, title=item.title, reason=payload.reason), ensure_ascii=False)))
    db.commit(); return {'message': '已下架' if row.hidden else '已恢复'}


@router.post('/knowledge/{kid}/reindex')
def reindex(kid: int, db: Session = Depends(get_db), user=Depends(security.get_current_user)):
    item = svc.get_item(db, user, kid)
    if item.created_by != user.uid and user.role != 'admin': raise HTTPException(403, '只能为自己的知识更新索引')
    return {'index_status': refresh_index(db, item)}
