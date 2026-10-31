# 木知前端与 AI 搜索

原木配色知识库，使用原生 HTML/CSS/JavaScript，与 FastAPI 同源部署。

## 当前可用

- 注册、登录、退出与服务器会话；管理员工作台、分类和知识管理。
- 64 条已发布数据结构知识与本地 BGE-small 的 512 维索引。
- 聊天框默认“语义增强搜索”：本地向量检索结合 BM25 关键词分数排序。
- 只搜索已发布、模型版本一致、正文与索引匹配的知识；不相关时返回空结果。
- 查看原文；用户选择后才调用 DeepSeek 解释；跳过解释不调用外部模型。
- 缺少 DeepSeek Key 时显示错误并保留搜索结果；服务异常可重试。
- 搜索来源快照及查询日志保存到服务器；页面的会话导航仍仅保留在本次打开期间。
- 发布/修改已发布正文会尝试同步重建索引；失败返回 index_status=pending，页面提示，旧索引不会参与搜索。再次发布或运行索引脚本可补建。

## 启动

先在项目根目录运行本地模型服务（Python 3.13 环境）：

```powershell
& 'C:\Users\xuxux\miniconda3\envs\anomaly_detection\python.exe' -u scripts/local_embedding_server.py
```

另开终端启动网页后端（项目 Python 3.8 环境）：

```powershell
.\database_experiment\Scripts\python.exe -m uvicorn app.main:app --reload
```

打开 http://127.0.0.1:8000 ，使用真实账号登录。登录页的演示入口仍是示例数据，不能用于验收真实语义搜索。前端更新后如显示旧提示，请 Ctrl+F5 强制刷新。

## 配置

`.env` 使用 `EMBEDDING_PROVIDER=local`、`LOCAL_EMBEDDING_URL=http://127.0.0.1:8011`。
可选解释需要在后端设置 `DEEPSEEK_API_KEY`，模型默认 `deepseek-flash`。修改环境变量后重启网页后端。密钥不进入浏览器或前端存储。

`SEMANTIC_MIN_SCORE` 默认 0.48，使用原始余弦相似度过滤后，再用 BM25 分数辅助排序。阈值只是当前小样本开发设置，不是概率或经过充分评测的准确率。后续需扩展评测再调整。

新数据库需在现有业务表创建后，单独运行以下安全初始化，不要重新执行带删库语句的完整 database.sql：

```powershell
.\database_experiment\Scripts\python.exe scripts/create_sessions.py
.\database_experiment\Scripts\python.exe scripts/create_search_contexts.py
```

管理员初始化：先通过注册页面创建账号，再由本机可信管理员运行 `scripts/make_admin.py 用户名`。密码目前仍采用原有 SHA-256，公网部署前应升级密码哈希、限流和 HTTPS。

## AI 接口

### POST /ai/search

登录后发送 `{"question":"最后放进去的元素为何最先出来？"}`，可选 category_id。
返回 search_id、sources（knowledge_id、title、excerpt、score、semantic_score）和 message。
空结果返回 200；本地模型未启动或知识索引无效返回 503；超长输入返回 422。不会在模型失败时假装“没有相关知识”。

### POST /ai/explain

发送 question、knowledge_ids、search_id。服务端验证搜索归属当前用户、问题一致、来源未变化且仍发布。搜索上下文有效期一小时，过期或源内容改变需重新搜索。兼容原关键词搜索时不传 search_id，后端重新校验问题与来源是否匹配。
返回 answer、status、sources。缺少 Key 为 503，模型网络故障为 504，输出或引用不合法为 502。模型只接收来源内容，前端按纯文本展示答案；引用合法不等于所有结论必然正确，仍需评估与审核。

### GET /ai/status

登录后返回本地模型服务是否可用，以及 DeepSeek 是否配置，只返回布尔状态和模型名，不返回密钥。

## 分类管理

GET `/categories`、GET `/categories/{id}`：登录用户查看；知识数量按权限过滤。
POST `/categories`、PUT `/categories/{id}`、DELETE `/categories/{id}`：仅管理员。重复名称 409、空白名称 422、有知识的分类禁止删除并返回 409。

## 数据与索引

种子数据位于 `scripts/data_structures_data.py`，共 8 类 64 条原创中文学习整理条目，含参考链接、定义、条件和常见误区。不是正式考试答案。

```powershell
.\database_experiment\Scripts\python.exe scripts/seed_data_structures.py --admin admin --publish
.\database_experiment\Scripts\python.exe scripts/index_local_embeddings.py
```

重复导入不覆盖已有知识；重复索引会跳过同版本模型且正文未变化的条目。

## 验证

```powershell
.\database_experiment\Scripts\python.exe -m tests.test_full_api
.\database_experiment\Scripts\python.exe -m tests.test_auth
.\database_experiment\Scripts\python.exe -m unittest tests.test_ai tests.test_embedding tests.test_seed -v
node tests/frontend.test.cjs
```

接口和 AI 单元测试使用独立数据库及模拟模型响应；真实搜索小样本结果记录在 tests/live-search-evaluation.json。本次真实语义检索可用；未配置 DeepSeek Key，真实 DeepSeek 成功响应尚未验收。浏览器视觉验收和 Docker/MCP 部署仍不属于这次完成范围。
# 知识审核操作（2026-10-31）

管理工作台新增状态筛选按钮：全部、未发布/待审核、已发布、已驳回。可同时按分类和标题/关键词筛选。长文件标题自动换行，右侧操作列固定，避免按钮被挤出可见区域。

| 状态 | 可执行操作 |
| --- | --- |
| 未发布/待审核（draft） | 查看、编辑、发布、填写理由驳回、删除 |
| 已发布（published） | 查看、编辑、撤回到待审核、删除 |
| 已驳回（rejected） | 查看内容和理由、编辑、恢复审核、删除 |

驳回和撤回都保留知识；删除会永久清理知识及其关联问答、来源和向量，前端会要求确认。已发布内容必须先撤回才能驳回。恢复审核不会自动发布。普通用户只能搜索和查看已发布内容。

新增 `PATCH /knowledge/{knowledge_id}/review`，请求为 `{"action":"reject","reason":"缺少来源"}`，或 `{"action":"withdraw"}`、`{"action":"restore"}`。只有管理员可操作；状态不匹配返回 409，空驳回理由返回 422。操作者、原状态、新状态和理由保存到 `update_logs`。`GET /knowledge` 支持 `status` 筛选。

已有 MySQL 库需要执行一次：

```powershell
.\database_experiment\Scripts\python.exe scripts/add_knowledge_review_status.py
```

当前开发库已执行。迁移仅在原有状态枚举末尾追加 `rejected`，不修改任何知识的当前状态。新建数据库直接使用更新后的 `database.sql`。

# 用户提交知识（2026-10-31）

普通用户登录后，左侧有“提交知识”和“我的投稿”。表单填写标题、正文、分类，可补充摘要、关键词、来源名称和链接。作者由登录会话确定，任何投稿都以待审核状态创建，不生成向量、不进入公开搜索。管理员可以按“用户投稿”来源筛选，查看投稿人和来源，沿用发布、驳回操作。

“我的投稿”只列出当前账号提交的内容，支持状态筛选、查看完整正文和驳回理由。待审核或已驳回内容可以修改后重新提交，重新进入待审核；已发布内容不能由投稿人直接修改，避免绕过审核。历史驳回理由和重投过程保留在更新日志中。

接口：`POST /submissions` 提交、`GET /submissions` 查看自己的列表、`GET /submissions/{id}` 查看自己的正文、`PUT /submissions/{id}` 修改重投。普通用户仍不能调用管理员新增、编辑、发布、驳回和删除接口。此功能复用现有知识、来源和日志表，不需要额外迁移数据库。

