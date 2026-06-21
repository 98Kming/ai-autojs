"""操作面板基类

浮动面板通用样式：半透明深色背景、白色文字、圆角
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel

from app.widgets.styles import COLORS


class BasePanel(QWidget):
    """浮动操作面板基类"""

    PANEL_STYLE = f"""
        BasePanel {{
            background: rgba(30, 30, 50, 0.95);
            border: 1px solid rgba(255,255,255,0.15);
            border-radius: 8px;
        }}
        BasePanel QLabel {{
            color: #ccc;
            border: none;
            font-size: 12px;
        }}
        BasePanel QLineEdit, BasePanel QSpinBox, BasePanel QDoubleSpinBox, BasePanel QComboBox {{
            border: 1px solid #555;
            border-radius: 4px;
            padding: 4px 8px;
            background: rgba(255,255,255,0.12);
            color: white;
            font-size: 12px;
        }}
        BasePanel QLineEdit:focus, BasePanel QSpinBox:focus, BasePanel QDoubleSpinBox:focus {{
            border-color: {COLORS['primary']};
        }}
        BasePanel QPushButton {{
            border: 1px solid {COLORS['primary']};
            border-radius: 4px;
            padding: 6px 16px;
            background: {COLORS['primary']};
            color: white;
            font-size: 12px;
        }}
        BasePanel QPushButton:hover {{
            background: #66b1ff;
        }}
        BasePanel QPushButton:disabled {{
            background: #555;
            border-color: #555;
        }}
        BasePanel QCheckBox {{
            color: #ccc;
            font-size: 12px;
        }}
        BasePanel QPlainTextEdit {{
            border: 1px solid #555;
            border-radius: 4px;
            padding: 4px;
            background: rgba(255,255,255,0.1);
            color: white;
            font-size: 12px;
        }}
    """

    def __init__(self, title: str, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("action_panel")
        self.setStyleSheet(self.PANEL_STYLE)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.setAutoFillBackground(True)
        self.setMaximumWidth(280)

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(12, 10, 12, 10)
        self._layout.setSpacing(8)

        # 标题
        title_label = QLabel(title)
        title_label.setStyleSheet("color: white; font-size: 13px; font-weight: bold; border: none;")
        self._layout.addWidget(title_label)

    def add_widget(self, widget: QWidget):
        self._layout.addWidget(widget)

    def add_layout(self, layout):
        self._layout.addLayout(layout)

    def show_at(self, x: int, y: int):
        """在指定位置显示面板"""
        self.move(x, y)
        self.adjustSize()  # 根据内容计算合适尺寸
        self.show()
        self.raise_()

    def hide_panel(self):
        self.hide()
