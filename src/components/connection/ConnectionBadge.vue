<script setup lang="ts">
import { computed } from 'vue'
import { useWebSocketStore } from '@/stores/useWebSocketStore'
import type { ConnectionStatus } from '@/types/autojs'

const wsStore = useWebSocketStore()

const statusConfig = computed<Record<ConnectionStatus, { type: 'success' | 'danger' | 'info' | 'warning'; text: string }>>(() => ({
  connected: { type: 'success', text: '已连接' },
  connecting: { type: 'warning', text: '连接中...' },
  disconnected: { type: 'info', text: '未连接' },
  error: { type: 'danger', text: '连接失败' },
}))
</script>

<template>
  <el-tag
    :type="statusConfig[wsStore.status].type"
    size="small"
    class="connection-badge"
  >
    <span class="status-dot" :class="wsStore.status" />
    {{ statusConfig[wsStore.status].text }}
  </el-tag>
</template>

<style scoped>
.connection-badge {
  font-size: 12px;
}

.status-dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  margin-right: 6px;
}

.status-dot.connected {
  background-color: var(--color-success);
  animation: pulse 2s infinite;
}

.status-dot.connecting {
  background-color: var(--color-warning);
  animation: pulse 0.8s infinite;
}

.status-dot.disconnected {
  background-color: var(--color-info);
}

.status-dot.error {
  background-color: var(--color-danger);
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}
</style>
