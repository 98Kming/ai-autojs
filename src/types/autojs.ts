// ===== 消息协议类型 =====

/** 连接状态 */
export type ConnectionStatus = 'disconnected' | 'connecting' | 'connected' | 'error'

/** 客户端 → 服务端：发送代码执行 */
export interface CommandMessage {
  type: 'command'
  data: string // JavaScript 代码
}

/** 服务端 → 客户端：执行结果 */
export interface ResultMessage {
  type: 'result'
  data: string // 文本输出 或 Base64 编码的二进制
  status: 'success' | 'error'
  dataType: 'text' | 'base64' // 结果数据类型
  mime?: string // dataType 为 base64 时的 MIME 类型
}

/** 客户端 → 服务端：心跳请求 */
export interface PingMessage {
  type: 'ping'
}

/** 服务端 → 客户端：心跳响应 */
export interface PongMessage {
  type: 'pong'
}

/** 所有出站消息联合类型 */
export type OutgoingMessage = CommandMessage | PingMessage

/** 所有入站消息联合类型 */
export type IncomingMessage = ResultMessage | PongMessage

// ===== 连接配置 =====

/** WebSocket 连接配置 */
export interface ConnectionConfig {
  host: string // 手机 IP 地址
  port: number // 默认 9318
  reconnectEnabled: boolean
  reconnectMaxAttempts: number // 0 = 无限重连
  reconnectBaseDelayMs: number // 初始延迟，默认 1000
  reconnectMaxDelayMs: number // 最大延迟，默认 30000
  heartbeatIntervalMs: number // 心跳间隔，默认 30000
}

/** 默认连接配置 */
export const DEFAULT_CONFIG: ConnectionConfig = {
  host: '127.0.0.1',
  port: 9318,
  reconnectEnabled: true,
  reconnectMaxAttempts: 0,
  reconnectBaseDelayMs: 1000,
  reconnectMaxDelayMs: 30000,
  heartbeatIntervalMs: 30000,
}

// ===== 执行历史 =====

/** 执行历史条目 */
export interface HistoryEntry {
  id: string
  code: string
  result: string
  resultDataType: 'text' | 'base64'
  resultMime?: string
  status: 'success' | 'error' | 'pending'
  timestamp: number
}
