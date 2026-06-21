"""AI-AutoJS Python 桌面版入口"""

import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from app.widgets.styles import GLOBAL_STYLESHEET


def main():
    # 高 DPI 支持
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(sys.argv)
    app.setApplicationName("AI-AutoJS")
    app.setOrganizationName("ai-autojs")
    app.setApplicationVersion("0.1.0")

    # 应用全局 QSS 主题
    app.setStyleSheet(GLOBAL_STYLESHEET)

    # 延迟导入主窗口（等 QApplication 创建后再导入 Qt 依赖的模块）
    from app.main_window import MainWindow
    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
