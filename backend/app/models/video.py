from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


class VideoTag(BaseModel):
    """标签模型"""
    name: str
    query: str = ""


class VideoStreamUrl(BaseModel):
    """视频流URL模型"""
    quality: str
    url: str


class VideoStudio(BaseModel):
    """视频制作商/发行商模型"""
    name: str
    icon_url: Optional[str] = ""
    url: Optional[str] = ""
    query: Optional[str] = ""


class VideoType(BaseModel):
    """视频类型模型"""
    name: str
    query: Optional[str] = ""


class VideoBase(BaseModel):
    """视频基础模型"""
    video_id: str
    title: str
    cover_url: Optional[str] = ""


# 首页Banner视频模型
class BannerVideo(VideoBase):
    description: Optional[str] = ""


class VideoPreview(VideoBase):
    """视频预览模型，用于列表展示"""
    duration: Optional[str] = ""
    view_count: Optional[int] = 0
    like_rate: Optional[str] = ""
    like_count: Optional[int] = 0
    studio: Optional[VideoStudio] = None


class VideoDetail(VideoPreview):
    """视频详情模型"""
    description: Optional[str] = ""
    subtitle: Optional[str] = ""
    upload_date: Optional[datetime] = ""
    video_type: Optional[VideoType] = None
    default_video_url: Optional[str] = ""
    stream_urls: List[VideoStreamUrl] = []
    tags: List[VideoTag] = []
    series_videos: Optional[List[VideoPreview]] = []
    # 基础相关视频（仅包含基本信息）
    basic_related_videos: List[VideoBase] = Field(default_factory=list, description="基础相关视频推荐，仅包含基本信息")
    # 详细相关视频（包含更多详细信息）
    detailed_related_videos: List[VideoPreview] = Field(default_factory=list, description="详细相关视频推荐，包含更多信息如时长、点赞等")


class HomeData(BaseModel):
    """首页数据模型"""
    banners: BannerVideo = None
    latest_videos: List[Dict[str, Any]] = []
    new_arrivals_videos: List[Dict[str, Any]] = []
    new_uploads_videos: List[Dict[str, Any]] = []
    popular_videos: List[Dict[str, Any]] = []
    ai_generated_videos: List[Dict[str, Any]] = []
    bubble_tea_videos: List[Dict[str, Any]] = []
    error: Optional[str] = None


class VideoComment(BaseModel):
    """视频评论模型"""
    comment_id: Optional[str] = ""
    user_avatar: Optional[str] = ""
    username: str
    comment_time: Optional[str] = ""
    comment_content: str
    like_count: Optional[int] = 0
    reply_count: Optional[int] = 0


class CommentReply(BaseModel):
    """评论回复模型"""
    user_avatar: Optional[str] = ""
    username: str
    reply_time: Optional[str] = ""
    reply_content: str
    like_count: Optional[int] = 0


class SearchCombination(BaseModel):
    """搜索组合模型"""
    video_types: List[str] = Field(default_factory=list, description="视频类型选项")
    tags: Dict[str, List[str]] = Field(default_factory=dict, description="按分类组织的标签选项")
    sort: List[str] = Field(default_factory=list, description="排序方式选项")


class SearchResults(BaseModel):
    """搜索结果模型"""
    total_pages: int = 0
    page: int = 1
    basic_videos: List[VideoBase] = []
    detailed_videos: List[VideoPreview] = []
    has_next: bool = False
