##database.py 是干嘛的
#它是“数据库连接层”和“会话管理层”。

#也就是说，它负责：

#连接 MySQL
#创建数据库引擎
#生成数据库会话
#给其他模块提供 db 对象
#让后面的 CRUD / 模型 能真正访问数据库
from sqlalchemy import sessionmaker
from sqlalchemy import create_engine
from app.config import DATABASE_URL

engine = create_engine(DATABASE_URL)
#生成一个数据库连接引擎

session = sessionmaker(bind = engine)

def get_db():
    db = session()
    try:
        yield db
    finally:
        db.close()
    #将数据库生命周期分为开始和结束
    