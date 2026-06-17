<script setup lang="ts">
import { computed } from 'vue'
import { VideoPlay, CopyDocument, Delete } from '@element-plus/icons-vue'
import type { HistoryEntry } from '@/types/autojs'

const props = defineProps<{
  entry: HistoryEntry
}>()

const emit = defineEmits<{
  reRun: [entry: HistoryEntry]
  delete: [id: string]
}>()

const formattedTime = computed(() => {
  const d = new Date(props.entry.timestamp)
  return d.toLocaleString('zh-CN', { hour12: false })
})

const formattedDuration = computed(() => {
  const ms = props.entry.durationMs
  if (ms == null) return ''
  return ms < 1000 ? `${ms}ms` : `${(ms / 1000).toFixed(1)}s`
})

const codePreview = computed(() => {
  const code = props.entry.code
  return code.length > 80 ? code.slice(0, 80) + '...' : code
})

const resultPreview = computed(() => {
  if (props.entry.resultDataType === 'base64') return '[二进制数据]'
  const text = props.entry.result
  return text.length > 60 ? text.slice(0, 60) + '...' : text || '(无输出)'
})

function copyCode() {
  navigator.clipboard.writeText(props.entry.code)
}

function onReRun() {
  emit('reRun', props.entry)
}

function onDelete() {
  emit('delete', props.entry.id)
}
</script>

<template>
  <div class="history-item" :class="entry.status">
    <div class="history-header">
      <el-tag :type="entry.status === 'success' ? 'success' : entry.status === 'error' ? 'danger' : 'info'" size="small">
        {{ entry.status === 'success' ? '成功' : entry.status === 'error' ? '失败' : '等待中' }}
      </el-tag>
      <span class="history-time">{{ formattedTime }}</span>
      <span v-if="formattedDuration" class="history-duration">{{ formattedDuration }}</span>
      <div class="history-actions">
        <el-tooltip content="重新运行" :show-after="500">
          <el-button size="small" text :icon="VideoPlay" @click="onReRun" />
        </el-tooltip>
        <el-tooltip content="复制代码" :show-after="500">
          <el-button size="small" text :icon="CopyDocument" @click="copyCode" />
        </el-tooltip>
        <el-tooltip content="删除记录" :show-after="500">
          <el-button size="small" text :icon="Delete" @click="onDelete" />
        </el-tooltip>
      </div>
    </div>
    <div class="history-code">
      <code>{{ codePreview }}</code>
    </div>
    <div class="history-result">
      <span class="result-label">结果：</span>{{ resultPreview }}
    </div>
  </div>
</template>

<style scoped>
.history-item {
  padding: 10px 12px;
  border-radius: var(--radius-sm);
  background-color: var(--color-bg-primary);
  border: 1px solid var(--color-border);
  margin-bottom: 8px;
  cursor: default;
  transition: box-shadow 0.2s;
}

.history-item:hover {
  box-shadow: var(--shadow-sm);
}

.history-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}

.history-time {
  font-size: 12px;
  color: var(--color-text-placeholder);
}

.history-duration {
  font-size: 11px;
  color: var(--color-text-placeholder);
  background: var(--color-bg-tertiary);
  padding: 0 5px;
  border-radius: 3px;
  font-family: var(--editor-font-family, monospace);
  margin-right: auto;
}

.history-actions {
  display: flex;
  gap: 2px;
  margin-left: auto;
}

.history-code {
  padding: 6px 8px;
  background-color: var(--color-bg-secondary);
  border-radius: var(--radius-sm);
  margin-bottom: 4px;
  font-family: var(--editor-font-family);
  font-size: 12px;
  color: var(--color-text-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.history-result {
  font-size: 12px;
  color: var(--color-text-secondary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.result-label {
  color: var(--color-text-placeholder);
}
</style>
