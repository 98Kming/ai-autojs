"""单条历史记录卡片，对应 HistoryItem.vue"""
from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QApplication,
)

from app.protocol.messages import HistoryEntry
from app.widgets.styles import COLORS

class HistoryItem(QFrame):
    """单条历史记录卡片"""

    re_run = Signal(HistoryEntry)
    delete_requested = Signal(str)

    def __init__(self, entry: HistoryEntry, parent: QWidget | None = None):
        super().__init__(parent)
        self._entry = entry
        self.setup_ui()

    def setup_ui(self):
        self.setStyleSheet(f"""
            HistoryItem {{
                border: 1px solid {COLORS['border']};
                border-radius: 6px;
                background: {COLORS['bg_primary']};
                margin: 3px 0;
            }}
            HistoryItem:hover {{
                border-color: {COLORS['primary']};
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(6)

        # ====== 头部 ======
        header = QHBoxLayout()

        # 状态标签
        status_text = {"success": "成功", "error": "失败", "pending": "等待中"}
        status_color = {
            "success": COLORS["success"],
            "error": COLORS["danger"],
            "pending": COLORS["warning"],
        }
        status_label = QLabel(status_text.get(self._entry.status, "未知"))
        status_label.setStyleSheet(f"""
            QLabel {{
                color: white;
                background: {status_color.get(self._entry.status, COLORS['info'])};
                border-radius: 3px;
                padding: 1px 6px;
                font-size: 11px;
            }}
        """)
        status_label.setFixedHeight(20)
        header.addWidget(status_label)

        header.addStretch()

        # 时间戳
        ts = datetime.fromtimestamp(self._entry.timestamp).strftime("%Y-%m-%d %H:%M:%S")
        ts_label = QLabel(ts)
        ts_label.setStyleSheet(f"color: {COLORS['text_placeholder']}; font-size: 11px; border: none;")
        header.addWidget(ts_label)

        # 执行耗时
        if self._entry.duration_ms is not None:
            dur = self._entry.duration_ms
            dur_text = f"{dur:.0f}ms" if dur < 1000 else f"{dur / 1000:.1f}s"
            dur_label = QLabel(dur_text)
            dur_label.setStyleSheet(f"""
                QLabel {{
                    color: {COLORS['text_secondary']};
                    background: {COLORS['bg_tertiary']};
                    border-radius: 3px;
                    padding: 1px 4px;
                    font-size: 11px;
                }}
            """)
            header.addWidget(dur_label)

        layout.addLayout(header)

        # ====== 代码预览 ======
        code_preview = self._entry.code[:80].replace("\n", " ")
        code_label = QLabel(code_preview + ("..." if len(self._entry.code) > 80 else ""))
        code_label.setFont(self._mono_font())
        code_label.setStyleSheet(f"""
            QLabel {{
                color: {COLORS['text_secondary']};
                background: {COLORS['bg_secondary']};
                border-radius: 3px;
                padding: 4px 6px;
                font-size: 12px;
                border: none;
            }}
        """)
        code_label.setWordWrap(True)
        layout.addWidget(code_label)

        # ====== 结果预览 ======
        if self._entry.result_data_type == "base64":
            result_text = "[二进制数据]"
        else:
            result_text = self._entry.result[:60].replace("\n", " ")
            if len(self._entry.result) > 60:
                result_text += "..."
        result_label = QLabel(result_text)
        result_label.setWordWrap(True)
        result_label.setStyleSheet(f"color: {COLORS['text_placeholder']}; font-size: 12px; border: none;")
        layout.addWidget(result_label)

        # ====== 操作按钮 ======
        actions = QHBoxLayout()

        re_run_btn = QPushButton("▶ 重新运行")
        re_run_btn.setFixedHeight(22)
        re_run_btn.setStyleSheet(f"font-size: 11px; padding: 1px 8px;")
        re_run_btn.clicked.connect(lambda _=False: self.re_run.emit(self._entry))
        actions.addWidget(re_run_btn)

        copy_btn = QPushButton("📋 复制代码")
        copy_btn.setFixedHeight(22)
        copy_btn.setStyleSheet(f"font-size: 11px; padding: 1px 8px;")
        copy_btn.clicked.connect(lambda _=False: QApplication.clipboard().setText(self._entry.code))
        actions.addWidget(copy_btn)

        actions.addStretch()

        delete_btn = QPushButton("删除")
        delete_btn.setFixedHeight(22)
        delete_btn.setStyleSheet(f"""
            QPushButton {{
                font-size: 11px; padding: 1px 8px;
                color: {COLORS['danger']};
                border: 1px solid {COLORS['danger']};
                border-radius: 3px;
            }}
            QPushButton:hover {{
                background: {COLORS['danger']};
                color: white;
            }}
        """)
        delete_btn.clicked.connect(lambda _=False: self.delete_requested.emit(self._entry.id))
        actions.addWidget(delete_btn)

        layout.addLayout(actions)

    def _mono_font(self) -> QFont:
        font = QFont("Consolas")
        font.setStyleHint(QFont.Monospace)
        font.setPixelSize(12)
        return font
