<script setup lang="ts">
import { Link, SwitchButton } from '@element-plus/icons-vue'
import { useWebSocketStore } from '@/stores/useWebSocketStore'

const wsStore = useWebSocketStore()

const emit = defineEmits<{
  connect: []
  disconnect: []
}>()

function onConnect() {
  emit('connect')
}

function onDisconnect() {
  emit('disconnect')
}
</script>

<template>
  <div class="connection-panel">
    <el-input
      v-model="wsStore.config.host"
      placeholder="输入手机 IP 地址"
      class="host-input"
      clearable
      :disabled="wsStore.status === 'connected'"
    >
      <template #prepend>ws://</template>
      <template #append>:{{ wsStore.config.port }}</template>
    </el-input>
    <el-button
      v-if="wsStore.status !== 'connected'"
      type="primary"
      :loading="wsStore.status === 'connecting'"
      :icon="Link"
      @click="onConnect"
    >
      连接
    </el-button>
    <el-button
      v-else
      type="danger"
      :icon="SwitchButton"
      @click="onDisconnect"
    >
      断开
    </el-button>
  </div>
</template>

<style scoped>
.connection-panel {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  background-color: var(--color-bg-secondary);
  border-bottom: 1px solid var(--color-border);
}

.host-input {
  flex: 1;
  max-width: 360px;
}
</style>
