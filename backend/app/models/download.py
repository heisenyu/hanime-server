from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from enum import Enum
from datetime import datetime


class DownloadStatus(str, Enum):
    """下载状态枚举"""
    PENDING = "pending"
    DOWNLOADING = "downloading"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    ERROR = "error"


class DownloadSegment(BaseModel):
    """下载分段模型"""
    start: int
    end: int
    downloaded: int = 0
    status: str = DownloadStatus.PENDING


class DownloadRequest(BaseModel):
    """下载请求模型"""
    video_id: str
    filename: Optional[str] = None
    force: Optional[bool] = False


class DownloadAction(BaseModel):
    """下载操作模型"""
    video_id: str
    action: str  # 'pause', 'resume', 'cancel', 'retry', 'delete'


class DownloadProgress(BaseModel):
    """下载进度模型"""
    video_id: str
    filename: str
    title: Optional[str] = None
    cover_url: Optional[str] = None
    total_size: int
    downloaded: int
    status: str
    speed: float  # bytes per second
    error_message: Optional[str] = None
    url: str = ""
    created_at: datetime
    completed_at: Optional[datetime] = None
    retry_count: int = 0
    max_retries: int = 3
    segments: Optional[List[DownloadSegment]] = None


class DownloadConfig(BaseModel):
    """下载配置模型"""
    chunk_size: int = 1024 * 1024 * 16  # 16MB
    buffer_size: int = 1024 * 1024 * 4  # 4MB
    max_segments: int = 4
    min_segment_size: int = 40 * 1024 * 1024  # 40MB
    max_retries: int = 3
    timeout: float = 30.0
    progress_update_interval: float = 0.5 