<script setup lang="ts">
import { ElMessageBox } from 'element-plus'
import { Delete } from '@element-plus/icons-vue'
import { useHistoryStore } from '@/stores/useHistoryStore'
import type { HistoryEntry } from '@/types/autojs'
import HistoryItem from './HistoryItem.vue'

const props = defineProps<{
  visible: boolean
}>()

const emit = defineEmits<{
  'update:visible': [val: boolean]
  reRun: [entry: HistoryEntry]
}>()

const historyStore = useHistoryStore()

function onReRun(entry: HistoryEntry) {
  emit('reRun', entry)
  emit('update:visible', false)
}

function onDelete(id: string) {
  historyStore.removeEntry(id)
}

function onClearAll() {
  if (historyStore.entries.length === 0) return
  ElMessageBox.confirm(
    '确定清空所有执行历史？此操作不可恢复。',
    '清空历史',
    {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning',
    }
  ).then(() => {
    historyStore.clearAll()
  }).catch(() => {})
}
</script>

<template>
  <el-drawer
    :model-value="visible"
    @update:model-value="emit('update:visible', $event)"
    title="执行历史"
    direction="rtl"
    size="380px"
  >
    <template #header>
      <div class="drawer-header">
        <span>执行历史</span>
        <el-button
          v-if="historyStore.entries.length > 0"
          size="small"
          type="danger"
          text
          :icon="Delete"
          @click="onClearAll"
        >
          清空全部
        </el-button>
      </div>
    </template>

    <div class="drawer-body">
      <template v-if="historyStore.entries.length > 0">
        <HistoryItem
          v-for="entry in historyStore.entries"
          :key="entry.id"
          :entry="entry"
          @re-run="onReRun"
          @delete="onDelete"
        />
      </template>
      <el-empty v-else description="暂无执行历史" :image-size="80" />
    </div>
  </el-drawer>
</template>

<style scoped>
.drawer-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
}

.drawer-body {
  padding: 0 4px;
}
</style>
