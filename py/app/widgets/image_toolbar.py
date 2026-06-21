"""图片工具栏，对应 ImagePanel 的 tool-bar 部分"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QSizePolicy,
)

from app.widgets.styles import COLORS


class ImageToolbar(QWidget):
    """左侧竖排工具按钮栏（72px 宽）"""

    trigger_screenshot = Signal()
    mode_changed = Signal(str)  # crop / resize / grayscale / threshold / adaptive / inrange / find

    BUTTONS = [
        ("screenshot", "📷\n截图", "截取手机屏幕"),
        ("crop", "✂️\n剪裁", "框选区域裁剪"),
        ("resize", "📐\n调整", "调整图片大小"),
        ("grayscale", "⬜\n灰度", "彩色转灰度"),
        ("threshold", "⚫\n阈值", "固定阈值二值化"),
        ("adaptive", "🔲\n自适应", "自适应阈值二值化"),
        ("inrange", "🎨\n二值化", "颜色范围二值化"),
        ("find", "🔍\n找图", "在屏幕上查找模板"),
        ("ocr", "🔤\nOCR", "文字识别（即将上线）"),
    ]

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setFixedWidth(72)
        self.setStyleSheet(f"background: {COLORS['bg_secondary']}; border-right: 1px solid {COLORS['border']};")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 8, 4, 8)
        layout.setSpacing(4)

        self._buttons: dict[str, QPushButton] = {}
        self._active_mode: str | None = None

        for mode, text, tooltip in self.BUTTONS:
            btn = QPushButton(text)
            btn.setToolTip(tooltip)
            btn.setFixedSize(64, 50)
            btn.setStyleSheet(f"""
                QPushButton {{
                    border: 1px solid transparent;
                    border-radius: 6px;
                    background: transparent;
                    font-size: 10px;
                    color: {COLORS['text_secondary']};
                    padding: 4px;
                }}
                QPushButton:hover {{
                    background: {COLORS['bg_primary']};
                    border-color: {COLORS['border']};
                }}
                QPushButton[active="true"] {{
                    background: {COLORS['bg_primary']};
                    border-color: {COLORS['primary']};
                    color: {COLORS['primary']};
                }}
            """)
            self._buttons[mode] = btn

            if mode == "screenshot":
                btn.clicked.connect(lambda _=False: self.trigger_screenshot.emit())
            elif mode == "ocr":
                btn.setEnabled(False)
                btn.setToolTip("OCR 功能即将上线")
            else:
                btn.clicked.connect(lambda checked=False, m=mode: self._on_mode_click(m))

            layout.addWidget(btn)

        layout.addStretch()

    def set_active(self, mode: str | None):
        """设置当前激活模式"""
        if self._active_mode == mode:
            return
        # 取消旧激活
        if self._active_mode and self._active_mode in self._buttons:
            self._buttons[self._active_mode].setProperty("active", False)
            self._buttons[self._active_mode].setStyleSheet(
                self._buttons[self._active_mode].styleSheet()
            )
        # 设置新激活
        self._active_mode = mode
        if mode and mode in self._buttons:
            self._buttons[mode].setProperty("active", True)
            self._buttons[mode].setStyleSheet(
                self._buttons[mode].styleSheet()
            )
        self.mode_changed.emit(mode or "")

    def _on_mode_click(self, mode: str):
        """点击模式按钮（切换激活）"""
        if self._active_mode == mode:
            self.set_active(None)  # 取消激活
        else:
            self.set_active(mode)
