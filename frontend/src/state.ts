/**
 * 轻量全局状态：侧栏任务列表刷新信号。
 * 创建/重新生成任务后 bumpSidebar()，AppSidebar watch 后自动刷新。
 */
import { ref } from 'vue'

export const sidebarVersion = ref(0)

export function bumpSidebar(): void {
  sidebarVersion.value += 1
}
