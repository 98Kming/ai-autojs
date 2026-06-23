"""放大镜组件，对应 ImagePanel 的 magnifier 部分

10x 像素放大镜：
- 190×190px 正方形镜片（ZOOM × 奇数 = 10 × 19）
- 10x 放大，每个源像素映射到精确 10×10 显示像素块
- 像素网格虚线叠加（间距 10px = 原图 1px）
- 红色十字准星穿过中心像素正中心
- 底部坐标 + 颜色信息栏
"""

from __future__ import annotations

from PySide6.QtCore import Qt, QPoint, QRect
from PySide6.QtGui import (
    QPainter, QColor, QPen, QFont, QFontMetrics, QImage,
)
from PySide6.QtWidgets import QWidget

from app.widgets.styles import COLORS


class MagnifierLens(QWidget):
    """10x 像素放大镜叠加层"""

    SIZE = 190  # 镜片边长（Zoom × 奇数，保证中心像素精确居中）
    ZOOM = 10  # 放大倍数
    GRID_SPACING = 10  # 像素网格间距（对应原图 1px）

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setFixedSize(self.SIZE, self.SIZE + 24)  # 底部信息栏 24px
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.hide()

        self._source_pixmap: QImage | None = None
        self._pixel_x = 0
        self._pixel_y = 0
        self._pixel_color = QColor(0, 0, 0)

        self.setStyleSheet("background: transparent;")

    @property
    def pixel_color(self) -> QColor:
        """当前采样的像素颜色"""
        return self._pixel_color

    def set_source(self, image: QImage):
        """设置源图片"""
        self._source_pixmap = image

    def set_pixel(self, x: int, y: int):
        """设置当前像素坐标并采样颜色"""
        self._pixel_x = x
        self._pixel_y = y

        if self._source_pixmap and not self._source_pixmap.isNull():
            ix = max(0, min(x, self._source_pixmap.width() - 1))
            iy = max(0, min(y, self._source_pixmap.height() - 1))
            self._pixel_color = self._source_pixmap.pixelColor(ix, iy)

        self.update()

    def paintEvent(self, event):
        if self._source_pixmap is None or self._source_pixmap.isNull():
            return

        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, False)

        # 镜片区域
        lens_rect = QRect(0, 0, self.SIZE, self.SIZE)

        # 1. 绘制放大区域（ZOOM 倍放大，奇数个像素，中心像素精确居中）
        half_source = self.SIZE // (2 * self.ZOOM)  # 9 像素半径
        src_x = self._pixel_x - half_source
        src_y = self._pixel_y - half_source
        src_w = half_source * 2 + 1  # 19 像素
        src_h = half_source * 2 + 1  # 19 像素

        # 源矩形（在源图中）
        src_rect = QRect(src_x, src_y, src_w, src_h)
        # 目标矩形（在镜片中）
        dst_rect = lens_rect

        # 绘制放大后的像素
        p.drawImage(dst_rect, self._source_pixmap, src_rect)

        # 2. 绘制像素网格（步长 ZOOM = 10px，与像素边界精确对齐）
        grid_pen = QPen(QColor(128, 128, 128, 80))
        grid_pen.setWidth(1)
        p.setPen(grid_pen)

        for i in range(0, self.SIZE + 1, self.GRID_SPACING):
            p.drawLine(i, 0, i, self.SIZE)   # 竖线
            p.drawLine(0, i, self.SIZE, i)   # 横线

        # 3. 绘制红色十字准星
        cx = self.SIZE // 2
        cy = self.SIZE // 2
        cross_pen = QPen(QColor(255, 50, 50, 200))
        cross_pen.setWidth(2)
        p.setPen(cross_pen)
        p.drawLine(cx, 0, cx, self.SIZE)    # 竖线
        p.drawLine(0, cy, self.SIZE, cy)    # 横线

        # 4. 绘制镜片边框
        border_pen = QPen(QColor(255, 255, 255))
        border_pen.setWidth(3)
        p.setPen(border_pen)
        p.drawRect(lens_rect)

        # 5. 底部信息栏
        info_y = self.SIZE
        info_rect = QRect(0, info_y, self.SIZE, 24)
        p.fillRect(info_rect, QColor(0, 0, 0, 180))

        font = QFont("Consolas", 9)
        p.setFont(font)

        # 坐标
        coord_text = f"({self._pixel_x}, {self._pixel_y})"
        p.setPen(QPen(QColor(255, 255, 255)))
        p.drawText(4, info_y, 80, 24, Qt.AlignVCenter, coord_text)

        # 颜色色块
        color_rect = QRect(self.SIZE - 66, info_y + 4, 16, 16)
        p.fillRect(color_rect, self._pixel_color)
        p.setPen(QPen(QColor(255, 255, 255)))
        p.drawRect(color_rect)

        # 十六进制颜色值
        hex_color = self._pixel_color.name().upper()
        p.drawText(self.SIZE - 46, info_y, 42, 24, Qt.AlignVCenter, hex_color)

        p.end()
