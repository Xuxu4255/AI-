# 项目风格说明

这是一个基于 Python FastAPI + MySQL + 前端的 AI 知识问答知识库管理系统项目。

## 1. 命名风格
- SQL 表名统一使用小写。
- 字段名统一使用小写。
- 关键字、状态值、枚举值也统一使用小写。
- 例如：users、categories、knowledge、documents、qa_pairs、feedback。
- 新增 SQL 时优先保持这种风格，不使用大写命名。

## 2. SQL 写法风格
- 统一使用 `create table`、`insert into`、`alter table` 等小写语法。
- 每个字段尽量写在一行，右侧添加中文注释。
- 注释统一使用 `--`。
- 例如：

```sql
create table knowledge (
    Kid int primary key auto_increment, -- 知识编号，主键，自动增长
    title varchar(255) not null, -- 知识标题
    content text not null, -- 知识正文
    category_id int not null -- 所属分类编号
);
```

## 3. 项目结构风格
- 后端目录：app/
- 前端目录：static/
- 配置文件：.env
- 依赖文件：requirements.txt
- Git 忽略：.gitignore
- 数据库脚本：database.sql

## 4. 业务逻辑风格
- 先做数据建模，再写接口。
- 主核心对象：users、categories、knowledge、documents、qa_pairs、feedback。
- AI 相关能力保持为扩展：knowledge_embedding、query_logs、tags、knowledge_tags、update_logs、related_knowledge。
- 重点围绕：知识库管理、知识搜索、问答查询、反馈修正。

## 5. 代码实现风格
- Python 代码保持清晰分层：main.py、database.py、models.py、schemas.py、crud.py、ai_service.py。
- 前端保持简单：index.html、style.css、script.js。
- 接口命名尽量直观，优先使用 CRUD 语义。
- 数据库结构应尽量符合 AI 应用场景：知识 + 检索 + 问答 + 反馈。

## 6. 说明
- 这个项目偏课程与演示型项目，强调可读性和结构清晰。
- 不追求过度抽象和过度分层。
- 优先保证：表结构清晰、接口易懂、功能可演示、代码风格统一。
