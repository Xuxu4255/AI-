import json
import math
from urllib.request import Request, urlopen

from app import config


def get_local_embeddings(texts, text_type="document"):
    if text_type not in ("document", "query"):
        raise ValueError("text_type 必须是 document 或 query")
    if not isinstance(texts, list) or not 1 <= len(texts) <= 8 or any(not isinstance(t, str) or not t.strip() for t in texts):
        raise ValueError("请提供 1 到 8 段非空文本")
    request = Request(config.LOCAL_EMBEDDING_URL.rstrip("/") + "/embeddings",
                      data=json.dumps({"texts": texts, "text_type": text_type}).encode("utf-8"),
                      headers={"Content-Type": "application/json"}, method="POST")
    with urlopen(request, timeout=30) as response:
        result = json.loads(response.read().decode("utf-8"))
    vectors = result.get("vectors")
    if (not isinstance(result.get("model"), str) or
            not result["model"].startswith(config.LOCAL_EMBEDDING_MODEL + "@") or
            result.get("dimension") != 512 or not isinstance(vectors, list) or len(vectors) != len(texts)):
        raise ValueError("本地模型标识或向量维度不符合预期")
    for vector in vectors:
        if (not isinstance(vector, list) or len(vector) != 512 or
                any(type(v) not in (int, float) or not math.isfinite(v) for v in vector) or
                abs(sum(v * v for v in vector) - 1) > 0.01):
            raise ValueError("本地模型返回了无效向量")
    return result


def get_embedding(text: str, text_type: str = "document"):
    if config.EMBEDDING_PROVIDER == "local":
        return get_local_embeddings([text], text_type)["vectors"][0]
    if config.EMBEDDING_PROVIDER != "aliyun":
        raise ValueError("未知 Embedding provider")
    return get_aliyun_embedding(text, text_type)


def get_aliyun_embedding(text: str, text_type: str = "document"):
    """把一段文字转换为向量。"""

    if not text.strip():
        raise ValueError("输入文字不能为空")

    if not config.DASHSCOPE_API_KEY:
        raise ValueError("没有配置阿里云 API Key")

    if not config.DASHSCOPE_WORKSPACE_ID:
        raise ValueError("没有配置阿里云百炼业务空间 ID")

    # 北京地域接口；业务空间 ID 要与 API Key 对应
    url = (
        f"https://{config.DASHSCOPE_WORKSPACE_ID}."
        "cn-beijing.maas.aliyuncs.com/api/v1/"
        "services/embeddings/text-embedding/text-embedding"
    )

    # 1. 准备要发送的数据
    body = {
        "model": config.EMBEDDING_MODEL,
        "input": {"texts": [text]},
        "parameters": {"text_type": text_type},
    }

    # 2. 创建 HTTP 请求
    request = Request(
        url=url,
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {config.DASHSCOPE_API_KEY}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    # 3. 发送请求并读取返回结果
    with urlopen(request, timeout=30) as response:
        result = json.loads(response.read().decode("utf-8"))

    # 4. 取出第一段文字对应的向量
    return result["output"]["embeddings"][0]["embedding"]
