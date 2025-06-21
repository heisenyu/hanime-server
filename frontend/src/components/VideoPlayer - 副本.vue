<template>
  <div class="video-player-container">
    <!-- 视频播放器组件 -->
    <div class="video-player" v-if="isPlaying">
      <video
          ref="videoPlayer"
          id="player"
          playsinline
          controls
          data-poster="{{ coverUrl }}"
          class="video-element"
          @error="handleVideoError"
          preload="auto"
          crossorigin="anonymous"
      >
        <source v-for="(stream, index) in processedStreamUrls"
                :key="index"
                :src="getStreamUrl(stream.url)"
                :type="'video/mp4'"
                :size="getQualityValue(stream.quality)">
        您的浏览器不支持 HTML5 视频播放
      </video>
    </div>

    <!-- 视频封面 -->
    <div v-else class="video-placeholder" @click="playVideo">
      <img :src="coverUrl" :alt="title" referrerpolicy="no-referrer" loading="lazy"/>
      <div class="play-button">
        <svg viewBox="0 0 24 24" width="60" height="60" fill="white">
          <path d="M8 5v14l11-7z"/>
        </svg>
      </div>
    </div>

    <!-- 调试信息区域 (开发环境) -->
    <div class="debug-info" v-if="showDebugInfo">
      <h4>播放器调试信息:</h4>
      <div v-for="(log, index) in debugLogs" :key="index" class="debug-log">
        {{ log }}
      </div>
    </div>
  </div>
</template>

<script lang="ts">
import {defineComponent, ref, onMounted, onUnmounted, nextTick, watch, computed} from 'vue';
// import {VideoApi} from '../api/video';
import {StreamUrl} from '../types/video';
import Plyr from 'plyr';
import 'plyr/dist/plyr.css';

export default defineComponent({
  name: 'VideoPlayer',
  props: {
    streamUrls: {
      type: Array as () => StreamUrl[],
      required: true
    },
    defaultVideoUrl: {
      type: String,
      default: ''
    },
    coverUrl: {
      type: String,
      required: true
    },
    title: {
      type: String,
      required: true
    },
    autoPlay: {
      type: Boolean,
      default: false
    },
    showDebugInfo: {
      type: Boolean,
      default: true
    }
  },
  emits: ['play-started', 'play-error'],
  setup(props, {emit}) {
    const isPlaying = ref(false);
    const videoPlayer = ref<HTMLVideoElement | null>(null);
    const plyrPlayer = ref<any>(null);
    const debugLogs = ref<string[]>([]);

    // 处理流URL，包括默认视频URL
    const processedStreamUrls = computed(() => {
      // 默认URL已经在streamUrls中，直接返回
      return [...props.streamUrls];
    });

    // 获取默认清晰度值
    const defaultQuality = computed(() => {
      if (!props.defaultVideoUrl) return undefined;
      
      const defaultStream = props.streamUrls.find(stream => stream.url === props.defaultVideoUrl);
      if (defaultStream) {
        const qualityValue = parseInt(getQualityValue(defaultStream.quality));
        return isNaN(qualityValue) ? undefined : qualityValue;
      }
      return undefined;
    });

    // 获取所有可用的清晰度选项
    const qualityOptions = computed(() => {
      return processedStreamUrls.value
        .map(stream => {
          const value = parseInt(getQualityValue(stream.quality));
          return isNaN(value) ? null : value;
        })
        .filter(Boolean)
        .sort((a, b) => b! - a!) as number[]; // 从大到小排序
    });

    // 当前选中的清晰度
    const currentQuality = ref<number | undefined>(undefined);

    // 调试日志函数
    const addDebugLog = (message: string) => {
      if (!props.showDebugInfo) return;

      const timestamp = new Date().toLocaleTimeString();
      const logMessage = `${timestamp}: ${message}`;
      debugLogs.value.push(logMessage);
      console.log(logMessage);

      // 限制日志条数
      if (debugLogs.value.length > 50) {
        debugLogs.value.shift();
      }
    };

    // 从quality字符串中提取数值
    const getQualityValue = (quality: string): string => {
      return quality.endsWith('p') ? quality.slice(0, -1) : quality;
    };

    // 获取流式URL
    const getStreamUrl = (url: string) => {
      if (!url) return '';
      // return VideoApi.getStreamUrl(url); // 使用API中的方法处理URL
      return url;
    };

    // 初始化Plyr播放器
    const initPlyrPlayer = async () => {
      try {
        addDebugLog('初始化播放器');
        addDebugLog(`视频源数量: ${processedStreamUrls.value.length}`);
        await nextTick();

        if (!videoPlayer.value) {
          addDebugLog('错误: 视频元素不存在');
          return;
        }

        // 销毁旧播放器实例
        destroyPlyrPlayer();

        // 设置初始清晰度为默认清晰度
        currentQuality.value = defaultQuality.value;

        // 记录清晰度设置
        addDebugLog(`清晰度选项: ${qualityOptions.value.join(', ')}`);
        addDebugLog(`默认清晰度: ${defaultQuality.value || '未设置'}`);

        // 初始化播放器
        plyrPlayer.value = new Plyr(videoPlayer.value, {
          controls: [
            'play-large', 'rewind', 'play', 'fast-forward', 'progress',
            'current-time', 'duration', 'mute', 'volume', 'settings',
            'pip', 'fullscreen'
          ],
          settings: ['captions', 'quality', 'speed', 'loop'],
          quality: {
            default: defaultQuality.value,
            options: qualityOptions.value
          },
          speed: {selected: 1, options: [0.5, 0.75, 1, 1.25, 1.5, 1.75, 2]},
          displayDuration: true,
          resetOnEnd: false,
          hideControls: true,
          clickToPlay: true,
          fullscreen: {enabled: true, fallback: true, iosNative: true},
          ratio: '16:9'
        });

        // 确保播放器容器样式正确
        // if (plyrPlayer.value.elements.container) {
        //   plyrPlayer.value.elements.container.style.width = '100%';
        //   plyrPlayer.value.elements.container.style.height = '100%';
        //   plyrPlayer.value.elements.container.style.minHeight = '100%';
        //   addDebugLog('播放器容器样式已设置');
        // }

        // 监听播放器事件
        plyrPlayer.value.on('ready', () => {
          addDebugLog('播放器已准备就绪');
          
          // 确保默认清晰度被正确应用
          if (currentQuality.value && plyrPlayer.value) {
            plyrPlayer.value.quality = currentQuality.value;
            addDebugLog(`已设置初始清晰度为: ${currentQuality.value}p`);
          }

          // 自动播放
          setTimeout(() => {
            if (plyrPlayer.value && !plyrPlayer.value.playing) {
              plyrPlayer.value.play().catch((error: any) => {
                addDebugLog(`自动播放失败: ${error.message || error}`);
              });
            }
          }, 100);
        });

        plyrPlayer.value.on('play', () => {
          addDebugLog('视频开始播放');
          emit('play-started');
        });

        plyrPlayer.value.on('error', (error: any) => {
          const errorMessage = error.detail ? error.detail.message : '未知错误';
          addDebugLog(`播放器错误: ${errorMessage}`);
          emit('play-error', errorMessage);
        });

      } catch (error: any) {
        console.error('初始化播放器失败:', error);
        addDebugLog(`初始化播放器失败: ${error}`);
        emit('play-error', `初始化播放器失败: ${error}`);
      }
    };

    // 销毁播放器实例
    const destroyPlyrPlayer = () => {
      if (plyrPlayer.value) {
        plyrPlayer.value.destroy();
        plyrPlayer.value = null;
        addDebugLog('播放器实例已销毁');
      }
    };

    const playVideo = async () => {
      if (processedStreamUrls.value && processedStreamUrls.value.length > 0) {
        addDebugLog(`开始播放视频，可用源数量: ${processedStreamUrls.value.length}`);
        isPlaying.value = true;
        await nextTick();
        await initPlyrPlayer();
      } else {
        addDebugLog('错误: 视频没有可用的流URL');
        emit('play-error', '视频没有可用的流URL');
      }
    };

    const handleVideoError = (event: Event) => {
      addDebugLog('视频加载失败');
      if (event.target && (event.target as HTMLVideoElement).error) {
        const errorCode = (event.target as HTMLVideoElement).error?.code;
        const errorMessage = (event.target as HTMLVideoElement).error?.message;
        addDebugLog(`错误代码: ${errorCode}, 错误信息: ${errorMessage}`);
        emit('play-error', `加载失败(${errorCode}): ${errorMessage}`);
      }
    };

    // 监听自动播放属性
    watch(() => props.autoPlay, (newVal) => {
      if (newVal && !isPlaying.value) {
        playVideo();
      }
    });

    onMounted(() => {
      // 添加容器信息到调试日志
      addDebugLog(`组件已挂载，视频标题: ${props.title}`);
      addDebugLog(`封面URL: ${props.coverUrl}`);
      
      // 自动播放
      if (props.autoPlay) {
        playVideo();
      }
    });

    onUnmounted(() => {
      destroyPlyrPlayer();
      addDebugLog('组件已卸载');
    });

    return {
      isPlaying,
      videoPlayer,
      processedStreamUrls,
      getStreamUrl,
      getQualityValue,
      debugLogs,
      playVideo,
      handleVideoError,
      currentQuality
    };
  }
});
</script>

<style scoped>
.video-player-container {
  width: 100%;
  border-radius: 8px;
  overflow: hidden;
  background-color: #000;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.4);
}

.video-player {
  width: 100%;
  position: relative;
  padding-top: 56.25%; /* 16:9 比例 */
  overflow: hidden;
}

.video-element {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  object-fit: contain;
  background-color: #000;
  z-index: 1;
}

.video-placeholder {
  position: relative;
  width: 100%;
  padding-top: 56.25%; /* 16:9 比例 */
  cursor: pointer;
}

.video-placeholder img {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.play-button {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 70px;
  height: 70px;
  background-color: rgba(0, 0, 0, 0.6);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.3s;
}

.play-button svg {
  fill: white;
  width: 40px;
  height: 40px;
}

.video-placeholder:hover .play-button {
  transform: translate(-50%, -50%) scale(1.1);
  background-color: rgba(0, 0, 0, 0.8);
}

/* 调试信息样式 */
.debug-info {
  margin: 20px 0;
  padding: 15px;
  background: #1f1f23;
  border-radius: 8px;
  border: 1px solid #3f3f46;
  max-height: 200px;
  overflow-y: auto;
}

.debug-info h4 {
  color: #ec4899;
  margin: 0 0 10px 0;
  font-size: 14px;
}

.debug-log {
  font-family: 'Courier New', monospace;
  font-size: 12px;
  color: #a1a1aa;
  margin-bottom: 5px;
  word-break: break-all;
}

/* Plyr播放器全局样式变量 */
:global(.plyr) {
  --plyr-color-main: #ec4899;
  --plyr-range-fill-background: #ec4899;
  --plyr-video-controls-background: linear-gradient(rgba(0, 0, 0, 0), rgba(0, 0, 0, 0.7));
  --plyr-menu-background: #27272a;
  --plyr-menu-color: #e4e4e7;
  --plyr-menu-item-text-color: #a1a1aa;
  --plyr-video-control-color: #e4e4e7;
  --plyr-video-control-color-hover: #ec4899;
  --plyr-badge-background: #ec4899;
  border-radius: 8px;
  overflow: hidden;
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
}

/* 确保视频元素正确显示 */
:global(.plyr__video-wrapper) {
  background: #000;
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  padding-top: 0 !important;
}

:global(.plyr video) {
  width: 100% !important;
  height: 100% !important;
  object-fit: contain;
  background: #000;
}
</style> 