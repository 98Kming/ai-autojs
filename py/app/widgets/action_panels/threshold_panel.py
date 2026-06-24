"""固定阈值面板"""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QLabel, QSpinBox, QLineEdit, QPushButton,
)

from app.widgets.action_panels.base_panel import BasePanel


class ThresholdPanel(BasePanel):
    """固定阈值二值化面板"""

    threshold_execute = Signal(int, int, str)  # thresh, maxval, filename

    def __init__(self, parent: QWidget | None = None):
        super().__init__("⚫ 固定阈值", parent)

        # 阈值 (0-255)
        row1 = QHBoxLayout()
        row1.addWidget(QLabel("阈值:"))
        self._thresh_input = QSpinBox()
        self._thresh_input.setRange(0, 255)
        self._thresh_input.setValue(127)
        row1.addWidget(self._thresh_input)
        self.add_layout(row1)

        # 最大值 (0-255)
        row2 = QHBoxLayout()
        row2.addWidget(QLabel("最大值:"))
        self._maxval_input = QSpinBox()
        self._maxval_input.setRange(0, 255)
        self._maxval_input.setValue(255)
        row2.addWidget(self._maxval_input)
        self.add_layout(row2)

        # 文件名
        row3 = QHBoxLayout()
        row3.addWidget(QLabel("文件名:"))
        self._filename = QLineEdit("threshold.png")
        self._filename.returnPressed.connect(self._on_execute)
        row3.addWidget(self._filename)
        self.add_layout(row3)

        # 执行
        exec_btn = QPushButton("执行阈值化")
        exec_btn.clicked.connect(self._on_execute)
        self.add_widget(exec_btn)

    def _on_execute(self):
        self.threshold_execute.emit(
            self._thresh_input.value(),
            self._maxval_input.value(),
            self._filename.text() or "threshold.png",
        )
