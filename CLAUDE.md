# AI-AutoJS 助手

基于 Vue 3 + TypeScript + Element Plus 的 AutoJS6 WebSocket 远程代码执行工具。

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
    │   └── useHistoryStore.ts     # 执行历史（localStorage 持久化，上限200条）
    ├── composables/               # Composition API hooks
    │   ├── useWebSocket.ts        # WebSocket 生命周期（连接/发送/30s心跳/30s执行超时）
    │   └── useAutoReconnect.ts    # 指数退避 + 随机抖动 自动重连
    ├── types/
    │   └── autojs.ts              # 消息协议类型定义 + 默认配置
    ├── utils/
    │   └── storage.ts             # localStorage 封装（JSON序列化 + QuotaExceededError处理）
    ├── views/
    │   └── HomeView.vue           # 主工作台，组合所有组件，实例化 useWebSocket
    ├── components/
    │   ├── layout/AppHeader.vue
    │   ├── connection/            # ConnectionPanel, ConnectionBadge
    │   ├── editor/                # CodeEditor (textarea + 行号标尺), EditorToolbar
    │   ├── result/                # ResultPanel, ResultItem (文本/图片/HexDump)
    │   └── history/               # HistoryDrawer (el-drawer), HistoryItem
    └── styles/
        └── variables.css          # CSS 自定义属性
```

## WebSocket 协议（端口 9318）

- 发送：`{"type":"command","data":"<js_code>"}`
- 返回：`{"type":"result","data":"<output>","status":"success|error","dataType":"text|base64","mime":"..."}`
- 心跳：`{"type":"ping"}` / `{"type":"pong"}`（文本帧，非 WebSocket opcode ping/pong）
- 二进制结果：Base64 编码 + `dataType:"base64"` + `mime` 字段
- 服务端支持返回值类型：字符串/数字/对象（text），Bitmap/byte[]/ByteArrayInputStream/File（base64）

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

## 常用代码模板

### 截图
```js
(function () {
    if (!requestScreenCapture()) return "请求截图失败";
    let img = images.captureScreen();
    let arr = images.toBytes(img);
    img.recycle();
    return arr;
}())
```

### 区域剪切
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
| `executeCode` | `eval()` 执行 JS 代码，劫持 `console.log`，检测二进制返回值 |
| `handleClient` | 单连接生命周期：握手 → 读帧 → 执行 → 写帧 |
| `acceptLoop` | 主线程阻塞 accept()，每个客户端 `threads.start()` 处理 |
| `createFloatyWindow` | `floaty.window()` 悬浮按钮（停止服务 + 连接数显示） |

## Rhino 引擎兼容性注意事项

AutoJS6 基于 Mozilla Rhino（Java 平台的 JS 引擎），以下写法不兼容：

| ❌ 不可用 | ✅ 替代方案 |
|---|---|
| `e instanceof java.net.SocketTimeoutException` | `String(e).indexOf('SocketTimeoutException') >= 0` |
| `java.lang.reflect.Array.newInstance(...).constructor(jsArray)` | 逐个赋值 `byteArray[k] = new java.lang.Integer(val).byteValue()` |
| `new java.lang.String(text).getBytes('UTF-8')` 中文字符 | 正常可用，UTF-8 编码正确 |
| `BufferedReader` 读取握手头 | 逐字节读到 `\r\n\r\n` 分隔符，避免缓冲破坏后续帧数据 |

**Java byte 赋值陷阱**：JS 数字是 unsigned（0-255），Java byte 是 signed（-128~127）。值超过 127 时必须用 `new java.lang.Integer(n).byteValue()` 做截断转换，否则抛 `Cannot convert 129 to java.lang.Byte`。

## 编码约定

- 中文代码注释，英文标识符
- Vue SFC 使用 `<script setup lang="ts">`
- Pinia store 使用 composition API 风格
- WebSocket 相关逻辑集中在 `composables/useWebSocket.ts`，组件通过 store 读取状态
- 子组件通过 Pinia store 获取状态，不通过 props 跨层传递
- CSS 变量统一定义在 `styles/variables.css`
