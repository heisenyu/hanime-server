<template>
  <div class="sidebar-container" :class="{ 'open': isOpen }">
    <div class="sidebar-overlay" @click="closeSidebar"></div>
    <aside class="sidebar">
      <div class="user-info">
        <div class="avatar">
          <span>H1</span>
        </div>
        <div class="login-status">未登录</div>
      </div>
      
      <nav class="nav-menu">
        <router-link to="/" class="nav-item" @click="closeSidebar">
          <el-icon :size="20"><HomeFilled /></el-icon> 主页
        </router-link>
        <router-link to="/settings" class="nav-item" @click="closeSidebar">
          <el-icon :size="20"><Setting /></el-icon> 设置
        </router-link>
        <div class="nav-item" @click="toggleTheme">
          <el-icon :size="20">
            <component :is="currentTheme === 'dark' ? 'Sunny' : 'Moon'" />
          </el-icon>
          {{ currentTheme === 'dark' ? '浅色模式' : '深色模式' }}
        </div>
      </nav>
      
      <div class="divider"></div>
      
      <nav class="nav-menu">
        <div class="menu-title">我的清单</div>
        <router-link to="/history" class="nav-item" @click="closeSidebar">
          <el-icon :size="20"><Timer /></el-icon> 稍后观看
        </router-link>
        <router-link to="/favorites" class="nav-item" @click="closeSidebar">
          <el-icon :size="20"><Star /></el-icon> 喜欢的影片
        </router-link>
        <router-link to="/playlists" class="nav-item" @click="closeSidebar">
          <el-icon :size="20"><Film /></el-icon> 播放清单
        </router-link>
      </nav>
      
      <div class="divider"></div>
      
      <nav class="nav-menu">
        <div class="menu-title">影片</div>
        <router-link to="/history" class="nav-item" @click="closeSidebar">
          <el-icon :size="20"><VideoCamera /></el-icon> 观看历史
        </router-link>
        <router-link to="/downloads" class="nav-item" @click="closeSidebar">
          <el-icon :size="20"><Download /></el-icon> 下载
        </router-link>
      </nav>
    </aside>
  </div>
</template>

<script lang="ts">
import { defineComponent, ref } from 'vue';
import { 
  HomeFilled, 
  Setting, 
  Moon, 
  Sunny, 
  Timer, 
  Star, 
  Film, 
  VideoCamera, 
  Download 
} from '@element-plus/icons-vue';

export default defineComponent({
  name: 'AppSidebar',
  components: {
    HomeFilled,
    Setting,
    Moon,
    Sunny,
    Timer,
    Star,
    Film,
    VideoCamera,
    Download
  },
  props: {
    isOpen: {
      type: Boolean,
      default: false
    }
  },
  emits: ['close', 'toggle-theme'],
  setup(props, { emit }) {
    const currentTheme = ref(localStorage.getItem('theme') || 'dark');

    // 获取当前主题
    const updateCurrentTheme = () => {
      currentTheme.value = localStorage.getItem('theme') || 'dark';
    };
    
    const closeSidebar = () => {
      emit('close');
    };
    
    const toggleTheme = () => {
      emit('toggle-theme');
      // 切换后需要更新本地的主题状态
      setTimeout(updateCurrentTheme, 100);
    };
    
    return {
      currentTheme,
      closeSidebar,
      toggleTheme
    };
  }
});
</script>

<style scoped>
.sidebar-container {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  z-index: 1000;
  pointer-events: none;
}

.sidebar-container.open {
  pointer-events: auto;
}

.sidebar-overlay {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-color: rgba(0, 0, 0, 0.5);
  opacity: 0;
  transition: opacity 0.3s ease;
  pointer-events: none;
}

.sidebar-container.open .sidebar-overlay {
  opacity: 1;
  pointer-events: auto;
}

.sidebar {
  position: absolute;
  top: 0;
  left: -280px;
  width: 280px;
  height: 100%;
  background-color: var(--bg-secondary-color);
  transition: left 0.3s ease;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  padding: 20px 0;
}

.sidebar-container.open .sidebar {
  left: 0;
}

.user-info {
  display: flex;
  align-items: center;
  padding: 0 20px 20px;
}

.avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background-color: var(--bg-color);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--primary-color);
  font-weight: bold;
  margin-right: 15px;
}

.login-status {
  color: var(--text-secondary-color);
  font-size: 14px;
}

.nav-menu {
  padding: 10px 0;
}

.menu-title {
  padding: 10px 20px;
  color: var(--text-secondary-color);
  font-size: 14px;
  text-transform: uppercase;
}

.nav-item {
  display: flex;
  align-items: center;
  padding: 12px 20px;
  color: var(--text-color);
  text-decoration: none;
  cursor: pointer;
  transition: background-color 0.2s;
}

.nav-item:hover {
  background-color: var(--hover-bg-color);
}

.nav-item .el-icon {
  margin-right: 15px;
}

.divider {
  height: 1px;
  background-color: var(--border-color);
  margin: 5px 0;
}
</style> 