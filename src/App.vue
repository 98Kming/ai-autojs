<script setup lang="ts">
import AppHeader from '@/components/layout/AppHeader.vue'
</script>

<template>
  <el-container class="app-container">
    <el-header height="56px" class="app-header">
      <AppHeader />
    </el-header>
    <el-main class="app-main">
      <router-view />
    </el-main>
  </el-container>
</template>

<style scoped>
.app-container {
  height: 100vh;
  display: flex;
  flex-direction: column;
}

.app-header {
  background-color: var(--color-bg-secondary);
  border-bottom: 1px solid var(--color-border);
  padding: 0 16px;
  display: flex;
  align-items: center;
  flex-shrink: 0;
}

.app-main {
  flex: 1;
  overflow: hidden;
  padding: 0;
}
</style>
