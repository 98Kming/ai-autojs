<script setup lang="ts">
import { computed } from 'vue'
import { CopyDocument, Download } from '@element-plus/icons-vue'
import type { ResultEntry } from '@/stores/useCodeStore'

const props = defineProps<{
  entry: ResultEntry
}>()

const emit = defineEmits<{
  reRun: [code: string]
}>()

const formattedTime = computed(() => {
  const d = new Date(props.entry.timestamp)
  return d.toLocaleTimeString('zh-CN', { hour12: false })
})

const formattedDuration = computed(() => {
  const ms = props.entry.durationMs
  if (ms == null) return ''
  return ms < 1000 ? `${ms}ms` : `${(ms / 1000).toFixed(1)}s`
})

const isImage = computed(() =>
  props.entry.dataType === 'base64' && props.entry.mime?.startsWith('image/')
)

const imgSrc = computed(() => {
  if (!isImage.value) return ''
  return `data:${props.entry.mime};base64,${props.entry.data}`
})

function copyResult() {
  if (props.entry.dataType === 'base64' && !isImage.value) {
    // 二进制结果：复制 Base64 字符串
    navigator.clipboard.writeText(props.entry.data)
  } else {
    navigator.clipboard.writeText(props.entry.data)
  }
}

function downloadBinary() {
  if (props.entry.dataType !== 'base64') return
  const byteChars = atob(props.entry.data)
  const byteNums = new Array(byteChars.length)
  for (let i = 0; i < byteChars.length; i++) {
    byteNums[i] = byteChars.charCodeAt(i)
  }
  const blob = new Blob([new Uint8Array(byteNums)], { type: props.entry.mime || 'application/octet-stream' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = 'autojs-result'
  a.click()
  URL.revokeObjectURL(url)
}

function hexDump(base64: string, maxBytes: number = 256): string {
  const binary = atob(base64)
  const len = Math.min(binary.length, maxBytes)
  const lines: string[] = []
  for (let i = 0; i < len; i += 16) {
    const offset = i.toString(16).padStart(8, '0')
    const hex = []
    const ascii = []
    for (let j = 0; j < 16 && i + j < len; j++) {
      const byte = binary.charCodeAt(i + j)
      hex.push(byte.toString(16).padStart(2, '0'))
      ascii.push(byte >= 32 && byte <= 126 ? String.fromCharCode(byte) : '.')
    }
    lines.push(`${offset}  ${hex.join(' ').padEnd(47)}  ${ascii.join('')}`)
  }
  if (binary.length > maxBytes) {
    lines.push(`... 共 ${binary.length} 字节，仅显示前 ${maxBytes} 字节`)
  }
  return lines.join('\n')
}
</script>

<template>
  <div class="result-item" :class="entry.status">
    <div class="result-header">
      <el-tag :type="entry.status === 'success' ? 'success' : 'danger'" size="small" class="result-tag">
        {{ entry.status === 'success' ? '成功' : '失败' }}
      </el-tag>
      <span v-if="entry.dataType === 'base64'" class="binary-badge">
        <el-tag type="info" size="small">二进制</el-tag>
      </span>
      <span class="result-time">{{ formattedTime }}</span>
      <span v-if="formattedDuration" class="result-duration">{{ formattedDuration }}</span>
      <div class="result-actions">
        <el-tooltip content="复制结果" :show-after="500">
          <el-button size="small" text :icon="CopyDocument" @click="copyResult" />
        </el-tooltip>
        <el-tooltip v-if="entry.dataType === 'base64' && !isImage" content="下载二进制" :show-after="500">
          <el-button size="small" text :icon="Download" @click="downloadBinary" />
        </el-tooltip>
      </div>
    </div>
    <div class="result-body">
      <!-- 图片预览 -->
      <div v-if="isImage" class="image-preview">
        <el-image :src="imgSrc" fit="contain" style="max-height: 300px" :preview-src-list="[imgSrc]" />
      </div>
      <!-- 二进制 Hex Dump -->
      <pre v-else-if="entry.dataType === 'base64'" class="result-hexdump">{{ hexDump(entry.data) }}</pre>
      <!-- 文本结果 -->
      <pre v-else class="result-text">{{ entry.data || '(无输出)' }}</pre>
    </div>
  </div>
</template>

<style scoped>
.result-item {
  border-radius: var(--radius-sm);
  border: 1px solid var(--color-border);
  margin-bottom: 8px;
  overflow: hidden;
}

.result-item.success {
  border-left: 3px solid var(--color-success);
}

.result-item.error {
  border-left: 3px solid var(--color-danger);
}

.result-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background-color: var(--color-bg-secondary);
  border-bottom: 1px solid var(--color-border);
}

.result-tag {
  flex-shrink: 0;
}

.binary-badge {
  flex-shrink: 0;
}

.result-time {
  font-size: 12px;
  color: var(--color-text-placeholder);
}

.result-duration {
  font-size: 11px;
  color: var(--color-text-placeholder);
  background: var(--color-bg-tertiary);
  padding: 0 5px;
  border-radius: 3px;
  font-family: var(--editor-font-family, monospace);
}

.result-actions {
  display: flex;
  gap: 4px;
  margin-left: auto;
}

.result-body {
  padding: 12px;
}

.result-text {
  margin: 0;
  font-family: var(--editor-font-family);
  font-size: 13px;
  line-height: 1.5;
  white-space: pre-wrap;
  word-break: break-all;
  max-height: 400px;
  overflow-y: auto;
}

.result-hexdump {
  margin: 0;
  font-family: var(--editor-font-family);
  font-size: 12px;
  line-height: 1.5;
  white-space: pre;
  max-height: 400px;
  overflow-y: auto;
  color: var(--color-text-secondary);
}

.image-preview {
  text-align: center;
}
</style>
