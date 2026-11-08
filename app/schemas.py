"""当前 HTTP 接口使用的认证、分类、检索与来源字段校验。"""
from typing import Optional,Literal,List

from pydantic import BaseModel,EmailStr,Field,ConfigDict,field_validator

class UserLogin(BaseModel):
    username: str
    password: str

class UserRegister(BaseModel):
    username: str 
    password: str = Field(...,min_length=8,max_length=15)
    email: EmailStr
    role: Literal["admin","user"]="user"

class CategoryCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    name: str = Field(min_length=1, max_length=100)
    description: Optional[str] = Field(default=None, max_length=1000)

class CategoryUpdate(CategoryCreate):
    pass

class AiSearch(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    question: str = Field(min_length=1, max_length=500)
    category_id: Optional[int] = Field(default=None, gt=0)
    knowledge_id: Optional[int] = Field(default=None, gt=0)
    space: Literal['public', 'personal'] = 'public'
    mode: Literal['semantic', 'keyword'] = 'semantic'

class AiExplain(AiSearch):
    knowledge_ids: List[int] = Field(min_length=1, max_length=3)
    search_id: Optional[str] = Field(default=None, min_length=32, max_length=32)

class AiChat(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra='forbid')
    search_id: str = Field(min_length=32, max_length=32)
    message: str = Field(min_length=1, max_length=2000)
    conversation_id: Optional[str] = Field(default=None, min_length=32, max_length=32)
    expected_turns: int = Field(default=0, ge=0)

class KnowledgeSubmission(BaseModel):
    """知识内容与来源字段；公开性和所有权由服务端处理。"""
    model_config = ConfigDict(str_strip_whitespace=True, extra='forbid')
    title: str = Field(min_length=5, max_length=255)
    content: str = Field(min_length=10, max_length=10000)
    summary: Optional[str] = Field(default=None, max_length=1000)
    category_id: int = Field(gt=0)
    keyword: str = Field(default='', max_length=255)
    source_name: str = Field(default='', max_length=255)
    source_url: Optional[str] = Field(default=None, max_length=500)

    @field_validator('source_url')
    @classmethod
    def validate_source_url(cls, value):
        from urllib.parse import urlsplit
        if not value:
            return None
        parsed = urlsplit(value)
        if parsed.scheme not in ('http', 'https') or not parsed.hostname or parsed.username or parsed.password:
            raise ValueError('来源链接需为不含账号密码的 http 或 https 地址')
        return value
