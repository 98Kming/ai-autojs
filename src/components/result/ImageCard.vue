<script setup lang="ts">
import { computed } from 'vue'
import { Download, Delete } from '@element-plus/icons-vue'
import type { ImageEntry } from '@/stores/useImageStore'

const props = defineProps<{
  image: ImageEntry
  selected: boolean
}>()

const emit = defineEmits<{
  select: [id: string]
  delete: [id: string]
}>()

const ext = computed(() => props.image.mime.split('/')[1] || 'png')
const src = computed(() => `data:${props.image.mime};base64,${props.image.data}`)
const fileName = computed(() => {
  const d = new Date(props.image.timestamp)
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getMonth() + 1}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
})

function onSelect() {
  emit('select', props.image.id)
}

function onDownload() {
  const a = document.createElement('a')
  a.href = src.value
  a.download = `screenshot-${props.image.id}.${ext.value}`
  a.click()
}

function onDelete() {
  emit('delete', props.image.id)
}
</script>

<template>
  <div class="image-card" :class="{ selected }" @click="onSelect">
    <div class="card-thumb">
      <el-image :src="src" fit="cover" lazy />
    </div>
    <div class="card-info">
      <span class="card-name">截图 {{ fileName }}</span>
      <div class="card-actions">
        <el-tooltip content="下载" :show-after="500">
          <el-button size="small" text :icon="Download" @click.stop="onDownload" />
        </el-tooltip>
        <el-tooltip content="删除" :show-after="500">
          <el-button size="small" text :icon="Delete" @click.stop="onDelete" />
        </el-tooltip>
      </div>
    </div>
  </div>
</template>

<style scoped>
.image-card {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px;
  border-radius: var(--radius-sm);
  border: 2px solid transparent;
  cursor: pointer;
  transition: border-color 0.15s, background-color 0.15s;
}

.image-card:hover {
  background-color: var(--color-bg-secondary);
}

.image-card.selected {
  border-color: var(--color-primary);
  background-color: #ecf5ff;
}

.card-thumb {
  flex-shrink: 0;
  width: 72px;
  height: 72px;
  border-radius: 4px;
  overflow: hidden;
  background-color: var(--color-bg-tertiary);
}

.card-thumb :deep(.el-image) {
  width: 100%;
  height: 100%;
}

.card-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.card-name {
  font-size: 12px;
  color: var(--color-text-secondary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.card-actions {
  display: flex;
  gap: 2px;
}
</style>
