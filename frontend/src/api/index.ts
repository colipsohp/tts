/**
 * axios 封装 + 后端接口方法。
 * 后端返回 snake_case，前端统一在响应拦截器转成 camelCase（与 types 对齐）。
 */
import axios from 'axios'
import type { Paged, TaskQuery, TtsTask, Voice, VoiceQuery } from '@/types'

const http = axios.create({
  baseURL: '/api',
  timeout: 60_000,
})

/** 递归把 snake_case 键转成 camelCase（仅作用于 JSON 响应体） */
function toCamelCase<T>(value: unknown): T {
  if (Array.isArray(value)) {
    return value.map((item) => toCamelCase(item)) as T
  }
  if (value !== null && typeof value === 'object') {
    const out: Record<string, unknown> = {}
    for (const [key, val] of Object.entries(value)) {
      const camel = key.replace(/_([a-z])/g, (_, c: string) => c.toUpperCase())
      out[camel] = toCamelCase(val)
    }
    return out as T
  }
  return value as T
}

http.interceptors.response.use((resp) => {
  if (resp.data && typeof resp.data === 'object') {
    resp.data = toCamelCase(resp.data)
  }
  return resp
})

export const api = {
  // ---------- 音色 ----------
  async listVoices(params: VoiceQuery = {}): Promise<Paged<Voice>> {
    const { data } = await http.get<Paged<Voice>>('/voices', {
      params: {
        search: params.search || undefined,
        only_favorite: params.onlyFavorite || undefined,
        recent: params.recent || undefined,
        gender: params.gender || undefined,
        is_builtin: params.isBuiltin === undefined ? undefined : String(params.isBuiltin),
        page: params.page || 1,
        page_size: params.pageSize || 50,
      },
    })
    return data
  },

  /** 上传自定义音色 */
  async uploadVoice(file: File, name: string): Promise<Voice> {
    const form = new FormData()
    form.append('name', name)
    form.append('file', file)
    const { data } = await http.post<Voice>('/voices', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 30_000,
    })
    return data
  },

  /** 试听参考音频的完整 URL（相对路径，走 vite proxy / 同源） */
  voiceAudioUrl(id: number): string {
    return `/api/voices/${id}/audio`
  },

  async favorite(id: number): Promise<boolean> {
    const { data } = await http.post<{ isFavorite: boolean }>(`/voices/${id}/favorite`)
    return data.isFavorite
  },

  async unfavorite(id: number): Promise<boolean> {
    const { data } = await http.delete<{ isFavorite: boolean }>(`/voices/${id}/favorite`)
    return data.isFavorite
  },

  // ---------- 任务 ----------
  async createTask(voiceId: number, text: string): Promise<TtsTask> {
    const { data } = await http.post<TtsTask>('/tasks', { voice_id: voiceId, text })
    return data
  },

  async listTasks(params: TaskQuery = {}): Promise<Paged<TtsTask>> {
    const { data } = await http.get<Paged<TtsTask>>('/tasks', {
      params: {
        search: params.search || undefined,
        page: params.page || 1,
        page_size: params.pageSize || 30,
      },
    })
    return data
  },

  async getTask(id: number): Promise<TtsTask> {
    const { data } = await http.get<TtsTask>(`/tasks/${id}`)
    return data
  },

  async regenerateTask(id: number): Promise<TtsTask> {
    const { data } = await http.post<TtsTask>(`/tasks/${id}/regenerate`)
    return data
  },

  /** 试听生成音频的完整 URL */
  taskAudioUrl(id: number): string {
    return `/api/tasks/${id}/audio`
  },

  /** 下载生成音频的完整 URL（浏览器直接导航触发下载） */
  taskDownloadUrl(id: number): string {
    return `/api/tasks/${id}/download`
  },
}

export default http
