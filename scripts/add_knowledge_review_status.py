"""为已有 MySQL 数据库追加 rejected 状态，不改写任何知识记录。"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from sqlalchemy import inspect, text
from app.database import engine


def migrate():
    column = next(c for c in inspect(engine).get_columns('knowledge') if c['name'] == 'status')
    values = getattr(column['type'], 'enums', None)
    if values is None:
        print('Status is not an ENUM; no migration required.')
        return
    if 'rejected' in values:
        print('Rejected status already available.')
        return
    if values != ['draft', 'published', 'deleted']:
        raise RuntimeError('Unexpected status enum; left unchanged.')
    with engine.begin() as connection:
        connection.execute(text("ALTER TABLE knowledge MODIFY COLUMN status ENUM('draft','published','deleted','rejected') NOT NULL DEFAULT 'draft'"))
    print('Added rejected status; existing knowledge unchanged.')


if __name__ == '__main__':
    migrate()
