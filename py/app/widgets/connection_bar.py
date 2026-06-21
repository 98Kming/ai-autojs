"""连接栏组件，对应 ConnectionPanel.vue"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QLabel, QLineEdit, QSpinBox, QPushButton,
)

from app.widgets.styles import COLORS

class ConnectionBar(QWidget):
    """连接栏：主机地址 + 端口 + 连接/断开按钮"""

    connect_clicked = Signal()
    disconnect_clicked = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setFixedHeight(44)
        self.setStyleSheet(f"background: {COLORS['bg_secondary']}; border-bottom: 1px solid {COLORS['border']};")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 6, 16, 6)
        layout.setSpacing(8)

        # ws:// 前缀标签
        prefix = QLabel("ws://")
        prefix.setStyleSheet(f"color: {COLORS['text_secondary']}; border: none;")
        layout.addWidget(prefix)

        # 主机地址输入
        self._host_input = QLineEdit()
        self._host_input.setPlaceholderText("输入手机 IP 地址")
        self._host_input.setMinimumWidth(160)
        self._host_input.setMaximumWidth(280)
        layout.addWidget(self._host_input)

        # 分隔符和端口
        layout.addWidget(QLabel(":"))
        self._port_input = QSpinBox()
        self._port_input.setRange(1, 65535)
        self._port_input.setValue(9318)
        self._port_input.setFixedWidth(80)
        layout.addWidget(self._port_input)

        layout.addSpacing(8)

        # 连接按钮
        self._connect_btn = QPushButton("🔗 连接")
        self._connect_btn.setStyleSheet(f"""
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
        self._connect_btn.clicked.connect(self.connect_clicked.emit)
        layout.addWidget(self._connect_btn)

        # 断开按钮
        self._disconnect_btn = QPushButton("断开")
        self._disconnect_btn.setStyleSheet(f"""
            QPushButton {{
                border: 1px solid {COLORS['danger']};
                border-radius: 4px;
                padding: 5px 14px;
                background: {COLORS['bg_primary']};
                color: {COLORS['danger']};
            }}
            QPushButton:hover {{
                background: {COLORS['danger']};
                color: white;
            }}
        """)
        self._disconnect_btn.clicked.connect(self.disconnect_clicked.emit)
        self._disconnect_btn.hide()
        layout.addWidget(self._disconnect_btn)

        layout.addStretch()

    @property
    def host(self) -> str:
        return self._host_input.text().strip()

    @host.setter
    def host(self, value: str):
        self._host_input.setText(value)

    @property
    def port(self) -> int:
        return self._port_input.value()

    @port.setter
    def port(self, value: int):
        self._port_input.setValue(value)

    def set_connected(self, connected: bool):
        """切换连接/断开按钮显示"""
        self._connect_btn.setVisible(not connected)
        self._disconnect_btn.setVisible(connected)
        self._host_input.setEnabled(not connected)
        self._port_input.setEnabled(not connected)

    def set_connecting(self):
        """连接中状态"""
        self._connect_btn.setText("连接中...")
        self._connect_btn.setEnabled(False)

    def reset_connect_button(self):
        """重置连接按钮"""
        self._connect_btn.setText("🔗 连接")
        self._connect_btn.setEnabled(True)
