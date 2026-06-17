<script setup lang="ts">
import { onMounted, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import { useWebSocketStore } from '@/stores/useWebSocketStore'
import { useCodeStore } from '@/stores/useCodeStore'
import { useHistoryStore } from '@/stores/useHistoryStore'
import { useWebSocket } from '@/composables/useWebSocket'
import type { HistoryEntry, ResultMessage } from '@/types/autojs'
import ConnectionPanel from '@/components/connection/ConnectionPanel.vue'
import CodeEditor from '@/components/editor/CodeEditor.vue'
import EditorToolbar from '@/components/editor/EditorToolbar.vue'
import ResultPanel from '@/components/result/ResultPanel.vue'
import HistoryDrawer from '@/components/history/HistoryDrawer.vue'

const wsStore = useWebSocketStore()
const codeStore = useCodeStore()
const historyStore = useHistoryStore()

// --- WebSocket 实例化 ---
const ws = useWebSocket()

// 注册结果回调：收到服务端返回后更新 store
ws.onResult((msg: ResultMessage) => {
  codeStore.setExecuting(false)
  codeStore.setResult(msg)

  // 更新历史记录
  historyStore.addEntry({
    id: Date.now().toString(36) + Math.random().toString(36).slice(2, 7),
    code: codeStore.content,
    result: msg.data,
    resultDataType: msg.dataType || 'text',
    resultMime: msg.mime,
    status: msg.status,
    timestamp: Date.now(),
  })

  if (msg.status === 'error') {
    ElMessage.error('执行出错: ' + (msg.data || '').slice(0, 100))
  } else {
    ElMessage.success('执行成功')
  }
})

// --- 连接 / 断开 ---
function onConnect() {
  ws.connect()
}

function onDisconnect() {
  ws.disconnect()
}

// --- 运行代码 ---
function onRun() {
  if (!codeStore.content.trim()) return
  codeStore.setExecuting(true)

  // 先添加一条 pending 状态的历史
  historyStore.addEntry({
    id: Date.now().toString(36) + Math.random().toString(36).slice(2, 7),
    code: codeStore.content,
    result: '',
    resultDataType: 'text',
    status: 'pending',
    timestamp: Date.now(),
  })

  const sent = ws.sendCode(codeStore.content)
  if (!sent) {
    codeStore.setExecuting(false)
    ElMessage.warning('未连接，无法执行代码')
  }
}

function onClear() {
  codeStore.clearContent()
}

function onFormat() {
  try {
    const lines = codeStore.content.split('\n')
    const formatted = lines.map(line => line.trim()).join('\n')
    codeStore.setContent(formatted)
  } catch {
    // 格式化失败静默处理
  }
}

function onReRun(entry: HistoryEntry) {
  codeStore.setContent(entry.code)
}

// --- beforeunload：页面关闭时断开连接 ---
function onBeforeUnload() {
  ws.disconnect()
}

// --- 键盘快捷键 ---
function onGlobalKeydown(e: KeyboardEvent) {
  if (e.ctrlKey && e.key === 'Enter') {
    e.preventDefault()
    onRun()
  }
}

onMounted(() => {
  window.addEventListener('keydown', onGlobalKeydown)
  window.addEventListener('beforeunload', onBeforeUnload)
})

onUnmounted(() => {
  window.removeEventListener('keydown', onGlobalKeydown)
  window.removeEventListener('beforeunload', onBeforeUnload)
})
</script>

<template>
  <div class="home-view">
    <ConnectionPanel
      @connect="onConnect"
      @disconnect="onDisconnect"
    />
    <div class="workspace">
      <div class="editor-section">
        <EditorToolbar
          @run="onRun"
          @clear="onClear"
          @format="onFormat"
        />
        <div class="editor-body">
          <CodeEditor />
        </div>
      </div>
      <div class="result-section">
        <ResultPanel />
      </div>
    </div>
    <HistoryDrawer
      v-model:visible="wsStore.historyVisible"
      @re-run="onReRun"
    />
  </div>
</template>

<style scoped>
.home-view {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.workspace {
  flex: 1;
  display: flex;
  overflow: hidden;
}

.editor-section {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  border-right: 1px solid var(--color-border);
}

.editor-body {
  flex: 1;
  overflow: hidden;
}

.result-section {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

/* 响应式：窄屏上下堆叠 */
@media (max-width: 900px) {
  .workspace {
    flex-direction: column;
  }

  .editor-section {
    border-right: none;
    border-bottom: 1px solid var(--color-border);
    flex: none;
    height: 50%;
  }

  .result-section {
    flex: none;
    height: 50%;
  }
}
</style>
