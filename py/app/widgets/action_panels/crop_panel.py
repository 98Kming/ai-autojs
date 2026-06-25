"""裁剪面板"""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QLineEdit, QSpinBox, QPushButton,
)

from app.widgets.action_panels.base_panel import BasePanel


class _InvertSpinBox(QSpinBox):
    """方向键反转的 SpinBox：按上减小、按下增大"""
    def stepBy(self, steps: int):
        super().stepBy(-steps)


class CropPanel(BasePanel):
    """裁剪参数面板：X/Y/W/H 编辑 + 执行"""

    crop_execute = Signal(int, int, int, int, str)  # x, y, w, h, filename
    region_changed = Signal(int, int, int, int)  # x, y, w, h

    def __init__(self, parent: QWidget | None = None):
        super().__init__("✂️ 裁剪", parent)

        # X, Y
        row1 = QHBoxLayout()
        row1.addWidget(QLabel("X:"))
        self._x_input = _InvertSpinBox()
        self._x_input.setRange(0, 99999)
        self._x_input.valueChanged.connect(self._on_coord_changed)
        row1.addWidget(self._x_input)
        row1.addWidget(QLabel("Y:"))
        self._y_input = _InvertSpinBox()
        self._y_input.setRange(0, 99999)
        self._y_input.valueChanged.connect(self._on_coord_changed)
        row1.addWidget(self._y_input)
        self.add_layout(row1)

        # W, H
        row2 = QHBoxLayout()
        row2.addWidget(QLabel("W:"))
        self._w_input = _InvertSpinBox()
        self._w_input.setRange(1, 99999)
        self._w_input.valueChanged.connect(self._on_coord_changed)
        row2.addWidget(self._w_input)
        row2.addWidget(QLabel("H:"))
        self._h_input = _InvertSpinBox()
        self._h_input.setRange(1, 99999)
        self._h_input.valueChanged.connect(self._on_coord_changed)
        row2.addWidget(self._h_input)
        self.add_layout(row2)

        # 文件名
        row3 = QHBoxLayout()
        row3.addWidget(QLabel("文件名:"))
        self._filename = QLineEdit("crop.png")
        self._filename.returnPressed.connect(self._on_execute)
        row3.addWidget(self._filename)
        self.add_layout(row3)

        # 执行按钮
        exec_btn = QPushButton("执行裁剪")
        exec_btn.clicked.connect(self._on_execute)
        self.add_widget(exec_btn)

    def set_region(self, x: int, y: int, w: int, h: int):
        """从查看器框选结果设置坐标"""
        self._x_input.setValue(x)
        self._y_input.setValue(y)
        self._w_input.setValue(w)
        self._h_input.setValue(h)
        self._filename.setText(f"_{x}_{y}_{w}_{h}.png")

    def _on_coord_changed(self):
        """坐标变化时更新文件名并通知查看器更新选区"""
        x = self._x_input.value()
        y = self._y_input.value()
        w = self._w_input.value()
        h = self._h_input.value()
        self._filename.setText(f"_{x}_{y}_{w}_{h}.png")
        self.region_changed.emit(x, y, w, h)

    def _on_execute(self):
        self.crop_execute.emit(
            self._x_input.value(),
            self._y_input.value(),
            self._w_input.value(),
            self._h_input.value(),
            self._filename.text() or "crop.png",
        )
