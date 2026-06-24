"""图片列表 Model，对应 useImageStore

与 Vue 版的关键差异：
- 无 MAX_IMAGES 数量限制
- 无 MAX_STORAGE_BYTES 容量限制
- 图片存为实际文件（images/ 目录），元数据存为 images.json 索引
"""
from __future__ import annotations

import time
import secrets
import base64
from pathlib import Path

from PySide6.QtCore import QObject, Signal

from app.protocol.messages import ImageEntry
from app.persistence import config_store

class ImageModel(QObject):
    """图片列表管理，文件系统持久化"""

    images_changed = Signal()
    image_added = Signal(ImageEntry)

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        # 从 images.json 加载索引
        self._images: list[ImageEntry] = []
        self._load_from_disk()

    @property
    def images(self) -> list[ImageEntry]:
        return self._images

    @property
    def count(self) -> int:
        return len(self._images)

    def add_image(self, data: str, mime: str = "image/png", code: str = "", name: str = ""):
        """添加图片

        Args:
            data: Base64 编码的图片数据
            mime: MIME 类型
            code: 生成该图片的源代码
            name: 显示名称
        """
        entry_id = secrets.token_hex(12)
        timestamp = time.time()

        # 确定文件扩展名
        ext = _mime_to_ext(mime)

        # 将 Base64 解码并写入文件
        filename = f"{entry_id}{ext}"
        try:
            raw_bytes = base64.b64decode(data)
            config_store.save_image_file(filename, raw_bytes)
        except Exception as e:
            print(f"[ImageModel] 保存图片文件失败: {e}")
            return

        entry = ImageEntry(
            id=entry_id,
            data=data,  # 保留 Base64 在内存中供快速预览
            mime=mime,
            timestamp=timestamp,
            code=code,
            name=name,
            file=filename,
        )
        self._images.insert(0, entry)
        self._persist_index()
        self.image_added.emit(entry)
        self.images_changed.emit()

    def remove_image(self, image_id: str):
        """删除图片（同时删除文件）"""
        for img in self._images:
            if img.id == image_id:
                config_store.delete_image_file(img.file)
                break
        self._images = [img for img in self._images if img.id != image_id]
        self._persist_index()
        self.images_changed.emit()

    def clear_all(self):
        """清空所有图片"""
        for img in self._images:
            config_store.delete_image_file(img.file)
        self._images.clear()
        self._persist_index()
        self.images_changed.emit()

    def get_image_by_id(self, image_id: str) -> ImageEntry | None:
        for img in self._images:
            if img.id == image_id:
                return img
        return None

    def load_image_data(self, image_id: str) -> str | None:
        """懒加载图片 Base64 数据（从磁盘文件读取）

        Returns:
            Base64 字符串，如果文件不存在则返回 None
        """
        for img in self._images:
            if img.id == image_id:
                if img.data:
                    return img.data  # 已在内存中
                if img.file:
                    filepath = config_store.get_image_path(img.file)
                    try:
                        with open(filepath, "rb") as f:
                            img.data = base64.b64encode(f.read()).decode("ascii")
                        return img.data
                    except OSError:
                        return None
                return None
        return None

    def _load_from_disk(self):
        """启动时从 images.json 和图片文件恢复"""
        index = config_store.load_images_index()
        for item in index:
            try:
                filename = item.get("file", "")
                filepath = config_store.get_image_path(filename)
                if not Path(filepath).exists():
                    continue  # 文件丢失，跳过

                entry = ImageEntry(
                    id=item.get("id", ""),
                    data="",  # 延迟加载，需要时再从文件读取
                    mime=item.get("mime", "image/png"),
                    timestamp=item.get("timestamp", 0.0),
                    code=item.get("code", ""),
                    name=item.get("name", ""),
                    file=filename,
                )
                self._images.append(entry)
            except Exception as e:
                print(f"[ImageModel] 跳过损坏的图片索引: {e}")

    def _persist_index(self):
        """保存图片元数据索引"""
        data = []
        for img in self._images:
            data.append({
                "id": img.id,
                "mime": img.mime,
                "timestamp": img.timestamp,
                "code": img.code,
                "name": img.name,
                "file": img.file,
            })
        config_store.save_images_index(data)

def _mime_to_ext(mime: str) -> str:
    """MIME 类型 → 文件扩展名"""
    mapping = {
        "image/png": ".png",
        "image/jpeg": ".jpg",
        "image/jpg": ".jpg",
        "image/bmp": ".bmp",
        "image/gif": ".gif",
        "image/webp": ".webp",
    }
    return mapping.get(mime, ".png")
