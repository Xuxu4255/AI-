"""将公开官网正文快照整理为知识并幂等导入；默认草稿，不调用付费模型。

prepare: python scripts/import_nbu_official.py prepare
preview: python scripts/import_nbu_official.py import --admin admin --dry-run
import:  python scripts/import_nbu_official.py import --admin admin

raw 是网页阅读器获取的可见正文快照，不是原始 HTML 或已下载的附件。
只读取逐行完整、经人工选定的正文范围；验证码、空页面不入库。
"""
import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
DATA = ROOT / 'data' / 'nbu_official'
SOURCE_TYPE = 'nbu_official'
BATCH = 'nbu_official_2026-10-31_v1'
COLLECTED_ON = '2026-10-31'

# id: (标题行, 正文起止行, 网页发布日期)。范围避开导航栏和重复的移动版正文。
PROFILES = {
    'competition_challenge_2026': (80, 84, 211, '2026-09-12'),
    'competition_math_2026': (65, 71, 145, '2026-09-04'),
    'competition_bclass_2026': (30, 36, 68, '2026-03-18'),
    'competition_programming_2026': (30, 36, 106, '2026-04-27'),
    'competition_calculus_2026': (30, 36, 92, '2026-03-09'),
    'transfer_2026_spring': (31, 37, 83, '2026-05-18'),
    'transfer_2025_autumn': (30, 36, 92, '2025-11-24'),
    'transfer_innovation_2026': (65, 71, 150, '2026-10-26'),
    'recommend_business_2027': (69, 74, 213, '2026-06-05'),
    'recommend_joint_2027': (13, 19, 192, '2026-05-13'),
    'recommend_volunteer_2027': (33, 39, 126, '2026-08-19'),
    'scholar_undergraduate_2026': (14, 16, 43, '2026-09-29'),
    'scholar_graduate_2026': (87, 91, 164, '2026-09-15'),
    'scholar_ai_2026': (73, 77, 162, '2026-10-08'),
    'scholar_aid_medicine_2026': (106, 112, 239, '2026-10-14'),
    'employment_materials_2026': (69, 75, 82, '2025-09-25'),
    'employment_services': (70, 72, 82, None),
    'party_ai_2026': (73, 77, 137, '2026-08-31'),
    'party_law_graduates_2026': (33, 39, 115, '2026-04-01'),
    'party_law_freshmen_2026': (33, 39, 66, '2026-08-28'),
}


def official_url(url):
    parsed = urlsplit(url)
    return (parsed.scheme in ('http', 'https') and parsed.hostname is not None
            and (parsed.hostname == 'nbu.edu.cn' or parsed.hostname.endswith('.nbu.edu.cn'))
            and not parsed.username and not parsed.password)


def digest(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def clean_line(text):
    def link(match):
        parts = match.group(1).split('†')
        label = parts[0]
        if label == 'Image' or label.startswith('Image:'):
            return ''
        if len(parts) > 1:
            return label + '（https://' + parts[-1] + '）'
        return label
    text = re.sub(r'【\d+†([^】]*)】', link, text)
    text = re.sub(r'^\s*#+\s*', '', text)
    return text.replace('\xa0', ' ').replace('\ufeff', '').strip()


def read_source(path):
    capture = json.loads(path.read_text(encoding='utf-8'))
    source = dict(capture['source'])
    source_id = source['id']
    if source_id not in PROFILES:
        raise ValueError('未选用：正文未读取、仅图片，或尚未核对')
    if not official_url(source['url']):
        raise ValueError('来源不是宁波大学官方域名')
    raw = capture['reader_response']
    rows = {int(n): text for n, text in re.findall(r'^L(\d+):[ \t]?(.*)$', raw, re.M)}
    title_line, first, last, published = PROFILES[source_id]
    if any(n not in rows for n in range(first, last + 1)) or title_line not in rows:
        raise ValueError('正文行缺失，禁止把截断快照当完整正文入库')
    if published and date.fromisoformat(published) > date.fromisoformat(COLLECTED_ON):
        raise ValueError('发布日期晚于采集日期')
    source['title'] = clean_line(rows[title_line])
    source['published_on'] = published
    source['collected_on'] = COLLECTED_ON
    source['reader_line_range'] = [first, last]
    if source_id.startswith('transfer_202'):
        source['temporal'] += '；2026-10-26专项通知已引用宁大政〔2026〕75号，当前规则须另核新版'
    if source_id == 'competition_challenge_2026':
        source['temporal'] += '；页面更新日期2026-09-12，文末署2026-09-11'
    lines = [clean_line(rows[n]) for n in range(first, last + 1)]
    lines = [line for line in lines if line and line != '* * *']
    body = '\n'.join(lines)
    if len(body) < 40:
        raise ValueError('无足够可读正文')
    # 没有解析附件：这里只保存官网页面列出的附件名称和原页面入口。
    source['attachments'] = list(dict.fromkeys(
        re.sub(r'^[ *]+', '', line).replace('已下载次', '').strip(' 〖〗')
        for line in lines if ('附件' in line and re.search(r'\.(?:pdf|docx?|xlsx?|zip|rar)\b', line, re.I))
    ))
    source['attachment_status'] = 'not_parsed' if source['attachments'] else 'not_applicable'
    source['body'] = body
    source['body_sha256'] = digest(body)
    source['capture_sha256'] = digest(raw)
    source['capture_path'] = path.relative_to(ROOT).as_posix()
    source['text_path'] = 'data/nbu_official/text/' + source_id + '.txt'
    return source


def split_body(body, budget=220, overlap=40):
    """优先按句末或换行切分，并保留相邻上下文；不生成模型猜测的问答。"""
    if budget <= overlap:
        raise ValueError('分段长度必须大于重叠长度')
    start = 0
    while start < len(body):
        end = min(start + budget, len(body))
        if end < len(body):
            boundaries = [body.rfind(char, start + budget // 2, end)
                          for char in ('\n', '。', '；', '！', '？')]
            boundary = max(boundaries)
            if boundary >= 0:
                end = boundary + 1
        yield start, end, body[start:end]
        if end == len(body):
            break
        start = end - overlap


def make_notes(source):
    # 让日期、学院限制进入检索和模型上下文；链接和采集细节放在展示区。
    context = ('发布日期：' + (source['published_on'] or '官网未标注') + '\n'
               + '适用范围：' + source['scope'] + '\n'
               + '时效说明：' + source['temporal'] + '\n'
               + '原文分段，完整资格和办理要求须合并全文及附件核对。\n')
    budget = min(220, 475 - len(source['title']) - len(context) - 25)
    if budget < 100:
        raise ValueError('来源限制说明过长，需人工整理上下文')
    pieces = list(split_body(source['body'], budget))
    notes = []
    for index, (start, end, excerpt) in enumerate(pieces, 1):
        title = source['title'] + '【原文分段{}/{}】'.format(index, len(pieces))
        displayed = ('\n\n资料性质：宁波大学官方网页正文摘录，待管理员核对；不是学校官方问答。\n'
                     + '原文标题：' + source['title'] + '\n'
                     + '原文链接：' + source['url'] + '\n'
                     + '采集日期：' + COLLECTED_ON + '\n'
                     + '附件状态：附件正文未解析；标题不代表已读取其内容。\n'
                     + '正文快照：' + source['text_path'] + '\n'
                     + '完整正文SHA256：' + source['body_sha256'])
        notes.append({
            'source_id': source['id'], 'source_url': source['url'],
            'source_title': source['title'], 'category': source['category'],
            'title': title, 'content': context + '原文摘录：\n' + excerpt + displayed,
            'summary': (source['published_on'] or '日期未标注') + '；' + source['scope'] + '；' + source['temporal'],
            'keyword': source['keywords'], 'chunk_index': index, 'chunk_count': len(pieces),
            'body_start': start, 'body_end': end, 'excerpt': excerpt,
            'source_hash': source['body_sha256'],
            'file_name': '{}__{:03d}.txt'.format(source['id'], index),
            'file_path': source['text_path'],
        })
    return notes


def prepare(data_dir=DATA):
    sources, notes, skipped = [], [], []
    text_dir = data_dir / 'text'
    text_dir.mkdir(parents=True, exist_ok=True)
    for path in sorted((data_dir / 'raw').glob('*.json')):
        try:
            source = read_source(path)
            source_notes = make_notes(source)
        except (ValueError, KeyError) as error:
            skipped.append({'capture': path.name, 'reason': str(error)})
            continue
        archive = ('标题：' + source['title'] + '\n来源：' + source['url']
                   + '\n发布日期：' + (source['published_on'] or '未标注')
                   + '\n采集日期：' + COLLECTED_ON + '\n适用范围：' + source['scope']
                   + '\n时效说明：' + source['temporal']
                   + '\n附件未解析；以下为网页可见正文。\n\n' + source['body'])
        (text_dir / (source['id'] + '.txt')).write_text(archive, encoding='utf-8')
        sources.append(source)
        notes.extend(source_notes)
    payload = {'batch': BATCH, 'collected_on': COLLECTED_ON, 'sources': sources,
               'notes': notes, 'skipped': skipped}
    (data_dir / 'corpus.json').write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    return payload


def validate_corpus(corpus):
    sources = {s['id']: s for s in corpus['sources']}
    if len(sources) != len(corpus['sources']) or not sources:
        raise ValueError('来源为空或来源编号重复')
    seen = set()
    for source in sources.values():
        if not official_url(source['url']) or digest(source['body']) != source['body_sha256']:
            raise ValueError('来源地址或正文摘要校验失败')
    for note in corpus['notes']:
        source = sources[note['source_id']]
        identity = (note['source_url'], note['file_name'])
        if identity in seen or note['source_url'] != source['url']:
            raise ValueError('条目标识重复或来源不匹配')
        seen.add(identity)
        if source['body'][note['body_start']:note['body_end']] != note['excerpt']:
            raise ValueError('摘录与官网正文快照不一致')
        expected = make_notes(source)[note['chunk_index'] - 1]
        if note != expected:
            raise ValueError('知识条目与可复现的正文分段不一致')
    if len(corpus['notes']) != sum(len(make_notes(s)) for s in sources.values()):
        raise ValueError('正文分段缺失')


def import_corpus(db, username, corpus):
    from app.models import User, Category, Knowledge, Document, UpdateLog
    validate_corpus(corpus)
    admin = db.query(User).filter(User.username == username, User.role == 'admin').first()
    if admin is None:
        raise ValueError('导入账号不存在或不是管理员')
    result = {'batch': BATCH, 'source_count': len(corpus['sources']), 'created': 0,
              'skipped': 0, 'categories_created': 0, 'knowledge_ids': [], 'status': 'draft'}
    category_cache = {}
    for note in corpus['notes']:
        existing = db.query(Document.did).filter(Document.source_type == SOURCE_TYPE,
                     Document.source_url == note['source_url'], Document.file_name == note['file_name']).first()
        if existing:
            # 不覆盖管理员编辑、发布状态或原文；重新采集的新版本应先另行审核。
            result['skipped'] += 1
            continue
        name = note['category']
        if name not in category_cache:
            category = db.query(Category).filter(Category.name == name).first()
            if category is None:
                category = Category(name=name, description='宁波大学官网资料；保留来源、适用对象及时间范围。')
                db.add(category)
                db.flush()
                result['categories_created'] += 1
            category_cache[name] = category
        item = Knowledge(title=note['title'], content=note['content'], summary=note['summary'],
                         category_id=category_cache[name].cid, created_by=admin.uid,
                         keyword=note['keyword'], status='draft')
        db.add(item)
        db.flush()
        db.add(Document(knowledge_id=item.kid, source_type=SOURCE_TYPE,
                        source_name=note['source_title'], source_url=note['source_url'],
                        file_name=note['file_name'], file_path=note['file_path']))
        db.add(UpdateLog(knowledge_id=item.kid, user_id=admin.uid, action_type='create',
                         new_value=json.dumps({'batch': BATCH, 'source_id': note['source_id'],
                         'source_url': note['source_url'], 'source_hash': note['source_hash'],
                         'chunk': note['chunk_index'], 'status': 'draft'}, ensure_ascii=False)))
        result['knowledge_ids'].append(item.kid)
        result['created'] += 1
    db.flush()
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('prepare')
    importer = commands.add_parser('import')
    importer.add_argument('--admin', required=True)
    importer.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    if args.command == 'prepare':
        corpus = prepare()
        print(json.dumps({'sources': len(corpus['sources']), 'notes': len(corpus['notes']),
              'categories': dict(Counter(s['category'] for s in corpus['sources'])),
              'skipped': corpus['skipped']}, ensure_ascii=False, indent=2))
        return
    from app.database import SessionLocal
    corpus = json.loads((DATA / 'corpus.json').read_text(encoding='utf-8'))
    with SessionLocal() as db:
        try:
            result = import_corpus(db, args.admin, corpus)
            if args.dry_run:
                db.rollback()
                result['dry_run'] = True
            else:
                db.commit()
        except Exception:
            db.rollback()
            raise
    if not args.dry_run:
        report = DATA / ('import-report-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '.json')
        report.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({key: value for key, value in result.items() if key != 'knowledge_ids'},
                     ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
