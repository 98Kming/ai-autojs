"""图片查看器，对应 ImagePanel 的 viewer 部分

基于 QGraphicsView，支持：
- 滚轮缩放（以鼠标位置为中心，0.2x ~ 10x）
- 拖拽平移
- 双击重置
- 放大镜叠加
- 裁剪框选

架构：view transform 恒为 identity，缩放和平移全部通过 pixmap_item 的
setPos（平移）和 setScale（缩放）实现，彻底避开 QGraphicsView 内部
viewportTransform 与 transform() 不同步的问题。
"""

from __future__ import annotations

import base64
from PySide6.QtCore import Qt, Signal, QPointF, QRectF
from PySide6.QtGui import (
    QPixmap, QPainter, QPen, QColor, QWheelEvent, QMouseEvent,
    QKeyEvent, QBrush, QCursor, QResizeEvent,
)
from PySide6.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsPixmapItem, QFrame

from app.protocol.messages import ImageEntry
from app.widgets.styles import COLORS


class ImageViewer(QGraphicsView):
    """图片查看器：缩放、平移、叠加层"""

    # 信号
    mouse_moved_image = Signal(QPointF)  # 鼠标在场景坐标系中的位置（用于 lens 定位）
    mouse_left_image = Signal()  # 鼠标离开图片区域
    zoom_changed = Signal(float)  # 当前缩放比例
    viewport_resized = Signal(int, int)  # 视窗宽、高
    region_selected = Signal(int, int, int, int)  # (x, y, w, h) 裁剪区域
    pixel_picked = Signal(int, int)  # 取色模式下点击图片 (x, y)

    MIN_ZOOM = 0.2
    MAX_ZOOM = 10.0
    ZOOM_STEP = 1.15

    def __init__(self, parent=None):
        super().__init__(parent)
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)

        self._pixmap_item: QGraphicsPixmapItem | None = None
        self._current_pixmap: QPixmap | None = None
        self._current_image: ImageEntry | None = None
        self._crop_rect_item = None
        self._crop_pixel_rect: QRectF | None = None  # 裁剪区域（图片像素坐标）

        # 缩放/平移状态
        self._zoom_level = 1.0
        # 居中偏移（fitInView 计算得出，视窗 resize 时重算）
        self._center_offset = QPointF(0, 0)
        # 用户拖拽偏移（resize 时保留）
        self._pan_offset = QPointF(0, 0)

        self._panning = False
        self._pan_start = QPointF()

        self._pick_mode = False

        self._virtual_cursor: QPointF | None = None
        self._sync_virtual_from_mouse = True
        self._mouse_outside_image = False

        # view transform 恒为 identity
        self.setStyleSheet(f"background: #1a1a2e; border: none;")
        self.setRenderHints(
            QPainter.Antialiasing | QPainter.SmoothPixmapTransform
        )
        self.setDragMode(QGraphicsView.NoDrag)
        self.setTransformationAnchor(QGraphicsView.NoAnchor)
        self.setResizeAnchor(QGraphicsView.NoAnchor)
        self.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)
        self.setFrameShape(QFrame.NoFrame)
        self.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setMouseTracking(True)

    # ============ item 变换辅助 ============

    def _item_set_transform(self):
        self._pixmap_item.setScale(self._zoom_level)

    def _sync_item_pos(self):
        """用 _center_offset + _pan_offset 更新 pixmap_item 位置"""
        self._pixmap_item.setPos(self._center_offset + self._pan_offset)

    def _recenter(self):
        """根据当前视窗大小重算居中偏移，保留用户拖拽偏移"""
        if self._pixmap_item is None or self._current_pixmap is None:
            return
        vp = self.viewport()
        dw = self._current_pixmap.width() * self._zoom_level
        dh = self._current_pixmap.height() * self._zoom_level
        self._center_offset = QPointF(
            (vp.width() - dw) / 2,
            (vp.height() - dh) / 2,
        )
        self._sync_item_pos()
        self._sync_crop_rect()

    def _scene_to_pixel(self, scene_pos: QPointF) -> QPointF:
        """场景坐标 → 图片像素坐标"""
        if self._pixmap_item is None:
            return scene_pos
        p = self._pixmap_item.pos()
        return QPointF(
            (scene_pos.x() - p.x()) / self._zoom_level,
            (scene_pos.y() - p.y()) / self._zoom_level,
        )

    def _pixel_to_scene(self, pixel: QPointF) -> QPointF:
        """图片像素坐标 → 场景坐标"""
        if self._pixmap_item is None:
            return pixel
        p = self._pixmap_item.pos()
        return QPointF(
            p.x() + self._zoom_level * pixel.x(),
            p.y() + self._zoom_level * pixel.y(),
        )

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

        self._crop_rect_item = None
        self._crop_pixel_rect = None

        # fitInView 计算合适缩放，提取居中偏移，然后 view 重置为 identity
        self.fitInView(self._scene.sceneRect(), Qt.KeepAspectRatio)
        self._zoom_level = self.transform().m11()
        self.resetTransform()
        # 限制初始缩放不超过 [MIN_ZOOM, MAX_ZOOM]，防止小图自动放太大导致无法缩放
        self._zoom_level = max(self.MIN_ZOOM, min(self.MAX_ZOOM, self._zoom_level))
        self._pan_offset = QPointF(0, 0)
        self._recenter()
        self._item_set_transform()
        self.zoom_changed.emit(self._zoom_level)
        self.setFocus()

    def get_image_at_cursor(self) -> QPointF | None:
        """获取鼠标处的图片像素坐标"""
        if self._pixmap_item is None:
            return None
        scene_pos = self.mapToScene(self.mapFromGlobal(self.cursor().pos()))
        return self._scene_to_pixel(scene_pos)

    def get_current_pixmap(self) -> QPixmap | None:
        return self._current_pixmap

    def get_current_image(self) -> ImageEntry | None:
        return self._current_image

    def scene_to_image(self, scene_pos: QPointF) -> QPointF:
        """场景坐标 → 图片像素坐标（公开接口）"""
        return self._scene_to_pixel(scene_pos)

    def set_pick_mode(self, enabled: bool):
        self._pick_mode = enabled
        self.setCursor(Qt.CrossCursor if enabled else Qt.ArrowCursor)

    def is_pick_mode(self) -> bool:
        return self._pick_mode

    def enterEvent(self, event):
        self.setFocus()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._mouse_outside_image = True
        self.mouse_left_image.emit()
        super().leaveEvent(event)

    def _is_in_image(self, pixel_pos: QPointF) -> bool:
        if self._current_pixmap is None:
            return False
        r = self._current_pixmap.rect()
        return 0 <= pixel_pos.x() < r.width() and 0 <= pixel_pos.y() < r.height()

    def reset_zoom(self):
        """重置缩放平移以适配视图"""
        if self._pixmap_item:
            self.clear_crop()
            self.fitInView(self._scene.sceneRect(), Qt.KeepAspectRatio)
            self._zoom_level = self.transform().m11()
            self.resetTransform()
            self._zoom_level = max(self.MIN_ZOOM, min(self.MAX_ZOOM, self._zoom_level))
            self._pan_offset = QPointF(0, 0)
            self._recenter()
            self._item_set_transform()
            self.zoom_changed.emit(self._zoom_level)

    def resizeEvent(self, event: QResizeEvent):
        super().resizeEvent(event)
        self._recenter()
        vp = self.viewport()
        self.viewport_resized.emit(vp.width(), vp.height())

    # ============ 事件处理 ============

    def wheelEvent(self, event: QWheelEvent):
        """滚轮缩放（以鼠标位置为中心）"""
        if self._pixmap_item is None:
            return

        factor = self.ZOOM_STEP if event.angleDelta().y() > 0 else 1.0 / self.ZOOM_STEP
        new_zoom = self._zoom_level * factor
        if new_zoom < self.MIN_ZOOM or new_zoom > self.MAX_ZOOM:
            return

        # 记录缩放前鼠标处的图片像素
        old_pixel = self._scene_to_pixel(
            self.mapToScene(int(event.position().x()), int(event.position().y()))
        )

        self._zoom_level = new_zoom
        self._item_set_transform()
        self._recenter()

        # 调整拖拽偏移使缩放中心像素仍位于鼠标下方
        target_scene = self._pixel_to_scene(old_pixel)
        current_scene = self.mapToScene(int(event.position().x()), int(event.position().y()))
        self._pan_offset += current_scene - target_scene
        self._sync_item_pos()
        self._sync_crop_rect()
        self.zoom_changed.emit(self._zoom_level)

    def _is_ctrl_pressed(self) -> bool:
        from PySide6.QtWidgets import QApplication
        return bool(QApplication.keyboardModifiers() & Qt.ControlModifier)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            if self._pick_mode:
                scene_pos = self.mapToScene(event.pos())
                x, y = int(scene_pos.x()), int(scene_pos.y())
                self.pixel_picked.emit(x, y)
                event.accept()
                return

            if self._is_ctrl_pressed():
                self._start_crop(event.position())
            else:
                self._panning = True
                self._pan_start = event.position()
                self.setCursor(Qt.ClosedHandCursor)
        elif event.button() == Qt.MiddleButton:
            self._panning = True
            self._pan_start = event.position()
            self.setCursor(Qt.ClosedHandCursor)

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        if self._panning:
            delta = event.position() - self._pan_start
            self._pan_start = event.position()
            self._pan_offset += delta
            self._sync_item_pos()
            self._sync_crop_rect()
        elif self._is_ctrl_pressed() and self._crop_rect_item:
            self._update_crop(event.position())

        scene_pos = self.mapToScene(event.pos())
        pixel_pos = self._scene_to_pixel(scene_pos)

        if not self._is_in_image(pixel_pos):
            if not self._mouse_outside_image:
                self._mouse_outside_image = True
                self.mouse_left_image.emit()
            self._sync_virtual_from_mouse = True
            super().mouseMoveEvent(event)
            return

        self._mouse_outside_image = False
        if self._sync_virtual_from_mouse:
            self._virtual_cursor = pixel_pos
            self.mouse_moved_image.emit(scene_pos)
        self._sync_virtual_from_mouse = True

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() in (Qt.LeftButton, Qt.MiddleButton):
            if self._is_ctrl_pressed() and self._crop_rect_item:
                self._finish_crop()
            self._panning = False
            if not self._pick_mode:
                self.setCursor(Qt.ArrowCursor)
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        self.reset_zoom()

    def keyPressEvent(self, event: QKeyEvent):
        """方向键移动鼠标 1 图片像素"""
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

        if self._virtual_cursor is None:
            pos = self.get_image_at_cursor()
            if pos is None:
                return
            self._virtual_cursor = pos

        self._virtual_cursor += QPointF(dx, dy)
        r = self._current_pixmap.rect()
        self._virtual_cursor.setX(max(0.0, min(self._virtual_cursor.x(), r.width() - 1)))
        self._virtual_cursor.setY(max(0.0, min(self._virtual_cursor.y(), r.height() - 1)))

        self.mouse_moved_image.emit(
            self._pixel_to_scene(self._virtual_cursor)
        )

        self._sync_virtual_from_mouse = False
        scene_pos = self._pixel_to_scene(self._virtual_cursor)
        view_pos = self.mapFromScene(scene_pos)
        global_pos = self.mapToGlobal(view_pos)
        QCursor.setPos(global_pos)
        event.accept()

    def _sync_crop_rect(self):
        """从 _crop_pixel_rect 更新场景中裁剪框的位置（缩放/重居中后调用）"""
        if self._crop_pixel_rect is not None and self._crop_rect_item is not None:
            tl = self._pixel_to_scene(self._crop_pixel_rect.topLeft())
            br = self._pixel_to_scene(self._crop_pixel_rect.bottomRight())
            self._crop_rect_item.setRect(QRectF(tl, br))

    # ============ 裁剪 ============

    def _start_crop(self, start_pos: QPointF):
        from PySide6.QtWidgets import QGraphicsRectItem
        from PySide6.QtCore import QPoint
        self.clear_crop()
        scene_pos = self.mapToScene(QPoint(int(start_pos.x()), int(start_pos.y())))
        self._crop_start_pixel = self._scene_to_pixel(scene_pos)
        pen = QPen(QColor(COLORS["primary"]), 1, Qt.DashLine)
        brush = QBrush(QColor(64, 158, 255, 40))
        self._crop_rect_item = QGraphicsRectItem(QRectF(scene_pos, scene_pos))
        self._crop_rect_item.setPen(pen)
        self._crop_rect_item.setBrush(brush)
        self._scene.addItem(self._crop_rect_item)

    def _update_crop(self, current_pos: QPointF):
        if self._crop_rect_item is None:
            return
        from PySide6.QtCore import QPoint
        scene_pos = self.mapToScene(QPoint(int(current_pos.x()), int(current_pos.y())))
        # 起始点用像素坐标实时转换，缩放后仍能对齐图片
        start_scene = self._pixel_to_scene(self._crop_start_pixel)
        rect = QRectF(start_scene, scene_pos).normalized()
        self._crop_rect_item.setRect(rect)
        # 保存图片像素坐标版本，用于缩放后重绘
        tl = self._scene_to_pixel(rect.topLeft())
        br = self._scene_to_pixel(rect.bottomRight())
        self._crop_pixel_rect = QRectF(tl, br)

    def _finish_crop(self):
        if self._crop_pixel_rect is None:
            return
        r = self._crop_pixel_rect.toRect()
        if r.width() > 5 and r.height() > 5:
            self.region_selected.emit(
                r.x(), r.y(), r.width(), r.height()
            )

    def get_crop_rect(self) -> QRectF | None:
        if self._crop_rect_item:
            return self._crop_rect_item.rect()
        return None

    def clear_crop(self):
        if self._crop_rect_item:
            self._scene.removeItem(self._crop_rect_item)
            self._crop_rect_item = None
        self._crop_pixel_rect = None

    # ============ 内部 ============

    def _load_pixmap(self, entry: ImageEntry) -> QPixmap:
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
