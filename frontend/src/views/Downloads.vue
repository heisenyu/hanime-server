<template>
  <div class="downloads-page">
    <div class="downloads-header">
      <div class="header-top">
        <h1 class="page-title">下载管理</h1>
        
        <!-- 普通模式下的批量操作按钮 -->
        <div v-if="!downloadStore.batchDeleteMode" class="bulk-actions">
          <el-button-group>
            <el-button :disabled="!activeDownloads.length" @click="pauseAllDownloads" type="primary">
              <el-icon><VideoPause /></el-icon> 全部暂停
            </el-button>
            <el-button :disabled="!(downloadStore.pausedDownloads.length)" @click="resumeAllDownloads" type="success">
              <el-icon><VideoPlay /></el-icon> 全部继续
            </el-button>
          </el-button-group>
          
          <el-dropdown @command="handleBatchAction" trigger="click">
            <el-button>
              批量操作 <el-icon class="el-icon--right"><ArrowDown /></el-icon>
            </el-button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="batchDelete">
                  <el-icon><Delete /></el-icon> 批量删除
                </el-dropdown-item>
                <el-dropdown-item command="clearFailed" :disabled="!downloadStore.failedDownloads.length">
                  <el-icon><Delete /></el-icon> 清除失败任务
                </el-dropdown-item>
                <el-dropdown-item command="retryFailed" :disabled="!downloadStore.failedDownloads.length">
                  <el-icon><RefreshRight /></el-icon> 重试失败任务
                </el-dropdown-item>
                <el-dropdown-item command="exportData" divided>
                  <el-icon><Download /></el-icon> 导出下载列表
                </el-dropdown-item>
                <el-dropdown-item command="refreshList">
                  <el-icon><Refresh /></el-icon> 刷新列表
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
        
        <!-- 批量删除模式下的操作面板 -->
        <div v-else class="batch-delete-actions">
          <div class="batch-action-info">
            <span class="selected-count">已选择 {{ downloadStore.selectedDownloadsCount }} 项</span>
          </div>
          <div class="batch-action-buttons">
            <el-button @click="toggleSelectAll" type="info" plain>
              <el-icon><component :is="allSelected ? 'CloseBold' : 'Select'" /></el-icon> {{ allSelected ? '取消全选' : '全选' }}
            </el-button>
            <el-button @click="confirmDeleteSelected" type="danger" :disabled="!downloadStore.hasSelectedDownloads">
              <el-icon><Delete /></el-icon> 删除所选
            </el-button>
            <el-button @click="downloadStore.toggleBatchDeleteMode()" type="default">
              <el-icon><Back /></el-icon> 退出
            </el-button>
          </div>
        </div>
      </div>
      
      <!-- 普通模式下显示统计信息 -->
      <div v-if="!downloadStore.batchDeleteMode" class="stats-container">
        <div class="download-stats">
          <div class="stat-card">
            <div class="stat-value">{{ activeDownloads?.length || 0 }}</div>
            <div class="stat-label">下载中</div>
          </div>
          <div class="stat-card">
            <div class="stat-value">{{ completedDownloads?.length || 0 }}</div>
            <div class="stat-label">已完成</div>
          </div>
          <div class="stat-card">
            <div class="stat-value">{{ downloadStore.failedDownloads.length || 0 }}</div>
            <div class="stat-label">已失败</div>
          </div>
          <div class="stat-card">
            <div class="stat-value">{{ allDownloads?.length || 0 }}</div>
            <div class="stat-label">总计</div>
          </div>
          <div class="stat-card">
            <div class="stat-value">{{ formatFileSize(totalDownloaded) }}</div>
            <div class="stat-label">已占用大小</div>
          </div>
        </div>
      </div>
    </div>
    
    <div class="download-content">
      <el-tabs v-model="activeTab" class="download-tabs">
        <el-tab-pane label="全部下载" name="all">
          <download-list :filter="'all'" @play-video="handlePlayVideo" />
        </el-tab-pane>
        <el-tab-pane label="下载中" name="active">
          <download-list :filter="'active'" @play-video="handlePlayVideo" />
        </el-tab-pane>
        <el-tab-pane label="已完成" name="completed">
          <download-list :filter="'completed'" @play-video="handlePlayVideo" />
        </el-tab-pane>
        <el-tab-pane label="已失败" name="failed">
          <download-list :filter="'failed'" @play-video="handlePlayVideo" />
        </el-tab-pane>
      </el-tabs>
    </div>
    
    <!-- 批量删除确认对话框 -->
    <el-dialog
      v-model="confirmDialogVisible"
      :title="confirmDialogTitle"
      width="30%"
    >
      <span>{{ confirmDialogMessage }}</span>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="confirmDialogVisible = false">取消</el-button>
          <el-button type="danger" @click="confirmAction">确认</el-button>
        </span>
      </template>
    </el-dialog>
    
    <!-- 视频播放器弹窗 -->
    <el-dialog
      v-model="videoPlayerVisible"
      :title="currentVideo.title || '离线播放'"
      width="80%"
      destroy-on-close
      top="5vh"
      class="video-dialog"
      :before-close="closeVideoPlayer"
    >
      <div class="video-player-wrapper">
        <VideoPlayer 
          v-if="videoPlayerVisible"
          :streamUrls="[{ url: currentVideo.url, quality: '原始质量' }]"
          :coverUrl="currentVideo.cover_url"
          :title="currentVideo.title"
          :autoPlay="true"
          :showDebugInfo="false"
        />
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue';
import { useDownloadStore } from '../stores/download';
import { storeToRefs } from 'pinia';
import DownloadList from '../components/DownloadList.vue';
import VideoPlayer from '../components/VideoPlayer.vue';
import { VideoPause, VideoPlay, ArrowDown, Delete, RefreshRight, Download, Refresh, Select, Close, Back, CloseBold } from '@element-plus/icons-vue';
import { ElMessageBox, ElMessage } from 'element-plus';
import { DownloadApi } from '../api/download';
import { DownloadProgress } from '../types/download';

// 引入下载状态管理
const downloadStore = useDownloadStore();
const { 
  activeDownloads, 
  completedDownloads,
  allDownloads,
  totalDownloaded,
  hasActiveDownloads,
  hasPausedDownloads
} = storeToRefs(downloadStore);

// 当前活跃的标签页
const activeTab = ref('all');
const confirmDialogVisible = ref(false);
const confirmDialogTitle = ref('');
const confirmDialogMessage = ref('');
const pendingAction = ref('');

// 视频播放相关状态
const videoPlayerVisible = ref(false);
const currentVideo = ref<{
  video_id: string;
  url: string;
  title: string;
  cover_url: string;
}>({
  video_id: '',
  url: '',
  title: '',
  cover_url: ''
});

// 当前选项卡下的所有可见下载项
const visibleDownloads = computed(() => {
  switch (activeTab.value) {
    case 'active':
      return activeDownloads.value;
    case 'completed':
      return completedDownloads.value;
    case 'failed':
      return downloadStore.failedDownloads;
    default:
      return allDownloads.value;
  }
});

// 计算总体下载进度
const overallProgress = computed(() => {
  return downloadStore.getOverallProgress();
});

// 判断是否全部选择了
const allSelected = computed(() => {
  const visibleCount = visibleDownloads.value.length;
  const selectedCount = visibleDownloads.value.filter(item => 
    downloadStore.selectedDownloads.has(item.video_id)
  ).length;
  
  return visibleCount > 0 && visibleCount === selectedCount;
});

// 切换全选/取消全选
const toggleSelectAll = () => {
  if (allSelected.value) {
    downloadStore.clearSelection();
  } else {
    selectAllVisible();
  }
};

// 初始化下载列表
onMounted(async () => {
  await downloadStore.initializeDownloads();
});

// 选中当前页面所有可见的下载项
const selectAllVisible = () => {
  downloadStore.selectAll(visibleDownloads.value);
};

// 确认删除已选项
const confirmDeleteSelected = async () => {
  if (!downloadStore.hasSelectedDownloads) return;
  
  try {
    await ElMessageBox.confirm(
      `确定要删除已选择的 ${downloadStore.selectedDownloadsCount} 个下载记录吗？此操作不可撤销。`,
      '确认删除',
      {
        confirmButtonText: '删除',
        cancelButtonText: '取消',
        type: 'warning'
      }
    );
    
    await downloadStore.deleteSelected();
  } catch (error) {
    // 用户取消操作
  }
};

// 格式化文件大小
const formatFileSize = (bytes: number | undefined): string => {
  if (bytes === undefined || isNaN(bytes)) {
    return '0 B';
  }
  return DownloadApi.formatFileSize(bytes);
};

// 暂停所有下载
const pauseAllDownloads = async () => {
  await downloadStore.pauseAllDownloads();
  ElMessage.success('已暂停所有下载');
};

// 恢复所有下载
const resumeAllDownloads = async () => {
  await downloadStore.resumeAllDownloads();
  ElMessage.success('已恢复所有下载');
};

// 导出下载列表为JSON
const exportDownloadData = () => {
  try {
    const data = JSON.stringify(allDownloads.value, null, 2);
    const blob = new Blob([data], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    
    const link = document.createElement('a');
    link.href = url;
    link.download = `downloads_${new Date().toISOString().split('T')[0]}.json`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    
    ElMessage.success('下载列表已导出');
  } catch (error) {
    console.error('导出下载列表失败:', error);
    ElMessage.error('导出下载列表失败');
  }
};

// 刷新下载列表
const refreshDownloadList = async () => {
  try {
    ElMessage.info('正在刷新下载列表...');
    await downloadStore.initializeDownloads();
    ElMessage.success('下载列表已刷新');
  } catch (error) {
    console.error('刷新下载列表失败:', error);
    ElMessage.error('刷新下载列表失败');
  }
};

// 确认执行操作
const confirmAction = async () => {
  confirmDialogVisible.value = false;
  
  try {
    switch (pendingAction.value) {
      case 'clearCompleted':
        await downloadStore.clearCompletedDownloads();
        ElMessage.success('已清除所有已完成的下载记录');
        break;
      case 'clearFailed':
        await downloadStore.clearFailedDownloads();
        ElMessage.success('已清除所有失败的下载记录');
        break;
      default:
        break;
    }
  } catch (error) {
    console.error(`执行操作 ${pendingAction.value} 失败:`, error);
    ElMessage.error('操作失败，请稍后重试');
  }
};

// 处理批量操作
const handleBatchAction = async (command: string) => {
  switch (command) {
    case 'batchDelete':
      downloadStore.toggleBatchDeleteMode();
      break;
      
    case 'clearCompleted':
      pendingAction.value = 'clearCompleted';
      confirmDialogTitle.value = '清除已完成下载';
      confirmDialogMessage.value = '确定要清除所有已完成的下载记录吗？此操作不可撤销。';
      confirmDialogVisible.value = true;
      break;
      
    case 'clearFailed':
      pendingAction.value = 'clearFailed';
      confirmDialogTitle.value = '清除失败下载';
      confirmDialogMessage.value = '确定要清除所有失败的下载记录吗？此操作不可撤销。';
      confirmDialogVisible.value = true;
      break;
      
    case 'retryFailed':
      await downloadStore.retryAllFailedDownloads();
      ElMessage.success('已重试所有失败的下载任务');
      break;
      
    case 'exportData':
      exportDownloadData();
      break;
      
    case 'refreshList':
      refreshDownloadList();
      break;
      
    default:
      break;
  }
};

// 当切换标签页时，如果在批量删除模式则清空选择
watch(activeTab, () => {
  if (downloadStore.batchDeleteMode) {
    downloadStore.clearSelection();
  }
});

// 处理播放视频事件
const handlePlayVideo = (videoInfo: { video_id: string; url: string; title: string; cover_url: string }) => {
  currentVideo.value = videoInfo;
  videoPlayerVisible.value = true;
};

// 关闭视频播放器
const closeVideoPlayer = () => {
  videoPlayerVisible.value = false;
  // 延迟清空数据，确保组件销毁后再清空
  setTimeout(() => {
    currentVideo.value = {
      video_id: '',
      url: '',
      title: '',
      cover_url: ''
    };
  }, 200);
};
</script>

<style scoped>
.downloads-page {
  width: 100%;
  padding: 20px;
  overflow-x: hidden;
}

.downloads-header {
  margin-bottom: 20px;
}

.header-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 15px;
  margin-bottom: 15px;
}

.page-title {
  font-size: 24px;
  margin: 0;
  color: var(--text-color);
}

.bulk-actions {
  display: flex;
  gap: 10px;
  align-items: center;
}

.batch-delete-actions {
  display: flex;
  flex-direction: column;
  gap: 10px;
  width: 100%;
}

.batch-action-info {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.selected-count {
  font-weight: 500;
  color: var(--primary-color);
}

.batch-action-buttons {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.stats-container {
  background-color: var(--bg-secondary-color);
  border-radius: 8px;
  padding: 15px;
  margin-bottom: 20px;
}

.download-stats {
  display: flex;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 10px;
  margin-bottom: 15px;
}

.stat-card {
  background-color: var(--bg-color);
  border-radius: 6px;
  padding: 10px 15px;
  flex: 1;
  min-width: 80px;
  text-align: center;
  box-shadow: var(--card-shadow);
}

.stat-value {
  font-size: 20px;
  font-weight: 600;
  color: var(--primary-color);
}

.stat-label {
  font-size: 14px;
  color: var(--text-secondary-color);
  margin-top: 5px;
}

.download-content {
  background-color: var(--bg-secondary-color);
  border-radius: 8px;
  padding: 15px;
}

.video-player-wrapper {
  width: 100%;
  aspect-ratio: 16 / 9;
}

.video-dialog :deep(.el-dialog__body) {
  padding: 10px;
}

/* 响应式样式 */
@media (max-width: 768px) {
  .downloads-page {
    padding: 10px;
  }
  
  .header-top {
    flex-direction: column;
    align-items: flex-start;
    gap: 10px;
  }
  
  .bulk-actions {
    width: 100%;
    justify-content: space-between;
  }
  
  .batch-action-buttons {
    justify-content: space-between;
    width: 100%;
  }
  
  .download-stats {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
  }
  
  .stat-card {
    min-width: 0;
    flex: none;
  }
  
  .download-tabs :deep(.el-tabs__header) {
    margin-bottom: 10px;
  }
  
  .download-tabs :deep(.el-tabs__nav) {
    width: 100%;
    display: flex;
  }
  
  .download-tabs :deep(.el-tabs__item) {
    flex: 1;
    text-align: center;
    padding: 0 5px;
    font-size: 14px;
  }
  
  .video-dialog {
    width: 95% !important;
    margin: 0 auto;
  }
}

@media (max-width: 480px) {
  .downloads-page {
    padding: 5px;
  }
  
  .page-title {
    font-size: 20px;
    width: 100%;
    margin-bottom: 10px;
  }
  
  .bulk-actions {
    flex-wrap: wrap;
    gap: 8px;
  }
  
  .download-stats {
    grid-template-columns: repeat(2, 1fr);
    gap: 8px;
  }
  
  .stat-card {
    padding: 8px;
  }
  
  .stat-value {
    font-size: 16px;
  }
  
  .stat-label {
    font-size: 12px;
  }
  
  .download-tabs :deep(.el-tabs__item) {
    font-size: 12px;
}

  .video-dialog {
    width: 100% !important;
    margin: 0;
  }
}

/* 手机端批量删除操作按钮样式 */
@media (max-width: 576px) {
  .batch-delete-actions {
    flex-direction: column;
    gap: 10px;
  }
  
  .batch-action-info {
    width: 100%;
    text-align: center;
  }
  
  .batch-action-buttons {
    display: flex;
    flex-direction: row;
    width: 100%;
    justify-content: space-between;
    flex-wrap: nowrap;
    gap: 5px;
  }
  
  .batch-action-buttons .el-button {
    flex: 1;
    padding: 8px 5px;
    min-width: 0;
  }
  
  .batch-action-buttons .el-button .el-icon {
    margin-right: 0;
  }
  
  .batch-action-buttons .el-button:not(.is-text) {
    width: auto;
  }
}
</style> 