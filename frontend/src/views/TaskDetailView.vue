<script setup lang="ts">
/**
 * 任务详情页：音色信息 + 文案 + 生成结果（试听/下载/失败重试）。
 * 生成中轮询任务状态（默认 2s）。
 */
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { api } from '@/api'
import { bumpSidebar } from '@/state'
import type { TtsTask } from '@/types'
import AudioPlayer from '@/components/AudioPlayer.vue'
import TaskStatusTag from '@/components/TaskStatusTag.vue'

const route = useRoute()
const router = useRouter()

const task = ref<TtsTask | null>(null)
const loading = ref(false)
const regenerating = ref(false)
let pollTimer: ReturnType<typeof setInterval> | undefined

const taskId = computed(() => Number(route.params.id))

const isActive = computed(() => !!task.value && ['pending', 'running'].includes(task.value.status))

const previewAudio = new Audio()
let previewSrc = ''

async function loadTask() {
  loading.value = true
  try {
    task.value = await api.getTask(taskId.value)
  } catch {
    task.value = null
    ElMessage.error('任务不存在或加载失败')
  } finally {
    loading.value = false
  }
}

function startPolling() {
  stopPolling()
  pollTimer = setInterval(() => {
    void loadTask()
  }, 2000)
}

function stopPolling() {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = undefined
  }
}

watch(isActive, (active) => {
  if (active) startPolling()
  else stopPolling()
})

onMounted(() => {
  loadTask().then(() => {
    if (isActive.value) startPolling()
  })
})

onBeforeUnmount(() => {
  stopPolling()
  previewAudio.pause()
})

function togglePreview() {
  if (!task.value) return
  if (!previewAudio.paused && previewSrc) {
    previewAudio.pause()
    previewSrc = ''
    return
  }
  const src = api.voiceAudioUrl(task.value.voice.id)
  if (previewSrc !== src) {
    previewSrc = src
    previewAudio.src = src
  }
  void previewAudio.play()
}

function copyText() {
  if (!task.value) return
  void navigator.clipboard.writeText(task.value.text)
  ElMessage.success('文案已复制')
}

function download() {
  if (!task.value) return
  const a = document.createElement('a')
  a.href = api.taskDownloadUrl(task.value.id)
  a.download = ''
  document.body.appendChild(a)
  a.click()
  a.remove()
}

async function regenerate() {
  regenerating.value = true
  try {
    const newTask = await api.regenerateTask(taskId.value)
    ElMessage.success('已重新生成')
    bumpSidebar()
    router.push(`/task/${newTask.id}`)
  } catch {
    ElMessage.error('重新生成失败')
  } finally {
    regenerating.value = false
  }
}

function goBack() {
  router.push('/')
}

const genderLabel = computed(() => {
  const g = task.value?.voice.gender
  if (g === 'male') return '男'
  if (g === 'female') return '女'
  return '未知'
})
</script>

<template>
  <div v-loading="loading" class="task-detail">
    <div class="task-detail__back">
      <el-button text :icon="'ArrowLeft'" @click="goBack">返回首页</el-button>
      <TaskStatusTag v-if="task" :status="task.status" />
    </div>

    <template v-if="task">
      <!-- 音色信息 -->
      <section class="card">
        <h3 class="card__title">音色信息</h3>
        <div class="card__voice">
          <div class="card__voice-avatar">{{ (task.voice.name || '声').charAt(0) }}</div>
          <div class="card__voice-meta">
            <div class="card__voice-name">{{ task.voice.name }}</div>
            <div class="card__voice-tags">
              <el-tag size="small" type="primary" effect="plain">{{ genderLabel }}</el-tag>
              <el-tag size="small" :type="task.voice.isBuiltin ? 'success' : 'warning'" effect="plain">
                {{ task.voice.isBuiltin ? '内置' : '自定义' }}
              </el-tag>
            </div>
          </div>
          <el-button size="small" :icon="'VideoPlay'" @click="togglePreview">试听参考音频</el-button>
        </div>
      </section>

      <!-- 文案 -->
      <section class="card">
        <h3 class="card__title">
          转语音文字
          <el-button text size="small" :icon="'CopyDocument'" @click="copyText">复制</el-button>
        </h3>
        <div class="card__text">{{ task.text }}</div>
      </section>

      <!-- 生成结果 -->
      <section class="card">
        <h3 class="card__title">生成结果</h3>

        <div v-if="task.status === 'succeeded'" class="card__result">
          <AudioPlayer :src="api.taskAudioUrl(task.id)" autoplay />
          <div class="card__result-meta">
            <span v-if="task.durationSeconds">时长：{{ task.durationSeconds }} 秒</span>
            <span>完成时间：{{ task.completedAt ? new Date(task.completedAt).toLocaleString() : '' }}</span>
          </div>
          <el-button type="primary" :icon="'Download'" @click="download">下载音频</el-button>
        </div>

        <div v-else-if="task.status === 'failed'" class="card__result card__result--failed">
          <el-alert type="error" :closable="false" show-icon>
            <template #title>生成失败</template>
            {{ task.errorMessage || '未知错误' }}
          </el-alert>
          <el-button type="primary" :loading="regenerating" @click="regenerate">
            <el-icon style="margin-right: 4px"><Refresh /></el-icon>
            重新生成
          </el-button>
        </div>

        <div v-else class="card__result card__result--loading">
          <el-icon class="is-loading" :size="24" color="#409eff"><Loading /></el-icon>
          <span>正在生成语音，请稍候…</span>
        </div>
      </section>
    </template>

    <el-empty v-else-if="!loading" description="任务不存在" />
  </div>
</template>

<style scoped>
.task-detail {
  max-width: 720px;
  margin: 0 auto;
}

.task-detail__back {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.card {
  background: #fff;
  border-radius: 12px;
  padding: 20px 24px;
  margin-bottom: 16px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);
}

.card__title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin: 0 0 14px;
  font-size: 15px;
  color: #303133;
}

.card__voice {
  display: flex;
  align-items: center;
  gap: 12px;
}

.card__voice-avatar {
  width: 44px;
  height: 44px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  color: #fff;
  background: linear-gradient(135deg, #7c6cf0, #409eff);
  flex-shrink: 0;
}

.card__voice-meta {
  flex: 1;
  min-width: 0;
}

.card__voice-name {
  font-weight: 600;
  margin-bottom: 4px;
}

.card__voice-tags {
  display: flex;
  gap: 4px;
}

.card__text {
  background: #fafafa;
  border: 1px solid #ebeef5;
  border-radius: 8px;
  padding: 14px;
  font-size: 14px;
  line-height: 1.7;
  color: #303133;
  white-space: pre-wrap;
  word-break: break-word;
  max-height: 240px;
  overflow-y: auto;
}

.card__result {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.card__result-meta {
  font-size: 12px;
  color: #909399;
  display: flex;
  gap: 16px;
}

.card__result--failed {
  align-items: flex-start;
}

.card__result--loading {
  align-items: center;
  justify-content: center;
  flex-direction: row;
  color: #909399;
  padding: 30px 0;
}
</style>
