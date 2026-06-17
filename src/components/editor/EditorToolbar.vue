<script setup lang="ts">
import { computed } from 'vue'
import { Operation, Delete, VideoPlay } from '@element-plus/icons-vue'
import { useCodeStore } from '@/stores/useCodeStore'
import { useWebSocketStore } from '@/stores/useWebSocketStore'

const codeStore = useCodeStore()
const wsStore = useWebSocketStore()

const emit = defineEmits<{
  run: []
  clear: []
  format: []
}>()

const canRun = computed(() =>
  wsStore.status === 'connected' &&
  !codeStore.isExecuting &&
  codeStore.content.trim().length > 0
)
</script>

<template>
  <div class="editor-toolbar">
    <div class="toolbar-left">
      <span class="toolbar-title">代码编辑器</span>
    </div>
    <div class="toolbar-actions">
      <el-tooltip content="格式化 (Shift+Alt+F)" :show-after="500">
        <el-button size="small" :icon="Operation" @click="emit('format')" :disabled="codeStore.isExecuting">格式化</el-button>
      </el-tooltip>
      <el-tooltip content="清空编辑器" :show-after="500">
        <el-button size="small" :icon="Delete" @click="emit('clear')" :disabled="codeStore.isExecuting">清空</el-button>
      </el-tooltip>
      <el-tooltip content="运行 (Ctrl+Enter)" :show-after="500">
        <el-button size="small" type="primary" :icon="VideoPlay" :disabled="!canRun" @click="emit('run')">
          {{ codeStore.isExecuting ? '执行中...' : '运行' }}
        </el-button>
      </el-tooltip>
    </div>
  </div>
</template>

<style scoped>
.editor-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  background-color: var(--color-bg-secondary);
  border-bottom: 1px solid var(--color-border);
  flex-shrink: 0;
}

.toolbar-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text-secondary);
}

.toolbar-actions {
  display: flex;
  gap: 8px;
}
</style>
