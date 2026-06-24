"""缩略图卡片，对应 ImageCard.vue"""

import base64
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap, QFont
from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QSizePolicy,
)

from app.protocol.messages import ImageEntry
from app.widgets.styles import COLORS


class ImageThumbnail(QFrame):
    """72x72 缩略图卡片"""

    image_selected = Signal(str)  # image_id
    delete_requested = Signal(str)  # image_id

    def __init__(self, image: ImageEntry, parent=None):
        super().__init__(parent)
        self._image = image
        self._selected = False
        self.setup_ui()

    def setup_ui(self):
        self.setFixedSize(88, 120)
        self.setCursor(Qt.PointingHandCursor)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 4)
        layout.setSpacing(4)

        # 缩略图
        thumb = QLabel()
        thumb.setFixedSize(72, 72)
        thumb.setAlignment(Qt.AlignCenter)
        thumb.setStyleSheet(f"""
            QLabel {{
                background: {COLORS['bg_tertiary']};
                border: 1px solid {COLORS['border']};
                border-radius: 3px;
            }}
        """)

        # 加载图片
        pixmap = self._load_thumbnail()
        if not pixmap.isNull():
            scaled = pixmap.scaled(
                68, 68, Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            thumb.setPixmap(scaled)

        layout.addWidget(thumb, alignment=Qt.AlignCenter)

        # 文件名标签
        name = self._generate_name()
        name_label = QLabel(name)
        name_label.setAlignment(Qt.AlignCenter)
        name_label.setStyleSheet(f"""
            color: {COLORS['text_secondary']};
            font-size: 10px;
            border: none;
        """)
        name_label.setToolTip(name)
        layout.addWidget(name_label)

    def _load_thumbnail(self) -> QPixmap:
        """加载缩略图"""
        pixmap = QPixmap()
        if self._image.data:
            # 内存中有 Base64 数据
            try:
                raw = base64.b64decode(self._image.data)
                pixmap.loadFromData(raw)
            except Exception:
                pass
        elif self._image.file:
            # 从磁盘加载
            from app.persistence.config_store import get_image_path
            filepath = get_image_path(self._image.file)
            pixmap.load(filepath)
        return pixmap

    def _generate_name(self) -> str:
        """生成缩略图名称"""
        if self._image.name:
            return self._image.name
        if self._image.code:
            code = self._image.code.strip()
            if "截图" in code or "captureScreen" in code:
                return "截图"
            if "clip" in code or "裁剪" in code:
                return "裁剪"
            if "grayscale" in code.lower():
                return "灰度"
            if "threshold" in code.lower():
                return "阈值"
        # 用文件名
        name = self._image.file.rsplit(".", 1)[0] if self._image.file else self._image.id[:8]
        return name

    @property
    def image_id(self) -> str:
        return self._image.id

    @property
    def selected(self) -> bool:
        return self._selected

    @selected.setter
    def selected(self, val: bool):
        self._selected = val
        if val:
            self.setStyleSheet(f"""
                ImageThumbnail {{
                    border: 2px solid {COLORS['primary']};
                    border-radius: 6px;
                    background: {COLORS['bg_secondary']};
                }}
            """)
        else:
            self.setStyleSheet(f"""
                ImageThumbnail {{
                    border: 1px solid {COLORS['border']};
                    border-radius: 6px;
                    background: {COLORS['bg_primary']};
                }}
                ImageThumbnail:hover {{
                    border-color: {COLORS['primary']};
                    background: {COLORS['bg_secondary']};
                }}
            """)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.image_selected.emit(self._image.id)
        super().mousePressEvent(event)

    def contextMenuEvent(self, event):
        """右键菜单：下载/删除"""
        from PySide6.QtWidgets import QMenu, QApplication
        menu = QMenu(self)
        download_action = menu.addAction("💾 下载")
        delete_action = menu.addAction("🗑️ 删除")

        action = menu.exec(event.globalPos())
        if action == download_action:
            self._on_download()
        elif action == delete_action:
            self.delete_requested.emit(self._image.id)

    def _on_download(self):
        from PySide6.QtWidgets import QFileDialog
        pixmap = self._load_thumbnail()
        if pixmap.isNull():
            return
        filepath, _ = QFileDialog.getSaveFileName(
            self, "保存图片", f"{self._generate_name()}.png",
            "PNG (*.png);;JPEG (*.jpg);;所有文件 (*.*)"
        )
        if filepath:
            pixmap.save(filepath)
