import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'

describe('DataPreparation Store', () => {
  let store: any

  beforeEach(async () => {
    setActivePinia(createPinia())
    const { useDataPreparationStore } = await import('../../../src/store/modules/dataPreparation')
    store = useDataPreparationStore()
  })

  describe('Initial State', () => {
    it('should have correct initial state', () => {
      expect(store.dataSources.data).toEqual([])
      expect(store.dataSources.current).toBeNull()
      expect(store.dataSources.loading).toBe(false)
      expect(store.dataSources.error).toBeNull()

      expect(store.dataTables.data).toEqual([])
      expect(store.dataTables.current).toBeNull()
      expect(store.dataTables.loading).toBe(false)

      expect(store.dictionaries.data).toEqual([])
      expect(store.dictionaries.current).toBeNull()
      expect(store.dictionaries.loading).toBe(false)

      expect(store.relations.data).toEqual([])
      expect(store.relations.loading).toBe(false)

      expect(store.ui.activeTab).toBe('datasource')
      expect(store.ui.modals.dataSourceForm.visible).toBe(false)
    })
  })

  describe('UI State Management', () => {
    it('should set active tab', () => {
      store.setActiveTab('tables')
      expect(store.ui.activeTab).toBe('tables')
    })

    it('should toggle modal visibility', () => {
      expect(store.ui.modals.dataSourceForm.visible).toBe(false)
      
      store.toggleModal('dataSourceForm', true)
      expect(store.ui.modals.dataSourceForm.visible).toBe(true)
      
      store.toggleModal('dataSourceForm')
      expect(store.ui.modals.dataSourceForm.visible).toBe(false)
    })

    it('should clear modal data when closing', () => {
      const testData = { id: '1', name: 'Test' }
      
      store.toggleModal('dataSourceForm', true, testData)
      store.setModalMode('dataSourceForm', 'edit')
      store.toggleModal('dataSourceForm', false)
      
      expect(store.ui.modals.dataSourceForm.visible).toBe(false)
      expect(store.ui.modals.dataSourceForm.data).toBeUndefined()
      expect(store.ui.modals.dataSourceForm.mode).toBeUndefined()
    })
  })

  describe('Data Source Operations', () => {
    it('should create data source with optimistic updates', async () => {
      const newDataSource = {
        name: 'Test Database',
        sourceType: 'DATABASE' as const,
        dbType: 'MYSQL' as const,
        host: 'localhost',
        port: 3306,
        databaseName: 'test_db',
        username: 'test_user'
      }

      const result = await store.createDataSource(newDataSource)
      
      expect(result.success).toBe(true)
      expect(store.dataSources.data).toHaveLength(1)
      expect(store.dataSources.data[0].name).toBe('Test Database')
      expect(store.dataSources.data[0].sourceType).toBe('DATABASE')
    })

    it('should handle batch operations', async () => {
      // Create multiple data sources
      await store.createDataSource({ name: 'DS1', sourceType: 'DATABASE' as const })
      await store.createDataSource({ name: 'DS2', sourceType: 'DATABASE' as const })
      await store.createDataSource({ name: 'DS3', sourceType: 'DATABASE' as const })

      const ids = store.dataSources.data.map((ds: any) => ds.id)
      const result = await store.batchDeleteDataSources(ids)
      
      expect(result.success).toBe(true)
      expect(store.dataSources.data).toHaveLength(0)
    })
  })

  describe('Undo/Redo Operations', () => {
    it('should support undo/redo for data sources', async () => {
      // Initial state
      expect(store.canUndoDataSources).toBe(false)
      expect(store.canRedoDataSources).toBe(false)

      // Create a data source
      await store.createDataSource({
        name: 'Test DS',
        sourceType: 'DATABASE' as const
      })

      expect(store.dataSources.data).toHaveLength(1)
      expect(store.canUndoDataSources).toBe(true)

      // Undo
      store.undoDataSources()
      expect(store.dataSources.data).toHaveLength(0)
      expect(store.canRedoDataSources).toBe(true)

      // Redo
      store.redoDataSources()
      expect(store.dataSources.data).toHaveLength(1)
      expect(store.dataSources.data[0].name).toBe('Test DS')
    })
  })

  describe('State Reset', () => {
    it('should reset all state', async () => {
      // Add some data
      await store.createDataSource({
        name: 'Test DS',
        sourceType: 'DATABASE' as const
      })
      
      store.setActiveTab('tables')
      store.toggleModal('dataSourceForm', true)

      // Reset
      store.resetState()

      // Verify reset
      expect(store.dataSources.data).toHaveLength(0)
      expect(store.dataSources.current).toBeNull()
      expect(store.ui.activeTab).toBe('datasource')
      expect(store.ui.modals.dataSourceForm.visible).toBe(false)
    })
  })

  describe('Error Handling', () => {
    it('should handle API errors gracefully', async () => {
      // Mock console.log to avoid noise in tests
      const consoleSpy = vi.spyOn(console, 'log').mockImplementation(() => {})

      const result = await store.testConnection({})
      
      expect(result.success).toBe(true)
      expect(result.data?.success).toBe(false)
      expect(result.data?.message).toBe('功能未实现')

      consoleSpy.mockRestore()
    })
  })
})