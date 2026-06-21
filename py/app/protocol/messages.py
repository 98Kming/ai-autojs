"""消息协议类型定义，对应 src/types/autojs.ts"""

from dataclasses import dataclass, field
from typing import Optional, Literal

# 连接状态
ConnectionStatus = Literal["disconnected", "connecting", "connected", "error"]

# 结果数据类型
ResultDataType = Literal["text", "base64", "binary"]

# 执行状态
ExecutionStatus = Literal["success", "error", "pending"]


@dataclass
class ConnectionConfig:
    """连接配置，对应 Vue 版 ConnectionConfig"""
    host: str = "127.0.0.1"
    port: int = 9318
    reconnect_enabled: bool = True
    reconnect_max_attempts: int = 0  # 0 = 无限
    reconnect_base_delay_ms: int = 1000
    reconnect_max_delay_ms: int = 30000
    heartbeat_interval_ms: int = 30000


# 默认配置
DEFAULT_CONFIG = ConnectionConfig()

# 协议常量
DEFAULT_PORT = 9318
EXECUTION_TIMEOUT_MS = 120000  # 2 分钟
HEARTBEAT_TIMEOUT_MULTIPLIER = 2  # pong 必须在 heartbeat_interval * 2 内到达


@dataclass
class ResultMessage:
    """服务端返回的执行结果"""
    type: str = "result"
    data: str = ""
    status: ExecutionStatus = "success"
    data_type: ResultDataType = "text"
    mime: Optional[str] = None
    size: Optional[int] = None

    @classmethod
    def from_json(cls, obj: dict) -> "ResultMessage":
        return cls(
            type=obj.get("type", "result"),
            data=obj.get("data", ""),
            status=obj.get("status", "success"),
            data_type=obj.get("dataType", "text"),
            mime=obj.get("mime"),
            size=obj.get("size"),
        )


@dataclass
class CommandMessage:
    """客户端发送的命令"""
    type: str = "command"
    data: str = ""


@dataclass
class PingMessage:
    """心跳 Ping"""
    type: str = "ping"


@dataclass
class PongMessage:
    """心跳 Pong"""
    type: str = "pong"


@dataclass
class ResultEntry:
    """单条执行结果（用于 UI 展示）"""
    id: str
    timestamp: float
    data: str
    status: ExecutionStatus
    data_type: ResultDataType
    mime: Optional[str] = None
    duration_ms: Optional[float] = None


@dataclass
class HistoryEntry:
    """执行历史条目，对应 Vue 版 HistoryEntry"""
    id: str
    code: str
    result: str
    result_data_type: ResultDataType = "text"
    result_mime: Optional[str] = None
    status: ExecutionStatus = "pending"
    timestamp: float = 0.0
    duration_ms: Optional[float] = None


@dataclass
class ImageEntry:
    """图片条目，对应 Vue 版 ImageEntry"""
    id: str
    data: str  # Base64 编码的图片数据（内存缓存），或为空（从文件加载）
    mime: str = "image/png"
    timestamp: float = 0.0
    code: str = ""  # 生成该图片的源代码
    file: str = ""  # 对应的磁盘文件名（相对于 images/ 目录）


# 二进制帧元数据（用于两帧协议）
@dataclass
class BinaryFrameMeta:
    """二进制帧元数据，第一帧 JSON 后等待第二帧二进制数据"""
    mime: str
    size: int
