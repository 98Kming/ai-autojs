<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import { useWebSocketStore } from '@/stores/useWebSocketStore'
import { useCodeStore } from '@/stores/useCodeStore'
import { useHistoryStore } from '@/stores/useHistoryStore'
import { useImageStore } from '@/stores/useImageStore'
import { useWebSocket } from '@/composables/useWebSocket'
import { SCREENSHOT_TEMPLATE, type HistoryEntry, type ResultMessage } from '@/types/autojs'
import ConnectionPanel from '@/components/connection/ConnectionPanel.vue'
import CodeEditor from '@/components/editor/CodeEditor.vue'
import EditorToolbar from '@/components/editor/EditorToolbar.vue'
import ResultPanel from '@/components/result/ResultPanel.vue'
import ImagePanel from '@/components/result/ImagePanel.vue'
import HistoryDrawer from '@/components/history/HistoryDrawer.vue'

const wsStore = useWebSocketStore()
const codeStore = useCodeStore()
const historyStore = useHistoryStore()
const imageStore = useImageStore()

// 执行起始时间（用于计算耗时）
let _execStartTime = 0

const activeTab = ref('code')

// --- WebSocket ---
const ws = useWebSocket()

ws.onResult((msg: ResultMessage) => {
  codeStore.setExecuting(false)
  const durationMs = _execStartTime > 0 ? Date.now() - _execStartTime : undefined
  codeStore.setResult(msg, durationMs)

  historyStore.updateLastEntry({
    result: msg.data,
    resultDataType: msg.dataType || 'text',
    resultMime: msg.mime,
    status: msg.status,
    durationMs,
  })

  // 图片结果 → 图片列表
  if (msg.dataType === 'base64' && msg.mime?.startsWith('image/') && msg.status === 'success') {
    imageStore.addImage(msg.data, msg.mime, codeStore.content)
    ElMessage.success('截图已保存')
    return
  }

  if (msg.status === 'error') {
    ElMessage.error('执行出错: ' + (msg.data || '').slice(0, 100))
  } else {
    ElMessage.success('执行成功')
  }
})

// --- 连接 ---
function onConnect() { ws.connect() }
function onDisconnect() { ws.disconnect() }

// --- 运行 ---
function onRun() {
  if (!codeStore.content.trim()) return
  _execStartTime = Date.now()
  codeStore.setExecuting(true)
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

function onClear() { codeStore.clearContent() }
function onFormat() {
  try {
    const lines = codeStore.content.split('\n')
    codeStore.setContent(lines.map(line => line.trim()).join('\n'))
  } catch { /* ignore */ }
}

function onReRun(entry: HistoryEntry) {
  codeStore.setContent(entry.code)
}

// --- 截图（从 ImagePanel 触发，直接执行不跳转） ---
function onTriggerScreenshot() {
  codeStore.setContent(SCREENSHOT_TEMPLATE)
  onRun()
}

// --- 图片查找（从 ImagePanel 触发） ---
function onTriggerFindImage(code: string) {
  codeStore.setContent(code)
  onRun()
}

// --- 快捷键 ---
function onGlobalKeydown(e: KeyboardEvent) {
  if (e.ctrlKey && e.key === 'Enter') {
    e.preventDefault()
    onRun()
  }
}

function onBeforeUnload() { ws.disconnect() }

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

    <el-tabs v-model="activeTab" class="main-tabs">
      <el-tab-pane label="代码执行" name="code">
        <div class="code-workspace">
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
      </el-tab-pane>

      <el-tab-pane name="image">
        <template #label>
          <span>图片处理</span>
          <el-badge
            v-if="imageStore.images.length > 0"
            :value="imageStore.images.length"
            class="tab-badge"
            type="info"
          />
        </template>
        <ImagePanel @trigger-screenshot="onTriggerScreenshot" @trigger-find-image="onTriggerFindImage" />
      </el-tab-pane>
    </el-tabs>

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

.main-tabs {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.main-tabs :deep(.el-tabs__header) {
  margin: 0;
  padding: 0 16px;
  background-color: var(--color-bg-primary);
  border-bottom: 1px solid var(--color-border);
}

.main-tabs :deep(.el-tabs__content) {
  flex: 1;
  overflow: hidden;
}

.main-tabs :deep(.el-tab-pane) {
  height: 100%;
}

.tab-badge {
  margin-left: 6px;
}

.code-workspace {
  display: flex;
  height: 100%;
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

@media (max-width: 900px) {
  .code-workspace {
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
