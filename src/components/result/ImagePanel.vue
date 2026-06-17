<script setup lang="ts">
import { ref, computed, watch, onUnmounted } from 'vue'
import { ElMessageBox, ElMessage } from 'element-plus'
import { Delete, Camera, Scissor, Reading, Loading, FullScreen } from '@element-plus/icons-vue'
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

// === 剪切 ===
const cropMode = ref(false)
const isCropping = ref(false)
const cropStartV = ref({ x: 0, y: 0 })
const cropEndV = ref({ x: 0, y: 0 })
const cropParams = ref<{ x: number; y: number; w: number; h: number } | null>(null)
const cropFileName = ref('')
const isCtrlHeld = ref(false)

function resetCrop() {
  cropMode.value = false
  isCropping.value = false
  cropParams.value = null
  cropFileName.value = ''
}

function toggleCropMode() {
  cropMode.value = !cropMode.value
  if (!cropMode.value) {
    isCropping.value = false
    cropParams.value = null
    cropFileName.value = ''
  } else {
    resizeMode.value = false // 互斥
  }
}

// === 调整大小（opencv.js） ===
const resizeMode = ref(false)
const cvReady = ref(false)
const cvLoading = ref(false)
const resizeW = ref(0)
const resizeH = ref(0)
const keepRatio = ref(true)
const interpolation = ref('INTER_LINEAR')
const resizeFileName = ref('')
const isResizing = ref(false)

const INTERPOLATION_OPTIONS = [
  { label: '最近邻', value: 'INTER_NEAREST' },
  { label: '双线性', value: 'INTER_LINEAR' },
  { label: '双三次', value: 'INTER_CUBIC' },
  { label: 'Lanczos4', value: 'INTER_LANCZOS4' },
  { label: '区域', value: 'INTER_AREA' },
]

function loadOpenCV(): Promise<void> {
  return new Promise((resolve, reject) => {
    if ((window as any).cv?.Mat) { cvReady.value = true; resolve(); return }
    cvLoading.value = true
    const script = document.createElement('script')
    script.src = 'https://docs.opencv.org/4.x/opencv.js'
    script.onload = () => {
      const timer = setInterval(() => {
        if ((window as any).cv?.Mat) {
          clearInterval(timer)
          cvReady.value = true
          cvLoading.value = false
          resolve()
        }
      }, 100)
    }
    script.onerror = () => { cvLoading.value = false; reject(new Error('OpenCV 加载失败')) }
    document.head.appendChild(script)
  })
}

function resetResize() {
  resizeMode.value = false
  cvLoading.value = false
  resizeW.value = 0
  resizeH.value = 0
  resizeFileName.value = ''
  isResizing.value = false
}

async function toggleResizeMode() {
  resizeMode.value = !resizeMode.value
  if (!resizeMode.value) return
  // 与剪切互斥
  if (cropMode.value) toggleCropMode()
  // 初始化当前图片尺寸
  resizeW.value = imageNaturalSize.value.width
  resizeH.value = imageNaturalSize.value.height
  resizeFileName.value = `_${resizeW.value}_${resizeH.value}.png`
  // 按需加载 opencv
  if (!cvReady.value && !cvLoading.value) {
    try {
      await loadOpenCV()
    } catch (e: any) {
      ElMessage.error(e.message)
    }
  }
}

function updateResizeRatio(changed: 'w' | 'h') {
  if (!keepRatio.value) return
  const nw = imageNaturalSize.value.width
  const nh = imageNaturalSize.value.height
  if (changed === 'w' && nw > 0) {
    resizeH.value = Math.round(resizeW.value * nh / nw)
  } else if (changed === 'h' && nh > 0) {
    resizeW.value = Math.round(resizeH.value * nw / nh)
  }
}

function executeResize() {
  if (!selectedImage.value || isResizing.value) return
  const newW = Math.max(1, Math.min(8192, resizeW.value))
  const newH = Math.max(1, Math.min(8192, resizeH.value))
  isResizing.value = true

  const img = new Image()
  img.onload = () => {
    const output = document.createElement('canvas')
    output.width = newW
    output.height = newH

    if (cvReady.value) {
      try {
        const cv = (window as any).cv
        const src = cv.imread(img)
        const dst = new cv.Mat()
        const size = new cv.Size(newW, newH)
        const interp = cv[interpolation.value] || cv.INTER_LINEAR
        cv.resize(src, dst, size, 0, 0, interp)
        cv.imshow(output, dst)
        src.delete()
        dst.delete()
      } catch (e) {
        ElMessage.error('OpenCV 处理出错，已切换 Canvas 回退')
        const ctx = output.getContext('2d')!
        ctx.drawImage(img, 0, 0, newW, newH)
      }
    } else {
      const ctx = output.getContext('2d')!
      ctx.imageSmoothingEnabled = true
      ctx.imageSmoothingQuality = 'high'
      ctx.drawImage(img, 0, 0, newW, newH)
    }

    const mime = selectedImage.value!.mime || 'image/png'
    const base64 = output.toDataURL(mime).split(',')[1]
    imageStore.addImage(base64, mime, resizeFileName.value || `_${newW}_${newH}`)
    isResizing.value = false
    ElMessage.success(`调整完成 ${newW}×${newH}`)
  }
  img.onerror = () => { isResizing.value = false; ElMessage.error('图片加载失败') }
  img.src = selectedSrc.value
}

// 切换图片时重置
watch(selectedId, () => {
  resetViewerTransform()
  resetCrop()
  resetResize()
})

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

// 带缩放/平移校正的原图坐标映射（viewer px → 原图坐标）
function getZoomedImageCoord(mx: number, my: number, viewer: HTMLElement, rect?: { x: number; y: number; w: number; h: number }) {
  const r = rect || getImageRenderRect(viewer)
  if (!r) return null
  const { width: natW, height: natH } = imageNaturalSize.value
  if (!natW || !natH) return null
  const z = viewerZoom.value
  const px = viewerPanX.value
  const py = viewerPanY.value
  const cx = viewer.clientWidth / 2
  const cy = viewer.clientHeight / 2
  const offsetX = mx - cx - px
  const offsetY = my - cy - py
  const natX = natW / 2 + (offsetX / z) * (natW / r.w)
  const natY = natH / 2 + (offsetY / z) * (natH / r.h)
  return { natX, natY }
}

// 原图坐标 → viewer px（反向映射，用于绘制已完成的选区）
function imageCoordToViewer(natX: number, natY: number, viewer: HTMLElement) {
  const rect = getImageRenderRect(viewer)
  if (!rect) return null
  const { width: natW, height: natH } = imageNaturalSize.value
  if (!natW || !natH) return null
  const z = viewerZoom.value
  const px = viewerPanX.value
  const py = viewerPanY.value
  const cx = viewer.clientWidth / 2
  const cy = viewer.clientHeight / 2
  return {
    x: cx + px + (natX - natW / 2) * z * (rect.w / natW),
    y: cy + py + (natY - natH / 2) * z * (rect.h / natH),
  }
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
  if (isCropping.value) {
    const viewer = viewerEl.value!
    const rect = viewer.getBoundingClientRect()
    const coord = getZoomedImageCoord(e.clientX - rect.left, e.clientY - rect.top, viewer)
    if (coord) cropEndV.value = { x: coord.natX, y: coord.natY }
    return
  }
  if (isDragging.value) return

  if (!magnifierEnabled.value || !viewerEl.value) return
  const rect = viewerEl.value.getBoundingClientRect()
  const mx = e.clientX - rect.left
  const my = e.clientY - rect.top
  mouseX.value = mx
  mouseY.value = my
  showMagnifier.value = true

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
  const vx = e.clientX - rect.left - viewerCenterX
  const vy = e.clientY - rect.top - viewerCenterY
  const oldZ = viewerZoom.value
  const delta = e.deltaY > 0 ? -0.2 : 0.2
  const newZ = Math.max(0.2, Math.min(10, oldZ + delta))
  if (newZ === oldZ) return
  viewerPanX.value = vx * (1 - newZ / oldZ) + viewerPanX.value * newZ / oldZ
  viewerPanY.value = vy * (1 - newZ / oldZ) + viewerPanY.value * newZ / oldZ
  viewerZoom.value = newZ
}

function onMouseDown(e: MouseEvent) {
  if (e.button !== 0) return
  // 剪切模式 + Ctrl → 开始框选（起始点存原图坐标，缩放时不变）
  if (cropMode.value && e.ctrlKey && viewerEl.value) {
    const rect = viewerEl.value.getBoundingClientRect()
    const mx = e.clientX - rect.left
    const my = e.clientY - rect.top
    const coord = getZoomedImageCoord(mx, my, viewerEl.value)
    if (!coord) return
    isCropping.value = true
    showMagnifier.value = false
    cropStartV.value = { x: coord.natX, y: coord.natY }
    cropEndV.value = { x: coord.natX, y: coord.natY }
    cropParams.value = null
    return
  }
  // 否则为平移拖拽
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
  if (isCropping.value) {
    isCropping.value = false
    showMagnifier.value = true
    const x1 = Math.round(cropStartV.value.x)
    const y1 = Math.round(cropStartV.value.y)
    const x2 = Math.round(cropEndV.value.x)
    const y2 = Math.round(cropEndV.value.y)
    const x = Math.min(x1, x2)
    const y = Math.min(y1, y2)
    const w = Math.max(1, Math.abs(x2 - x1))
    const h = Math.max(1, Math.abs(y2 - y1))
    cropParams.value = { x, y, w, h }
    cropFileName.value = `_${x1}_${y1}_${x2}_${y2}.png`
    return
  }
  isDragging.value = false
  window.removeEventListener('mousemove', onDragMove)
  window.removeEventListener('mouseup', onDragEnd)
}

// Ctrl 键跟踪（用于光标切换）
function onWindowKeyDown(e: KeyboardEvent) {
  if (e.key === 'Control') isCtrlHeld.value = true
}
function onWindowKeyUp(e: KeyboardEvent) {
  if (e.key === 'Control') isCtrlHeld.value = false
}

// === 前端 Canvas 剪切 ===
function executeCrop() {
  if (!cropParams.value || !selectedImage.value) return
  const { x, y, w, h } = cropParams.value
  if (w < 1 || h < 1) return

  const img = new Image()
  img.onload = () => {
    const canvas = document.createElement('canvas')
    canvas.width = w
    canvas.height = h
    const ctx = canvas.getContext('2d')!
    ctx.drawImage(img, x, y, w, h, 0, 0, w, h)
    const mime = selectedImage.value!.mime || 'image/png'
    const base64 = canvas.toDataURL(mime).split(',')[1]
    imageStore.addImage(base64, mime, cropFileName.value || `${x}_${y}_${w}_${h}`)
    ElMessage.success('剪切完成')
  }
  img.src = selectedSrc.value
}

// === 计算样式 ===
const isZoomed = computed(() => viewerZoom.value > 1.01)

const imageTransformStyle = computed(() => {
  let cursor = 'default'
  if (cropMode.value && (isCtrlHeld.value || isCropping.value)) {
    cursor = 'crosshair'
  } else if (isZoomed.value) {
    cursor = isDragging.value ? 'grabbing' : 'grab'
  }
  return {
    transform: `translate(${viewerPanX.value}px, ${viewerPanY.value}px) scale(${viewerZoom.value})`,
    cursor,
  }
})

const zoomPercent = computed(() => `${Math.round(viewerZoom.value * 100)}%`)

// 剪切选区覆盖层样式
const cropOverlayStyle = computed(() => {
  if (!cropMode.value) return { display: 'none' }
  const viewer = viewerEl.value
  if (!viewer) return { display: 'none' }

  let vx: number, vy: number, vw: number, vh: number

  if (isCropping.value) {
    const tl = imageCoordToViewer(cropStartV.value.x, cropStartV.value.y, viewer)
    const br = imageCoordToViewer(cropEndV.value.x, cropEndV.value.y, viewer)
    if (!tl || !br) return { display: 'none' }
    vx = Math.min(tl.x, br.x)
    vy = Math.min(tl.y, br.y)
    vw = Math.abs(br.x - tl.x)
    vh = Math.abs(br.y - tl.y)
  } else if (cropParams.value) {
    const cp = cropParams.value
    const tl = imageCoordToViewer(cp.x, cp.y, viewer)
    const br = imageCoordToViewer(cp.x + cp.w, cp.y + cp.h, viewer)
    if (!tl || !br) return { display: 'none' }
    vx = Math.min(tl.x, br.x)
    vy = Math.min(tl.y, br.y)
    vw = Math.abs(br.x - tl.x)
    vh = Math.abs(br.y - tl.y)
  } else {
    return { display: 'none' }
  }

  if (vw < 2 || vh < 2) return { display: 'none' }

  return {
    left: `${vx}px`,
    top: `${vy}px`,
    width: `${vw}px`,
    height: `${vh}px`,
    display: 'block',
  }
})

const lensStyle = computed(() => {
  if (!showMagnifier.value || !selectedImage.value) return { display: 'none' }

  const viewer = viewerEl.value
  if (!viewer) return { display: 'none' }

  const { width: natW, height: natH } = imageNaturalSize.value
  if (!natW || !natH) return { display: 'none' }

  const rect = getImageRenderRect(viewer)
  if (!rect) return { display: 'none' }

  const bounds = getZoomedImageBounds(viewer)
  if (!bounds) return { display: 'none' }
  if (mouseX.value < bounds.left || mouseX.value > bounds.right ||
      mouseY.value < bounds.top || mouseY.value > bounds.bottom) {
    return { display: 'none' }
  }

  const coord = getZoomedImageCoord(mouseX.value, mouseY.value, viewer, rect)
  if (!coord) return { display: 'none' }

  const natX = coord.natX
  const natY = coord.natY

  const bgPosX = MAGNIFIER_SIZE / 2 - natX * MAGNIFIER_ZOOM
  const bgPosY = MAGNIFIER_SIZE / 2 - natY * MAGNIFIER_ZOOM

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

// === 生命周期 ===
onUnmounted(() => {
  window.removeEventListener('mousemove', onDragMove)
  window.removeEventListener('mouseup', onDragEnd)
  window.removeEventListener('keydown', onWindowKeyDown)
  window.removeEventListener('keyup', onWindowKeyUp)
  _pixelCanvas = null
  _pixelCtx = null
})

// 全局 Ctrl 键监听
window.addEventListener('keydown', onWindowKeyDown)
window.addEventListener('keyup', onWindowKeyUp)
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

      <el-tooltip content="剪裁（Ctrl+拖拽选取区域）" placement="right" :show-after="300">
        <el-button :icon="Scissor" circle :type="cropMode ? 'primary' : 'default'" @click="toggleCropMode" />
      </el-tooltip>
      <span class="tool-label" :class="{ active: cropMode }">剪裁</span>

      <el-divider class="tool-divider" />

      <el-tooltip content="调整大小" placement="right" :show-after="300">
        <el-button :icon="FullScreen" circle :type="resizeMode ? 'primary' : 'default'" @click="toggleResizeMode" />
      </el-tooltip>
      <span class="tool-label" :class="{ active: resizeMode }">调整</span>

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
      :class="{ 'is-dragging': isDragging || isCropping }"
      @mousemove="onViewerMouseMove"
      @mouseleave="onViewerMouseLeave"
      @wheel.prevent="onWheel"
      @mousedown="onMouseDown"
      @mouseup="onDragEnd"
      @dblclick="resetViewerTransform"
    >
      <template v-if="selectedImage">
        <!-- 顶部工具栏 -->
        <div class="viewer-toolbar">
          <el-checkbox v-model="magnifierEnabled" size="small">🔍 放大镜</el-checkbox>
          <span v-if="isZoomed" class="zoom-badge">{{ zoomPercent }}</span>
          <span v-if="cropMode" class="mode-badge">✂️ 剪裁</span>
          <span v-if="resizeMode" class="mode-badge">📐 调整</span>
        </div>

        <img
          :src="selectedSrc"
          class="viewer-image"
          :style="imageTransformStyle"
          draggable="false"
          alt="screenshot"
        />

        <!-- 剪切选区覆盖层 -->
        <div class="crop-overlay" :style="cropOverlayStyle" />

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

        <!-- 剪切参数面板 -->
        <div v-if="cropParams && cropMode" class="action-panel" @wheel.stop @dblclick.stop>
          <div class="panel-title">✂️ 剪切</div>
          <div class="crop-params-row">
            <label>X <input v-model.number="cropParams.x" type="number" class="ap-input" /></label>
            <label>Y <input v-model.number="cropParams.y" type="number" class="ap-input" /></label>
            <label>W <input v-model.number="cropParams.w" type="number" class="ap-input" min="1" /></label>
            <label>H <input v-model.number="cropParams.h" type="number" class="ap-input" min="1" /></label>
          </div>
          <div class="panel-row">
            <input v-model="cropFileName" class="ap-input file-input" />
            <el-button size="small" type="primary" @click="executeCrop">✂️ 执行</el-button>
          </div>
        </div>

        <!-- 调整大小面板 -->
        <div v-if="resizeMode" class="action-panel" @wheel.stop @dblclick.stop>
          <div class="panel-title">📐 调整大小</div>
          <div class="panel-info">原图 {{ imageNaturalSize.width }} × {{ imageNaturalSize.height }}</div>
          <div class="crop-params-row">
            <label>W <input :value="resizeW" type="number" class="ap-input" min="1" max="8192" @input="e => { const el = e.target as HTMLInputElement; resizeW = Number(el.value); updateResizeRatio('w') }" /></label>
            <label>H <input :value="resizeH" type="number" class="ap-input" min="1" max="8192" @input="e => { const el = e.target as HTMLInputElement; resizeH = Number(el.value); updateResizeRatio('h') }" /></label>
            <label class="ratio-label">
              <input type="checkbox" v-model="keepRatio" /> 比例
            </label>
          </div>
          <div class="panel-row">
            <span class="panel-label">插值</span>
            <select v-model="interpolation" class="ap-select">
              <option v-for="opt in INTERPOLATION_OPTIONS" :key="opt.value" :value="opt.value">{{ opt.label }} ({{ opt.value }})</option>
            </select>
          </div>
          <div class="panel-row">
            <input v-model="resizeFileName" class="ap-input file-input" />
            <el-button
              size="small"
              type="primary"
              :disabled="cvLoading || isResizing"
              :loading="isResizing"
              @click="executeResize"
            >
              {{ cvLoading ? '加载中...' : '📐 执行' }}
            </el-button>
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

.tool-label.active {
  color: var(--color-primary);
  font-weight: 600;
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
  user-select: none;
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

/* 顶部工具栏 */
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

.mode-badge {
  color: #409eff;
  font-size: 11px;
  background: rgba(64, 158, 255, 0.2);
  padding: 0 6px;
  border-radius: 3px;
  line-height: 18px;
  font-weight: 600;
}

/* 剪切选区覆盖层 */
.crop-overlay {
  position: absolute;
  pointer-events: none;
  z-index: 15;
  border: 2px dashed #409eff;
  background: rgba(64, 158, 255, 0.1);
}

/* 通用操作面板（剪切 + 调整大小） */
.action-panel {
  position: absolute;
  bottom: 8px;
  right: 8px;
  z-index: 30;
  background: rgba(30, 30, 50, 0.92);
  border: 1px solid rgba(255, 255, 255, 0.15);
  border-radius: 6px;
  padding: 10px 12px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-width: 280px;
}

.panel-title {
  font-size: 12px;
  font-weight: 600;
  color: #fff;
  margin-bottom: 2px;
}

.panel-info {
  font-size: 11px;
  color: #888;
  font-family: var(--editor-font-family, monospace);
}

.panel-row {
  display: flex;
  align-items: center;
  gap: 6px;
}

.panel-label {
  font-size: 11px;
  color: #aaa;
  white-space: nowrap;
}

.crop-params-row {
  display: flex;
  gap: 6px;
  align-items: center;
}

.crop-params-row label {
  display: flex;
  align-items: center;
  gap: 2px;
  font-size: 11px;
  color: #aaa;
  font-family: var(--editor-font-family, monospace);
}

.ratio-label {
  display: flex;
  align-items: center;
  gap: 2px;
  font-size: 11px;
  color: #ccc !important;
  cursor: pointer;
  white-space: nowrap;
}

.ratio-label input[type="checkbox"] {
  accent-color: #409eff;
}

.ap-input {
  width: 52px;
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 3px;
  color: #fff;
  font-size: 11px;
  font-family: var(--editor-font-family, monospace);
  padding: 2px 4px;
  outline: none;
  text-align: center;
}

.ap-input:focus {
  border-color: #409eff;
}

.ap-select {
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 3px;
  color: #fff;
  font-size: 11px;
  font-family: var(--editor-font-family, monospace);
  padding: 2px 4px;
  outline: none;
  flex: 1;
}

.ap-select option {
  background: #2a2a4a;
  color: #fff;
}

.file-input {
  flex: 1;
  width: auto;
  text-align: left;
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

/* 放大镜信息栏 */
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
