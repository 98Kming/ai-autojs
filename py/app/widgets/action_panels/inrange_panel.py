"""颜色范围二值化 (inRange) 面板 — 使用 #RRGGBB hex 输入，与 Vue 版一致"""

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
        self._update_style()

    def set_color(self, color: QColor):
        self._color = color
        self._update_style()

    def _update_style(self):
        self.setStyleSheet(
            f"background: {self._color.name()}; border: 1px solid #555; border-radius: 3px;"
        )


class InRangePanel(BasePanel):
    """颜色范围二值化面板 — hex 输入 + 取色两段式，与 Vue 版一致"""

    inrange_execute = Signal(str, str, str)  # lower_hex, upper_hex, filename
    color_pick_requested = Signal(str)  # "lower" / "upper" 进入取色，"" 取消取色

    def __init__(self, parent: QWidget | None = None):
        super().__init__("⬛ 二值化 (inRange)", parent)

        self.add_widget(QLabel("点击取色按钮后点击图片选取颜色"))

        # 下界（默认红色，与 Vue 版一致）
        row1 = QHBoxLayout()
        row1.addWidget(QLabel("下界"))
        self._lower_swatch = ColorSwatch(QColor(255, 0, 0))
        row1.addWidget(self._lower_swatch)
        self._lower_hex = QLineEdit("#FF0000")
        self._lower_hex.setFixedWidth(80)
        self._lower_hex.setPlaceholderText("#RRGGBB")
        row1.addWidget(self._lower_hex)
        self._pick_lower_btn = QPushButton("取色")
        self._pick_lower_btn.setFixedWidth(60)
        self._pick_lower_btn.setStyleSheet("padding: 2px 4px;")
        self._pick_lower_btn.clicked.connect(lambda _=False: self._on_pick_click("lower"))
        row1.addWidget(self._pick_lower_btn)
        self.add_layout(row1)

        # 上界（默认白色，与 Vue 版一致）
        row2 = QHBoxLayout()
        row2.addWidget(QLabel("上界"))
        self._upper_swatch = ColorSwatch(QColor(255, 255, 255))
        row2.addWidget(self._upper_swatch)
        self._upper_hex = QLineEdit("#FFFFFF")
        self._upper_hex.setFixedWidth(80)
        self._upper_hex.setPlaceholderText("#RRGGBB")
        row2.addWidget(self._upper_hex)
        self._pick_upper_btn = QPushButton("取色")
        self._pick_upper_btn.setFixedWidth(60)
        self._pick_upper_btn.setStyleSheet("padding: 2px 4px;")
        self._pick_upper_btn.clicked.connect(lambda _=False: self._on_pick_click("upper"))
        row2.addWidget(self._pick_upper_btn)
        self.add_layout(row2)

        # 文件名 + 执行
        row3 = QHBoxLayout()
        self._filename = QLineEdit("_inrange.png")
        row3.addWidget(self._filename)
        exec_btn = QPushButton("⬛ 执行")
        exec_btn.clicked.connect(self._on_execute)
        row3.addWidget(exec_btn)
        self.add_layout(row3)

        self._pick_target: str | None = None

    # ============ 取色模式 ============

    def _on_pick_click(self, target: str):
        """取色按钮点击：两段式切换（与 Vue 版一致）"""
        if self._pick_target == target:
            # 同一目标 → 取消取色
            self._pick_target = None
            self._update_pick_buttons()
            self.color_pick_requested.emit("")
        else:
            # 切换目标或新目标 → 进入取色
            self._pick_target = target
            self._update_pick_buttons()
            self.color_pick_requested.emit(target)

    def _update_pick_buttons(self):
        """刷新按钮文本：取色 / 取色中"""
        self._pick_lower_btn.setText("取色中" if self._pick_target == "lower" else "取色")
        self._pick_upper_btn.setText("取色中" if self._pick_target == "upper" else "取色")

    def cancel_pick(self):
        """取消取色模式（由外部在取色完成后调用）"""
        self._pick_target = None
        self._update_pick_buttons()

    # ============ 颜色设置 ============

    def set_picked_color(self, blue: int, green: int, red: int):
        """从取色器设置颜色值（QColor 分量 → RGB hex）"""
        hex_str = f"#{red:02X}{green:02X}{blue:02X}"
        qcolor = QColor(red, green, blue)
        if self._pick_target == "lower":
            self._lower_hex.setText(hex_str)
            self._lower_swatch.set_color(qcolor)
        elif self._pick_target == "upper":
            self._upper_hex.setText(hex_str)
            self._upper_swatch.set_color(qcolor)

    # ============ 执行 ============

    def _on_execute(self):
        lower_hex = self._lower_hex.text().strip()
        upper_hex = self._upper_hex.text().strip()
        filename = self._filename.text() or "_inrange.png"
        self.inrange_execute.emit(lower_hex, upper_hex, filename)
