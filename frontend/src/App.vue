<script setup lang="ts">
import { ref, onMounted, watch } from 'vue';
import AppHeader from "./components/AppHeader.vue";
import AppSidebar from "./components/AppSidebar.vue";
import './assets/styles/common.css';
import { useDownloadStore } from './stores/download';

const sidebarOpen = ref(false);
const theme = ref(localStorage.getItem('theme') || 'dark');
const downloadStore = useDownloadStore();

// 切换侧边栏
const toggleSidebar = () => {
  sidebarOpen.value = !sidebarOpen.value;
};

// 关闭侧边栏
const closeSidebar = () => {
  sidebarOpen.value = false;
};

// 切换主题
const toggleTheme = () => {
  theme.value = theme.value === 'dark' ? 'light' : 'dark';
  localStorage.setItem('theme', theme.value);
  setTheme();
};

// 应用主题到 HTML 元素
const setTheme = () => {
  const htmlEl = document.documentElement;
  if (theme.value === 'dark') {
    htmlEl.classList.add('dark');
    htmlEl.classList.remove('light');
  } else {
    htmlEl.classList.add('light');
    htmlEl.classList.remove('dark');
  }
};

// 监听主题变化
watch(theme, () => {
  setTheme();
});

// 组件挂载时设置主题
onMounted(() => {
  // 确保默认使用暗黑模式
  if (!localStorage.getItem('theme')) {
    localStorage.setItem('theme', 'dark');
    theme.value = 'dark';
  }
  setTheme();
  
  // 初始化下载存储和WebSocket连接
  downloadStore.initializeDownloads();
});
</script>

<template>
  <div class="app">
    <AppHeader 
      :sidebar-open="sidebarOpen"
      :current-theme="theme"
      @toggle-sidebar="toggleSidebar"
      @toggle-theme="toggleTheme"
    />
    
    <AppSidebar 
      :is-open="sidebarOpen"
      @close="closeSidebar"
      @toggle-theme="toggleTheme"
    />
    
    <main class="app-content">
      <router-view/>
    </main>

    <footer class="app-footer">
      <div class="container">
        <p>&copy; {{ new Date().getFullYear() }} Hanime View. 仅供学习研究使用。</p>
      </div>
    </footer>
  </div>
</template>

<style>
/* 基础样式设置 */
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: 'Roboto', sans-serif;
}

.app {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}

.app-content {
  flex: 1;
  margin-top: 10px;
}

.app-footer {
  background-color: var(--bg-secondary-color);
  border-top: 1px solid var(--border-color);
  padding: 20px 0;
  margin-top: 30px;
  text-align: center;
  color: var(--text-secondary-color);
  font-size: 14px;
}

/* Element Plus 图标全局样式 */
.el-icon {
  vertical-align: middle;
}
</style>
