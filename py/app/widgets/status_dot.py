"""连接状态指示灯，对应 ConnectionBadge.vue

自绘圆形指示灯，connected/connecting 时带脉冲动画
"""

from __future__ import annotations

from PySide6.QtCore import Qt, QTimer, Property, QEasingCurve, QPropertyAnimation
from PySide6.QtGui import QPainter, QColor, QBrush, QPen
from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel

from app.widgets.styles import COLORS


class StatusDot(QWidget):
    """连接状态指示灯（圆形 + 脉冲动画）"""

    SIZE = 10  # 圆点直径

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setFixedSize(90, 24)  # 宽 90px 高 24px，水平排列圆点+文字
        self._status = "disconnected"
        self._opacity = 1.0

        # 脉冲动画
        self._anim = QPropertyAnimation(self, b"opacity")
        self._anim.setDuration(2000)
        self._anim.setStartValue(1.0)
        self._anim.setEndValue(0.4)
        self._anim.setEasingCurve(QEasingCurve.InOutSine)
        self._anim.setLoopCount(-1)  # 无限循环

    # opacity 属性供动画使用
    def get_opacity(self) -> float:
        return self._opacity

    def set_opacity(self, val: float):
        self._opacity = val
        self.update()

    opacity = Property(float, get_opacity, set_opacity)

    def set_status(self, status: str):
        """设置连接状态：disconnected / connecting / connected / error"""
        if self._status == status:
            return
        self._status = status
        if status in ("connected", "connecting"):
            self._anim.start()
        else:
            self._anim.stop()
            self._opacity = 1.0
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        # 颜色映射
        color_map = {
            "connected": QColor(COLORS["success"]),
            "connecting": QColor(COLORS["warning"]),
            "disconnected": QColor(COLORS["info"]),
            "error": QColor(COLORS["danger"]),
        }
        color = color_map.get(self._status, QColor(COLORS["info"]))

        # 文本映射
        text_map = {
            "connected": "已连接",
            "connecting": "连接中...",
            "disconnected": "未连接",
            "error": "连接失败",
        }
        text = text_map.get(self._status, "未知")

        # 绘制圆形（左侧居中）
        r = self.SIZE / 2
        cy = self.height() / 2
        cx = r + 4

        alpha = int(self._opacity * 255)
        color.setAlpha(alpha)
        p.setBrush(QBrush(color))
        p.setPen(Qt.NoPen)
        p.drawEllipse(int(cx - r), int(cy - r), self.SIZE, self.SIZE)

        # 绘制状态文字（圆点右侧，垂直居中）
        p.setPen(QPen(QColor(COLORS["text_secondary"])))
        text_x = self.SIZE + 10
        p.drawText(text_x, 0, self.width() - text_x, self.height(), Qt.AlignVCenter | Qt.AlignLeft, text)
        p.end()
