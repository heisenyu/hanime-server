from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager

import uvicorn
import time

from app.api.routes import api_router
from app.config import settings, logger


def log_proxy_status():
    """记录代理状态"""
    if settings.USE_PROXY and settings.PROXY_URL:
        proxy_info = settings.PROXY_URL
        if "@" in proxy_info:
            parts = proxy_info.split("@")
            proxy_info = f"***@{parts[1]}"
        logger.info(f"代理服务已启用，代理地址: {proxy_info}")
    else:
        logger.info("代理服务未启用")

    if settings.USE_DOWNLOAD_PROXY:
        logger.info("下载视频代理服务已启用")
    else:
        logger.info("下载视频代理服务未启用")

    if settings.USE_CLOUDFLARE_BYPASS:
        logger.info("Cloudflare Bypass服务已启用")
    else:
        logger.info("Cloudflare Bypass服务未启用")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用启动和关闭时的事件处理"""
    logger.info(f"启动 {settings.APP_NAME} 服务")

    log_proxy_status()

    yield

    # 应用关闭时的清理工作可以放在这里


app = FastAPI(
    title=settings.APP_NAME,
    description=settings.APP_DESCRIPTION,
    version=settings.APP_VERSION,
    lifespan=lifespan
)
# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境请替换为实际的前端域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载下载目录
app.mount("/downloads", StaticFiles(directory=str(settings.DOWNLOAD_PATH)), name="downloads")


# 日志中间件
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    logger.info(f"{request.method} {request.url.path} - {response.status_code} ({process_time:.2f}s)")
    return response


# 异常处理
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "服务器内部错误，请稍后再试"}
    )


# 注册路由
app.include_router(api_router, prefix="/api")


@app.get("/")
async def root():
    return {"message": "欢迎使用HanimeViewer API"}


if __name__ == "__main__":
    # 配置日志拦截
    uvicorn.run(
        "main:app",  # 修改为直接引用当前文件中的app
        host=settings.HOST,  # 使用配置文件中的HOST设置
        port=settings.PORT,
        reload=settings.RELOAD,
        log_level=settings.LOG_LEVEL.lower(),
        access_log=False  # 禁用uvicorn的访问日志
    ) 