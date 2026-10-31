"""本机管理命令：python scripts/make_admin.py 用户名。"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.database import SessionLocal
from app.models import User

if len(sys.argv) != 2:
    raise SystemExit('用法: python scripts/make_admin.py 用户名')
with SessionLocal() as db:
    user = db.query(User).filter(User.username == sys.argv[1]).first()
    if user is None:
        raise SystemExit('账号不存在，请先注册。')
    user.role = 'admin'
    db.commit()
    print('已将指定账号设置为管理员。')
