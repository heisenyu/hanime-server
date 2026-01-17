from pydantic import BaseModel
from typing import Optional
from loguru import logger
from pathlib import Path
import logging
import os
from dotenv import load_dotenv

import sys

# 尝试从项目根目录和当前目录加载环境变量
project_root = Path(__file__).parent.parent.parent  # 向上三级到项目根目录
backend_root = Path(__file__).parent.parent  # 向上两级到backend根目录
root_env_path = project_root / '.env'
local_env_path = backend_root / '.env'  # 后端目录下的.env

# 先尝试加载项目根目录的.env文件，然后尝试加载后端目录的.env文件
if root_env_path.exists():
    load_dotenv(dotenv_path=root_env_path)
    logger.info(f"从项目根目录加载.env文件: {root_env_path}")
elif local_env_path.exists():
    load_dotenv(dotenv_path=local_env_path)
    logger.info(f"从后端目录加载.env文件: {local_env_path}")
else:
    load_dotenv()  # 尝试默认加载
    logger.info("使用默认方式加载环境变量")


class Settings(BaseModel):
    # 基础设置
    APP_NAME: str = os.getenv("APP_NAME", "HanimeViewer")
    APP_DESCRIPTION: str = os.getenv("APP_DESCRIPTION", "HanimeViewer API服务")
    APP_VERSION: str = os.getenv("APP_VERSION", "1.0.0")
    RELOAD: bool = os.getenv("RELOAD", "False").lower() in ("true", "1", "t")
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))

    # 外部API设置
    HANIME_BASE_URL: str = os.getenv("HANIME_BASE_URL", "https://hanime1.me")

    # 文件设置
    DOWNLOAD_PATH: Path = Path(os.getenv("DOWNLOAD_PATH", str(backend_root / "downloads")))
    DB_PATH: Path = Path(os.getenv("DOWNLOAD_PATH", str(backend_root / "db")))
    COVER_PATH: Path = Path(os.getenv("COVER_PATH", str(backend_root / "downloads" / "covers")))

    # 爬虫设置
    USER_AGENT: str = os.getenv("USER_AGENT","Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")

    # 代理设置
    USE_PROXY: bool = os.getenv("USE_PROXY", "True").lower() in ("true", "1", "t")
    PROXY_URL: Optional[str] = os.getenv("PROXY_URL")

    # 视频下载专用代理设置
    USE_DOWNLOAD_PROXY: bool = os.getenv("USE_DOWNLOAD_PROXY", "False").lower() in ("true", "1", "t")
    DOWNLOAD_PROXY_URL: Optional[str] = os.getenv("DOWNLOAD_PROXY_URL", os.getenv("PROXY_URL"))

    CLOUDFLARE_BYPASS_SERVICE_URL: str = os.getenv("CLOUDFLARE_BYPASS_SERVICE_URL", "http://cf-bypass:8000")

    # 日志设置
    LOG_PATH: Path = Path(os.getenv("LOG_PATH", str(backend_root / "logs")))
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT: str = "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
    USE_LOG_FILE: bool = os.getenv("USE_LOG_FILE", "False").lower() in ("true", "1", "t")


settings = Settings()

# 打印下载目录信息
logger.info(f"下载目录: {settings.DOWNLOAD_PATH}")
logger.info(f"数据库目录: {settings.DB_PATH}")
logger.info(f"封面目录: {settings.COVER_PATH}")

# 确保下载目录存在
settings.DOWNLOAD_PATH.mkdir(exist_ok=True)
settings.DB_PATH.mkdir(exist_ok=True)
settings.COVER_PATH.mkdir(parents=True, exist_ok=True)


# 配置并初始化logger
logger.remove()  # 移除默认处理程序

# 基础处理程序配置
handlers = [
    {
        "sink": sys.stdout,
        "format": settings.LOG_FORMAT,
        "level": settings.LOG_LEVEL,
        "colorize": True,
    }
]

# 根据开关决定是否添加文件日志处理程序
if settings.USE_LOG_FILE:
    # 确保日志目录存在
    settings.LOG_PATH.mkdir(exist_ok=True)
    logger.info(f"日志目录: {settings.LOG_PATH}")
    handlers.append({
        "sink": str(settings.LOG_PATH / "app.log"),
        "format": settings.LOG_FORMAT,
        "level": settings.LOG_LEVEL,
        "rotation": "10 MB",
        "retention": "7 days",
        "compression": "zip",
        "enqueue": True,
    })

logger.configure(handlers=handlers)


# 配置uvicorn日志拦截
class InterceptHandler(logging.Handler):
    def emit(self, record):
        # 获取对应的Loguru级别
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # 找到调用者的帧
        frame, depth = logging.currentframe(), 2
        while frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


# 拦截uvicorn的日志
logging.basicConfig(handlers=[InterceptHandler()], level=0)

# 替换所有使用标准库logging的模块的处理程序
for _log in ['uvicorn', 'uvicorn.error', 'uvicorn.access', 'fastapi']:
    _logger = logging.getLogger(_log)
    _logger.handlers = [InterceptHandler()]
