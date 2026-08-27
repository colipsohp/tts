<script setup lang="ts">
/**
 * 音色卡片：圆形头像、名称、性别/来源标签、播放按钮、星标收藏按钮。
 * 选中态蓝色描边高亮；点击卡片选中。
 */
import { computed } from 'vue'
import type { Voice } from '@/types'
import { api } from '@/api'

const props = defineProps<{
  voice: Voice
  selected?: boolean
  /** 当前是否正在播放参考音频 */
  playing?: boolean
}>()

const emit = defineEmits<{
  (e: 'select', voice: Voice): void
  (e: 'play', voice: Voice): void
  (e: 'favorite-changed', voice: Voice): void
}>()

const avatarChar = computed(() => (props.voice.name || '声').trim().charAt(0))

const genderLabel = computed(() => {
  const map: Record<string, string> = { male: '男', female: '女', unknown: '未知' }
  return map[props.voice.gender ?? 'unknown'] ?? '未知'
})

const genderTagType = computed(() => {
  const map: Record<string, 'danger' | 'primary' | 'info'> = {
    male: 'primary',
    female: 'danger',
    unknown: 'info',
  }
  return map[props.voice.gender ?? 'unknown'] ?? 'info'
})

async function toggleFavorite() {
  try {
    const next = props.voice.isFavorite
      ? await api.unfavorite(props.voice.id)
      : await api.favorite(props.voice.id)
    props.voice.isFavorite = next
    emit('favorite-changed', props.voice)
  } catch {
    /* 收藏失败静默（按钮不阻塞） */
  }
}
</script>

<template>
  <div
    class="voice-card"
    :class="{ 'voice-card--selected': selected }"
    @click="emit('select', voice)"
  >
    <div class="voice-card__avatar">{{ avatarChar }}</div>
    <div class="voice-card__body">
      <div class="voice-card__name text-ellipsis" :title="voice.name">{{ voice.name }}</div>
      <div class="voice-card__tags">
        <el-tag size="small" :type="genderTagType" effect="plain">{{ genderLabel }}</el-tag>
        <el-tag size="small" type="success" effect="plain" v-if="voice.isBuiltin">内置</el-tag>
        <el-tag size="small" type="warning" effect="plain" v-else>自定义</el-tag>
      </div>
    </div>
    <div class="voice-card__actions">
      <el-button
        circle
        size="small"
        :type="playing ? 'primary' : 'default'"
        :title="playing ? '停止试听' : '试听参考音频'"
        @click.stop="emit('play', voice)"
      >
        <template #icon>
          <el-icon>
            <VideoPause v-if="playing" />
            <VideoPlay v-else />
          </el-icon>
        </template>
      </el-button>
      <el-button
        circle
        size="small"
        :type="voice.isFavorite ? 'warning' : 'default'"
        :icon="voice.isFavorite ? 'StarFilled' : 'Star'"
        :title="voice.isFavorite ? '取消收藏' : '收藏'"
        @click.stop="toggleFavorite"
      >
        <template #icon>
          <el-icon>
            <StarFilled v-if="voice.isFavorite" />
            <Star v-else />
          </el-icon>
        </template>
      </el-button>
    </div>
  </div>
</template>

<style scoped>
.voice-card {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border: 1.5px solid transparent;
  border-radius: 10px;
  background: #fff;
  cursor: pointer;
  transition: border-color 0.2s, box-shadow 0.2s;
}

.voice-card:hover {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

.voice-card--selected {
  border-color: #409eff;
  box-shadow: 0 0 0 2px rgba(64, 158, 255, 0.2);
}

.voice-card__avatar {
  width: 40px;
  height: 40px;
  flex-shrink: 0;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  color: #fff;
  background: linear-gradient(135deg, #7c6cf0, #409eff);
}

.voice-card__body {
  flex: 1;
  min-width: 0;
}

.voice-card__name {
  font-size: 13px;
  font-weight: 600;
  margin-bottom: 4px;
}

.voice-card__tags {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
}

.voice-card__actions {
  display: flex;
  gap: 2px;
  flex-shrink: 0;
}
</style>
