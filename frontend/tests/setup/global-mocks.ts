// global-mocks.ts
// This file sets up the global test environment for Vue components

// Import vitest for mocking
import { vi } from 'vitest'

// Import Element Plus stubs setup
import { setupElementPlusMocks } from './element-plus-stubs'

// Mock DOM environment for jsdom
// Ensure document and window are available
if (typeof window === 'undefined') {
  // Create a global window and document object for jsdom
  const { JSDOM } = require('jsdom')
  
  const dom = new JSDOM('<!DOCTYPE html><html><head></head><body></body></html>', {
    url: 'http://localhost',
    resources: 'usable',
    runScripts: 'dangerously',
    pretendToBeVisual: true
  })
  
  // Copy all properties from JSDOM window to global
  ;(global as any).window = dom.window
  ;(global as any).document = dom.window.document
  ;(global as any).navigator = dom.window.navigator
  ;(global as any).location = dom.window.location
  ;(global as any).requestAnimationFrame = dom.window.requestAnimationFrame
  ;(global as any).cancelAnimationFrame = dom.window.cancelAnimationFrame
  ;(global as any).ResizeObserver = dom.window.ResizeObserver
  ;(global as any).Event = dom.window.Event
  ;(global as any).MouseEvent = dom.window.MouseEvent
  ;(global as any).KeyboardEvent = dom.window.KeyboardEvent
  ;(global as any).FocusEvent = dom.window.FocusEvent
  ;(global as any).CustomEvent = dom.window.CustomEvent
  ;(global as any).URL = dom.window.URL
  ;(global as any).Blob = dom.window.Blob
  ;(global as any).FileReader = dom.window.FileReader
  ;(global as any).XMLHttpRequest = dom.window.XMLHttpRequest
  ;(global as any).fetch = dom.window.fetch
}

// Mock console.error and console.warn to avoid test noise
vi.spyOn(console, 'error').mockImplementation(() => {})
vi.spyOn(console, 'warn').mockImplementation(() => {})

// Mock dataTableApi globally to prevent real API calls in tests
// This ensures the mock is applied before any component imports
vi.mock('@/api/dataTableApi', () => ({
  dataTableApi: {
    getById: vi.fn().mockResolvedValue({
      id: 1,
      table_name: 'users',
      source_id: 1,
      sourceName: 'MySQL 数据源',
      fieldCount: 0,
      row_count: 100,
      lastSynced: '2026-01-28T10:00:00Z',
      isActive: true,
      description: '用户信息表',
      created_at: '2026-01-28T10:00:00Z',
      columns: []
    }),
    updateField: vi.fn().mockResolvedValue({}),
    syncStructure: vi.fn().mockResolvedValue({}),
    addField: vi.fn().mockResolvedValue({}),
    deleteField: vi.fn().mockResolvedValue({})
  }
}))

// Set up Element Plus mocks
setupElementPlusMocks()

// Ensure global mocks are available for all tests
export {}