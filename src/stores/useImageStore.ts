import { ref, watch } from 'vue'
import { defineStore } from 'pinia'
import { loadFromStorage, saveToStorage } from '@/utils/storage'

const STORAGE_KEY = 'autojs-images'
const MAX_IMAGES = 20
const MAX_STORAGE_BYTES = 4 * 1024 * 1024 // 4MB 上限，保留给其他数据

export interface ImageEntry {
  id: string
  data: string        // base64
  mime: string        // image/png, image/jpeg, ...
  timestamp: number
  code: string        // 生成该图片的源代码
}

export const useImageStore = defineStore('image', () => {
  const images = ref<ImageEntry[]>(loadFromStorage<ImageEntry[]>(STORAGE_KEY, []))

  // 持久化（容量保护：超过 4MB 时裁剪旧图）
  watch(images, (val) => {
    const json = JSON.stringify(val)
    // 超过限制时丢弃最旧的一半
    let trimmed = val
    while (json.length > MAX_STORAGE_BYTES && trimmed.length > 1) {
      trimmed = trimmed.slice(0, Math.ceil(trimmed.length / 2))
    }
    if (trimmed.length < val.length) {
      images.value = trimmed
      // 裁剪后不再触发本轮 watch（Vue 会再触发一次，但此时大小已达标）
    }
    saveToStorage(STORAGE_KEY, trimmed)
  }, { deep: true })

  function addImage(data: string, mime: string, code: string) {
    images.value.unshift({
      id: Date.now().toString(36) + Math.random().toString(36).slice(2, 7),
      data,
      mime,
      timestamp: Date.now(),
      code,
    })
    if (images.value.length > MAX_IMAGES) {
      images.value = images.value.slice(0, MAX_IMAGES)
    }
  }

  function removeImage(id: string) {
    images.value = images.value.filter(img => img.id !== id)
  }

  function clearAll() {
    images.value = []
  }

  return { images, addImage, removeImage, clearAll }
})
