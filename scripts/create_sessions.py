"""仅创建会话表，不删除已有数据库或其他表。"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.database import engine
from app.models import UserSession

UserSession.__table__.create(bind=engine, checkfirst=True)
print('user_sessions 表已就绪。')
