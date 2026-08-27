<script setup lang="ts">
/**
 * 首页：输入区 + 音色选择，生成后跳转任务详情页。
 */
import { useRouter } from 'vue-router'
import TaskInputPanel from '@/components/TaskInputPanel.vue'

const router = useRouter()

function onCreated(taskId: number) {
  router.push(`/task/${taskId}`)
}
</script>

<template>
  <div class="home">
    <h2 class="home__title">文字转语音</h2>
    <p class="home__subtitle">选择音色，输入文字，一键生成自然语音</p>
    <TaskInputPanel @created="onCreated" />
  </div>
</template>

<style scoped>
.home__title {
  text-align: center;
  margin: 8px 0 4px;
  font-size: 22px;
  color: #303133;
}

.home__subtitle {
  text-align: center;
  color: #909399;
  font-size: 13px;
  margin: 0 0 24px;
}
</style>
