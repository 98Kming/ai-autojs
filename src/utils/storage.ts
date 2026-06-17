/**
 * localStorage 封装，带 JSON 序列化和错误处理
 */

/** 从 localStorage 读取并反序列化 */
export function loadFromStorage<T>(key: string, fallback: T): T {
  try {
    const raw = localStorage.getItem(key)
    if (raw === null) return fallback
    return JSON.parse(raw) as T
  } catch {
    return fallback
  }
}

/** 序列化并写入 localStorage */
export function saveToStorage<T>(key: string, value: T): void {
  try {
    localStorage.setItem(key, JSON.stringify(value))
  } catch (e) {
    if (e instanceof DOMException && e.name === 'QuotaExceededError') {
      console.warn(`[storage] localStorage 配额已满，无法保存 key="${key}"`)
    } else {
      console.error(`[storage] 写入 localStorage 失败 key="${key}":`, e)
    }
  }
}

/** 从 localStorage 移除 */
export function removeFromStorage(key: string): void {
  try {
    localStorage.removeItem(key)
  } catch (e) {
    console.error(`[storage] 移除 localStorage 失败 key="${key}":`, e)
  }
}
