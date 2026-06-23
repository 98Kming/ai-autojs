"""图片查看器，对应 ImagePanel 的 viewer 部分

基于 QGraphicsView，支持：
- 滚轮缩放（以鼠标位置为中心，0.2x ~ 10x）
- 拖拽平移
- 双击重置
- 放大镜叠加
- 裁剪框选
"""

from __future__ import annotations

import base64
from PySide6.QtCore import Qt, Signal, QPointF, QRectF
from PySide6.QtGui import (
    QPixmap, QPainter, QPen, QColor, QWheelEvent, QMouseEvent,
    QKeyEvent, QBrush, QCursor,
)
from PySide6.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsPixmapItem

from app.protocol.messages import ImageEntry
from app.widgets.styles import COLORS


class ImageViewer(QGraphicsView):
    """图片查看器：缩放、平移、叠加层"""

    # 信号
    mouse_moved_image = Signal(QPointF)  # 鼠标在图片坐标系中的位置
    mouse_left_image = Signal()  # 鼠标离开图片区域
    zoom_changed = Signal(float)  # 当前缩放比例
    region_selected = Signal(int, int, int, int)  # (x, y, w, h) 裁剪区域
    pixel_picked = Signal(int, int)  # 取色模式下点击图片 (x, y)

    MIN_ZOOM = 0.2
    MAX_ZOOM = 10.0
    ZOOM_STEP = 1.15  # 每级缩放因子

    def __init__(self, parent=None):
        super().__init__(parent)
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)

        # 图片项
        self._pixmap_item: QGraphicsPixmapItem | None = None
        self._current_pixmap: QPixmap | None = None
        self._current_image: ImageEntry | None = None

        # 裁剪矩形
        self._crop_rect_item = None  # QGraphicsRectItem

        # 缩放状态
        self._zoom_level = 1.0

        # 平移状态
        self._panning = False
        self._pan_start = QPointF()

        # 取色模式
        self._pick_mode = False

        # 方向键虚拟光标（亚像素累积）
        self._virtual_cursor: QPointF | None = None
        self._sync_virtual_from_mouse = True  # setPos 后短暂关闭，防止覆写

        # 鼠标离开图片区域标记
        self._mouse_outside_image = False

        # 样式
        self.setStyleSheet(f"background: #1a1a2e; border: none;")
        self.setRenderHints(
            QPainter.Antialiasing | QPainter.SmoothPixmapTransform
        )
        self.setDragMode(QGraphicsView.NoDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        self.setViewportUpdateMode(QGraphicsView.SmartViewportUpdate)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        # 键盘聚焦（方向键漫游）
        self.setFocusPolicy(Qt.StrongFocus)

        # 跟踪鼠标
        self.setMouseTracking(True)

    # ============ 公共方法 ============

    def load_image(self, entry: ImageEntry):
        """加载图片"""
        self._current_image = entry
        pixmap = self._load_pixmap(entry)
        if pixmap.isNull():
            return

        self._current_pixmap = pixmap
        self._scene.clear()
        self._pixmap_item = QGraphicsPixmapItem(pixmap)
        self._scene.addItem(self._pixmap_item)
        self._scene.setSceneRect(QRectF(pixmap.rect()))

        # 重置裁剪矩形
        self._crop_rect_item = None

        # 适配视图
        self.fitInView(self._scene.sceneRect(), Qt.KeepAspectRatio)
        self._zoom_level = self.transform().m11()  # 水平缩放因子
        self.zoom_changed.emit(self._zoom_level)

        # 自动聚焦，无需先点击图片即可响应方向键
        self.setFocus()

    def get_image_at_cursor(self) -> QPointF | None:
        """获取鼠标处的图片坐标"""
        if self._pixmap_item is None:
            return None
        pos = self.mapToScene(self.mapFromGlobal(self.cursor().pos()))
        return pos

    def get_current_pixmap(self) -> QPixmap | None:
        return self._current_pixmap

    def get_current_image(self) -> ImageEntry | None:
        return self._current_image

    def set_pick_mode(self, enabled: bool):
        """设置取色模式开关"""
        self._pick_mode = enabled
        if enabled:
            self.setCursor(Qt.CrossCursor)
        else:
            self.setCursor(Qt.ArrowCursor)

    def is_pick_mode(self) -> bool:
        return self._pick_mode

    def enterEvent(self, event):
        """鼠标进入图片区域自动聚焦，无需点击即可响应方向键"""
        self.setFocus()
        super().enterEvent(event)

    def leaveEvent(self, event):
        """鼠标离开整个查看器区域"""
        self._mouse_outside_image = True
        self.mouse_left_image.emit()
        super().leaveEvent(event)

    def _is_in_image(self, image_pos: QPointF) -> bool:
        """检查坐标是否在图片像素范围内"""
        if self._current_pixmap is None:
            return False
        r = self._current_pixmap.rect()
        return 0 <= image_pos.x() < r.width() and 0 <= image_pos.y() < r.height()

    def reset_zoom(self):
        """重置缩放以适配视图"""
        if self._pixmap_item:
            self.fitInView(self._scene.sceneRect(), Qt.KeepAspectRatio)
            self._zoom_level = self.transform().m11()
            self.zoom_changed.emit(self._zoom_level)

    # ============ 事件处理 ============

    def wheelEvent(self, event: QWheelEvent):
        """滚轮缩放"""
        if self._pixmap_item is None:
            return

        delta = event.angleDelta().y()
        if delta > 0:
            factor = self.ZOOM_STEP
        else:
            factor = 1.0 / self.ZOOM_STEP

        new_zoom = self._zoom_level * factor
        if new_zoom < self.MIN_ZOOM or new_zoom > self.MAX_ZOOM:
            return

        self._zoom_level = new_zoom
        self.scale(factor, factor)
        self.zoom_changed.emit(self._zoom_level)

    def _is_ctrl_pressed(self) -> bool:
        """实时检测 Ctrl 键状态（不依赖 keyPress/keyRelease 追踪，避免焦点丢失问题）"""
        from PySide6.QtWidgets import QApplication
        return bool(QApplication.keyboardModifiers() & Qt.ControlModifier)

    def mousePressEvent(self, event: QMouseEvent):
        """鼠标按下"""
        if event.button() == Qt.LeftButton:
            # 取色模式优先：点击取色，可多次点击覆盖前一次结果
            if self._pick_mode:
                scene_pos = self.mapToScene(event.pos())
                x, y = int(scene_pos.x()), int(scene_pos.y())
                self.pixel_picked.emit(x, y)
                event.accept()
                return

            if self._is_ctrl_pressed():
                # Ctrl+拖拽：开始裁剪框选
                self._start_crop(event.position())
            else:
                # 普通拖拽：平移
                self._panning = True
                self._pan_start = event.position()
                self.setCursor(Qt.ClosedHandCursor)
        elif event.button() == Qt.MiddleButton:
            self._panning = True
            self._pan_start = event.position()
            self.setCursor(Qt.ClosedHandCursor)

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        """鼠标移动"""
        if self._panning:
            delta = event.position() - self._pan_start
            self._pan_start = event.position()
            self.horizontalScrollBar().setValue(
                self.horizontalScrollBar().value() - int(delta.x())
            )
            self.verticalScrollBar().setValue(
                self.verticalScrollBar().value() - int(delta.y())
            )
        elif self._is_ctrl_pressed() and self._crop_rect_item:
            # 更新裁剪矩形
            self._update_crop(event.position())

        # 发射鼠标在图片像素坐标系中的位置
        scene_pos = self.mapToScene(event.pos())
        image_pos = self._image_coord(scene_pos)

        # 鼠标在图片外（暗色背景）时隐藏放大镜
        if not self._is_in_image(image_pos):
            if not self._mouse_outside_image:
                self._mouse_outside_image = True
                self.mouse_left_image.emit()
            self._sync_virtual_from_mouse = True
            super().mouseMoveEvent(event)
            return

        self._mouse_outside_image = False
        if self._sync_virtual_from_mouse:
            self._virtual_cursor = image_pos
            self.mouse_moved_image.emit(image_pos)
        self._sync_virtual_from_mouse = True

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        """鼠标释放"""
        if event.button() in (Qt.LeftButton, Qt.MiddleButton):
            if self._is_ctrl_pressed() and self._crop_rect_item:
                self._finish_crop()
            self._panning = False
            if not self._pick_mode:
                self.setCursor(Qt.ArrowCursor)

        super().mouseReleaseEvent(event)

    def _image_coord(self, scene_pos: QPointF) -> QPointF:
        """scene 坐标 → 图片像素坐标（pixmap_item 移位后两者有偏移）"""
        if self._pixmap_item:
            p = self._pixmap_item.pos()
            return QPointF(scene_pos.x() - p.x(), scene_pos.y() - p.y())
        return scene_pos

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        """双击重置缩放"""
        self.reset_zoom()

    def keyPressEvent(self, event: QKeyEvent):
        """方向键移动鼠标 1 图片像素（亚像素累积，任意缩放比精确）"""
        if self._pixmap_item is None:
            super().keyPressEvent(event)
            return

        key = event.key()
        dx, dy = 0.0, 0.0
        if key == Qt.Key_Left:
            dx = -1.0
        elif key == Qt.Key_Right:
            dx = 1.0
        elif key == Qt.Key_Up:
            dy = -1.0
        elif key == Qt.Key_Down:
            dy = 1.0
        else:
            super().keyPressEvent(event)
            return

        # 初始化虚拟光标（首次或缩放重置后）
        if self._virtual_cursor is None:
            pos = self.get_image_at_cursor()
            if pos is None:
                return
            self._virtual_cursor = pos

        # 移动 1 图片像素
        self._virtual_cursor += QPointF(dx, dy)
        
        # 夹紧至图片边界
        r = self._current_pixmap.rect()
        self._virtual_cursor.setX(max(0.0, min(self._virtual_cursor.x(), r.width() - 1)))
        self._virtual_cursor.setY(max(0.0, min(self._virtual_cursor.y(), r.height() - 1)))

        # 先发送精确位置给放大镜
        self.mouse_moved_image.emit(self._virtual_cursor)

        # 移动 OS 光标；关闭鼠标事件对虚拟光标的覆写（setPos 会触发 mouseMoveEvent）
        self._sync_virtual_from_mouse = False
        scene_pos = self._virtual_cursor + self._pixmap_item.pos()
        view_pos = self.mapFromScene(scene_pos)
        global_pos = self.mapToGlobal(view_pos)
        QCursor.setPos(global_pos)

        event.accept()

    # ============ 裁剪 ============

    def _start_crop(self, start_pos: QPointF):
        """开始裁剪框选"""
        from PySide6.QtWidgets import QGraphicsRectItem
        from PySide6.QtCore import QPoint
        # 先清除上次的框选
        self.clear_crop()
        scene_pos = self.mapToScene(QPoint(int(start_pos.x()), int(start_pos.y())))
        self._crop_start = scene_pos

        pen = QPen(QColor(COLORS["primary"]), 1, Qt.DashLine)
        brush = QBrush(QColor(64, 158, 255, 40))
        self._crop_rect_item = QGraphicsRectItem(QRectF(scene_pos, scene_pos))
        self._crop_rect_item.setPen(pen)
        self._crop_rect_item.setBrush(brush)
        self._scene.addItem(self._crop_rect_item)

    def _update_crop(self, current_pos: QPointF):
        """更新裁剪矩形"""
        if self._crop_rect_item is None:
            return
        from PySide6.QtCore import QPoint
        scene_pos = self.mapToScene(QPoint(int(current_pos.x()), int(current_pos.y())))
        rect = QRectF(self._crop_start, scene_pos).normalized()
        self._crop_rect_item.setRect(rect)

    def _finish_crop(self):
        """完成裁剪框选"""
        if self._crop_rect_item is None:
            return
        rect = self._crop_rect_item.rect().toRect()
        if rect.width() > 5 and rect.height() > 5:
            self.region_selected.emit(
                rect.x(), rect.y(), rect.width(), rect.height()
            )
        # 保留矩形以供显示，在 load_image 时清除

    def get_crop_rect(self) -> QRectF | None:
        """获取当前裁剪矩形"""
        if self._crop_rect_item:
            return self._crop_rect_item.rect()
        return None

    def clear_crop(self):
        """清除裁剪矩形"""
        if self._crop_rect_item:
            self._scene.removeItem(self._crop_rect_item)
            self._crop_rect_item = None

    # ============ 内部 ============

    def _load_pixmap(self, entry: ImageEntry) -> QPixmap:
        """从 ImageEntry 加载 QPixmap"""
        pixmap = QPixmap()
        if entry.data:
            try:
                raw = base64.b64decode(entry.data)
                pixmap.loadFromData(raw)
            except Exception:
                pass
        if pixmap.isNull() and entry.file:
            from app.persistence.config_store import get_image_path
            filepath = get_image_path(entry.file)
            pixmap.load(filepath)
        return pixmap
