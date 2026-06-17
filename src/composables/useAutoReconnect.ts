import { ref, watch, type Ref } from 'vue'

/**
 * 自动重连组合式函数
 * 使用指数退避 + 随机抖动算法
 */
export function useAutoReconnect(config: {
  enabled: Ref<boolean>
  maxAttempts: Ref<number>    // 0 = 无限
  baseDelayMs: Ref<number>
  maxDelayMs: Ref<number>
  onReconnect: () => void     // 重连触发时的回调
}) {
  const attemptCount = ref(0)
  const isReconnecting = ref(false)
  let timer: ReturnType<typeof setTimeout> | null = null

  /** 计算当前退避延迟 */
  function calcDelay(): number {
    const base = config.baseDelayMs.value
    const max = config.maxDelayMs.value
    const exponential = base * Math.pow(2, attemptCount.value)
    // 添加 0~50% 的随机抖动
    const jitter = Math.floor(Math.random() * 0.5 * exponential)
    return Math.min(exponential + jitter, max)
  }

  /** 调度下次重连 */
  function scheduleReconnect() {
    if (!config.enabled.value) return
    const maxAttempts = config.maxAttempts.value
    if (maxAttempts > 0 && attemptCount.value >= maxAttempts) {
      console.warn('[reconnect] 已达最大重连次数 (' + maxAttempts + ')，停止重连')
      isReconnecting.value = false
      return
    }

    isReconnecting.value = true
    const delay = calcDelay()
    console.log('[reconnect] 将在 ' + delay + 'ms 后尝试第 ' + (attemptCount.value + 1) + ' 次重连')

    timer = setTimeout(() => {
      attemptCount.value++
      config.onReconnect()
    }, delay)
  }

  /** 成功后重置计数器 */
  function reset() {
    attemptCount.value = 0
    isReconnecting.value = false
    if (timer) {
      clearTimeout(timer)
      timer = null
    }
  }

  /** 清理 */
  function destroy() {
    if (timer) {
      clearTimeout(timer)
      timer = null
    }
    attemptCount.value = 0
    isReconnecting.value = false
  }

  return {
    enabled: config.enabled,
    maxAttempts: config.maxAttempts,
    baseDelayMs: config.baseDelayMs,
    maxDelayMs: config.maxDelayMs,
    attemptCount,
    isReconnecting,
    scheduleReconnect,
    reset,
    destroy,
  }
}
