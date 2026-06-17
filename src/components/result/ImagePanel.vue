<script setup lang="ts">
import { ref, computed, watch, onUnmounted } from 'vue'
import { ElMessageBox } from 'element-plus'
import { Delete, Camera, Scissor, Reading, Loading } from '@element-plus/icons-vue'
import { useImageStore, type ImageEntry } from '@/stores/useImageStore'
import { useCodeStore } from '@/stores/useCodeStore'
import ImageCard from './ImageCard.vue'

const imageStore = useImageStore()
const codeStore = useCodeStore()
const selectedId = ref<string | null>(null)

const MAGNIFIER_SIZE = 180
const MAGNIFIER_ZOOM = 10

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

// === 放大镜 ===
const magnifierEnabled = ref(true)
const mouseX = ref(0)
const mouseY = ref(0)
const showMagnifier = ref(false)
const imageNaturalSize = ref({ width: 0, height: 0 })
const viewerEl = ref<HTMLElement | null>(null)

// 像素信息（坐标 + 16 进制颜色）
const pixelInfo = ref({ x: 0, y: 0, hex: '#000000' })
let _pixelCanvas: HTMLCanvasElement | null = null
let _pixelCtx: CanvasRenderingContext2D | null = null

// === 缩放 / 平移 ===
const viewerZoom = ref(1)
const viewerPanX = ref(0)
const viewerPanY = ref(0)
const isDragging = ref(false)
const dragStart = ref({ x: 0, y: 0, panX: 0, panY: 0 })

function resetViewerTransform() {
  viewerZoom.value = 1
  viewerPanX.value = 0
  viewerPanY.value = 0
}

// 切换图片时重置
watch(selectedId, () => resetViewerTransform())

// 计算图片在 viewer 中实际渲染区域（object-fit: contain 居中缩放）
function getImageRenderRect(viewer: HTMLElement) {
  const { width: natW, height: natH } = imageNaturalSize.value
  if (!natW || !natH) return null
  const viewerW = viewer.clientWidth
  const viewerH = viewer.clientHeight
  const imgAspect = natW / natH
  const viewAspect = viewerW / viewerH
  let w: number, h: number, x: number, y: number
  if (imgAspect > viewAspect) {
    w = viewerW; h = viewerW / imgAspect; x = 0; y = (viewerH - h) / 2
  } else {
    h = viewerH; w = viewerH * imgAspect; x = (viewerW - w) / 2; y = 0
  }
  return { x, y, w, h }
}

// 带缩放/平移校正的原图坐标映射
function getZoomedImageCoord(mx: number, my: number, viewer: HTMLElement, rect?: { x: number; y: number; w: number; h: number }) {
  const r = rect || getImageRenderRect(viewer)
  if (!r) return null
  const { width: natW, height: natH } = imageNaturalSize.value
  if (!natW || !natH) return null
  const z = viewerZoom.value
  const px = viewerPanX.value
  const py = viewerPanY.value
  // 鼠标偏移 image 中心 → 缩放到 zoom=1 空间 → 映射到原图坐标
  const cx = viewer.clientWidth / 2
  const cy = viewer.clientHeight / 2
  const offsetX = mx - cx - px
  const offsetY = my - cy - py
  const natX = natW / 2 + (offsetX / z) * (natW / r.w)
  const natY = natH / 2 + (offsetY / z) * (natH / r.h)
  return { natX, natY }
}

// 缩放后图片在 viewer 中的可视边界
function getZoomedImageBounds(viewer: HTMLElement) {
  const rect = getImageRenderRect(viewer)
  if (!rect || !imageNaturalSize.value.width || !imageNaturalSize.value.height) return null
  const z = viewerZoom.value
  const px = viewerPanX.value
  const py = viewerPanY.value
  const cx = viewer.clientWidth / 2
  const cy = viewer.clientHeight / 2
  return {
    left: cx + px - rect.w * z / 2,
    right: cx + px + rect.w * z / 2,
    top: cy + py - rect.h * z / 2,
    bottom: cy + py + rect.h * z / 2,
  }
}

// 预加载图片获取自然尺寸
function loadImageNaturalSize(src: string) {
  const img = new Image()
  img.onload = () => {
    imageNaturalSize.value = { width: img.naturalWidth, height: img.naturalHeight }
  }
  img.onerror = () => {
    imageNaturalSize.value = { width: 0, height: 0 }
  }
  img.src = src
}

watch(selectedSrc, (src) => {
  if (src) {
    loadImageNaturalSize(src)
    loadPixelCanvas(src)
  }
})

// 像素颜色采样（Canvas 解码 base64 → getImageData）
function loadPixelCanvas(src: string) {
  const img = new Image()
  img.onload = () => {
    _pixelCanvas = document.createElement('canvas')
    _pixelCanvas.width = img.naturalWidth
    _pixelCanvas.height = img.naturalHeight
    _pixelCtx = _pixelCanvas.getContext('2d')
    _pixelCtx!.drawImage(img, 0, 0)
  }
  img.onerror = () => { _pixelCanvas = null; _pixelCtx = null }
  img.src = src
}

function samplePixel(natX: number, natY: number) {
  if (!_pixelCtx || !_pixelCanvas) return
  const x = Math.round(natX)
  const y = Math.round(natY)
  const cx = Math.max(0, Math.min(x, _pixelCanvas.width - 1))
  const cy = Math.max(0, Math.min(y, _pixelCanvas.height - 1))
  const data = _pixelCtx.getImageData(cx, cy, 1, 1).data
  const hex = '#' + [data[0], data[1], data[2]]
    .map(v => v.toString(16).padStart(2, '0')).join('').toUpperCase()
  pixelInfo.value = { x: cx, y: cy, hex }
}

// === 鼠标事件 ===
function onViewerMouseMove(e: MouseEvent) {
  if (isDragging.value) return // 拖拽中由 onDragMove 处理

  if (!magnifierEnabled.value || !viewerEl.value) return
  const rect = viewerEl.value.getBoundingClientRect()
  const mx = e.clientX - rect.left
  const my = e.clientY - rect.top
  mouseX.value = mx
  mouseY.value = my
  showMagnifier.value = true

  // 计算原图坐标并采样像素颜色
  const viewer = viewerEl.value
  const imgRect = getImageRenderRect(viewer)
  const bounds = getZoomedImageBounds(viewer)
  if (!imgRect || !bounds) return
  if (mx < bounds.left || mx > bounds.right || my < bounds.top || my > bounds.bottom) return

  const coord = getZoomedImageCoord(mx, my, viewer, imgRect)
  if (!coord) return
  samplePixel(coord.natX, coord.natY)
}

function onViewerMouseLeave() {
  showMagnifier.value = false
}

function onWheel(e: WheelEvent) {
  const viewer = viewerEl.value
  if (!viewer) return
  const rect = viewer.getBoundingClientRect()
  const viewerCenterX = viewer.clientWidth / 2
  const viewerCenterY = viewer.clientHeight / 2
  // 鼠标相对 viewer 中心
  const vx = e.clientX - rect.left - viewerCenterX
  const vy = e.clientY - rect.top - viewerCenterY
  const oldZ = viewerZoom.value
  const delta = e.deltaY > 0 ? -0.2 : 0.2
  const newZ = Math.max(0.2, Math.min(10, oldZ + delta))
  if (newZ === oldZ) return
  // 保持鼠标位置在原图上的对应点不变
  viewerPanX.value = vx * (1 - newZ / oldZ) + viewerPanX.value * newZ / oldZ
  viewerPanY.value = vy * (1 - newZ / oldZ) + viewerPanY.value * newZ / oldZ
  viewerZoom.value = newZ
}

function onMouseDown(e: MouseEvent) {
  if (e.button !== 0) return
  isDragging.value = true
  showMagnifier.value = false
  dragStart.value = { x: e.clientX, y: e.clientY, panX: viewerPanX.value, panY: viewerPanY.value }
  window.addEventListener('mousemove', onDragMove)
  window.addEventListener('mouseup', onDragEnd)
}

function onDragMove(e: MouseEvent) {
  if (!isDragging.value) return
  const dx = e.clientX - dragStart.value.x
  const dy = e.clientY - dragStart.value.y
  viewerPanX.value = dragStart.value.panX + dx
  viewerPanY.value = dragStart.value.panY + dy
}

function onDragEnd() {
  isDragging.value = false
  window.removeEventListener('mousemove', onDragMove)
  window.removeEventListener('mouseup', onDragEnd)
}

// 组件卸载时清理
onUnmounted(() => {
  window.removeEventListener('mousemove', onDragMove)
  window.removeEventListener('mouseup', onDragEnd)
  _pixelCanvas = null
  _pixelCtx = null
})

// 缩放的 image 样式
const isZoomed = computed(() => viewerZoom.value > 1.01)

const imageTransformStyle = computed(() => {
  const z = viewerZoom.value
  const cursor = isZoomed.value
    ? (isDragging.value ? 'grabbing' : 'grab')
    : 'default'
  return {
    transform: `translate(${viewerPanX.value}px, ${viewerPanY.value}px) scale(${z})`,
    cursor,
  }
})

// 缩放百分比文字
const zoomPercent = computed(() => `${Math.round(viewerZoom.value * 100)}%`)

const lensStyle = computed(() => {
  if (!showMagnifier.value || !selectedImage.value) return { display: 'none' }

  const viewer = viewerEl.value
  if (!viewer) return { display: 'none' }

  const { width: natW, height: natH } = imageNaturalSize.value
  if (!natW || !natH) return { display: 'none' }

  const rect = getImageRenderRect(viewer)
  if (!rect) return { display: 'none' }

  // 检查鼠标是否在缩放后图片可见范围内
  const bounds = getZoomedImageBounds(viewer)
  if (!bounds) return { display: 'none' }
  if (mouseX.value < bounds.left || mouseX.value > bounds.right ||
      mouseY.value < bounds.top || mouseY.value > bounds.bottom) {
    return { display: 'none' }
  }

  // 带缩放/平移校正的原图坐标
  const coord = getZoomedImageCoord(mouseX.value, mouseY.value, viewer, rect)
  if (!coord) return { display: 'none' }

  const natX = coord.natX
  const natY = coord.natY

  // 背景偏移：让原图 (natX, natY) 对准放大镜圆心
  const bgPosX = MAGNIFIER_SIZE / 2 - natX * MAGNIFIER_ZOOM
  const bgPosY = MAGNIFIER_SIZE / 2 - natY * MAGNIFIER_ZOOM

  // 放大镜位置：默认右下偏移，贴边自动翻转
  const viewerW = viewer.clientWidth
  const viewerH = viewer.clientHeight
  let lensLeft = mouseX.value + 15
  let lensTop = mouseY.value + 15
  if (lensLeft + MAGNIFIER_SIZE > viewerW) lensLeft = mouseX.value - MAGNIFIER_SIZE - 15
  if (lensTop + MAGNIFIER_SIZE > viewerH) lensTop = mouseY.value - MAGNIFIER_SIZE - 15

  return {
    backgroundImage: `url(${selectedSrc.value})`,
    backgroundSize: `${natW * MAGNIFIER_ZOOM}px ${natH * MAGNIFIER_ZOOM}px`,
    backgroundPosition: `${bgPosX}px ${bgPosY}px`,
    width: `${MAGNIFIER_SIZE}px`,
    height: `${MAGNIFIER_SIZE}px`,
    left: `${lensLeft}px`,
    top: `${lensTop}px`,
    display: 'block',
  }
})
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
    <div
      ref="viewerEl"
      class="image-viewer"
      :class="{ 'is-dragging': isDragging }"
      @mousemove="onViewerMouseMove"
      @mouseleave="onViewerMouseLeave"
      @wheel.prevent="onWheel"
      @mousedown="onMouseDown"
      @mouseup="onDragEnd"
      @dblclick="resetViewerTransform"
    >
      <template v-if="selectedImage">
        <!-- 放大镜勾选框 -->
        <div class="viewer-toolbar">
          <el-checkbox v-model="magnifierEnabled" size="small">🔍 放大镜</el-checkbox>
          <span v-if="isZoomed" class="zoom-badge">{{ zoomPercent }}</span>
        </div>
        <img
          :src="selectedSrc"
          class="viewer-image"
          :style="imageTransformStyle"
          draggable="false"
          alt="screenshot"
        />
        <!-- 放大镜镜片 -->
        <div v-show="showMagnifier && magnifierEnabled" class="magnifier-lens" :style="lensStyle">
          <div class="pixel-grid" />
          <div class="magnifier-crosshair" />
          <div class="magnifier-info">
            <span class="mi-coords">({{ pixelInfo.x }}, {{ pixelInfo.y }})</span>
            <span class="mi-swatch" :style="{ backgroundColor: pixelInfo.hex }" />
            <span class="mi-hex">{{ pixelInfo.hex }}</span>
          </div>
        </div>
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
  position: relative;
}

.viewer-image {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
  transform-origin: center center;
  user-select: none;
  -webkit-user-drag: none;
}

.viewer-empty {
  display: flex;
  align-items: center;
  justify-content: center;
}

.image-viewer.is-dragging {
  cursor: grabbing;
}

/* 顶部工具栏（放大镜勾选 + 缩放比例） */
.viewer-toolbar {
  position: absolute;
  top: 8px;
  left: 8px;
  z-index: 10;
  display: flex;
  align-items: center;
  gap: 8px;
  background: rgba(0, 0, 0, 0.5);
  border-radius: 4px;
  padding: 2px 8px;
}

.viewer-toolbar :deep(.el-checkbox__label) {
  color: #fff;
  font-size: 12px;
}

.viewer-toolbar :deep(.el-checkbox__inner) {
  border-color: rgba(255, 255, 255, 0.6);
}

.zoom-badge {
  color: #fff;
  font-size: 11px;
  font-family: var(--editor-font-family, monospace);
  background: rgba(255, 255, 255, 0.15);
  padding: 0 6px;
  border-radius: 3px;
  line-height: 18px;
}

/* 放大镜镜片 */
.magnifier-lens {
  position: absolute;
  border-radius: 2px;
  border: 3px solid #fff;
  box-shadow:
    0 0 12px rgba(0, 0, 0, 0.5),
    inset 0 0 8px rgba(0, 0, 0, 0.1);
  pointer-events: none;
  background-repeat: no-repeat;
  z-index: 20;
}

/* 放大镜像素网格 */
.pixel-grid {
  position: absolute;
  inset: 0;
  pointer-events: none;
  border-radius: inherit;
  --grid-size: 10px;
  background-image:
    repeating-linear-gradient(
      to bottom,
      transparent,
      transparent calc(var(--grid-size) - 1px),
      rgba(128, 128, 128, 0.45) calc(var(--grid-size) - 1px),
      rgba(128, 128, 128, 0.45) var(--grid-size)
    ),
    repeating-linear-gradient(
      to right,
      transparent,
      transparent calc(var(--grid-size) - 1px),
      rgba(128, 128, 128, 0.45) calc(var(--grid-size) - 1px),
      rgba(128, 128, 128, 0.45) var(--grid-size)
    );
}

/* 放大镜十字准星 */
.magnifier-crosshair {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  pointer-events: none;
  z-index: 21;
  width: 14px;
  height: 14px;
}

.magnifier-crosshair::before,
.magnifier-crosshair::after {
  content: '';
  position: absolute;
  background: rgba(255, 60, 60, 0.85);
}

.magnifier-crosshair::before {
  width: 100%;
  height: 1px;
  top: 50%;
  left: 0;
  transform: translateY(-50%);
}

.magnifier-crosshair::after {
  width: 1px;
  height: 100%;
  top: 0;
  left: 50%;
  transform: translateX(-50%);
}

/* 放大镜信息栏（坐标 + 颜色） */
.magnifier-info {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 22px;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 6px;
  font-size: 10px;
  font-family: var(--editor-font-family, monospace);
  color: #eee;
  border-bottom-left-radius: 2px;
  border-bottom-right-radius: 2px;
  gap: 4px;
}

.mi-swatch {
  display: inline-block;
  width: 12px;
  height: 12px;
  border: 1px solid rgba(255, 255, 255, 0.3);
  border-radius: 2px;
  flex-shrink: 0;
}

.mi-coords,
.mi-hex {
  white-space: nowrap;
}
</style>
