import { describe, it, expect, beforeEach } from 'vitest'
import { useUIStore } from '@/store/modules/ui'
import { setActivePinia, createPinia } from 'pinia'

// 创建一个独立的 Pinia 实例用于测试，避免状态污染
const pinia = createPinia()

beforeEach(() => {
  setActivePinia(pinia)
})

describe('UI Store', () => {
  it('should have correct initial state', () => {
    const store = useUIStore()
    
    expect(store.isConfigDrawerOpen).toBe(false)
    expect(store.isReportTemplateModalOpen).toBe(false)
    expect(store.isKnowledgeBaseModalOpen).toBe(false)
    expect(store.isLoading).toBe(false)
    expect(store.loadingMessage).toBe('')
    expect(store.toastMessage).toBe('')
    expect(store.toastType).toBeNull()
    expect(store.isSidebarCollapsed).toBe(false)
  })

  it('should toggle config drawer correctly', () => {
    const store = useUIStore()
    
    // 初始状态为 false
    expect(store.isConfigDrawerOpen).toBe(false)
    
    // 调用 toggleConfigDrawer
    store.toggleConfigDrawer()
    expect(store.isConfigDrawerOpen).toBe(true)
    
    // 再次调用 toggleConfigDrawer
    store.toggleConfigDrawer()
    expect(store.isConfigDrawerOpen).toBe(false)
  })

  it('should open and close config drawer correctly', () => {
    const store = useUIStore()
    
    // 测试 openConfigDrawer
    store.openConfigDrawer()
    expect(store.isConfigDrawerOpen).toBe(true)
    
    // 测试 closeConfigDrawer
    store.closeConfigDrawer()
    expect(store.isConfigDrawerOpen).toBe(false)
  })

  it('should open and close report template modal correctly', () => {
    const store = useUIStore()
    
    // 测试 openReportTemplateModal
    store.openReportTemplateModal()
    expect(store.isReportTemplateModalOpen).toBe(true)
    
    // 测试 closeReportTemplateModal
    store.closeReportTemplateModal()
    expect(store.isReportTemplateModalOpen).toBe(false)
  })

  it('should open and close knowledge base modal correctly', () => {
    const store = useUIStore()
    
    // 测试 openKnowledgeBaseModal
    store.openKnowledgeBaseModal()
    expect(store.isKnowledgeBaseModalOpen).toBe(true)
    
    // 测试 closeKnowledgeBaseModal
    store.closeKnowledgeBaseModal()
    expect(store.isKnowledgeBaseModalOpen).toBe(false)
  })

  it('should set loading state correctly', () => {
    const store = useUIStore()
    
    // 测试设置加载状态
    store.setLoading(true, 'Loading data...')
    expect(store.isLoading).toBe(true)
    expect(store.loadingMessage).toBe('Loading data...')
    
    // 测试关闭加载状态
    store.setLoading(false)
    expect(store.isLoading).toBe(false)
    expect(store.loadingMessage).toBe('')
  })

  it('should show and clear toast correctly', () => {
    const store = useUIStore()
    
    // 测试显示成功提示
    store.showToast('Operation successful', 'success')
    expect(store.toastMessage).toBe('Operation successful')
    expect(store.toastType).toBe('success')
    
    // 测试显示错误提示
    store.showToast('Error occurred', 'error')
    expect(store.toastMessage).toBe('Error occurred')
    expect(store.toastType).toBe('error')
    
    // 测试清除 toast
    store.clearToast()
    expect(store.toastMessage).toBe('')
    expect(store.toastType).toBeNull()
  })

  it('should toggle sidebar correctly', () => {
    const store = useUIStore()
    
    // 初始状态为 false
    expect(store.isSidebarCollapsed).toBe(false)
    
    // 调用 toggleSidebar
    store.toggleSidebar()
    expect(store.isSidebarCollapsed).toBe(true)
    
    // 再次调用 toggleSidebar
    store.toggleSidebar()
    expect(store.isSidebarCollapsed).toBe(false)
  })

  it('should have correct hasActiveModal getter', () => {
    const store = useUIStore()
    
    // 初始状态：两个模态框都关闭
    expect(store.hasActiveModal).toBe(false)
    
    // 打开报告模板模态框
    store.openReportTemplateModal()
    expect(store.hasActiveModal).toBe(true)
    
    // 关闭报告模板模态框，打开知识库模态框
    store.closeReportTemplateModal()
    store.openKnowledgeBaseModal()
    expect(store.hasActiveModal).toBe(true)
    
    // 两个模态框都关闭
    store.closeKnowledgeBaseModal()
    expect(store.hasActiveModal).toBe(false)
  })
})
