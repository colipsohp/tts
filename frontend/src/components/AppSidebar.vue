<script setup lang="ts">
/**
 * 左侧导航栏：品牌区 + 新建任务入口 + 最近历史任务列表（含搜索过滤）。
 */
import { onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '@/api'
import { sidebarVersion } from '@/state'
import type { TtsTask } from '@/types'
import TaskStatusTag from './TaskStatusTag.vue'

const router = useRouter()
const tasks = ref<TtsTask[]>([])
const loading = ref(false)
const search = ref('')
const total = ref(0)
let searchTimer: ReturnType<typeof setTimeout> | undefined

async function loadTasks() {
  loading.value = true
  try {
    const data = await api.listTasks({ search: search.value || undefined, pageSize: 30 })
    tasks.value = data.list
    total.value = data.total
  } finally {
    loading.value = false
  }
}

watch(search, () => {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(loadTasks, 300)
})

// 任务创建/重新生成后自动刷新列表
watch(sidebarVersion, loadTasks)

onMounted(loadTasks)

function goNewTask() {
  router.push('/')
}

function goDetail(id: number) {
  router.push(`/task/${id}`)
}

function formatTime(iso: string | null): string {
  if (!iso) return ''
  const date = new Date(iso)
  const now = Date.now()
  const diff = now - date.getTime()
  const minute = 60_000
  const hour = 60 * minute
  const day = 24 * hour
  if (diff < minute) return '刚刚'
  if (diff < hour) return `${Math.floor(diff / minute)} 分钟前`
  if (diff < day) return `${Math.floor(diff / hour)} 小时前`
  if (diff < 7 * day) return `${Math.floor(diff / day)} 天前`
  const m = String(date.getMonth() + 1).padStart(2, '0')
  const d = String(date.getDate()).padStart(2, '0')
  return `${date.getFullYear()}-${m}-${d}`
}

defineExpose({ reload: loadTasks })
</script>

<template>
  <aside class="app-sidebar">
    <div class="app-sidebar__brand">
      <el-icon :size="22" color="#409eff"><Microphone /></el-icon>
      <span class="app-sidebar__title">TTS 语音合成</span>
    </div>

    <div class="app-sidebar__new">
      <el-button type="primary" style="width: 100%" @click="goNewTask">
        <el-icon style="margin-right: 4px"><Plus /></el-icon>
        新建任务
      </el-button>
    </div>

    <div class="app-sidebar__search">
      <el-input
        v-model="search"
        placeholder="搜索历史任务"
        clearable
        :prefix-icon="'Search'"
        size="default"
      />
    </div>

    <div class="app-sidebar__group-title">
      <span>最近</span>
      <span class="app-sidebar__count" v-if="total > 0">{{ total }}</span>
    </div>

    <div v-loading="loading" class="app-sidebar__list">
      <template v-if="tasks.length">
        <div
          v-for="task in tasks"
          :key="task.id"
          class="app-sidebar__item"
          @click="goDetail(task.id)"
        >
          <div class="app-sidebar__item-top">
            <TaskStatusTag :status="task.status" />
            <span class="app-sidebar__time">{{ formatTime(task.createdAt) }}</span>
          </div>
          <div class="app-sidebar__voice text-ellipsis">
            <el-icon><Headset /></el-icon>
            {{ task.voice.name }}
          </div>
          <div class="app-sidebar__text text-ellipsis">{{ task.text }}</div>
        </div>
      </template>
      <el-empty v-else-if="!loading" description="暂无历史任务" :image-size="60" />
    </div>
  </aside>
</template>

<style scoped>
.app-sidebar {
  width: 280px;
  height: 100%;
  display: flex;
  flex-direction: column;
  background: #fff;
  border-right: 1px solid #e4e7ed;
  padding: 16px 12px;
  overflow: hidden;
}

.app-sidebar__brand {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 6px 16px;
}

.app-sidebar__title {
  font-size: 17px;
  font-weight: 700;
  color: #303133;
}

.app-sidebar__new {
  margin-bottom: 12px;
}

.app-sidebar__search {
  margin-bottom: 14px;
}

.app-sidebar__group-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 13px;
  color: #909399;
  padding: 0 4px 8px;
}

.app-sidebar__count {
  background: #f0f2f5;
  border-radius: 10px;
  padding: 0 8px;
  font-size: 12px;
}

.app-sidebar__list {
  flex: 1;
  overflow-y: auto;
  min-height: 0;
}

.app-sidebar__item {
  padding: 10px 10px;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.15s;
  margin-bottom: 4px;
}

.app-sidebar__item:hover {
  background: #f5f7fa;
}

.app-sidebar__item-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 6px;
}

.app-sidebar__time {
  font-size: 11px;
  color: #c0c4cc;
}

.app-sidebar__voice {
  font-size: 13px;
  font-weight: 600;
  color: #303133;
  display: flex;
  align-items: center;
  gap: 4px;
  margin-bottom: 4px;
}

.app-sidebar__text {
  font-size: 12px;
  color: #909399;
}
</style>
