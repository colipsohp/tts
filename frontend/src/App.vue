<script setup lang="ts">
/**
 * 整体布局：左侧 Sidebar + 右侧内容区（router-view）。
 */
import AppSidebar from '@/components/AppSidebar.vue'
</script>

<template>
  <div class="app-layout">
    <AppSidebar class="app-layout__sidebar" />
    <main class="app-layout__main">
      <router-view />
    </main>
  </div>
</template>

<style scoped>
.app-layout {
  display: flex;
  height: 100vh;
  overflow: hidden;
}

.app-layout__sidebar {
  flex-shrink: 0;
}

.app-layout__main {
  flex: 1;
  min-width: 0;
  overflow-y: auto;
  padding: 24px;
}
</style>
