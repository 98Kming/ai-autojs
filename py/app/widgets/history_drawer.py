"""历史记录抽屉，对应 HistoryDrawer.vue

从右侧滑入的动画面板（380px 宽）
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal, QPropertyAnimation, QEasingCurve, Property
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QMessageBox, QFrame,
)

from app.protocol.messages import HistoryEntry
from app.widgets.history_item import HistoryItem
from app.widgets.styles import COLORS


class HistoryDrawer(QWidget):
    """右侧滑出历史面板"""

    re_run_requested = Signal(HistoryEntry)
    visible_changed = Signal(bool)

    WIDTH = 380

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._items: list[HistoryItem] = []

        # 自身样式
        self.setFixedWidth(self.WIDTH)
        self.setStyleSheet(f"""
            HistoryDrawer {{
                background: {COLORS['bg_primary']};
                border-left: 1px solid {COLORS['border']};
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 标题栏
        header = QWidget()
        header.setFixedHeight(44)
        header.setStyleSheet(f"background: {COLORS['bg_secondary']}; border-bottom: 1px solid {COLORS['border']};")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(16, 0, 12, 0)

        title = QLabel("执行历史")
        title.setStyleSheet(f"font-weight: bold; border: none; font-size: 14px;")
        header_layout.addWidget(title)
        header_layout.addStretch()

        clear_btn = QPushButton("清空全部")
        clear_btn.setStyleSheet(f"""
            QPushButton {{
                color: {COLORS['danger']};
                border: none;
                background: transparent;
                font-size: 12px;
            }}
            QPushButton:hover {{
                color: red;
            }}
        """)
        clear_btn.clicked.connect(self._confirm_clear)
        header_layout.addWidget(clear_btn)

        layout.addWidget(header)

        # 列表滚动区
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self._list_container = QWidget()
        self._list_layout = QVBoxLayout(self._list_container)
        self._list_layout.setContentsMargins(12, 8, 12, 8)
        self._list_layout.setSpacing(4)
        self._list_layout.addStretch()

        scroll.setWidget(self._list_container)
        layout.addWidget(scroll)

        # 空状态
        self._empty_label = QLabel("暂无执行历史")
        self._empty_label.setAlignment(Qt.AlignCenter)
        self._empty_label.setStyleSheet(f"""
            color: {COLORS['text_placeholder']};
            border: none;
            padding: 40px;
            font-size: 14px;
        """)
        self._list_layout.insertWidget(0, self._empty_label)

        # 动画（_slide_offset 必须在 QPropertyAnimation 之前初始化）
        self._slide_offset = 0
        self._visible = False
        self._anim = QPropertyAnimation(self, b"slide_offset")
        self._anim.setDuration(250)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        self._anim.finished.connect(self._on_anim_finished)

    # ============ slide_offset 属性（动画用） ============

    def get_slide_offset(self) -> int:
        return self._slide_offset

    def set_slide_offset(self, val: int):
        self._slide_offset = val
        if self.parent():
            self.move(self.parent().width() - self.WIDTH + val, self.y())

    slide_offset = Property(int, get_slide_offset, set_slide_offset)

    # ============ 公共方法 ============

    def set_visible(self, visible: bool):
        """显示/隐藏动画"""
        if self._visible == visible:
            return
        self._visible = visible

        if visible:
            self.show()
            self.raise_()
            self._anim.setStartValue(self.WIDTH)
            self._anim.setEndValue(0)
        else:
            self._anim.setStartValue(0)
            self._anim.setEndValue(self.WIDTH)
        self._anim.start()

    def is_visible(self) -> bool:
        return self._visible

    def refresh(self, entries: list[HistoryEntry],
                on_re_run: callable = None,
                on_delete: callable = None):
        """刷新列表"""
        # 清除旧项
        for item in self._items:
            self._list_layout.removeWidget(item)
            item.deleteLater()
        self._items.clear()

        if not entries:
            self._empty_label.show()
            return

        self._empty_label.hide()
        # 在 stretch 之前插入新项
        insert_pos = self._list_layout.count() - 1
        for entry in entries:
            item = HistoryItem(entry)
            if on_re_run:
                item.re_run.connect(on_re_run)
            if on_delete:
                item.delete_requested.connect(on_delete)
            self._items.append(item)
            self._list_layout.insertWidget(insert_pos, item)
            insert_pos += 1

    # ============ 内部 ============

    def _confirm_clear(self):
        reply = QMessageBox.question(
            self, "确认清空", "确定要清空所有执行历史吗？",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            # 清除信号由外部处理
            self.clear_all()

    def clear_all(self):
        for item in self._items:
            self._list_layout.removeWidget(item)
            item.deleteLater()
        self._items.clear()
        self._empty_label.show()

    def _on_anim_finished(self):
        if not self._visible:
            self.hide()
        self.visible_changed.emit(self._visible)
