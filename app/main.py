from fastapi import FastAPI, Depends
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from app.security import check_origin

from app.routers import (
    auth,
    knowledge,
    search,
    categories,
    ai,
    spaces,
)

app = FastAPI(title='知识星海', version='2.0.0', dependencies=[Depends(check_origin)])

# 保持原有路由注册顺序，避免改变路径匹配行为。
app.include_router(auth.router)
app.include_router(knowledge.router)
# 旧审核、全库日志及向量导出接口不注册，避免旧权限绕过个人空间。
app.include_router(search.router)
app.include_router(categories.router)
app.include_router(ai.router)
app.include_router(spaces.router)


@app.on_event('startup')
def prepare_star_sea():
    from app.database import Base, engine
    # create_all 只增加缺失表，不删除或覆盖原记录。
    Base.metadata.create_all(engine)

# 与 API 同源提供前端，避免单独启动前端服务器和配置跨域。
STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/", include_in_schema=False)
def frontend():
    return FileResponse(STATIC_DIR / 'library.html', headers={'Cache-Control': 'no-cache'})


@app.get('/library', include_in_schema=False)
def library_preview():
    """可交互的 3D 图书馆初版，登录复用原有服务端会话。"""
    return FileResponse(STATIC_DIR / 'library.html', headers={'Cache-Control': 'no-cache'})


@app.get('/manage', include_in_schema=False)
def management():
    """知识编辑、注册与管理员操作入口。"""
    return FileResponse(STATIC_DIR / 'manage' / 'index.html', headers={'Cache-Control': 'no-cache'})
