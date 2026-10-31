"""服务端会话：Cookie 只保存随机令牌，数据库保存令牌的哈希。"""
import hashlib
import secrets
from datetime import datetime, timedelta

from fastapi import Cookie, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, UserSession

COOKIE_NAME = "muzhi_session"
SESSION_SECONDS = 8 * 60 * 60


def token_hash(token):
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_session(db, user):
    token = secrets.token_urlsafe(32)
    session = UserSession(user_id=user.uid, token_hash=token_hash(token),
                          expires_at=datetime.utcnow() + timedelta(seconds=SESSION_SECONDS))
    db.add(session)
    db.commit()
    return token


def get_current_user(muzhi_session: str = Cookie(default=None), db: Session = Depends(get_db)):
    if not muzhi_session or len(muzhi_session) > 128:
        raise HTTPException(status_code=401, detail="请先登录")
    session = db.query(UserSession).filter(UserSession.token_hash == token_hash(muzhi_session),
                                           UserSession.expires_at > datetime.utcnow()).first()
    user = db.query(User).filter(User.uid == session.user_id).first() if session else None
    if user is None:
        raise HTTPException(status_code=401, detail="登录已过期，请重新登录")
    return user


def require_admin(user: User = Depends(get_current_user)):
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="需要管理员权限")
    return user


def check_origin(request: Request):
    """拒绝浏览器从其他网站发起的修改请求。"""
    if request.method not in ("GET", "HEAD", "OPTIONS"):
        origin = request.headers.get("origin")
        if origin and origin.rstrip("/") != str(request.base_url).rstrip("/"):
            raise HTTPException(status_code=403, detail="不允许跨站请求")
