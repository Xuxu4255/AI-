from fastapi import FastAPI

from app.routers import (
    auth,
    knowledge,
    qa,
    feedback,
    tags,
    related_knowledge,
    embeddings,
    search,
    logs,
)

app = FastAPI()

# 保持原有路由注册顺序，避免改变路径匹配行为。
app.include_router(auth.router)
app.include_router(knowledge.router)
app.include_router(qa.router)
app.include_router(feedback.router)
app.include_router(tags.router)
app.include_router(related_knowledge.router)
app.include_router(embeddings.router)
app.include_router(search.router)
app.include_router(logs.router)
