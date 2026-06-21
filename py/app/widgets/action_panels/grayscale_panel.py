"""灰度化面板"""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QLabel, QLineEdit, QPushButton,
)

from app.widgets.action_panels.base_panel import BasePanel


class GrayscalePanel(BasePanel):
    """灰度化面板"""

    grayscale_execute = Signal(str)  # filename

    def __init__(self, parent: QWidget | None = None):
        super().__init__("⬜ 灰度化", parent)

        info = QLabel("将彩色图片转换为灰度图")
        self.add_widget(info)

        # 文件名
        row = QHBoxLayout()
        row.addWidget(QLabel("文件名:"))
        self._filename = QLineEdit("gray.png")
        row.addWidget(self._filename)
        self.add_layout(row)

        # 执行按钮
        exec_btn = QPushButton("执行灰度化")
        exec_btn.clicked.connect(self._on_execute)
        self.add_widget(exec_btn)

    def _on_execute(self):
        self.grayscale_execute.emit(self._filename.text() or "gray.png")
