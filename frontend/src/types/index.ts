/**
 * 与后端 Pydantic 模型字段一一对齐的类型定义。
 * 后端改动 schema 时同步更新本文件（AGENTS.md §7 类型对齐）。
 */

/** 音色（内置 / 自定义） */
export interface Voice {
  id: number
  name: string
  isBuiltin: boolean
  gender: 'male' | 'female' | 'unknown' | null
  isFavorite: boolean
  lastUsedAt: string | null
  createdAt: string
  sourcePath: string | null
  sampleText: string | null
}

export type TaskStatus = 'pending' | 'running' | 'succeeded' | 'failed'

/** TTS 生成任务 */
export interface TtsTask {
  id: number
  voice: Voice
  text: string
  status: TaskStatus
  /** /api/tasks/{id}/audio 相对路径；未生成时为 null */
  audioUrl: string | null
  errorMessage: string | null
  durationSeconds: number | null
  createdAt: string
  completedAt: string | null
}

/** 分页响应 */
export interface Paged<T> {
  list: T[]
  total: number
}

/** 音色列表查询参数 */
export interface VoiceQuery {
  search?: string
  onlyFavorite?: boolean
  recent?: number
  gender?: string
  /** true=仅内置，false=仅自定义，缺省=全部 */
  isBuiltin?: boolean
  page?: number
  pageSize?: number
}

/** 任务列表查询参数 */
export interface TaskQuery {
  search?: string
  page?: number
  pageSize?: number
}
