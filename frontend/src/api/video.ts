import request from '../utils/request.ts';
import { HomeData, VideoDetail, VideoComment, CommentReply, SearchResults, BannerVideo, SearchCombination } from '../types/video';

// 搜索参数接口
interface SearchParams {
  query?: string;
  genre?: string;
  tags?: string[];
  broad?: boolean;
  sort?: string;
  year?: number;
  month?: number;
  page?: number;
}

/**
 * 视频相关API服务
 */
export const VideoApi = {
  /**
   * 获取首页数据
   */
  getHomeData: async (): Promise<HomeData> => {
    try {
      const response = await request.get<HomeData>(`/videos/home`);
      return response.data;
    } catch (error) {
      console.error('获取首页数据失败:', error);
      // 创建一个空的BannerVideo对象
      const emptyBanner: BannerVideo = {
        video_id: '',
        title: '',
        cover_url: ''
      };
      
      return {
        banners: emptyBanner,
        latest_videos: [],
        new_arrivals_videos: [],
        new_uploads_videos: [],
        chinese_subtitle_videos: [],
        daily_rank_videos: [],
        monthly_rank_videos: [],
        error: '获取首页数据失败'
      };
    }
  },
  
  /**
   * 获取视频详情
   */
  getVideoDetail: async (videoId: string): Promise<VideoDetail | null> => {
    try {
      const response = await request.get<VideoDetail>(`/videos/detail/${videoId}`);
      return response.data;
    } catch (error) {
      console.error('获取视频详情失败:', error);
      return null;
    }
  },
  
  /**
   * 获取视频评论
   */
  getVideoComments: async (videoId: string): Promise<VideoComment[]> => {
    try {
      const response = await request.get<VideoComment[]>(`/videos/loadComments/${videoId}`);
      return response.data;
    } catch (error) {
      console.error('获取视频评论失败:', error);
      return [];
    }
  },
  
  /**
   * 获取评论回复
   */
  getCommentReplies: async (commentId: string): Promise<CommentReply[]> => {
    try {
      const response = await request.get<CommentReply[]>(`/videos/loadReplies/${commentId}`);
      return response.data;
    } catch (error) {
      console.error('获取评论回复失败:', error);
      return [];
    }
  },
  
  /**
   * 获取搜索组合选项
   */
  getSearchCombination: async (): Promise<SearchCombination> => {
    try {
      const response = await request.get<SearchCombination>(`/videos/search_combination`);
      return response.data;
    } catch (error) {
      console.error('获取搜索选项失败:', error);
      return {
        video_types: [],
        tags: {},
        sort: []
      };
    }
  },
  
  /**
   * 搜索视频
   * 
   * 说明：axios 默认会将数组参数序列化为 tags[0]=值1&tags[1]=值2 格式
   * 而 FastAPI 期望的格式是 tags=值1&tags=值2，因此需要特殊处理
   */
  searchVideos: async (params: SearchParams): Promise<SearchResults> => {
    try {
      // 创建 axios 请求配置
      const response = await request.get<SearchResults>('/videos/search', {
        params: params,
        // 添加 paramsSerializer 来自定义参数序列化
        paramsSerializer: {
          indexes: null // 这会使 axios 生成 tags=值1&tags=值2 格式而不是 tags[0]=值1
        }
      });
      return response.data;
    } catch (error) {
      console.error('搜索视频失败:', error);
      return {
        total_pages: 0,
        page: params.page || 1,
        has_next: false,
        basic_videos: [],
        detailed_videos: []
      };
    }
  },

  /**
   * 获取视频流URL
   * @param url 原始视频URL
   * @returns 视频流的完整URL
   */
  getStreamUrl: (url: string): string => {
    // 检查URL参数是否有效
    if (!url) {
      console.error('无效的视频URL参数:', url);
      return '';
    }
    
    // 确保URL不是路径而是完整的URL
    if (url.startsWith('/') || !url.includes('://')) {
      console.error('提供的URL不是完整URL:', url);
      return '';
    }

    // 视频播放器直接使用此URL，不经过axios，所以需要提供完整URL
    const API_BASE_URL = request.defaults.baseURL
    const streamUrl = `${API_BASE_URL}/videos/stream/proxy?url=${encodeURIComponent(url)}`;
    console.log('Generated stream URL:', streamUrl);
    return streamUrl;
  }
}; 