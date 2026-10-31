"""创建搜索来源快照表，不修改或删除已有业务数据。"""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from app.database import engine
from app.models import SearchContext
SearchContext.__table__.create(bind=engine,checkfirst=True)
print('Search context table is ready.')
