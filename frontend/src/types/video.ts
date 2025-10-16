/**
 * 视频相关数据类型定义
 */

// 视频标签类型
export interface VideoTag {
  name: string;
  query: string;
}

// 视频流地址类型
export interface StreamUrl {
  quality: string;
  url: string;
}

// 视频制作商/发行商
export interface VideoStudio {
  name: string;
  icon_url?: string;
  url?: string;
  query?: string;
}

// 视频类型
export interface VideoType {
  name: string;
  query?: string;
}

// 基础视频信息
export interface VideoBase {
  video_id: string;
  title: string;
  cover_url: string;
}

// Banner视频
export interface BannerVideo extends VideoBase {
  description?: string;
}

// 视频预览信息（详细视频）
export interface VideoPreview extends VideoBase {
  duration?: string;
  view_count?: number;
  like_rate?: string;
  like_count?: number;
  studio?: VideoStudio;
}

// 视频详情
export interface VideoDetail extends VideoPreview {
  description?: string;
  subtitle?: string;
  video_type?: VideoType;
  default_video_url?: string;
  stream_urls: StreamUrl[];
  tags: VideoTag[];
  upload_date?: string;
  views?: string;
  series_videos?: VideoPreview[];
  basic_related_videos?: VideoBase[];
  detailed_related_videos?: VideoPreview[];
}

// 视频分类数据
export interface VideoSection {
  title: string;
  search_suffix: string;
  videos: VideoBase[] | VideoPreview[];
}

// 首页数据响应
export interface HomeData {
  banners: BannerVideo;
  latest_videos: VideoSection[];
  new_arrivals_videos: VideoSection[];
  new_uploads_videos: VideoSection[];
  chinese_subtitle_videos: VideoSection[];
  popular_videos: VideoSection[];
  daily_rank_videos: VideoSection[];
  monthly_rank_videos: VideoSection[];
  error?: string;
}

// 视频评论
export interface VideoComment {
  comment_id?: string;
  user_avatar?: string;
  username: string;
  comment_time?: string;
  comment_content: string;
  like_count?: number;
  reply_count?: number;
}

// 评论回复
export interface CommentReply {
  user_avatar?: string;
  username: string;
  reply_time?: string;
  reply_content: string;
  like_count?: number;
}

// 搜索结果
export interface SearchResults {
  total_pages: number;
  page: number;
  has_next: boolean;
  basic_videos: VideoBase[];
  detailed_videos: VideoPreview[];
}

// 搜索组合选项
export interface SearchCombination {
  video_types: string[];
  tags: Record<string, string[]>;
  sort: string[];
} 