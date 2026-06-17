<script setup lang="ts">
import { Clock } from '@element-plus/icons-vue'
import ConnectionBadge from '@/components/connection/ConnectionBadge.vue'
import { useHistoryStore } from '@/stores/useHistoryStore'
import { useWebSocketStore } from '@/stores/useWebSocketStore'

const historyStore = useHistoryStore()
const wsStore = useWebSocketStore()
</script>

<template>
  <div class="header-content">
    <div class="header-left">
      <h1 class="logo">AI-AutoJS</h1>
    </div>
    <div class="header-center">
      <ConnectionBadge />
    </div>
    <div class="header-right">
      <el-badge :value="historyStore.entries.length" :max="99" :hidden="historyStore.entries.length === 0">
        <el-button circle :icon="Clock" @click="wsStore.toggleHistory()" title="执行历史" />
      </el-badge>
    </div>
  </div>
</template>

<style scoped>
.header-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
}

.header-left .logo {
  font-size: 18px;
  font-weight: 700;
  color: var(--color-primary);
  white-space: nowrap;
}

.header-center {
  flex: 1;
  display: flex;
  justify-content: center;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 8px;
}
</style>
