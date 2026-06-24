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
  triggerFindImage: [code: string]
}>()

function onSelect(id: string) { selectedId.value = id }
function onDelete(id: string) {
  if (selectedId.value === id) selectedId.value = null
  imageStore.removeImage(id)
}
function onClearAll() {
  if (imageStore.images.length === 0) return
  ElMessageBox.confirm('确定清空所有截图？', '清空截图', { confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning' })
    .then(() => { imageStore.clearAll(); selectedId.value = null }).catch(() => {})
}
function onScreenshot() { closeAllPanels(); emit('triggerScreenshot') }

// === 放大镜 ===
const magnifierEnabled = ref(true)
const mouseX = ref(0)
const mouseY = ref(0)
const showMagnifier = ref(false)
const imageNaturalSize = ref({ width: 0, height: 0 })
const viewerEl = ref<HTMLElement | null>(null)
const pixelInfo = ref({ x: 0, y: 0, hex: '#000000' })
let _pixelCanvas: HTMLCanvasElement | null = null
let _pixelCtx: CanvasRenderingContext2D | null = null

// === 缩放 / 平移 ===
const viewerZoom = ref(1)
const viewerPanX = ref(0)
const viewerPanY = ref(0)
const isDragging = ref(false)
const dragStart = ref({ x: 0, y: 0, panX: 0, panY: 0 })
function resetViewerTransform() { viewerZoom.value = 1; viewerPanX.value = 0; viewerPanY.value = 0 }

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
function closeAllPanels() {
  cropMode.value = false
  resizeMode.value = false
  grayMode.value = false
  thresholdMode.value = false
  adaptiveMode.value = false
  inRangeMode.value = false
  findMode.value = false
}

function toggleCropMode() {
  cropMode.value = !cropMode.value
  if (!cropMode.value) {
    isCropping.value = false
    cropParams.value = null
    cropFileName.value = ''
  } else {
    closeAllPanels()
    cropMode.value = true
  }
}

// === 调整大小 ===
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
  { label: '最近邻', value: 'INTER_NEAREST' }, { label: '双线性', value: 'INTER_LINEAR' },
  { label: '双三次', value: 'INTER_CUBIC' }, { label: 'Lanczos4', value: 'INTER_LANCZOS4' },
  { label: '区域', value: 'INTER_AREA' },
]

function loadOpenCV(): Promise<void> {
  return new Promise((resolve, reject) => {
    if ((window as any).cv?.Mat) { cvReady.value = true; resolve(); return }
    cvLoading.value = true
    const script = document.createElement('script')
    script.src = 'https://docs.opencv.org/4.x/opencv.js'
    script.onload = () => {
      const t = setInterval(() => {
        if ((window as any).cv?.Mat) { clearInterval(t); cvReady.value = true; cvLoading.value = false; resolve() }
      }, 100)
    }
    script.onerror = () => { cvLoading.value = false; reject(new Error('OpenCV 加载失败')) }
    document.head.appendChild(script)
  })
}

function ensureCV() {
  if (!cvReady.value && !cvLoading.value) loadOpenCV().catch(e => ElMessage.error(e.message))
}

function resetResize() { resizeMode.value = false; resizeW.value = 0; resizeH.value = 0; resizeFileName.value = ''; isResizing.value = false }
async function toggleResizeMode() {
  resizeMode.value = !resizeMode.value
  if (!resizeMode.value) return
  closeAllPanels()
  resizeMode.value = true
  resizeW.value = imageNaturalSize.value.width
  resizeH.value = imageNaturalSize.value.height
  resizeFileName.value = `_${resizeW.value}_${resizeH.value}.png`
  ensureCV()
}
function updateResizeRatio(changed: 'w' | 'h') {
  if (!keepRatio.value) return
  const nw = imageNaturalSize.value.width, nh = imageNaturalSize.value.height
  if (changed === 'w' && nw > 0) resizeH.value = Math.round(resizeW.value * nh / nw)
  else if (changed === 'h' && nh > 0) resizeW.value = Math.round(resizeH.value * nw / nh)
}
function executeResize() {
  if (!selectedImage.value || isResizing.value) return
  const newW = Math.max(1, Math.min(8192, resizeW.value)), newH = Math.max(1, Math.min(8192, resizeH.value))
  isResizing.value = true
  const img = new Image()
  img.onload = () => {
    const output = document.createElement('canvas'); output.width = newW; output.height = newH
    if (cvReady.value) {
      try {
        const cv = (window as any).cv; const src = cv.imread(img); const dst = new cv.Mat()
        const size = new cv.Size(newW, newH); const interp = cv[interpolation.value] || cv.INTER_LINEAR
        cv.resize(src, dst, size, 0, 0, interp); cv.imshow(output, dst); src.delete(); dst.delete()
      } catch { ElMessage.error('OpenCV 出错，已切换 Canvas 回退')
        output.getContext('2d')!.drawImage(img, 0, 0, newW, newH) }
    } else { output.getContext('2d')!.drawImage(img, 0, 0, newW, newH) }
    const base64 = output.toDataURL('image/png').split(',')[1]
    imageStore.addImage(base64, 'image/png', resizeFileName.value || `_${newW}_${newH}`)
    isResizing.value = false; ElMessage.success(`调整完成 ${newW}×${newH}`)
  }
  img.onerror = () => { isResizing.value = false; ElMessage.error('图片加载失败') }
  img.src = selectedSrc.value
}

// === 图像处理（分拆为独立按钮） ===
const grayMode = ref(false)
const thresholdMode = ref(false)
const adaptiveMode = ref(false)
const grayFileName = ref('_gray.png')
const processThreshFileName = ref('_thresh_128.png')
const processAdaptFileName = ref('_adapt_11_2.png')
const processThresh = ref(128)
const processMaxval = ref(255)
const processBlockSize = ref(11)
const processC = ref(2)
const processAdaptMethod = ref('ADAPTIVE_THRESH_GAUSSIAN_C')
const isProcessing = ref(false)

// inRange 二值化
const inRangeMode = ref(false)
const inRangeLower = ref({ r: 255, g: 0, b: 0 })
const inRangeUpper = ref({ r: 255, g: 255, b: 255 })
const inRangeFileName = ref('_inrange.png')
const isPicking = ref<'lower' | 'upper' | null>(null)

function pickColor() {
  const hex = pixelInfo.value.hex
  if (!hex || hex === '#000000') return
  const r = parseInt(hex.slice(1, 3), 16)
  const g = parseInt(hex.slice(3, 5), 16)
  const b = parseInt(hex.slice(5, 7), 16)
  if (isPicking.value === 'lower') inRangeLower.value = { r, g, b }
  else if (isPicking.value === 'upper') inRangeUpper.value = { r, g, b }
  // 取色模式保持活跃，可多次点击覆盖前次结果，按钮切换退出
}

function executeInRange() {
  if (!selectedImage.value || isProcessing.value || !cvReady.value) return
  isProcessing.value = true
  const img = new Image()
  img.onload = () => {
    const output = document.createElement('canvas')
    try {
      const cv = (window as any).cv; const src = cv.imread(img)
      const rgb = new cv.Mat()
      cv.cvtColor(src, rgb, cv.COLOR_RGBA2RGB)
      const lower = cv.matFromArray(1, 1, cv.CV_8UC3, [inRangeLower.value.b, inRangeLower.value.g, inRangeLower.value.r])
      const upper = cv.matFromArray(1, 1, cv.CV_8UC3, [inRangeUpper.value.b, inRangeUpper.value.g, inRangeUpper.value.r])
      const mask = new cv.Mat()
      cv.inRange(rgb, lower, upper, mask)
      cv.imshow(output, mask)
      src.delete(); rgb.delete(); lower.delete(); upper.delete(); mask.delete()
      const base64 = output.toDataURL('image/png').split(',')[1]
      imageStore.addImage(base64, 'image/png', inRangeFileName.value)
      isProcessing.value = false; ElMessage.success('二值化完成')
    } catch (e) { isProcessing.value = false; ElMessage.error('处理出错: ' + String(e)) }
  }
  img.onerror = () => { isProcessing.value = false; ElMessage.error('图片加载失败') }
  img.src = selectedSrc.value
}

const ADAPT_METHODS = [
  { label: '高斯', value: 'ADAPTIVE_THRESH_GAUSSIAN_C' },
  { label: '均值', value: 'ADAPTIVE_THRESH_MEAN_C' },
]

function executeProcess(type: 'grayscale' | 'otsu', fileName: string) {
  if (!selectedImage.value || isProcessing.value || !cvReady.value) return
  isProcessing.value = true
  const img = new Image()
  img.onload = () => {
    const output = document.createElement('canvas')
    try {
      const cv = (window as any).cv; const src = cv.imread(img); const gray = new cv.Mat()
      cv.cvtColor(src, gray, cv.COLOR_RGBA2GRAY)
      let result: any
      if (type === 'grayscale') {
        result = gray
      } else {
        result = new cv.Mat()
        cv.threshold(gray, result, 0, 255, cv.THRESH_BINARY + cv.THRESH_OTSU)
        gray.delete()
      }
      cv.imshow(output, result)
      const base64 = output.toDataURL('image/png').split(',')[1]
      imageStore.addImage(base64, 'image/png', fileName)
      src.delete(); result.delete(); isProcessing.value = false; ElMessage.success('处理完成')
    } catch (e) { isProcessing.value = false; ElMessage.error('处理出错: ' + String(e)) }
  }
  img.onerror = () => { isProcessing.value = false; ElMessage.error('图片加载失败') }
  img.src = selectedSrc.value
}

function executeThreshold() {
  if (!selectedImage.value || isProcessing.value || !cvReady.value) return
  isProcessing.value = true
  const img = new Image()
  img.onload = () => {
    const output = document.createElement('canvas')
    try {
      const cv = (window as any).cv; const src = cv.imread(img); const gray = new cv.Mat()
      cv.cvtColor(src, gray, cv.COLOR_RGBA2GRAY)
      const result = new cv.Mat()
      cv.threshold(gray, result, processThresh.value, processMaxval.value, cv.THRESH_BINARY)
      cv.imshow(output, result)
      const base64 = output.toDataURL('image/png').split(',')[1]
      imageStore.addImage(base64, 'image/png', processThreshFileName.value)
      src.delete(); gray.delete(); result.delete(); isProcessing.value = false; ElMessage.success('阈值处理完成')
    } catch (e) { isProcessing.value = false; ElMessage.error('处理出错: ' + String(e)) }
  }
  img.onerror = () => { isProcessing.value = false; ElMessage.error('图片加载失败') }
  img.src = selectedSrc.value
}

function executeAdaptive() {
  if (!selectedImage.value || isProcessing.value || !cvReady.value) return
  isProcessing.value = true
  const img = new Image()
  img.onload = () => {
    const output = document.createElement('canvas')
    try {
      const cv = (window as any).cv; const src = cv.imread(img); const gray = new cv.Mat()
      cv.cvtColor(src, gray, cv.COLOR_RGBA2GRAY)
      const result = new cv.Mat()
      cv.adaptiveThreshold(gray, result, processMaxval.value, cv[processAdaptMethod.value], cv.THRESH_BINARY, processBlockSize.value | 1, processC.value)
      cv.imshow(output, result)
      const base64 = output.toDataURL('image/png').split(',')[1]
      imageStore.addImage(base64, 'image/png', processAdaptFileName.value)
      src.delete(); gray.delete(); result.delete(); isProcessing.value = false; ElMessage.success('自适应阈值完成')
    } catch (e) { isProcessing.value = false; ElMessage.error('处理出错: ' + String(e)) }
  }
  img.onerror = () => { isProcessing.value = false; ElMessage.error('图片加载失败') }
  img.src = selectedSrc.value
}

// === 图片查找 ===
const findMode = ref(false)
const findRegion = ref({ x: 0, y: 0, w: 0, h: 0 })
const findThreshold = ref(0.9)
const findResult = ref('')

function parseCropFileName(name: string) {
  if (!name) return null
  const m = name.match(/_(\d+)_(\d+)_(\d+)_(\d+)\.\w+$/)
  if (!m) return null
  const x1 = +m[1], y1 = +m[2], x2 = +m[3], y2 = +m[4]
  return { x: Math.min(x1, x2), y: Math.min(y1, y2), w: Math.abs(x2 - x1), h: Math.abs(y2 - y1) }
}

function refreshFindRegion() {
  findResult.value = ''
  const parsed = parseCropFileName(selectedImage.value?.code || '')
  if (parsed) {
    const expX = 50, expY = Math.max(1, Math.round((imageNaturalSize.value.height || 1920) / 10))
    findRegion.value = { x: Math.max(0, parsed.x - expX), y: Math.max(0, parsed.y - expY), w: parsed.w + expX * 2, h: parsed.h + expY * 2 }
  } else {
    findRegion.value = { x: 0, y: 0, w: 0, h: 0 }
  }
}

function openFind() {
  findMode.value = !findMode.value
  if (!findMode.value) return
  closeAllPanels()
  findMode.value = true
  refreshFindRegion()
}

async function executeFind() {
  if (!selectedImage.value || codeStore.isExecuting) return
  const { x, y, w, h } = findRegion.value
  const { FIND_TEMPLATE } = await import('@/types/autojs')
  const code = FIND_TEMPLATE(selectedImage.value.data,
    w > 0 && h > 0 ? [x, y, w, h] : [],
    findThreshold.value)
  emit('triggerFindImage', code)
}

// 切换面板：互斥 + 确保 opencv 加载
function openGray() {
  grayMode.value = !grayMode.value
  if (!grayMode.value) return
  closeAllPanels()
  grayMode.value = true
  ensureCV()
}
function openInRange() {
  inRangeMode.value = !inRangeMode.value
  if (!inRangeMode.value) return
  closeAllPanels()
  inRangeMode.value = true
  ensureCV()
}
function openThreshold() {
  thresholdMode.value = !thresholdMode.value
  if (!thresholdMode.value) return
  closeAllPanels()
  thresholdMode.value = true
  ensureCV()
}
function openAdaptive() {
  adaptiveMode.value = !adaptiveMode.value
  if (!adaptiveMode.value) return
  closeAllPanels()
  adaptiveMode.value = true
  ensureCV()
}

// 执行结果回填找图面板
watch(() => codeStore.lastResult, (r) => {
  if (r && findMode.value && r.dataType === 'text') findResult.value = r.data
})

// 图片选中变化：重置缩放/剪切，找图模式开启时更新区域
watch(selectedId, () => {
  resetViewerTransform()
  resetCrop()
  if (findMode.value) refreshFindRegion()
})

// 新图片加载完成后同步 resize 面板尺寸
watch(imageNaturalSize, (size) => {
  if (resizeMode.value && size.width > 0 && size.height > 0) {
    resizeW.value = size.width
    resizeH.value = size.height
    resizeFileName.value = `_${size.width}_${size.height}.png`
  }
})

// === 坐标工具函数 ===
function getImageRenderRect(viewer: HTMLElement) {
  const { width: natW, height: natH } = imageNaturalSize.value
  if (!natW || !natH) return null
  const viewerW = viewer.clientWidth, viewerH = viewer.clientHeight
  const imgAspect = natW / natH, viewAspect = viewerW / viewerH
  let w: number, h: number, x: number, y: number
  if (imgAspect > viewAspect) { w = viewerW; h = viewerW / imgAspect; x = 0; y = (viewerH - h) / 2 }
  else { h = viewerH; w = viewerH * imgAspect; x = (viewerW - w) / 2; y = 0 }
  return { x, y, w, h }
}

function getZoomedImageCoord(mx: number, my: number, viewer: HTMLElement, rect?: { x: number; y: number; w: number; h: number }) {
  const r = rect || getImageRenderRect(viewer)
  if (!r) return null
  const { width: natW, height: natH } = imageNaturalSize.value
  if (!natW || !natH) return null
  const z = viewerZoom.value, px = viewerPanX.value, py = viewerPanY.value
  const cx = viewer.clientWidth / 2, cy = viewer.clientHeight / 2
  const offsetX = mx - cx - px, offsetY = my - cy - py
  const natX = natW / 2 + (offsetX / z) * (natW / r.w), natY = natH / 2 + (offsetY / z) * (natH / r.h)
  return { natX, natY }
}

function imageCoordToViewer(natX: number, natY: number, viewer: HTMLElement) {
  const rect = getImageRenderRect(viewer)
  if (!rect) return null
  const { width: natW, height: natH } = imageNaturalSize.value
  if (!natW || !natH) return null
  const z = viewerZoom.value, px = viewerPanX.value, py = viewerPanY.value
  const cx = viewer.clientWidth / 2, cy = viewer.clientHeight / 2
  return { x: cx + px + (natX - natW / 2) * z * (rect.w / natW), y: cy + py + (natY - natH / 2) * z * (rect.h / natH) }
}

function getZoomedImageBounds(viewer: HTMLElement) {
  const rect = getImageRenderRect(viewer)
  if (!rect || !imageNaturalSize.value.width || !imageNaturalSize.value.height) return null
  const z = viewerZoom.value, px = viewerPanX.value, py = viewerPanY.value
  const cx = viewer.clientWidth / 2, cy = viewer.clientHeight / 2
  return { left: cx + px - rect.w * z / 2, right: cx + px + rect.w * z / 2, top: cy + py - rect.h * z / 2, bottom: cy + py + rect.h * z / 2 }
}

// === 图片加载 ===
function loadImageNaturalSize(src: string) {
  const img = new Image()
  img.onload = () => { imageNaturalSize.value = { width: img.naturalWidth, height: img.naturalHeight } }
  img.onerror = () => { imageNaturalSize.value = { width: 0, height: 0 } }
  img.src = src
}
watch(selectedSrc, (src) => { if (src) { loadImageNaturalSize(src); loadPixelCanvas(src) } })

function loadPixelCanvas(src: string) {
  const img = new Image()
  img.onload = () => {
    _pixelCanvas = document.createElement('canvas'); _pixelCanvas.width = img.naturalWidth; _pixelCanvas.height = img.naturalHeight
    _pixelCtx = _pixelCanvas.getContext('2d'); _pixelCtx!.drawImage(img, 0, 0)
  }
  img.onerror = () => { _pixelCanvas = null; _pixelCtx = null }; img.src = src
}

function samplePixel(natX: number, natY: number) {
  if (!_pixelCtx || !_pixelCanvas) return
  const x = Math.round(natX), y = Math.round(natY)
  const cx = Math.max(0, Math.min(x, _pixelCanvas.width - 1)), cy = Math.max(0, Math.min(y, _pixelCanvas.height - 1))
  const data = _pixelCtx.getImageData(cx, cy, 1, 1).data
  pixelInfo.value = { x: cx, y: cy, hex: '#' + [data[0], data[1], data[2]].map(v => v.toString(16).padStart(2, '0')).join('').toUpperCase() }
}

// === 鼠标事件 ===
function onViewerMouseMove(e: MouseEvent) {
  if (isCropping.value) {
    const rect = viewerEl.value!.getBoundingClientRect()
    const coord = getZoomedImageCoord(e.clientX - rect.left, e.clientY - rect.top, viewerEl.value!)
    if (coord) cropEndV.value = { x: coord.natX, y: coord.natY }; return
  }
  if (isDragging.value) return
  if (!magnifierEnabled.value || !viewerEl.value) return
  const rect = viewerEl.value.getBoundingClientRect(), mx = e.clientX - rect.left, my = e.clientY - rect.top
  mouseX.value = mx; mouseY.value = my; showMagnifier.value = true
  const viewer = viewerEl.value, imgRect = getImageRenderRect(viewer), bounds = getZoomedImageBounds(viewer)
  if (!imgRect || !bounds) return
  if (mx < bounds.left || mx > bounds.right || my < bounds.top || my > bounds.bottom) return
  const coord = getZoomedImageCoord(mx, my, viewer, imgRect)
  if (coord) samplePixel(coord.natX, coord.natY)
}
function onViewerMouseLeave() { showMagnifier.value = false }
function onWheel(e: WheelEvent) {
  const viewer = viewerEl.value; if (!viewer) return
  const rect = viewer.getBoundingClientRect(), cx = viewer.clientWidth / 2, cy = viewer.clientHeight / 2
  const vx = e.clientX - rect.left - cx, vy = e.clientY - rect.top - cy
  const oldZ = viewerZoom.value, delta = e.deltaY > 0 ? -0.2 : 0.2, newZ = Math.max(0.2, Math.min(10, oldZ + delta))
  if (newZ === oldZ) return
  viewerPanX.value = vx * (1 - newZ / oldZ) + viewerPanX.value * newZ / oldZ
  viewerPanY.value = vy * (1 - newZ / oldZ) + viewerPanY.value * newZ / oldZ
  viewerZoom.value = newZ
}
function onMouseDown(e: MouseEvent) {
  if (e.button !== 0) return
  // 取色模式：点击图片取色，但忽略面板内的点击
  if (isPicking.value && viewerEl.value && !(e.target as HTMLElement).closest('.action-panel')) {
    pickColor(); return
  }
  if (cropMode.value && e.ctrlKey && viewerEl.value) {
    const rect = viewerEl.value.getBoundingClientRect(), mx = e.clientX - rect.left, my = e.clientY - rect.top
    const coord = getZoomedImageCoord(mx, my, viewerEl.value); if (!coord) return
    isCropping.value = true; showMagnifier.value = false
    cropStartV.value = { x: coord.natX, y: coord.natY }; cropEndV.value = { x: coord.natX, y: coord.natY }; cropParams.value = null; return
  }
  isDragging.value = true; showMagnifier.value = false
  dragStart.value = { x: e.clientX, y: e.clientY, panX: viewerPanX.value, panY: viewerPanY.value }
  window.addEventListener('mousemove', onDragMove); window.addEventListener('mouseup', onDragEnd)
}
function onDragMove(e: MouseEvent) {
  if (!isDragging.value) return
  viewerPanX.value = dragStart.value.panX + e.clientX - dragStart.value.x
  viewerPanY.value = dragStart.value.panY + e.clientY - dragStart.value.y
}
function onDragEnd() {
  if (isCropping.value) {
    isCropping.value = false; showMagnifier.value = true
    const x1 = Math.round(cropStartV.value.x), y1 = Math.round(cropStartV.value.y)
    const x2 = Math.round(cropEndV.value.x), y2 = Math.round(cropEndV.value.y)
    const x = Math.min(x1, x2), y = Math.min(y1, y2), w = Math.max(1, Math.abs(x2 - x1)), h = Math.max(1, Math.abs(y2 - y1))
    cropParams.value = { x, y, w, h }; cropFileName.value = `_${x1}_${y1}_${x2}_${y2}.png`; return
  }
  isDragging.value = false; window.removeEventListener('mousemove', onDragMove); window.removeEventListener('mouseup', onDragEnd)
}
function onWindowKeyDown(e: KeyboardEvent) { if (e.key === 'Control') isCtrlHeld.value = true }
function onWindowKeyUp(e: KeyboardEvent) { if (e.key === 'Control') isCtrlHeld.value = false }

// === 剪切 ===
function executeCrop() {
  if (!cropParams.value || !selectedImage.value) return
  const { x, y, w, h } = cropParams.value; if (w < 1 || h < 1) return
  const img = new Image()
  img.onload = () => {
    const canvas = document.createElement('canvas'); canvas.width = w; canvas.height = h
    canvas.getContext('2d')!.drawImage(img, x, y, w, h, 0, 0, w, h)
    const base64 = canvas.toDataURL('image/png').split(',')[1]
    imageStore.addImage(base64, 'image/png', cropFileName.value || `${x}_${y}_${w}_${h}`); ElMessage.success('剪切完成')
  }
  img.src = selectedSrc.value
}

// === 计算样式 ===
const isZoomed = computed(() => viewerZoom.value > 1.01)
const imageTransformStyle = computed(() => {
  let cursor = 'default'
  if (cropMode.value && (isCtrlHeld.value || isCropping.value)) cursor = 'crosshair'
  else if (isZoomed.value) cursor = isDragging.value ? 'grabbing' : 'grab'
  return { transform: `translate(${viewerPanX.value}px, ${viewerPanY.value}px) scale(${viewerZoom.value})`, cursor }
})
const zoomPercent = computed(() => `${Math.round(viewerZoom.value * 100)}%`)

const cropOverlayStyle = computed(() => {
  if (!cropMode.value) return { display: 'none' }
  const viewer = viewerEl.value; if (!viewer) return { display: 'none' }
  let vx: number, vy: number, vw: number, vh: number
  if (isCropping.value) {
    const tl = imageCoordToViewer(cropStartV.value.x, cropStartV.value.y, viewer)
    const br = imageCoordToViewer(cropEndV.value.x, cropEndV.value.y, viewer)
    if (!tl || !br) return { display: 'none' }
    vx = Math.min(tl.x, br.x); vy = Math.min(tl.y, br.y); vw = Math.abs(br.x - tl.x); vh = Math.abs(br.y - tl.y)
  } else if (cropParams.value) {
    const cp = cropParams.value
    const tl = imageCoordToViewer(cp.x, cp.y, viewer), br = imageCoordToViewer(cp.x + cp.w, cp.y + cp.h, viewer)
    if (!tl || !br) return { display: 'none' }
    vx = Math.min(tl.x, br.x); vy = Math.min(tl.y, br.y); vw = Math.abs(br.x - tl.x); vh = Math.abs(br.y - tl.y)
  } else return { display: 'none' }
  if (vw < 2 || vh < 2) return { display: 'none' }
  return { left: `${vx}px`, top: `${vy}px`, width: `${vw}px`, height: `${vh}px`, display: 'block' }
})

const lensStyle = computed(() => {
  if (!showMagnifier.value || !selectedImage.value) return { display: 'none' }
  const viewer = viewerEl.value; if (!viewer) return { display: 'none' }
  const { width: natW, height: natH } = imageNaturalSize.value; if (!natW || !natH) return { display: 'none' }
  const rect = getImageRenderRect(viewer); if (!rect) return { display: 'none' }
  const bounds = getZoomedImageBounds(viewer); if (!bounds) return { display: 'none' }
  if (mouseX.value < bounds.left || mouseX.value > bounds.right || mouseY.value < bounds.top || mouseY.value > bounds.bottom) return { display: 'none' }
  const coord = getZoomedImageCoord(mouseX.value, mouseY.value, viewer, rect); if (!coord) return { display: 'none' }
  const natX = coord.natX, natY = coord.natY, bgPosX = MAGNIFIER_SIZE / 2 - natX * MAGNIFIER_ZOOM, bgPosY = MAGNIFIER_SIZE / 2 - natY * MAGNIFIER_ZOOM
  const viewerW = viewer.clientWidth, viewerH = viewer.clientHeight
  let lensLeft = mouseX.value + 15, lensTop = mouseY.value + 15
  if (lensLeft + MAGNIFIER_SIZE > viewerW) lensLeft = mouseX.value - MAGNIFIER_SIZE - 15
  if (lensTop + MAGNIFIER_SIZE > viewerH) lensTop = mouseY.value - MAGNIFIER_SIZE - 15
  return { backgroundImage: `url(${selectedSrc.value})`, backgroundSize: `${natW * MAGNIFIER_ZOOM}px ${natH * MAGNIFIER_ZOOM}px`, backgroundPosition: `${bgPosX}px ${bgPosY}px`, width: `${MAGNIFIER_SIZE}px`, height: `${MAGNIFIER_SIZE}px`, left: `${lensLeft}px`, top: `${lensTop}px`, display: 'block' }
})

// === 生命周期 ===
onUnmounted(() => {
  window.removeEventListener('mousemove', onDragMove); window.removeEventListener('mouseup', onDragEnd)
  window.removeEventListener('keydown', onWindowKeyDown); window.removeEventListener('keyup', onWindowKeyUp)
  _pixelCanvas = null; _pixelCtx = null
})
window.addEventListener('keydown', onWindowKeyDown); window.addEventListener('keyup', onWindowKeyUp)
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

      <el-tooltip content="灰度化" placement="right" :show-after="300">
        <el-button circle :type="grayMode ? 'primary' : 'default'" @click="openGray">
          <span style="font-size:16px">🌫️</span>
        </el-button>
      </el-tooltip>
      <span class="tool-label" :class="{ active: grayMode }">灰度</span>

      <el-tooltip content="阈值化" placement="right" :show-after="300">
        <el-button circle :type="thresholdMode ? 'primary' : 'default'" @click="openThreshold">
          <span style="font-size:16px">⚫</span>
        </el-button>
      </el-tooltip>
      <span class="tool-label" :class="{ active: thresholdMode }">阈值</span>

      <el-tooltip content="自适应阈值化" placement="right" :show-after="300">
        <el-button circle :type="adaptiveMode ? 'primary' : 'default'" @click="openAdaptive">
          <span style="font-size:16px">🔲</span>
        </el-button>
      </el-tooltip>
      <span class="tool-label" :class="{ active: adaptiveMode }">自适应</span>

      <el-tooltip content="二值化(inRange)" placement="right" :show-after="300">
        <el-button circle :type="inRangeMode ? 'primary' : 'default'" @click="openInRange">
          <span style="font-size:16px">⬛</span>
        </el-button>
      </el-tooltip>
      <span class="tool-label" :class="{ active: inRangeMode }">二值化</span>

      <el-divider class="tool-divider" />

      <el-tooltip content="图片查找" placement="right" :show-after="300">
        <el-button circle :type="findMode ? 'primary' : 'default'" @click="openFind">
          <span style="font-size:16px">🔍</span>
        </el-button>
      </el-tooltip>
      <span class="tool-label" :class="{ active: findMode }">找图</span>

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
          <ImageCard v-for="img in imageStore.images" :key="img.id" :image="img" :selected="img.id === selectedId" @select="onSelect" @delete="onDelete" />
        </template>
        <div v-else class="list-empty"><span class="empty-text">暂无截图</span></div>
      </div>
      <div class="list-footer">
        <el-button v-if="imageStore.images.length > 0" size="small" text type="danger" :icon="Delete" @click="onClearAll">清空全部</el-button>
      </div>
    </div>

    <!-- 图片展示区 -->
    <div ref="viewerEl" class="image-viewer" :class="{ 'is-dragging': isDragging || isCropping }"
      @mousemove="onViewerMouseMove" @mouseleave="onViewerMouseLeave" @wheel.prevent="onWheel"
      @mousedown="onMouseDown" @mouseup="onDragEnd" @dblclick="resetViewerTransform">
      <template v-if="selectedImage">
        <div class="viewer-toolbar">
          <el-checkbox v-model="magnifierEnabled" size="small">🔍 放大镜</el-checkbox>
          <span v-if="isZoomed" class="zoom-badge">{{ zoomPercent }}</span>
          <span v-if="cropMode" class="mode-badge">✂️ 剪裁</span>
          <span v-if="resizeMode" class="mode-badge">📐 调整</span>
          <span v-if="grayMode" class="mode-badge">🌫️ 灰度</span>
          <span v-if="thresholdMode" class="mode-badge">⚫ 阈值</span>
          <span v-if="adaptiveMode" class="mode-badge">🔲 自适应</span>
          <span v-if="inRangeMode" class="mode-badge">⬛ 二值化</span>
          <span v-if="findMode" class="mode-badge">🔍 找图</span>
        </div>

        <img :src="selectedSrc" class="viewer-image" :style="imageTransformStyle" draggable="false" alt="screenshot" />
        <div class="crop-overlay" :style="cropOverlayStyle" />

        <!-- 放大镜 -->
        <div v-show="showMagnifier && magnifierEnabled" class="magnifier-lens" :style="lensStyle">
          <div class="pixel-grid" /><div class="magnifier-crosshair" />
          <div class="magnifier-info">
            <span class="mi-coords">({{ pixelInfo.x }}, {{ pixelInfo.y }})</span>
            <span class="mi-swatch" :style="{ backgroundColor: pixelInfo.hex }" /><span class="mi-hex">{{ pixelInfo.hex }}</span>
          </div>
        </div>

        <!-- 剪切面板 -->
        <div v-if="cropParams && cropMode" class="action-panel" @wheel.stop @dblclick.stop>
          <div class="panel-title">✂️ 剪切</div>
          <div class="crop-params-row">
            <label>X <input v-model.number="cropParams.x" type="number" class="ap-input" /></label>
            <label>Y <input v-model.number="cropParams.y" type="number" class="ap-input" /></label>
            <label>W <input v-model.number="cropParams.w" type="number" class="ap-input" min="1" /></label>
            <label>H <input v-model.number="cropParams.h" type="number" class="ap-input" min="1" /></label>
          </div>
          <div class="panel-row"><input v-model="cropFileName" class="ap-input file-input" @keydown.enter="executeCrop" /><el-button size="small" type="primary" @click="executeCrop">✂️ 执行</el-button></div>
        </div>

        <!-- 灰度面板 -->
        <div v-if="grayMode" class="action-panel" @wheel.stop @dblclick.stop>
          <div class="panel-title">🌫️ 灰度化</div>
          <div class="panel-info">将彩色图片转为灰度图</div>
          <div class="panel-row">
            <input v-model="grayFileName" class="ap-input file-input" @keydown.enter="executeProcess('grayscale', grayFileName)" />
            <el-button size="small" type="primary" :disabled="!cvReady || isProcessing" :loading="isProcessing" @click="executeProcess('grayscale', grayFileName)">🌫️ 执行</el-button>
          </div>
        </div>

        <!-- 阈值面板 -->
        <div v-if="thresholdMode" class="action-panel" @wheel.stop @dblclick.stop>
          <div class="panel-title">⚫ 阈值化</div>
          <div class="crop-params-row">
            <label>阈值 <input v-model.number="processThresh" type="number" class="ap-input" min="0" max="255" /></label>
            <label>最大 <input v-model.number="processMaxval" type="number" class="ap-input" min="0" max="255" /></label>
          </div>
          <div class="panel-row">
            <input v-model="processThreshFileName" class="ap-input file-input" @keydown.enter="executeThreshold" />
            <el-button size="small" type="primary" :disabled="!cvReady || isProcessing" :loading="isProcessing" @click="executeThreshold">⚫ 执行</el-button>
          </div>
        </div>

        <!-- 自适应阈值面板 -->
        <div v-if="adaptiveMode" class="action-panel" @wheel.stop @dblclick.stop>
          <div class="panel-title">🔲 自适应阈值化</div>
          <div class="crop-params-row">
            <label>最大 <input v-model.number="processMaxval" type="number" class="ap-input" min="0" max="255" /></label>
            <label>块 <input v-model.number="processBlockSize" type="number" class="ap-input" min="3" max="99" step="2" /></label>
            <label>C <input v-model.number="processC" type="number" class="ap-input" min="-50" max="50" /></label>
          </div>
          <div class="panel-row">
            <span class="panel-label">方法</span>
            <select v-model="processAdaptMethod" class="ap-select"><option v-for="opt in ADAPT_METHODS" :key="opt.value" :value="opt.value">{{ opt.label }}</option></select>
          </div>
          <div class="panel-row">
            <input v-model="processAdaptFileName" class="ap-input file-input" @keydown.enter="executeAdaptive" />
            <el-button size="small" type="primary" :disabled="!cvReady || isProcessing" :loading="isProcessing" @click="executeAdaptive">🔲 执行</el-button>
          </div>
        </div>

        <!-- 二值化面板 (inRange) -->
        <div v-if="inRangeMode" class="action-panel" @wheel.stop @dblclick.stop>
          <div class="panel-title">⬛ 二值化 (inRange)</div>
          <div class="panel-info">点击取色按钮后点击图片选取颜色</div>
          <div class="panel-row" style="gap:4px">
            <span class="panel-label">下界</span>
            <span class="color-swatch" :style="{ backgroundColor: `rgb(${inRangeLower.r},${inRangeLower.g},${inRangeLower.b})` }" />
            <input :value="'#' + [inRangeLower.r,inRangeLower.g,inRangeLower.b].map(v=>v.toString(16).padStart(2,'0')).join('')" type="text" class="ap-input" style="width:80px" @input="e => { const h = (e.target as HTMLInputElement).value.replace('#',''); if(/^[0-9a-fA-F]{6}$/.test(h)) { inRangeLower.value = { r: parseInt(h.slice(0,2),16), g: parseInt(h.slice(2,4),16), b: parseInt(h.slice(4,6),16) } } }" />
            <el-button size="small" :type="isPicking === 'lower' ? 'primary' : 'default'" @click="isPicking = isPicking === 'lower' ? null : 'lower'">
              {{ isPicking === 'lower' ? '取色中' : '取色' }}
            </el-button>
          </div>
          <div class="panel-row" style="gap:4px">
            <span class="panel-label">上界</span>
            <span class="color-swatch" :style="{ backgroundColor: `rgb(${inRangeUpper.r},${inRangeUpper.g},${inRangeUpper.b})` }" />
            <input :value="'#' + [inRangeUpper.r,inRangeUpper.g,inRangeUpper.b].map(v=>v.toString(16).padStart(2,'0')).join('')" type="text" class="ap-input" style="width:80px" @input="e => { const h = (e.target as HTMLInputElement).value.replace('#',''); if(/^[0-9a-fA-F]{6}$/.test(h)) { inRangeUpper.value = { r: parseInt(h.slice(0,2),16), g: parseInt(h.slice(2,4),16), b: parseInt(h.slice(4,6),16) } } }" />
            <el-button size="small" :type="isPicking === 'upper' ? 'primary' : 'default'" @click="isPicking = isPicking === 'upper' ? null : 'upper'">
              {{ isPicking === 'upper' ? '取色中' : '取色' }}
            </el-button>
          </div>
          <div class="panel-row">
            <input v-model="inRangeFileName" class="ap-input file-input" @keydown.enter="executeInRange" />
            <el-button size="small" type="primary" :disabled="!cvReady || cvLoading || isProcessing" :loading="isProcessing" @click="executeInRange">{{ cvLoading ? '加载中...' : '⬛ 执行' }}</el-button>
          </div>
        </div>

        <!-- 找图面板 -->
        <div v-if="findMode" class="action-panel" @wheel.stop @dblclick.stop>
          <div class="panel-title">🔍 图片查找</div>
          <div class="panel-info" style="margin-bottom:2px">模板: {{ selectedImage?.code?.length < 60 ? selectedImage?.code : (selectedImage?.code?.slice(0, 40) + '...') }}</div>
          <div class="crop-params-row">
            <label>X <input v-model.number="findRegion.x" type="number" class="ap-input" min="0" /></label>
            <label>Y <input v-model.number="findRegion.y" type="number" class="ap-input" min="0" /></label>
            <label>W <input v-model.number="findRegion.w" type="number" class="ap-input" min="0" /></label>
            <label>H <input v-model.number="findRegion.h" type="number" class="ap-input" min="0" /></label>
          </div>
          <div class="panel-row">
            <span class="panel-label">阈值</span>
            <input v-model.number="findThreshold" type="number" class="ap-input" min="0" max="1" step="0.01" style="width:70px" />
          </div>
          <div class="panel-row">
            <span class="panel-label">结果</span>
            <span class="hex-text">{{ findResult || '—' }}</span>
          </div>
          <div class="panel-row">
            <el-button size="small" type="primary" :disabled="codeStore.isExecuting" :loading="codeStore.isExecuting" @click="executeFind">🔍 执行</el-button>
          </div>
        </div>

        <!-- 调整大小面板 -->
        <div v-if="resizeMode" class="action-panel" @wheel.stop @dblclick.stop>
          <div class="panel-title">📐 调整大小</div>
          <div class="panel-info">原图 {{ imageNaturalSize.width }} × {{ imageNaturalSize.height }}</div>
          <div class="crop-params-row">
            <label>W <input :value="resizeW" type="number" class="ap-input" min="1" max="8192" @input="e => { const el = e.target as HTMLInputElement; resizeW = Number(el.value); updateResizeRatio('w') }" /></label>
            <label>H <input :value="resizeH" type="number" class="ap-input" min="1" max="8192" @input="e => { const el = e.target as HTMLInputElement; resizeH = Number(el.value); updateResizeRatio('h') }" /></label>
            <label class="ratio-label"><input type="checkbox" v-model="keepRatio" /> 比例</label>
          </div>
          <div class="panel-row">
            <span class="panel-label">插值</span>
            <select v-model="interpolation" class="ap-select"><option v-for="opt in INTERPOLATION_OPTIONS" :key="opt.value" :value="opt.value">{{ opt.label }} ({{ opt.value }})</option></select>
          </div>
          <div class="panel-row">
            <input v-model="resizeFileName" class="ap-input file-input" @keydown.enter="executeResize" />
            <el-button size="small" type="primary" :disabled="cvLoading || isResizing" :loading="isResizing" @click="executeResize">{{ cvLoading ? '加载中...' : '📐 执行' }}</el-button>
          </div>
        </div>
      </template>
      <div v-else class="viewer-empty"><el-empty description="点击左侧缩略图查看大图" :image-size="80" /></div>
    </div>
  </div>
</template>

<style scoped>
.image-panel { display: flex; height: 100%; overflow: hidden; }
.tool-bar { width: 72px; flex-shrink: 0; display: flex; flex-direction: column; align-items: center; padding: 16px 8px; border-right: 1px solid var(--color-border); background-color: var(--color-bg-secondary); }
.tool-label { font-size: 11px; color: var(--color-text-secondary); margin-top: 4px; }
.tool-label.disabled { color: var(--color-text-placeholder); }
.tool-label.active { color: var(--color-primary); font-weight: 600; }
.tool-divider { margin: 8px 0; }

.image-list { width: 240px; flex-shrink: 0; display: flex; flex-direction: column; border-right: 1px solid var(--color-border); overflow: hidden; }
.image-scroll { flex: 1; overflow-y: auto; }
.list-empty { flex: 1; display: flex; align-items: center; justify-content: center; }
.empty-text { font-size: 13px; color: var(--color-text-placeholder); }
.list-footer { padding: 8px; border-top: 1px solid var(--color-border); text-align: center; }

.image-viewer { flex: 1; display: flex; align-items: center; justify-content: center; background-color: #1a1a2e; overflow: hidden; position: relative; user-select: none; }
.viewer-image { max-width: 100%; max-height: 100%; object-fit: contain; transform-origin: center center; user-select: none; -webkit-user-drag: none; }
.viewer-empty { display: flex; align-items: center; justify-content: center; }
.image-viewer.is-dragging { cursor: grabbing; }

.viewer-toolbar { position: absolute; top: 8px; left: 8px; z-index: 10; display: flex; align-items: center; gap: 8px; background: rgba(0, 0, 0, 0.5); border-radius: 4px; padding: 2px 8px; }
.viewer-toolbar :deep(.el-checkbox__label) { color: #fff; font-size: 12px; }
.viewer-toolbar :deep(.el-checkbox__inner) { border-color: rgba(255, 255, 255, 0.6); }
.zoom-badge { color: #fff; font-size: 11px; font-family: var(--editor-font-family, monospace); background: rgba(255, 255, 255, 0.15); padding: 0 6px; border-radius: 3px; line-height: 18px; }
.mode-badge { color: #409eff; font-size: 11px; background: rgba(64, 158, 255, 0.2); padding: 0 6px; border-radius: 3px; line-height: 18px; font-weight: 600; }

.crop-overlay { position: absolute; pointer-events: none; z-index: 15; border: 2px dashed #409eff; background: rgba(64, 158, 255, 0.1); }

.action-panel { position: absolute; bottom: 8px; right: 8px; z-index: 30; background: rgba(30, 30, 50, 0.92); border: 1px solid rgba(255, 255, 255, 0.15); border-radius: 6px; padding: 10px 12px; display: flex; flex-direction: column; gap: 6px; min-width: 260px; }
.panel-title { font-size: 12px; font-weight: 600; color: #fff; margin-bottom: 2px; }
.panel-info { font-size: 11px; color: #888; font-family: var(--editor-font-family, monospace); }
.panel-row { display: flex; align-items: center; gap: 6px; }
.panel-label { font-size: 11px; color: #aaa; white-space: nowrap; }
.crop-params-row { display: flex; gap: 6px; align-items: center; }
.crop-params-row label { display: flex; align-items: center; gap: 2px; font-size: 11px; color: #aaa; font-family: var(--editor-font-family, monospace); }
.ratio-label { display: flex; align-items: center; gap: 2px; font-size: 11px; color: #ccc !important; cursor: pointer; white-space: nowrap; }
.ratio-label input[type="checkbox"] { accent-color: #409eff; }

.ap-input { width: 52px; background: rgba(255, 255, 255, 0.1); border: 1px solid rgba(255, 255, 255, 0.2); border-radius: 3px; color: #fff; font-size: 11px; font-family: var(--editor-font-family, monospace); padding: 2px 4px; outline: none; text-align: center; }
.ap-input:focus { border-color: #409eff; }
.ap-select { background: rgba(255, 255, 255, 0.1); border: 1px solid rgba(255, 255, 255, 0.2); border-radius: 3px; color: #fff; font-size: 11px; font-family: var(--editor-font-family, monospace); padding: 2px 4px; outline: none; flex: 1; }
.ap-select option { background: #2a2a4a; color: #fff; }
.file-input { flex: 1; width: auto; text-align: left; }
.color-swatch { display: inline-block; width: 18px; height: 18px; border-radius: 3px; border: 1px solid rgba(255,255,255,0.3); flex-shrink: 0; }
.hex-text { font-size: 10px; font-family: var(--editor-font-family,monospace); color: #ddd; }

.magnifier-lens { position: absolute; border-radius: 2px; border: 3px solid #fff; box-shadow: 0 0 12px rgba(0, 0, 0, 0.5), inset 0 0 8px rgba(0, 0, 0, 0.1); pointer-events: none; background-repeat: no-repeat; z-index: 20; }
.pixel-grid { position: absolute; inset: 0; pointer-events: none; border-radius: inherit; --grid-size: 10px; background-image: repeating-linear-gradient(to bottom,transparent,transparent calc(var(--grid-size) - 1px),rgba(128,128,128,0.45) calc(var(--grid-size) - 1px),rgba(128,128,128,0.45) var(--grid-size)),repeating-linear-gradient(to right,transparent,transparent calc(var(--grid-size) - 1px),rgba(128,128,128,0.45) calc(var(--grid-size) - 1px),rgba(128,128,128,0.45) var(--grid-size)); }
.magnifier-crosshair { position: absolute; top: 50%; left: 50%; transform: translate(-50%,-50%); pointer-events: none; z-index: 21; width: 14px; height: 14px; }
.magnifier-crosshair::before, .magnifier-crosshair::after { content: ''; position: absolute; background: rgba(255,60,60,0.85); }
.magnifier-crosshair::before { width: 100%; height: 1px; top: 50%; left: 0; transform: translateY(-50%); }
.magnifier-crosshair::after { width: 1px; height: 100%; top: 0; left: 50%; transform: translateX(-50%); }
.magnifier-info { position: absolute; bottom: 0; left: 0; right: 0; height: 22px; background: rgba(0,0,0,0.6); display: flex; align-items: center; justify-content: space-between; padding: 0 6px; font-size: 10px; font-family: var(--editor-font-family,monospace); color: #eee; border-bottom-left-radius: 2px; border-bottom-right-radius: 2px; gap: 4px; }
.mi-swatch { display: inline-block; width: 12px; height: 12px; border: 1px solid rgba(255,255,255,0.3); border-radius: 2px; flex-shrink: 0; }
.mi-coords, .mi-hex { white-space: nowrap; }
</style>
