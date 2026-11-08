"""Transactional replacement of public knowledge with prepared study notes.

Preview: python scripts/import_runoob_notes.py
Apply:   python scripts/import_runoob_notes.py --apply
Index:   python scripts/import_runoob_notes.py --reindex

Backups contain knowledge tables only, never user passwords/session tokens.
"""
import argparse
import hashlib
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from sqlalchemy import select

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app import models as m
from app.database import SessionLocal
from app.services.indexing import refresh_index

SOURCE = 'runoob_study_note'
COURSES = ['Python', 'C++', 'Java', 'FastAPI', 'MySQL', 'Docker']
TABLES = [m.Category, m.Knowledge, m.Document, m.PersonalCategory, m.PersonalEntry,
          m.PlanetSetting, m.Moderation, m.KnowledgeEmbedding, m.KnowledgeChunk,
          m.PersonalLink, m.RelatedKnowledge, m.QaPair, m.Feedback, m.KnowledgeTag, m.Tag, m.UpdateLog]


def read_notes():
    raw = (ROOT / 'data/runoob/notes.json').read_bytes()
    payload = json.loads(raw)
    if payload.get('kind') != 'original_study_notes_with_runoob_references':
        raise ValueError('Unexpected dataset kind')
    items = payload['items']
    if Counter(x['category'] for x in items) != Counter({c: 16 for c in COURSES}):
        raise ValueError('Expected 16 notes in each of the six categories')
    if len({x['key'] for x in items}) != 96: raise ValueError('Duplicate import keys')
    verified = json.loads((ROOT / 'data/runoob/verified_links.json').read_text(encoding='utf-8'))
    for item in items:
        if item['source_url'] not in verified or verified[item['source_url']]['http_status'] != 200:
            raise ValueError('Source not verified: ' + item['source_url'])
        if not item['source_url'].startswith('https://www.runoob.com/'):
            raise ValueError('Unexpected source host')
        if not 1 <= len(item['content']) <= 10000: raise ValueError('Unexpected content length')
    return items, hashlib.sha256(raw).hexdigest()


def backup(db):
    folder = ROOT / 'data/backups'; folder.mkdir(parents=True, exist_ok=True)
    path = folder / ('before_runoob_' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '.json')
    data = {'created_at': datetime.now(timezone.utc).isoformat(), 'scope': 'knowledge_tables', 'tables': {}}
    for model in TABLES:
        data['tables'][model.__tablename__] = [dict(row) for row in db.execute(select(model.__table__)).mappings()]
    # Exclusive creation prevents accidentally overwriting an earlier snapshot.
    with path.open('x', encoding='utf-8') as output:
        json.dump(data, output, ensure_ascii=False, default=str)
    parsed = json.loads(path.read_text(encoding='utf-8'))
    if len(parsed['tables']['knowledge']) != db.query(m.Knowledge).count():
        raise ValueError('Backup verification failed')
    return path


def apply(items, digest):
    with SessionLocal() as db:
        try:
            admin = db.query(m.User).filter_by(username='admin', role='admin').one()
            # Lock existing knowledge for the duration of the snapshot/replacement.
            db.query(m.Knowledge).with_for_update().all()
            path = backup(db)
            private_before = {k.kid: (k.status, k.content) for k in db.query(m.Knowledge).filter(m.Knowledge.status == 'draft')}
            existing = {d.file_name: d for d in db.query(m.Document).filter_by(source_type=SOURCE)}
            retained = {existing[x['key']].knowledge_id for x in items if x['key'] in existing}
            old = db.query(m.Knowledge).filter(m.Knowledge.status == 'published')
            if retained: old = old.filter(~m.Knowledge.kid.in_(retained))
            old_ids = [k.kid for k in old]
            # Existing rows/links/vectors remain recoverable. All search scopes filter this state.
            if old_ids:
                db.query(m.Knowledge).filter(m.Knowledge.kid.in_(old_ids)).update({'status': 'deleted'}, synchronize_session=False)
            categories = {}; personal = {}
            for index, name in enumerate(COURSES):
                cat = db.query(m.Category).filter_by(name=name).first()
                if cat is None:
                    cat = m.Category(name=name, description='编程学习笔记与菜鸟教程原文入口'); db.add(cat); db.flush()
                categories[name] = cat
                setting = db.get(m.PlanetSetting, cat.cid)
                if setting is None: setting = m.PlanetSetting(category_id=cat.cid); db.add(setting)
                setting.visible = True; setting.position = index
                own_cat = db.query(m.PersonalCategory).filter_by(user_id=admin.uid, name=name).first()
                if own_cat is None:
                    own_cat = m.PersonalCategory(user_id=admin.uid, name=name, color='#96CBAF'); db.add(own_cat); db.flush()
                personal[name] = own_cat
            inserted = updated = 0
            for row in items:
                doc = existing.get(row['key'])
                if doc:
                    item = db.get(m.Knowledge, doc.knowledge_id)
                    if item.created_by != admin.uid: raise ValueError('Import ownership mismatch')
                    updated += 1
                else:
                    item = m.Knowledge(created_by=admin.uid); db.add(item); inserted += 1
                for field in ['title', 'content', 'summary', 'keyword']: setattr(item, field, row[field])
                item.category_id = categories[row['category']].cid; item.status = 'published'
                db.flush()
                if doc is None:
                    doc = m.Document(knowledge_id=item.kid, source_type=SOURCE, file_name=row['key']); db.add(doc)
                doc.source_name = row['source_name']; doc.source_url = row['source_url']
                entry = db.query(m.PersonalEntry).filter_by(user_id=admin.uid, knowledge_id=item.kid).first()
                if entry is None:
                    entry = m.PersonalEntry(user_id=admin.uid, knowledge_id=item.kid); db.add(entry)
                entry.category_id = personal[row['category']].id
                moderation = db.get(m.Moderation, item.kid)
                if moderation: moderation.hidden = False
            db.flush()
            private_after = {k.kid: (k.status, k.content) for k in db.query(m.Knowledge).filter(m.Knowledge.status == 'draft')}
            if private_before != private_after: raise ValueError('Private drafts unexpectedly changed')
            db.add(m.SpaceEvent(user_id=admin.uid, action='替换公共知识库', detail=json.dumps({
                'source': SOURCE, 'manifest_sha256': digest, 'backup': str(path.relative_to(ROOT)),
                'archived_ids': old_ids, 'created': inserted, 'updated': updated}, ensure_ascii=False)))
            db.commit()
            return dict(created=inserted, updated=updated, archived=len(old_ids), private_drafts_preserved=len(private_before), backup=str(path))
        except Exception:
            db.rollback(); raise


def reindex():
    from app.services.embedding import get_local_embeddings
    get_local_embeddings(['索引服务可用性检查'], 'document')
    outcomes = Counter()
    with SessionLocal() as db:
        ids = [row[0] for row in db.query(m.Knowledge.kid).join(m.Document).filter(
            m.Document.source_type == SOURCE, m.Knowledge.status == 'published').distinct()]
        for number, kid in enumerate(ids, 1):
            result = refresh_index(db, db.get(m.Knowledge, kid)); outcomes[result] += 1
            if number % 8 == 0: print('Indexed', number, '/', len(ids), flush=True)
    print(json.dumps({'index': dict(outcomes)}, ensure_ascii=False), flush=True)
    if outcomes['pending']: raise RuntimeError('Some indexes failed; rerun --reindex')


def restore_public(snapshot):
    """Restore only the visibility statuses changed by this replacement batch."""
    path = Path(snapshot).resolve(); allowed = (ROOT / 'data/backups').resolve()
    if allowed not in path.parents: raise ValueError('Snapshot must be in data/backups')
    snapshot = json.loads(path.read_text(encoding='utf-8'))
    old = {row['kid']: row for row in snapshot['tables']['knowledge']}
    with SessionLocal() as db:
        for item in db.query(m.Knowledge):
            if item.kid in old and old[item.kid]['status'] == 'published' and item.status == 'deleted':
                item.status = 'published'
        imported = db.query(m.Knowledge).join(m.Document).filter(m.Document.source_type == SOURCE).all()
        for item in imported:
            if item.kid not in old: item.status = 'deleted'
        db.commit()
    print('Restored publication statuses from', path)


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--apply', action='store_true'); group.add_argument('--reindex', action='store_true')
    group.add_argument('--restore-public', metavar='SNAPSHOT')
    args = parser.parse_args()
    if args.reindex: reindex(); return
    if args.restore_public: restore_public(args.restore_public); return
    items, digest = read_notes()
    if args.apply: print(json.dumps(apply(items, digest), ensure_ascii=False), flush=True)
    else:
        with SessionLocal() as db:
            print(json.dumps({'dry_run': True, 'notes': len(items), 'categories': dict(Counter(x['category'] for x in items)),
                'currently_published': db.query(m.Knowledge).filter_by(status='published').count()}, ensure_ascii=False))


if __name__ == '__main__': main()
