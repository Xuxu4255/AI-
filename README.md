# 知识图书馆

FastAPI + MySQL + 本地 BGE-small Embedding + DeepSeek，提供公私有知识管理、3D 书架、关键词搜索、语义搜索和连续 AI 对话。

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
