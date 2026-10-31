# 本地 Embedding 实验

模型：BAAI/bge-small-zh-v1.5，官方地址 https://huggingface.co/BAAI/bge-small-zh-v1.5 ，MIT 许可证。
权重与配置位于 `.models/bge-small-zh-v1.5/`（已加入 Git 忽略）。下载时固定实际仓库 revision，记录在该目录 MODEL_INFO.json。

本次使用机器已有的 Python 3.13 环境，不向该环境安装或升级依赖，也不改动项目的 Python 3.8 后端。

```powershell
& 'C:\Users\xuxux\miniconda3\envs\anomaly_detection\python.exe' scripts/local_embedding.py
```

该命令使用 local_files_only 离线加载已下载的权重，完成三条示例知识的语义排序。首次下载可以显式增加 `--download`（会请求 Hugging Face 官方站点）。运行环境本次检测到 torch 2.12.1+cu130、transformers 5.16.1、huggingface_hub 1.29.0；其他电脑需自行建立兼容 Python 环境并安装这些依赖。

实现采用模型作者说明的 CLS pooling、L2 归一化和查询指令，输出 512 维向量；文档不加查询指令。测试默认使用 CPU，模型在 LocalEmbedder 实例构造时加载一次，encode 重复使用。输入最多 512 tokenizer tokens，超过会截断；正式索引长文时需要先设计切分。

测试结果：`tests/local-embedding-smoke.json`。这是一个独立的最小推理测试，不是完整搜索效果评测。得分是相似度，不是正确概率，也不能根据这一个例子确定拒答阈值。

当前 `app/services/embedding.py` 仍是阿里云适配器，网站尚未切换到本地模型。下一步需要考虑 Python 3.8 后端和新模型环境的隔离方式（例如仅监听本地的 Embedding 服务），再给 64 条知识建立索引并实现搜索接口。不要让每次请求都重新加载模型或重新下载权重。

## 本地服务和数据库索引（已实现）

本地服务已在 `http://127.0.0.1:8011` 运行，启动时加载一次模型，使用锁串行处理推理。仅监听 loopback，拒绝浏览器 Origin 和非本机 Host；不开放 CORS。服务最多接收 8 段文本、单段 512 tokenizer tokens，超长返回 422，不静默截断。适用于本机开发，不是公网部署服务。

手动启动（项目根目录，需要保持进程运行）：

```powershell
& 'C:\Users\xuxux\miniconda3\envs\anomaly_detection\python.exe' -u scripts/local_embedding_server.py
```

Python 3.8 后端通过 `app/services/embedding.py` 的 HTTP 适配器调用它，无需在后端安装 PyTorch。`.env` 已切换 `EMBEDDING_PROVIDER=local` 和 `LOCAL_EMBEDDING_URL=http://127.0.0.1:8011`；阿里云 Key 保留但本地模式不使用。后端需要重启才会读取新的环境变量。`EMBEDDING_MODEL` 仍用于阿里云配置，本地模型标识由服务返回，包含固定权重 revision。

已为 64 条已发布知识写入本地模型向量。重复运行下面命令会跳过同版本模型、正文未变化的知识；正文变化时新增一条向量记录。脚本使用单个数据库事务，任一批次失败则回滚本次写入。

```powershell
.\database_experiment\Scripts\python.exe scripts/index_local_embeddings.py
.\database_experiment\Scripts\python.exe scripts/check_local_index.py
```

文本构造在 `app/services/indexing.py`，当前为标题加正文，排除种子资料末尾的性质说明和来源链接。数据库保留实际编码文本；未来搜索必须检查模型版本、最新记录和正文新鲜度，不使用草稿或过期索引。发布/修改知识后的自动重建尚未实现，需要手动运行索引脚本。

当前验证：64 条 512 维非零归一化向量；二次运行新增 0、跳过 64；本地服务错误输入与客户端向量校验通过。真实的 3 个口语化查询中，栈和队列命中第一，二分查找未命中前三；命中率 2/3 仅是小样本观察，不可当作整体准确率，尚无校准过的拒答阈值。结果记录于 `tests/local-index-smoke.json`。

网站 `/ai/search` 接口仍未接入，不会因为本地服务启动就自动拥有语义搜索能力。下一步需要实现带权限与索引新鲜度过滤的搜索接口，再评估关键词与向量融合、重排和阈值。

## 网站语义搜索已接通

POST /ai/search 已实现本地向量检索与 BM25 融合排序，并验证发布状态、模型版本、正文新鲜度和数字向量。新建的搜索快照表用于可选解释的用户归属与来源校验。网站直接选择“语义增强搜索”即可使用。

知识发布及修改已发布正文时会尝试更新单条向量；失败时返回 pending，避免使用旧正文索引。批量索引脚本仍可用于补建。最新用法见 FRONTEND.md。
