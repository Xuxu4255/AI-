"""公私有访问范围的唯一入口。先限制可访问集合，再做计数与搜索。"""
import json
from sqlalchemy import and_, or_
from fastapi import HTTPException
from app import models as m

STYLES = ['jupiter', 'saturn', 'neptune', 'violet', 'earth']


def base_query(db):
    return db.query(m.Knowledge).outerjoin(m.Moderation,
        m.Moderation.knowledge_id == m.Knowledge.kid)


def public_filter():
    return and_(m.Knowledge.status == 'published',
                or_(m.Moderation.knowledge_id.is_(None), m.Moderation.hidden.is_(False)))


def accessible(db, user):
    return base_query(db).filter(m.Knowledge.status != 'deleted', or_(
        m.Knowledge.created_by == user.uid, public_filter()))


def scoped(db, user, space='public', category_id=None):
    if space == 'public':
        q = base_query(db).filter(public_filter())
        if category_id is not None:
            q = q.filter(m.Knowledge.category_id == category_id)
        return q
    q = accessible(db, user)
    entry = db.query(m.PersonalEntry.id).filter(m.PersonalEntry.user_id == user.uid,
        m.PersonalEntry.knowledge_id == m.Knowledge.kid)
    if category_id is not None:
        own_category(db, user, category_id)
        entry = entry.filter(m.PersonalEntry.category_id == category_id)
        return q.filter(entry.exists())
    return q.filter(or_(m.Knowledge.created_by == user.uid, entry.exists()))


def own_category(db, user, category_id):
    cat = db.query(m.PersonalCategory).filter_by(id=category_id, user_id=user.uid).first()
    if not cat:
        raise HTTPException(404, '个人门类不存在')
    return cat


def get_item(db, user, kid, owner=False):
    q = accessible(db, user).filter(m.Knowledge.kid == kid)
    if owner:
        q = q.filter(m.Knowledge.created_by == user.uid).with_for_update()
    item = q.first()
    if item is None:
        raise HTTPException(404, '知识不存在或不可访问')
    return item


def serialize(db, item, user, detail=False):
    entry = db.query(m.PersonalEntry).filter_by(user_id=user.uid, knowledge_id=item.kid).first()
    moderation = db.get(m.Moderation, item.kid)
    data = dict(kid=item.kid, title=item.title, summary=item.summary or item.content[:150],
        category_id=item.category_id, created_by=item.created_by,
        author=item.creator.username, owned=item.created_by == user.uid,
        visibility='public' if item.status == 'published' else 'private',
        hidden=bool(moderation and moderation.hidden),
        moderation_reason=moderation.reason if moderation and item.created_by == user.uid else '',
        personal_category_id=entry.category_id if entry else None,
        bookmarked=bool(entry and item.created_by != user.uid),
        updated_at=item.updated_at.isoformat() if item.updated_at else None)
    if detail:
        data.update(content=item.content, keyword=item.keyword or '',
            sources=[dict(source_name=d.source_name, source_url=d.source_url,
                          source_type=d.source_type) for d in item.documents])
    return data


def log(db, user, item, action, **fields):
    db.add(m.UpdateLog(knowledge_id=item.kid, user_id=user.uid, action_type=action,
        new_value=json.dumps(fields, ensure_ascii=False)))


def bootstrap_personal(db, user):
    """仅把自己的旧知识归类；不更改任何旧知识的公开状态。"""
    own = db.query(m.Knowledge).filter(m.Knowledge.created_by == user.uid,
        m.Knowledge.status != 'deleted', ~db.query(m.PersonalEntry.id).filter(
            m.PersonalEntry.user_id == user.uid,
            m.PersonalEntry.knowledge_id == m.Knowledge.kid).exists()).all()
    categories = {c.name: c for c in db.query(m.PersonalCategory).filter_by(user_id=user.uid)}
    for item in own:
        name = item.category.name
        if name not in categories:
            cat = m.PersonalCategory(user_id=user.uid, name=name)
            db.add(cat); db.flush(); categories[name] = cat
        db.add(m.PersonalEntry(user_id=user.uid, category_id=categories[name].id, knowledge_id=item.kid))
    if own:
        db.commit()
