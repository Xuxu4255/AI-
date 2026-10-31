"""学生投稿：所有权、待审核状态和正文修改在同一事务中处理。"""
import json
from app import models

SOURCE_TYPE = 'student_submission'


def own_query(db, user_id):
    return db.query(models.Knowledge).filter(
        models.Knowledge.created_by == user_id,
        models.Knowledge.status.in_(['draft', 'published', 'rejected']),
        db.query(models.Document.did).filter(
            models.Document.knowledge_id == models.Knowledge.kid,
            models.Document.source_type == SOURCE_TYPE).exists())


def save(db, user, payload, knowledge_id=None):
    item = None
    if knowledge_id is not None:
        item = own_query(db, user.uid).filter(models.Knowledge.kid == knowledge_id).with_for_update().first()
        if item is None:
            return None
        if item.status not in ('draft', 'rejected'):
            raise ValueError('已发布内容由管理员维护，不能直接修改；请联系管理员。')
    if db.query(models.Category.cid).filter(models.Category.cid == payload.category_id).first() is None:
        raise LookupError('分类不存在，请刷新后重新选择')
    fields = dict(title=payload.title, content=payload.content, summary=payload.summary,
                  category_id=payload.category_id, keyword=payload.keyword or payload.title)
    old_status = item.status if item is not None else None
    old_value = json.dumps({'status': old_status, 'title': item.title, 'content': item.content,
                            'summary': item.summary, 'category_id': item.category_id,
                            'keyword': item.keyword}, ensure_ascii=False) if item is not None else None
    if item is None:
        item = models.Knowledge(**fields, created_by=user.uid, status='draft')
        db.add(item)
        db.flush()
        document = models.Document(knowledge_id=item.kid, source_type=SOURCE_TYPE)
        db.add(document)
    else:
        for name, value in fields.items():
            setattr(item, name, value)
        document = db.query(models.Document).filter(models.Document.knowledge_id == item.kid,
                                                    models.Document.source_type == SOURCE_TYPE).first()
    document.source_name = payload.source_name or '用户投稿'
    document.source_url = payload.source_url
    item.status = 'draft'
    db.add(models.UpdateLog(knowledge_id=item.kid, user_id=user.uid,
        action_type='create' if knowledge_id is None else 'update', old_value=old_value,
        new_value=json.dumps({'event': 'knowledge_review', 'action': 'submit' if knowledge_id is None else 'resubmit',
                              'status': 'draft', 'reason': '', 'source_url': payload.source_url}, ensure_ascii=False)))
    db.commit()
    db.refresh(item)
    return item
