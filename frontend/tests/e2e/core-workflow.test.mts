import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useChatStore } from '../../src/store/modules/chat'
import { useDataPrepStore } from '../../src/store/modules/dataPrep'
import { useUIStore } from '../../src/store/modules/ui'

// Mock response data
const mockDataSourceResponse = {
  id: '1',
  name: 'Test MySQL Source',
  type: 'mysql',
  isActive: true,
  createdAt: new Date(),
  updatedAt: new Date()
}

const mockQueryResponse = {
  result: {
    explanation: 'Sales data for the last month shows an upward trend',
    chart_type: 'line',
    data: [
      { month: 'Jan', sales: 12000 },
      { month: 'Feb', sales: 15000 },
      { month: 'Mar', sales: 18000 }
    ]
  }
}

const mockHistoryResponse = [
  {
    id: 1,
    queryText: 'Show sales data for last month',
    result: mockQueryResponse.result,
    chartType: 'line',
    created_at: new Date().toISOString()
  },
  {
    id: 2,
    queryText: 'Show top 5 customers',
    result: { explanation: 'Top customers data' },
    chartType: 'bar',
    created_at: new Date().toISOString()
  }
]

// Mock fetch globally
const originalFetch = global.fetch
let mockFetch: any

beforeEach(() => {
  mockFetch = vi.fn((url: string, options?: any) => {
    // 更具体的条件应该放在前面
    if (url.includes('/api/query/history') && options?.method === 'DELETE') {
      return Promise.resolve({
        ok: true,
        json: async () => ({ success: true })
      })
    } else if (url.includes('/api/query/history')) {
      // 这会匹配 GET /api/query/history
      return Promise.resolve({
        ok: true,
        json: async () => mockHistoryResponse
      })
    } else if (url.includes('/api/query')) {
      return Promise.resolve({
        ok: true,
        json: async () => mockQueryResponse
      })
    } else if (url.includes('/api/datasources') && options?.method === 'POST') {
      return Promise.resolve({
        ok: true,
        json: async () => mockDataSourceResponse
      })
    } else if (url.includes('/api/datasources') && !options?.method) {
      return Promise.resolve({
        ok: true,
        json: async () => [mockDataSourceResponse]
      })
    }
    return Promise.resolve({
      ok: false,
      status: 404
    })
  })
  
  global.fetch = mockFetch
})

afterEach(() => {
  global.fetch = originalFetch
})

describe('Core Workflow E2E Test', () => {
  beforeEach(() => {
    // Initialize Pinia store
    const pinia = createPinia()
    setActivePinia(pinia)
  })

  it('should create data source and activate it', async () => {
    // Arrange
    const dataPrepStore = useDataPrepStore()
    const uiStore = useUIStore()
    
    // Act - Create data source
    await dataPrepStore.createDataSource({
      name: 'Test MySQL Source',
      type: 'mysql',
      connectionString: 'mysql://localhost:3306/testdb'
    })
    
    // Assert
    expect(mockFetch).toHaveBeenCalledWith(
      '/api/datasources',
      expect.objectContaining({
        method: 'POST'
      })
    )
    expect(dataPrepStore.dataSources).toHaveLength(1)
    expect(dataPrepStore.dataSources[0].name).toBe('Test MySQL Source')
  })

  it('should send query and receive response', async () => {
    // Arrange
    const chatStore = useChatStore()
    const dataPrepStore = useDataPrepStore()
    
    // Set up mock data source
    dataPrepStore.activeDataSourceId = '1'
    chatStore.currentDataSource = '1'
    
    // Act - Send message
    await chatStore.sendMessage('Show sales data for last month')
    
    // Assert
    expect(mockFetch).toHaveBeenCalledWith(
      '/api/query',
      expect.objectContaining({
        method: 'POST'
      })
    )
    // Verify messages were added (user message + AI response)
    expect(chatStore.messages.length).toBeGreaterThanOrEqual(1)
    expect(chatStore.messages[0].role).toBe('user')
    expect(chatStore.messages[0].content).toBe('Show sales data for last month')
  })

  it('should display query result in message stream', async () => {
    // Arrange
    const chatStore = useChatStore()
    
    // Set up initial state
    chatStore.currentDataSource = '1'
    
    // Act - Send query
    await chatStore.sendMessage('Show sales data for last month')
    
    // Assert - Verify both user and AI messages are in the stream
    expect(chatStore.messages.length).toBeGreaterThanOrEqual(2)
    
    // Check user message
    const userMessage = chatStore.messages.find(m => m.role === 'user')
    expect(userMessage).toBeDefined()
    expect(userMessage?.content).toBe('Show sales data for last month')
    
    // Check AI message
    const aiMessage = chatStore.messages.find(m => m.role === 'assistant')
    expect(aiMessage).toBeDefined()
    expect(aiMessage?.chartType).toBe('line')
  })

  it('should add query to history', async () => {
    // Arrange
    const chatStore = useChatStore()
    
    // Set up initial state
    chatStore.currentDataSource = '1'
    
    // Act - Send query (which should add to history)
    await chatStore.sendMessage('Show sales data for last month')
    
    // Assert - Verify query was added to history
    expect(chatStore.queryHistory.length).toBeGreaterThanOrEqual(1)
    expect(chatStore.queryHistory[0].queryText).toBe('Show sales data for last month')
  })

  it('should load and display query history', async () => {
    // Arrange
    const chatStore = useChatStore()
    
    // Act - Load history
    await chatStore.loadHistory()
    
    // Assert
    expect(mockFetch).toHaveBeenCalledWith('/api/query/history')
    expect(chatStore.queryHistory.length).toBeGreaterThanOrEqual(1)
    // The store maps the response data, so check the actual field names
    expect(chatStore.queryHistory[0].queryText).toBe('Show sales data for last month')
  })

  it('should clear session messages', async () => {
    // Arrange
    const chatStore = useChatStore()
    
    // Add some messages
    chatStore.currentDataSource = '1'
    await chatStore.sendMessage('Show sales data for last month')
    
    // Verify messages exist
    expect(chatStore.messages.length).toBeGreaterThan(0)
    
    // Act - Clear messages
    chatStore.clearMessages()
    
    // Assert
    expect(chatStore.messages).toHaveLength(0)
  })
})
