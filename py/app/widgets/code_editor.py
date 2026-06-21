"""代码编辑器组件，对应 CodeEditor.vue

QPlainTextEdit 派生类，带行号标尺和当前行高亮
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal, QRect
from PySide6.QtGui import (
    QPainter, QColor, QFont, QTextFormat, QPen, QFontMetrics,
)
from PySide6.QtWidgets import QPlainTextEdit, QWidget, QTextEdit

from app.widgets.styles import COLORS, FONTS


class LineNumberArea(QWidget):
    """行号标尺"""

    def __init__(self, editor: "CodeEditor"):
        super().__init__(editor)
        self._editor = editor

    def sizeHint(self):
        return self._editor.line_number_area_size()

    def paintEvent(self, event):
        self._editor.paint_line_numbers(event)


class CodeEditor(QPlainTextEdit):
    """代码编辑器（带行号）"""

    run_requested = Signal()  # Ctrl+Enter

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._line_number_area = LineNumberArea(self)

        # 字体设置
        font = QFont()
        font.setFamilies([
            "Cascadia Code", "Fira Code", "JetBrains Mono",
            "Consolas", "Courier New", "monospace",
        ])
        font.setPixelSize(14)
        font.setStyleHint(QFont.Monospace)
        self.setFont(font)

        # 样式
        self.setStyleSheet(f"""
            QPlainTextEdit {{
                background: #fafbfc;
                border: 1px solid {COLORS['border']};
                border-radius: 4px;
                padding: 8px;
                font-family: {FONTS['editor_family']};
                font-size: {FONTS['editor_size']};
                line-height: {FONTS['editor_line_height']};
            }}
            QPlainTextEdit:focus {{
                border-color: {COLORS['primary']};
            }}
        """)

        self.setTabStopDistance(20)  # 约 2 个空格宽度
        self.setPlaceholderText("在此编写 AutoJS 代码...")

        # 信号
        self.blockCountChanged.connect(self._update_line_number_area_width)
        self.updateRequest.connect(self._update_line_number_area)
        self.cursorPositionChanged.connect(self._highlight_current_line)

        self._update_line_number_area_width(0)
        self._highlight_current_line()

    def line_number_area(self) -> LineNumberArea:
        return self._line_number_area

    def line_number_area_width(self) -> int:
        """根据最大行号计算标尺宽度"""
        digits = 1
        max_block = max(1, self.blockCount())
        while max_block >= 10:
            max_block //= 10
            digits += 1
        fm = QFontMetrics(self.font())
        return 12 + fm.horizontalAdvance('9') * digits

    def line_number_area_size(self):
        return QRect(0, 0, self.line_number_area_width(), 0)

    # ============ 重写 ============

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cr = self.contentsRect()
        w = self.line_number_area_width()
        self._line_number_area.setGeometry(
            cr.left(), cr.top(), w, cr.height()
        )

    def keyPressEvent(self, event):
        # Ctrl+Enter → 运行
        if event.key() == Qt.Key_Return and event.modifiers() & Qt.ControlModifier:
            self.run_requested.emit()
            return
        super().keyPressEvent(event)

    # ============ 行号绘制 ============

    def paint_line_numbers(self, event):
        p = QPainter(self._line_number_area)
        p.fillRect(event.rect(), QColor(COLORS["bg_secondary"]))

        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        top = int(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + int(self.blockBoundingRect(block).height())

        fm = QFontMetrics(self.font())
        current_block_number = self.textCursor().blockNumber()

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(block_number + 1)
                # 当前行高亮
                if block_number == current_block_number:
                    p.setPen(QPen(QColor(COLORS["text_primary"])))
                    font = p.font()
                    font.setBold(True)
                    p.setFont(font)
                else:
                    p.setPen(QPen(QColor(COLORS["text_placeholder"])))
                    font = p.font()
                    font.setBold(False)
                    p.setFont(font)

                p.drawText(
                    0, top,
                    self._line_number_area.width() - 4, fm.height(),
                    Qt.AlignRight | Qt.AlignVCenter,
                    number,
                )

            block = block.next()
            top = bottom
            bottom = top + int(self.blockBoundingRect(block).height())
            block_number += 1

        p.end()

    # ============ 内部 ============

    def _update_line_number_area_width(self, _new_block_count: int):
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)

    def _update_line_number_area(self, rect: QRect, dy: int):
        if dy:
            self._line_number_area.scroll(0, dy)
        else:
            self._line_number_area.update(
                0, rect.y(),
                self._line_number_area.width(), rect.height()
            )
        if rect.contains(self.viewport().rect()):
            self._update_line_number_area_width(0)

    def _highlight_current_line(self):
        """高亮当前行背景"""
        selections = []
        cursor = self.textCursor()
        if not cursor.hasSelection():
            sel = QTextEdit.ExtraSelection()
            sel.format.setBackground(QColor("#f0f5ff"))
            sel.format.setProperty(QTextFormat.FullWidthSelection, True)
            sel.cursor = cursor
            sel.cursor.clearSelection()
            selections.append(sel)
        self.setExtraSelections(selections)
