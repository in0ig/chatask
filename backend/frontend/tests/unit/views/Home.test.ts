import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import Home from '@/views/Home.vue'
import { createPinia, setActivePinia } from 'pinia'
import { useChatStore } from '@/store/modules/chat'
import { useUiStore } from '@/store/modules/ui'
import { useDataPrepStore } from '@/store/modules/dataPrep'
import { createRouter, createWebHistory } from 'vue-router'

// Mock components
const MockDataSourceSelector = {
  template: '<div class="mock-data-source-selector"><slot></slot></div>',
  props: ['selectedSource', 'loading', 'error'],
  emits: ['update:selectedSource', 'retry']
}

const MockDataPreviewModal = {
  template: '<div class="mock-data-preview-modal"><slot></slot></div>',
  props: ['visible', 'source', 'loading'],
  emits: ['update:visible', 'close']
}

const MockChartRenderer = {
  template: '<div class="mock-chart-renderer"><slot></slot></div>',
  props: ['chartType', 'data', 'loading']
}

const MockDataTable = {
  template: '<div class="mock-data-table"><slot></slot></div>',
  props: ['data', 'columns', 'loading']
}

// Mock Vue Router
const mockUseRoute = vi.fn()

// Mock Pinia stores
const mockChatStore = {
  messages: [],
  userInput: '',
  isSending: false,
  addMessage: vi.fn(),
  clearMessages: vi.fn(),
  sendQuery: vi.fn(),
  reset: vi.fn()
}

const mockUiStore = {
  mode: 'query', // 'query' or 'report'
  setMode: vi.fn(),
  isMobile: false,
  toggleMobile: vi.fn()
}

const mockDataPrepStore = {
  dataSources: [],
  loading: false,
  error: null,
  loadDataSources: vi.fn(),
  uploadFile: vi.fn(),
  selectedSource: null,
  setSelectedSource: vi.fn(),
  previewData: vi.fn(),
  clearPreview: vi.fn()
}

describe('Home.vue', () => {
  let wrapper
  let pinia
  let router

  beforeEach(() => {
    // Reset mocks
    vi.clearAllMocks()
    
    // Create Pinia instance
    pinia = createPinia()
    setActivePinia(pinia)
    
    // Mock Vue Router
    vi.mock('vue-router', () => ({
      useRoute: () => mockUseRoute()
    }))
    
    // Mock stores
    vi.mock('@/store/modules/chat', () => ({
      useChatStore: () => mockChatStore
    }))
    
    vi.mock('@/store/modules/ui', () => ({
      useUiStore: () => mockUiStore
    }))
    
    vi.mock('@/store/modules/dataPrep', () => ({
      useDataPrepStore: () => mockDataPrepStore
    }))
    
    // Mock components
    vi.mock('@/components/DataSource/DataSourceSelector.vue', () => ({
      default: MockDataSourceSelector
    }))
    
    vi.mock('@/components/DataSource/DataPreviewModal.vue', () => ({
      default: MockDataPreviewModal
    }))
    
    vi.mock('@/components/ChartRenderer.vue', () => ({
      default: MockChartRenderer
    }))
    
    vi.mock('@/components/DataTable.vue', () => ({
      default: MockDataTable
    }))
    
    // Create router
    router = createRouter({
      history: createWebHistory(),
      routes: [
        { path: '/', component: Home }
      ]
    })
    
    // Mount component
    wrapper = mount(Home, {
      global: {
        plugins: [pinia, router],
        stubs: {
          // Use mocks instead of stubs for better testing
          DataSourceSelector: MockDataSourceSelector,
          DataPreviewModal: MockDataPreviewModal,
          ChartRenderer: MockChartRenderer,
          DataTable: MockDataTable
        }
      }
    })
  })

  // 1. 组件初始化测试 - 验证 stores 正确初始化和数据源加载
  it('should initialize stores and load data sources on mount', async () => {
    // Verify stores are properly initialized
    const chatStore = useChatStore()
    const uiStore = useUiStore()
    const dataPrepStore = useDataPrepStore()
    
    expect(chatStore).toBeDefined()
    expect(uiStore).toBeDefined()
    expect(dataPrepStore).toBeDefined()
    
    // Verify loadDataSources is called on mount
    expect(mockDataPrepStore.loadDataSources).toHaveBeenCalledTimes(1)
  })

  // 2. 数据源加载状态测试 - 验证加载中、成功、失败状态
  it('should handle data sources loading states correctly', async () => {
    // Loading state
    mockDataPrepStore.loading = true
    mockDataPrepStore.error = null
    mockDataPrepStore.dataSources = []
    
    // Force update
    await wrapper.vm.$nextTick()
    
    // Check loading state
    const dataSourceSelector = wrapper.findComponent(MockDataSourceSelector)
    expect(dataSourceSelector.props('loading')).toBe(true)
    expect(dataSourceSelector.props('error')).toBeNull()
    
    // Success state
    mockDataPrepStore.loading = false
    mockDataPrepStore.error = null
    mockDataPrepStore.dataSources = [
      { id: 1, name: 'MySQL Source', type: 'mysql' },
      { id: 2, name: 'Excel File', type: 'excel' }
    ]
    
    await wrapper.vm.$nextTick()
    
    expect(dataSourceSelector.props('loading')).toBe(false)
    expect(dataSourceSelector.props('error')).toBeNull()
    expect(dataSourceSelector.props('selectedSource')).toBeNull() // Initially null
    
    // Error state
    mockDataPrepStore.loading = false
    mockDataPrepStore.error = 'Failed to load data sources'
    mockDataPrepStore.dataSources = []
    
    await wrapper.vm.$nextTick()
    
    expect(dataSourceSelector.props('loading')).toBe(false)
    expect(dataSourceSelector.props('error')).toBe('Failed to load data sources')
  })

  // 3. 错误处理测试 - 验证错误显示和重试功能
  it('should handle errors and retry functionality', async () => {
    // Set error state
    mockDataPrepStore.error = 'Failed to load data sources'
    mockDataPrepStore.loading = false
    
    await wrapper.vm.$nextTick()
    
    // Check error message is displayed
    const errorElement = wrapper.find('.error-message')
    expect(errorElement.exists()).toBe(true)
    expect(errorElement.text()).toContain('Failed to load data sources')
    
    // Find retry button and click it
    const retryButton = wrapper.find('.retry-button')
    expect(retryButton.exists()).toBe(true)
    
    await retryButton.trigger('click')
    
    // Verify loadDataSources is called again
    expect(mockDataPrepStore.loadDataSources).toHaveBeenCalledTimes(2)
  })

  // 4. 用户交互测试 - 数据源选择、预览、消息发送
  it('should handle user interactions: source selection, preview, and message sending', async () => {
    // Set up data sources
    mockDataPrepStore.dataSources = [
      { id: 1, name: 'MySQL Source', type: 'mysql' },
      { id: 2, name: 'Excel File', type: 'excel' }
    ]
    mockDataPrepStore.loading = false
    mockDataPrepStore.error = null
    
    await wrapper.vm.$nextTick()
    
    // Test data source selection
    const dataSourceSelector = wrapper.findComponent(MockDataSourceSelector)
    await dataSourceSelector.vm.$emit('update:selectedSource', { id: 1, name: 'MySQL Source', type: 'mysql' })
    
    expect(mockDataPrepStore.setSelectedSource).toHaveBeenCalledWith({ id: 1, name: 'MySQL Source', type: 'mysql' })
    expect(mockDataPrepStore.selectedSource).toEqual({ id: 1, name: 'MySQL Source', type: 'mysql' })
    
    // Test preview functionality
    mockDataPrepStore.previewData = vi.fn().mockResolvedValue({
      data: [{ col1: 'val1', col2: 'val2' }],
      columns: [{ name: 'col1', type: 'string' }, { name: 'col2', type: 'string' }]
    })
    
    await wrapper.vm.$nextTick()
    
    // Trigger preview (assuming there's a button or event)
    const previewButton = wrapper.find('.preview-button')
    if (previewButton.exists()) {
      await previewButton.trigger('click')
    }
    
    expect(mockDataPrepStore.previewData).toHaveBeenCalledWith({ id: 1, name: 'MySQL Source', type: 'mysql' })
    
    // Test message sending
    mockChatStore.userInput = 'What is the sales for last month?'
    mockChatStore.sendQuery = vi.fn().mockResolvedValue(true)
    
    // Simulate form submission
    const input = wrapper.find('input[type="text"]')
    await input.setValue('What is the sales for last month?')
    
    const sendButton = wrapper.find('.send-button')
    await sendButton.trigger('click')
    
    expect(mockChatStore.sendQuery).toHaveBeenCalledTimes(1)
    expect(mockChatStore.sendQuery).toHaveBeenCalledWith('What is the sales for last month?')
    expect(mockChatStore.userInput).toBe('') // Should be cleared after sending
  })

  // 5. 文件上传测试 - 文件类型验证和上传处理
  it('should handle file upload with type validation', async () => {
    // Mock file upload
    mockDataPrepStore.uploadFile = vi.fn().mockResolvedValue({ success: true, source: { id: 3, name: 'uploaded.xlsx', type: 'excel' } })
    
    // Test valid file type (.xlsx)
    const fileInput = wrapper.find('input[type="file"]')
    const validFile = new File(['content'], 'data.xlsx', { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' })
    
    await fileInput.setValue(validFile)
    
    // Verify upload was called with correct file
    expect(mockDataPrepStore.uploadFile).toHaveBeenCalledTimes(1)
    expect(mockDataPrepStore.uploadFile).toHaveBeenCalledWith(validFile)
    
    // Test invalid file type (.txt)
    const invalidFile = new File(['content'], 'data.txt', { type: 'text/plain' })
    
    await fileInput.setValue(invalidFile)
    
    // Verify upload was not called for invalid file type
    expect(mockDataPrepStore.uploadFile).toHaveBeenCalledTimes(1) // Still only called once
    
    // Check for error message
    const errorMessage = wrapper.find('.file-error-message')
    expect(errorMessage.exists()).toBe(true)
    expect(errorMessage.text()).toContain('只支持 Excel 文件')
  })

  // 6. 推荐问题测试 - 点击填充输入框
  it('should handle recommendation question selection', async () => {
    // Set up recommendation questions
    const recommendations = [
      '上月的销售额是多少？',
      '本周的用户增长情况如何？',
      '各地区销售占比是多少？'
    ]
    
    // Mock the recommendations in the component
    const recommendationItems = wrapper.findAll('.recommendation-item')
    
    // Click on first recommendation
    await recommendationItems[0].trigger('click')
    
    // Verify userInput is set
    expect(mockChatStore.userInput).toBe('上月的销售额是多少？')
    
    // Verify the input field is updated
    const input = wrapper.find('input[type="text"]')
    expect(input.element.value).toBe('上月的销售额是多少？')
  })

  // 7. 模式切换测试 - 智能问数/生成报告切换
  it('should handle mode switching between query and report', async () => {
    // Initial state
    expect(mockUiStore.mode).toBe('query')
    
    // Switch to report mode
    const reportModeButton = wrapper.find('.mode-switch-report')
    await reportModeButton.trigger('click')
    
    expect(mockUiStore.setMode).toHaveBeenCalledWith('report')
    expect(mockUiStore.mode).toBe('report')
    
    // Switch back to query mode
    const queryModeButton = wrapper.find('.mode-switch-query')
    await queryModeButton.trigger('click')
    
    expect(mockUiStore.setMode).toHaveBeenCalledWith('query')
    expect(mockUiStore.mode).toBe('query')
  })

  // 8. 响应式状态测试 - computed 属性正确计算
  it('should correctly compute reactive properties', async () => {
    // Test computed properties
    mockDataPrepStore.selectedSource = { id: 1, name: 'MySQL Source', type: 'mysql' }
    mockDataPrepStore.previewDataResult = { data: [{ col1: 'val1' }], columns: [{ name: 'col1', type: 'string' }] }
    mockUiStore.mode = 'report'
    
    await wrapper.vm.$nextTick()
    
    // Check if computed properties are correctly updated
    // These would be defined in Home.vue as computed properties
    // For example:
    // const hasSelectedSource = computed(() => !!dataPrepStore.selectedSource)
    // const hasPreviewData = computed(() => !!dataPrepStore.previewDataResult?.data)
    // const isReportMode = computed(() => uiStore.mode === 'report')
    
    // We can't directly test computed properties without knowing their names,
    // but we can verify that the component renders correctly based on these states
    
    // If there's a computed property that determines if preview should be shown
    const previewModal = wrapper.findComponent(MockDataPreviewModal)
    expect(previewModal.props('visible')).toBe(true) // Assuming preview modal shows when there's data and in query mode
    
    // If there's a computed property for chart visibility
    const chartRenderer = wrapper.findComponent(MockChartRenderer)
    expect(chartRenderer.exists()).toBe(false) // Assuming chart is not shown in report mode
    
    // If there's a computed property for table visibility
    const dataTable = wrapper.findComponent(MockDataTable)
    expect(dataTable.exists()).toBe(true) // Assuming table is shown in report mode
  })
})

// Additional tests for edge cases

describe('Home.vue - Edge Cases', () => {
  let wrapper
  let pinia

  beforeEach(() => {
    // Reset mocks
    vi.clearAllMocks()
    
    // Create Pinia instance
    pinia = createPinia()
    setActivePinia(pinia)
    
    // Mock stores
    vi.mock('@/store/modules/chat', () => ({
      useChatStore: () => mockChatStore
    }))
    
    vi.mock('@/store/modules/ui', () => ({
      useUiStore: () => mockUiStore
    }))
    
    vi.mock('@/store/modules/dataPrep', () => ({
      useDataPrepStore: () => mockDataPrepStore
    }))
    
    // Mock components
    vi.mock('@/components/DataSource/DataSourceSelector.vue', () => ({
      default: MockDataSourceSelector
    }))
    
    vi.mock('@/components/DataSource/DataPreviewModal.vue', () => ({
      default: MockDataPreviewModal
    }))
    
    vi.mock('@/components/ChartRenderer.vue', () => ({
      default: MockChartRenderer
    }))
    
    vi.mock('@/components/DataTable.vue', () => ({
      default: MockDataTable
    }))
    
    // Mount component
    wrapper = mount(Home, {
      global: {
        plugins: [pinia]
      }
    })
  })

  it('should handle empty data sources', async () => {
    mockDataPrepStore.dataSources = []
    mockDataPrepStore.loading = false
    mockDataPrepStore.error = null
    
    await wrapper.vm.$nextTick()
    
    const dataSourceSelector = wrapper.findComponent(MockDataSourceSelector)
    expect(dataSourceSelector.props('dataSources')).toEqual([])
    expect(dataSourceSelector.props('selectedSource')).toBeNull()
  })

  it('should handle empty user input', async () => {
    mockChatStore.userInput = ''
    
    await wrapper.vm.$nextTick()
    
    const sendButton = wrapper.find('.send-button')
    expect(sendButton.exists()).toBe(true)
    
    // Should still be able to trigger send even if input is empty
    await sendButton.trigger('click')
    expect(mockChatStore.sendQuery).toHaveBeenCalledTimes(1)
    expect(mockChatStore.sendQuery).toHaveBeenCalledWith('')
  })

  it('should handle failed message sending', async () => {
    mockChatStore.sendQuery = vi.fn().mockResolvedValue(false)
    mockChatStore.userInput = 'Test query'
    
    await wrapper.vm.$nextTick()
    
    const sendButton = wrapper.find('.send-button')
    await sendButton.trigger('click')
    
    expect(mockChatStore.sendQuery).toHaveBeenCalledTimes(1)
    expect(mockChatStore.sendQuery).toHaveBeenCalledWith('Test query')
    
    // Should not clear input if sending failed
    expect(mockChatStore.userInput).toBe('Test query')
  })

  it('should handle file upload failure', async () => {
    mockDataPrepStore.uploadFile = vi.fn().mockRejectedValue(new Error('Upload failed'))
    
    const fileInput = wrapper.find('input[type="file"]')
    const validFile = new File(['content'], 'data.xlsx', { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' })
    
    await fileInput.setValue(validFile)
    
    // Verify upload was called
    expect(mockDataPrepStore.uploadFile).toHaveBeenCalledTimes(1)
    
    // Check for error message
    const errorMessage = wrapper.find('.file-error-message')
    expect(errorMessage.exists()).toBe(true)
    expect(errorMessage.text()).toContain('上传失败')
  })
})
