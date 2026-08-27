<script setup lang="ts">
/**
 * 音色选择弹窗（附图 2）：
 * - 双 Tab：内置音色 / 上传自定义音色
 * - 顶部搜索 + 只看星标 + 最近使用分组
 * - 卡片列表（试听 / 星标 / 选中），底部「确定」回传选中音色
 */
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import type { UploadFile, UploadRawFile } from 'element-plus'
import { api } from '@/api'
import type { Voice } from '@/types'
import VoiceCard from './VoiceCard.vue'

const props = defineProps<{
  modelValue: boolean
  selectedVoice: Voice | null
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void
  (e: 'confirm', voice: Voice): void
  (e: 'favorite-changed'): void
}>()

const visible = computed({
  get: () => props.modelValue,
  set: (v: boolean) => emit('update:modelValue', v),
})

const activeTab = ref<'builtin' | 'custom'>('builtin')
const search = ref('')
const onlyFavorite = ref(false)

const recentVoices = ref<Voice[]>([])
const builtinVoices = ref<Voice[]>([])
const builtinPage = ref(1)
const builtinTotal = ref(0)
const builtinLoading = ref(false)
const builtinDone = ref(false)

const customVoices = ref<Voice[]>([])
const customPage = ref(1)
const customTotal = ref(0)
const customLoading = ref(false)
const customDone = ref(false)

const selected = ref<Voice | null>(null)
const previewAudio = new Audio()
let audioSrc = ''

// ---------- 加载 ----------
async function loadRecent() {
  try {
    const data = await api.listVoices({ recent: 10 })
    recentVoices.value = data.list
  } catch {
    recentVoices.value = []
  }
}

async function loadBuiltin(reset = false) {
  if (reset) {
    builtinPage.value = 1
    builtinDone.value = false
    builtinVoices.value = []
  }
  if (builtinLoading.value || builtinDone.value) return
  builtinLoading.value = true
  try {
    const data = await api.listVoices({
      search: search.value || undefined,
      onlyFavorite: onlyFavorite.value,
      isBuiltin: true,
      page: builtinPage.value,
      pageSize: 60,
    })
    const items = data.list
    builtinVoices.value.push(...items)
    builtinTotal.value = data.total
    builtinDone.value = builtinVoices.value.length >= data.total
    builtinPage.value += 1
  } finally {
    builtinLoading.value = false
  }
}

async function loadCustom(reset = false) {
  if (reset) {
    customPage.value = 1
    customDone.value = false
    customVoices.value = []
  }
  if (customLoading.value || customDone.value) return
  customLoading.value = true
  try {
    const data = await api.listVoices({
      search: search.value || undefined,
      onlyFavorite: onlyFavorite.value,
      isBuiltin: false,
      page: customPage.value,
      pageSize: 60,
    })
    const items = data.list
    customVoices.value.push(...items)
    customTotal.value = data.total
    customDone.value = customVoices.value.length >= data.total
    customPage.value += 1
  } finally {
    customLoading.value = false
  }
}

function refreshAll() {
  loadRecent()
  loadBuiltin(true)
  loadCustom(true)
}

watch(visible, (v) => {
  if (v) {
    selected.value = props.selectedVoice ? { ...props.selectedVoice } : null
    refreshAll()
  } else {
    stopPreview()
  }
})

watch([search, onlyFavorite], () => {
  refreshAll()
})

// ---------- 试听（单实例 audio） ----------
const playingId = ref<number | null>(null)

function stopPreview() {
  previewAudio.pause()
  previewAudio.removeAttribute('src')
  audioSrc = ''
  playingId.value = null
}

function togglePlay(voice: Voice) {
  if (playingId.value === voice.id) {
    stopPreview()
    return
  }
  const src = api.voiceAudioUrl(voice.id)
  if (audioSrc !== src) {
    audioSrc = src
    previewAudio.src = src
  }
  previewAudio.onended = () => {
    playingId.value = null
  }
  void previewAudio.play()
  playingId.value = voice.id
}

// ---------- 收藏 ----------
async function onFavoriteChanged(voice: Voice) {
  emit('favorite-changed')
  // 同步列表里的引用
  syncVoice(voice)
}

function syncVoice(voice: Voice) {
  for (const list of [recentVoices.value, builtinVoices.value, customVoices.value]) {
    const item = list.find((v) => v.id === voice.id)
    if (item) item.isFavorite = voice.isFavorite
  }
  if (selected.value && selected.value.id === voice.id) {
    selected.value.isFavorite = voice.isFavorite
  }
}

// ---------- 选中 / 确定 ----------
function selectVoice(voice: Voice) {
  selected.value = voice
}

function onConfirm() {
  if (!selected.value) {
    ElMessage.warning('请先选择一个音色')
    return
  }
  emit('confirm', selected.value)
  visible.value = false
}

// ---------- 上传自定义音色 ----------
const uploadName = ref('')
const uploading = ref(false)
const uploadFileList = ref<UploadFile[]>([])

async function handleUpload(file: UploadRawFile) {
  const ext = (file.name.split('.').pop() ?? '').toLowerCase()
  if (!['wav', 'mp3', 'm4a'].includes(ext)) {
    ElMessage.error('仅支持 wav / mp3 / m4a 格式')
    return false
  }
  if (file.size > 50 * 1024 * 1024) {
    ElMessage.error('音频文件不能超过 50MB')
    return false
  }
  const name = uploadName.value.trim() || file.name.replace(/\.[^.]+$/, '')
  uploading.value = true
  try {
    const voice = await api.uploadVoice(file, name)
    ElMessage.success(`已上传自定义音色「${voice.name}」`)
    uploadName.value = ''
    uploadFileList.value = []
    selectVoice(voice)
    await loadCustom(true)
    loadRecent()
  } catch (e) {
    ElMessage.error('上传失败，请重试')
  } finally {
    uploading.value = false
  }
  return false
}

// ---------- 滚动加载更多 ----------
function onBuiltinScroll(e: Event) {
  const el = e.target as HTMLElement
  if (el.scrollTop + el.clientHeight >= el.scrollHeight - 40) {
    loadBuiltin()
  }
}

function onCustomScroll(e: Event) {
  const el = e.target as HTMLElement
  if (el.scrollTop + el.clientHeight >= el.scrollHeight - 40) {
    loadCustom()
  }
}

onBeforeUnmount(stopPreview)
</script>

<template>
  <el-dialog
    v-model="visible"
    title="选择音色"
    width="720px"
    top="6vh"
    destroy-on-close
    append-to-body
  >
    <!-- 顶部工具栏：搜索 + 只看星标 -->
    <div class="vs-toolbar">
      <el-input
        v-model="search"
        placeholder="搜索音色名"
        clearable
        :prefix-icon="'Search'"
        style="width: 260px"
      />
      <el-switch v-model="onlyFavorite" active-text="只看星标" />
    </div>

    <el-tabs v-model="activeTab">
      <!-- 内置音色 -->
      <el-tab-pane label="内置音色" name="builtin">
        <!-- 最近使用 -->
        <div v-if="recentVoices.length" class="vs-recent">
          <div class="vs-recent__title">最近使用</div>
          <div class="vs-recent__row">
            <VoiceCard
              v-for="v in recentVoices"
              :key="'r' + v.id"
              :voice="v"
              :selected="selected?.id === v.id"
              @select="selectVoice"
              @play="togglePlay"
              @favorite-changed="onFavoriteChanged"
            />
          </div>
        </div>

        <div
          v-loading="builtinLoading && !builtinVoices.length"
          class="vs-list"
          @scroll="onBuiltinScroll"
        >
          <template v-if="builtinVoices.length">
            <VoiceCard
              v-for="v in builtinVoices"
              :key="'b' + v.id"
              :voice="v"
              :selected="selected?.id === v.id"
              :playing="playingId === v.id"
              @select="selectVoice"
              @play="togglePlay"
              @favorite-changed="onFavoriteChanged"
            />
            <div v-if="builtinLoading" class="vs-list__loading">加载中…</div>
            <div v-else-if="builtinDone" class="vs-list__end">— 已加载全部 —</div>
          </template>
          <el-empty v-else-if="!builtinLoading" description="无匹配音色" :image-size="70" />
        </div>
      </el-tab-pane>

      <!-- 上传自定义音色 -->
      <el-tab-pane label="上传自定义音色" name="custom">
        <div class="vs-upload">
          <el-input
            v-model="uploadName"
            placeholder="音色名称（可选，默认取文件名）"
            style="width: 100%; margin-bottom: 10px"
          />
          <el-upload
            v-model:file-list="uploadFileList"
            drag
            accept=".wav,.mp3,.m4a"
            :auto-upload="false"
            :show-file-list="false"
            :on-change="(f: UploadFile) => handleUpload(f.raw as UploadRawFile)"
            :disabled="uploading"
          >
            <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
            <div class="el-upload__text">
              拖拽音频到此处，或 <em>点击上传</em>
            </div>
            <template #tip>
              <div class="el-upload__tip">
                支持 wav / mp3 / m4a，≤50MB；建议 10~30 秒干净人声
              </div>
            </template>
          </el-upload>
        </div>

        <div
          v-loading="customLoading && !customVoices.length"
          class="vs-list"
          @scroll="onCustomScroll"
        >
          <template v-if="customVoices.length">
            <VoiceCard
              v-for="v in customVoices"
              :key="'c' + v.id"
              :voice="v"
              :selected="selected?.id === v.id"
              :playing="playingId === v.id"
              @select="selectVoice"
              @play="togglePlay"
              @favorite-changed="onFavoriteChanged"
            />
            <div v-if="customLoading" class="vs-list__loading">加载中…</div>
            <div v-else-if="customDone" class="vs-list__end">— 已加载全部 —</div>
          </template>
          <el-empty v-else-if="!customLoading" description="暂无自定义音色，上传一个试试" :image-size="70" />
        </div>
      </el-tab-pane>
    </el-tabs>

    <!-- 底部操作区 -->
    <template #footer>
      <div class="vs-footer">
        <span class="vs-footer__selected" v-if="selected">
          已选：{{ selected.name }}
        </span>
        <span v-else />
        <div>
          <el-button @click="visible = false">取消</el-button>
          <el-button type="primary" @click="onConfirm">确定</el-button>
        </div>
      </div>
    </template>
  </el-dialog>
</template>

<style scoped>
.vs-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.vs-recent {
  margin-bottom: 12px;
}

.vs-recent__title {
  font-size: 13px;
  color: #909399;
  margin-bottom: 8px;
}

.vs-recent__row {
  display: flex;
  gap: 8px;
  overflow-x: auto;
  padding-bottom: 6px;
}

.vs-recent__row :deep(.voice-card) {
  min-width: 220px;
}

.vs-list {
  height: 380px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding-right: 4px;
}

.vs-list__loading,
.vs-list__end {
  text-align: center;
  color: #c0c4cc;
  font-size: 12px;
  padding: 8px 0;
}

.vs-upload {
  margin-bottom: 14px;
}

.vs-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.vs-footer__selected {
  color: #409eff;
  font-size: 13px;
  max-width: 60%;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}
</style>
