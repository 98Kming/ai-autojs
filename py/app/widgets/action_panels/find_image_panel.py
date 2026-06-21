"""模板匹配 (findImage) 面板"""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QLabel, QSpinBox, QDoubleSpinBox, QLineEdit, QPushButton,
    QPlainTextEdit,
)

from app.widgets.action_panels.base_panel import BasePanel


class FindImagePanel(BasePanel):
    """模板匹配面板：搜索区域 + 阈值 + 结果"""

    find_execute = Signal(int, int, int, int, float)  # x, y, w, h, threshold

    def __init__(self, parent: QWidget | None = None):
        super().__init__("🔍 找图", parent)

        # 搜索区域 X, Y
        row1 = QHBoxLayout()
        row1.addWidget(QLabel("X:"))
        self._x_input = QSpinBox()
        self._x_input.setRange(0, 99999)
        row1.addWidget(self._x_input)
        row1.addWidget(QLabel("Y:"))
        self._y_input = QSpinBox()
        self._y_input.setRange(0, 99999)
        row1.addWidget(self._y_input)
        self.add_layout(row1)

        # W, H
        row2 = QHBoxLayout()
        row2.addWidget(QLabel("W:"))
        self._w_input = QSpinBox()
        self._w_input.setRange(1, 99999)
        self._w_input.setValue(500)
        row2.addWidget(self._w_input)
        row2.addWidget(QLabel("H:"))
        self._h_input = QSpinBox()
        self._h_input.setRange(1, 99999)
        self._h_input.setValue(500)
        row2.addWidget(self._h_input)
        self.add_layout(row2)

        # 阈值 (0.01 ~ 1.0)
        row3 = QHBoxLayout()
        row3.addWidget(QLabel("阈值:"))
        self._threshold_input = QDoubleSpinBox()
        self._threshold_input.setRange(0.01, 1.0)
        self._threshold_input.setSingleStep(0.05)
        self._threshold_input.setValue(0.9)
        row3.addWidget(self._threshold_input)
        self.add_layout(row3)

        # 模板提示
        self._template_label = QLabel("模板: 当前选中图片")
        self._template_label.setStyleSheet("color: #8af; font-size: 11px; border: none;")
        self.add_widget(self._template_label)

        # 结果展示
        self._result_view = QPlainTextEdit()
        self._result_view.setReadOnly(True)
        self._result_view.setMaximumHeight(80)
        self._result_view.setPlaceholderText("查找结果将显示在此处...")
        self.add_widget(self._result_view)

        # 执行按钮
        exec_btn = QPushButton("执行找图")
        exec_btn.clicked.connect(self._on_execute)
        self.add_widget(exec_btn)

    def set_region(self, x: int, y: int, w: int, h: int):
        """从裁剪坐标自动扩展搜索区域"""
        self._x_input.setValue(max(0, x - 50))
        self._y_input.setValue(max(0, y - 50))
        self._w_input.setValue(w + 100)
        self._h_input.setValue(h + 100)

    def set_result(self, text: str):
        self._result_view.setPlainText(text)

    def _on_execute(self):
        self.find_execute.emit(
            self._x_input.value(),
            self._y_input.value(),
            self._w_input.value(),
            self._h_input.value(),
            self._threshold_input.value(),
        )
