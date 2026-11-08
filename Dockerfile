# 一个 Dockerfile，分别构建网站和模型服务两个镜像。
FROM python:3.11-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1
WORKDIR /app
RUN useradd --create-home --uid 10001 library

FROM base AS app
COPY requirement.txt ./
RUN pip install -r requirement.txt
COPY app ./app
COPY static ./static
COPY scripts ./scripts
COPY data/runoob ./data/runoob
RUN mkdir -p data/backups && chown -R library:library /app
USER library
EXPOSE 8000
CMD ["python", "scripts/start_docker.py"]

FROM base AS embedding
# CPU 版 PyTorch：不把 CUDA 运行库带进镜像。
RUN pip install torch==2.12.1 --index-url https://download.pytorch.org/whl/cpu
COPY requirements-embedding.txt ./
RUN pip install -r requirements-embedding.txt
COPY scripts/local_embedding.py scripts/local_embedding_server.py ./scripts/
ENV HF_HUB_OFFLINE=1 \
    TRANSFORMERS_OFFLINE=1 \
    HF_HUB_DISABLE_TELEMETRY=1
USER library
EXPOSE 8011
CMD ["python", "scripts/local_embedding_server.py", "--host", "0.0.0.0"]
