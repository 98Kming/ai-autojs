"""WebSocket 客户端，对应 useWebSocket.ts

基于 QWebSocket，信号驱动，与 Qt 事件循环无缝集成。

关键协议细节：
- 文本帧：JSON 格式 {type, data, status, dataType, mime, size}
- 二进制帧（双帧协议）：先 meta JSON (dataType:"binary")，再 binary frame
- 心跳：发送 ping JSON 文本帧，期望 pong JSON 文本帧（非 WebSocket opcode ping/pong）
- 执行超时：120s
"""
from __future__ import annotations

import json
from PySide6.QtCore import QObject, Signal, QTimer, QUrl
from PySide6.QtWebSockets import QWebSocket
from PySide6.QtNetwork import QAbstractSocket

from app.protocol.messages import (
    ResultMessage, BinaryFrameMeta,
    EXECUTION_TIMEOUT_MS, HEARTBEAT_TIMEOUT_MULTIPLIER,
)
from app.network.reconnect import ReconnectTimer

class WebSocketClient(QObject):
    """WebSocket 客户端，管理连接生命周期"""

    # 信号
    connected = Signal()
    disconnected = Signal()  # 非主动断开
    status_changed = Signal(str)  # ConnectionStatus
    result_received = Signal(ResultMessage)

    def __init__(self,
                 host: str = "127.0.0.1",
                 port: int = 9318,
                 heartbeat_interval_ms: int = 30000,
                 reconnect_enabled: bool = True,
                 reconnect_max_attempts: int = 0,
                 reconnect_base_delay_ms: int = 1000,
                 reconnect_max_delay_ms: int = 30000,
                 parent: QObject | None = None):
        super().__init__(parent)
        self._host = host
        self._port = port
        self._heartbeat_interval_ms = heartbeat_interval_ms

        # QWebSocket 实例
        self._socket: QWebSocket | None = None
        self._intentional_close = False

        # 定时器（在 __init__ 中创建，复用，避免泄漏）
        self._heartbeat_timer = QTimer(self)
        self._heartbeat_timer.timeout.connect(self._send_heartbeat)
        self._heartbeat_timeout = QTimer(self)
        self._heartbeat_timeout.setSingleShot(True)
        self._heartbeat_timeout.timeout.connect(self._on_heartbeat_timeout)
        self._execution_timer = QTimer(self)
        self._execution_timer.setSingleShot(True)
        self._execution_timer.timeout.connect(self._on_execution_timeout)
        self._pending_binary_timer: QTimer | None = None

        # 二进制帧协议
        self._pending_binary_meta: BinaryFrameMeta | None = None
        self._pending_binary_timer = QTimer(self)
        self._pending_binary_timer.setSingleShot(True)
        self._pending_binary_timer.timeout.connect(self._on_pending_binary_timeout)

        # 重连
        self._reconnect = ReconnectTimer(
            enabled=reconnect_enabled,
            max_attempts=reconnect_max_attempts,
            base_delay_ms=reconnect_base_delay_ms,
            max_delay_ms=reconnect_max_delay_ms,
            on_reconnect=self._do_connect,
            parent=self,
        )

    # ============ 公共 API ============

    def connect_to_host(self, host: str, port: int):
        """更新地址并连接"""
        self._host = host
        self._port = port
        self._do_connect()

    def disconnect(self):
        """主动断开连接"""
        self._intentional_close = True
        self._reconnect.destroy()
        self._stop_heartbeat()
        self._clear_execution_timeout()
        self._clear_pending_binary()

        if self._socket:
            self._socket.close(1000, "用户主动断开")
            self._socket = None

        self.status_changed.emit("disconnected")
        print("[WS] 已断开连接")

    def send_code(self, code: str) -> bool:
        """发送 JS 代码执行"""
        if self._socket is None or self._socket.state() != QAbstractSocket.ConnectedState:
            print("[WS] 未连接，无法发送代码")
            return False

        msg = json.dumps({"type": "command", "data": code}, ensure_ascii=False)
        result = self._socket.sendTextMessage(msg)
        if result > 0:
            print(f"[WS] 已发送代码 ({len(code)} 字符)")
            self._start_execution_timeout()
            return True
        else:
            print("[WS] 发送失败")
            return False

    def update_reconnect_config(self, enabled: bool, max_attempts: int,
                                 base_delay_ms: int, max_delay_ms: int):
        """更新重连配置"""
        self._reconnect.enabled = enabled
        self._reconnect.max_attempts = max_attempts
        self._reconnect.base_delay_ms = base_delay_ms
        self._reconnect.max_delay_ms = max_delay_ms

    # ============ 内部实现 ============

    def _do_connect(self):
        """执行实际连接"""
        if self._socket and self._socket.state() == QAbstractSocket.ConnectedState:
            print("[WS] 已连接，无需重复连接")
            return

        # 清理旧 socket（避免重连时泄漏）
        if self._socket:
            self._socket.deleteLater()
            self._socket = None

        self._intentional_close = False
        self.status_changed.emit("connecting")

        url = f"ws://{self._host}:{self._port}"
        print(f"[WS] 正在连接 {url}")

        self._socket = QWebSocket()
        self._socket.connected.connect(self._on_connected)
        self._socket.disconnected.connect(self._on_disconnected)
        self._socket.textMessageReceived.connect(self._on_text_message)
        self._socket.binaryMessageReceived.connect(self._on_binary_message)
        self._socket.errorOccurred.connect(self._on_error)

        self._socket.open(QUrl(url))

    def _on_connected(self):
        print("[WS] 连接成功")
        self.status_changed.emit("connected")
        self._reconnect.reset()
        self._start_heartbeat()
        self.connected.emit()

    def _on_disconnected(self):
        print("[WS] 连接关闭")
        self._socket = None
        self._stop_heartbeat()
        self._clear_execution_timeout()
        self._clear_pending_binary()

        if not self._intentional_close:
            self.status_changed.emit("disconnected")
            self.disconnected.emit()
            self._reconnect.schedule()

    def _on_error(self, error: QAbstractSocket.SocketError):
        print(f"[WS] 连接错误: {error}")
        # errorOccurred 之后会触发 disconnected，不在此处设置状态

    def _on_text_message(self, text: str):
        """处理文本帧"""
        try:
            msg = json.loads(text)
        except json.JSONDecodeError:
            print(f"[WS] 收到无效 JSON: {text[:100]}")
            return

        msg_type = msg.get("type", "")

        if msg_type == "result":
            self._clear_execution_timeout()

            data_type = msg.get("dataType", "text")
            if data_type == "binary":
                # 二进制元数据帧：等待后续二进制数据
                self._pending_binary_meta = BinaryFrameMeta(
                    mime=msg.get("mime", "image/png"),
                    size=msg.get("size", 0),
                )
                self._start_pending_binary_timeout()
                return

            # 普通文本/Base64 结果
            result = ResultMessage.from_json(msg)
            self.result_received.emit(result)

        elif msg_type == "pong":
            self._reset_heartbeat_timeout()

    def _on_binary_message(self, data: bytes):
        """处理二进制帧"""
        if self._pending_binary_meta:
            meta = self._pending_binary_meta
            self._pending_binary_meta = None
            self._clear_pending_binary()

            # QByteArray 转 Base64（同步，极快）
            import base64
            b64 = base64.b64encode(data).decode("ascii")

            self._clear_execution_timeout()
            result = ResultMessage(
                type="result",
                status="success",
                data_type="base64",
                data=b64,
                mime=meta.mime,
            )
            self.result_received.emit(result)

    # ============ 心跳 ============

    def _start_heartbeat(self):
        self._stop_heartbeat()
        self._heartbeat_timer.start(self._heartbeat_interval_ms)

    def _stop_heartbeat(self):
        self._heartbeat_timer.stop()
        self._heartbeat_timeout.stop()

    def _send_heartbeat(self):
        if self._socket and self._socket.state() == QAbstractSocket.ConnectedState:
            self._socket.sendTextMessage(json.dumps({"type": "ping"}))

            timeout_ms = self._heartbeat_interval_ms * HEARTBEAT_TIMEOUT_MULTIPLIER
            self._heartbeat_timeout.start(timeout_ms)

    def _reset_heartbeat_timeout(self):
        self._heartbeat_timeout.stop()

    def _on_heartbeat_timeout(self):
        print("[WS] 心跳超时，断开连接")
        if self._socket:
            self._socket.close()
            self._socket = None

    # ============ 执行超时 ============

    def _start_execution_timeout(self):
        self._execution_timer.start(EXECUTION_TIMEOUT_MS)

    def _clear_execution_timeout(self):
        self._execution_timer.stop()

    def _on_execution_timeout(self):
        print("[WS] 执行超时")
        result = ResultMessage(
            type="result",
            status="error",
            data_type="text",
            data=f"执行超时（超过 {EXECUTION_TIMEOUT_MS // 1000} 秒无响应）",
        )
        self.result_received.emit(result)

    # ============ 二进制帧超时 ============

    def _start_pending_binary_timeout(self):
        self._pending_binary_timer.start(EXECUTION_TIMEOUT_MS)

    def _clear_pending_binary(self):
        self._pending_binary_timer.stop()

    def _on_pending_binary_timeout(self):
        print("[WS] 等待二进制帧超时")
        self._pending_binary_meta = None
