"""结果面板容器，对应 ResultPanel.vue"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QSizePolicy,
)

from app.protocol.messages import ResultEntry
from app.widgets.result_item import ResultItem
from app.widgets.styles import COLORS

class ResultPanel(QWidget):
    """执行结果列表（可滚动）"""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._results: list[ResultItem] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 标题栏
        header = QHBoxLayout()
        header.setContentsMargins(12, 8, 12, 8)
        title = QLabel("执行结果")
        title.setStyleSheet(f"color: {COLORS['text_secondary']}; font-weight: bold; border: none;")
        header.addWidget(title)
        header.addStretch()

        self._clear_btn = QPushButton("清空")
        self._clear_btn.setStyleSheet(f"font-size: 12px; padding: 2px 10px;")
        self._clear_btn.clicked.connect(self.clear)
        self._clear_btn.hide()
        header.addWidget(self._clear_btn)

        layout.addLayout(header)

        # 滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self._container = QWidget()
        self._container_layout = QVBoxLayout(self._container)
        self._container_layout.setContentsMargins(12, 0, 12, 8)
        self._container_layout.setSpacing(4)
        self._container_layout.addStretch()

        scroll.setWidget(self._container)
        layout.addWidget(scroll)

        # 空状态
        self._empty_label = QLabel("等待代码执行...")
        self._empty_label.setAlignment(Qt.AlignCenter)
        self._empty_label.setStyleSheet(f"""
            color: {COLORS['text_placeholder']};
            border: none;
            padding: 40px;
            font-size: 14px;
        """)
        self._container_layout.insertWidget(0, self._empty_label)

    def add_result(self, entry: ResultEntry):
        """添加新结果到列表顶部"""
        item = ResultItem(entry)
        self._results.insert(0, item)
        # 移除旧空状态
        self._empty_label.hide()

        # 插入到 stretch 之前
        self._container_layout.insertWidget(
            self._container_layout.count() - 1, item
        )
        self._clear_btn.show()

    def clear(self):
        """清空所有结果"""
        for item in self._results:
            self._container_layout.removeWidget(item)
            item.deleteLater()
        self._results.clear()
        self._empty_label.show()
        self._clear_btn.hide()
