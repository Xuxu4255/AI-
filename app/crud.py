from sqlalchemy import or_
from sqlalchemy.orm import Session
from app import models


#哈希加密
def hash_password(password: str)->str:
    import hashlib
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def create_user(db: Session,input_username: str,input_password: str,input_email: str):
    # 用户名或邮箱已存在时直接返回 None
    exists = db.query(models.User).filter(
        or_(models.User.username == input_username, models.User.email == input_email)
    ).first()
    if exists is not None:
        return None

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


def get_user_by_id(db: Session, input_uid: int):
    return db.query(models.User).filter(models.User.uid == input_uid).first()



def login_user(db: Session,input_username: str,input_password: str):
    user=db.query(models.User).filter(models.User.username==input_username).first()

    if user==None:
        return False

    if user.password_hash==hash_password(input_password):
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
    category.description = input_new_description

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

#知识的增删改查

def create_knowledge(db: Session,input_title: str,input_content: str,
                    input_category_id: int,input_keyword: str,input_summary: str,input_created_by: int):
    # 先校验外键是否存在，避免数据库抛 IntegrityError
    if get_category_by_id(db, input_category_id) is None:
        return None
    if get_user_by_id(db, input_created_by) is None:
        return None

    new_knowledge = models.Knowledge(
        title = input_title,
        content = input_content,
        category_id = input_category_id,
        keyword = input_keyword,
        summary=input_summary,
        created_by=input_created_by
    )

    db.add(new_knowledge)
    db.commit()
    db.refresh(new_knowledge)
    return new_knowledge



def get_knowledge_list(db: Session,input_category_id: int = None,input_keyword: str = None):
    query = db.query(models.Knowledge)

    if input_category_id is not None:
        query = query.filter(models.Knowledge.category_id == input_category_id)
    if input_keyword is not None and input_keyword != "":
        query = query.filter(models.Knowledge.keyword.like(f"%{input_keyword}%"))

    return query.all()


#kid在数据库中是主键
def update_knowledge(db: Session,input_title: str,input_content: str,
                     input_summary: str,input_kid: int,input_keyword: str,
                     input_created_by: int,input_category_id: int):
    under_update_knowledge = db.query(models.Knowledge).filter(models.Knowledge.kid==input_kid).first()
    if under_update_knowledge==None:
        return None

    # 要修改的外键必须先存在
    if input_category_id is not None and get_category_by_id(db, input_category_id) is None:
        return None
    if input_created_by is not None and get_user_by_id(db, input_created_by) is None:
        return None

    if input_title !=None:
        under_update_knowledge.title = input_title
    if input_content != None:
        under_update_knowledge.content = input_content
    if input_summary != None:
        under_update_knowledge.summary = input_summary
    if input_keyword != None:
        under_update_knowledge.keyword = input_keyword
    if input_category_id != None:
        under_update_knowledge.category_id = input_category_id
    if input_created_by != None:
        under_update_knowledge.created_by = input_created_by

    db.commit()
    db.refresh(under_update_knowledge)
    return under_update_knowledge


def delete_knowledge(db: Session,input_kid: int):
    under_delete_knowledge = db.query(models.Knowledge).filter(models.Knowledge.kid==input_kid).first()

    if under_delete_knowledge==None:
        return False

    db.delete(under_delete_knowledge)
    db.commit()
    return True

def get_knowledge_by_id(db: Session, input_kid: int):
    return db.query(models.Knowledge).filter(models.Knowledge.kid == input_kid).first()


# 创建问答对
def create_qapair(db: Session, input_question_text: str,
                input_answer_text: str, input_knowledge_id: int, input_created_by: int):
    # 先校验外键是否存在
    if get_knowledge_by_id(db, input_knowledge_id) is None:
        return None
    if get_user_by_id(db, input_created_by) is None:
        return None

    new_qapair = models.QaPair(
        question_text=input_question_text,
        answer_text=input_answer_text,
        knowledge_id=input_knowledge_id,
        created_by=input_created_by,
        status="pending"#默认为审核
    )

    db.add(new_qapair)
    db.commit()
    db.refresh(new_qapair)

    return new_qapair


# 查询条件说明：
# 1. qid 是主键，优先作为唯一查询条件
# 2. knowledge_id 和 created_by 只能作为辅助筛选条件
# 3. 这两个字段可以分开用，也可以一起用
# 4. 三个条件可以同时存在，最终是“AND”关系
# 5. 只传 qid 时，按主键精确查询
# 6. 只传 knowledge_id 或 created_by 时，按对应筛选查询
# 7. 传两个条件时，按两者组合筛选
# 8. 传三个条件时，按三者同时满足筛选

def get_qapair_list(db: Session, input_qid: int = None, input_knowledge_id: int = None,
                   input_created_by: int = None,input_status: str = None):
    query = db.query(models.QaPair)

    if input_qid is not None:
        query = query.filter(models.QaPair.qid == input_qid)
    if input_knowledge_id is not None:
        query = query.filter(models.QaPair.knowledge_id == input_knowledge_id)
    if input_created_by is not None:
        query = query.filter(models.QaPair.created_by == input_created_by)
    if input_status is not None:
        query = query.filter(models.QaPair.status == input_status)

    return query.all()



def get_qapair_by_id(db: Session, input_qid: int = None):
    return db.query(models.QaPair).filter(models.QaPair.qid == input_qid).first()




def review_qapair(db: Session, input_qid: int, input_status: str):
    under_review_qapair = db.query(models.QaPair).filter(models.QaPair.qid == input_qid).first()

    if under_review_qapair == None:
        return None
    if input_status not in ["approved", "rejected"]:
        return None

    under_review_qapair.status = input_status
    db.commit()
    db.refresh(under_review_qapair)

    return under_review_qapair






def create_feedback(db: Session, input_user_id: int, input_feedback_type: str,
                   input_content: str = None, input_knowledge_id: int = None,
                   input_qa_id: int = None):
    # 先校验外键是否存在
    if get_user_by_id(db, input_user_id) is None:
        return None
    if input_knowledge_id is not None and get_knowledge_by_id(db, input_knowledge_id) is None:
        return None
    if input_qa_id is not None and get_qapair_by_id(db, input_qa_id) is None:
        return None

    new_feedback = models.Feedback(
        knowledge_id=input_knowledge_id,
        qa_id=input_qa_id,
        user_id=input_user_id,
        feedback_type=input_feedback_type,
        content=input_content,
    )

    db.add(new_feedback)
    db.commit()
    db.refresh(new_feedback)

    return new_feedback


def get_feedback_list(db: Session, input_fid: int = None, input_knowledge_id: int = None,
                    input_qa_id: int = None, input_user_id: int = None,
                    input_feedback_type: str = None):
    query = db.query(models.Feedback)

    if input_fid is not None:
        query = query.filter(models.Feedback.fid == input_fid)
    if input_knowledge_id is not None:
        query = query.filter(models.Feedback.knowledge_id == input_knowledge_id)
    if input_qa_id is not None:
        query = query.filter(models.Feedback.qa_id == input_qa_id)
    if input_user_id is not None:
        query = query.filter(models.Feedback.user_id == input_user_id)
    if input_feedback_type is not None:
        query = query.filter(models.Feedback.feedback_type == input_feedback_type)

    return query.all()


def get_feedback_by_id(db: Session, input_fid: int):
    return db.query(models.Feedback).filter(models.Feedback.fid == input_fid).first()


def update_feedback(db: Session, input_fid: int, input_content: str = None,
                  input_feedback_type: str = None, input_knowledge_id: int = None,
                  input_qa_id: int = None):
    feedback = db.query(models.Feedback).filter(models.Feedback.fid == input_fid).first()

    if feedback is None:
        return None

    # 要修改的外键必须先存在
    if input_knowledge_id is not None and get_knowledge_by_id(db, input_knowledge_id) is None:
        return None
    if input_qa_id is not None and get_qapair_by_id(db, input_qa_id) is None:
        return None

    if input_content is not None:
        feedback.content = input_content
    if input_feedback_type is not None:
        feedback.feedback_type = input_feedback_type
    if input_knowledge_id is not None:
        feedback.knowledge_id = input_knowledge_id
    if input_qa_id is not None:
        feedback.qa_id = input_qa_id

    db.commit()
    db.refresh(feedback)
    return feedback


def delete_feedback(db: Session, input_fid: int):
    feedback = db.query(models.Feedback).filter(models.Feedback.fid == input_fid).first()

    if feedback is None:
        return False

    db.delete(feedback)
    db.commit()
    return True











    
    