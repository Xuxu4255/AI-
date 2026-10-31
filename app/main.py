from fastapi import FastAPI, Depends
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from app.security import require_admin, check_origin

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
    categories,
    ai,
    submissions,
)

app = FastAPI(dependencies=[Depends(check_origin)])

# 保持原有路由注册顺序，避免改变路径匹配行为。
app.include_router(auth.router)
app.include_router(knowledge.router)
app.include_router(qa.router, dependencies=[Depends(require_admin)])
app.include_router(feedback.router, dependencies=[Depends(require_admin)])
app.include_router(tags.router, dependencies=[Depends(require_admin)])
app.include_router(related_knowledge.router, dependencies=[Depends(require_admin)])
app.include_router(embeddings.router, dependencies=[Depends(require_admin)])
app.include_router(search.router)
app.include_router(logs.router, dependencies=[Depends(require_admin)])
app.include_router(categories.router)
app.include_router(ai.router)
app.include_router(submissions.router)

# 与 API 同源提供前端，避免单独启动前端服务器和配置跨域。
STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/", include_in_schema=False)
def frontend():
    return FileResponse(STATIC_DIR / "index.html")
