"""代码编辑器 Model，对应 useCodeStore"""
from __future__ import annotations

from PySide6.QtCore import QObject, Signal

from app.protocol.messages import ResultEntry, ResultMessage

class CodeEditorModel(QObject):
    """编辑器内容与执行状态"""

    content_changed = Signal(str)
    executing_changed = Signal(bool)
    result_received = Signal(ResultEntry)

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self._content = ""
        self._is_executing = False
        self._last_result: ResultEntry | None = None

    @property
    def content(self) -> str:
        return self._content

    @property
    def is_executing(self) -> bool:
        return self._is_executing

    @property
    def last_result(self) -> ResultEntry | None:
        return self._last_result

    def set_content(self, text: str):
        if self._content != text:
            self._content = text
            self.content_changed.emit(text)

    def clear_content(self):
        self._content = ""
        self._last_result = None
        self.content_changed.emit("")

    def set_executing(self, val: bool):
        if self._is_executing != val:
            self._is_executing = val
            self.executing_changed.emit(val)

    def set_result(self, msg: ResultMessage, duration_ms: float = 0):
        """将 WebSocket ResultMessage 转为 ResultEntry"""
        import time
        import secrets

        entry = ResultEntry(
            id=secrets.token_hex(8),
            timestamp=time.time(),
            data=msg.data,
            status=msg.status,
            data_type=msg.data_type,
            mime=msg.mime,
            duration_ms=duration_ms,
        )
        self._last_result = entry
        self.result_received.emit(entry)

    def clear_result(self):
        self._last_result = None
