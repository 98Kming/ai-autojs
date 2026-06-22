# AI-AutoJS 助手

基于 Vue 3 + TypeScript + Element Plus 的 AutoJS6 WebSocket 远程代码执行工具，支持截图管理和图片处理。同时提供 Python / PySide6 桌面版（`py/`），取消浏览器限制。

## 技术栈

| 层 | 技术 |
|---|---|
| 前端框架 | Vue 3 (Composition API) + TypeScript |
| UI 组件库 | Element Plus + @element-plus/icons-vue |
| 状态管理 | Pinia (composition style) |
| 路由 | Vue Router 4 |
| 构建工具 | Vite 5 |
| 通信 | 浏览器原生 WebSocket |

**手机端：** AutoJS6（Rhino 引擎），`server/autojs-server.js` WebSocket 服务脚本

## 项目结构

```
├── server/autojs-server.js       # AutoJS6 手机端 WebSocket 服务脚本
├── .claude/autojs-image/         # autojs-image 技能（截图/图像处理参考）
│   ├── skill.md
│   └── resources/image.html      # AutoJS6 images 模块文档
└── src/
    ├── main.ts
    ├── App.vue
    ├── router/index.ts
    ├── stores/                    # Pinia stores
    │   ├── useWebSocketStore.ts   # 连接状态 + 配置 + 历史抽屉开关
    │   ├── useCodeStore.ts        # 编辑器内容 + 执行状态
    │   ├── useHistoryStore.ts     # 执行历史（localStorage 持久化，上限200条）
    │   └── useImageStore.ts       # 截图列表（localStorage 显式持久化，上限20张，超4MB弹确认裁剪）
    ├── composables/               # Composition API hooks
    │   ├── useWebSocket.ts        # WebSocket 生命周期（连接/发送/30s心跳/120s执行超时）
    │   └── useAutoReconnect.ts    # 指数退避 + 随机抖动 自动重连
    ├── types/
    │   └── autojs.ts              # 消息协议类型 + 默认配置 + SCREENSHOT_TEMPLATE 常量
    ├── utils/
    │   └── storage.ts             # localStorage 封装（JSON序列化 + QuotaExceededError处理）
    ├── views/
    │   └── HomeView.vue           # 主工作台，顶层 tabs 切换「代码执行」/「图片处理」
    ├── components/
    │   ├── layout/AppHeader.vue
    │   ├── connection/            # ConnectionPanel, ConnectionBadge
    │   ├── editor/                # CodeEditor (textarea + 行号标尺), EditorToolbar
    │   ├── result/                # ResultPanel, ResultItem, ImagePanel, ImageCard
    │   └── history/               # HistoryDrawer (el-drawer), HistoryItem
    └── styles/
        └── variables.css          # CSS 自定义属性
```

## UI 布局

```
┌──────────────────────────────────────────────────────────┐
│ AppHeader  [Logo]                     [状态灯] [历史]     │
├──────────────────────────────────────────────────────────┤
│ ConnectionPanel  [ws://127.0.0.1:9318] [连接] [断开]      │
├──────────────────────────────────────────────────────────┤
│ [ 代码执行 ]  [ 图片处理 (N) ]              ← 顶层 tabs   │
├──────────────────────────┬───────────────────────────────┤
│ EditorToolbar            │ ResultPanel                   │
│ [格式化][清空][运行]      │ ResultItem × N                │
│ CodeEditor               │                               │
└──────────────────────────┴───────────────────────────────┘
```

图片处理 tab 为三栏布局（工具 | 缩略图列表 | 大图展示）。

## WebSocket 协议（端口 9318）

- 发送：`{"type":"command","data":"<js_code>"}`
- 心跳：`{"type":"ping"}` / `{"type":"pong"}`（文本帧，非 WebSocket opcode ping/pong）

### 结果传输

| 数据类型 | 协议 | 说明 |
|---|---|---|
| 文本 | 单文本帧 `{"type":"result","data":"...","dataType":"text"}` | 字符串/数字/对象输出 |
| 二进制（旧） | 单文本帧 `dataType:"base64"` + Base64 编码 | 兼容模式 |
| 二进制（新） | 元数据文本帧 `dataType:"binary"` + 紧跟二进制 WebSocket 帧（opcode=0x2） | 省去 Base64 编码，减少 ~25% 传输量 |

传输优化：
- 截图使用 JPEG 格式（`images.toBytes(img, 'jpg')`），文件大小减少 ~90%
- 二进制帧传输原始 byte[]，消除 Base64 33% 膨胀
- 综合 JPEG + 二进制帧，端到端传输量约为原始 PNG Base64 的 **5-10%**
- `ArrayBuffer` → `btoa()` 转 Base64 供下游消费，组件层无感知
- `pendingBinaryMeta` 超时与执行超时同步（120s），防止大图传输中途被清空

### 二进制帧流程

```
服务端 → 前端: {"type":"result","status":"success","dataType":"binary","mime":"image/jpeg","size":12345}
服务端 → 前端: [WebSocket 二进制帧, opcode=0x2, payload=原始 byte[]]
```

### 编码修复

`decodeFrame` 中 `payloadString` 改用 `new java.lang.String(byte[], Charset.forName('UTF-8'))`，解决中文逐字节 `String.fromCharCode` 导致的乱码问题。

### 兼容性

旧客户端收到的 `dataType:"binary"` 文本帧会被忽略，二进制帧因默认 binaryType=Blob 也不会触发正确解析——安全退化，无报错。

### 服务端检测

- Java `byte[]` 通过 `getClass().getName() === '[B'` 检测，`images.toBytes()` 输出自动识别
- 支持返回值类型：字符串/数字/对象（text），Bitmap/byte[]/ByteArrayInputStream/File（base64/binary）

## 开发命令

```bash
npm install
npm run dev        # 启动开发服务器 → http://localhost:3000
npm run build      # 生产构建
npm run preview    # 预览生产构建
```

## 使用方式

### 真机 / MuMu 模拟器

1. AutoJS6 加载 `server/autojs-server.js` 并运行
2. **真机**：PC 前端输入手机 WiFi IP → 连接
3. **MuMu 模拟器**（NAT 网络，需 ADB 端口转发）：
   ```bash
   adb connect 127.0.0.1:7555
   adb -s 127.0.0.1:7555 forward tcp:9318 tcp:9318
   ```
   前端地址填 `127.0.0.1`
4. 连接成功后，悬浮按钮显示 "已连接 1 台设备"
5. 编写代码，Ctrl+Enter 运行，结果实时展示

### 截图功能

1. 切换到「图片处理」tab
2. 点击左侧工具栏「📷 截图」按钮
3. 自动执行截图，完成后图片出现在缩略图列表，右侧大图预览
4. 支持下载、删除，页面刷新后图片从 localStorage 恢复（最多保留 20 张 / 4MB）

### 执行耗时

- 每次代码执行自动记录耗时，显示在结果头部和历史记录中
- 格式：`<1000ms` 显示为 `45ms`，≥1000ms 显示为 `1.2s`
- 耗时数据持久化在历史记录的 `durationMs` 字段中

## 常用代码模板

### 截图（已内置到「图片处理」tab）
```js
(function () {
    if (!requestScreenCapture()) return "请求截图失败";
    let img = images.captureScreen();
    let arr = images.toBytes(img);
    img.recycle();
    return arr;
}())
```

### 区域剪切（已内置到「图片处理」tab 剪裁模式）

```js
// 已替换为前端 Canvas 裁剪，无需 WebSocket 执行
// 用户 Ctrl+拖拽框选区域后直接在前端完成剪切
```

### AutoJS 区域剪切模板（需要服务端执行时使用）
```js
(function () {
    if (!requestScreenCapture()) return "请求截图失败";
    let img = images.captureScreen();
    let clip = images.clip(img, x, y, w, h);  // 修改 x/y/w/h
    img.recycle();
    let arr = images.toBytes(clip);
    clip.recycle();
    return arr;
}())
```

## 服务端架构 (autojs-server.js)

| 模块 | 职责 |
|---|---|
| `performHandshake` | 逐字节读取 HTTP Upgrade 请求，SHA-1+Base64 计算 Accept Key，返回 101 |
| `decodeFrame` | 解析 WebSocket 帧（处理 client→server 的 mask XOR） |
| `encodeFrame` | 构建 WebSocket 帧为 Java byte[]（不 mask，server→client） |
| `isJavaByteArray` | 通过 `getClass().getName() === '[B'` 检测 Java 原生 byte[] |
| `executeCode` | `eval()` 执行 JS 代码，劫持 `console.log`，检测二进制返回值 |
| `handleClient` | 单连接生命周期：握手 → 读帧（command/ping/close） → 执行 → 写帧 |
| `acceptLoop` | 主线程阻塞 accept()，每个客户端 `threads.start()` 处理 |
| `createFloatyWindow` | `floaty.window()` 悬浮按钮（停止服务 + 连接数显示） |

## Rhino 引擎兼容性注意事项

AutoJS6 基于 Mozilla Rhino（Java 平台的 JS 引擎），以下写法不兼容：

| ❌ 不可用 | ✅ 替代方案 |
|---|---|
| `e instanceof java.net.SocketTimeoutException` | `String(e).indexOf('SocketTimeoutException') >= 0` |
| `e instanceof java.net.BindException` | `String(e).indexOf('BindException') >= 0` |
| `java.lang.reflect.Array.newInstance(...).constructor(jsArray)` | 逐个赋值 `byteArray[k] = new java.lang.Integer(val).byteValue()` |
| `BufferedReader` 读取握手头 | 逐字节读到 `\r\n\r\n` 分隔符，避免缓冲破坏后续帧数据 |
| `value instanceof byte[]`（检测 Java 数组类型） | `isJavaByteArray(value)` → `getClass().getName() === '[B'` |

**Java byte 赋值陷阱**：JS 数字是 unsigned（0-255），Java byte 是 signed（-128~127）。值超过 127 时必须用 `new java.lang.Integer(n).byteValue()` 做截断转换，否则抛 `Cannot convert 129 to java.lang.Byte`。

## 图片查看器功能

图片展示区（`ImagePanel.vue`）集成三个功能模块：

### 放大镜

| 特性 | 说明 |
|---|---|
| 触发方式 | 勾选「🔍 放大镜」复选框，默认开启 |
| 镜片 | 180×180px 正方形，10x 放大，白色边框 + 阴影 |
| 像素网格 | `repeating-linear-gradient` 虚线网格，间距 10px（对应原图 1px），中灰色 |
| 坐标信息 | 镜片底部显示原图像素坐标 `(x, y)` |
| 颜色采样 | Canvas `getImageData` 实时取色，显示色块 + 16 进制值 |
| 鼠标指示 | 镜片中心红色十字准星，标识当前像素位置 |
| 方向键漫游 | ↑↓←→ 每次精确移动 1 图片像素，浮点虚拟光标亚像素累积，任意缩放比精确 |
| 边缘翻转 | 镜片靠近 viewer 边缘时自动反向偏移，避免溢出 |

### 缩放平移

| 操作 | 效果 |
|---|---|
| 滚轮 | 以鼠标位置为中心缩放，0.2x ~ 10x，步进 0.2 |
| 拖拽 | 图片超出可视区时可拖拽平移（cursor grab/grabbing） |
| 双击 | 重置缩放/平移恢复适配视图 |
| 切换图片 | 自动重置 |
| 缩放提示 | 右上角显示当前缩放百分比 |

### 剪切

| 特性 | 说明 |
|---|---|
| 触发方式 | 点击工具栏「✂️ 剪裁」按钮进入剪切模式 |
| 框选 | Ctrl + 拖拽在图片上选取矩形区域（蓝色虚线 + 半透明填充） |
| 参数面板 | 右下角 x/y/w/h 数值输入框，可手动编辑，选区实时跟随 |
| 文件名 | 默认 `_{x1}_{y1}_{x2}_{y2}.png`，可编辑 |
| 执行 | 前端 Canvas 裁剪，结果直接加入图片列表（无需 WebSocket） |
| 放大镜 | 框选时放大镜保持可见，辅助精确定位 |

### 调整大小

| 特性 | 说明 |
|---|---|
| 触发方式 | 点击工具栏「📐 调整」按钮 |
| 引擎 | OpenCV.js（CDN 按需加载，首次后缓存），含 Canvas 回退 |
| 插值方式 | 最近邻 / 双线性 / 双三次 / Lanczos4 / 区域 |
| 比例锁定 | checkbox 勾选时修改宽自动计算高，反之亦然 |
| 文件命名 | 默认 `_{W}_{H}.png`，可编辑 |
| 执行 | OpenCV `cv.resize()` 处理，结果加入图片列表 |

### 灰度化

一键执行，将彩色图片转为灰度图。文件名 `_gray.png`。

### 阈值化

弹面板调参：阈值(0-255) + 最大值(0-255)，`cv.threshold()` 二值化。文件名可编辑。

### 自适应阈值化

弹面板调参：最大值、块大小(3-99)、C值(-50~50)、方法(高斯/均值)，`cv.adaptiveThreshold()`。文件名可编辑。

### 二值化 (inRange)

颜色范围选取，参数输入与 Vue 版一致。

| 特性 | 说明 |
|---|---|
| 参数格式 | `#RRGGBB` 十六进制输入（非 BGR 分量），与 Vue 版一致 |
| 默认值 | 下界 `#FF0000`（红），上界 `#FFFFFF`（白） |
| 取色流程 | 点击「取色」→ 按钮变「取色中」→ 点击图片（可多次，后次覆盖前次）→ 再次点击按钮退出 |
| 执行 | `cv.inRange()` 生成二值掩码，文件名可编辑 |

### 图片查找 (findImage)

| 特性 | 说明 |
|---|---|
| 触发方式 | 点击工具栏「🔍 找图」按钮 |
| 模板 | 当前选中图片，通过 `images.fromBase64()` 在手机端解码 |
| 搜索区域 | 从剪切坐标自动扩展（x ±50px, y ±1/10 屏高），可手动编辑 |
| 阈值 | 0~1 可调，默认 0.9 |
| 执行 | WebSocket 发送代码 → 手机 `images.findImage()` → 返回坐标 |

### 切换图片行为

- 缩放/平移 — 重置（适配新图片尺寸）
- 剪切选区 — 重置（选区与图片绑定）
- 调整大小面板 — 保持打开，尺寸自动同步到新图片
- 灰度/阈值/自适应/inRange 面板 — 保持打开，参数不变

## 编码约定

- 中文代码注释，英文标识符
- Vue SFC 使用 `<script setup lang="ts">`
- Pinia store 使用 composition API 风格
- WebSocket 相关逻辑集中在 `composables/useWebSocket.ts`，组件通过 store 读取状态
- 子组件通过 Pinia store 获取状态，不通过 props 跨层传递
- CSS 变量统一定义在 `styles/variables.css`
- 公共代码模板常量定义在 `types/autojs.ts`

## Python 版

Python 桌面 GUI 移植版，功能等齐 Vue 版，取消浏览器限制。

### 技术栈

| 层 | 技术 |
|---|---|
| GUI 框架 | PySide6 >= 6.5（Qt for Python，LGPL） |
| WebSocket | QWebSocket（PySide6 内置，事件循环集成） |
| 图像处理 | opencv-python-headless >= 4.8 + Pillow 回退 |
| 状态管理 | QObject + Signal（对应 Pinia store） |
| 持久化 | JSON 文件（QStandardPaths::AppDataLocation） |
| 包管理 | uv |

### 项目结构

```
py/
├── main.py                          # QApplication 入口
├── pyproject.toml                   # uv 项目配置
│
├── app/
│   ├── main_window.py               # 主窗口：信号接线、标签页、快捷键
│   │
│   ├── protocol/
│   │   ├── messages.py              # @dataclass 消息类型、协议常量
│   │   └── templates.py            # JS 代码模板（截图、找图）
│   │
│   ├── models/                      # 状态管理（QObject + Signal）
│   │   ├── connection.py            # 连接配置 + 状态
│   │   ├── code_editor.py           # 编辑器内容 + 执行状态
│   │   ├── history.py              # 执行历史（JSON 持久化，上限 500）
│   │   └── images.py               # 图片列表（文件系统持久化，无上限）
│   │
│   ├── network/
│   │   ├── ws_client.py             # QWebSocket 生命周期、二进制帧、心跳、超时
│   │   └── reconnect.py            # 指数退避 + 随机抖动重连
│   │
│   ├── persistence/
│   │   └── config_store.py          # JSON 文件读写 (config/history/images)
│   │
│   ├── image_processing/
│   │   ├── cv_manager.py            # OpenCV 可用性检测、惰性导入
│   │   └── operations.py           # 灰度/阈值/自适应/inRange/缩放 纯函数
│   │
│   └── widgets/
│       ├── styles.py                # 全局 QSS 样式
│       ├── header_bar.py            # 顶栏 + 状态灯
│       ├── status_dot.py            # 自绘脉冲动画指示灯
│       ├── connection_bar.py        # 主机/端口 + 连接/断开
│       ├── code_editor.py           # QPlainTextEdit + 行号标尺
│       ├── editor_toolbar.py        # 格式化/清空/运行
│       ├── result_panel.py          # 结果列表容器
│       ├── result_item.py           # 文本/hex/图片 三种展示
│       ├── history_drawer.py        # 右侧滑出历史面板
│       ├── history_item.py          # 单条历史卡片
│       ├── image_toolbar.py         # 左侧竖排工具按钮
│       ├── image_list_panel.py      # 缩略图列表
│       ├── image_thumbnail.py       # 72x72 缩略图卡片
│       ├── image_viewer.py          # QGraphicsView 缩放/平移/叠加
│       ├── magnifier_lens.py        # 10x 放大镜（像素网格+十字线+取色）
│       ├── crop_overlay.py          # 裁剪框选覆盖层
│       └── action_panels/           # 图像处理操作面板
│           ├── base_panel.py        # 浮动面板基类
│           ├── crop_panel.py        # 裁剪参数
│           ├── resize_panel.py      # 缩放参数
│           ├── grayscale_panel.py   # 灰度化
│           ├── threshold_panel.py   # 固定阈值
│           ├── adaptive_panel.py    # 自适应阈值
│           ├── inrange_panel.py     # 颜色范围+取色器
│           └── find_image_panel.py  # 模板匹配
```

### Model → Widget 信号流

```
ConnectionModel.status_changed → StatusDot.set_status, ConnectionBar.set_connected
CodeEditorModel.executing_changed → EditorToolbar.set_executing
CodeEditorModel.result_received → ResultPanel.add_result
HistoryModel.entries_changed → HistoryDrawer.refresh
ImageModel.images_changed → ImageListPanel.refresh + tab label
ImageModel.image_added → ImageViewer.load_image
```

### 图片持久化机制

```
<AppDataLocation>/ai-autojs/
├── config.json          # 连接配置
├── history.json         # 执行历史
├── images.json          # 图片元数据索引 [{id, mime, timestamp, code, file}]
└── images/              # 实际图片文件
    ├── <id>.png
    └── <id>.jpg
```

- 图片存为实际 PNG/JPEG 文件，不在 JSON 中塞 Base64
- `ImageModel.load_image_data(id)` 懒加载 Base64 到内存
- 无数量/大小上限，仅受磁盘空间限制

### 与 Vue 版的关键差异

| 特性 | Vue 版 | Python 版 |
|---|---|---|
| 图片数量上限 | 20 | **无限制** |
| 存储容量上限 | 4MB (localStorage) | **无限制** |
| 图片持久化 | localStorage + 容量告警 | 文件系统（JSON 索引 + 实际文件） |
| 历史记录上限 | 200 | 500 |
| 超容量对话框 | 有 | **移除** |
| 图像处理引擎 | OpenCV.js CDN 动态加载 | pip 本地 opencv-python-headless |
| 缩放平移 | CSS transform | QGraphicsView 原生 |
| Base64 转换 | FileReader 异步 | QByteArray.toBase64 同步 |

### 开发命令

```bash
cd py
uv run python main.py              # 直接运行
uv tool install . && ai-autojs     # 安装为命令行工具
```

### 编码约定

- 中文注释，英文标识符
- Model 层：QObject 子类，通过 Signal 通知 UI（对应 Pinia store）
- Widget 层：纯 UI，通过 Signal/Slot 与 Model 解耦
- `from __future__ import annotations` 在所有文件顶部（兼容 Python 3.8 `X | None` 语法）
- QSS 样式集中在 `widgets/styles.py`
- WebSocket 逻辑集中在 `network/ws_client.py`
- 图像处理纯函数在 `image_processing/operations.py`，优先 OpenCV，不可用时 Pillow 回退
