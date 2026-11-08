"""升级前备份现有业务表，再创建知识星海附属表。不会公开旧草稿。"""
import sys
import gzip
import json
from datetime import datetime
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from sqlalchemy import inspect, text
from app.database import engine, Base
from app import models


def upgrade():
    folder = Path(__file__).resolve().parent.parent / 'data' / 'backups'
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / ('before-star-sea-' + datetime.now().strftime('%Y%m%d-%H%M%S') + '.json.gz')
    data = {}
    with engine.connect() as connection:
        for table in inspect(engine).get_table_names():
            data[table] = [dict(row) for row in connection.execute(text('SELECT * FROM `' + table.replace('`', '``') + '`')).mappings()]
    with gzip.open(path, 'wt', encoding='utf-8') as file:
        json.dump(data, file, ensure_ascii=False, default=str)
    Base.metadata.create_all(engine)
    print('Backup saved:', path)
    print('Original knowledge records:', len(data.get('knowledge', [])))
    print('Additional tables ready. Existing publication status preserved.')


if __name__ == '__main__': upgrade()
