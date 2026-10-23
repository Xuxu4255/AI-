from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app import crud

app=FastAPI()

#1.用户认证功能
'''
注册接口
登录接口
密码校验
用户状态管理
'''
@app.post("/register")
#post 前端把用户名、密码、邮箱提交给后端,后端处理注册逻辑,保存到数据库
def register(input_username: str,input_password: 
             str,input_email: str,db: Session = Depends(get_db)):
    user = crud.create_user(db,input_username,input_password,input_email)

    if user is None:
        return {"message":"用户名和邮箱已存在"}

    return{
        "message": "注册成功",
        "user": {
            "uid": user.uid,
            "username": user.username,
            "email": user.email
        }
    }

@app.post("/login")
def login(input_username: str,input_password: str,
          db:Session = Depends(get_db)):
    
    if crud.login_user(db,input_username,input_password) is True:
        return {
            "message": "登陆成功！欢迎光临喵。喵喵喵"
        }
    else:
        return {
            "message": "登陆失败！喵"
        }

@app.get("/users/{input_username}")
#get 前端想拿某个用户的信息,直接访问这个地址,后端返回数据
#FastAPI 会把 URL 里的这个部分自动赋值给函数参数：
def get_user_by_username(input_username: str,db: Session=Depends(get_db)):
    user = crud.get_user_by_username(db, input_username)
    return {
    "uid": user.uid,
    "username": user.username,
    "email": user.email
    }




#2.知识库crud
'''
创建知识
查询知识列表
查询单条知识
修改知识
删除知识
'''



#3.问答模块
'''
创建问答对
查询问答对
审核问答对
处理问答反馈
'''

#4.反馈模块
'''
用户点赞/差评
错误反馈
建议反馈
反馈统计
'''

#5.设计与搜索
'''
tags
knowledge_tags
related_knowledge
knowledge_embedding
'''

#6.日志模块
'''
query_logs
update_logs
'''

#7.AI模块
