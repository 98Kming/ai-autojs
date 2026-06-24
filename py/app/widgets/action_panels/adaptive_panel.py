"""自适应阈值面板"""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QLabel, QSpinBox, QComboBox, QLineEdit, QPushButton,
)

from app.widgets.action_panels.base_panel import BasePanel


class AdaptivePanel(BasePanel):
    """自适应阈值二值化面板"""

    adaptive_execute = Signal(int, str, int, int, str)  # maxval, method, block_size, C, filename

    def __init__(self, parent: QWidget | None = None):
        super().__init__("🔲 自适应阈值", parent)

        # 最大值
        row1 = QHBoxLayout()
        row1.addWidget(QLabel("最大值:"))
        self._maxval_input = QSpinBox()
        self._maxval_input.setRange(0, 255)
        self._maxval_input.setValue(255)
        row1.addWidget(self._maxval_input)
        self.add_layout(row1)

        # 方法
        row2 = QHBoxLayout()
        row2.addWidget(QLabel("方法:"))
        self._method_combo = QComboBox()
        self._method_combo.addItems(["高斯 (Gaussian)", "均值 (Mean)"])
        row2.addWidget(self._method_combo)
        self.add_layout(row2)

        # 块大小 (3-99, 奇数)
        row3 = QHBoxLayout()
        row3.addWidget(QLabel("块大小:"))
        self._block_input = QSpinBox()
        self._block_input.setRange(3, 99)
        self._block_input.setSingleStep(2)
        self._block_input.setValue(11)
        row3.addWidget(self._block_input)
        self.add_layout(row3)

        # C 值 (-50 ~ 50)
        row4 = QHBoxLayout()
        row4.addWidget(QLabel("C 值:"))
        self._c_input = QSpinBox()
        self._c_input.setRange(-50, 50)
        self._c_input.setValue(2)
        row4.addWidget(self._c_input)
        self.add_layout(row4)

        # 文件名
        row5 = QHBoxLayout()
        row5.addWidget(QLabel("文件名:"))
        self._filename = QLineEdit("adaptive.png")
        self._filename.returnPressed.connect(self._on_execute)
        row5.addWidget(self._filename)
        self.add_layout(row5)

        # 执行
        exec_btn = QPushButton("执行自适应阈值")
        exec_btn.clicked.connect(self._on_execute)
        self.add_widget(exec_btn)

    def _on_execute(self):
        method = "gaussian" if "高斯" in self._method_combo.currentText() else "mean"
        self.adaptive_execute.emit(
            self._maxval_input.value(),
            method,
            self._block_input.value(),
            self._c_input.value(),
            self._filename.text() or "adaptive.png",
        )
