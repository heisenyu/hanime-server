<template>
  <div class="page-container">
    <h2>新番列表</h2>
    <p>这是新番列表页面，目前正在开发中...</p>
  </div>
</template>

<script lang="ts">
import { defineComponent } from 'vue';

export default defineComponent({
  name: 'CalendarPage',
  setup() {
    return {};
  }
});
</script>

<style scoped>
.page-container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px;
  background-color: #18181b;
  min-height: 100vh;
  color: #fff;
}

h2 {
  margin-bottom: 20px;
  color: var(--primary-color);
}
</style> 