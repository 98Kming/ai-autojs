"""缩略图列表面板，对应 ImagePanel 的 image-list 部分"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QScrollArea, QPushButton, QMessageBox,
    QSizePolicy,
)

from app.protocol.messages import ImageEntry
from app.widgets.image_thumbnail import ImageThumbnail
from app.widgets.styles import COLORS


class ImageListPanel(QWidget):
    """缩略图列表（240px 宽）"""

    image_selected = Signal(str)  # image_id
    delete_image = Signal(str)  # image_id
    clear_all = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setMinimumWidth(100)
        self.setMaximumWidth(260)
        self._thumbnails: dict[str, ImageThumbnail] = {}
        self._selected_id: str | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self._container = QWidget()
        self._grid = QVBoxLayout(self._container)
        self._grid.setContentsMargins(8, 8, 8, 8)
        self._grid.setSpacing(6)
        self._grid.setAlignment(Qt.AlignTop)

        # 水平流式布局（用多个 HBoxLayout 模拟）
        self._row_layouts: list = []

        scroll.setWidget(self._container)
        layout.addWidget(scroll)

        # 清空按钮
        clear_btn = QPushButton("清空全部")
        clear_btn.setStyleSheet(f"""
            QPushButton {{
                border: none;
                border-top: 1px solid {COLORS['border']};
                border-radius: 0;
                padding: 8px;
                color: {COLORS['danger']};
                background: {COLORS['bg_primary']};
            }}
            QPushButton:hover {{
                background: {COLORS['bg_secondary']};
            }}
        """)
        clear_btn.clicked.connect(self._on_clear_all)
        layout.addWidget(clear_btn)

    def refresh(self, images: list[ImageEntry]):
        """刷新列表"""
        # 清除旧缩略图
        for thumb in self._thumbnails.values():
            self._grid.removeWidget(thumb)
            thumb.deleteLater()
        self._thumbnails.clear()
        self._row_layouts.clear()
        self._selected_id = None

        # 创建新缩略图（流式排列，每行约 3 个）
        row = QWidget()
        row_layout = None
        col = 0

        for img in images:
            if col == 0:
                row = QWidget()
                row_layout = None  # will use layout set below
                row.setLayout(None)

            thumb = ImageThumbnail(img)
            thumb.image_selected.connect(self._on_select)
            thumb.delete_requested.connect(self.delete_image.emit)
            self._thumbnails[img.id] = thumb

            # 简单的流式布局：用嵌套 widget
            if col == 0:
                row_layout = QVBoxLayout(row) if False else None  # placeholder

            col += 1
            if col >= 3:
                col = 0

        # 简化：直接逐个添加（垂直排列），不做流式
        for img in images:
            thumb = ImageThumbnail(img)
            thumb.image_selected.connect(self._on_select)
            thumb.delete_requested.connect(self.delete_image.emit)
            self._thumbnails[img.id] = thumb
            self._grid.addWidget(thumb, alignment=Qt.AlignCenter)

        # 自动选中第一张
        if images and self._thumbnails:
            first_id = images[0].id
            self._on_select(first_id)

    def select(self, image_id: str):
        self._on_select(image_id)

    def _on_select(self, image_id: str):
        """选中某张缩略图"""
        if self._selected_id == image_id:
            return
        # 取消旧选中
        if self._selected_id and self._selected_id in self._thumbnails:
            self._thumbnails[self._selected_id].selected = False
        self._selected_id = image_id
        if image_id in self._thumbnails:
            self._thumbnails[image_id].selected = True
        self.image_selected.emit(image_id)

    def _on_clear_all(self):
        reply = QMessageBox.question(
            self, "确认清空", "确定要清空所有图片吗？",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self.clear_all.emit()
