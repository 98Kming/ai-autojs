<script setup lang="ts">
import { ref, watch, nextTick } from 'vue'
import { Delete } from '@element-plus/icons-vue'
import { useCodeStore, type ResultEntry } from '@/stores/useCodeStore'
import ResultItem from './ResultItem.vue'

const codeStore = useCodeStore()
const resultList = ref<ResultEntry[]>([])
const listRef = ref<HTMLDivElement | null>(null)

// 实时结果收集
watch(() => codeStore.lastResult, (entry) => {
  if (entry) {
    resultList.value.unshift(entry)
  }
})

// 自动滚动到最新结果
watch(() => resultList.value.length, async () => {
  await nextTick()
  if (listRef.value) {
    listRef.value.scrollTop = 0
  }
})

function clearResults() {
  resultList.value = []
  codeStore.clearResult()
}
</script>

<template>
  <div class="result-panel">
    <div class="result-toolbar">
      <span class="result-title">执行结果</span>
      <el-button
        v-if="resultList.length > 0"
        size="small"
        text
        :icon="Delete"
        @click="clearResults"
      >
        清空
      </el-button>
    </div>
    <div ref="listRef" class="result-list">
      <template v-if="resultList.length > 0">
        <ResultItem
          v-for="entry in resultList"
          :key="entry.id"
          :entry="entry"
        />
      </template>
      <div v-else class="result-empty">
        <el-empty description="等待代码执行..." :image-size="80" />
      </div>
    </div>
  </div>
</template>

<style scoped>
.result-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.result-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  background-color: var(--color-bg-secondary);
  border-bottom: 1px solid var(--color-border);
  flex-shrink: 0;
}

.result-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text-secondary);
}

.result-list {
  flex: 1;
  overflow-y: auto;
  padding: 12px;
}

.result-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
}
</style>
