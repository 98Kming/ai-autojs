"""全局 QSS 样式表，对应 src/styles/variables.css"""

# CSS 变量 → QSS 映射
COLORS = {
    "bg_primary": "#ffffff",
    "bg_secondary": "#f5f7fa",
    "bg_tertiary": "#ebeef5",
    "border": "#dcdfe6",
    "text_primary": "#303133",
    "text_secondary": "#606266",
    "text_placeholder": "#c0c4cc",
    "success": "#67c23a",
    "warning": "#e6a23c",
    "danger": "#f56c6c",
    "info": "#909399",
    "primary": "#409eff",
}

FONTS = {
    "editor_family": "'Cascadia Code', 'Fira Code', 'JetBrains Mono', 'Consolas', 'Courier New', monospace",
    "editor_size": "14px",
    "editor_line_height": "1.6",
}

GLOBAL_STYLESHEET = f"""
/* 全局样式 */
QWidget {{
    font-family: "Microsoft YaHei", "Segoe UI", sans-serif;
    font-size: 13px;
    color: {COLORS["text_primary"]};
}}

/* 主窗口背景 */
QMainWindow {{
    background-color: {COLORS["bg_secondary"]};
}}

/* 输入框 */
QLineEdit, QSpinBox, QComboBox {{
    border: 1px solid {COLORS["border"]};
    border-radius: 4px;
    padding: 5px 8px;
    background: {COLORS["bg_primary"]};
}}
QLineEdit:focus, QSpinBox:focus, QComboBox:focus {{
    border-color: {COLORS["primary"]};
}}

/* 按钮 */
QPushButton {{
    border: 1px solid {COLORS["border"]};
    border-radius: 4px;
    padding: 5px 14px;
    background: {COLORS["bg_primary"]};
}}
QPushButton:hover {{
    border-color: {COLORS["primary"]};
    color: {COLORS["primary"]};
}}
QPushButton:pressed {{
    background: {COLORS["bg_tertiary"]};
}}
QPushButton:disabled {{
    color: {COLORS["text_placeholder"]};
    background: {COLORS["bg_tertiary"]};
}}
/* 标签页 */
QTabWidget::pane {{
    border: 1px solid {COLORS["border"]};
    background: {COLORS["bg_primary"]};
    border-radius: 4px;
}}
QTabBar::tab {{
    padding: 8px 20px;
    border: 1px solid transparent;
    border-bottom: none;
    margin-right: 2px;
}}
QTabBar::tab:selected {{
    color: {COLORS["primary"]};
    border-bottom: 2px solid {COLORS["primary"]};
}}
QTabBar::tab:hover {{
    color: {COLORS["primary"]};
}}

/* 滚动条 */
QScrollBar:vertical {{
    width: 8px;
    background: transparent;
}}
QScrollBar::handle:vertical {{
    background: {COLORS["border"]};
    border-radius: 4px;
    min-height: 20px;
}}
QScrollBar::handle:vertical:hover {{
    background: {COLORS["text_placeholder"]};
}}

/* 滚动区域 */
QScrollArea {{
    border: none;
    background: transparent;
}}

/* 分割器 */
QSplitter::handle {{
    background: {COLORS["border"]};
}}
QSplitter::handle:horizontal {{
    width: 1px;
}}
QSplitter::handle:vertical {{
    height: 1px;
}}

/* 菜单 */
QMenu {{
    border: 1px solid {COLORS["border"]};
    border-radius: 4px;
    padding: 4px;
}}
QMenu::item {{
    padding: 6px 24px;
    border-radius: 2px;
}}
QMenu::item:selected {{
    background: {COLORS["bg_secondary"]};
}}

/* 状态栏 */
QStatusBar {{
    background: {COLORS["bg_secondary"]};
    border-top: 1px solid {COLORS["border"]};
    font-size: 12px;
    color: {COLORS["text_secondary"]};
}}
"""
