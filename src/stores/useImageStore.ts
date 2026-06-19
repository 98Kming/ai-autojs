import { ref } from 'vue'
import { defineStore } from 'pinia'
import { ElMessageBox } from 'element-plus'
import { loadFromStorage, saveToStorage } from '@/utils/storage'

const STORAGE_KEY = 'autojs-images'
const MAX_IMAGES = 20
const MAX_STORAGE_BYTES = 4 * 1024 * 1024 // 4MB

export interface ImageEntry {
  id: string
  data: string        // base64
  mime: string        // image/png, image/jpeg, ...
  timestamp: number
  code: string        // 生成该图片的源代码
}

export const useImageStore = defineStore('image', () => {
  const images = ref<ImageEntry[]>(loadFromStorage<ImageEntry[]>(STORAGE_KEY, []))
  let capacityDialogPending = false // 容量对话框竞态 guard

  async function addImage(data: string, mime: string, code: string) {
    images.value.unshift({
      id: Date.now().toString(36) + Math.random().toString(36).slice(2, 7),
      data,
      mime,
      timestamp: Date.now(),
      code,
    })

    // 数量上限裁剪（静默，保留最新）
    if (images.value.length > MAX_IMAGES) {
      images.value = images.value.slice(0, MAX_IMAGES)
    }

    // 容量检查（弹确认对话框，同时只弹一个防止竞态）
    const json = JSON.stringify(images.value)
    if (json.length > MAX_STORAGE_BYTES && images.value.length > 1) {
      if (capacityDialogPending) {
        // 已有对话框在显示，本次添加的图片直接丢弃
        images.value.shift()
        return
      }
      capacityDialogPending = true
      try {
        await ElMessageBox.confirm(
          '图片存储超过限制（当前 ' + (json.length / 1024 / 1024).toFixed(1) + 'MB / 上限 ' + (MAX_STORAGE_BYTES / 1024 / 1024).toFixed(0) + 'MB），是否删除最旧图片？',
          '存储容量告警',
          { confirmButtonText: '删除旧图', cancelButtonText: '取消本次截图', type: 'warning' }
        )
        // 用户确认：从最旧开始逐张移除，直至容量达标
        const trimmed = [...images.value]
        while (JSON.stringify(trimmed).length > MAX_STORAGE_BYTES && trimmed.length > 1) {
          trimmed.pop()
        }
        images.value = trimmed
      } catch {
        // 用户取消：移除本次添加的图片
        images.value.shift()
        saveToStorage(STORAGE_KEY, images.value)
        return
      } finally {
        capacityDialogPending = false
      }
    }

    saveToStorage(STORAGE_KEY, images.value)
  }

  function removeImage(id: string) {
    images.value = images.value.filter(img => img.id !== id)
    saveToStorage(STORAGE_KEY, images.value)
  }

  function clearAll() {
    images.value = []
    saveToStorage(STORAGE_KEY, [])
  }

  return { images, addImage, removeImage, clearAll }
})
