"""编辑器工具栏，对应 EditorToolbar.vue"""
from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton

from app.widgets.styles import COLORS

class EditorToolbar(QWidget):
    """代码编辑器工具栏：格式化 / 清空 / 运行"""

    run_clicked = Signal()
    clear_clicked = Signal()
    format_clicked = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setFixedHeight(40)
        self.setStyleSheet(f"background: {COLORS['bg_secondary']}; border-bottom: 1px solid {COLORS['border']};")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 4, 12, 4)
        layout.setSpacing(8)

        # 标题
        title = QLabel("代码编辑器")
        title.setStyleSheet(f"color: {COLORS['text_secondary']}; border: none; font-weight: bold;")
        layout.addWidget(title)

        layout.addStretch()

        # 格式化按钮
        self._format_btn = QPushButton("格式化")
        self._format_btn.setToolTip("去除每行首尾空白")
        self._format_btn.clicked.connect(self.format_clicked.emit)
        layout.addWidget(self._format_btn)

        # 清空按钮
        self._clear_btn = QPushButton("清空")
        self._clear_btn.setToolTip("清空编辑器和结果")
        self._clear_btn.clicked.connect(self.clear_clicked.emit)
        layout.addWidget(self._clear_btn)

        # 运行按钮
        self._run_btn = QPushButton("▶ 运行")
        self._run_btn.setStyleSheet(f"""
            QPushButton {{
                background: {COLORS['primary']};
                color: white;
                border: 1px solid {COLORS['primary']};
                border-radius: 4px;
                padding: 5px 14px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background: #66b1ff;
            }}
            QPushButton:disabled {{
                background: #a0cfff;
                border-color: #a0cfff;
            }}
        """)
        self._run_btn.setToolTip("运行代码 (Ctrl+Enter)")
        self._run_btn.clicked.connect(self.run_clicked.emit)
        layout.addWidget(self._run_btn)

    def set_buttons_enabled(self, can_run: bool):
        """更新按钮可用状态"""
        self._format_btn.setEnabled(not (not can_run and self._is_executing))
        self._clear_btn.setEnabled(can_run or not self._is_executing)
        self._run_btn.setEnabled(can_run)

    def set_executing(self, executing: bool):
        """执行中状态"""
        self._is_executing = executing
        if executing:
            self._run_btn.setText("执行中...")
            self._run_btn.setEnabled(False)
            self._format_btn.setEnabled(False)
            self._clear_btn.setEnabled(False)
        else:
            self._run_btn.setText("▶ 运行")
            self._run_btn.setEnabled(True)
            self._format_btn.setEnabled(True)
            self._clear_btn.setEnabled(True)
