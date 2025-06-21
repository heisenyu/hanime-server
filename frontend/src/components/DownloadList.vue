<template>
  <div class="download-list">
    <!-- 搜索和排序工具栏 -->
    <div class="download-toolbar">
      <el-input
        v-model="searchQuery"
        placeholder="搜索视频名称..."
        prefix-icon="Search"
        clearable
        class="search-input"
      />
      
      <el-select v-model="sortBy" placeholder="排序方式" class="sort-select">
        <el-option label="按名称排序" value="name" />
        <el-option label="按下载时间排序" value="created_at" />
        <el-option label="按完成时间排序" value="completed_at" />
        <el-option label="按文件大小排序" value="size" />
      </el-select>
      
      <el-button @click="sortOrder = sortOrder === 'asc' ? 'desc' : 'asc'" class="sort-direction-btn">
        <el-icon>
          <component :is="sortOrder === 'asc' ? 'SortUp' : 'SortDown'" />
        </el-icon>
      </el-button>
    </div>
    
    <div v-if="isLoading" class="loading-container">
      <el-skeleton :rows="3" animated />
    </div>
    
    <div v-else-if="sortedAndFilteredDownloads.length === 0" class="empty-message">
      <el-empty 
        :description="searchQuery ? '没有匹配的下载任务' : getEmptyMessage()" 
        :image-size="80"
      >
        <template #image>
          <el-icon :size="40" class="empty-icon"><Document /></el-icon>
        </template>
      </el-empty>
    </div>
    
    <div v-else class="download-items">
      <download-item 
        v-for="download in sortedAndFilteredDownloads" 
        :key="download.video_id"
        :download="download"
        @play-video="onPlayVideo"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue';
import { DownloadApi } from '../api/download';
import { DownloadActionType, DownloadProgress } from '../types/download';
import DownloadItem from './DownloadItem.vue';
import { useDownloadStore } from '../stores/download';
import { storeToRefs } from 'pinia';
import { Document, Search, SortUp, SortDown } from '@element-plus/icons-vue';

// Props定义
const props = defineProps({
  filter: {
    type: String,
    default: 'all',
    validator: (value: string) => ['all', 'active', 'completed', 'failed'].includes(value)
  }
});

// 定义emit
const emit = defineEmits<{
  'play-video': [payload: { video_id: string, url: string, title: string, cover_url: string }]
}>();

const isLoading = ref(false);
const searchQuery = ref('');
const sortBy = ref('completed_at'); // 默认按完成时间排序
const sortOrder = ref('desc'); // 默认降序
const secondarySortBy = ref('created_at'); // 二级排序字段

// 使用下载状态管理
const downloadStore = useDownloadStore();
const { allDownloads } = storeToRefs(downloadStore);

// 播放视频事件转发
const onPlayVideo = (videoInfo: { video_id: string, url: string, title: string, cover_url: string }) => {
  emit('play-video', videoInfo);
};

// 从文件名中提取有意义的名称（去掉视频ID前缀）
const extractFilename = (filename: string): string => {
  if (!filename) return '';
  
  // 文件名格式通常是 "videoID_实际名称.mp4"
  const match = filename.match(/^[^_]+_(.+)\.mp4$/);
  return match ? match[1] : filename;
};

// 过滤下载列表
const filteredDownloads = computed(() => {
  let result = [];
  
  if (props.filter === 'all') {
    result = allDownloads.value;
  } else if (props.filter === 'active') {
    result = allDownloads.value.filter(download => 
      ['downloading', 'paused', 'pending'].includes(download.status)
    );
  } else if (props.filter === 'completed') {
    result = allDownloads.value.filter(download => 
      download.status === 'completed'
    );
  } else if (props.filter === 'failed') {
    result = allDownloads.value.filter(download => 
      download.status === 'error' || download.status === 'cancelled'
    );
  } else {
    result = allDownloads.value;
  }
  
  return result;
});

// 应用搜索过滤和排序
const sortedAndFilteredDownloads = computed(() => {
  // 先应用搜索过滤
  let result = searchQuery.value
    ? filteredDownloads.value.filter(download => {
        const title = extractFilename(download.filename) || download.title || '';
        return title.toLowerCase().includes(searchQuery.value.toLowerCase());
      })
    : filteredDownloads.value;
  
  // 再应用多级排序
  result = [...result].sort((a, b) => {
    // 主排序
    let primaryValA = getPrimaryValue(a, sortBy.value);
    let primaryValB = getPrimaryValue(b, sortBy.value);
    
    // 如果主排序值相等，则使用二级排序
    if (compareValues(primaryValA, primaryValB, sortOrder.value) === 0) {
      let secondaryValA = getPrimaryValue(a, secondarySortBy.value);
      let secondaryValB = getPrimaryValue(b, secondarySortBy.value);
      return compareValues(secondaryValA, secondaryValB, sortOrder.value);
    }
    
    return compareValues(primaryValA, primaryValB, sortOrder.value);
  });
  
  return result;
});

// 获取排序值
const getPrimaryValue = (item: DownloadProgress, sortField: string) => {
  switch (sortField) {
    case 'name':
      return extractFilename(item.filename) || item.title || '';
    case 'created_at':
      return new Date(item.created_at).getTime();
    case 'completed_at':
      return item.completed_at ? new Date(item.completed_at).getTime() : 0;
    case 'size':
      return item.total_size;
    default:
      return extractFilename(item.filename) || item.title || '';
  }
};

// 比较值
const compareValues = (valA: any, valB: any, order: string) => {
  // 字符串比较
  if (typeof valA === 'string' && typeof valB === 'string') {
    return order === 'asc'
      ? valA.localeCompare(valB)
      : valB.localeCompare(valA);
  }
  
  // 数值比较
  return order === 'asc'
    ? valA - valB
    : valB - valA;
};

// 处理下载操作
const handleAction = async (videoId: string, action: DownloadActionType) => {
  // 如果是删除操作，直接删除UI上的项
  if (action === 'delete') {
    await DownloadApi.handleDownloadAction(videoId, action);
  } else {
    // 其他操作由WebSocket更新处理
    await DownloadApi.handleDownloadAction(videoId, action);
  }
};

// 根据过滤类型获取空消息
const getEmptyMessage = () => {
  switch (props.filter) {
    case 'active':
      return '没有正在下载的任务';
    case 'completed':
      return '没有已完成的下载';
    case 'failed':
      return '没有失败的下载';
    default:
      return '没有下载任务';
  }
};

// 重试所有失败的下载
const retryAllFailed = async () => {
  await downloadStore.retryAllFailedDownloads();
};

// 切换标签时清除搜索
watch(() => props.filter, () => {
  searchQuery.value = '';
});

onMounted(() => {
  // WebSocket连接由store统一管理，不需要在这里单独连接
});
</script>

<style scoped>
.download-list {
  width: 100%;
  margin: 0 auto;
}

.download-toolbar {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 20px;
}

.search-input {
  flex: 1;
}

.sort-select {
  width: 160px;
}

.sort-direction-btn {
  padding: 12px;
}

.download-items {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.empty-message {
  text-align: center;
  color: var(--text-secondary-color);
  padding: 30px 20px;
  background-color: var(--bg-color);
  border-radius: 8px;
  opacity: 0.8;
}

.empty-icon {
  color: var(--text-secondary-color);
  opacity: 0.6;
}

.loading-container {
  padding: 20px;
  background-color: var(--bg-secondary-color);
  border-radius: 8px;
}

@media (max-width: 768px) {
  .download-toolbar {
    flex-direction: row;
    align-items: center;
    flex-wrap: wrap;
    gap: 8px;
  }
  
  .search-input {
    flex: 1;
    min-width: 120px;
  }
  
  .sort-select {
    width: auto;
    min-width: 120px;
  }
  
  .sort-direction-btn {
    padding: 8px;
  }
}

@media (max-width: 576px) {
  .download-toolbar {
    gap: 6px;
  }
  
  .search-input :deep(.el-input__wrapper) {
    padding: 0 8px;
  }
  
  .search-input :deep(.el-input__inner) {
    font-size: 14px;
  }
  
  .sort-select {
    min-width: 100px;
  }
  
  .sort-select :deep(.el-input__wrapper) {
    padding: 0 8px;
  }
  
  .sort-direction-btn {
    padding: 8px;
  }
}
</style> 