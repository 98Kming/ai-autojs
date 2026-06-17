import { ref } from 'vue'
import { defineStore } from 'pinia'
import type { ResultMessage } from '@/types/autojs'

export interface ResultEntry {
  id: string
  timestamp: number
  durationMs?: number
  data: string
  status: 'success' | 'error'
  dataType: 'text' | 'base64'
  mime?: string
}

export const useCodeStore = defineStore('code', () => {
  // --- 状态 ---
  const content = ref('')
  const isExecuting = ref(false)
  const lastResult = ref<ResultEntry | null>(null)

  // --- actions ---
  function setContent(text: string) {
    content.value = text
  }

  function clearContent() {
    content.value = ''
    lastResult.value = null
  }

  function setExecuting(val: boolean) {
    isExecuting.value = val
  }

  function setResult(msg: ResultMessage, execDurationMs?: number) {
    lastResult.value = {
      id: Date.now().toString(36) + Math.random().toString(36).slice(2, 7),
      timestamp: Date.now(),
      durationMs: execDurationMs,
      data: msg.data,
      status: msg.status,
      dataType: msg.dataType || 'text',
      mime: msg.mime,
    }
  }

  function clearResult() {
    lastResult.value = null
  }

  return {
    content,
    isExecuting,
    lastResult,
    setContent,
    clearContent,
    setExecuting,
    setResult,
    clearResult,
  }
})
