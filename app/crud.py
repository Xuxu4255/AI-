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

    # 先把挂在知识下面的子数据清掉，不然外键会把删除拦住
    # 1. 反馈：既可能挂着知识，也可能挂着这条知识下的问答对
    qa_id_list = db.query(models.QaPair.qid).filter(models.QaPair.knowledge_id == input_kid).all()
    qa_id_list = [row[0] for row in qa_id_list]
    db.query(models.Feedback).filter(or_(
        models.Feedback.knowledge_id == input_kid,
        models.Feedback.qa_id.in_(qa_id_list),
    )).delete()

    # 2. 问答对、文档、更新日志
    db.query(models.QaPair).filter(models.QaPair.knowledge_id == input_kid).delete()
    db.query(models.Document).filter(models.Document.knowledge_id == input_kid).delete()
    db.query(models.UpdateLog).filter(models.UpdateLog.knowledge_id == input_kid).delete()

    # 3. 标签绑定、向量、关联知识
    db.query(models.KnowledgeTag).filter(models.KnowledgeTag.knowledge_id == input_kid).delete()
    db.query(models.KnowledgeEmbedding).filter(models.KnowledgeEmbedding.knowledge_id == input_kid).delete()
    db.query(models.RelatedKnowledge).filter(
        or_(
            models.RelatedKnowledge.knowledge_id == input_kid,
            models.RelatedKnowledge.related_knowledge_id == input_kid,
        )
    ).delete()

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


#5.标签、关联知识、向量的增删改查，以及搜索

#标签的增删改查

def get_tag_by_id(db: Session, input_tid: int):
    return db.query(models.Tag).filter(models.Tag.tid == input_tid).first()


def get_tag_by_name(db: Session, input_name: str):
    return db.query(models.Tag).filter(models.Tag.name == input_name).first()


def get_tag_list(db: Session):
    return db.query(models.Tag).all()


def create_tag(db: Session, input_name: str, input_description: str = None):
    # 标签名是唯一的，重名就直接返回 None
    if get_tag_by_name(db, input_name) is not None:
        return None

    new_tag = models.Tag(
        name=input_name,
        description=input_description
    )

    db.add(new_tag)
    db.commit()
    db.refresh(new_tag)
    return new_tag


def update_tag(db: Session, input_tid: int, input_new_name: str = None, input_new_description: str = None):
    tag = get_tag_by_id(db, input_tid)

    if tag is None:
        return None

    # 改名字的时候要保证不和别的标签重名
    if input_new_name is not None and input_new_name != tag.name:
        if get_tag_by_name(db, input_new_name) is not None:
            return None

    if input_new_name is not None:
        tag.name = input_new_name
    if input_new_description is not None:
        tag.description = input_new_description

    db.commit()
    db.refresh(tag)
    return tag


def delete_tag(db: Session, input_tid: int):
    tag = get_tag_by_id(db, input_tid)

    if tag is None:
        return False

    # 先解绑知识，不然外键会拦住删除
    db.query(models.KnowledgeTag).filter(models.KnowledgeTag.tag_id == input_tid).delete()

    db.delete(tag)
    db.commit()
    return True


#知识和标签的绑定

def get_knowledge_tag(db: Session, input_knowledge_id: int, input_tag_id: int):
    return db.query(models.KnowledgeTag).filter(
        models.KnowledgeTag.knowledge_id == input_knowledge_id,
        models.KnowledgeTag.tag_id == input_tag_id
    ).first()


def add_knowledge_tag(db: Session, input_knowledge_id: int, input_tag_id: int):
    # 先校验两个外键是否存在
    if get_knowledge_by_id(db, input_knowledge_id) is None:
        return None
    if get_tag_by_id(db, input_tag_id) is None:
        return None
    # 组合主键，重复绑定会报错，这里提前挡掉
    if get_knowledge_tag(db, input_knowledge_id, input_tag_id) is not None:
        return None

    new_knowledge_tag = models.KnowledgeTag(
        knowledge_id=input_knowledge_id,
        tag_id=input_tag_id
    )

    db.add(new_knowledge_tag)
    db.commit()
    db.refresh(new_knowledge_tag)
    return new_knowledge_tag


def remove_knowledge_tag(db: Session, input_knowledge_id: int, input_tag_id: int):
    knowledge_tag = get_knowledge_tag(db, input_knowledge_id, input_tag_id)

    if knowledge_tag is None:
        return False

    db.delete(knowledge_tag)
    db.commit()
    return True


#某个知识身上的所有标签
def get_tags_by_knowledge(db: Session, input_knowledge_id: int):
    return db.query(models.Tag).join(
        models.KnowledgeTag, models.KnowledgeTag.tag_id == models.Tag.tid
    ).filter(
        models.KnowledgeTag.knowledge_id == input_knowledge_id
    ).all()


#某个标签下的所有知识
def get_knowledge_by_tag(db: Session, input_tag_id: int):
    return db.query(models.Knowledge).join(
        models.KnowledgeTag, models.KnowledgeTag.knowledge_id == models.Knowledge.kid
    ).filter(
        models.KnowledgeTag.tag_id == input_tag_id
    ).all()


#相关知识的增删查

def get_related_knowledge_by_id(db: Session, input_rid: int):
    return db.query(models.RelatedKnowledge).filter(models.RelatedKnowledge.rid == input_rid).first()


def create_related_knowledge(db: Session, input_knowledge_id: int,
                            input_related_knowledge_id: int, input_relevance_score: float = 0.0):
    # 两条知识都必须存在
    if get_knowledge_by_id(db, input_knowledge_id) is None:
        return None
    if get_knowledge_by_id(db, input_related_knowledge_id) is None:
        return None
    # 自己不能和自己关联
    if input_knowledge_id == input_related_knowledge_id:
        return None
    # 同一条关联不重复插入
    exists = db.query(models.RelatedKnowledge).filter(
        models.RelatedKnowledge.knowledge_id == input_knowledge_id,
        models.RelatedKnowledge.related_knowledge_id == input_related_knowledge_id
    ).first()
    if exists is not None:
        return None

    new_relation = models.RelatedKnowledge(
        knowledge_id=input_knowledge_id,
        related_knowledge_id=input_related_knowledge_id,
        relevance_score=input_relevance_score
    )

    db.add(new_relation)
    db.commit()
    db.refresh(new_relation)
    return new_relation


#查某条知识关联出去的知识，相关度高的排前面
def get_related_knowledge_list(db: Session, input_knowledge_id: int):
    return db.query(models.RelatedKnowledge).filter(
        models.RelatedKnowledge.knowledge_id == input_knowledge_id
    ).order_by(
        models.RelatedKnowledge.relevance_score.desc()
    ).all()


def delete_related_knowledge(db: Session, input_rid: int):
    relation = get_related_knowledge_by_id(db, input_rid)

    if relation is None:
        return False

    db.delete(relation)
    db.commit()
    return True


#知识向量

def get_embedding_by_id(db: Session, input_embedding_id: int):
    return db.query(models.KnowledgeEmbedding).filter(
        models.KnowledgeEmbedding.embedding_id == input_embedding_id
    ).first()


#取某条知识最新的一条向量
def get_embedding_by_knowledge(db: Session, input_knowledge_id: int):
    return db.query(models.KnowledgeEmbedding).filter(
        models.KnowledgeEmbedding.knowledge_id == input_knowledge_id
    ).order_by(
        models.KnowledgeEmbedding.embedding_id.desc()
    ).first()


def create_embedding(db: Session, input_knowledge_id: int, input_embedding_model: str,
                    input_embedding_text: str = None, input_embedding_vector: str = None):
    # 先校验外键是否存在
    if get_knowledge_by_id(db, input_knowledge_id) is None:
        return None

    new_embedding = models.KnowledgeEmbedding(
        knowledge_id=input_knowledge_id,
        embedding_model=input_embedding_model,
        embedding_text=input_embedding_text,
        embedding_vector=input_embedding_vector
    )

    db.add(new_embedding)
    db.commit()
    db.refresh(new_embedding)
    return new_embedding


def update_embedding(db: Session, input_embedding_id: int, input_embedding_model: str = None,
                    input_embedding_text: str = None, input_embedding_vector: str = None):
    embedding = get_embedding_by_id(db, input_embedding_id)

    if embedding is None:
        return None

    if input_embedding_model is not None:
        embedding.embedding_model = input_embedding_model
    if input_embedding_text is not None:
        embedding.embedding_text = input_embedding_text
    if input_embedding_vector is not None:
        embedding.embedding_vector = input_embedding_vector

    db.commit()
    db.refresh(embedding)
    return embedding


def delete_embedding(db: Session, input_embedding_id: int):
    embedding = get_embedding_by_id(db, input_embedding_id)

    if embedding is None:
        return False

    db.delete(embedding)
    db.commit()
    return True


#搜索：关键词、分类、标签、状态可以单独用，也可以组合用
def search_knowledge(db: Session, input_keyword: str = None, input_category_id: int = None,
                    input_tag_id: int = None, input_status: str = None):
    query = db.query(models.Knowledge)

    if input_category_id is not None:
        query = query.filter(models.Knowledge.category_id == input_category_id)
    if input_status is not None:
        query = query.filter(models.Knowledge.status == input_status)
    if input_keyword is not None and input_keyword != "":
        # 标题、正文、摘要、关键词任意一个命中就算搜索到
        query = query.filter(or_(
            models.Knowledge.title.like(f"%{input_keyword}%"),
            models.Knowledge.content.like(f"%{input_keyword}%"),
            models.Knowledge.summary.like(f"%{input_keyword}%"),
            models.Knowledge.keyword.like(f"%{input_keyword}%"),
        ))
    if input_tag_id is not None:
        query = query.join(
            models.KnowledgeTag, models.KnowledgeTag.knowledge_id == models.Knowledge.kid
        ).filter(models.KnowledgeTag.tag_id == input_tag_id)

    # 标签join可能让一条知识出现多次，用distinct去重
    return query.distinct().all()


#6.日志模块：查询日志和更新日志

#查询日志：记录用户问了什么、系统答了什么

def create_query_log(db: Session, input_question_text: str, input_user_id: int = None,
                    input_answer_text: str = None, input_model_name: str = None,
                    input_retrieval_count: int = 0, input_feedback_status: str = "unrated"):
    # user_id 可以为空（游客提问），但传了就必须是真实用户
    if input_user_id is not None and get_user_by_id(db, input_user_id) is None:
        return None

    new_query_log = models.QueryLog(
        user_id=input_user_id,
        question_text=input_question_text,
        answer_text=input_answer_text,
        model_name=input_model_name,
        retrieval_count=input_retrieval_count,
        feedback_status=input_feedback_status
    )

    db.add(new_query_log)
    db.commit()
    db.refresh(new_query_log)
    return new_query_log


def get_query_log_by_id(db: Session, input_lid: int):
    return db.query(models.QueryLog).filter(models.QueryLog.lid == input_lid).first()


#查询条件可以单独用，也可以组合用，最终是AND关系
def get_query_log_list(db: Session, input_lid: int = None, input_user_id: int = None,
                    input_feedback_status: str = None):
    query = db.query(models.QueryLog)

    if input_lid is not None:
        query = query.filter(models.QueryLog.lid == input_lid)
    if input_user_id is not None:
        query = query.filter(models.QueryLog.user_id == input_user_id)
    if input_feedback_status is not None:
        query = query.filter(models.QueryLog.feedback_status == input_feedback_status)

    #日志按时间倒序，最新的排前面
    return query.order_by(models.QueryLog.lid.desc()).all()


def update_query_log(db: Session, input_lid: int, input_answer_text: str = None,
                    input_model_name: str = None, input_retrieval_count: int = None,
                    input_feedback_status: str = None):
    query_log = get_query_log_by_id(db, input_lid)

    if query_log is None:
        return None

    if input_answer_text is not None:
        query_log.answer_text = input_answer_text
    if input_model_name is not None:
        query_log.model_name = input_model_name
    if input_retrieval_count is not None:
        query_log.retrieval_count = input_retrieval_count
    if input_feedback_status is not None:
        query_log.feedback_status = input_feedback_status

    db.commit()
    db.refresh(query_log)
    return query_log


def delete_query_log(db: Session, input_lid: int):
    query_log = get_query_log_by_id(db, input_lid)

    if query_log is None:
        return False

    db.delete(query_log)
    db.commit()
    return True


#更新日志：记录谁对哪条知识做了什么操作

def create_update_log(db: Session, input_knowledge_id: int, input_user_id: int,
                    input_action_type: str, input_old_value: str = None,
                    input_new_value: str = None):
    # 先校验外键是否存在
    if get_knowledge_by_id(db, input_knowledge_id) is None:
        return None
    if get_user_by_id(db, input_user_id) is None:
        return None
    # 操作类型是枚举，不合法就不写库
    if input_action_type not in ["create", "update", "delete", "publish", "revert"]:
        return None

    new_update_log = models.UpdateLog(
        knowledge_id=input_knowledge_id,
        user_id=input_user_id,
        action_type=input_action_type,
        old_value=input_old_value,
        new_value=input_new_value
    )

    db.add(new_update_log)
    db.commit()
    db.refresh(new_update_log)
    return new_update_log


def get_update_log_by_id(db: Session, input_log_id: int):
    return db.query(models.UpdateLog).filter(models.UpdateLog.log_id == input_log_id).first()


def get_update_log_list(db: Session, input_log_id: int = None, input_knowledge_id: int = None,
                    input_user_id: int = None, input_action_type: str = None):
    query = db.query(models.UpdateLog)

    if input_log_id is not None:
        query = query.filter(models.UpdateLog.log_id == input_log_id)
    if input_knowledge_id is not None:
        query = query.filter(models.UpdateLog.knowledge_id == input_knowledge_id)
    if input_user_id is not None:
        query = query.filter(models.UpdateLog.user_id == input_user_id)
    if input_action_type is not None:
        query = query.filter(models.UpdateLog.action_type == input_action_type)

    #日志按时间倒序，最新的排前面
    return query.order_by(models.UpdateLog.log_id.desc()).all()


def delete_update_log(db: Session, input_log_id: int):
    update_log = get_update_log_by_id(db, input_log_id)

    if update_log is None:
        return False

    db.delete(update_log)
    db.commit()
    return True











    
    