/**
 * UI Store - 管理界面状态
 * 对应 PRD 模块 2.1 和模块 3
 */
import { defineStore } from 'pinia'

export interface UIState {
  // 右侧配置抽屉
  isConfigDrawerOpen: boolean
  
  // 模态框状态
  isReportTemplateModalOpen: boolean
  isKnowledgeBaseModalOpen: boolean
  isPromptManagementModalOpen: boolean
  isDataSourceModalOpen: boolean
  isSmartTableSelectionModalOpen: boolean
  
  // 配置抽屉新增模态框状态
  isEmbedManagementModalOpen: boolean
  isFunctionPermissionsModalOpen: boolean
  isTablePermissionsModalOpen: boolean
  isDataInterpretationModalOpen: boolean
  isFluctuationAnalysisModalOpen: boolean
  isConversationSettingsModalOpen: boolean
  isConversationIdSettingsModalOpen: boolean
  isFormatManagementModalOpen: boolean
  
  // 加载状态
  isLoading: boolean
  loadingMessage: string
  
  // Toast 通知
  toastMessage: string
  toastType: 'success' | 'error' | 'warning' | 'info' | null
  
  // 侧边栏折叠状态
  isSidebarCollapsed: boolean
}

export const useUIStore = defineStore('ui', {
  state: (): UIState => ({
    isConfigDrawerOpen: false,
    isReportTemplateModalOpen: false,
    isKnowledgeBaseModalOpen: false,
    isPromptManagementModalOpen: false,
    isDataSourceModalOpen: false,
    isSmartTableSelectionModalOpen: false,
    isEmbedManagementModalOpen: false,
    isFunctionPermissionsModalOpen: false,
    isTablePermissionsModalOpen: false,
    isDataInterpretationModalOpen: false,
    isFluctuationAnalysisModalOpen: false,
    isConversationSettingsModalOpen: false,
    isConversationIdSettingsModalOpen: false,
    isFormatManagementModalOpen: false,
    isLoading: false,
    loadingMessage: '',
    toastMessage: '',
    toastType: null,
    isSidebarCollapsed: false
  }),
  
  getters: {
    hasActiveModal: (state) => {
      return state.isReportTemplateModalOpen || state.isKnowledgeBaseModalOpen || state.isPromptManagementModalOpen
    }
  },
  
  actions: {
    // 配置抽屉控制
    toggleConfigDrawer() {
      this.isConfigDrawerOpen = !this.isConfigDrawerOpen
    },
    
    openConfigDrawer() {
      this.isConfigDrawerOpen = true
    },
    
    closeConfigDrawer() {
      this.isConfigDrawerOpen = false
    },
    
    // 模态框控制
    openReportTemplateModal() {
      this.isReportTemplateModalOpen = true
    },
    
    closeReportTemplateModal() {
      this.isReportTemplateModalOpen = false
    },
    
    openKnowledgeBaseModal() {
      this.isKnowledgeBaseModalOpen = true
    },
    
    closeKnowledgeBaseModal() {
      this.isKnowledgeBaseModalOpen = false
    },
    
    openPromptManagementModal() {
      this.isPromptManagementModalOpen = true
    },
    
    closePromptManagementModal() {
      this.isPromptManagementModalOpen = false
    },
    
    // 数据表选择模态框控制
    openDataSourceModal() {
      this.isDataSourceModalOpen = true
    },
    
    closeDataSourceModal() {
      this.isDataSourceModalOpen = false
    },
    
    // 智能选表模态框控制
    openSmartTableSelectionModal() {
      this.isSmartTableSelectionModalOpen = true
    },
    
    closeSmartTableSelectionModal() {
      this.isSmartTableSelectionModalOpen = false
    },
    
    // 配置抽屉新增模态框控制
    openEmbedManagementModal() {
      this.isEmbedManagementModalOpen = true
    },
    
    closeEmbedManagementModal() {
      this.isEmbedManagementModalOpen = false
    },
    
    openFunctionPermissionsModal() {
      this.isFunctionPermissionsModalOpen = true
    },
    
    closeFunctionPermissionsModal() {
      this.isFunctionPermissionsModalOpen = false
    },
    
    openTablePermissionsModal() {
      this.isTablePermissionsModalOpen = true
    },
    
    closeTablePermissionsModal() {
      this.isTablePermissionsModalOpen = false
    },
    
    openDataInterpretationModal() {
      this.isDataInterpretationModalOpen = true
    },
    
    closeDataInterpretationModal() {
      this.isDataInterpretationModalOpen = false
    },
    
    openFluctuationAnalysisModal() {
      this.isFluctuationAnalysisModalOpen = true
    },
    
    closeFluctuationAnalysisModal() {
      this.isFluctuationAnalysisModalOpen = false
    },
    
    openConversationSettingsModal() {
      this.isConversationSettingsModalOpen = true
    },
    
    closeConversationSettingsModal() {
      this.isConversationSettingsModalOpen = false
    },
    
    openConversationIdSettingsModal() {
      this.isConversationIdSettingsModalOpen = true
    },
    
    closeConversationIdSettingsModal() {
      this.isConversationIdSettingsModalOpen = false
    },
    
    openFormatManagementModal() {
      this.isFormatManagementModalOpen = true
    },
    
    closeFormatManagementModal() {
      this.isFormatManagementModalOpen = false
    },
    
    // 加载状态
    setLoading(loading: boolean, message = '') {
      this.isLoading = loading
      this.loadingMessage = message
    },
    
    // Toast 通知
    showToast(message: string, type: 'success' | 'error' | 'warning' | 'info' = 'info') {
      this.toastMessage = message
      this.toastType = type
      
      // 3秒后自动关闭
      setTimeout(() => {
        this.clearToast()
      }, 3000)
    },
    
    clearToast() {
      this.toastMessage = ''
      this.toastType = null
    },
    
    // 侧边栏控制
    toggleSidebar() {
      this.isSidebarCollapsed = !this.isSidebarCollapsed
    }
  }
})
