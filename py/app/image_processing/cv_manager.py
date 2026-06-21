"""OpenCV 可用性检测，对应 Vue 版的 OpenCV.js 动态加载

在 Python 桌面版中，OpenCV 通过 pip 安装（opencv-python-headless），
无需运行时加载。此模块提供可用性检查和惰性导入。
"""

from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)

_cv_module: Optional[object] = None
_cv_checked = False


def is_cv_available() -> bool:
    """检测 OpenCV 是否可用"""
    global _cv_checked
    if not _cv_checked:
        try:
            import cv2
            global _cv_module
            _cv_module = cv2
            logger.info(f"OpenCV {cv2.__version__} 已就绪")
        except ImportError:
            logger.warning("OpenCV 未安装，图像处理将使用 Pillow 回退")
        _cv_checked = True
    return _cv_module is not None


def get_cv():
    """获取 cv2 模块，不可用时返回 None"""
    if not _cv_checked:
        is_cv_available()
    return _cv_module


def ensure_cv():
    """获取 cv2 模块，不可用时抛出 ImportError"""
    if not _cv_checked:
        is_cv_available()
    if _cv_module is None:
        raise ImportError(
            "OpenCV 未安装。请运行: pip install opencv-python-headless"
        )
    return _cv_module


def get_cv_version() -> str | None:
    """获取 OpenCV 版本号"""
    cv = get_cv()
    if cv:
        return cv.__version__
    return None
