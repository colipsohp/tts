<script setup lang="ts">
/**
 * 任务状态标签：pending/running/succeeded/failed。
 */
import { computed } from 'vue'
import type { TaskStatus } from '@/types'

const props = defineProps<{ status: TaskStatus }>()

const map: Record<TaskStatus, { type: 'info' | 'warning' | 'success' | 'danger'; label: string }> = {
  pending: { type: 'info', label: '排队中' },
  running: { type: 'warning', label: '生成中' },
  succeeded: { type: 'success', label: '成功' },
  failed: { type: 'danger', label: '失败' },
}

const tag = computed(() => map[props.status] ?? { type: 'info', label: props.status })
</script>

<template>
  <el-tag :type="tag.type" size="small" effect="light">
    <el-icon v-if="status === 'running'" class="is-loading" style="margin-right: 2px">
      <Loading />
    </el-icon>
    {{ tag.label }}
  </el-tag>
</template>
