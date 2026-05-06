<template>
  <!-- 动态注入 Element Plus 语言包，随 locale store 切换 -->
  <el-config-provider :locale="elLocale">
    <div id="app" class="chatbi-app">
      <!-- 左侧导航栏 -->
      <NavigationSidebar />
      
      <!-- 主内容区域 -->
      <div class="main-content">
        <router-view />
      </div>
      
      <!-- 配置抽屉 -->
      <ConfigDrawer />
    </div>
  </el-config-provider>
</template>

<script setup>
import { computed } from 'vue'
import { RouterView } from 'vue-router'
import { useUIStore } from '@/store/modules/ui'
import { useLocaleStore } from '@/store/modules/locale'
import NavigationSidebar from '@/components/Navigation/NavigationSidebar.vue'
import ConfigDrawer from '@/components/Config/ConfigDrawer.vue'
// Element Plus 语言包
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import en from 'element-plus/es/locale/lang/en'

const uiStore = useUIStore()
const localeStore = useLocaleStore()

// 根据 locale store 动态选择 Element Plus 语言包
const elLocale = computed(() => localeStore.locale === 'en-US' ? en : zhCn)
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: 'PingFang SC', 'Microsoft YaHei', sans-serif;
  background-color: #f5f7fa;
  color: #333;
  height: 100vh;
  overflow: hidden;
}

.chatbi-app {
  display: flex;
  height: 100vh;
}

.main-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  margin-left: 260px; /* 左侧导航栏宽度 */
  overflow: hidden;
}

.top-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 15px 30px;
  background-color: #fff;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  z-index: 100;
  min-height: 56px;
}

.logo-container {
  display: flex;
  align-items: center;
  gap: 12px;
}

.logo-circle {
  width: 24px;
  height: 24px;
  background-color: #1890ff;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.logo-text {
  font-size: 20px;
  font-weight: 700;
  color: #1890ff;
}

.settings-btn {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background-color: transparent;
  border: none;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background-color 0.3s;
}

.settings-btn:hover {
  background-color: #f5f7fa;
}

/* Router View 样式 */
:deep(> div) {
  flex: 1;
  overflow: auto;
}

/* 全局加载遮罩样式 */
.global-loading-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.7);
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  z-index: 9999;
  color: white;
}

.loading-spinner {
  width: 40px;
  height: 40px;
  border: 3px solid #f3f3f3;
  border-top: 3px solid #1890ff;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-bottom: 15px;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

/* 响应式设计 */
@media (max-width: 1024px) {
  .top-bar {
    padding: 12px 20px;
  }
  
  .logo-text {
    font-size: 18px;
  }
  
  .settings-btn {
    padding: 5px 10px;
    font-size: 14px;
  }
}

@media (max-width: 768px) {
  .top-bar {
    padding: 10px 15px;
  }
  
  .logo-text {
    font-size: 16px;
  }
  
  .settings-btn {
    padding: 4px 8px;
    font-size: 12px;
  }
}

/* Element Plus 组件全局样式覆盖 */
.el-button {
  border-radius: 4px;
  font-weight: 500;
}

.el-button--primary {
  background-color: #1890ff;
  border-color: #1890ff;
}

.el-button--primary:hover {
  background-color: #096dd9;
  border-color: #096dd9;
}

.el-switch {
  --el-switch-on-color: #1890ff;
  --el-switch-off-color: #e0e0e0;
}

.el-select {
  border-radius: 20px;
}

.el-select .el-input {
  border-radius: 20px;
}

.el-input {
  border-radius: 20px;
}

.el-input__inner {
  border-radius: 20px;
}

.el-card {
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

.el-drawer {
  border-radius: 8px;
}

.el-drawer__header {
  border-bottom: 1px solid #e0e0e0;
}

.el-drawer__body {
  padding: 16px;
}
</style>
