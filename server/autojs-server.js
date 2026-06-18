/**
 * AutoJS6 WebSocket 服务端脚本
 * 运行在 Android 手机上，接收 PC 前端发来的代码并执行
 *
 * 使用方式：
 * 1. 在 AutoJS6 应用中打开此脚本
 * 2. 点击运行，悬浮按钮出现
 * 3. 点击悬浮按钮可停止服务
 */

'use strict';

const PORT = 9318;
const MAX_CONNECTIONS = 5;
const EXECUTION_TIMEOUT_MS = 30000;
const HEARTBEAT_TIMEOUT_MS = 60000;

// ===== 全局状态 =====
var serverSocket = null;
var isRunning = false;
var activeClients = [];      // { socket, thread, inputStream, outputStream }
var floatyWindow = null;

// ===== WebSocket 常量 =====
var WS_GUID = '258EAFA5-E914-47DA-95CA-C5AB0DC85B11';
var OPCODE_TEXT = 0x1;
var OPCODE_BINARY = 0x2;
var OPCODE_CLOSE = 0x8;
var OPCODE_PING = 0x9;
var OPCODE_PONG = 0xA;

// ===== 工具函数：生成 UUID =====
function generateUUID() {
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function (c) {
        var r = Math.random() * 16 | 0;
        var v = c === 'x' ? r : (r & 0x3 | 0x8);
        return v.toString(16);
    });
}

// ===== 工具函数：日志 =====
function log(msg) {
    var ts = new java.text.SimpleDateFormat('HH:mm:ss').format(new java.util.Date());
    console.log('[' + ts + '] ' + msg);
    toast(msg);
}

// ===== WebSocket 握手处理（逐字节读取，避免 BufferedReader 缓冲破坏帧数据） =====
function performHandshake(inputStream, outputStream) {
    var headerBytes = [];
    var b;
    var endMarker = [13, 10, 13, 10]; // \r\n\r\n
    var matchIdx = 0;

    // 逐字节读取直到遇到 \r\n\r\n（HTTP 头结束标记）
    while (matchIdx < 4) {
        b = inputStream.read();
        if (b < 0) {
            throw new Error('客户端在握手阶段断开');
        }
        headerBytes.push(b);
        if (b === endMarker[matchIdx]) {
            matchIdx++;
        } else {
            matchIdx = 0;
        }
        // 防止超长头部
        if (headerBytes.length > 8192) {
            throw new Error('HTTP 请求头过长');
        }
    }

    // 将字节数组转为字符串
    var headerStr = '';
    for (var i = 0; i < headerBytes.length; i++) {
        headerStr += String.fromCharCode(headerBytes[i]);
    }

    // 提取 Sec-WebSocket-Key
    var lines = headerStr.split('\r\n');
    var wsKey = null;
    for (var j = 0; j < lines.length; j++) {
        var line = lines[j].trim();
        if (line.indexOf('Sec-WebSocket-Key:') === 0) {
            wsKey = line.substring('Sec-WebSocket-Key:'.length).trim();
            break;
        }
    }

    if (!wsKey) {
        throw new Error('缺少 Sec-WebSocket-Key 头部');
    }

    // 计算 Accept Key: SHA-1(key + GUID) -> Base64
    var md = java.security.MessageDigest.getInstance('SHA-1');
    var acceptKey = wsKey + WS_GUID;
    var hash = md.digest(new java.lang.String(acceptKey).getBytes('UTF-8'));
    var encodedKey = android.util.Base64.encodeToString(hash, android.util.Base64.NO_WRAP);

    // 发送 101 Switching Protocols 响应
    var response = 'HTTP/1.1 101 Switching Protocols\r\n' +
        'Upgrade: websocket\r\n' +
        'Connection: Upgrade\r\n' +
        'Sec-WebSocket-Accept: ' + encodedKey + '\r\n' +
        '\r\n';
    outputStream.write(new java.lang.String(response).getBytes('UTF-8'));
    outputStream.flush();

    log('握手完成');
}

// ===== WebSocket 帧解码（客户端→服务端，需要 unmask） =====
function decodeFrame(inputStream) {
    var buf = [];
    var b;

    // 读取第一个字节
    b = inputStream.read();
    if (b < 0) return null;
    var fin = (b >> 7) & 1;
    var opcode = b & 0xF;

    // 读取第二个字节
    b = inputStream.read();
    if (b < 0) return null;
    var masked = (b >> 7) & 1;
    var payloadLen = b & 0x7F;

    // 扩展长度
    if (payloadLen === 126) {
        payloadLen = ((inputStream.read() & 0xFF) << 8) | (inputStream.read() & 0xFF);
    } else if (payloadLen === 127) {
        // 64位长度，高4字节忽略（实际使用不超过2GB）
        for (var i = 0; i < 4; i++) inputStream.read();
        payloadLen = 0;
        for (var j = 0; j < 4; j++) {
            payloadLen = (payloadLen << 8) | (inputStream.read() & 0xFF);
        }
    }

    // 读取 mask key
    var maskKey = null;
    if (masked) {
        maskKey = [];
        for (var k = 0; k < 4; k++) {
            maskKey.push(inputStream.read() & 0xFF);
        }
    }

    // 读取 payload
    var payload = [];
    for (var n = 0; n < payloadLen; n++) {
        b = inputStream.read() & 0xFF;
        if (maskKey) {
            b = b ^ maskKey[n % 4];
        }
        payload.push(b);
    }

    return {
        fin: fin,
        opcode: opcode,
        payload: payload,
        payloadString: function() {
            var arr = java.lang.reflect.Array.newInstance(java.lang.Byte.TYPE, payload.length);
            for (var i = 0; i < payload.length; i++) arr[i] = new java.lang.Integer(payload[i]).byteValue();
            return new java.lang.String(arr, java.nio.charset.Charset.forName('UTF-8'));
        }()
    };
}

// ===== WebSocket 帧编码（服务端→客户端，不 mask） =====
// payloadBytes 为 Java byte[] 时使用 ByteArrayOutputStream 避免逐字节 JS 循环
function encodeFrame(opcode, payloadBytes) {
    var len = payloadBytes.length;
    var headerSize = len < 126 ? 2 : (len < 65536 ? 4 : 10);
    var baos = new java.io.ByteArrayOutputStream(headerSize + len);

    // 第一个字节：FIN + opcode
    baos.write(0x80 | opcode);

    // 长度编码
    if (len < 126) {
        baos.write(len);
    } else if (len < 65536) {
        baos.write(126);
        baos.write((len >> 8) & 0xFF);
        baos.write(len & 0xFF);
    } else {
        baos.write(127);
        for (var i = 0; i < 4; i++) baos.write(0);
        baos.write((len >> 24) & 0xFF);
        baos.write((len >> 16) & 0xFF);
        baos.write((len >> 8) & 0xFF);
        baos.write(len & 0xFF);
    }

    // payload（服务端不需 mask）— 直接写入 Java byte[]，零 JS 循环
    baos.write(payloadBytes, 0, len);

    return baos.toByteArray();
}

// ===== 发送文本帧 =====
function sendTextFrame(outputStream, text) {
    var bytes = new java.lang.String(text).getBytes('UTF-8');
    var frame = encodeFrame(OPCODE_TEXT, bytes);
    outputStream.write(frame);
    outputStream.flush();
}

// ===== 发送二进制帧 =====
function sendBinaryFrame(outputStream, javaBytes) {
    var frame = encodeFrame(OPCODE_BINARY, javaBytes);
    outputStream.write(frame);
    outputStream.flush();
}

// ===== 发送 Pong 帧 =====
function sendPong(outputStream, pingPayload) {
    var frame = encodeFrame(OPCODE_PONG, pingPayload);
    outputStream.write(frame);
    outputStream.flush();
}

// ===== 发送 Close 帧 =====
function sendCloseFrame(outputStream) {
    var frame = encodeFrame(OPCODE_CLOSE, []);
    try {
        outputStream.write(frame);
        outputStream.flush();
    } catch (e) {
        // 连接可能已断开
    }
}

// ===== 检测 Java byte[] 数组 =====
function isJavaByteArray(value) {
    try {
        return value != null && value.getClass && value.getClass().getName() === '[B';
    } catch (e) {
        return false;
    }
}

// ===== 检测二进制结果 =====
function isBinaryResult(value) {
    if (value === null || value === undefined) return false;
    if (value instanceof android.graphics.Bitmap) return true;
    if (value instanceof java.io.ByteArrayInputStream) return true;
    if (value instanceof java.io.File) return true;
    if (isJavaByteArray(value)) return true;
    // 检测 JavaScript number 数组（byte 范围）
    if (Array.isArray(value) && value.length > 0 &&
        value.every(function (v) { return typeof v === 'number' && v >= 0 && v <= 255; })) {
        return true;
    }
    return false;
}

// ===== 转为 byte[] =====
function toByteArray(value) {
    // Java 原生 byte[] — 直接返回
    if (isJavaByteArray(value)) return value;
    if (value instanceof android.graphics.Bitmap) {
        var stream = new java.io.ByteArrayOutputStream();
        value.compress(android.graphics.Bitmap.CompressFormat.PNG, 100, stream);
        return stream.toByteArray();
    }
    if (value instanceof java.io.ByteArrayInputStream) {
        var buf = java.lang.reflect.Array.newInstance(java.lang.Byte.TYPE, value.available());
        value.read(buf);
        return buf;
    }
    if (value instanceof java.io.File) {
        var fis = new java.io.FileInputStream(value);
        var fileBuf = java.lang.reflect.Array.newInstance(java.lang.Byte.TYPE, value.length());
        fis.read(fileBuf);
        fis.close();
        return fileBuf;
    }
    if (Array.isArray(value)) {
        var arrBuf = java.lang.reflect.Array.newInstance(java.lang.Byte.TYPE, value.length);
        for (var i = 0; i < value.length; i++) arrBuf[i] = value[i];
        return arrBuf;
    }
    return null;
}

// ===== 检测 MIME 类型 =====
function detectMime(value) {
    if (value instanceof android.graphics.Bitmap) return 'image/png';
    // Java byte[] — 通过魔数检测实际格式（PNG/JPEG/BMP/GIF）
    if (isJavaByteArray(value) && value.length >= 4) {
        var b0 = value[0] & 0xFF, b1 = value[1] & 0xFF, b2 = value[2] & 0xFF, b3 = value[3] & 0xFF;
        if (b0 === 0xFF && b1 === 0xD8 && b2 === 0xFF) return 'image/jpeg';
        if (b0 === 0x89 && b1 === 0x50 && b2 === 0x4E && b3 === 0x47) return 'image/png';
        if (b0 === 0x42 && b1 === 0x4D) return 'image/bmp';
        if (b0 === 0x47 && b1 === 0x49 && b2 === 0x46) return 'image/gif';
        return 'image/png'; // 默认 fallback
    }
    if (value instanceof java.io.File) {
        var name = value.getName().toLowerCase();
        if (name.endsWith('.png')) return 'image/png';
        if (name.endsWith('.jpg') || name.endsWith('.jpeg')) return 'image/jpeg';
        if (name.endsWith('.txt')) return 'text/plain';
        if (name.endsWith('.json')) return 'application/json';
        if (name.endsWith('.html')) return 'text/html';
    }
    return 'application/octet-stream';
}

// ===== 代码执行（二进制结果返回对象，元数据与数据分离） =====
function executeCode(code) {
    var logs = [];
    var originalLog = console.log;

    console.log = function () {
        var parts = [];
        for (var i = 0; i < arguments.length; i++) {
            parts.push(String(arguments[i]));
        }
        logs.push(parts.join(' '));
    };

    try {
        var result = eval(code);
        console.log = originalLog;

        // 二进制结果：返回元数据 + 原始 byte[]
        if (isBinaryResult(result)) {
            var bytes = toByteArray(result);
            var mime = detectMime(result);
            return {
                isBinary: true,
                metaJson: JSON.stringify({
                    type: 'result',
                    status: 'success',
                    dataType: 'binary',
                    mime: mime,
                    size: bytes.length
                }),
                bytes: bytes
            };
        }

        // 文本结果
        var output;
        if (logs.length > 0) {
            output = logs.join('\n');
        } else {
            output = result !== undefined ? String(result) : '';
        }
        return {
            isBinary: false,
            textJson: JSON.stringify({
                type: 'result',
                status: 'success',
                dataType: 'text',
                data: output
            })
        };

    } catch (e) {
        console.log = originalLog;
        return {
            isBinary: false,
            textJson: JSON.stringify({
                type: 'result',
                status: 'error',
                dataType: 'text',
                data: e.message + '\n' + (e.stack || '')
            })
        };
    }
}

// ===== 客户端处理线程 =====
function handleClient(socket) {
    var clientId = generateUUID();
    var inputStream = socket.getInputStream();
    var outputStream = socket.getOutputStream();
    var clientRecord = {
        id: clientId,
        socket: socket,
        inputStream: inputStream,
        outputStream: outputStream
    };

    activeClients.push(clientRecord);
    log('新连接: ' + clientId + ' (当前: ' + activeClients.length + ' 台)');
    try {
        // WebSocket 握手
        performHandshake(inputStream, outputStream);

        // 循环读取帧
        while (isRunning) {
            var frame = decodeFrame(inputStream);
            if (!frame) break; // 连接关闭

            if (frame.opcode === OPCODE_TEXT) {
                // 文本帧：解析 JSON 消息
                var msg;
                try {
                    msg = JSON.parse(frame.payloadString);
                } catch (e) {
                    log('JSON 解析失败: ' + e.message);
                    continue;
                }

                if (msg.type === 'command') {
                    log('执行代码 (来自 ' + clientId + ')...');
                    var execResult = executeCode(msg.data);
                    if (execResult.isBinary) {
                        sendTextFrame(outputStream, execResult.metaJson);
                        sendBinaryFrame(outputStream, execResult.bytes);
                    } else {
                        sendTextFrame(outputStream, execResult.textJson);
                    }
                } else if (msg.type === 'ping') {
                    // 心跳：回复 pong
                    sendTextFrame(outputStream, JSON.stringify({ type: 'pong' }));
                }
                // 其他未知类型静默忽略
            } else if (frame.opcode === OPCODE_PING) {
                sendPong(outputStream, frame.payload);
            } else if (frame.opcode === OPCODE_CLOSE) {
                break;
            }
            // 忽略其他帧类型
        }
    } catch (e) {
        log('连接异常 (' + clientId + '): ' + e.message);
    } finally {
        // 清理
        removeClient(clientId);
        try { socket.close(); } catch (e) { /* ignore */ }
        log('断开连接: ' + clientId + ' (剩余: ' + activeClients.length + ' 台)');
    }
}

// ===== 客户端连接管理 =====
function removeClient(clientId) {
    for (var i = activeClients.length - 1; i >= 0; i--) {
        if (activeClients[i].id === clientId) {
            activeClients.splice(i, 1);
            break;
        }
    }
}

function disconnectAllClients() {
    var notice = JSON.stringify({
        type: 'result',
        status: 'error',
        dataType: 'text',
        data: '服务端已停止'
    });
    for (var i = activeClients.length - 1; i >= 0; i--) {
        var client = activeClients[i];
        try {
            sendTextFrame(client.outputStream, notice);
        } catch (e) { /* ignore */ }
        try {
            sendCloseFrame(client.outputStream);
        } catch (e) { /* ignore */ }
        try { client.socket.close(); } catch (e) { /* ignore */ }
    }
    activeClients = [];
}

// ===== 悬浮窗 UI =====
function createFloatyWindow() {
    try {
        floatyWindow = floaty.window(
            <frame>
                <button id='stopBtn' text='停止' textColor='#FF6B6B' textSize='12sp' w='48dp' h='36dp' bg='#CC333333' gravity='center' />
            </frame>
        );

        // 拖拽 + 点击处理
        var _touchX = 0, _touchY = 0, _touchMoved = false;
        floatyWindow.stopBtn.setOnTouchListener(function(view, event) {
            var action = event.getAction();
            switch (action) {
                case android.view.MotionEvent.ACTION_DOWN:
                    _touchX = event.getRawX();
                    _touchY = event.getRawY();
                    _touchMoved = false;
                    return true;
                case android.view.MotionEvent.ACTION_MOVE:
                    var dx = event.getRawX() - _touchX;
                    var dy = event.getRawY() - _touchY;
                    if (Math.abs(dx) > 5 || Math.abs(dy) > 5) {
                        _touchMoved = true;
                        floatyWindow.setPosition(floatyWindow.getX() + dx, floatyWindow.getY() + dy);
                        _touchX = event.getRawX();
                        _touchY = event.getRawY();
                    }
                    return true;
                case android.view.MotionEvent.ACTION_UP:
                    if (!_touchMoved) {
                        dialogs.confirm('提示', '确定停止服务？', function () {
                            stopServer();
                        });
                    }
                    return true;
            }
            return false;
        });

        // 设置悬浮窗位置（屏幕右上角）
        floatyWindow.setPosition(
            Math.max(0, device.width - 120),
            80
        );

        log('悬浮按钮已创建');
    } catch (e) {
        toast('悬浮窗创建失败: ' + String(e).slice(0, 50));
        log('悬浮窗创建失败: ' + e.message);
    }
}

function destroyFloatyWindow() {
    if (floatyWindow) {
        try {
            floatyWindow.close();
        } catch (e) { /* ignore */ }
        floatyWindow = null;
    }
}

// ===== 服务器启动 =====
function startServer() {
    if (isRunning) {
        toast('服务已在运行中');
        return;
    }

    try {
        serverSocket = new java.net.ServerSocket(PORT);
        // 不设 SoTimeout，accept() 阻塞等待直到有连接
        isRunning = true;
        log('服务已启动，端口: ' + PORT);
        toast('Autojs 服务启动: ' + PORT);
    } catch (e) {
        isRunning = false;
        log('启动失败: ' + String(e));
        toast('启动失败: ' + String(e).slice(0, 30));
        return;
    }
}

// ===== 接受连接循环（主线程阻塞运行） =====
function acceptLoop() {
    log('进入 accept 循环...');
    while (isRunning) {
        try {
            var clientSocket = serverSocket.accept();
            log('收到连接: ' + clientSocket.getInetAddress().getHostAddress());

            // 检查连接数限制
            if (activeClients.length >= MAX_CONNECTIONS) {
                log('连接数已达上限，拒绝新连接');
                try { clientSocket.close(); } catch (e2) { /* ignore */ }
                continue;
            }

            // 为新连接启动线程处理
            var sock = clientSocket;
            threads.start(function () {
                handleClient(sock);
            });

        } catch (e) {
            if (!isRunning) break;
            var errStr = String(e);
            // serverSocket.close() 会导致 accept 抛异常，这是正常的停止流程
            if (errStr.indexOf('SocketClosed') >= 0 || errStr.indexOf('Closed') >= 0) {
                break;
            }
            log('accept 异常: ' + errStr.slice(0, 80));
        }
    }
    log('accept 循环已退出');

    // 清理 ServerSocket
    if (serverSocket) {
        try { serverSocket.close(); } catch (e) { /* ignore */ }
        serverSocket = null;
    }
}

// ===== 服务器停止 =====
function stopServer() {
    if (!isRunning) {
        return;
    }

    isRunning = false;
    log('正在停止服务...');

    // 断开所有客户端
    disconnectAllClients();

    // 关闭 ServerSocket（会中断阻塞的 accept）
    if (serverSocket) {
        try {
            serverSocket.close();
        } catch (e) { /* ignore */ }
        serverSocket = null;
    }

    // 移除悬浮窗
    destroyFloatyWindow();

    toast('服务已停止');
    log('服务已停止');
}

// ===== 入口 =====
log('=== Autojs WebSocket 服务启动中 ===');

// 启动服务（创建 ServerSocket）
startServer();

if (!isRunning) {
    log('服务启动失败，退出');
    exit();
}

// 创建悬浮窗（失败不影响服务运行）
try {
    createFloatyWindow();
} catch (e) {
    log('悬浮窗创建异常: ' + String(e).slice(0, 50));
}

// 注册脚本停止事件
events.on('exit', function () {
    log('脚本退出，清理资源...');
    stopServer();
});

// accept 循环在主线程运行（阻塞）
log('开始 accept 循环（阻塞主线程）...');
acceptLoop();

// acceptLoop 退出后，脚本自然结束
log('脚本结束');
