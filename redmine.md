选题

智能问答知识库管理系统

知识条目、文档来源、问答对、知识分类、更新记录、用户反馈

半结构化数据组织、索引设计、知识建模、数据更新维护

开发流程

确定选题
数据建模
设计数据库表
写后端接口
连接 MySQL
写前端页面
联调前后端
测试
整理文档和提交 Git



前端页面
   ↓
FastAPI 后端
   ↓
MySQL 数据库（保存知识、问答、用户、反馈）
   ↓
DeepSeek API（生成回答）



架构图：



数据库作业/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── database.py
│   ├── models.py
│   ├── schemas.py
│   ├── crud.py
│   ├── ai_service.py
│   └── config.py
├── static/
│   ├── index.html
│   ├── style.css
│   └── script.js
├── .env
├── .gitignore
├── requirements.txt
├── README.md
└── database.sql


这些文件分别干什么
1. main.py
后端入口，写 FastAPI 路由

例如：

POST /ask
POST /knowledge
GET /knowledge
GET /categories
POST /feedback


2. database.py
数据库连接配置

例如：

MySQL 连接
建表初始化
获取数据库连接对象


3. models.py
数据库表结构

例如：

User
Category
Knowledge
Question
Feedback
QueryLog


4. schemas.py
请求和响应模型

例如：

用户提交问题
知识新增请求
反馈请求
返回 JSON 结构


5. crud.py
数据库操作逻辑

例如：

create_knowledge()
get_knowledge_by_id()
search_knowledge()
save_feedback()
save_query_log()


6. app/ai_service.py
AI 接口封装

例如：

调用 DeepSeek API
生成回答
组织 prompt
处理返回结果


7. app/config.py
配置文件

例如：

API Key
模型名称
数据库地址
超时设置


8. index.html
前端页面

输入框
按钮
列表展示区
结果展示区


9. script.js
前端逻辑

调用后端接口
渲染知识列表
提交问题
展示返回结果


10. .env
环境变量文件

MySQL 用户名密码
DeepSeek API Key


11. requirements.txt
依赖包列表

例如：
fastapi
uvicorn
pymysql
python-dotenv
requests
pydantic


12. database.sql
SQL 文件

建库
建表
插入示例数据

ad
13. README.md
项目说明文档

项目介绍
功能说明
运行步骤
技术栈














数据建模：
问: 这个系统是管理员维护，还是普通用户也能使用？
答: 两种角色都有 - 管理员 + 普通用户都需要
问: 你们的核心数据对象有哪些？
答: 知识条目 - 知识库内容，问答对 - FAQ/问题与答案，文档来源 - 知识来源或文档信息，知识分类 - 按类别组织知识，用户反馈 - 反馈/纠错记录，更新记录 - 版本或更新日志
问: 系统最重要的功能是什么？
答: 新增知识 - 添加知识条目，修改知识 - 编辑和更新，删除知识 - 删除过期内容，搜索知识 - 按关键词/分类查找，问答查询 - 根据问题查答案，反馈与审核 - 用户反馈和审核
问: 每条知识和问题大概需要哪些关键字段？可以直接写一个简短示例。
答: 知识的编号（主键） 知识 知识的来源 知识的标签（例如lleetcode里面的题目标签）知识的来源 知识和哪些别的知识相关（标签一致） 知识关键字（问题如何搜索才可以获得这个知识）

设计数据库核心表：

一、先做核心版表
建议最先建立这 6 类表：



1. users 用户表
作用：区分管理员和普通用户


字段建议：

id：主键
username：用户名
password：密码
email：邮箱
role：角色，admin / user
created_at：创建时间


2. categories 分类表
作用：给知识分门别类


字段建议：

id：主键
name：分类名
description：分类说明
created_at：创建时间
例子：

Python
数据库
AI
Java



3. knowledge 知识条目表
作用：存放核心知识内容

字段建议：

id：主键
title：标题
content：知识正文
summary：知识摘要
category_id：外键，关联分类
created_by：外键，关联用户
keyword：关键词，用于搜索
status：状态，draft / published / deleted
created_at：创建时间
updated_at：更新时间
说明：

这是整个系统最核心的表
关键词字段很重要，因为你提到“知识关键字”



4. documents 文档来源表
作用：记录知识来自哪里

字段建议：

id：主键
knowledge_id：外键，关联知识
source_type：来源类型，如 book / article / online / file
source_name：来源名称
source_url：来源链接
file_name：文件名
file_path：文件路径
created_at：创建时间
说明：

你提到“文档来源”，这个表专门存来源信息
这样知识和来源分离更规范



5. qa_pairs 问答对表
作用：存储“问题 + 回答”对

字段建议：

id：主键
question_text：问题内容
answer_text：答案内容
knowledge_id：外键，关联知识条目
created_by：外键，关联用户
created_at：创建时间
status：状态，pending / approved / rejected
说明：

这是“智能问答知识库”的核心对话数据
你可以用它做 FAQ、问答管理


6. feedback 用户反馈表
作用：记录用户对知识内容的反馈

字段建议：

id：主键
user_id：外键，关联用户
knowledge_id：外键，关联知识
feedback_type：反馈类型，如 error / useful / not_clear / duplicate
content：反馈内容
created_at：创建时间
