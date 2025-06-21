<template>
  <div class="video-section">
    <div class="section-header">
      <h2 class="section-title">{{ title }}</h2>
      <el-button
          v-if="searchSuffix"
          type="primary"
          size="small"
          @click="$emit('view-more', searchSuffix)"
          class="more-btn"
      >
        查看更多
        <el-icon><ArrowRight /></el-icon>
      </el-button>
    </div>

    <div class="horizontal-scroll">
      <video-card
          v-for="video in videos"
          :key="video.video_id"
          :video="video"
          :thumbnail-class="thumbnailClass"
          :custom-class="'horizontal-item ' + itemClass"
          :single-line-title="thumbnailClass === 'landscape'"
          @click="(videoId) => $emit('video-click', videoId)"
      />
    </div>
  </div>
</template>

<script lang="ts">
import {defineComponent, PropType} from 'vue';
import {VideoBase, VideoPreview} from '../types/video';
import VideoCard from "./VideoCard.vue";
import { ArrowRight } from '@element-plus/icons-vue';


export default defineComponent({
  name: 'VideoSection',
  components: {
    VideoCard
  },
  props: {
    title: {
      type: String,
      required: true
    },
    searchSuffix: {
      type: String,
      default: ''
    },
    videos: {
      type: Array as PropType<(VideoBase | VideoPreview)[]>,
      required: true
    },
    itemClass: {
      type: String,
      default: ''
    },
    thumbnailClass: {
      type: String,
      default: 'landscape'
    }
  },
  emits: ['view-more', 'video-click']
});
</script>

<style scoped>
.video-section {
  margin-bottom: 20px;
  background-color: var(--bg-secondary-color);
  border-radius: 8px;
  padding: 15px;
  box-shadow: var(--card-shadow);
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
  border-bottom: 1px solid var(--border-color);
  padding-bottom: 10px;
}

.section-title {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: var(--text-color);
  position: relative;
  padding-left: 12px;
}

.section-title::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  height: 100%;
  width: 4px;
  background: #ec4899; /* 粉色 */
  border-radius: 2px;
}

.more-btn {
  font-weight: 500;
  transition: all 0.3s;
  background-color: #ec4899; /* 粉色 */
  border-color: #ec4899;
}

.more-btn:hover {
  background-color: #d946ef; /* 紫色 */
  border-color: #d946ef;
  transform: translateY(-2px);
}

.more-btn i {
  margin-left: 5px;
  transition: transform 0.3s;
}

.more-btn:hover i {
  transform: translateX(3px);
}

/* 水平滚动布局 */
.horizontal-scroll {
  display: flex;
  overflow-x: auto;
  gap: 12px;
  padding-bottom: 10px;
  scrollbar-width: thin;
  scroll-behavior: smooth;
}

/* 使用webkit自定义滚动条 */
.horizontal-scroll::-webkit-scrollbar {
  height: 8px;
}

.horizontal-scroll::-webkit-scrollbar-track {
  background: var(--border-color);
  border-radius: 10px;
}

.horizontal-scroll::-webkit-scrollbar-thumb {
  background: var(--secondary-color);
  border-radius: 10px;
  border: 2px solid var(--border-color);
}

.horizontal-scroll::-webkit-scrollbar-thumb:hover {
  background: #d946ef;
}

/* Firefox自定义滚动条 */
@supports (scrollbar-color: var(--secondary-color) var(--border-color)) {
  .horizontal-scroll {
    scrollbar-color: var(--secondary-color) var(--border-color);
    scrollbar-width: thin;
  }
}

.horizontal-item {
  flex: 0 0 240px;
}

.latest-horizontal-item {
  flex: 0 0 160px;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .video-section {
    padding: 12px;
    margin-bottom: 15px;
  }

  .section-title {
    font-size: 16px;
  }

  .horizontal-item {
    flex: 0 0 180px;
  }

  .latest-horizontal-item {
    flex: 0 0 140px;
  }
}

@media (max-width: 480px) {
  .video-section {
    padding: 10px;
    margin-bottom: 12px;
  }

  .section-title {
    font-size: 15px;
  }

  .horizontal-item {
    flex: 0 0 48%;
  }

  .latest-horizontal-item {
    flex: 0 0 120px;
  }
}
</style> 