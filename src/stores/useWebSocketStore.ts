import { ref, watch } from 'vue'
import { defineStore } from 'pinia'
import type { ConnectionConfig, ConnectionStatus } from '@/types/autojs'
import { DEFAULT_CONFIG } from '@/types/autojs'
import { loadFromStorage, saveToStorage } from '@/utils/storage'

const STORAGE_KEY = 'autojs-ws-config'

export const useWebSocketStore = defineStore('webSocket', () => {
  // --- 状态 ---
  const savedConfig = loadFromStorage<Partial<ConnectionConfig>>(STORAGE_KEY, {})
  const config = ref<ConnectionConfig>({ ...DEFAULT_CONFIG, ...savedConfig })
  const status = ref<ConnectionStatus>('disconnected')
  const lastError = ref<string | null>(null)
  const historyVisible = ref(false)

  // --- 持久化 config ---
  watch(
    config,
    (val) => {
      saveToStorage(STORAGE_KEY, {
        host: val.host,
        port: val.port,
        reconnectEnabled: val.reconnectEnabled,
      })
    },
    { deep: true }
  )

  // --- actions ---
  function setStatus(s: ConnectionStatus) {
    status.value = s
    if (s !== 'error') lastError.value = null
  }

  function setLastError(msg: string) {
    lastError.value = msg
    status.value = 'error'
  }

  function updateHost(host: string) {
    config.value.host = host
  }

  function toggleHistory() {
    historyVisible.value = !historyVisible.value
  }

  return {
    config,
    status,
    lastError,
    historyVisible,
    setStatus,
    setLastError,
    updateHost,
    toggleHistory,
  }
})
