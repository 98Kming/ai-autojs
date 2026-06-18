import { ref, watch, onUnmounted, type Ref } from 'vue'
import { useWebSocketStore } from '@/stores/useWebSocketStore'
import { useAutoReconnect } from './useAutoReconnect'
import type { ConnectionConfig, IncomingMessage, ResultMessage } from '@/types/autojs'

const EXECUTION_TIMEOUT_MS = 120000
const HEARTBEAT_TIMEOUT_MULTIPLIER = 2

/**
 * WebSocket 核心组合式函数
 * 封装完整的 WebSocket 生命周期：连接/断开/发送/心跳/重连
 */
export function useWebSocket() {
  const wsStore = useWebSocketStore()

  // --- 响应式状态 ---
  const rawSocket = ref<WebSocket | null>(null)
  const intentionalClose = ref(false)
  let heartbeatTimer: ReturnType<typeof setInterval> | null = null
  let heartbeatTimeout: ReturnType<typeof setTimeout> | null = null
  let executionTimer: ReturnType<typeof setTimeout> | null = null
  let onResultCallback: ((msg: ResultMessage) => void) | null = null
  let pendingBinaryMeta: { mime: string; size: number } | null = null
  let pendingBinaryMetaTimer: ReturnType<typeof setTimeout> | null = null

  // --- 自动重连 ---
  const reconnect = useAutoReconnect({
    enabled: ref(true),
    maxAttempts: ref(wsStore.config.reconnectMaxAttempts),
    baseDelayMs: ref(wsStore.config.reconnectBaseDelayMs),
    maxDelayMs: ref(wsStore.config.reconnectMaxDelayMs),
    onReconnect: () => {
      connect()
    },
  })

  // 同步 config 到重连模块
  watch(() => wsStore.config.reconnectMaxAttempts, (v) => { reconnect.maxAttempts.value = v })
  watch(() => wsStore.config.reconnectBaseDelayMs, (v) => { reconnect.baseDelayMs.value = v })
  watch(() => wsStore.config.reconnectMaxDelayMs, (v) => { reconnect.maxDelayMs.value = v })

  // --- 注册结果回调 ---
  function onResult(callback: (msg: ResultMessage) => void) {
    onResultCallback = callback
  }

  // --- 连接 ---
  function connect() {
    if (rawSocket.value && rawSocket.value.readyState === WebSocket.OPEN) {
      console.log('[ws] 已连接，无需重复连接')
      return
    }

    intentionalClose.value = false
    wsStore.setStatus('connecting')

    const host = wsStore.config.host
    const port = wsStore.config.port
    const url = 'ws://' + host + ':' + port

    console.log('[ws] 正在连接 ' + url)

    let socket: WebSocket
    try {
      socket = new WebSocket(url)
      socket.binaryType = 'arraybuffer'
    } catch (e) {
      console.error('[ws] 创建 WebSocket 失败:', e)
      wsStore.setLastError('创建连接失败: ' + (e as Error).message)
      return
    }

    socket.onopen = () => {
      console.log('[ws] 连接成功')
      rawSocket.value = socket
      wsStore.setStatus('connected')
      reconnect.reset()
      startHeartbeat()
    }

    socket.onmessage = (event: MessageEvent) => {
      // 二进制帧：二进制结果数据
      if (event.data instanceof ArrayBuffer) {
        if (pendingBinaryMeta) {
          const meta = pendingBinaryMeta
          pendingBinaryMeta = null
          if (pendingBinaryMetaTimer) { clearTimeout(pendingBinaryMetaTimer); pendingBinaryMetaTimer = null }
          const bytes = new Uint8Array(event.data)
          let binary = ''
          for (let i = 0; i < bytes.byteLength; i++) {
            binary += String.fromCharCode(bytes[i])
          }
          const base64 = btoa(binary)
          clearExecutionTimeout()
          if (onResultCallback) {
            onResultCallback({
              type: 'result',
              status: 'success',
              dataType: 'base64',
              data: base64,
              mime: meta.mime,
            })
          }
        }
        return
      }

      // 文本帧
      let msg: IncomingMessage
      try {
        msg = JSON.parse(event.data as string) as IncomingMessage
      } catch {
        console.warn('[ws] 收到无效 JSON:', (event.data as string).slice(0, 100))
        return
      }

      if (msg.type === 'result') {
        clearExecutionTimeout()
        // 二进制元数据帧：等待后续二进制数据
        if (msg.dataType === 'binary') {
          pendingBinaryMeta = { mime: msg.mime || 'image/png', size: msg.size || 0 }
          if (pendingBinaryMetaTimer) clearTimeout(pendingBinaryMetaTimer)
          pendingBinaryMetaTimer = setTimeout(() => { pendingBinaryMeta = null; pendingBinaryMetaTimer = null }, EXECUTION_TIMEOUT_MS)
          return
        }
        if (onResultCallback) {
          onResultCallback(msg as ResultMessage)
        }
      } else if (msg.type === 'pong') {
        resetHeartbeatTimeout()
      }
    }

    socket.onerror = (event: Event) => {
      console.error('[ws] 连接错误')
    }

    socket.onclose = (event: CloseEvent) => {
      console.log('[ws] 连接关闭, code=' + event.code)
      rawSocket.value = null
      stopHeartbeat()

      if (!intentionalClose.value) {
        wsStore.setStatus('disconnected')
        // 如果之前是已连接状态，触发重连
        if (reconnect.enabled.value) {
          reconnect.scheduleReconnect()
        }
      } else {
        wsStore.setStatus('disconnected')
      }
    }
  }

  // --- 断开连接 ---
  function disconnect() {
    intentionalClose.value = true
    reconnect.destroy()
    stopHeartbeat()
    clearExecutionTimeout()

    if (rawSocket.value) {
      rawSocket.value.close(1000, '用户主动断开')
      rawSocket.value = null
    }
    wsStore.setStatus('disconnected')
    console.log('[ws] 已断开连接')
  }

  // --- 发送代码执行 ---
  function sendCode(code: string) {
    if (!rawSocket.value || rawSocket.value.readyState !== WebSocket.OPEN) {
      console.warn('[ws] 未连接，无法发送代码')
      return false
    }

    const msg = JSON.stringify({
      type: 'command',
      data: code,
    })

    try {
      rawSocket.value.send(msg)
      console.log('[ws] 已发送代码 (' + code.length + ' 字符)')

      // 启动执行超时计时器
      startExecutionTimeout()
      return true
    } catch (e) {
      console.error('[ws] 发送失败:', e)
      return false
    }
  }

  // --- 心跳 ---
  function startHeartbeat() {
    stopHeartbeat()
    const interval = wsStore.config.heartbeatIntervalMs

    heartbeatTimer = setInterval(() => {
      if (rawSocket.value && rawSocket.value.readyState === WebSocket.OPEN) {
        rawSocket.value.send(JSON.stringify({ type: 'ping' }))

        // 设置 pong 超时
        heartbeatTimeout = setTimeout(() => {
          console.warn('[ws] 心跳超时，断开连接')
          if (rawSocket.value) {
            const sock = rawSocket.value
            rawSocket.value = null
            sock.close()
          }
        }, interval * HEARTBEAT_TIMEOUT_MULTIPLIER)
      }
    }, interval)
  }

  function stopHeartbeat() {
    if (heartbeatTimer) {
      clearInterval(heartbeatTimer)
      heartbeatTimer = null
    }
    if (heartbeatTimeout) {
      clearTimeout(heartbeatTimeout)
      heartbeatTimeout = null
    }
  }

  function resetHeartbeatTimeout() {
    if (heartbeatTimeout) {
      clearTimeout(heartbeatTimeout)
      heartbeatTimeout = null
    }
  }

  // --- 执行超时 ---
  function startExecutionTimeout() {
    clearExecutionTimeout()
    executionTimer = setTimeout(() => {
      console.warn('[ws] 执行超时')
      if (onResultCallback) {
        onResultCallback({
          type: 'result',
          status: 'error',
          dataType: 'text',
          data: '执行超时（超过 ' + (EXECUTION_TIMEOUT_MS / 1000) + ' 秒无响应）',
        })
      }
    }, EXECUTION_TIMEOUT_MS)
  }

  function clearExecutionTimeout() {
    if (executionTimer) {
      clearTimeout(executionTimer)
      executionTimer = null
    }
  }

  // --- 生命周期 ---
  onUnmounted(() => {
    if (pendingBinaryMetaTimer) clearTimeout(pendingBinaryMetaTimer)
    pendingBinaryMeta = null
    disconnect()
  })

  return {
    connect,
    disconnect,
    sendCode,
    onResult,
    rawSocket,
  }
}
