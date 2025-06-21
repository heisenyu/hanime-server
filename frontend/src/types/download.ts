/**
 * 下载相关类型定义
 */

// 下载操作类型
export type DownloadActionType = 'pause' | 'resume' | 'cancel' | 'retry' | 'delete';

// 下载状态类型
export type DownloadStatus = 'pending' | 'downloading' | 'paused' | 'completed' | 'cancelled' | 'error';

// 下载分段类型
export interface DownloadSegment {
  start: number;
  end: number;
  downloaded: number;
  status: string;
}

// 下载进度类型
export interface DownloadProgress {
  video_id: string;
  filename: string;
  title?: string;
  cover_url?: string;
  total_size: number;
  downloaded: number;
  status: DownloadStatus;
  speed: number;
  error_message?: string;
  url: string;
  created_at: string;
  completed_at?: string;
  retry_count: number;
  max_retries: number;
  segments?: DownloadSegment[];
}

// 下载请求类型
export interface DownloadRequest {
  video_id: string;
  filename?: string;
  force?: boolean;
}

// 下载操作请求类型
export interface DownloadAction {
  video_id: string;
  action: DownloadActionType;
}

// 下载操作响应类型
export interface DownloadResponse {
  status: 'success' | 'error' | 'warning';
  message?: string;
  video_id?: string;
  existing_download?: DownloadProgress;
} 