<script setup lang="ts">
/**
 * 音频播放器封装（HTML5 <audio>），试听参考音频与生成音频共用。
 */
import { ref, watch } from 'vue'

const props = withDefaults(
  defineProps<{
    src: string
    autoplay?: boolean
  }>(),
  { autoplay: false },
)

const audioRef = ref<HTMLAudioElement | null>(null)
const isPlaying = ref(false)
const currentTime = ref(0)
const duration = ref(0)

watch(
  () => props.src,
  () => {
    currentTime.value = 0
    duration.value = 0
    isPlaying.value = false
  },
)

function onPlay() {
  isPlaying.value = true
}

function onPause() {
  isPlaying.value = false
}

function onTimeUpdate() {
  if (audioRef.value) {
    currentTime.value = audioRef.value.currentTime
  }
}

function onLoadedMetadata() {
  if (audioRef.value && Number.isFinite(audioRef.value.duration)) {
    duration.value = audioRef.value.duration
  }
}

function togglePlay() {
  if (!audioRef.value) return
  if (audioRef.value.paused) {
    void audioRef.value.play()
  } else {
    audioRef.value.pause()
  }
}

function formatTime(seconds: number): string {
  if (!seconds || !Number.isFinite(seconds)) return '00:00'
  const m = Math.floor(seconds / 60)
  const s = Math.floor(seconds % 60)
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
}
</script>

<template>
  <div class="audio-player">
    <audio
      ref="audioRef"
      :src="src"
      :autoplay="autoplay"
      @play="onPlay"
      @pause="onPause"
      @timeupdate="onTimeUpdate"
      @loadedmetadata="onLoadedMetadata"
    />
    <el-button
      circle
      :type="isPlaying ? 'primary' : 'default'"
      :icon="isPlaying ? 'VideoPause' : 'VideoPlay'"
      aria-label="播放/暂停"
      @click="togglePlay"
    />
    <div class="audio-player__times">
      <span>{{ formatTime(currentTime) }}</span>
      <el-slider
        class="audio-player__slider"
        :model-value="currentTime"
        :max="duration || 1"
        :show-tooltip="false"
        :disabled="!duration"
        @input="(v: number) => audioRef && (audioRef.currentTime = v)"
      />
      <span>{{ formatTime(duration) }}</span>
    </div>
  </div>
</template>

<style scoped>
.audio-player {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
}

.audio-player__times {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: #909399;
  min-width: 0;
}

.audio-player__slider {
  flex: 1;
  min-width: 0;
}
</style>
