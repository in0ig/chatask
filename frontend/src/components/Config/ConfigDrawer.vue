<template>
  <el-drawer
    v-model="isConfigDrawerOpen"
    :title="$t('settings.configDrawer.title')"
    :direction="'rtl'"
    :size="'900px'"
    :with-header="true"
    :show-close="true"
    :close-on-click-modal="false"
    :close-on-press-escape="true"
    class="config-drawer"
    @close="handleDrawerClose"
  >
    <div class="config-content">
      <template v-if="!activeComponent">
        <!-- 配置组分类 -->
        <div class="config-groups">
          <!-- 核心配置组 -->
          <div class="config-group">
            <h3 class="group-title">{{ $t('settings.configDrawer.coreConfig') }}</h3>
            <el-menu
              :default-active="activeIndex"
              class="el-menu-vertical-demo"
              background-color="#f5f7fa"
              text-color="#303133"
              active-text-color="#409EFF"
              mode="vertical"
            >
              <el-menu-item index="2" @click="handleKnowledgeBaseClick">
                <span>{{ $t('settings.configDrawer.knowledgeBase') }}</span>
              </el-menu-item>
              <el-menu-item index="3" @click="handleReportTemplateClick">
                <span>{{ $t('settings.configDrawer.reportTemplate') }}</span>
              </el-menu-item>
              <el-menu-item index="4" @click="handleEmbedManagementClick">
                <span>{{ $t('settings.configDrawer.embedManagement') }}</span>
              </el-menu-item>
            </el-menu>
          </div>
          
          <!-- 权限管理组 -->
          <div class="config-group">
            <h3 class="group-title">{{ $t('settings.configDrawer.permissionManagement') }}</h3>
            <el-menu
              :default-active="activeIndex"
              class="el-menu-vertical-demo"
              background-color="#f5f7fa"
              text-color="#303133"
              active-text-color="#409EFF"
              mode="vertical"
            >
              <el-menu-item index="5" @click="handleFunctionPermissionsClick">
                <span>{{ $t('settings.configDrawer.functionPermissions') }}</span>
              </el-menu-item>
              <el-menu-item index="6" @click="handleTablePermissionsClick">
                <span>{{ $t('settings.configDrawer.tablePermissions') }}</span>
              </el-menu-item>
            </el-menu>
          </div>
          
          <!-- 智能工具组 -->
          <div class="config-group">
            <h3 class="group-title">{{ $t('settings.configDrawer.smartTools') }}</h3>
            <el-menu
              :default-active="activeIndex"
              class="el-menu-vertical-demo"
              background-color="#f5f7fa"
              text-color="#303133"
              active-text-color="#409EFF"
              mode="vertical"
            >
              <el-menu-item index="7" @click="handleDataInterpretationClick">
                <span>{{ $t('settings.configDrawer.dataInterpretation') }}</span>
              </el-menu-item>
              <el-menu-item index="8" @click="handleFluctuationAnalysisClick">
                <span>{{ $t('settings.configDrawer.fluctuationAnalysis') }}</span>
              </el-menu-item>
              <el-menu-item index="9" @click="handleSmartTableSelectionClick">
                <span>{{ $t('settings.configDrawer.smartTableSelection') }}</span>
              </el-menu-item>
            </el-menu>
          </div>
          
          <!-- 高级设置组 -->
          <div class="config-group">
            <h3 class="group-title">{{ $t('settings.configDrawer.advancedSettings') }}</h3>
            <el-menu
              :default-active="activeIndex"
              class="el-menu-vertical-demo"
              background-color="#f5f7fa"
              text-color="#303133"
              active-text-color="#409EFF"
              mode="vertical"
            >
              <el-menu-item index="10" @click="handleConversationSettingsClick">
                <span>{{ $t('settings.configDrawer.conversationSettings') }}</span>
              </el-menu-item>
              <el-menu-item index="11" @click="handleConversationIdSettingsClick">
                <span>{{ $t('settings.configDrawer.conversationIdSettings') }}</span>
              </el-menu-item>
              <el-menu-item index="12" @click="handleFormatManagementClick">
                <span>{{ $t('settings.configDrawer.formatManagement') }}</span>
              </el-menu-item>
            </el-menu>
          </div>
        </div>
      </template>
      
      <!-- 动态渲染选中的组件 -->
      <component 
        :is="activeComponent" 
        v-if="activeComponent"
        @back="activeComponent = null"
      />
    </div>
  </el-drawer>
</template>

<script setup lang="ts">
import { computed, ref, shallowRef } from 'vue'
import { useUIStore } from '@/store/modules/ui'
import ConversationHistoryUI from './ConversationHistoryUI.vue'
import KnowledgeBaseManager from '@/components/KnowledgeBase/KnowledgeBaseManager.vue'

const uiStore = useUIStore()

const activeIndex = ref('')
const activeComponent = shallowRef(null)

const isConfigDrawerOpen = computed({
  get: () => uiStore.isConfigDrawerOpen,
  set: (value) => {
    if (value) {
      uiStore.openConfigDrawer()
    } else {
      uiStore.closeConfigDrawer()
    }
  }
})

// 处理抽屉关闭事件 - 重置状态
const handleDrawerClose = () => {
  activeComponent.value = null
  activeIndex.value = ''
}

// 点击事件处理器
const handleKnowledgeBaseClick = () => {
  // 设置为显示知识库管理组件
  activeComponent.value = KnowledgeBaseManager
  activeIndex.value = '2'
}

const handleReportTemplateClick = () => {
  uiStore.openReportTemplateModal()
}

const handleEmbedManagementClick = () => {
  uiStore.openEmbedManagementModal()
}

const handleFunctionPermissionsClick = () => {
  uiStore.openFunctionPermissionsModal()
}

const handleTablePermissionsClick = () => {
  uiStore.openTablePermissionsModal()
}

const handleDataInterpretationClick = () => {
  uiStore.openDataInterpretationModal()
}

const handleFluctuationAnalysisClick = () => {
  uiStore.openFluctuationAnalysisModal()
}

const handleSmartTableSelectionClick = () => {
  uiStore.openSmartTableSelectionModal()
}

const handleConversationSettingsClick = () => {
  uiStore.openConversationSettingsModal()
}

const handleConversationIdSettingsClick = () => {
  uiStore.openConversationIdSettingsModal()
}

const handleFormatManagementClick = () => {
  uiStore.openFormatManagementModal()
}
</script>
<style scoped>
.config-drawer {
  --el-drawer-size: 600px;
}

.config-content {
  padding: 16px;
  height: 100%;
}

.config-groups {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.config-group {
  border: none;
  border-radius: 8px;
  padding: 16px;
  background-color: #f5f7fa;
}

.group-title {
  font-size: 16px;
  font-weight: 600;
  color: #333;
  margin-bottom: 12px;
  padding-bottom: 6px;
  border-bottom: 1px solid #e0e0e0;
}

.el-menu-vertical-demo {
  border-right: none;
  width: 100%;
}

.el-menu-item {
  display: flex;
  align-items: center;
  padding: 10px 16px;
  margin: 0;
  border-radius: 4px;
}

.el-menu-item:hover {
  background-color: #e8f4ff;
}

.el-menu-item.is-active {
  background-color: #e8f4ff;
  border-left: 3px solid #409EFF;
}
</style>