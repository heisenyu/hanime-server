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

// 扩展window接口，添加自定义属性
declare global {
  interface Window {
    plyrResizeObservers?: ResizeObserver[];
  }
}

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
    const isMobile = ref(false);

    // 检测是否为移动设备
    const checkMobileDevice = () => {
      const isMobileUserAgent = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
      const isNarrowScreen = window.innerWidth <= 768; // 添加屏幕宽度检查
      
      // 同时考虑用户代理和屏幕宽度
      isMobile.value = isMobileUserAgent || isNarrowScreen;
      addDebugLog(`设备类型: ${isMobile.value ? '移动设备' : '桌面设备'} (UA: ${isMobileUserAgent}, 宽度: ${window.innerWidth}px)`);
      return isMobile.value;
    };

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

        // 检测设备类型
        const isMobileDevice = checkMobileDevice();
        
        // 根据设备类型选择不同的控制选项
        const controlOptions = isMobileDevice 
          ? [
              'play-large', 'rewind', 'play', 'fast-forward', 'progress',
              'mute', 'settings', 'pip', 'fullscreen'
            ]
          : [
              'play-large', 'rewind', 'play', 'fast-forward', 'progress',
              'current-time', 'duration', 'mute', 'volume', 'settings',
              'pip', 'fullscreen'
            ];

        // 初始化播放器
        plyrPlayer.value = new Plyr(videoPlayer.value, {
          controls: controlOptions,
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

        // 监听播放器事件
        plyrPlayer.value.on('ready', () => {
          addDebugLog('播放器已准备就绪');
          
          // 确保默认清晰度被正确应用
          if (currentQuality.value && plyrPlayer.value) {
            plyrPlayer.value.quality = currentQuality.value;
            addDebugLog(`已设置初始清晰度为: ${currentQuality.value}p`);
          }

          // 对移动设备应用自定义样式
          if (isMobileDevice) {
            applyMobileStyles();
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

    // 为移动设备应用自定义样式
    const applyMobileStyles = () => {
      addDebugLog('应用移动设备样式');
      
      // 给播放器添加自定义事件监听，确保DOM已完全加载
      if (plyrPlayer.value) {
        // 在播放器就绪后添加时间显示
        plyrPlayer.value.on('ready', () => {
          addDebugLog('播放器就绪，尝试添加时间显示');
          setTimeout(createTimeDisplay, 100);
        });
        
        // 监听控制栏显示/隐藏事件
        plyrPlayer.value.on('controlsshown', () => {
          showTimeDisplay();
        });
        
        plyrPlayer.value.on('controlshidden', () => {
          hideTimeDisplay();
        });
      }
      
      // 多次尝试创建时间显示，确保DOM正常加载后能添加
      setTimeout(createTimeDisplay, 200);
      setTimeout(createTimeDisplay, 500);
      setTimeout(createTimeDisplay, 1000);
    };
    
    // 显示时间元素
    const showTimeDisplay = () => {
      const container = plyrPlayer.value?.elements?.container;
      if (!container) return;
      
      const currentTimeEl = container.querySelector('.plyr-custom-time-current');
      const durationEl = container.querySelector('.plyr-custom-time-duration');
      
      if (currentTimeEl) currentTimeEl.style.opacity = '1';
      if (durationEl) durationEl.style.opacity = '1';
    };
    
    // 隐藏时间元素
    const hideTimeDisplay = () => {
      const container = plyrPlayer.value?.elements?.container;
      if (!container) return;
      
      const currentTimeEl = container.querySelector('.plyr-custom-time-current');
      const durationEl = container.querySelector('.plyr-custom-time-duration');
      
      if (currentTimeEl) currentTimeEl.style.opacity = '0';
      if (durationEl) durationEl.style.opacity = '0';
    };
    
    // 创建时间显示元素
    const createTimeDisplay = () => {
      try {
        // 获取播放器容器
        const container = plyrPlayer.value?.elements?.container;
        if (!container) {
          addDebugLog('获取播放器容器失败');
          return;
        }
        
        // 检查是否已经存在自定义时间容器
        if (container.querySelector('.plyr-custom-time-current')) {
          addDebugLog('时间容器已存在，更新显示');
          updateTimeDisplay();
          return;
        }
        
        // 获取进度条容器
        const progressContainer = container.querySelector('.plyr__progress__container');
        if (!progressContainer) {
          addDebugLog('获取进度条容器失败');
          return;
        }
        
        // 创建当前时间显示元素
        const currentTimeEl = document.createElement('div');
        currentTimeEl.className = 'plyr-custom-time-current';
        setTimeElementStyles(currentTimeEl, true);
        
        // 创建总时长显示元素
        const durationEl = document.createElement('div');
        durationEl.className = 'plyr-custom-time-duration';
        setTimeElementStyles(durationEl, false);
        
        // 添加到容器中
        container.appendChild(currentTimeEl);
        container.appendChild(durationEl);
        
        // 调整元素位置，使其更接近进度条上方（减小间距）
        positionTimeElements(progressContainer, currentTimeEl, durationEl);
        
        addDebugLog('创建了新的时间显示元素');
        
        // 立即更新时间
        updateTimeDisplay();
        
        // 添加时间更新事件监听
        if (plyrPlayer.value) {
          plyrPlayer.value.on('timeupdate', updateTimeDisplay);
          
          // 初始状态与控制栏保持一致
          if (plyrPlayer.value.controls) {
            showTimeDisplay();
          } else {
            hideTimeDisplay();
          }
          
          addDebugLog('添加了时间更新和显示/隐藏事件监听');
        }
      } catch (err) {
        addDebugLog(`创建时间显示失败: ${err}`);
      }
    };
    
    // 设置时间元素的基础样式
    const setTimeElementStyles = (element: HTMLElement, isCurrentTime: boolean) => {
      element.style.position = 'absolute';
      element.style.color = 'rgba(255, 255, 255, 0.9)';
      element.style.fontSize = '12px';
      element.style.fontWeight = '400';
      element.style.zIndex = '10';
      element.style.transition = 'opacity 0.2s ease';
      element.style.textShadow = '0 1px 2px rgba(0, 0, 0, 0.7)';
      element.style.fontFamily = '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif';
      element.style.lineHeight = '1';
      
      // 左右对齐
      if (isCurrentTime) {
        element.style.left = '0';
        element.style.textAlign = 'left';
      } else {
        element.style.right = '0';
        element.style.textAlign = 'right';
      }
    };
    
    // 根据进度条位置调整时间元素位置
    const positionTimeElements = (progressContainer: Element, currentTimeEl: HTMLElement, durationEl: HTMLElement) => {
      try {
        // 使用ResizeObserver监听进度条位置和尺寸变化
        const resizeObserver = new ResizeObserver(() => {
          const rect = progressContainer.getBoundingClientRect();
          const containerRect = progressContainer.closest('.plyr__controls')?.getBoundingClientRect();
          
          if (rect && containerRect) {
            // 计算相对于控制栏的位置
            const leftOffset = rect.left - containerRect.left;
            const rightOffset = containerRect.right - rect.right;
            
            // 设置位置，使其更接近进度条上方（减小间距）
            currentTimeEl.style.bottom = `${containerRect.height}px`;
            durationEl.style.bottom = `${containerRect.height}px`;
            
            // 水平对齐
            currentTimeEl.style.left = `${leftOffset}px`;
            durationEl.style.right = `${rightOffset}px`;
            
            // 宽度设置为进度条的宽度，这样左右对齐才准确
            currentTimeEl.style.width = `${rect.width * 0.5}px`;
            durationEl.style.width = `${rect.width * 0.5}px`;
          }
        });
        
        resizeObserver.observe(progressContainer);
        
        // 保存observer引用以便组件卸载时移除
        if (!window.plyrResizeObservers) window.plyrResizeObservers = [];
        window.plyrResizeObservers.push(resizeObserver);
        
      } catch (err) {
        addDebugLog(`调整时间元素位置失败: ${err}`);
        
        // 降级方案：使用固定位置，减小间距使其更接近进度条
        currentTimeEl.style.bottom = '35px';
        currentTimeEl.style.left = '10px';
        durationEl.style.bottom = '35px';
        durationEl.style.right = '10px';
      }
    };
    
    // 更新时间显示
    const updateTimeDisplay = () => {
      try {
        const container = plyrPlayer.value?.elements?.container;
        if (!container) return;
        
        const currentTimeEl = container.querySelector('.plyr-custom-time-current');
        const durationEl = container.querySelector('.plyr-custom-time-duration');
        if (!currentTimeEl || !durationEl || !plyrPlayer.value) return;
        
        const currentTime = formatTime(plyrPlayer.value.currentTime || 0);
        const duration = formatTime(plyrPlayer.value.duration || 0);
        
        currentTimeEl.textContent = currentTime;
        durationEl.textContent = duration;
      } catch (err) {
        // 静默错误处理
      }
    };

    // 格式化时间为 MM:SS 或 HH:MM:SS 格式
    const formatTime = (seconds: number): string => {
      if (isNaN(seconds)) return '00:00';
      
      // 对于超过1小时的视频，显示小时
      if (seconds >= 3600) {
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        const remainingSeconds = Math.floor(seconds % 60);
        
        const formattedHours = String(hours).padStart(2, '0');
        const formattedMinutes = String(minutes).padStart(2, '0');
        const formattedSeconds = String(remainingSeconds).padStart(2, '0');
        
        return `${formattedHours}:${formattedMinutes}:${formattedSeconds}`;
      } else {
        const minutes = Math.floor(seconds / 60);
        const remainingSeconds = Math.floor(seconds % 60);
        
        const formattedMinutes = String(minutes).padStart(2, '0');
        const formattedSeconds = String(remainingSeconds).padStart(2, '0');
        
        return `${formattedMinutes}:${formattedSeconds}`;
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

    // 重置播放器
    const reset = () => {
      addDebugLog('重置播放器');
      
      // 停止视频播放
      if (plyrPlayer.value) {
        try {
          plyrPlayer.value.pause();
          
          // 重置时间位置
          plyrPlayer.value.currentTime = 0;
          
          // 销毁播放器
          destroyPlyrPlayer();
          
          addDebugLog('播放器已暂停并重置');
        } catch (e) {
          console.error('重置播放器失败:', e);
          addDebugLog(`重置播放器失败: ${e}`);
        }
      }
      
      // 重置回到封面状态
      isPlaying.value = false;
    };

    // 监听自动播放属性
    watch(() => props.autoPlay, (newVal) => {
      if (newVal && !isPlaying.value) {
        playVideo();
      }
    });

    // 监听窗口大小变化
    const handleWindowResize = () => {
      const wasMobile = isMobile.value;
      const newIsMobile = checkMobileDevice();
      
      // 如果设备类型发生变化，需要重新初始化播放器
      if (wasMobile !== newIsMobile && plyrPlayer.value) {
        addDebugLog(`设备类型切换: ${wasMobile ? '移动→桌面' : '桌面→移动'}`);
        
        // 延迟重新初始化以避免频繁重载
        setTimeout(() => {
          if (isPlaying.value) {
            const currentTime = plyrPlayer.value.currentTime;
            destroyPlyrPlayer();
            initPlyrPlayer().then(() => {
              // 恢复播放位置
              if (plyrPlayer.value) {
                plyrPlayer.value.currentTime = currentTime;
              }
            });
          }
        }, 300);
      }
    };

    onMounted(() => {
      // 添加容器信息到调试日志
      addDebugLog(`组件已挂载，视频标题: ${props.title}`);
      addDebugLog(`封面URL: ${props.coverUrl}`);
      
      // 添加窗口大小变化监听
      window.addEventListener('resize', handleWindowResize);
      
      // 自动播放
      if (props.autoPlay) {
        playVideo();
      }
    });

    onUnmounted(() => {
      // 移除窗口大小变化监听
      window.removeEventListener('resize', handleWindowResize);
      
      // 清理所有ResizeObserver
      if (window.plyrResizeObservers && window.plyrResizeObservers.length) {
        window.plyrResizeObservers.forEach(observer => observer.disconnect());
        window.plyrResizeObservers = [];
        addDebugLog('已清理ResizeObserver');
      }
      
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
      currentQuality,
      reset
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

/* 自定义时间显示样式 - 不需要这些全局样式，因为我们使用内联样式 */
/* :global(.plyr-custom-time) {
  display: flex;
  align-items: center;
  font-size: 13px;
  color: #fff;
  padding: 0 5px;
  white-space: nowrap;
  margin-right: 5px;
  margin-left: -5px;
  min-width: 80px;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
} */

@media (max-width: 768px) {
  /* 移动端隐藏控制栏中的时间显示 */
  :global(.plyr__controls .plyr__time) {
    display: none !important;
  }
  
  /* 确保进度条在移动端有足够的点击区域 */
  :global(.plyr__progress) {
    margin-top: 0;
    margin-bottom: 0;
  }
  
  :global(.plyr__progress input[type='range']) {
    height: 18px !important;
  }
  
  /* 移动端增大控制按钮间距 */
  :global(.plyr__controls button) {
    padding: 5px !important;
  }
  
  /* 优化移动端控制栏布局 */
  :global(.plyr__controls) {
    flex-wrap: nowrap !important;
    padding: 5px !important;
    align-items: center;
  }
  
  /* 确保进度条有足够空间 */
  :global(.plyr__progress__container) {
    flex: 1;
    min-width: 40px;
    margin-right: 0;
  }
}
</style> 