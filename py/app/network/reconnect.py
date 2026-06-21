"""自动重连调度器，对应 useAutoReconnect.ts

指数退避 + 随机抖动算法
"""

from __future__ import annotations

import random
from PySide6.QtCore import QObject, QTimer


class ReconnectTimer(QObject):
    """指数退避重连调度器"""

    def __init__(self,
                 enabled: bool = True,
                 max_attempts: int = 0,
                 base_delay_ms: int = 1000,
                 max_delay_ms: int = 30000,
                 on_reconnect: callable = None,
                 parent: QObject | None = None):
        super().__init__(parent)
        self._enabled = enabled
        self._max_attempts = max_attempts  # 0 = 无限
        self._base_delay_ms = base_delay_ms
        self._max_delay_ms = max_delay_ms
        self._on_reconnect = on_reconnect
        self._attempt_count = 0
        self._timer: QTimer | None = None

    @property
    def attempt_count(self) -> int:
        return self._attempt_count

    @property
    def is_active(self) -> bool:
        return self._timer is not None and self._timer.isActive()

    @property
    def enabled(self) -> bool:
        return self._enabled

    @enabled.setter
    def enabled(self, val: bool):
        self._enabled = val

    @property
    def max_attempts(self) -> int:
        return self._max_attempts

    @max_attempts.setter
    def max_attempts(self, val: int):
        self._max_attempts = val

    @property
    def base_delay_ms(self) -> int:
        return self._base_delay_ms

    @base_delay_ms.setter
    def base_delay_ms(self, val: int):
        self._base_delay_ms = val

    @property
    def max_delay_ms(self) -> int:
        return self._max_delay_ms

    @max_delay_ms.setter
    def max_delay_ms(self, val: int):
        self._max_delay_ms = val

    def _calc_delay(self) -> int:
        """计算当前退避延迟（指数退避 + 随机抖动）"""
        exponential = self._base_delay_ms * (2 ** self._attempt_count)
        jitter = random.randint(0, int(0.5 * exponential))
        return min(exponential + jitter, self._max_delay_ms)

    def schedule(self):
        """调度下次重连"""
        if not self._enabled:
            return
        if self._max_attempts > 0 and self._attempt_count >= self._max_attempts:
            print(f"[Reconnect] 已达最大重连次数 ({self._max_attempts})，停止")
            return

        delay = self._calc_delay()
        print(f"[Reconnect] 将在 {delay}ms 后尝试第 {self._attempt_count + 1} 次重连")

        if self._timer is None:
            self._timer = QTimer(self)
            self._timer.setSingleShot(True)
            self._timer.timeout.connect(self._on_timeout)
        self._timer.start(delay)

    def _on_timeout(self):
        self._attempt_count += 1
        if self._on_reconnect:
            self._on_reconnect()

    def reset(self):
        """成功后重置计数器"""
        self._attempt_count = 0
        self._stop_timer()

    def destroy(self):
        """清理定时器"""
        self._stop_timer()
        self._attempt_count = 0

    def _stop_timer(self):
        if self._timer is not None:
            self._timer.stop()
