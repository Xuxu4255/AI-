from fastapi import FastAPI,Depends
from app.database import get_db
from sqlalchemy.orm import Session
from app import models

app = FastAPI()


@app.post("/users")
def create_user(db: Session,input_username: str,input_password: str,input_email: str):
    new_user = models.User(
        user= input_username,
        password_hash = input_password,
        email=input_email
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user
    
#增加一个知识问答对
def create_category(db: Session,input_name: str, input_description: str=None):
    #新建一个Category实例，调用MOD层封装好的数据库类
    new_category = models.Category(
        name= input_name,
        description=input_description
    )
    #把这个对象存进会话里
    #但是没有真的写进数据库
    db.add(new_category)   #PS.有点像git提交

    #真正保存到数据库
    db.commit()

    #让对象更新成数据库里真实生成的数据，比如自增的Cid
    db.refresh(new_category)

    return new_category


#通过cid来查询Category表里面的一条
def get_category_by_id(db: Session,input_cid: int): 
    #在数据库会话中查询表Category,.filter加筛选条件，.first()只取第一条
    return db.query(models.Category).filter(models.Category.cid == input_cid).first()
    


def get_category_list(db: Session):
    return db.query(models.Category).all()


#models.XX代表了表名 告诉我们要修改哪一个表
def update_category(db: Session,input_cid: int,input_new_name: str,input_new_description: str):
    db.query(models.Category).name=input_new_name
    db.query(models.Category).description=input_new_description


def