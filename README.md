# 知识图书馆

FastAPI + MySQL + 本地 BGE-small Embedding + DeepSeek，提供公私有知识管理、3D 书架、关键词搜索、语义搜索和连续 AI 对话。

## Docker 启动

先打开 Docker Desktop，使用 Linux 容器。在项目根目录执行：

```powershell
# 首次迁移：只读导出现有数据库、生成独立的容器配置；重复运行保留已有文件
.\database_experiment\Scripts\python.exe scripts/prepare_docker.py

# 构建镜像并启动三个服务
docker compose --env-file .env.docker up -d --build

# 查看运行与健康状态
docker compose --env-file .env.docker ps
```

打开 <http://127.0.0.1:8080/>，管理页面为 <http://127.0.0.1:8080/manage>。账号与知识来自迁移快照；原来的本机数据库和 8000 服务不变。若安装后终端找不到 `docker`，请重新打开 PowerShell。

管理员工作台：<http://127.0.0.1:8080/admin>。采用与图书馆一致的浅色玻璃风格，管理公共知识的下架与恢复、分类与真实书架样式，并查看操作记录；私有知识不在管理范围内。旧 `/manage#/admin` 地址会跳转到新工作台。

- `Dockerfile`：网站与 Embedding 两个镜像的构建步骤，分别使用 `app`、`embedding` 构建目标。
- `compose.yaml`：管理网站、MySQL、模型服务及其网络、健康检查和数据卷。
- `.dockerignore`：控制构建上下文，密钥、虚拟环境、备份和模型权重不进入镜像。
- `.env.docker`：本机生成的容器配置，复制 DeepSeek 配置并生成独立数据库密码，不提交 Git。`--env-file` 用它替换 Compose 默认读取的 `.env`。
- `requirements-embedding.txt`：模型服务依赖；CPU 版 PyTorch 在 Dockerfile 中单独安装。

应用通过 `db:3306` 连接数据库，通过 `embedding:8011` 调用模型。数据库和模型端口不发布到宿主机。仅网站的容器端口 8000 映射到本机 8080。模型目录以只读方式挂载，复制项目到其他电脑时需要同时复制 `.models/bge-small-zh-v1.5/`。

容器通过 `scripts/start_docker.py` 启动网站，自动读取 Docker 网关地址并信任该代理传入的 HTTPS 信息，供宿主机上的穿透客户端转发使用；跨站请求检查继续生效。图书馆弹窗支持登录、注册，登录后留在图书馆；顶部“知识管理 / 平台管理”进入独立管理页面。

MySQL 数据保存在命名卷中，`data/docker-init/10-existing.sql` 只在全新数据卷首次初始化时导入。`.env.docker` 与迁移快照需妥善保存，不发到公开仓库。两套数据库运行后相互独立，修改不会自动同步。

```powershell
# 查看日志（Ctrl+C 退出查看，服务继续运行）
docker compose --env-file .env.docker logs -f app

# 停止并移除容器，保留数据库卷
docker compose --env-file .env.docker down

# 再次启动
docker compose --env-file .env.docker up -d

# 修改代码后重建应用镜像
docker compose --env-file .env.docker up -d --build app
```

日常停机不要给 `down` 加 `-v`，该参数会删除命名卷中的数据库数据。迁移时不要挂载根目录的 `database.sql`，它是旧实验脚本。

## 启动

配置保存在 `.env`，字段参考 `.env.example`。先启动 MySQL，再在项目根目录运行：

```powershell
.\database_experiment\Scripts\python.exe -m pip install -r requirement.txt
.\database_experiment\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

另开终端启动本地 Embedding（使用已有模型环境）：

```powershell
& 'C:\Users\xuxux\miniconda3\envs\anomaly_detection\python.exe' -u scripts/local_embedding_server.py
```

模型权重位于 `.models/bge-small-zh-v1.5/`。Embedding 环境使用 PyTorch、Transformers；重新下载模型还需要 huggingface_hub。后端通过 HTTP 调用模型服务。

## 入口

- 图书馆：<http://127.0.0.1:8000/>
- 注册与知识管理：<http://127.0.0.1:8000/manage>
- 接口文档：<http://127.0.0.1:8000/docs>
- 模型状态：<http://127.0.0.1:8011/health>

## 目录

- `app/`：后端接口、权限、数据模型、检索和 AI 调用。
- `static/`：图书馆与管理页面、字体和 Three.js。
- `scripts/`：模型服务、资料导入、索引和数据库备份工具。
- `data/runoob/`：学习笔记与来源链接。
- `data/backups/`：数据和文件恢复备份。
- `.models/`：本地模型权重。
- `database_experiment/`：后端 Python 虚拟环境。

## 数据维护

```powershell
# 导出现有数据库数据，并创建缺失表
.\database_experiment\Scripts\python.exe scripts/backup_database.py

# 重建导入笔记的本地向量索引（需要先启动 Embedding）
.\database_experiment\Scripts\python.exe scripts/import_runoob_notes.py --reindex
```

账号、知识和向量保存在 MySQL 中。`database.sql` 是原始实验建库脚本，包含重建数据库操作，日常启动无需执行。密钥、本地环境、模型和备份已排除在 Git 之外。字体、模型及第三方库的许可说明随资源保留。
