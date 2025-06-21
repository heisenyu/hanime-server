<template>
  <div class="page-container">
    <!-- 视频播放区域 -->
    <div class="video-player-container">
      <VideoPlayer
        :stream-urls="videoDetail.stream_urls"
        :default-video-url="videoDetail.default_video_url"
        :cover-url="videoDetail.cover_url"
        :title="videoDetail.title"
        :show-debug-info="showDebugInfo"
        @play-started="handlePlayStarted"
        @play-error="handlePlayError"
      />
    </div>

    <!-- 标签页切换 -->
    <div class="tab-container">
      <div class="tab-header">
        <div class="tab" :class="{ active: currentTab === 'intro' }" @click="switchTab('intro')">简介</div>
        <div class="tab" :class="{ active: currentTab === 'comments' }" @click="switchTab('comments')">
          评论 <span class="comment-count-badge">{{ commentCount }}</span>
        </div>
      </div>
    </div>

    <!-- 视频基本信息 -->
    <div class="video-info-container" v-show="currentTab === 'intro'">
      <div class="video-header">
        <!-- 视频作者信息 -->
        <div class="video-author" v-if="videoDetail.studio">
          <div class="author-avatar">
            <img :src="videoDetail.studio.icon_url || defaultAvatarUrl" alt="作者头像"
                 referrerpolicy="no-referrer" loading="lazy" @error="handleImageError"/>
          </div>
          <div class="author-info">
            <div class="author-name" @click="goToSearch(videoDetail.studio.query)" :class="{'clickable': !!videoDetail.studio.query}">{{ videoDetail.studio.name }}</div>
            <div class="author-type" v-if="videoDetail.video_type" @click="goToSearch(videoDetail.video_type.query)" :class="{'clickable': !!videoDetail.video_type.query}">{{ videoDetail.video_type.name }}</div>
          </div>
        </div>

        <h1 class="video-title">{{ videoDetail.title }}</h1>

        <!-- 副标题显示 -->
        <p v-if="videoDetail.subtitle" class="video-subtitle">{{ videoDetail.subtitle }}</p>

        <div class="video-meta">
          <div class="meta-item">
            <el-icon><View /></el-icon>
            <span>{{ formatViewCount(videoDetail.view_count || 0) }} 次观看</span>
            <span class="meta-separator">|</span>
            <el-icon><Calendar /></el-icon>
            <span>{{ formatDate(videoDetail.upload_date) }}</span>
          </div>
          <div class="video-actions">
            <!-- 视频下载按钮组件 -->
            <el-button type="primary" :loading="isDownloading" @click="handleDownload">
              <el-icon><Download /></el-icon> 下载
            </el-button>
            
            <!-- 如果有系列，则添加一个系列下载按钮 -->
            <el-button v-if="hasSeriesVideos" type="success" @click="openSeriesDialog">
              <el-icon><VideoCamera /></el-icon> 系列下载
            </el-button>
          </div>
        </div>
      </div>

      <!-- 视频描述 -->
      <div class="video-description" v-if="videoDetail.description">
        <p :class="{'collapsed': !isDescriptionExpanded}" class="description-content">
          {{ videoDetail.description }}
        </p>
        <div class="expand-button" @click="toggleDescription">
          {{ isDescriptionExpanded ? '收起' : '展开' }}
          <el-icon>
            <component :is="isDescriptionExpanded ? 'ArrowUp' : 'ArrowDown'" />
          </el-icon>
        </div>
      </div>

      <!-- 视频标签 -->
      <div class="video-tags-container" v-if="videoDetail.tags && videoDetail.tags.length">
        <h3 class="section-title">TAGs</h3>
        <div class="tags-list">
          <el-tag
              v-for="tag in videoDetail.tags"
              :key="tag.name"
              size="default"
              effect="dark"
              class="tag-item"
              @click="goToSearch(tag.query)"
          >
            {{ tag.name }}
          </el-tag>
        </div>
      </div>
    </div>

    <!-- 评论区 -->
    <VideoComments
      v-show="currentTab === 'comments'"
      :video-id="videoDetail.video_id"
      @comment-count-updated="updateCommentCount"
      @debug-log="addDebugLog"
    />

    <!-- 系列视频 -->
    <video-section
        v-if="videoDetail.series_videos && videoDetail.series_videos.length"
        :title="'系列影片'"
        :videos="videoDetail.series_videos"
        thumbnail-class="portrait"
        item-class="latest-horizontal-item"
        @video-click="goToVideo"
    />

    <!-- 相关视频 -->
    <div class="related-section" v-if="(videoDetail.basic_related_videos && videoDetail.basic_related_videos.length) || (videoDetail.detailed_related_videos && videoDetail.detailed_related_videos.length)">
      <h3 class="section-title">相关影片</h3>
      <div v-if="videoDetail.basic_related_videos && videoDetail.basic_related_videos.length" class="video-grid-basic">
        <video-card
            v-for="video in videoDetail.basic_related_videos"
            :key="video.video_id"
            :video="video"
            :custom-class="'video-card basic-video-card'"
            thumbnail-class="portrait"
            :show-play-icon="true"
            @click="goToVideo(video.video_id)"
        />
      </div>
      <div v-if="videoDetail.detailed_related_videos && videoDetail.detailed_related_videos.length" class="video-grid-detailed">
        <video-card
            v-for="video in videoDetail.detailed_related_videos"
            :key="video.video_id"
            :video="video"
            :custom-class="'video-card wide-video-card'"
            thumbnail-class="landscape"
            :single-line-title="true"
            :show-play-icon="true"
            @click="goToVideo(video.video_id)"
        />
      </div>
    </div>

    <!-- 系列视频选择对话框 -->
    <el-dialog
      v-model="seriesDialogVisible" 
      title="选择系列视频下载" 
      width="80%"
      class="series-download-dialog"
    >
      <div class="series-selection">
        <div class="selection-header">
          <el-checkbox v-model="selectAll" @change="handleSelectAllChange">全选</el-checkbox>
          <div class="selection-count">已选择：{{ selectedSeries.length }} / {{ videoDetail.series_videos?.length || 0 }}</div>
            </div>
        
        <div class="series-grid">
          <div v-for="(video, index) in videoDetail.series_videos" 
               :key="video.video_id" 
               class="series-item"
          >
            <el-checkbox v-model="selectedSeriesMap[video.video_id]" @change="updateSelectedSeries"></el-checkbox>
            <div class="series-card" 
                 :class="{ 
                    'selected': selectedSeriesMap[video.video_id],
                    'already-downloaded': isVideoAlreadyDownloaded(video.video_id)
                 }" 
                 @click="toggleSeriesSelection(video.video_id)"
            >
              <div class="series-thumbnail">
                <img :src="video.cover_url" :alt="video.title" loading="lazy" referrerpolicy="no-referrer" />
                <span v-if="video.duration" class="duration-badge">{{ video.duration }}</span>
                <span v-if="isVideoAlreadyDownloaded(video.video_id)" class="download-status-badge">已下载</span>
      </div>
              <div class="series-info">
                <div class="series-title">{{ video.title }}</div>
        </div>
        </div>
      </div>
        </div>
      </div>
      
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="seriesDialogVisible = false">取消</el-button>
          <el-button type="primary" :disabled="!selectedSeries.length" @click="downloadSelectedSeries">
            下载已选择 ({{ selectedSeries.length }})
          </el-button>
        </div>
      </template>
    </el-dialog>

    <!-- 返回顶部按钮 -->
    <el-backtop :right="20" :bottom="20"></el-backtop>
  </div>
</template>

<script lang="ts">
import {defineComponent, ref, onMounted, onActivated, watch, computed, h} from 'vue';
import {useRoute, useRouter} from 'vue-router';
import {VideoApi} from '../api/video';
import {VideoDetail, VideoPreview} from '../types/video';
import VideoCard from '../components/VideoCard.vue';
import VideoSection from '../components/VideoSection.vue';
import { ElMessage, ElNotification, ElMessageBox } from 'element-plus';
import VideoPlayer from './VideoPlayer.vue';
import VideoComments from './VideoComments.vue';
import { View, Calendar, ArrowUp, ArrowDown, Download, VideoCamera, Collection, InfoFilled } from '@element-plus/icons-vue';
import { useDownloadStore } from '../stores/download';
import defaultAvatar from '../assets/default-avatar.svg';

export default defineComponent({
  name: 'VideoDetailPage',
  components: {
    VideoCard,
    VideoSection,
    VideoPlayer,
    VideoComments,
    View,
    Calendar,
    ArrowUp,
    ArrowDown,
    Download,
    VideoCamera,
    Collection,
    InfoFilled
  },
  setup() {
    const route = useRoute();
    const router = useRouter();
    const loading = ref(true);
    const error = ref(false);
    const commentCount = ref(0);
    const currentTab = ref('intro');
    const isDescriptionExpanded = ref(false);
    const isDownloading = ref(false);
    const seriesDialogVisible = ref(false);
    const selectAll = ref(false);
    const selectedSeries = ref<string[]>([]);
    const selectedSeriesMap = ref<Record<string, boolean>>({});
    // const showDebugInfo = ref('development');
    const showDebugInfo = ref(false); // 改为布尔值，false表示不显示调试信息，true表示显示
    const debugLogs = ref<string[]>([]);

    // 视频详情数据
    const videoDetail = ref<VideoDetail>({
      video_id: '',
      title: '',
      cover_url: '',
      description: '',
      views: '',
      duration: '',
      upload_date: '',
      tags: [],
      stream_urls: [],
      basic_related_videos: [],
      detailed_related_videos: []
    });

    // 计算是否有系列视频
    const hasSeriesVideos = computed(() => {
      return videoDetail.value.series_videos && videoDetail.value.series_videos.length > 0;
    });

    // 使用下载状态管理
    const downloadStore = useDownloadStore();
    
    // 默认头像URL
    const defaultAvatarUrl = ref(defaultAvatar);
    
    // 处理头像加载错误
    const handleImageError = (event: Event) => {
      const imgElement = event.target as HTMLImageElement;
      imgElement.src = defaultAvatar;
    };

    // 获取用于下载的文件名
    const getDownloadFileName = (video: VideoDetail | undefined) => {
      if (!video) return 'video';
      // 优先使用副标题作为文件名，如果没有副标题，则使用标题
      return video.subtitle || video.title || 'video';
    };

    // 调试日志函数
    const addDebugLog = (message: string) => {
      if (showDebugInfo.value === false) return;
      
      debugLogs.value.push(`[${new Date().toLocaleTimeString()}] ${message}`);
      console.log(`[Debug] ${message}`);
    };

    // 处理下载命令
    const handleDownload = async () => {
      try {
        // 先检查视频是否已经下载
        if (isVideoAlreadyDownloaded(videoDetail.value.video_id)) {
          ElMessageBox.confirm(
            '该视频已经下载过，是否重新下载？',
            '确认操作',
            {
              confirmButtonText: '重新下载',
              cancelButtonText: '取消',
              type: 'warning'
            }
          ).then(async () => {
            await startDownloadProcess(true);
          }).catch(() => {
            ElMessage.info('已取消下载');
          });
          return;
        }
        
        // 视频未下载，直接开始下载
        await startDownloadProcess(false);
      } catch (error) {
        console.error('下载出错:', error);
        ElMessage.error('下载请求失败');
        isDownloading.value = false;
      }
    };
    
    // 开始下载流程
    const startDownloadProcess = async (force: boolean) => {
      isDownloading.value = true;
      
      try {
        // 直接下载视频（使用最高清晰度）
        const result = await downloadStore.startDownload(videoDetail.value.video_id, force);
        
        if (result === true) {
      ElMessage.success('开始下载视频');
          // 创建可点击通知
          ElNotification({
            title: '下载已开始',
            message: h('div', {
              class: 'clickable-notification',
              onClick: () => router.push('/downloads')
            }, [
              h('p', '可在下载管理页面查看详情'),
              h('el-button', {
                size: 'small',
                type: 'primary',
                style: 'margin-top: 8px; width: 100%;'
              }, '前往下载管理')
            ]),
            type: 'success',
            duration: 5000,
            position: 'bottom-right'
          });
        } else if (result && result.status === 'warning') {
          // 视频已经下载过，询问是否重新下载
          ElMessageBox.confirm(
            '该视频已下载过，是否重新下载？',
            '确认操作',
            {
              confirmButtonText: '重新下载',
              cancelButtonText: '取消',
              type: 'warning'
            }
          ).then(async () => {
            await downloadStore.startDownload(videoDetail.value.video_id, true);
            ElMessage.success('开始重新下载');
          }).catch(() => {
            ElMessage.info('已取消下载');
          });
        }
      } finally {
        isDownloading.value = false;
      }
    };

    // 判断是否为推荐质量
    const isRecommendedQuality = (url: any): boolean => {
      if (!url || !videoDetail.value.stream_urls || videoDetail.value.stream_urls.length === 0) {
        return false;
      }
      
      // 如果只有一个选项，它就是推荐的
      if (videoDetail.value.stream_urls.length === 1) {
        return true;
      }
      
      // 如果有多个选项，选择最高质量的作为推荐
      const sortedUrls = [...videoDetail.value.stream_urls].sort((a, b) => {
        if (a.size && b.size) {
          return b.size - a.size;
        }
        return 0;
      });
      
      // 选择最高的选项
      const highestIndex = 0;
      return url === sortedUrls[highestIndex];
    };

    // 更新评论数
    const updateCommentCount = (count: number) => {
      commentCount.value = count;
      addDebugLog(`评论数已更新: ${count}`);
    };

    const fetchVideoDetail = async () => {
      const videoId = route.params.id as string;
      
      if (!videoId) {
        addDebugLog('无效的视频ID');
        error.value = true;
        loading.value = false;
        return Promise.reject('无效的视频ID');
      }

      try {
        loading.value = true;
        error.value = false;

        const response = await VideoApi.getVideoDetail(videoId);

        if (response) {
          videoDetail.value = response;
          
          debugLogs.value = [];
          addDebugLog(`视频详情加载成功: ${response.title}`);
          return Promise.resolve(response);
        } else {
          error.value = true;
          return Promise.reject('获取视频详情失败');
        }
      } catch (err) {
        addDebugLog(`获取视频详情失败: ${err}`);
        error.value = true;
        return Promise.reject(err);
      } finally {
        loading.value = false;
      }
    };

    // 处理播放开始事件
    const handlePlayStarted = () => {
      addDebugLog('视频开始播放');
    };

    // 处理播放错误事件
    const handlePlayError = (errorMessage: string) => {
      addDebugLog(`播放错误: ${errorMessage}`);
      ElMessage.error(`播放失败: ${errorMessage}`);
    };

    const formatDate = (dateString: string) => {
      if (!dateString) return '';
      const date = new Date(dateString);
      return date.toLocaleDateString('zh-CN', {
        year: 'numeric',
        month: 'numeric',
        day: 'numeric'
      });
    };

    const formatViewCount = (count: number): string => {
      if (!count) return '0';
      if (count >= 10000) {
        return `${(count / 10000).toFixed(1)}万`;
      } else if (count >= 1000) {
        return `${(count / 1000).toFixed(1)}千`;
      }
      return count.toString();
    };

    // 格式化文件大小
    const formatFileSize = (bytes: number): string => {
      if (!bytes || bytes === 0) return '未知大小';
      
      const units = ['B', 'KB', 'MB', 'GB', 'TB'];
      let size = bytes;
      let unitIndex = 0;
      
      while (size >= 1024 && unitIndex < units.length - 1) {
        size /= 1024;
        unitIndex++;
      }
      
      return `${size.toFixed(2)} ${units[unitIndex]}`;
    };

    const goToVideo = (videoId: string) => {
      if (videoId === videoDetail.value.video_id) return;
      router.push(`/video/${videoId}`);
    };

    // 切换标签页
    const switchTab = (tab: string) => {
      currentTab.value = tab;
    };

    // 展开/收起视频描述
    const toggleDescription = () => {
      isDescriptionExpanded.value = !isDescriptionExpanded.value;
    };

    const goToSearch = (query: string) => {
      if (query) {
        router.push(`/search?${query}`);
      }
    };

    // 处理全选/取消全选
    const handleSelectAllChange = () => {
      if (selectAll.value) {
        // 全选时只选择没有下载过的视频
        const notDownloadedVideos = videoDetail.value.series_videos
          .filter(video => !isVideoAlreadyDownloaded(video.video_id))
          .map(video => video.video_id);
        
        selectedSeries.value = notDownloadedVideos;
        // 更新选择状态映射
        selectedSeriesMap.value = {};
        notDownloadedVideos.forEach(id => {
          selectedSeriesMap.value[id] = true;
        });
      } else {
        selectedSeries.value = [];
        selectedSeriesMap.value = {};
      }
    };

    // 更新选中的系列视频
    const updateSelectedSeries = () => {
      selectedSeries.value = Object.keys(selectedSeriesMap.value).filter(
        videoId => selectedSeriesMap.value[videoId]
      );
      
      // 更新全选状态
      if (videoDetail.value.series_videos) {
        const notDownloadedCount = videoDetail.value.series_videos.filter(
          video => !isVideoAlreadyDownloaded(video.video_id)
        ).length;
        
        selectAll.value = selectedSeries.value.length === notDownloadedCount && notDownloadedCount > 0;
      }
    };

    // 切换视频选中状态
    const toggleSeriesSelection = (videoId: string) => {
      // 如果视频已经下载过，则不允许选择
      if (isVideoAlreadyDownloaded(videoId)) {
        ElMessage.info('该视频已经下载过');
        return;
      }
      
      selectedSeriesMap.value[videoId] = !selectedSeriesMap.value[videoId];
      updateSelectedSeries();
    };
    
    // 打开系列视频选择对话框
    const openSeriesDialog = () => {
      if (!hasSeriesVideos.value || !videoDetail.value.series_videos) {
        ElMessage.warning('该视频没有系列内容');
        return;
      }
      
      seriesDialogVisible.value = true;
      selectAll.value = false;
      selectedSeries.value = [];
      selectedSeriesMap.value = {};
      
      // 初始化所有视频为未选中状态
      if (videoDetail.value.series_videos) {
        videoDetail.value.series_videos.forEach(video => {
          selectedSeriesMap.value[video.video_id] = false;
        });
    
        // 显示已下载状态
        highlightDownloadedSeriesVideos();
      }
    };

    // 下载选中的系列视频
    const downloadSelectedSeries = async () => {
      if (selectedSeries.value.length === 0) {
        ElMessage.warning('请先选择要下载的视频');
        return;
      }
      
      try {
        // 立即设置加载状态，但很快就会释放
        isDownloading.value = true;
        
        // 获取要下载的视频ID列表（过滤掉已下载的）
        const videosToDownload = selectedSeries.value.filter(
          videoId => !isVideoAlreadyDownloaded(videoId)
        );
        
        const alreadyDownloadedCount = selectedSeries.value.length - videosToDownload.length;
        
        // 构建初始结果消息
        let resultMessage = '';
        if (videosToDownload.length > 0) {
          resultMessage += `已将 ${videosToDownload.length} 个视频添加到下载队列`;
        }
        if (alreadyDownloadedCount > 0) {
          resultMessage += resultMessage ? '，' : '';
          resultMessage += `${alreadyDownloadedCount} 个视频已下载，已跳过`;
        }
        
        // 先关闭对话框，避免阻塞UI
        seriesDialogVisible.value = false;
        
        // 显示初始成功消息
        if (videosToDownload.length > 0) {
          ElMessage.success(resultMessage);
          
          // 显示通知
          ElNotification({
            title: '系列下载已添加',
            message: h('div', {
              class: 'clickable-notification',
              onClick: () => router.push('/downloads')
            }, [
              h('p', resultMessage),
              h('el-button', {
                size: 'small',
                type: 'primary',
                style: 'margin-top: 8px; width: 100%;'
              }, '前往下载管理')
            ]),
            type: 'success',
            duration: 5000,
            position: 'bottom-right'
          });
        } else if (alreadyDownloadedCount > 0) {
          ElMessage.info(resultMessage);
        }
        
        // 异步处理下载，不阻塞UI
        if (videosToDownload.length > 0) {
          // 使用Promise.all并行发送所有下载请求
          Promise.all(
            videosToDownload.map(videoId => 
              downloadStore.startDownload(videoId, false)
                .catch(error => {
                  console.error(`下载视频 ${videoId} 失败:`, error);
                  return { status: 'error', videoId };
                })
            )
          )
          .then(results => {
            // 这里可以处理所有下载请求的结果，但不会阻塞用户界面
            const successCount = results.filter(result => result === true).length;
            const failedCount = results.filter(result => result && result.status === 'error').length;
            
            console.log(`系列下载结果: 成功=${successCount}, 失败=${failedCount}, 已存在=${alreadyDownloadedCount}`);
          });
        }
      } catch (error) {
        console.error('系列下载失败:', error);
        ElMessage.error('系列下载失败，请稍后重试');
      } finally {
        // 快速释放加载状态，不等待所有下载完成
        isDownloading.value = false;
      }
    };

    // 判断视频是否已经下载
    const isVideoAlreadyDownloaded = (videoId: string): boolean => {
      return downloadStore.isDownloaded(videoId);
    };
    
    // 显示已下载的系列视频
    const highlightDownloadedSeriesVideos = () => {
      if (videoDetail.value.series_videos) {
        // 显示已下载的视频数量
        const downloadedCount = videoDetail.value.series_videos.filter(
          video => isVideoAlreadyDownloaded(video.video_id)
        ).length;
        
        if (downloadedCount > 0) {
          ElMessage.info(`系列中有 ${downloadedCount} 个视频已下载`);
        }
      }
    };

    onMounted(() => {
      fetchVideoDetail();
    });

    // 当从缓存激活组件时更新视频ID
    onActivated(() => {
      const videoId = route.params.id as string;
      if (videoId !== videoDetail.value.video_id) {
        fetchVideoDetail();
      }
    });

    // 添加路由参数监听
    watch(() => route.params.id, (newId) => {
      if (newId && newId !== videoDetail.value.video_id) {
        fetchVideoDetail();
      }
    });

    return {
      loading,
      error,
      videoDetail,
      commentCount,
      currentTab,
      showDebugInfo,
      debugLogs,
      seriesDialogVisible,
      selectAll,
      selectedSeries,
      selectedSeriesMap,
      isDownloading,
      handleDownload,
      formatDate,
      formatViewCount,
      formatFileSize,
      fetchVideoDetail,
      goToVideo,
      handlePlayStarted,
      handlePlayError,
      switchTab,
      isDescriptionExpanded,
      toggleDescription,
      addDebugLog,
      updateCommentCount,
      goToSearch,
      hasSeriesVideos,
      openSeriesDialog,
      handleSelectAllChange,
      updateSelectedSeries,
      downloadSelectedSeries,
      getDownloadFileName,
      toggleSeriesSelection,
      isVideoAlreadyDownloaded,
      startDownloadProcess,
      defaultAvatarUrl,
      handleImageError,
      highlightDownloadedSeriesVideos
    };
  }
});
</script>

<style scoped>
.video-player-container {
  margin-bottom: 20px;
  border-radius: 8px;
  overflow: hidden;
}

.video-info-container {
  margin-bottom: 30px;
}

.video-header {
  margin-bottom: 20px;
}

.video-author {
  display: flex;
  align-items: center;
  margin-bottom: 15px;
}

.author-avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  overflow: hidden;
  margin-right: 15px;
}

.author-avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.author-info {
  display: flex;
  flex-direction: column;
}

.author-name {
  font-size: 16px;
  font-weight: 500;
  color: var(--text-color);
}

.author-type {
  font-size: 12px;
  color: var(--text-secondary-color);
}

.video-title {
  font-size: 24px;
  font-weight: 700;
  margin-bottom: 10px;
  line-height: 1.3;
}

.video-subtitle {
  font-size: 16px;
  color: var(--text-secondary-color);
  margin-bottom: 15px;
}

.video-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
  margin-bottom: 15px;
}

.meta-item {
  display: flex;
  align-items: center;
  font-size: 14px;
  color: var(--text-secondary-color);
}

.meta-item .el-icon {
  color: var(--primary-color);
  margin-right: 5px;
}

.meta-separator {
  margin: 0 8px;
  color: var(--text-secondary-color);
}

.video-actions {
  display: flex;
  gap: 10px;
}

/* 下载按钮样式 */
.download-button {
  display: flex;
  align-items: center;
  gap: 5px;
}

.video-description {
  margin: 20px 0;
  position: relative;
}

.description-content {
  font-size: 14px;
  line-height: 1.6;
  color: var(--text-color);
  white-space: pre-wrap;
}

.description-content.collapsed {
  max-height: 80px;
  overflow: hidden;
}

.expand-button {
  margin-top: 10px;
  font-size: 14px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--primary-color);
}

.expand-button .el-icon {
  margin-left: 5px;
}

.video-tags-container {
  margin: 20px 0;
}

.section-title {
  font-size: 18px;
  font-weight: 600;
  margin-bottom: 15px;
  color: var(--text-secondary-color);
}

.tags-list {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.tag-item {
  cursor: pointer;
  transition: all 0.2s;
  background-color: var(--bg-secondary-color) !important;
  border-color: var(--border-color) !important;
  color: var(--text-color) !important;
  padding: 8px 15px !important;
  font-size: 14px !important;
}

.tag-item:hover {
  transform: translateY(-2px);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
  background-color: var(--primary-color) !important;
  border-color: var(--primary-color) !important;
  color: var(--button-text-color) !important;
}

.tab-container {
  margin-bottom: 20px;
}

.tab-header {
  display: flex;
  border-bottom: 1px solid var(--border-color);
}

.tab {
  padding: 12px 20px;
  font-size: 16px;
  cursor: pointer;
  position: relative;
  color: var(--text-secondary-color);
  transition: color 0.3s;
}

.tab:hover {
  color: var(--text-color);
}

.tab.active {
  color: var(--text-color);
}

.tab.active::after {
  content: '';
  position: absolute;
  bottom: -1px;
  left: 0;
  width: 100%;
  height: 2px;
  background: var(--primary-color);
}

.comment-count-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 20px;
  height: 20px;
  padding: 0 6px;
  border-radius: 10px;
  background-color: var(--primary-color);
  color: var(--button-text-color);
  font-size: 12px;
  font-weight: 500;
  margin-left: 5px;
}

/* 评论区样式 */
.comments-container {
  margin-top: 20px;
}

/* 视频下载对话框样式 */
.download-dialog {
  background-color: var(--bg-secondary-color) !important;
  border-color: var(--border-color) !important;
  color: var(--text-color) !important;
}

.download-dialog :deep(.el-dialog__header) {
  background-color: var(--bg-secondary-color);
  padding: 15px 20px;
}

.download-dialog :deep(.el-dialog__title) {
  color: var(--text-color);
  font-size: 18px;
  font-weight: 600;
}

.download-dialog :deep(.el-dialog__headerbtn .el-dialog__close) {
  color: var(--text-secondary-color);
}

.download-dialog .el-dialog__body {
  background-color: var(--bg-color);
  padding: 20px;
}

.download-list {
  list-style: none;
  padding: 0;
}

.download-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 15px;
  margin-bottom: 10px;
  background-color: var(--bg-secondary-color);
  border-radius: 8px;
  transition: all 0.3s;
}

.download-item:hover {
  transform: translateY(-2px);
  box-shadow: var(--card-shadow);
}

.download-info {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.download-quality {
  font-size: 16px;
  font-weight: 500;
  color: var(--text-color);
}

.download-size {
  font-size: 14px;
  color: var(--text-secondary-color);
}

.series-download-info {
  text-align: center;
  margin-bottom: 20px;
}

.download-notice {
  margin-top: 10px;
  color: var(--text-secondary-color);
}

.series-download-actions {
  display: flex;
  justify-content: center;
}

.disabled-item {
  opacity: 0.6;
  cursor: not-allowed;
}

.info-icon {
  margin-left: 5px;
  font-size: 14px;
  color: var(--text-secondary-color);
}

/* 可点击项样式 */
.clickable {
  cursor: pointer;
  transition: color 0.2s;
}

.clickable:hover {
  color: var(--primary-color);
}

/* 移除下划线样式 */

/* 响应式设计 */
@media (max-width: 768px) {
  .video-title {
    font-size: 20px;
  }
  
  .video-meta {
    flex-direction: column;
    align-items: flex-start;
  }
  
  .video-actions {
    margin-top: 10px;
  }
}

@media (max-width: 480px) {
  .video-title {
    font-size: 18px;
  }
  
  .tab {
    padding: 10px 15px;
    font-size: 14px;
  }
}

/* 相关视频网格布局样式 */
.related-section {
  margin-top: 20px;
}

.video-grid-basic {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: 15px;
  margin-bottom: 30px;
}

.video-grid-detailed {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 15px;
  margin-bottom: 30px;
}

.basic-video-card {
  height: 100%;
}

.wide-video-card {
  height: 100%;
}

@media (max-width: 768px) {
  .video-grid-basic {
    grid-template-columns: repeat(3, 1fr);
    gap: 12px;
  }
  .video-grid-detailed {
    grid-template-columns: repeat(2, 1fr);
    gap: 12px;
  }
}

@media (max-width: 480px) {
  .video-grid-basic {
    grid-template-columns: repeat(3, 1fr);
    gap: 8px;
  }
  .video-grid-detailed {
    grid-template-columns: repeat(2, 1fr);
    gap: 8px;
  }
}

/* 下载按钮样式 */
.quality-options-header {
  padding: 8px 16px;
  font-size: 14px;
  color: var(--text-secondary-color);
  background-color: var(--bg-secondary-color);
  border-bottom: 1px solid var(--border-color);
  margin-bottom: 4px;
}

.quality-option {
  display: flex;
  flex-direction: column;
  gap: 4px;
  width: 100%;
}

.quality-label {
  display: flex;
  align-items: center;
  gap: 8px;
}

.quality-size {
  font-size: 12px;
  color: var(--text-secondary-color);
}

.series-option {
  display: flex;
  align-items: center;
  gap: 8px;
}

/* 系列视频选择对话框样式 */
.series-download-dialog {
  background-color: var(--bg-secondary-color) !important;
  border-color: var(--border-color) !important;
  color: var(--text-color) !important;
}

.series-download-dialog :deep(.el-dialog__header) {
  background-color: var(--bg-secondary-color);
  padding: 15px 20px;
}

.series-download-dialog :deep(.el-dialog__title) {
  color: var(--text-color);
  font-size: 18px;
  font-weight: 600;
}

.series-download-dialog :deep(.el-dialog__headerbtn .el-dialog__close) {
  color: var(--text-secondary-color);
}

.series-download-dialog .el-dialog__body {
  background-color: var(--bg-color);
  padding: 20px;
}

.series-selection {
  margin-bottom: 20px;
}

.selection-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 0;
  border-bottom: 1px solid var(--border-color);
  margin-bottom: 20px;
}

.selection-count {
  font-size: 14px;
  padding: 4px 12px;
  background-color: var(--primary-color);
  color: #fff;
  border-radius: 20px;
}

.series-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 20px;
  margin-top: 20px;
  max-height: 60vh;
  overflow-y: auto;
  padding-right: 10px;
}

.series-item {
  position: relative;
  margin-bottom: 10px;
}

.series-item .el-checkbox {
  position: absolute;
  top: 10px;
  left: 10px;
  z-index: 10;
}

.series-card {
  width: 100%;
  background-color: var(--bg-secondary-color);
  border: 2px solid transparent;
  border-radius: 8px;
  overflow: hidden;
  transition: all 0.3s;
  cursor: pointer;
}

.series-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--card-shadow);
  border-color: var(--primary-color-light);
}

.series-card.selected {
  border-color: var(--primary-color);
  box-shadow: 0 0 0 1px var(--primary-color);
}

.series-card.already-downloaded {
  opacity: 0.6;
  cursor: not-allowed;
}

.series-thumbnail {
  position: relative;
  width: 100%;
  padding-top: 56.25%; /* 16:9 宽高比 */
}

.series-thumbnail img {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.duration-badge {
  position: absolute;
  bottom: 8px;
  right: 8px;
  background-color: rgba(0, 0, 0, 0.7);
  color: #fff;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
}

.series-info {
  padding: 12px;
}

.series-title {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-color);
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  line-height: 1.4;
  height: 2.8em;
}

.download-status-badge {
  position: absolute;
  top: 8px;
  right: 8px;
  background-color: rgba(0, 0, 0, 0.7);
  color: #fff;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
}

.dialog-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

/* 媒体查询适配移动设备 */
@media (max-width: 768px) {
  .series-grid {
    grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
    gap: 10px;
  }
  
  .series-title {
    font-size: 13px;
  }
  
  .series-info {
    padding: 8px;
  }
  
  .duration-badge {
    font-size: 10px;
    padding: 1px 6px;
  }
  
  .selection-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 10px;
  }
}

/* 移动设备上的对话框样式 */
@media (max-width: 480px) {
  .series-grid {
    grid-template-columns: repeat(auto-fill, minmax(110px, 1fr));
    gap: 8px;
  }
  
  .series-item .el-checkbox {
    top: 5px;
    left: 5px;
  }
}
</style>