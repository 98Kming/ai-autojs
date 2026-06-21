"""颜色范围二值化 (inRange) 面板"""

from __future__ import annotations

from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QLineEdit, QPushButton, QFrame,
)

from app.widgets.action_panels.base_panel import BasePanel


class ColorSwatch(QFrame):
    """颜色色块预览"""

    def __init__(self, color: QColor = QColor(0, 0, 0), parent=None):
        super().__init__(parent)
        self.setFixedSize(24, 24)
        self._color = color
        self.setStyleSheet(f"border: 1px solid #555; border-radius: 3px;")

    def set_color(self, color: QColor):
        self._color = color
        self.setStyleSheet(
            f"background: {color.name()}; border: 1px solid #555; border-radius: 3px;"
        )


class InRangePanel(BasePanel):
    """颜色范围二值化面板"""

    inrange_execute = Signal(int, int, int, int, int, int, str)  # lb,lg,lr, ub,ug,ur, filename
    color_pick_requested = Signal(str)  # "lower" or "upper"

    def __init__(self, parent: QWidget | None = None):
        super().__init__("🎨 二值化 (inRange)", parent)

        # 下界
        lower_label = QLabel("下界 (BGR):")
        lower_label.setStyleSheet("color: #fea; font-weight: bold; border: none;")
        self.add_widget(lower_label)

        row1 = QHBoxLayout()
        row1.addWidget(QLabel("B:"))
        self._lower_b = QLineEdit("0")
        self._lower_b.setFixedWidth(50)
        row1.addWidget(self._lower_b)
        row1.addWidget(QLabel("G:"))
        self._lower_g = QLineEdit("0")
        self._lower_g.setFixedWidth(50)
        row1.addWidget(self._lower_g)
        row1.addWidget(QLabel("R:"))
        self._lower_r = QLineEdit("0")
        self._lower_r.setFixedWidth(50)
        row1.addWidget(self._lower_r)
        self._lower_swatch = ColorSwatch(QColor(0, 0, 0))
        row1.addWidget(self._lower_swatch)
        pick_lower = QPushButton("取色")
        pick_lower.setFixedWidth(40)
        pick_lower.clicked.connect(lambda _=False: self.color_pick_requested.emit("lower"))
        row1.addWidget(pick_lower)
        self.add_layout(row1)

        # 上界
        upper_label = QLabel("上界 (BGR):")
        upper_label.setStyleSheet("color: #fea; font-weight: bold; border: none;")
        self.add_widget(upper_label)

        row2 = QHBoxLayout()
        row2.addWidget(QLabel("B:"))
        self._upper_b = QLineEdit("255")
        self._upper_b.setFixedWidth(50)
        row2.addWidget(self._upper_b)
        row2.addWidget(QLabel("G:"))
        self._upper_g = QLineEdit("255")
        self._upper_g.setFixedWidth(50)
        row2.addWidget(self._upper_g)
        row2.addWidget(QLabel("R:"))
        self._upper_r = QLineEdit("255")
        self._upper_r.setFixedWidth(50)
        row2.addWidget(self._upper_r)
        self._upper_swatch = ColorSwatch(QColor(255, 255, 255))
        row2.addWidget(self._upper_swatch)
        pick_upper = QPushButton("取色")
        pick_upper.setFixedWidth(40)
        pick_upper.clicked.connect(lambda _=False: self.color_pick_requested.emit("upper"))
        row2.addWidget(pick_upper)
        self.add_layout(row2)

        # 文件名
        row3 = QHBoxLayout()
        row3.addWidget(QLabel("文件名:"))
        self._filename = QLineEdit("inrange.png")
        row3.addWidget(self._filename)
        self.add_layout(row3)

        # 执行
        exec_btn = QPushButton("执行 inRange")
        exec_btn.clicked.connect(self._on_execute)
        self.add_widget(exec_btn)

        self._pick_target: str | None = None

    def set_picked_color(self, b: int, g: int, r: int):
        """从取色器设置颜色值"""
        if self._pick_target == "lower":
            self._lower_b.setText(str(b))
            self._lower_g.setText(str(g))
            self._lower_r.setText(str(r))
            self._lower_swatch.set_color(QColor(r, g, b))
        elif self._pick_target == "upper":
            self._upper_b.setText(str(b))
            self._upper_g.setText(str(g))
            self._upper_r.setText(str(r))
            self._upper_swatch.set_color(QColor(r, g, b))

    def set_pick_target(self, target: str):
        self._pick_target = target

    def _on_execute(self):
        try:
            lb = int(self._lower_b.text() or 0)
            lg = int(self._lower_g.text() or 0)
            lr = int(self._lower_r.text() or 0)
            ub = int(self._upper_b.text() or 255)
            ug = int(self._upper_g.text() or 255)
            ur = int(self._upper_r.text() or 255)
        except ValueError:
            return
        self.inrange_execute.emit(
            lb, lg, lr, ub, ug, ur,
            self._filename.text() or "inrange.png",
        )
