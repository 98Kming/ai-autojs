"""图像处理操作函数，对应 Vue 版 OpenCV.js 调用

优先使用 OpenCV，不可用时回退到 Pillow。
所有函数接受 numpy 数组，返回 numpy 数组（BGR 格式）。
"""

from __future__ import annotations

import numpy as np
from app.image_processing.cv_manager import get_cv


def grayscale(image: np.ndarray) -> np.ndarray:
    """彩色转灰度"""
    cv = get_cv()
    if cv is not None:
        gray = cv.cvtColor(image, cv.COLOR_BGR2GRAY)
        return cv.cvtColor(gray, cv.COLOR_GRAY2BGR)  # 转回 3 通道便于显示

    # Pillow 回退
    from PIL import Image
    pil_img = Image.fromarray(image[:, :, ::-1])  # BGR → RGB
    gray_pil = pil_img.convert("L").convert("RGB")
    return np.array(gray_pil)[:, :, ::-1]  # RGB → BGR


def threshold_fixed(image: np.ndarray, thresh: int = 127, maxval: int = 255) -> np.ndarray:
    """固定阈值二值化"""
    cv = get_cv()
    if cv is not None:
        gray = cv.cvtColor(image, cv.COLOR_BGR2GRAY)
        _, result = cv.threshold(gray, thresh, maxval, cv.THRESH_BINARY)
        return cv.cvtColor(result, cv.COLOR_GRAY2BGR)

    # Pillow 回退
    from PIL import Image
    pil_img = Image.fromarray(image[:, :, ::-1])
    gray_pil = pil_img.convert("L")
    bw = gray_pil.point(lambda p: 255 if p > thresh else 0)
    rgb = bw.convert("RGB")
    return np.array(rgb)[:, :, ::-1]


def adaptive_threshold(image: np.ndarray, maxval: int = 255,
                       method: str = "gaussian", block_size: int = 11,
                       C: int = 2) -> np.ndarray:
    """自适应阈值二值化

    Args:
        method: "gaussian" 或 "mean"
        block_size: 块大小（奇数，3-99）
        C: 阈值偏移
    """
    cv = get_cv()
    if cv is not None:
        gray = cv.cvtColor(image, cv.COLOR_BGR2GRAY)
        # 确保 block_size 为奇数
        if block_size % 2 == 0:
            block_size += 1
        block_size = max(3, min(block_size, 99))

        cv_method = cv.ADAPTIVE_THRESH_GAUSSIAN_C if method == "gaussian" else cv.ADAPTIVE_THRESH_MEAN_C
        result = cv.adaptiveThreshold(gray, maxval, cv_method, cv.THRESH_BINARY, block_size, C)
        return cv.cvtColor(result, cv.COLOR_GRAY2BGR)

    # Pillow 回退：简化为固定阈值
    return threshold_fixed(image, 127, maxval)


def in_range(image: np.ndarray, lower: tuple, upper: tuple) -> np.ndarray:
    """颜色范围二值化

    Args:
        lower: 下界 BGR (b, g, r)
        upper: 上界 BGR (b, g, r)
    """
    cv = get_cv()
    if cv is not None:
        lower_arr = np.array(lower, dtype=np.uint8)
        upper_arr = np.array(upper, dtype=np.uint8)
        mask = cv.inRange(image, lower_arr, upper_arr)
        return cv.cvtColor(mask, cv.COLOR_GRAY2BGR)

    # Pillow 回退
    from PIL import Image
    pil_img = Image.fromarray(image[:, :, ::-1])  # BGR → RGB
    arr = np.array(pil_img)
    # 简单实现：检查每个像素是否在范围内
    mask = np.all((arr >= lower[::-1]) & (arr <= upper[::-1]), axis=2)
    result = np.zeros_like(arr)
    result[mask] = 255
    return result[:, :, ::-1]  # RGB → BGR


def resize(image: np.ndarray, new_w: int, new_h: int,
           interpolation: str = "bilinear") -> np.ndarray:
    """调整图片大小

    Args:
        interpolation: nearest / bilinear / bicubic / lanczos4 / area
    """
    inter_map = {
        "nearest": 0,
        "bilinear": 1,
        "bicubic": 2,
        "lanczos4": 4,
        "area": 3,
    }
    inter_code = inter_map.get(interpolation, 1)

    cv = get_cv()
    if cv is not None:
        cv_inter = {
            "nearest": cv.INTER_NEAREST,
            "bilinear": cv.INTER_LINEAR,
            "bicubic": cv.INTER_CUBIC,
            "lanczos4": cv.INTER_LANCZOS4,
            "area": cv.INTER_AREA,
        }
        return cv.resize(image, (new_w, new_h), interpolation=cv_inter.get(interpolation, cv.INTER_LINEAR))

    # Pillow 回退
    from PIL import Image
    pil_inter = {
        "nearest": Image.NEAREST,
        "bilinear": Image.BILINEAR,
        "bicubic": Image.BICUBIC,
        "lanczos4": Image.LANCZOS,
        "area": Image.LANCZOS,  # Pillow 无 AREA
    }
    pil_img = Image.fromarray(image[:, :, ::-1])
    resized = pil_img.resize((new_w, new_h), pil_inter.get(interpolation, Image.BILINEAR))
    return np.array(resized)[:, :, ::-1]


def crop(image: np.ndarray, x: int, y: int, w: int, h: int) -> np.ndarray:
    """裁剪图片"""
    h_img, w_img = image.shape[:2]
    x = max(0, min(x, w_img - 1))
    y = max(0, min(y, h_img - 1))
    w = max(1, min(w, w_img - x))
    h = max(1, min(h, h_img - y))
    return image[y:y + h, x:x + w].copy()


def np_array_to_pixmap(array: np.ndarray) -> "QPixmap":
    """numpy BGR 数组 → QPixmap"""
    from PySide6.QtGui import QPixmap, QImage
    h, w = array.shape[:2]
    bytes_per_line = 3 * w
    qimg = QImage(array.data, w, h, bytes_per_line, QImage.Format_BGR888)
    return QPixmap.fromImage(qimg)


def pixmap_to_np_array(pixmap: "QPixmap") -> np.ndarray:
    """QPixmap → numpy BGR 数组"""
    from PySide6.QtGui import QImage
    qimg = pixmap.toImage().convertToFormat(QImage.Format_BGR888)
    w, h = qimg.width(), qimg.height()
    ptr = qimg.bits()
    # PySide6: QImage.bits() 返回 bytes-like
    arr = np.array(ptr, dtype=np.uint8).reshape(h, w, 3)
    return arr.copy()
