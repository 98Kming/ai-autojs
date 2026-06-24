"""调整大小面板"""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QLabel, QSpinBox, QComboBox, QCheckBox, QPushButton,
    QLineEdit,
)

from app.widgets.action_panels.base_panel import BasePanel


class ResizePanel(BasePanel):
    """调整图片大小面板"""

    resize_execute = Signal(int, int, str, str)  # w, h, interpolation, filename

    def __init__(self, parent: QWidget | None = None):
        super().__init__("📐 调整大小", parent)

        # 原始尺寸
        self._orig_w_label = QLabel("原图: - × -")
        self.add_widget(self._orig_w_label)

        # 宽度
        row1 = QHBoxLayout()
        row1.addWidget(QLabel("宽:"))
        self._w_input = QSpinBox()
        self._w_input.setRange(1, 8192)
        self._w_input.setValue(1920)
        self._w_input.valueChanged.connect(self._on_w_changed)
        row1.addWidget(self._w_input)
        self.add_layout(row1)

        # 高度
        row2 = QHBoxLayout()
        row2.addWidget(QLabel("高:"))
        self._h_input = QSpinBox()
        self._h_input.setRange(1, 8192)
        self._h_input.setValue(1080)
        self._h_input.valueChanged.connect(self._on_h_changed)
        row2.addWidget(self._h_input)
        self.add_layout(row2)

        # 锁定比例
        self._lock_ratio = QCheckBox("锁定宽高比")
        self._lock_ratio.setChecked(True)
        self.add_widget(self._lock_ratio)

        # 插值方法
        row3 = QHBoxLayout()
        row3.addWidget(QLabel("插值:"))
        self._interp_combo = QComboBox()
        self._interp_combo.addItems([
            "最近邻 (Nearest)",
            "双线性 (Bilinear)",
            "双三次 (Bicubic)",
            "Lanczos4",
            "区域 (Area)",
        ])
        self._interp_combo.setCurrentIndex(3)  # Lanczos4 默认
        row3.addWidget(self._interp_combo)
        self.add_layout(row3)

        # 文件名
        row4 = QHBoxLayout()
        row4.addWidget(QLabel("文件名:"))
        self._filename = QLineEdit("resized.png")
        self._filename.returnPressed.connect(self._on_execute)
        row4.addWidget(self._filename)
        self.add_layout(row4)

        # 执行按钮
        exec_btn = QPushButton("执行缩放")
        exec_btn.clicked.connect(self._on_execute)
        self.add_widget(exec_btn)

        self._orig_w = 0
        self._orig_h = 0
        self._ratio = 1.0
        self._updating = False

    def set_original_size(self, w: int, h: int):
        """设置原始尺寸"""
        self._orig_w = w
        self._orig_h = h
        self._ratio = w / h if h > 0 else 1.0
        self._orig_w_label.setText(f"原图: {w} × {h}")
        self._w_input.setValue(w)
        self._h_input.setValue(h)

    def _on_w_changed(self, val: int):
        if self._updating:
            return
        if self._lock_ratio.isChecked() and self._ratio > 0:
            self._updating = True
            self._h_input.setValue(int(val / self._ratio))
            self._updating = False
        self._filename.setText(f"resized_{self._w_input.value()}_{self._h_input.value()}.png")

    def _on_h_changed(self, val: int):
        if self._updating:
            return
        if self._lock_ratio.isChecked() and self._ratio > 0:
            self._updating = True
            self._w_input.setValue(int(val * self._ratio))
            self._updating = False
        self._filename.setText(f"resized_{self._w_input.value()}_{self._h_input.value()}.png")

    def _on_execute(self):
        inter_map = {
            "最近邻 (Nearest)": "nearest",
            "双线性 (Bilinear)": "bilinear",
            "双三次 (Bicubic)": "bicubic",
            "Lanczos4": "lanczos4",
            "区域 (Area)": "area",
        }
        interp = inter_map.get(self._interp_combo.currentText(), "bilinear")
        self.resize_execute.emit(
            self._w_input.value(),
            self._h_input.value(),
            interp,
            self._filename.text() or "resized.png",
        )
