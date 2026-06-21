"""执行历史 Model，对应 useHistoryStore"""
from __future__ import annotations

import time
import secrets
from typing import Optional

from PySide6.QtCore import QObject, Signal

from app.protocol.messages import HistoryEntry, ExecutionStatus, ResultDataType
from app.persistence import config_store

class HistoryModel(QObject):
    """执行历史管理，JSON 文件持久化"""

    MAX_ENTRIES = 500  # 放宽至 500（Vue 版为 200）

    entries_changed = Signal()

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        # 从文件加载历史
        saved = config_store.load_history()
        self._entries: list[HistoryEntry] = []
        for item in saved:
            try:
                self._entries.append(HistoryEntry(
                    id=item.get("id", ""),
                    code=item.get("code", ""),
                    result=item.get("result", ""),
                    result_data_type=item.get("result_data_type", "text"),
                    result_mime=item.get("result_mime"),
                    status=item.get("status", "pending"),
                    timestamp=item.get("timestamp", 0.0),
                    duration_ms=item.get("duration_ms"),
                ))
            except Exception:
                pass  # 跳过损坏的条目

    @property
    def entries(self) -> list[HistoryEntry]:
        return self._entries

    @property
    def count(self) -> int:
        return len(self._entries)

    def add_entry(self, entry: HistoryEntry):
        """添加新条目到列表头部"""
        self._entries.insert(0, entry)
        self._trim()
        self._persist()
        self.entries_changed.emit()

    def update_last_entry(self, result: str, status: ExecutionStatus,
                          data_type: ResultDataType = "text",
                          mime: Optional[str] = None,
                          duration_ms: Optional[float] = None):
        """更新最新条目的结果"""
        if self._entries:
            e = self._entries[0]
            e.result = result
            e.status = status
            e.result_data_type = data_type
            e.result_mime = mime
            if duration_ms is not None:
                e.duration_ms = duration_ms
            self._persist()
            self.entries_changed.emit()

    def remove_entry(self, entry_id: str):
        self._entries = [e for e in self._entries if e.id != entry_id]
        self._persist()
        self.entries_changed.emit()

    def clear_all(self):
        self._entries.clear()
        self._persist()
        self.entries_changed.emit()

    def _trim(self):
        """超过上限时截断"""
        while len(self._entries) > self.MAX_ENTRIES:
            self._entries.pop()

    def _persist(self):
        """序列化并保存到文件"""
        data = []
        for e in self._entries:
            data.append({
                "id": e.id,
                "code": e.code,
                "result": e.result,
                "result_data_type": e.result_data_type,
                "result_mime": e.result_mime,
                "status": e.status,
                "timestamp": e.timestamp,
                "duration_ms": e.duration_ms,
            })
        config_store.save_history(data)
