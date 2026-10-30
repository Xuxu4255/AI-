from fastapi import APIRouter, Depends, HTTPException, status as http_status
from sqlalchemy.orm import Session

from app import crud, schemas
from app.database import get_db

router = APIRouter()


#1.用户认证功能
'''
注册接口
登录接口
密码校验
用户状态管理
'''
@router.post("/register", status_code=http_status.HTTP_201_CREATED)
#post 前端把用户名、密码、邮箱提交给后端,后端处理注册逻辑,保存到数据库
def register(payload: schemas.UserRegister, db: Session = Depends(get_db)):
    user = crud.create_user(db, payload.username, payload.password, payload.email)

    if user is None:
        raise HTTPException(
            status_code=http_status.HTTP_409_CONFLICT,
            detail="用户名或邮箱已存在",
        )

    return{
        "message": "注册成功",
        "user": {
            "uid": user.uid,
            "username": user.username,
            "email": user.email
        }
    }

@router.post("/login")
def login(payload: schemas.UserLogin, db: Session = Depends(get_db)):
    if not crud.login_user(db, payload.username, payload.password):
        raise HTTPException(
            status_code=http_status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
        )

    return {
        "message": "登陆成功！欢迎光临喵。喵喵喵"
    }

@router.get("/users/{input_username}")
#get 前端想拿某个用户的信息,直接访问这个地址,后端返回数据
#FastAPI 会把 URL 里的这个部分自动赋值给函数参数：
def get_user_by_username(input_username: str,db: Session=Depends(get_db)):
    user = crud.get_user_by_username(db, input_username)
    if user is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="用户不存在",
        )
    return {
    "uid": user.uid,
    "username": user.username,
    "email": user.email
    }
