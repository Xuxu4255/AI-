"""幂等导入中文数据结构知识，不覆盖已有条目。
用法：python scripts/seed_data_structures.py --admin admin --publish
默认为草稿；--publish 仅用于明确授权发布学习示例的场景。
"""
import argparse
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.database import SessionLocal
from app.models import User, Category, Knowledge, Document, UpdateLog
from scripts.data_structures_data import get_notes, CATEGORY_DESCRIPTIONS, SOURCE_NAME, SOURCE_URL


def seed(db, username, publish=False):
    admin = db.query(User).filter(User.username == username, User.role == 'admin').first()
    if admin is None:
        raise ValueError('指定账号不存在或不是管理员，不会导入数据。')
    notes = get_notes()
    assert len(notes) == 64
    assert len({(n['category'], n['title']) for n in notes}) == len(notes)
    created = skipped = categories_created = 0
    for name, description in CATEGORY_DESCRIPTIONS.items():
        category = db.query(Category).filter(Category.name == name).first()
        if category is None:
            category = Category(name=name, description=description)
            db.add(category)
            db.flush()
            categories_created += 1
        for note in (n for n in notes if n['category'] == name):
            assert 5 <= len(note['title']) <= 30
            assert len(note['keyword']) <= 255
            if db.query(Knowledge.kid).filter(Knowledge.category_id == category.cid, Knowledge.title == note['title']).first():
                skipped += 1
                continue
            item = Knowledge(title=note['title'], content=note['content'], summary=note['summary'],
                             keyword=note['keyword'], category_id=category.cid,
                             created_by=admin.uid, status='published' if publish else 'draft')
            db.add(item)
            db.flush()
            db.add(Document(knowledge_id=item.kid, source_type='online', source_name=SOURCE_NAME, source_url=SOURCE_URL))
            db.add(UpdateLog(knowledge_id=item.kid,user_id=admin.uid,action_type='create',new_value=json.dumps({'source':'data_structures_seed_v1','title':item.title},ensure_ascii=False)))
            if publish:
                db.add(UpdateLog(knowledge_id=item.kid,user_id=admin.uid,action_type='publish',new_value='published'))
            created += 1
    return {'categories_created':categories_created,'knowledge_created':created,'knowledge_skipped':skipped}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--admin', required=True)
    parser.add_argument('--publish', action='store_true')
    args = parser.parse_args()
    with SessionLocal() as db:
        try:
            result = seed(db, args.admin, args.publish)
            db.commit()
        except Exception:
            db.rollback()
            raise
    print(json.dumps(result, ensure_ascii=True))
