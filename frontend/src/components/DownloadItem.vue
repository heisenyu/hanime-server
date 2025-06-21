<template>
  <div class="download-item" 
       :class="[`status-${download.status}`, {'batch-mode': downloadStore.batchDeleteMode}]"
       @click="handleItemClick"
  >
    <div class="item-content">
      <!-- 选择复选框 -->
      <div v-if="downloadStore.batchDeleteMode" class="item-checkbox">
        <el-checkbox 
          v-model="isSelected"
          @change="toggleSelection"
          size="large"
        />
      </div>
      <!-- 缩略图 -->
      <div class="item-thumbnail">
        <img 
          v-if="download.cover_url" 
          :src="download.cover_url" 
          class="thumbnail" 
          :alt="extractFilename(download.filename) || download.title"
          loading="lazy"
          referrerpolicy="no-referrer"
        />
        <div v-else class="thumbnail placeholder"></div>
      </div>
      
      <!-- 信息区 -->
      <div class="item-info">
        <div class="item-header">
          <h3 class="item-title">
            <router-link
              v-if="!downloadStore.batchDeleteMode"
              :to="`/video/${download.video_id}`"
              class="item-title-link"
              :title="extractFilename(download.filename) || download.title"
            >
              {{ extractFilename(download.filename) || download.title }}
            </router-link>
            <span v-else>{{ extractFilename(download.filename) || download.title }}</span>
          </h3>
        </div>
        
        <div class="item-meta">
          <el-tag
            :type="getStatusType()"
            size="small"
            :style="getStatusTagStyle()"
          >
            {{ getStatusText() }}
          </el-tag>
          <span class="meta-date">{{ formatDate(download.created_at) }}</span>
        </div>
        
        <!-- 进度条 -->
        <div v-if="['downloading', 'paused', 'pending'].includes(download.status)" class="progress-section">
          <div class="progress-bar">
            <el-progress 
              :percentage="getProgressPercent()" 
              :status="getProgressStatus()"
              :stroke-width="8"
              :show-text="false"
            />
          </div>
          <div class="progress-info">
            <span>{{ formatFileSize(download.downloaded) }} / {{ formatFileSize(download.total_size) }}</span>
            <span v-if="download.status === 'downloading'" class="download-speed">
              {{ formatDownloadSpeed(download.speed) }}
            </span>
            <span v-if="download.status === 'downloading'" class="remaining-time">
              {{ getEstimatedTime() }}
            </span>
          </div>
        </div>
        
        <!-- 错误消息 -->
        <div v-if="download.error_message" class="error-message">
          {{ download.error_message }}
        </div>
      </div>
      
      <!-- 操作区 -->
      <div v-if="!downloadStore.batchDeleteMode" class="item-actions" @click.stop>
        <!-- 下载中 -->
        <el-button 
          v-if="download.status === 'downloading'"
          @click="pauseDownload"
          size="small"
          type="primary"
        >
          <el-icon><VideoPause /></el-icon>
        </el-button>
        
        <!-- 暂停中 -->
        <el-button 
          v-if="download.status === 'paused'"
          @click="resumeDownload"
          size="small"
          type="primary"
        >
          <el-icon><VideoPlay /></el-icon>
        </el-button>
        
        <!-- 完成状态 -->
        <el-button 
          v-if="download.status === 'completed'"
          @click="playVideo"
          size="small"
          type="success"
        >
          <el-icon><VideoPlay /></el-icon>
        </el-button>
        
        <!-- 错误状态 - 移到与播放按钮相同位置 -->
        <el-button 
          v-if="download.status === 'error'"
          @click="retryDownload"
          size="small"
          type="danger"
        >
          <el-icon><RefreshRight /></el-icon>
        </el-button>
        
        <!-- 取消状态 - 添加重试按钮 -->
        <el-button 
          v-if="download.status === 'cancelled'"
          @click="retryDownload"
          size="small"
          type="warning"
        >
          <el-icon><RefreshRight /></el-icon>
        </el-button>
        
        <!-- 其他操作 -->
        <el-dropdown trigger="click">
          <el-button size="small" circle>
            <el-icon><More /></el-icon>
          </el-button>
          <template #dropdown>
            <el-dropdown-menu>
              <!-- 取消下载 -->
              <el-dropdown-item 
                v-if="['downloading', 'paused', 'pending'].includes(download.status)"
                @click="confirmCancel"
              >
                <el-icon><Close /></el-icon> 取消下载
              </el-dropdown-item>
              
              <!-- 删除记录 -->
              <el-dropdown-item @click="confirmDelete">
                <el-icon><Delete /></el-icon> 删除记录
              </el-dropdown-item>
              
              <!-- 查看详情 -->
              <el-dropdown-item @click="toggleDetails">
                <el-icon><InfoFilled /></el-icon> {{ showDetails ? '隐藏详情' : '查看详情' }}
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </div>
    
    <!-- 详情区 -->
    <div v-if="showDetails" class="item-details" @click.stop>
      <div class="details-grid">
        <div class="detail-item">
          <div class="detail-label">视频ID</div>
          <div class="detail-value">{{ download.video_id }}</div>
        </div>
        
        <div class="detail-item">
          <div class="detail-label">创建时间</div>
          <div class="detail-value">{{ formatDate(download.created_at, true) }}</div>
        </div>
        
        <div class="detail-item" v-if="download.completed_at">
          <div class="detail-label">完成时间</div>
          <div class="detail-value">{{ formatDate(download.completed_at, true) }}</div>
        </div>
        
        <div class="detail-item">
          <div class="detail-label">文件大小</div>
          <div class="detail-value">{{ formatFileSize(download.total_size) }}</div>
        </div>
        
        <div class="detail-item" v-if="download.error_message">
          <div class="detail-label">错误信息</div>
          <div class="detail-value">{{ download.error_message }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue';
import { useDownloadStore } from '../stores/download';
import { DownloadApi } from '../api/download';
import type { DownloadProgress } from '../types/download';
import { VideoPause, VideoPlay, RefreshRight, Close, Delete, InfoFilled, More } from '@element-plus/icons-vue';
import { ElMessageBox } from 'element-plus';
import { useRouter } from 'vue-router';

// 定义props
interface Props {
  download: DownloadProgress;
}

const props = defineProps<Props>();
// 添加emit定义
const emit = defineEmits<{
  'play-video': [payload: { video_id: string, url: string, title: string, cover_url: string }]
}>();

// 使用下载状态管理
const downloadStore = useDownloadStore();

// 是否显示详情
const showDetails = ref(false);

// 计算属性：是否被选中
const isSelected = computed({
  get: () => downloadStore.isSelected(props.download.video_id),
  set: (value) => {
    if (value) {
      downloadStore.selectedDownloads.add(props.download.video_id);
    } else {
      downloadStore.selectedDownloads.delete(props.download.video_id);
    }
  }
});

// 切换选择
const toggleSelection = () => {
  downloadStore.toggleSelection(props.download.video_id);
};

// 从文件名中提取有意义的名称（去掉视频ID前缀）
const extractFilename = (filename: string): string => {
  if (!filename) return '';
  
  // 文件名格式通常是 "videoID_实际名称.mp4"
  const match = filename.match(/^[^_]+_(.+)\.mp4$/);
  return match ? match[1] : filename;
};

// 获取状态类型（用于标签颜色）
const getStatusType = () => {
  switch (props.download.status) {
    case 'downloading':
      return 'info';
    case 'paused':
      return 'warning';
    case 'completed':
      return 'success';
    case 'error':
      return 'danger';
    case 'cancelled':
      return '';
    default:
      return 'info';
  }
};
    
    // 获取状态文本
    const getStatusText = () => {
      const statusMap: Record<string, string> = {
        pending: '准备中',
        downloading: '下载中',
        paused: '已暂停',
        completed: '已完成',
        cancelled: '已取消',
        error: '下载失败'
      };
      
      return statusMap[props.download.status] || props.download.status;
    };

// 获取进度条状态
const getProgressStatus = () => {
  switch (props.download.status) {
    case 'downloading':
      return '';
    case 'paused':
      return 'warning';
    case 'completed':
      return 'success';
    case 'error':
      return 'exception';
    default:
      return '';
  }
};
    
    // 获取进度百分比
    const getProgressPercent = () => {
      const { downloaded, total_size } = props.download;
      if (total_size === 0) return 0;
      const percent = Math.floor((downloaded / total_size) * 100);
  return Math.min(100, Math.max(0, percent)); // 限制在0-100之间
    };
    
    // 格式化文件大小
    const formatFileSize = (bytes: number) => {
      return DownloadApi.formatFileSize(bytes);
    };
    
    // 格式化下载速度
    const formatDownloadSpeed = (bytesPerSecond: number) => {
      // 使用缓存的平滑速度值，避免频繁跳动
      if (lastSpeedValue.value !== null && props.download.status === 'downloading') {
        return DownloadApi.formatSpeed(lastSpeedValue.value);
      }
      return DownloadApi.formatSpeed(bytesPerSecond);
    };

// 格式化日期
const formatDate = (dateStr: string, showTime: boolean = false) => {
      try {
    if (!dateStr) return '-';
    
        const date = new Date(dateStr);
    if (showTime) {
        // 显示完整日期时间，精确到秒
        return date.toLocaleString('zh-CN', { 
          year: 'numeric',
          month: '2-digit',
          day: '2-digit',
          hour: '2-digit',
          minute: '2-digit',
          second: '2-digit',
          hour12: false
        });
    } else {
      // 只显示日期时，精确到天
      return date.toLocaleDateString('zh-CN', { 
        year: 'numeric',
        month: '2-digit',
        day: '2-digit'
      });
    }
      } catch {
    return dateStr || '-';
      }
    };
    
    // 计算估计剩余时间 (内部方法)
    const calculateEstimatedTime = () => {
      const { downloaded, total_size, speed } = props.download;
      
      if (speed <= 0) return '计算中...';
      
      const remainingBytes = total_size - downloaded;
      const remainingSeconds = Math.floor(remainingBytes / speed);
      
      if (remainingSeconds < 60) {
        return `剩余 ${remainingSeconds} 秒`;
      } else if (remainingSeconds < 3600) {
        const minutes = Math.floor(remainingSeconds / 60);
        const seconds = remainingSeconds % 60;
        return `剩余 ${minutes} 分 ${seconds} 秒`;
      } else {
        const hours = Math.floor(remainingSeconds / 3600);
        const minutes = Math.floor((remainingSeconds % 3600) / 60);
        const seconds = remainingSeconds % 60;
        return `剩余 ${hours}时${minutes}分${seconds}秒`;
      }
    };
    
    // 获取预计剩余时间 (对外接口)
    const getEstimatedTime = () => {
      // 如果正在下载，且有上次计算的估计时间，则使用它
      if (props.download.status === 'downloading') {
        // 首次计算或刷新缓存
        if (lastEstimateValue.value === null) {
          lastEstimateValue.value = calculateEstimatedTime();
        }
        return lastEstimateValue.value;
      }
      
      return calculateEstimatedTime();
    };
    
    // 播放视频
    const playVideo = () => {
      // 获取视频文件URL
      const url = DownloadApi.getVideoFileUrl(props.download.video_id);
      // 触发自定义事件而不是直接打开窗口
      emit('play-video', {
        video_id: props.download.video_id,
        url: url,
        title: extractFilename(props.download.filename) || props.download.title,
        cover_url: props.download.cover_url
      });
    };
    
// 暂停下载
const pauseDownload = async () => {
  await downloadStore.pauseDownload(props.download.video_id);
    };
    
// 继续下载
const resumeDownload = async () => {
  await downloadStore.resumeDownload(props.download.video_id);
    };
    
// 重试下载
const retryDownload = async () => {
  await downloadStore.retryDownload(props.download.video_id);
};

// 确认取消下载
const confirmCancel = async () => {
  try {
    await ElMessageBox.confirm(
      '确定要取消此下载任务吗？',
      '确认取消',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    );
    
    // 执行取消操作
    const result = await downloadStore.cancelDownload(props.download.video_id);
    
    if (result) {
      // 询问用户是否删除记录
      try {
        const shouldDelete = await ElMessageBox.confirm(
          '下载已取消，是否同时删除下载记录？',
          '删除记录',
          {
            confirmButtonText: '删除记录',
            cancelButtonText: '保留记录',
            type: 'info'
          }
        );
        
        if (shouldDelete === 'confirm') {
          await downloadStore.deleteDownload(props.download.video_id);
        }
      } catch {
        // 用户选择保留记录
      }
    }
  } catch {
    // 用户取消操作
  }
};
    
// 确认删除下载记录
const confirmDelete = async () => {
  try {
    await ElMessageBox.confirm(
      '确定要删除此下载记录吗？',
      '确认删除',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    );
    await downloadStore.deleteDownload(props.download.video_id);
  } catch {
    // 用户取消操作
  }
};

// 切换显示详情
const toggleDetails = () => {
  showDetails.value = !showDetails.value;
};

// 新增：自定义状态标签颜色
const getStatusTagStyle = () => {
  switch (props.download.status) {
    case 'completed':
      return { backgroundColor: '#e1f3d8', color: '#67C23A', borderColor: '#67C23A' };
    case 'error':
      return { backgroundColor: '#fde2e2', color: '#F56C6C', borderColor: '#F56C6C' };
    default:
      return {};
  }
};

// 新增：处理根元素点击事件
const handleItemClick = () => {
  if (downloadStore.batchDeleteMode) {
    toggleSelection();
  }
};

// 临时存储平滑处理的计算值
const lastSpeedValue = ref<number | null>(null);
const lastEstimateValue = ref<string | null>(null);
const estimateTimer = ref<number | null>(null);

// 在组件挂载时设置定时更新
onMounted(() => {
  // 每1秒更新一次估计时间，使显示更平滑
  estimateTimer.value = window.setInterval(() => {
    if (props.download.status === 'downloading') {
      // 强制更新估计时间计算
      lastEstimateValue.value = calculateEstimatedTime();
    }
  }, 1000);
});

// 在组件卸载时清除定时器
onUnmounted(() => {
  if (estimateTimer.value !== null) {
    clearInterval(estimateTimer.value);
  }
});

// 监听下载状态变化，更新速度显示
watch(() => props.download.speed, (newSpeed) => {
  if (props.download.status === 'downloading') {
    // 对于小于10 KB/s的速度，舍入到0.1精度，其他舍入到1的精度
    if (newSpeed < 10 * 1024) {
      lastSpeedValue.value = Math.round(newSpeed * 10) / 10;
    } else {
      lastSpeedValue.value = Math.round(newSpeed);
    }
  }
}, { immediate: true });

// 监听状态变化，重置临时变量
watch(() => props.download.status, (newStatus) => {
  if (newStatus !== 'downloading') {
    lastSpeedValue.value = null;
    lastEstimateValue.value = null;
  }
}, { immediate: true });
</script>

<style scoped>
.download-item {
  background-color: var(--bg-color);
  border-radius: 10px;
  padding: 12px 14px;
  margin-bottom: 14px;
  transition: all 0.2s ease;
  box-shadow: var(--card-shadow);
  border-left: 4px solid transparent;
  display: flex;
  flex-direction: column;
}

.download-item.status-downloading {
  border-left-color: #409EFF; /* 蓝色 - 下载中 */
}

.download-item.status-completed {
  border-left-color: #67C23A; /* 绿色 - 已完成 */
}

.download-item.status-error {
  border-left-color: #F56C6C; /* 红色 - 错误 */
}

.download-item.status-paused {
  border-left-color: #E6A23C; /* 黄色 - 已暂停 */
}

.download-item.status-cancelled {
  border-left-color: #909399; /* 灰色 - 已取消 */
}

.download-item:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 12px rgba(0, 0, 0, 0.15);
}

.item-content {
  display: flex;
  align-items: center;
  position: relative;
  gap: 12px;
}

.item-checkbox {
  position: absolute;
  top: 0;
  left: 0;
  z-index: 5;
}

.item-thumbnail {
  flex: 0 0 130px;
  width: 130px;
  height: 73px;
  border-radius: 6px;
  overflow: hidden;
  background-color: #1a1a1a;
  position: relative;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.thumbnail {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.placeholder {
  width: 100%;
  height: 100%;
  background: linear-gradient(135deg, #2d2d2d 0%, #1a1a1a 100%);
}

.item-info {
  flex: 1;
  min-width: 0;
  padding-right: 10px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}

.item-header {
  margin-bottom: 4px;
}

.item-title {
  margin: 0 0 6px 0;
  font-size: 16px;
  font-weight: 600;
  color: var(--text-color);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.item-title-link {
  color: inherit;
  text-decoration: none;
}

.item-title-link:hover {
  color: var(--primary-color);
}

.item-meta {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.meta-date {
  font-size: 13px;
  color: var(--text-secondary-color);
}

.progress-section {
  margin-top: 6px;
}

.progress-bar {
  margin-bottom: 4px;
}

.progress-info {
  display: flex;
  justify-content: space-between;
  font-size: 13px;
  color: var(--text-secondary-color);
}

.download-speed {
  color: var(--primary-color);
  font-weight: 500;
}

.remaining-time {
  color: var(--warning-color);
  font-weight: 500;
}

.error-message {
  margin-top: 8px;
  padding: 8px;
  background-color: rgba(245, 108, 108, 0.1);
  border-left: 2px solid var(--danger-color);
  color: var(--danger-color);
  font-size: 13px;
  border-radius: 4px;
}

.item-actions {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  align-self: center;
}

.item-details {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid var(--border-color);
}

.details-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 12px;
}

.detail-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
  background-color: var(--bg-secondary-color);
  padding: 8px;
  border-radius: 5px;
}

.detail-label {
  font-size: 13px;
  color: var(--text-secondary-color);
}

.detail-value {
  font-size: 14px;
  color: var(--text-color);
  word-break: break-all;
}

/* 批量删除模式时的样式 */
.batch-mode {
  background-color: var(--bg-color);
}

.batch-mode .item-checkbox {
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 5;
}

.batch-mode:hover {
  background-color: var(--bg-hover-color);
}

.batch-mode.selected {
  background-color: rgba(var(--primary-color-rgb), 0.1);
}

/* 平板端显示 */
@media (max-width: 992px) {
  .item-thumbnail {
    flex: 0 0 120px;
    width: 120px;
    height: 68px;
  }
}

/* 手机端显示 */
@media (max-width: 768px) {
  .download-item {
    padding: 10px;
  }
  
  .item-content {
    gap: 10px;
  }
  
  .item-thumbnail {
    flex: 0 0 100px;
    width: 100px;
    height: 56px;
  }
  
  .item-title {
    font-size: 15px;
    margin-bottom: 4px;
  }
}

/* 小屏幕手机端显示 */
@media (max-width: 576px) {
  .download-item {
    border-left-width: 3px;
    padding: 10px;
  }

  .item-content {
    flex-direction: column;
    gap: 8px;
    position: relative;
  }

  .item-thumbnail {
    flex: none;
    width: 100%;
    height: auto;
    aspect-ratio: 16/9;
    margin-bottom: 8px;
    border-radius: 8px;
    position: relative;
  }
  
  .item-info {
    width: 100%;
    padding-right: 0;
  }
  
  .item-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 5px;
  }
  
  .item-title {
    flex: 1;
    font-size: 14px;
    margin-bottom: 0;
    padding-right: 0;
  }
  
  .item-meta {
    margin-bottom: 6px;
    gap: 6px;
  }
  
  .progress-section {
    margin-top: 4px;
    margin-bottom: 8px;
  }
  
  .progress-info {
    font-size: 12px;
  }
  
  .item-actions {
    position: absolute;
    top: 8px;
    right: 8px;
    z-index: 10;
    display: flex;
    gap: 8px;
    background-color: rgba(0, 0, 0, 0.65);
    border-radius: 8px;
    padding: 5px;
  }
  
  .item-actions .el-button {
    height: 32px;
    width: 32px;
    padding: 8px;
  }
  
  .status-completed .item-actions {
    background-color: rgba(103, 194, 58, 0.65);
  }
  
  .status-downloading .item-actions {
    background-color: rgba(64, 158, 255, 0.65);
  }
  
  .status-paused .item-actions {
    background-color: rgba(230, 162, 60, 0.65);
  }
  
  .status-error .item-actions {
    background-color: rgba(245, 108, 108, 0.65);
  }
  
  /* 批量删除模式的移动端样式 */
  .batch-mode .item-checkbox {
    position: absolute;
    top: 8px;
    left: 8px;
    background-color: rgba(0, 0, 0, 0.65);
    border-radius: 8px;
    padding: 4px;
    z-index: 10;
    height: 32px;
    width: 32px;
    display: flex;
    align-items: center;
    justify-content: center;
  }
  
  .batch-mode .item-checkbox :deep(.el-checkbox__inner) {
    border-color: #fff;
    height: 20px;
    width: 20px;
    border-radius: 4px;
  }
  
  /* 隐藏选中状态的对勾 */
  .batch-mode .item-checkbox :deep(.el-checkbox__inner::after) {
    display: none;
  }
  
  /* 选中状态下，使用背景色填充 */
  .batch-mode .item-checkbox :deep(.el-checkbox.is-checked .el-checkbox__inner) {
    background-color: #409EFF;
    border-color: #409EFF;
  }
  
  .batch-mode.selected {
    background-color: rgba(64, 158, 255, 0.1);
    border: 1px solid var(--primary-color);
  }
  
  .batch-mode.selected .item-thumbnail {
    opacity: 0.8;
  }
  
  .batch-mode.selected .item-checkbox {
    background-color: rgba(64, 158, 255, 0.85);
  }
  
  .details-grid {
    grid-template-columns: 1fr;
    gap: 10px;
  }
}
</style> 