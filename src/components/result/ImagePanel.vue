<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { ElMessageBox } from 'element-plus'
import { Delete, Camera, Scissor, Reading, Loading } from '@element-plus/icons-vue'
import { useImageStore, type ImageEntry } from '@/stores/useImageStore'
import { useCodeStore } from '@/stores/useCodeStore'
import ImageCard from './ImageCard.vue'

const imageStore = useImageStore()
const codeStore = useCodeStore()
const selectedId = ref<string | null>(null)

// 新图片添加时自动选中预览
watch(() => imageStore.images.length, (newLen, oldLen) => {
  if (newLen > oldLen && imageStore.images.length > 0) {
    selectedId.value = imageStore.images[0].id
  }
})

const selectedImage = computed<ImageEntry | null>(() => {
  if (!selectedId.value) return null
  return imageStore.images.find(img => img.id === selectedId.value) || null
})

const selectedSrc = computed(() => {
  if (!selectedImage.value) return ''
  return `data:${selectedImage.value.mime};base64,${selectedImage.value.data}`
})

const emit = defineEmits<{
  triggerScreenshot: []
}>()

function onSelect(id: string) {
  selectedId.value = id
}

function onDelete(id: string) {
  if (selectedId.value === id) {
    selectedId.value = null
  }
  imageStore.removeImage(id)
}

function onClearAll() {
  if (imageStore.images.length === 0) return
  ElMessageBox.confirm(
    '确定清空所有截图？',
    '清空截图',
    { confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning' }
  ).then(() => {
    imageStore.clearAll()
    selectedId.value = null
  }).catch(() => {})
}

function onScreenshot() {
  emit('triggerScreenshot')
}
</script>

<template>
  <div class="image-panel">
    <!-- 工具栏 -->
    <div class="tool-bar">
      <el-tooltip :content="codeStore.isExecuting ? '截图中...' : '截取手机屏幕'" placement="right" :show-after="300">
        <el-button :icon="codeStore.isExecuting ? Loading : Camera" circle :loading="codeStore.isExecuting" @click="onScreenshot" />
      </el-tooltip>
      <span class="tool-label" :class="{ active: codeStore.isExecuting }">{{ codeStore.isExecuting ? '截图中...' : '截图' }}</span>

      <el-divider class="tool-divider" />

      <el-tooltip content="剪裁（即将上线）" placement="right" :show-after="300">
        <el-button :icon="Scissor" circle disabled />
      </el-tooltip>
      <span class="tool-label disabled">剪裁</span>

      <el-divider class="tool-divider" />

      <el-tooltip content="文字识别（即将上线）" placement="right" :show-after="300">
        <el-button :icon="Reading" circle disabled />
      </el-tooltip>
      <span class="tool-label disabled">OCR</span>
    </div>

    <!-- 缩略图列表 -->
    <div class="image-list">
      <div class="image-scroll">
        <template v-if="imageStore.images.length > 0">
          <ImageCard
            v-for="img in imageStore.images"
            :key="img.id"
            :image="img"
            :selected="img.id === selectedId"
            @select="onSelect"
            @delete="onDelete"
          />
        </template>
        <div v-else class="list-empty">
          <span class="empty-text">暂无截图</span>
        </div>
      </div>
      <div class="list-footer">
        <el-button
          v-if="imageStore.images.length > 0"
          size="small"
          text
          type="danger"
          :icon="Delete"
          @click="onClearAll"
        >
          清空全部
        </el-button>
      </div>
    </div>

    <!-- 图片展示区 -->
    <div class="image-viewer">
      <template v-if="selectedImage">
        <el-image :src="selectedSrc" fit="contain" class="viewer-image" />
      </template>
      <div v-else class="viewer-empty">
        <el-empty description="点击左侧缩略图查看大图" :image-size="80" />
      </div>
    </div>
  </div>
</template>

<style scoped>
.image-panel {
  display: flex;
  height: 100%;
  overflow: hidden;
}

/* 工具栏 */
.tool-bar {
  width: 72px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 16px 8px;
  border-right: 1px solid var(--color-border);
  background-color: var(--color-bg-secondary);
}

.tool-label {
  font-size: 11px;
  color: var(--color-text-secondary);
  margin-top: 4px;
}

.tool-label.disabled {
  color: var(--color-text-placeholder);
}

.tool-divider {
  margin: 8px 0;
}

/* 缩略图列表 */
.image-list {
  width: 240px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  border-right: 1px solid var(--color-border);
  overflow: hidden;
}

.image-scroll {
  flex: 1;
  overflow-y: auto;
}

.list-empty {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
}

.empty-text {
  font-size: 13px;
  color: var(--color-text-placeholder);
}

.list-footer {
  padding: 8px;
  border-top: 1px solid var(--color-border);
  text-align: center;
}

/* 展示区 */
.image-viewer {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: #1a1a2e;
  overflow: hidden;
}

.viewer-image {
  max-width: 100%;
  max-height: 100%;
}

.viewer-image :deep(img) {
  object-fit: contain;
}

.viewer-empty {
  display: flex;
  align-items: center;
  justify-content: center;
}
</style>
