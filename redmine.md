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
答: 知识的编号（主键），知识标题，知识内容，知识来源，知识标签（例如 LeetCode 里面的题目标签），知识和哪些其他知识相关（标签一致），知识关键字（用于搜索问题时快速定位知识）

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

这是整个系统最核心的表。
关键词字段很重要，因为你提到“知识关键字”。

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

你提到“文档来源”，这个表专门存来源信息。
这样知识和来源分离更规范。

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

这是“智能问答知识库”的核心对话数据。
你可以用它做 FAQ、问答管理。

6. feedback 用户反馈表
作用：记录用户对知识内容的反馈

字段建议：

id：主键
user_id：外键，关联用户
knowledge_id：外键，关联知识
feedback_type：反馈类型，如 error / useful / not_clear / duplicate
content：反馈内容
created_at：创建时间

二、AI 应用补充表
在“AI 智能问答知识库管理系统”中，除了上述基础表外，还需要增加 AI 相关的补充表，以支持语义检索、问答日志、知识向量化和知识更新追踪。

7. knowledge_embedding 知识向量表
作用：用于 AI 检索和语义匹配

字段建议：

id：主键
knowledge_id：外键，关联知识条目
embedding_text：向量化文本内容
embedding_vector：向量数据
model_name：模型名称
created_at：创建时间

说明：

这是 AI 应用最关键的补充表之一。
它用来支持“问题相似度搜索”和“知识召回”，帮助模型找到最相关的知识。

8. query_logs 提问日志表
作用：记录用户提问、系统检索和回答过程

字段建议：

id：主键
user_id：外键，关联用户
question_text：用户问题内容
matched_knowledge_ids：检索到的知识 ID 列表
answer_text：AI 生成的回答
created_at：创建时间

说明：

用于记录问答历史，便于分析用户需求和优化知识库。
这是 AI 系统的重要运营数据表。

9. tags 标签表
作用：给知识进行主题标签管理

字段建议：

id：主键
name：标签名称

说明：

例如：Python、AI、数据库、面试题、算法等。
标签可以帮助知识更方便地被检索和分类。

10. knowledge_tags 知识标签关联表
作用：建立知识与标签之间的多对多关系

字段建议：

id：主键
knowledge_id：外键，关联知识条目
tag_id：外键，关联标签

说明：

一条知识可以对应多个标签，标签也可以关联多条知识。
这样可以增强知识查找能力。

11. update_logs 更新记录表
作用：记录知识的版本更新与变更历史

字段建议：

id：主键
knowledge_id：外键，关联知识条目
operator_id：外键，关联操作用户
action：操作类型，如 create / update / delete
old_content：更新前内容
new_content：更新后内容
changed_at：更新时间

说明：

这张表可以追踪知识变更历史，便于审计和回滚。
它也符合“更新记录”的需求。

12. related_knowledge 相关知识表
作用：记录知识之间的关联关系

字段建议：

id：主键
knowledge_id：外键，关联知识条目
related_knowledge_id：关联的另一条知识 ID
relation_type：关联类型，如 same_topic / prerequisite / extension

说明：

用于表达知识的关联关系，可以帮助系统在问答时查找相关知识。
这也符合“知识和哪些别的知识相关”的需求。


三、真实运行流程
1. 管理员维护知识库
管理员往 knowledge 中写知识，写分类，写来源。

2. 用户提问
用户在前端输入问题：

“python如何删除列表中的元素？”
3. 系统先做检索
后端从 knowledge / knowledge_embedding 中找相似知识。

4. AI 生成答案
把相关知识和问题发给 DeepSeek，生成回答。

5. 保存日志
把这次真实提问记录到 query_logs。

6. 反馈修正
如果用户觉得答案不对，就写入 feedback。

7. 质量提升
如果某个高频问题常被问，管理员可以整理成标准问答，写入 qa_pairs。


