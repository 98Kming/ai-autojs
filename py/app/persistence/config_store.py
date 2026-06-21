"""JSON 文件持久化，对应 src/utils/storage.ts

使用 QStandardPaths 获取跨平台应用数据目录：
- Windows: %APPDATA%/ai-autojs/
- Linux:   ~/.local/share/ai-autojs/
- macOS:   ~/Library/Application Support/ai-autojs/
"""

import json
import os
from typing import Any, Optional

from PySide6.QtCore import QStandardPaths


def _config_dir() -> str:
    """获取配置目录，不存在则创建"""
    base = QStandardPaths.writableLocation(QStandardPaths.AppDataLocation)
    path = os.path.join(base, "ai-autojs")
    os.makedirs(path, exist_ok=True)
    return path


def _images_dir() -> str:
    """获取图片存储目录，不存在则创建"""
    path = os.path.join(_config_dir(), "images")
    os.makedirs(path, exist_ok=True)
    return path


def _read_json(filename: str, default: Any = None) -> Any:
    """读取 JSON 文件，失败返回默认值"""
    filepath = os.path.join(_config_dir(), filename)
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return default


def _write_json(filename: str, data: Any) -> bool:
    """写入 JSON 文件，返回是否成功"""
    filepath = os.path.join(_config_dir(), filename)
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except OSError as e:
        print(f"[ConfigStore] 写入 {filename} 失败: {e}")
        return False


# ============ 连接配置 ============

def load_config() -> dict:
    """加载连接配置，返回 dict（与默认值合并）"""
    data = _read_json("config.json", {})
    if not isinstance(data, dict):
        data = {}
    return data


def save_config(config: dict) -> bool:
    """保存连接配置"""
    return _write_json("config.json", config)


# ============ 执行历史 ============

def load_history() -> list:
    """加载执行历史，返回列表"""
    data = _read_json("history.json", [])
    if not isinstance(data, list):
        data = []
    return data


def save_history(entries: list) -> bool:
    """保存执行历史"""
    return _write_json("history.json", entries)


# ============ 图片元数据 ============

def load_images_index() -> list:
    """加载图片元数据索引"""
    data = _read_json("images.json", [])
    if not isinstance(data, list):
        data = []
    return data


def save_images_index(entries: list) -> bool:
    """保存图片元数据索引"""
    return _write_json("images.json", entries)


def get_image_path(filename: str) -> str:
    """获取图片文件的完整路径"""
    return os.path.join(_images_dir(), filename)


def save_image_file(filename: str, data: bytes) -> bool:
    """保存图片二进制数据到文件"""
    filepath = get_image_path(filename)
    try:
        with open(filepath, "wb") as f:
            f.write(data)
        return True
    except OSError as e:
        print(f"[ConfigStore] 保存图片 {filename} 失败: {e}")
        return False


def delete_image_file(filename: str) -> bool:
    """删除图片文件"""
    filepath = get_image_path(filename)
    try:
        if os.path.exists(filepath):
            os.remove(filepath)
        return True
    except OSError as e:
        print(f"[ConfigStore] 删除图片 {filename} 失败: {e}")
        return False
