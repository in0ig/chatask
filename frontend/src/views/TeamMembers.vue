<script setup lang="ts">
import { ref } from 'vue';

// 组件逻辑
const message = ref('此功能正在开发中...');
</script>

<template>
  <div class="placeholder-page">
    <h1>项目成员管理</h1>
    <p>{{ message }}</p>
  </div>
</template>

<style scoped>
.placeholder-page {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100vh;
  text-align: center;
  padding: 2rem;
}

.placeholder-page h1 {
  margin-bottom: 1rem;
  color: #333;
  font-size: 1.8rem;
}

.placeholder-page p {
  color: #666;
  font-size: 1.1rem;
}
</style>