"""连接状态 Model，对应 useWebSocketStore"""
from __future__ import annotations

from PySide6.QtCore import QObject, Signal, Property

from app.protocol.messages import ConnectionConfig, ConnectionStatus, DEFAULT_CONFIG
from app.persistence import config_store

class ConnectionModel(QObject):
    """连接配置与状态管理"""

    # 信号
    config_changed = Signal()
    status_changed = Signal(str)  # ConnectionStatus
    history_visible_changed = Signal(bool)

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        # 从文件加载配置，与默认值合并
        saved = config_store.load_config()
        self._config = ConnectionConfig(
            host=saved.get("host", DEFAULT_CONFIG.host),
            port=saved.get("port", DEFAULT_CONFIG.port),
            reconnect_enabled=saved.get("reconnectEnabled", DEFAULT_CONFIG.reconnect_enabled),
            reconnect_max_attempts=saved.get("reconnectMaxAttempts", DEFAULT_CONFIG.reconnect_max_attempts),
            reconnect_base_delay_ms=saved.get("reconnectBaseDelayMs", DEFAULT_CONFIG.reconnect_base_delay_ms),
            reconnect_max_delay_ms=saved.get("reconnectMaxDelayMs", DEFAULT_CONFIG.reconnect_max_delay_ms),
            heartbeat_interval_ms=saved.get("heartbeatIntervalMs", DEFAULT_CONFIG.heartbeat_interval_ms),
        )
        self._status: ConnectionStatus = "disconnected"
        self._last_error: str | None = None
        self._history_visible = False

    # ============ 属性 ============

    @property
    def host(self) -> str:
        return self._config.host

    @host.setter
    def host(self, value: str):
        if self._config.host != value:
            self._config.host = value
            self._save_config()

    @property
    def port(self) -> int:
        return self._config.port

    @port.setter
    def port(self, value: int):
        if self._config.port != value:
            self._config.port = value
            self._save_config()

    @property
    def status(self) -> ConnectionStatus:
        return self._status

    @property
    def last_error(self) -> str | None:
        return self._last_error

    @property
    def history_visible(self) -> bool:
        return self._history_visible

    @property
    def config(self) -> ConnectionConfig:
        return self._config

    @property
    def is_connected(self) -> bool:
        return self._status == "connected"

    # ============ 方法 ============

    def set_status(self, status: ConnectionStatus):
        """设置连接状态，非 error 时自动清除 last_error"""
        if self._status != status:
            self._status = status
            if status != "error":
                self._last_error = None
            self.status_changed.emit(status)

    def set_error(self, message: str):
        """设置错误状态"""
        self._last_error = message
        self._status = "error"
        self.status_changed.emit("error")

    def toggle_history(self):
        """切换历史抽屉显示"""
        self._history_visible = not self._history_visible
        self.history_visible_changed.emit(self._history_visible)

    def _save_config(self):
        """持久化当前配置"""
        config_store.save_config({
            "host": self._config.host,
            "port": self._config.port,
            "reconnectEnabled": self._config.reconnect_enabled,
            "reconnectMaxAttempts": self._config.reconnect_max_attempts,
            "reconnectBaseDelayMs": self._config.reconnect_base_delay_ms,
            "reconnectMaxDelayMs": self._config.reconnect_max_delay_ms,
            "heartbeatIntervalMs": self._config.heartbeat_interval_ms,
        })
        self.config_changed.emit()
