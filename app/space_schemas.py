"""知识书架接口校验。公开性与所有权由服务端执行，拒绝额外字段。"""
from typing import Optional, Literal
from pydantic import BaseModel, ConfigDict, Field
from app.schemas import KnowledgeSubmission


class Strict(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra='forbid')


class PersonalCategoryInput(Strict):
    name: str = Field(min_length=1, max_length=100)
    color: str = Field(default='#74DCFF', pattern=r'^#[0-9a-fA-F]{6}$')


class ShelfStyleInput(Strict):
    style: Literal['glass', 'oak', 'arch', 'wide'] = 'glass'


class ShelfCreate(ShelfStyleInput):
    name: str = Field(min_length=1, max_length=100)
    space: Literal['personal', 'public'] = 'personal'


class KnowledgeInput(KnowledgeSubmission):
    # 原 category_id 用于公共主分类；个人归类使用独立 ID。
    title: str = Field(min_length=1, max_length=255)
    content: str = Field(min_length=1, max_length=10000)
    personal_category_id: int = Field(gt=0)
    visibility: Literal['private', 'public'] = 'private'


class VisibilityInput(Strict):
    visibility: Literal['private', 'public']
    category_id: Optional[int] = Field(default=None, gt=0)


class EntryInput(Strict):
    personal_category_id: int = Field(gt=0)


class LinkInput(Strict):
    source_id: int = Field(gt=0)
    target_id: int = Field(gt=0)
    relation: Literal['相关', '前置知识', '补充说明'] = '相关'


class AppearanceInput(Strict):
    exposure: float = Field(default=1.0, ge=0.5, le=1.5, allow_inf_nan=False)
    theme: Literal['blue', 'purple', 'teal', 'black', 'custom'] = 'blue'
    custom_color: str = Field(default='#102A48', pattern=r'^#[0-9a-fA-F]{6}$')
    paused: bool = False
    reduced_motion: bool = False


class PlanetInput(Strict):
    visible: bool = True
    style: Literal['jupiter', 'saturn', 'neptune', 'violet', 'earth'] = 'jupiter'
    position: int = Field(default=0, ge=0, le=10000)


class ModerationInput(Strict):
    hidden: bool
    reason: str = Field(default='', max_length=500)


class AdminCategoryInput(Strict):
    name: str = Field(min_length=1, max_length=100)
    description: str = Field(default='', max_length=1000)
    shelf_style: Literal['glass', 'oak', 'arch', 'wide'] = 'glass'
    visible: bool = True


class PlanetBatchInput(Strict):
    visible: bool
