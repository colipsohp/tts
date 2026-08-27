<script setup lang="ts">
/**
 * 中间输入区：已选音色卡片 + 文字输入（含字数）+ 确认生成。
 * 校验：未选音色 / 文字为空时禁用按钮；超长提示。
 */
import { computed, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { api } from '@/api'
import { bumpSidebar } from '@/state'
import type { Voice } from '@/types'
import VoiceSelectorDialog from './VoiceSelectorDialog.vue'

const emit = defineEmits<{
  (e: 'created', taskId: number): void
}>()

const selectedVoice = ref<Voice | null>(null)
const text = ref('')
const generating = ref(false)
const selectorVisible = ref(false)

const MAX_LENGTH = 2000

const canGenerate = computed(() => {
  return !!selectedVoice.value && text.value.trim().length > 0 && text.value.trim().length <= MAX_LENGTH
})

const previewAudio = new Audio()
let previewSrc = ''

function openSelector() {
  selectorVisible.value = true
}

function onConfirmVoice(voice: Voice) {
  selectedVoice.value = voice
}

function togglePreview() {
  if (!selectedVoice.value) return
  if (!previewAudio.paused && previewSrc) {
    previewAudio.pause()
    previewSrc = ''
    return
  }
  const src = api.voiceAudioUrl(selectedVoice.value.id)
  if (previewSrc !== src) {
    previewSrc = src
    previewAudio.src = src
  }
  void previewAudio.play()
}

async function generate() {
  if (!selectedVoice.value) {
    ElMessage.warning('请先选择音色')
    return
  }
  const trimmed = text.value.trim()
  if (!trimmed) {
    ElMessage.warning('请输入要转成语音的文字')
    return
  }
  if (trimmed.length > MAX_LENGTH) {
    ElMessage.warning(`文字长度超出限制（最多 ${MAX_LENGTH} 字）`)
    return
  }
  generating.value = true
  try {
    const task = await api.createTask(selectedVoice.value.id, trimmed)
    ElMessage.success('任务已创建，正在生成…')
    bumpSidebar()
    emit('created', task.id)
  } catch (e: unknown) {
    const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
    ElMessage.error(msg || '创建任务失败，请重试')
  } finally {
    generating.value = false
  }
}
</script>

<template>
  <div class="task-input">
    <!-- 已选音色 -->
    <div class="task-input__voice" v-if="selectedVoice">
      <div class="task-input__voice-info">
        <div class="task-input__voice-avatar">{{ (selectedVoice.name || '声').charAt(0) }}</div>
        <div class="task-input__voice-meta">
          <div class="task-input__voice-name text-ellipsis">{{ selectedVoice.name }}</div>
          <div class="task-input__voice-tags">
            <el-tag size="small" type="primary" effect="plain">
              {{ selectedVoice.gender === 'male' ? '男' : selectedVoice.gender === 'female' ? '女' : '未知' }}
            </el-tag>
            <el-tag size="small" :type="selectedVoice.isBuiltin ? 'success' : 'warning'" effect="plain">
              {{ selectedVoice.isBuiltin ? '内置' : '自定义' }}
            </el-tag>
          </div>
        </div>
      </div>
      <div class="task-input__voice-actions">
        <el-button size="small" :icon="'VideoPlay'" @click="togglePreview">试听</el-button>
        <el-button size="small" @click="openSelector">更换</el-button>
      </div>
    </div>
    <!-- 未选音色 -->
    <div v-else class="task-input__voice task-input__voice--empty" @click="openSelector">
      <el-icon :size="22" color="#909399"><Headset /></el-icon>
      <span>点击选择音色</span>
    </div>

    <!-- 文字输入 -->
    <div class="task-input__text">
      <el-input
        v-model="text"
        type="textarea"
        :rows="10"
        resize="none"
        :maxlength="MAX_LENGTH"
        placeholder="输入要转成语音的文字…"
        show-word-limit
      />
    </div>

    <!-- 生成按钮 -->
    <div class="task-input__footer">
      <el-button
        type="primary"
        size="large"
        :disabled="!canGenerate"
        :loading="generating"
        style="min-width: 160px"
        @click="generate"
      >
        <el-icon style="margin-right: 4px"><MagicStick /></el-icon>
        确认生成
      </el-button>
      <span class="task-input__hint">
        {{ selectedVoice ? '已选音色，输入文字后即可生成' : '请先选择音色' }}
      </span>
    </div>

    <!-- 音色选择弹窗 -->
    <VoiceSelectorDialog
      v-model="selectorVisible"
      :selected-voice="selectedVoice"
      @confirm="onConfirmVoice"
    />
  </div>
</template>

<style scoped>
.task-input {
  max-width: 680px;
  margin: 0 auto;
  background: #fff;
  border-radius: 12px;
  padding: 24px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);
}

.task-input__voice {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 14px;
  border: 1px solid #e4e7ed;
  border-radius: 10px;
  margin-bottom: 16px;
  background: #fafafa;
}

.task-input__voice--empty {
  cursor: pointer;
  justify-content: center;
  gap: 8px;
  color: #909399;
  background: #fff;
  border-style: dashed;
}

.task-input__voice--empty:hover {
  border-color: #409eff;
  color: #409eff;
}

.task-input__voice-info {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}

.task-input__voice-avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  color: #fff;
  background: linear-gradient(135deg, #7c6cf0, #409eff);
  flex-shrink: 0;
}

.task-input__voice-meta {
  min-width: 0;
}

.task-input__voice-name {
  font-weight: 600;
  font-size: 14px;
  margin-bottom: 4px;
}

.task-input__voice-tags {
  display: flex;
  gap: 4px;
}

.task-input__text {
  margin-bottom: 16px;
}

.task-input__footer {
  display: flex;
  align-items: center;
  gap: 12px;
}

.task-input__hint {
  font-size: 12px;
  color: #c0c4cc;
}
</style>
