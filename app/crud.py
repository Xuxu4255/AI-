from sqlalchemy.orm import Session
from app import models


#哈希加密
def hash_password(password: str)->str:
    import hashlib
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def create_user(db: Session,input_username: str,input_password: str,input_email: str):
    new_user = models.User(
        username= input_username,
        password_hash = hash_password(input_password),
        email=input_email
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user



def get_user_by_username(db: Session,input_username: str):
    user=db.query(models.User).filter(models.User.username==input_username).first()
    return user



def login_user(db: Session,input_username: str,input_password: str):
    user=db.query(models.User).filter(models.User.username==input_username).first()

    if user==None:
        return False

    if user.hash_password==input_password:
        return True
    return False



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

    

#
def get_category_list(db: Session):
    return db.query(models.Category).all()



#models.XX代表了表名 告诉我们要修改哪一个表
def update_category(db: Session,input_cid: int,input_new_name: str,input_new_description: str):
    category = db.query(models.Category).filter(models.Category.cid == input_cid).first()

    if category is None:
        return None

    category.name = input_new_name
    category.desrciption = input_new_description

    db.commit()
    db.refresh(category)

    return category



def delete_category(db: Session,input_cid: int):
    category = db.query(models.Category).filter(models.Category.cid==input_cid).first()
    
    if category is None:
        return False

    db.delete(category)
    db.commit()
    return True



