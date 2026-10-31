"""离线检验官方正文摘录、导入事务和审核隔离，不访问生产库和外部模型。"""
import copy
import json
import unittest
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from app.database import Base
from app.models import User, Category, Knowledge, Document, UpdateLog
from app.services.indexing import build_embedding_text
from scripts.import_nbu_official import (
    DATA, SOURCE_TYPE, import_corpus, validate_corpus, official_url, read_source,
)


class NbuCorpusTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.corpus = json.loads((DATA / 'corpus.json').read_text(encoding='utf-8'))

    def test_sources_are_complete_official_snapshots_in_all_six_categories(self):
        validate_corpus(self.corpus)
        self.assertEqual(len(self.corpus['sources']), 20)
        self.assertEqual(len({s['category'] for s in self.corpus['sources']}), 6)
        for source in self.corpus['sources']:
            captured = read_source(DATA / 'raw' / (source['id'] + '.json'))
            self.assertEqual(source, captured)
            self.assertTrue(official_url(source['url']))
            notes = [n for n in self.corpus['notes'] if n['source_id'] == source['id']]
            covered = set()
            for note in notes:
                covered.update(range(note['body_start'], note['body_end']))
            self.assertEqual(len(covered), len(source['body']))

    def test_wrong_excerpt_missing_piece_and_duplicate_are_rejected(self):
        for operation in ('excerpt', 'missing', 'duplicate'):
            corpus = copy.deepcopy(self.corpus)
            if operation == 'excerpt':
                corpus['notes'][0]['excerpt'] = '不存在于原文的规则'
            elif operation == 'missing':
                corpus['notes'].pop()
            else:
                corpus['notes'].append(corpus['notes'][0])
            with self.assertRaises(ValueError):
                validate_corpus(corpus)

    def test_context_and_sources_are_preserved_without_navigation(self):
        for note in self.corpus['notes']:
            text = build_embedding_text(type('Item', (), note))
            self.assertIn('适用范围：', text)
            self.assertIn('时效说明：', text)
            self.assertIn('发布日期：', text)
            self.assertLessEqual(len(text), 475)
            self.assertNotIn('†', text)
            self.assertIn(note['source_url'], note['content'])
            self.assertNotIn('管理登录', note['content'])

    def test_spoofed_domains_are_not_official(self):
        for url in ('https://nbu.edu.cn.evil.test/a', 'https://bnu.edu.cn/a',
                    'https://nbu.edu.cn@evil.test/a', 'file:///nbu.edu.cn'):
            self.assertFalse(official_url(url))


class NbuImportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.corpus = json.loads((DATA / 'corpus.json').read_text(encoding='utf-8'))

    def setUp(self):
        self.engine = create_engine('sqlite://')
        @event.listens_for(self.engine, 'connect')
        def enable_fk(connection, record):
            connection.execute('PRAGMA foreign_keys=ON')
        Base.metadata.create_all(self.engine)
        self.db = sessionmaker(bind=self.engine)()
        self.admin = User(username='admin', role='admin', email='admin@example.test', password_hash='test')
        self.db.add_all([self.admin, User(username='student', role='user',
                         email='student@example.test', password_hash='test')])
        self.db.flush()
        category = Category(name='原有分类')
        self.db.add(category)
        self.db.flush()
        self.existing = Knowledge(title='原有已发布知识', content='不能覆盖', category_id=category.cid,
                                  created_by=self.admin.uid, status='published')
        self.db.add(self.existing)
        self.db.commit()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def test_idempotent_drafts_keep_original_data_and_admin_edits(self):
        result = import_corpus(self.db, 'admin', self.corpus)
        self.db.commit()
        total = len(self.corpus['notes'])
        self.assertEqual(result['created'], total)
        self.assertEqual(result['categories_created'], 6)
        self.assertEqual(self.db.query(Knowledge).filter(Knowledge.status == 'draft').count(), total)
        self.assertEqual(self.db.query(Knowledge).filter(Knowledge.status == 'published').count(), 1)
        self.assertEqual(self.existing.content, '不能覆盖')
        first = self.db.query(Knowledge).filter(Knowledge.kid == result['knowledge_ids'][0]).one()
        first.content = '管理员核对后改过的内容'
        first.status = 'published'
        self.db.commit()
        repeat = import_corpus(self.db, 'admin', self.corpus)
        self.db.commit()
        self.assertEqual(repeat['created'], 0)
        self.assertEqual(repeat['skipped'], total)
        self.assertEqual(first.content, '管理员核对后改过的内容')
        self.assertEqual(first.status, 'published')
        self.assertEqual(self.db.query(Document).filter(Document.source_type == SOURCE_TYPE).count(), total)
        self.assertEqual(self.db.query(UpdateLog).count(), total)

    def test_dry_run_rolls_back_every_insert(self):
        import_corpus(self.db, 'admin', self.corpus)
        self.db.rollback()
        self.assertEqual(self.db.query(Knowledge).count(), 1)
        self.assertEqual(self.db.query(Category).count(), 1)
        self.assertEqual(self.db.query(Document).count(), 0)
        self.assertEqual(self.db.query(UpdateLog).count(), 0)

    def test_student_and_unknown_importer_are_rejected(self):
        for name in ('student', 'unknown'):
            with self.assertRaises(ValueError):
                import_corpus(self.db, name, self.corpus)
        self.assertEqual(self.db.query(Knowledge).count(), 1)


if __name__ == '__main__':
    unittest.main()
