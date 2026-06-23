"""主窗口，对应 HomeView.vue + App.vue

中央编排器：创建所有 Model、WebSocketClient、Widget，并连接信号。
"""

import time
import secrets

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QTabWidget,
    QStatusBar, QLabel, QCheckBox,
)
from PySide6.QtGui import QKeyEvent

from app.protocol.messages import (
    ResultMessage, HistoryEntry,
)
from app.protocol.templates import (
    SCREENSHOT_TEMPLATE,
    find_image_template,
)

from app.models.connection import ConnectionModel
from app.models.code_editor import CodeEditorModel
from app.models.history import HistoryModel
from app.models.images import ImageModel

from app.network.ws_client import WebSocketClient

from app.widgets.header_bar import HeaderBar
from app.widgets.connection_bar import ConnectionBar
from app.widgets.code_editor import CodeEditor
from app.widgets.editor_toolbar import EditorToolbar
from app.widgets.result_panel import ResultPanel
from app.widgets.history_drawer import HistoryDrawer
from app.widgets.image_toolbar import ImageToolbar
from app.widgets.image_list_panel import ImageListPanel
from app.widgets.image_viewer import ImageViewer
from app.widgets.magnifier_lens import MagnifierLens

from app.widgets.styles import COLORS


class MainWindow(QMainWindow):
    """AI-AutoJS 主窗口"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("AI-AutoJS")
        self.resize(1200, 800)
        self.setMinimumSize(800, 500)

        # ============ Model 层 ============
        self._conn_model = ConnectionModel(self)
        self._code_model = CodeEditorModel(self)
        self._history_model = HistoryModel(self)
        self._image_model = ImageModel(self)

        # ============ WebSocket 客户端 ============
        self._ws_client = WebSocketClient(
            host=self._conn_model.host,
            port=self._conn_model.port,
            heartbeat_interval_ms=self._conn_model.config.heartbeat_interval_ms,
            reconnect_enabled=self._conn_model.config.reconnect_enabled,
            reconnect_max_attempts=self._conn_model.config.reconnect_max_attempts,
            reconnect_base_delay_ms=self._conn_model.config.reconnect_base_delay_ms,
            reconnect_max_delay_ms=self._conn_model.config.reconnect_max_delay_ms,
            parent=self,
        )

        # ============ UI 构建 ============
        self._setup_ui()
        self._setup_statusbar()
        self._wire_signals()

        # 执行起始时间（用于计算耗时）
        self._exec_start_time: float = 0.0
        self._current_zoom: float = 1.0

        # ============ 恢复状态 ============
        self._restore_window_state()
        # 加载已有图片和历史记录
        self._on_images_changed()
        self._refresh_history_drawer()

    def _setup_ui(self):
        """构建 UI 布局"""
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ---- 顶栏 ----
        self._header_bar = HeaderBar()
        layout.addWidget(self._header_bar)

        # ---- 连接栏 ----
        self._connection_bar = ConnectionBar()
        self._connection_bar.host = self._conn_model.host
        self._connection_bar.port = self._conn_model.port
        layout.addWidget(self._connection_bar)

        # ---- 标签页 ----
        self._tab_widget = QTabWidget()
        layout.addWidget(self._tab_widget)

        # Tab 1: 代码执行
        self._setup_code_tab()

        # Tab 2: 图片处理
        self._setup_image_tab()

        # ---- 历史抽屉 ----
        self._history_drawer = HistoryDrawer(self)
        self._history_drawer.set_top_offset(self._header_bar.height())
        self._history_drawer.hide()

        self._tab_widget.currentChanged.connect(self._on_tab_changed)

    def _setup_code_tab(self):
        """代码执行 Tab 布局"""
        splitter = QSplitter(Qt.Horizontal)

        # 左侧：编辑器
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)

        self._editor_toolbar = EditorToolbar()
        left_layout.addWidget(self._editor_toolbar)

        self._code_editor = CodeEditor()
        left_layout.addWidget(self._code_editor)

        splitter.addWidget(left)

        # 右侧：结果
        self._result_panel = ResultPanel()
        splitter.addWidget(self._result_panel)

        splitter.setSizes([600, 600])
        self._tab_widget.addTab(splitter, "代码执行")

    def _setup_image_tab(self):
        """图片处理 Tab 布局：工具栏 | 缩略图列表 | 大图查看器"""
        splitter = QSplitter(Qt.Horizontal)

        # 左侧：工具栏（72px）
        self._image_toolbar = ImageToolbar()
        splitter.addWidget(self._image_toolbar)

        # 中间：缩略图列表（240px）
        self._image_list_panel = ImageListPanel()
        splitter.addWidget(self._image_list_panel)

        # 右侧：查看器
        viewer_container = QWidget()
        viewer_layout = QVBoxLayout(viewer_container)
        viewer_layout.setContentsMargins(0, 0, 0, 0)
        viewer_layout.setSpacing(0)

        # 查看器工具栏：放大镜复选框 + 缩放比例 + 模式徽章
        toolbar = QWidget()
        toolbar.setFixedHeight(32)
        toolbar.setStyleSheet(f"background: rgba(26,26,46,0.95);")
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(8, 4, 8, 4)

        self._magnifier_checkbox = QCheckBox("🔍 放大镜")
        self._magnifier_checkbox.setChecked(True)
        self._magnifier_checkbox.setStyleSheet(f"color: white; font-size: 12px;")
        self._magnifier_checkbox.toggled.connect(self._on_magnifier_toggled)
        toolbar_layout.addWidget(self._magnifier_checkbox)

        toolbar_layout.addStretch()

        self._image_info_label = QLabel()
        self._image_info_label.setStyleSheet(f"color: {COLORS['text_placeholder']}; font-size: 12px; border: none;")
        toolbar_layout.addWidget(self._image_info_label)

        self._viewport_label = QLabel()
        self._viewport_label.setStyleSheet(f"color: {COLORS['text_placeholder']}; font-size: 12px; border: none;")
        toolbar_layout.addWidget(self._viewport_label)

        self._zoom_label = QLabel("100%")
        self._zoom_label.setStyleSheet(f"color: {COLORS['text_placeholder']}; font-size: 12px; border: none;")
        toolbar_layout.addWidget(self._zoom_label)

        viewer_layout.addWidget(toolbar)

        # QGraphicsView 查看器
        self._image_viewer = ImageViewer()
        viewer_layout.addWidget(self._image_viewer)

        # 放大镜叠加层
        self._magnifier_lens = MagnifierLens(self._image_viewer)
        self._magnifier_lens.hide()

        splitter.addWidget(viewer_container)
        splitter.setSizes([72, 240, 888])
        self._tab_widget.addTab(splitter, "图片处理")

        # --- 操作面板（浮动在查看器上方）---
        self._setup_action_panels(viewer_container)

    def _setup_action_panels(self, parent: QWidget):
        """创建所有操作面板（浮动在查看器上方）"""
        from app.widgets.action_panels.crop_panel import CropPanel
        from app.widgets.action_panels.resize_panel import ResizePanel
        from app.widgets.action_panels.grayscale_panel import GrayscalePanel
        from app.widgets.action_panels.threshold_panel import ThresholdPanel
        from app.widgets.action_panels.adaptive_panel import AdaptivePanel
        from app.widgets.action_panels.inrange_panel import InRangePanel
        from app.widgets.action_panels.find_image_panel import FindImagePanel

        self._action_panels = {}

        # 裁剪面板
        crop_panel = CropPanel(parent)
        crop_panel.crop_execute.connect(self._on_crop_execute)
        self._action_panels["crop"] = crop_panel

        # 调整大小面板
        resize_panel = ResizePanel(parent)
        resize_panel.resize_execute.connect(self._on_resize_execute)
        self._action_panels["resize"] = resize_panel

        # 灰度化面板
        grayscale_panel = GrayscalePanel(parent)
        grayscale_panel.grayscale_execute.connect(self._on_grayscale_execute)
        self._action_panels["grayscale"] = grayscale_panel

        # 阈值面板
        threshold_panel = ThresholdPanel(parent)
        threshold_panel.threshold_execute.connect(self._on_threshold_execute)
        self._action_panels["threshold"] = threshold_panel

        # 自适应阈值面板
        adaptive_panel = AdaptivePanel(parent)
        adaptive_panel.adaptive_execute.connect(self._on_adaptive_execute)
        self._action_panels["adaptive"] = adaptive_panel

        # inRange 面板
        inrange_panel = InRangePanel(parent)
        inrange_panel.inrange_execute.connect(self._on_inrange_execute)
        inrange_panel.color_pick_requested.connect(self._on_color_pick)
        self._action_panels["inrange"] = inrange_panel

        # 找图面板
        find_panel = FindImagePanel(parent)
        find_panel.find_execute.connect(self._on_find_execute)
        self._action_panels["find"] = find_panel

        # 全部隐藏
        for panel in self._action_panels.values():
            panel.hide()

    def _setup_statusbar(self):
        """底部状态栏"""
        self._statusbar = QStatusBar()
        self._statusbar.setStyleSheet(f"""
            QStatusBar {{
                background: {COLORS['bg_secondary']};
                border-top: 1px solid {COLORS['border']};
                font-size: 12px;
                color: {COLORS['text_secondary']};
            }}
        """)
        self.setStatusBar(self._statusbar)
        self._status_label = QLabel("就绪")
        self._statusbar.addWidget(self._status_label)

    # ============ 信号接线 ============

    def _wire_signals(self):
        """连接所有信号和槽"""

        # --- 顶栏 ---
        self._header_bar.history_clicked.connect(self._toggle_history)

        # --- 连接栏 ---
        self._connection_bar.connect_clicked.connect(self._on_connect)
        self._connection_bar.disconnect_clicked.connect(self._on_disconnect)

        # --- 编辑器工具栏 ---
        self._editor_toolbar.run_clicked.connect(self._on_run)
        self._editor_toolbar.clear_clicked.connect(self._on_clear)
        self._editor_toolbar.format_clicked.connect(self._on_format)

        # --- 代码编辑器 ---
        self._code_editor.textChanged.connect(self._on_code_changed)
        self._code_editor.run_requested.connect(self._on_run)  # Ctrl+Enter

        # --- WebSocket 客户端 ---
        self._ws_client.status_changed.connect(self._on_ws_status_changed)
        self._ws_client.result_received.connect(self._on_ws_result)

        # --- CodeEditorModel ---
        self._code_model.executing_changed.connect(self._editor_toolbar.set_executing)

        # --- HistoryModel ---
        self._history_model.entries_changed.connect(self._refresh_history_drawer)

        # --- ConnectionModel ---
        self._conn_model.status_changed.connect(self._header_bar.status_dot.set_status)
        self._conn_model.history_visible_changed.connect(self._history_drawer.set_visible)

        # --- HistoryDrawer ---
        self._history_drawer.re_run_requested.connect(self._on_re_run)

        # --- Image Tab ---
        self._image_toolbar.trigger_screenshot.connect(self._on_trigger_screenshot)
        self._image_toolbar.mode_changed.connect(self._on_image_mode_changed)
        self._image_list_panel.image_selected.connect(self._on_image_selected)
        self._image_list_panel.delete_image.connect(self._on_image_delete)
        self._image_list_panel.clear_all.connect(self._image_model.clear_all)
        self._image_viewer.zoom_changed.connect(self._on_zoom_changed)
        self._image_viewer.viewport_resized.connect(self._on_viewport_resized)
        self._image_viewer.mouse_moved_image.connect(self._on_viewer_mouse_moved)
        self._image_viewer.mouse_left_image.connect(self._on_viewer_mouse_left)
        self._image_viewer.region_selected.connect(self._on_crop_region_selected)
        self._image_viewer.pixel_picked.connect(self._on_pixel_picked)
        self._image_model.images_changed.connect(self._on_images_changed)
        self._image_model.image_added.connect(self._on_image_added)

    # ============ 槽函数 ============

    def _on_connect(self):
        """连接按钮"""
        host = self._connection_bar.host
        port = self._connection_bar.port
        self._conn_model.host = host
        self._conn_model.port = port
        self._ws_client.connect_to_host(host, port)

    def _on_disconnect(self):
        """断开按钮"""
        self._ws_client.disconnect()

    def _on_ws_status_changed(self, status: str):
        """WebSocket 状态变化"""
        self._conn_model.set_status(status)

        if status == "connected":
            self._connection_bar.set_connected(True)
            self._status_label.setText(f"已连接 {self._conn_model.host}:{self._conn_model.port}")
            self.setWindowTitle(f"AI-AutoJS - 已连接 {self._conn_model.host}:{self._conn_model.port}")
        elif status == "connecting":
            self._connection_bar.set_connecting()
            self._status_label.setText("正在连接...")
            self.setWindowTitle("AI-AutoJS - 连接中...")
        elif status == "disconnected":
            self._connection_bar.set_connected(False)
            self._connection_bar.reset_connect_button()
            self._status_label.setText("未连接")
            self.setWindowTitle("AI-AutoJS - 未连接")
        elif status == "error":
            self._connection_bar.set_connected(False)
            self._connection_bar.reset_connect_button()
            self._status_label.setText(f"连接错误: {self._conn_model.last_error or '未知错误'}")
            self.setWindowTitle("AI-AutoJS - 连接错误")

    def _on_run(self):
        """执行代码"""
        code = self._code_model.content.strip()
        if not code:
            return

        self._exec_start_time = time.time()
        self._code_model.set_executing(True)

        # 添加 pending 历史条目
        entry = HistoryEntry(
            id=secrets.token_hex(10),
            code=code,
            result="",
            result_data_type="text",
            status="pending",
            timestamp=time.time(),
        )
        self._history_model.add_entry(entry)

        sent = self._ws_client.send_code(code)
        if not sent:
            self._code_model.set_executing(False)
            self._status_label.setText("未连接，无法执行代码")
            # 将 pending 更新为错误
            self._history_model.update_last_entry(
                result="未连接，无法执行代码",
                status="error",
            )

    def _on_clear(self):
        """清空编辑器和结果"""
        self._code_model.clear_content()
        self._code_editor.setPlainText("")
        self._result_panel.clear()

    def _on_format(self):
        """格式化代码：去除每行首尾空白"""
        lines = self._code_model.content.split("\n")
        formatted = "\n".join(line.strip() for line in lines)
        self._code_model.set_content(formatted)
        self._code_editor.setPlainText(formatted)

    def _on_code_changed(self):
        """编辑器内容变化"""
        self._code_model.set_content(self._code_editor.toPlainText())

    def _on_ws_result(self, msg: ResultMessage):
        """收到 WebSocket 执行结果"""
        self._code_model.set_executing(False)
        duration_ms = (time.time() - self._exec_start_time) * 1000 if self._exec_start_time > 0 else 0
        self._code_model.set_result(msg, duration_ms)

        # 更新历史记录
        self._history_model.update_last_entry(
            result=msg.data,
            status=msg.status,
            data_type=msg.data_type,
            mime=msg.mime,
            duration_ms=duration_ms,
        )

        # 添加到结果面板
        if self._code_model.last_result:
            self._result_panel.add_result(self._code_model.last_result)

        # 图片结果 → 图片列表
        if (msg.data_type == "base64"
                and msg.mime
                and msg.mime.startswith("image/")
                and msg.status == "success"):
            self._image_model.add_image(
                data=msg.data,
                mime=msg.mime,
                code=self._code_model.content,
            )
            self._status_label.setText("截图已保存")
            return

        if msg.status == "error":
            err_text = (msg.data or "")[:100]
            self._status_label.setText(f"执行出错: {err_text}")
        else:
            self._status_label.setText("执行成功")

    def _on_re_run(self, entry: HistoryEntry):
        """重新运行历史代码"""
        self._code_model.set_content(entry.code)
        self._code_editor.setPlainText(entry.code)
        self._tab_widget.setCurrentIndex(0)  # 切换到代码执行 Tab

    def _on_trigger_screenshot(self):
        """触发截图"""
        self._code_model.set_content(SCREENSHOT_TEMPLATE)
        self._code_editor.setPlainText(SCREENSHOT_TEMPLATE)
        self._on_run()

    def _on_trigger_find_image(self, template_base64: str,
                                x: int, y: int, w: int, h: int,
                                threshold: float = 0.9):
        """触发找图"""
        code = find_image_template(template_base64, x, y, w, h, threshold)
        self._code_model.set_content(code)
        self._code_editor.setPlainText(code)
        self._on_run()

    def _toggle_history(self):
        """切换历史抽屉"""
        self._conn_model.toggle_history()

    def _refresh_history_drawer(self):
        """刷新历史抽屉内容"""
        self._history_drawer.refresh(
            self._history_model.entries,
            on_re_run=self._on_re_run,
            on_delete=lambda eid: self._history_model.remove_entry(eid),
        )
        self._header_bar.update_badge(self._history_model.count)

    def _update_image_tab_label(self):
        """更新图片 Tab 标签"""
        count = self._image_model.count
        label = f"图片处理 ({count})" if count > 0 else "图片处理"
        self._tab_widget.setTabText(1, label)

    def _on_tab_changed(self, index: int):
        """Tab 切换"""
        pass

    # ============ 图片 Tab 槽函数 ============

    def _on_image_mode_changed(self, mode: str):
        """图片处理模式切换 → 显示对应操作面板"""
        # 隐藏所有面板
        for panel in self._action_panels.values():
            panel.hide_panel()

        if not mode:
            self._status_label.setText("就绪")
            return

        # 显示对应面板（定位在查看器右上角）
        panel = self._action_panels.get(mode)
        if panel:
            container = self._image_viewer.parent()
            cw = container.width() if container else 800
            px = max(0, cw - 290)
            py = 40
            panel.show_at(px, py)
            panel.raise_()
            # 如果是调整大小面板，同步当前图片尺寸
            if mode == "resize":
                pixmap = self._image_viewer.get_current_pixmap()
                if pixmap and not pixmap.isNull():
                    panel.set_original_size(pixmap.width(), pixmap.height())
            self._status_label.setText(f"模式: {mode}")
        else:
            self._status_label.setText(f"模式: {mode or '无'}")

    def _on_image_selected(self, image_id: str):
        """选中缩略图 → 加载到查看器"""
        entry = self._image_model.get_image_by_id(image_id)
        if entry:
            self._image_viewer.load_image(entry)

    def _on_image_delete(self, image_id: str):
        """删除图片"""
        self._image_model.remove_image(image_id)

    def _on_images_changed(self):
        """图片列表变化 → 刷新缩略图列表和 Tab 标签"""
        self._image_list_panel.refresh(self._image_model.images)
        self._update_image_tab_label()

    def _on_image_added(self, entry):
        """新图片添加 → 自动选中"""
        self._image_viewer.load_image(entry)

    def _on_zoom_changed(self, zoom: float):
        """缩放比例变化"""
        self._current_zoom = zoom
        pct = int(zoom * 100)
        self._zoom_label.setText(f"{pct}%")
        self._update_image_info()

    def _update_image_info(self):
        """更新图片原图和显示尺寸"""
        pixmap = self._image_viewer.get_current_pixmap()
        if pixmap is None or pixmap.isNull():
            self._image_info_label.setText("")
            return
        iw, ih = pixmap.width(), pixmap.height()
        dw = int(iw * self._current_zoom)
        dh = int(ih * self._current_zoom)
        self._image_info_label.setText(f"原图 {iw}×{ih} | 显示 {dw}×{dh}")

    def _on_viewport_resized(self, w: int, h: int):
        """视窗大小变化"""
        self._viewport_label.setText(f"视窗 {w}×{h}")

    def _on_viewer_mouse_moved(self, scene_pos):
        """鼠标在图片上移动 → 更新放大镜"""
        if not self._magnifier_checkbox.isChecked():
            return
        pixmap = self._image_viewer.get_current_pixmap()
        if pixmap is None:
            return

        # 更新放大镜位置和源像素
        x, y = int(scene_pos.x()), int(scene_pos.y())
        self._magnifier_lens.set_pixel(x, y)

        # 定位放大镜在鼠标右下角
        global_pos = self._image_viewer.mapFromScene(scene_pos)
        lens_x = int(global_pos.x()) + 20
        lens_y = int(global_pos.y()) + 20

        # 边缘翻转：确保不超出 viewer
        vw = self._image_viewer.width()
        vh = self._image_viewer.height()
        if lens_x + self._magnifier_lens.SIZE > vw:
            lens_x = int(global_pos.x()) - self._magnifier_lens.SIZE - 20
        if lens_y + self._magnifier_lens.SIZE + 24 > vh:
            lens_y = int(global_pos.y()) - self._magnifier_lens.SIZE - 44

        self._magnifier_lens.move(lens_x, lens_y)

        # 设置源图片（QImage 格式）
        qimage = pixmap.toImage()
        self._magnifier_lens.set_source(qimage)
        self._magnifier_lens.show()
        self._magnifier_lens.raise_()

    def _on_viewer_mouse_left(self):
        """鼠标离开图片 → 隐藏放大镜"""
        self._magnifier_lens.hide()

    def _on_magnifier_toggled(self, checked: bool):
        """放大镜开关"""
        if not checked:
            self._magnifier_lens.hide()

    def _on_crop_region_selected(self, x: int, y: int, w: int, h: int):
        """裁剪区域框选完成 → 填充到裁剪面板"""
        panel = self._action_panels.get("crop")
        if panel:
            panel.set_region(x, y, w, h)
            # 自动切换到裁剪模式并显示面板
            self._image_toolbar.set_active("crop")

    # ============ 图像处理执行槽 ============

    def _process_image(self, operation_name: str, processor, *args):
        """通用图像处理执行：读取当前图片 → 处理 → 添加到 ImageModel"""
        import base64
        import numpy as np
        from PySide6.QtGui import QImage
        from app.image_processing.operations import np_array_to_pixmap

        pixmap = self._image_viewer.get_current_pixmap()
        if pixmap is None:
            self._status_label.setText("没有可处理的图片")
            return

        # QPixmap → numpy BGR
        qimg = pixmap.toImage().convertToFormat(QImage.Format_BGR888)
        if qimg.isNull():
            self._status_label.setText("图片格式转换失败")
            return

        w, h = qimg.width(), qimg.height()
        bpl = qimg.bytesPerLine()
        ptr = qimg.bits()
        arr = np.array(ptr, dtype=np.uint8).reshape(h, bpl)[:, :w * 3].reshape(h, w, 3).copy()

        try:
            result = processor(arr, *args)
        except Exception as e:
            self._status_label.setText(f"{operation_name}失败: {e}")
            return

        # numpy → QPixmap → Base64
        result_pixmap = np_array_to_pixmap(result)
        if result_pixmap.isNull():
            self._status_label.setText(f"{operation_name}结果转换失败")
            return

        from PySide6.QtCore import QBuffer
        qbuf = QBuffer()
        qbuf.open(QBuffer.ReadWrite)
        result_pixmap.save(qbuf, "PNG")
        b64 = base64.b64encode(qbuf.data().data()).decode("ascii")
        qbuf.close()

        self._image_model.add_image(
            data=b64,
            mime="image/png",
            code=f"// {operation_name}",
        )
        self._status_label.setText(f"{operation_name}完成")

    def _on_crop_execute(self, x: int, y: int, w: int, h: int, filename: str):
        from app.image_processing.operations import crop
        self._process_image("裁剪", crop, x, y, w, h)

    def _on_resize_execute(self, new_w: int, new_h: int, interp: str, filename: str):
        from app.image_processing.operations import resize
        self._process_image("调整大小", resize, new_w, new_h, interp)

    def _on_grayscale_execute(self, filename: str):
        from app.image_processing.operations import grayscale
        self._process_image("灰度化", grayscale)

    def _on_threshold_execute(self, thresh: int, maxval: int, filename: str):
        from app.image_processing.operations import threshold_fixed
        self._process_image("阈值化", threshold_fixed, thresh, maxval)

    def _on_adaptive_execute(self, maxval: int, method: str, block_size: int, C: int, filename: str):
        from app.image_processing.operations import adaptive_threshold
        self._process_image("自适应阈值", adaptive_threshold, maxval, method, block_size, C)

    def _on_inrange_execute(self, lower_hex: str, upper_hex: str, filename: str):
        from app.image_processing.operations import in_range

        def _parse_hex(h: str):
            h = h.strip().lstrip("#")
            if len(h) != 6:
                return None
            try:
                r = int(h[0:2], 16)
                g = int(h[2:4], 16)
                b = int(h[4:6], 16)
            except ValueError:
                return None
            return (b, g, r)  # BGR for OpenCV

        lower = _parse_hex(lower_hex)
        upper = _parse_hex(upper_hex)
        if lower is None or upper is None:
            self._status_label.setText(f"颜色格式无效，请使用 #RRGGBB：\"{lower_hex}\" \"{upper_hex}\"")
            return

        self._process_image("inRange", in_range, lower, upper)

    def _on_find_execute(self, x: int, y: int, w: int, h: int, threshold: float):
        """找图：通过 WebSocket 执行"""
        current = self._image_viewer.get_current_image()
        if current is None:
            self._status_label.setText("没有可用的模板图片")
            return

        # 获取模板图片的 Base64（懒加载）
        template_data = self._image_model.load_image_data(current.id)
        if not template_data:
            self._status_label.setText("无法读取模板图片数据")
            return

        self._on_trigger_find_image(template_data, x, y, w, h, threshold)

    def _on_color_pick(self, target: str):
        """取色模式两段式：进入/取消取色（与 Vue 版一致）"""
        panel = self._action_panels.get("inrange")
        if not panel:
            return
        if target:
            # 进入取色模式
            self._image_viewer.set_pick_mode(True)
        else:
            # 取消取色
            self._image_viewer.set_pick_mode(False)

    def _on_pixel_picked(self, x: int, y: int):
        """图片点击取色，可多次点击覆盖前次结果"""
        color = self._magnifier_lens.pixel_color
        b = color.blue()
        g = color.green()
        r = color.red()
        panel = self._action_panels.get("inrange")
        if panel:
            panel.set_picked_color(b, g, r)

    # ============ 窗口状态 ============

    def _restore_window_state(self):
        """恢复窗口大小和位置"""
        from PySide6.QtCore import QSettings
        settings = QSettings("ai-autojs", "ai-autojs")
        geo = settings.value("window/geometry")
        if geo:
            self.restoreGeometry(geo)
        state = settings.value("window/state")
        if state:
            self.restoreState(state)

    def closeEvent(self, event):
        """窗口关闭时清理并保存状态"""
        from PySide6.QtCore import QSettings
        settings = QSettings("ai-autojs", "ai-autojs")
        settings.setValue("window/geometry", self.saveGeometry())
        settings.setValue("window/state", self.saveState())

        self._ws_client.disconnect()
        event.accept()

    def keyPressEvent(self, event: QKeyEvent):
        """全局快捷键"""
        # Ctrl+Enter 在 CodeEditor 中已处理
        super().keyPressEvent(event)
