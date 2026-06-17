<script setup lang="ts">
import { ref, watch, onMounted, nextTick } from 'vue'
import { useCodeStore } from '@/stores/useCodeStore'

const codeStore = useCodeStore()
const textareaRef = ref<HTMLTextAreaElement | null>(null)
const lineNumbersRef = ref<HTMLDivElement | null>(null)
const lineCount = ref(1)
const cursorLine = ref(1)

// 同步行数
function updateLineCount() {
  const lines = codeStore.content.split('\n').length
  lineCount.value = lines
}

watch(() => codeStore.content, updateLineCount, { immediate: true })

// 同步滚动
function syncScroll() {
  if (textareaRef.value && lineNumbersRef.value) {
    lineNumbersRef.value.scrollTop = textareaRef.value.scrollTop
  }
}

// 快捷键处理
function onKeydown(e: KeyboardEvent) {
  if (e.ctrlKey && e.key === 'Enter') {
    e.preventDefault()
    // Run 事件由父组件处理
  }
}

onMounted(() => {
  updateLineCount()
})
</script>

<template>
  <div class="code-editor-wrapper">
    <div ref="lineNumbersRef" class="line-numbers" aria-hidden="true">
      <span
        v-for="n in lineCount"
        :key="n"
        class="line-number"
        :class="{ active: n === cursorLine }"
      >{{ n }}</span>
    </div>
    <textarea
      ref="textareaRef"
      v-model="codeStore.content"
      class="code-textarea"
      placeholder="在此编写 Autojs 代码..."
      spellcheck="false"
      @scroll="syncScroll"
      @keydown="onKeydown"
    />
  </div>
</template>

<style scoped>
.code-editor-wrapper {
  position: relative;
  display: flex;
  height: 100%;
  min-height: 200px;
  overflow: hidden;
}

.line-numbers {
  flex-shrink: 0;
  width: 48px;
  padding: 12px 0;
  overflow: hidden;
  text-align: right;
  background-color: var(--color-bg-secondary);
  border-right: 1px solid var(--color-border);
  user-select: none;
}

.line-number {
  display: block;
  padding: 0 10px 0 4px;
  font-family: var(--editor-font-family);
  font-size: var(--editor-font-size);
  line-height: var(--editor-line-height);
  color: var(--color-text-placeholder);
  tab-size: var(--editor-tab-size);
}

.line-number.active {
  color: var(--color-text-secondary);
  background-color: var(--color-bg-tertiary);
}

.code-textarea {
  flex: 1;
  padding: 12px 16px;
  border: none;
  outline: none;
  resize: none;
  font-family: var(--editor-font-family);
  font-size: var(--editor-font-size);
  line-height: var(--editor-line-height);
  color: var(--color-text-primary);
  background-color: var(--color-bg-primary);
  tab-size: var(--editor-tab-size);
  white-space: pre;
  overflow-wrap: normal;
  overflow-x: auto;
  overflow-y: auto;
}

.code-textarea::placeholder {
  color: var(--color-text-placeholder);
}

.code-textarea:focus {
  background-color: #fafbfc;
}
</style>
