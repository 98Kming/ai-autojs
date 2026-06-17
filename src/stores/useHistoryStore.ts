import { ref, watch } from 'vue'
import { defineStore } from 'pinia'
import type { HistoryEntry } from '@/types/autojs'
import { loadFromStorage, saveToStorage } from '@/utils/storage'

const STORAGE_KEY = 'autojs-history'
const MAX_ENTRIES = 200

export const useHistoryStore = defineStore('history', () => {
  // --- 状态 ---
  const entries = ref<HistoryEntry[]>(loadFromStorage<HistoryEntry[]>(STORAGE_KEY, []))

  // --- 持久化 ---
  watch(entries, (val) => {
    saveToStorage(STORAGE_KEY, val)
  }, { deep: true })

  // --- actions ---
  function addEntry(entry: HistoryEntry) {
    entries.value.unshift(entry)
    // 超出上限时裁剪最旧记录
    if (entries.value.length > MAX_ENTRIES) {
      entries.value = entries.value.slice(0, MAX_ENTRIES)
    }
  }

  function updateLastEntry(updates: Partial<HistoryEntry>) {
    if (entries.value.length > 0) {
      Object.assign(entries.value[0], updates)
    }
  }

  function removeEntry(id: string) {
    entries.value = entries.value.filter(e => e.id !== id)
  }

  function clearAll() {
    entries.value = []
  }

  return {
    entries,
    addEntry,
    updateLastEntry,
    removeEntry,
    clearAll,
  }
})
