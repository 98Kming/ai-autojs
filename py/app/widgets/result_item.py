"""单条结果组件，对应 ResultItem.vue

支持三种显示模式：文本结果、二进制 hex dump、图片预览
"""

from __future__ import annotations

import base64
from datetime import datetime

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QPlainTextEdit,
    QApplication, QFileDialog, QSizePolicy,
)

from app.protocol.messages import ResultEntry
from app.widgets.styles import COLORS


class ResultItem(QFrame):
    """单条执行结果卡片"""

    def __init__(self, entry: ResultEntry, parent: QWidget | None = None):
        super().__init__(parent)
        self._entry = entry
        self.setup_ui()

    def setup_ui(self):
        self.setStyleSheet(f"""
            ResultItem {{
                border: 1px solid {COLORS['border']};
                border-radius: 6px;
                background: {COLORS['bg_primary']};
                margin: 4px 0;
            }}
        """)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(8)

        # ====== 头部信息行 ======
        header = QHBoxLayout()

        # 状态标签
        status_label = QLabel("成功" if self._entry.status == "success" else "失败")
        status_color = COLORS["success"] if self._entry.status == "success" else COLORS["danger"]
        status_label.setStyleSheet(f"""
            QLabel {{
                color: white;
                background: {status_color};
                border-radius: 3px;
                padding: 2px 8px;
                font-size: 12px;
            }}
        """)
        status_label.setFixedHeight(22)
        header.addWidget(status_label)

        # 二进制标签
        if self._entry.data_type == "base64":
            bin_label = QLabel("二进制" if not self._is_image() else "图片")
            bin_label.setStyleSheet(f"""
                QLabel {{
                    color: {COLORS['primary']};
                    border: 1px solid {COLORS['primary']};
                    border-radius: 3px;
                    padding: 2px 8px;
                    font-size: 12px;
                }}
            """)
            bin_label.setFixedHeight(22)
            header.addWidget(bin_label)

        header.addStretch()

        # 时间戳
        ts = datetime.fromtimestamp(self._entry.timestamp).strftime("%H:%M:%S")
        ts_label = QLabel(ts)
        ts_label.setStyleSheet(f"color: {COLORS['text_placeholder']}; font-size: 12px; border: none;")
        header.addWidget(ts_label)

        # 执行耗时
        if self._entry.duration_ms is not None:
            dur = self._entry.duration_ms
            if dur < 1000:
                dur_text = f"{dur:.0f}ms"
            else:
                dur_text = f"{dur / 1000:.1f}s"
            dur_label = QLabel(dur_text)
            dur_label.setStyleSheet(f"""
                QLabel {{
                    color: {COLORS['text_secondary']};
                    background: {COLORS['bg_tertiary']};
                    border-radius: 3px;
                    padding: 2px 6px;
                    font-size: 12px;
                }}
            """)
            header.addWidget(dur_label)

        # 复制按钮
        copy_btn = QPushButton("📋 复制")
        copy_btn.setFixedHeight(24)
        copy_btn.setStyleSheet(f"font-size: 12px; padding: 2px 8px;")
        copy_btn.clicked.connect(self._on_copy)
        header.addWidget(copy_btn)

        # 下载按钮（二进制数据）
        if self._entry.data_type == "base64" and not self._is_image():
            download_btn = QPushButton("💾 下载")
            download_btn.setFixedHeight(24)
            download_btn.setStyleSheet(f"font-size: 12px; padding: 2px 8px;")
            download_btn.clicked.connect(self._on_download)
            header.addWidget(download_btn)

        layout.addLayout(header)

        # ====== 结果内容 ======
        if self._entry.data_type == "base64" and self._is_image():
            # 图片预览
            try:
                pixmap = QPixmap()
                raw = base64.b64decode(self._entry.data)
                pixmap.loadFromData(raw)
                if not pixmap.isNull():
                    img_label = QLabel()
                    scaled = pixmap.scaledToWidth(
                        400, Qt.SmoothTransformation
                    ) if pixmap.width() > 400 else pixmap
                    img_label.setPixmap(scaled)
                    img_label.setAlignment(Qt.AlignCenter)
                    img_label.setStyleSheet("border: none;")
                    layout.addWidget(img_label)
            except Exception:
                pass
        elif self._entry.data_type == "base64":
            # 二进制 hex dump
            hex_view = QPlainTextEdit()
            hex_view.setReadOnly(True)
            hex_view.setFont(self._mono_font())
            hex_view.setMaximumHeight(200)
            hex_view.setStyleSheet(f"background: {COLORS['bg_secondary']}; border: none;")
            hex_view.setPlainText(self._format_hex_dump())
            layout.addWidget(hex_view)
        else:
            # 纯文本结果
            text_view = QPlainTextEdit()
            text_view.setReadOnly(True)
            text_view.setFont(self._mono_font())
            text_view.setMaximumHeight(400)
            text_view.setStyleSheet(f"background: {COLORS['bg_secondary']}; border: none;")
            text = self._entry.data if self._entry.data else "(无输出)"
            text_view.setPlainText(text)
            layout.addWidget(text_view)

    # ============ 私有方法 ============

    def _is_image(self) -> bool:
        mime = (self._entry.mime or "").lower()
        return mime.startswith("image/")

    def _mono_font(self):
        from PySide6.QtGui import QFont
        font = QFont("Consolas")
        font.setStyleHint(QFont.Monospace)
        font.setPixelSize(13)
        return font

    def _format_hex_dump(self, max_bytes: int = 256) -> str:
        """格式化二进制 hex dump（偏移量 + 十六进制 + ASCII）"""
        try:
            raw = base64.b64decode(self._entry.data)
        except Exception:
            return "(二进制解码失败)"

        lines = []
        for offset in range(0, min(len(raw), max_bytes), 16):
            chunk = raw[offset:offset + 16]
            hex_part = " ".join(f"{b:02x}" for b in chunk)
            ascii_part = "".join(
                chr(b) if 32 <= b <= 126 else "."
                for b in chunk
            )
            lines.append(f"{offset:08x}  {hex_part:<48s} {ascii_part}")

        if len(raw) > max_bytes:
            lines.append(f"... (共 {len(raw)} 字节，仅显示前 {max_bytes} 字节)")

        return "\n".join(lines)

    def _on_copy(self):
        QApplication.clipboard().setText(self._entry.data)

    def _on_download(self):
        filepath, _ = QFileDialog.getSaveFileName(
            self, "保存二进制数据", "data.bin",
            "所有文件 (*.*)"
        )
        if filepath:
            try:
                raw = base64.b64decode(self._entry.data)
                with open(filepath, "wb") as f:
                    f.write(raw)
            except Exception as e:
                print(f"保存失败: {e}")
