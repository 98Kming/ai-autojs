"""裁剪框选覆盖层，对应 ImagePanel 的 crop-overlay

在 QGraphicsScene 上绘制蓝色虚线矩形 + 半透明填充
"""

from __future__ import annotations

from PySide6.QtCore import Qt, QRectF, Signal
from PySide6.QtGui import QPen, QColor, QBrush
from PySide6.QtWidgets import QGraphicsRectItem

from app.widgets.styles import COLORS


class CropOverlay(QGraphicsRectItem):
    """裁剪框选矩形"""

    region_changed = Signal(int, int, int, int)  # (x, y, w, h)

    def __init__(self, parent=None):
        super().__init__(parent)
        pen = QPen(QColor(COLORS["primary"]), 1.5, Qt.DashLine)
        brush = QBrush(QColor(64, 158, 255, 40))
        self.setPen(pen)
        self.setBrush(brush)
        self.setZValue(10)  # 确保在图片上方
        self.setFlag(QGraphicsRectItem.ItemIsMovable, True)
        self.setFlag(QGraphicsRectItem.ItemIsSelectable, True)
        self.hide()

    def set_region(self, x: int, y: int, w: int, h: int):
        """设置裁剪区域"""
        self.setRect(QRectF(x, y, w, h))
        self.show()

    def get_region(self) -> tuple:
        """获取裁剪区域 (x, y, w, h)"""
        r = self.rect().toRect()
        return (r.x(), r.y(), r.width(), r.height())

    def clear(self):
        """隐藏并重置"""
        self.hide()
        self.setRect(QRectF())
