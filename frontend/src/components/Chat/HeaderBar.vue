<template>
  <div class="header-bar">
    <!-- 左侧: Logo -->
    <div class="left-section">
      <div class="logo">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
          <path d="M12 2L2 7L12 12L22 7L12 2Z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
          <path d="M2 17L12 22L22 17" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
          <path d="M2 12L12 17L22 12" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
      </div>
    </div>
    
    <!-- 右侧: 语言切换按钮 + 配置按钮 -->
    <div class="right-section">
      <!-- 语言切换按钮 -->
      <el-button
        text
        class="lang-button"
        :title="$t('header.language')"
        @click="localeStore.toggleLocale()"
      >
        <span class="lang-icon">🌐</span>
        <span class="lang-label">{{ localeStore.localeLabel }}</span>
      </el-button>

      <el-button 
        text
        class="config-button" 
        @click="toggleConfigDrawer"
      >
        <el-icon><Setting /></el-icon>
      </el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useUIStore } from '@/store/modules/ui'
import { useLocaleStore } from '@/store/modules/locale'
import { Setting } from '@element-plus/icons-vue'
import { useI18n } from 'vue-i18n'

const uiStore = useUIStore()
const localeStore = useLocaleStore()
const { t: $t } = useI18n()

const toggleConfigDrawer = () => {
  uiStore.toggleConfigDrawer()
}
</script>

<style scoped>
.header-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 24px;
  height: 60px;
  background-color: #ffffff;
  border-bottom: 1px solid #ebeef5;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.left-section {
  display: flex;
  align-items: center;
  gap: 12px;
}

.logo svg {
  color: #409eff;
}

.right-section {
  display: flex;
  align-items: center;
  gap: 20px;
}



.lang-button {
  padding: 0 8px;
  height: 36px;
  border-radius: 18px;
  display: flex;
  align-items: center;
  gap: 4px;
  transition: background-color 0.3s ease;
}

.lang-button:hover {
  background-color: #f5f7fa;
}

.lang-icon {
  font-size: 16px;
  line-height: 1;
}

.lang-label {
  font-size: 13px;
  font-weight: 500;
  color: #666;
  min-width: 18px;
}

.config-button {
  padding: 0;
  width: 36px;
  height: 36px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background-color 0.3s ease;
}

.config-button:hover {
  background-color: #f5f7fa;
}

.config-button .el-icon {
  color: #666;
  font-size: 18px;
}
</style>