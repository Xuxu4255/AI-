import unittest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from app.database import Base
from app.models import User, Category, Knowledge, Document, UpdateLog
from scripts.seed_data_structures import seed

class SeedTests(unittest.TestCase):
    def setUp(self):
        self.engine=create_engine('sqlite://')
        @event.listens_for(self.engine,'connect')
        def fk(connection, record): connection.execute('PRAGMA foreign_keys=ON')
        Base.metadata.create_all(self.engine)
        self.db=sessionmaker(bind=self.engine)()
        self.db.add(User(username='admin',role='admin',email='admin@example.com',password_hash='test'))
        self.db.commit()
    def tearDown(self):
        self.db.close();self.engine.dispose()
    def test_idempotent_and_preserves_edits(self):
        first=seed(self.db,'admin',True);self.db.commit()
        self.assertEqual(first['knowledge_created'],64)
        self.assertEqual(self.db.query(Category).count(),8)
        item=self.db.query(Knowledge).first();item.content='custom edit';self.db.commit()
        second=seed(self.db,'admin',True);self.db.commit()
        self.assertEqual(second['knowledge_created'],0)
        self.assertEqual(second['knowledge_skipped'],64)
        self.assertEqual(self.db.query(Knowledge).count(),64)
        self.assertEqual(self.db.query(Knowledge).filter(Knowledge.status=='published').count(),64)
        self.assertEqual(self.db.query(Document).count(),64)
        self.assertEqual(self.db.query(UpdateLog).count(),128)
        self.assertEqual(self.db.query(Knowledge).first().content,'custom edit')
    def test_requires_admin(self):
        with self.assertRaises(ValueError):seed(self.db,'missing',True)
        self.assertEqual(self.db.query(Knowledge).count(),0)
    def test_default_draft(self):
        seed(self.db,'admin');self.db.commit()
        self.assertEqual(self.db.query(Knowledge).filter(Knowledge.status=='draft').count(),64)

if __name__=='__main__':unittest.main()
