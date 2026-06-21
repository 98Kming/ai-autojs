"""顶栏组件，对应 AppHeader.vue"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPainter, QColor, QFont
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QLabel, QToolButton, QSizePolicy,
)

from app.widgets.status_dot import StatusDot
from app.widgets.styles import COLORS

class HeaderBar(QWidget):
    """顶栏：Logo + 状态指示灯 + 历史按钮"""

    history_clicked = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setFixedHeight(48)
        self.setStyleSheet(f"background: {COLORS['bg_primary']}; border-bottom: 1px solid {COLORS['border']};")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 0, 12, 0)
        layout.setSpacing(0)

        # 左侧：Logo
        logo = QLabel("AI-AutoJS")
        logo.setFont(QFont("Microsoft YaHei", 14, QFont.Bold))
        logo.setStyleSheet(f"color: {COLORS['primary']}; border: none;")
        layout.addWidget(logo)

        layout.addStretch()

        # 中间：状态指示灯
        self._status_dot = StatusDot()
        layout.addWidget(self._status_dot)
        layout.addSpacing(12)

        # 右侧：历史记录按钮
        self._history_btn = QToolButton()
        self._history_btn.setText("📋 历史")
        self._history_btn.setToolTip("查看执行历史")
        self._history_btn.setStyleSheet(f"""
            QToolButton {{
                border: 1px solid {COLORS['border']};
                border-radius: 4px;
                padding: 4px 12px;
                background: {COLORS['bg_primary']};
            }}
            QToolButton:hover {{
                border-color: {COLORS['primary']};
            }}
        """)
        self._history_btn.clicked.connect(self.history_clicked.emit)
        layout.addWidget(self._history_btn)

    @property
    def status_dot(self) -> StatusDot:
        return self._status_dot

    def update_badge(self, count: int):
        """更新历史按钮上的数量徽章"""
        if count > 0:
            self._history_btn.setText(f"📋 历史 ({count})")
        else:
            self._history_btn.setText("📋 历史")
