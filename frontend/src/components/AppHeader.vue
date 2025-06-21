<template>
  <header class="app-header">
    <div class="header-left">
      <button class="menu-button" @click="toggleSidebar">
        <el-icon :size="24"><Menu /></el-icon>
      </button>
      <button v-if="showBackButton" class="back-button" @click="goBack">
        <el-icon :size="24"><Back /></el-icon>
      </button>
      <h1 class="app-title" @click="goToHome">Han1meViewer</h1>
    </div>
    <div class="header-right">
      <button class="theme-button" @click="toggleTheme">
        <el-icon :size="24">
          <Moon v-if="currentTheme === 'light'" />
          <Sunny v-else />
        </el-icon>
      </button>
      <button class="calendar-button" @click="goToCalendar">
        <el-icon :size="24"><Calendar /></el-icon>
      </button>
      <button class="search-button" @click="goToSearch">
        <el-icon :size="24"><Search /></el-icon>
      </button>
    </div>
  </header>
</template>

<script lang="ts">
import { defineComponent, computed } from 'vue';
import { useRouter, useRoute } from 'vue-router';
import { Menu, Back, Calendar, Search, Moon, Sunny } from '@element-plus/icons-vue';

export default defineComponent({
  name: 'AppHeader',
  components: {
    Menu,
    Back,
    Calendar,
    Search,
    Moon,
    Sunny
  },
  props: {
    sidebarOpen: {
      type: Boolean,
      default: false
    },
    currentTheme: {
      type: String,
      default: 'dark'
    }
  },
  emits: ['toggle-sidebar', 'toggle-theme'],
  setup(props, { emit }) {
    const router = useRouter();
    const route = useRoute();

    const showBackButton = computed(() => {
      return route.path !== '/';
    });

    const toggleSidebar = () => {
      emit('toggle-sidebar');
    };
    
    const toggleTheme = () => {
      emit('toggle-theme');
    };

    const goBack = () => {
      router.back();
    };

    const goToHome = () => {
      if (route.path !== '/') {
        router.push('/');
      }
    };

    const goToCalendar = () => {
      router.push('/calendar');
    };

    const goToSearch = () => {
      router.push('/search');
    };

    return {
      showBackButton,
      toggleSidebar,
      toggleTheme,
      goBack,
      goToHome,
      goToCalendar,
      goToSearch
    };
  }
});
</script>

<style scoped>
.app-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 15px;
  background-color: var(--bg-color);
  color: var(--text-color);
  position: sticky;
  top: 0;
  z-index: 100;
  border-bottom: 1px solid var(--bg-secondary-color);
}

.header-left, .header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.menu-button, .back-button, .calendar-button, .search-button, .theme-button {
  display: flex;
  align-items: center;
  justify-content: center;
  background: none;
  border: none;
  color: var(--text-color);
  cursor: pointer;
  padding: 6px;
  border-radius: 50%;
  transition: background-color 0.2s;
}

.menu-button:hover, .back-button:hover, .calendar-button:hover, .search-button:hover, .theme-button:hover {
  background-color: var(--hover-bg-color);
}

.app-title {
  margin: 0;
  font-size: 24px;
  font-weight: bold;
  color: var(--primary-color);
  cursor: pointer;
  margin-left: 5px;
}

.header-right {
  margin-left: auto;
}

.nav-links {
  display: flex;
  align-items: center;
  gap: 12px;
}

.nav-link {
  text-decoration: none;
  color: var(--text-color);
  cursor: pointer;
}

@media (max-width: 480px) {
  .app-title {
    font-size: 20px;
  }
}
</style> 