##database.py 是干嘛的
#它是“数据库连接层”和“会话管理层”。

#也就是说，它负责：

#连接 MySQL
#创建数据库引擎
#生成数据库会话
#给其他模块提供 db 对象
#让后面的 CRUD / 模型 能真正访问数据库
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy import create_engine
from app.config import DATABASE_URL

Base = declarative_base()
#创建一个 SQLAlchemy 的“模型基类”，让后面的所有表模型都继承它。



engine = create_engine(DATABASE_URL)
#生成一个数据库连接引擎

SessionLocal = sessionmaker(bind = engine,autocommit=False,autoflush=False)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
    #将数据库生命周期分为开始和结束
    