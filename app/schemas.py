#校验层，检验前端传过来的Json文件是否合规
#如果不合规，会报402错误



from typing import Optional,Literal
#typing python自带的类型工具

#Optional:这个字段可以为空
#Literal:这个字段可以取某几个固定值

from pydantic import BaseModel,EmailStr,Field
#fastAPI最核心的库，用来做数据校验

#BaseModel:定义一个数据结构模板
#EmailStr:要求这个字段是邮箱格式
#Field:给字段加限制，比如最小长度，最大长度

#登录请求：
class UserLogin(BaseModel):
    username: str
    password: str

    
#用户注册
class UserRegister(BaseModel):
    username: str 
    password: str = Field(...,min_length=8,max_length=15)
    email: EmailStr
    role: Literal["admin","user"]="user"


#声明
class CategoryCreate(BaseModel):
    name: str
    description: Optional[str]=None


class KnowledgeCreate(BaseModel):
    title: str = Field(...,min_length=5,max_length=30)
    content: str
    summary: Optional[str]=None
    category_id: int
    created_by: int
    keyword: str



class KnowledgeUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    summary: Optional[str]=None
    category_id: Optional[int] = None
    created_by: Optional[int] = None
    keyword: Optional[str]=None


class FeedbackCreate(BaseModel):
    knowledge_id: Optional[int]=None
    qa_id: Optional[int]=None
    user_id: int
    content: Optional[str]=None
    feedback_type: Literal["like","dislike","error","suggestion"]



class QaCreate(BaseModel):
    knowledge_id: int
    question_text: str
    answer_text: str
    created_by: int
    status: Literal["pending","approved","reject"] = "pending"



class QueryLogCreate(BaseModel):
    user_id: Optional[int]=None
    question_text: str
    answer_text: str
    model_name: Optional[str]=Field(default=None,max_length=100)
    retrieval_count: int
    feedback_status: Literal["unrated","liked","disliked"]="unrated"
