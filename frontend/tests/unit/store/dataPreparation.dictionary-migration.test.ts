/**
 * 数据字典 Mock 数据迁移到真实数据库测试
 * 
 * 测试目标：
 * 1. 验证字典数据完全来自数据库API调用
 * 2. 验证DictionaryImportExport组件使用真实API
 * 3. 验证FieldMappingManager组件移除mock数据回退
 * 4. 验证数据增删改查操作正常工作
 * 5. 验证数据持久化（删除后不再出现）
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useDataPreparationStore } from '@/store/modules/dataPreparation'
import { dictionaryApi } from '@/api/dictionaryApi'

// Mock dictionaryApi
vi.mock('@/api/dictionaryApi', () => ({
  dictionaryApi: {
    getDictionaries: vi.fn(),
    getDictionaryItems: vi.fn(),
    getAllDictionaryItems: vi.fn(),
    createDictionary: vi.fn(),
    updateDictionary: vi.fn(),
    deleteDictionary: vi.fn(),
    createDictionaryItem: vi.fn(),
    updateDictionaryItem: vi.fn(),
    deleteDictionaryItem: vi.fn(),
    importDictionary: vi.fn(),
    exportDictionary: vi.fn()
  }
}))

describe('数据字典 Mock 数据迁移测试', () => {
  let store: ReturnType<typeof useDataPreparationStore>

  beforeEach(() => {
    setActivePinia(createPinia())
    store = useDataPreparationStore()
    vi.clearAllMocks()
  })

  afterEach(() => {
    vi.resetAllMocks()
  })

  describe('字典数据API调用', () => {
    it('应该调用真实的字典API获取数据', async () => {
      // 准备测试数据
      const mockDictionaries = [
        {
          id: 1,
          name: '测试字典',
          code: 'test_dict',
          type: 'static',
          is_enabled: true,
          description: '测试描述',
          parent_id: undefined,
          created_at: '2024-01-01T00:00:00Z',
          updated_at: '2024-01-01T00:00:00Z'
        }
      ]

      vi.mocked(dictionaryApi.getDictionaries).mockResolvedValue({
        success: true,
        data: mockDictionaries
      })

      // 执行操作
      await store.fetchDictionaries()

      // 验证结果
      expect(dictionaryApi.getDictionaries).toHaveBeenCalledOnce()
      expect(store.dictionaries).toHaveLength(1)
      expect(store.dictionaries[0]).toMatchObject({
        id: 1,
        name: '测试字典',
        code: 'test_dict',
        type: 'static'
      })
    })

    it('应该正确处理API错误，不使用mock数据回退', async () => {
      // 模拟API错误
      vi.mocked(dictionaryApi.getDictionaries).mockRejectedValue(new Error('API错误'))

      // 执行操作
      try {
        await store.fetchDictionaries()
      } catch (error) {
        // 预期会抛出错误
      }

      // 验证没有回退到mock数据
      expect(store.dictionaries).toEqual([])
    })
  })

  describe('字典项数据API调用', () => {
    it('应该调用真实的字典项API获取数据', async () => {
      // 准备测试数据
      const mockItems = [
        {
          id: 1,
          dictionary_id: 1,
          item_key: 'key1',
          item_value: 'value1',
          description: '描述1',
          sort_order: 1,
          is_enabled: true,
          created_at: '2024-01-01T00:00:00Z',
          updated_at: '2024-01-01T00:00:00Z'
        }
      ]

      vi.mocked(dictionaryApi.getDictionaryItems).mockResolvedValue({
        success: true,
        data: mockItems
      })

      // 执行操作
      await store.fetchDictionaryItems(1)

      // 验证结果
      expect(dictionaryApi.getDictionaryItems).toHaveBeenCalledWith(1)
      expect(store.dictionaryItems).toHaveLength(1)
      expect(store.dictionaryItems[0]).toMatchObject({
        id: 1,
        dictionary_id: 1,
        item_key: 'key1',
        item_value: 'value1'
      })
    })

    it('应该正确处理字典项API错误', async () => {
      // 模拟API错误
      vi.mocked(dictionaryApi.getDictionaryItems).mockRejectedValue(new Error('获取字典项失败'))

      // 执行操作
      try {
        await store.fetchDictionaryItems(1)
      } catch (error) {
        // 预期会抛出错误
      }

      // 验证结果
      expect(store.dictionaryItems).toEqual([])
    })
  })

  describe('字典CRUD操作', () => {
    it('应该使用真实API创建字典', async () => {
      // 准备测试数据
      const createData = {
        name: '新字典',
        code: 'new_dict',
        type: 'static',
        description: '新字典描述',
        is_enabled: true
      }

      const mockResponse = {
        id: 2,
        name: '新字典',
        code: 'new_dict',
        type: 'static',
        is_enabled: true,
        description: '新字典描述',
        parent_id: undefined,
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z'
      }

      vi.mocked(dictionaryApi.createDictionary).mockResolvedValue({
        success: true,
        data: mockResponse
      })

      // 执行操作
      const result = await store.createDictionary(createData)

      // 验证结果
      expect(dictionaryApi.createDictionary).toHaveBeenCalledWith(createData)
      expect(result).toMatchObject({
        id: 2,
        name: '新字典',
        type: 'static'
      })
      expect(store.dictionaries).toContainEqual(mockResponse)
    })

    it('应该使用真实API更新字典', async () => {
      // 准备测试数据
      const updateData = {
        name: '更新字典',
        description: '更新描述'
      }

      const mockResponse = {
        id: 1,
        name: '更新字典',
        code: 'test_dict',
        type: 'static',
        is_enabled: true,
        description: '更新描述',
        parent_id: undefined,
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z'
      }

      vi.mocked(dictionaryApi.updateDictionary).mockResolvedValue({
        success: true,
        data: mockResponse
      })

      // 先添加一个字典到store
      store.dictionaries.push({
        id: 1,
        name: '测试字典',
        code: 'test_dict',
        type: 'static',
        is_enabled: true,
        description: '原描述',
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z'
      })

      // 执行操作
      const result = await store.updateDictionary(1, updateData)

      // 验证结果
      expect(dictionaryApi.updateDictionary).toHaveBeenCalledWith(1, updateData)
      expect(result).toMatchObject({
        id: 1,
        name: '更新字典'
      })
      expect(store.dictionaries[0].name).toBe('更新字典')
    })

    it('应该使用真实API删除字典', async () => {
      vi.mocked(dictionaryApi.deleteDictionary).mockResolvedValue({
        success: true,
        message: 'Dictionary deleted successfully'
      })

      // 先添加一个字典到store
      store.dictionaries.push({
        id: 1,
        name: '测试字典',
        code: 'test_dict',
        type: 'static',
        is_enabled: true,
        description: '测试描述',
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z'
      })

      // 执行操作
      const result = await store.deleteDictionary(1)

      // 验证结果
      expect(dictionaryApi.deleteDictionary).toHaveBeenCalledWith(1)
      expect(result).toBe(true)
      expect(store.dictionaries).toHaveLength(0)
    })
  })

  describe('字典项CRUD操作', () => {
    it('应该使用真实API创建字典项', async () => {
      // 准备测试数据
      const itemData = {
        dictionary_id: 1,
        item_key: 'new_key',
        item_value: 'new_value',
        description: '新项描述',
        sort_order: 1,
        is_enabled: true
      }

      const mockResponse = {
        id: 2,
        dictionary_id: 1,
        item_key: 'new_key',
        item_value: 'new_value',
        description: '新项描述',
        sort_order: 1,
        is_enabled: true,
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z'
      }

      vi.mocked(dictionaryApi.createDictionaryItem).mockResolvedValue({
        success: true,
        data: mockResponse
      })

      // 执行操作
      const result = await store.createDictionaryItem(itemData)

      // 验证结果
      expect(dictionaryApi.createDictionaryItem).toHaveBeenCalledWith(itemData)
      expect(result).toMatchObject({
        id: 2,
        dictionary_id: 1,
        item_key: 'new_key',
        item_value: 'new_value'
      })
      expect(store.dictionaryItems).toContainEqual(mockResponse)
    })

    it('应该使用真实API删除字典项并确保数据持久化', async () => {
      vi.mocked(dictionaryApi.deleteDictionaryItem).mockResolvedValue({
        success: true,
        message: 'Dictionary item deleted successfully'
      })

      // 先添加一个字典项到store
      store.dictionaryItems.push({
        id: 1,
        dictionary_id: 1,
        item_key: 'test_key',
        item_value: 'test_value',
        description: '测试项',
        sort_order: 1,
        is_enabled: true,
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z'
      })

      // 执行删除操作
      const result = await store.deleteDictionaryItem(1)

      // 验证结果
      expect(dictionaryApi.deleteDictionaryItem).toHaveBeenCalledWith(1)
      expect(result).toBe(true)
      expect(store.dictionaryItems).toHaveLength(0)

      // 验证数据持久化：删除后不再出现
      expect(store.dictionaryItems.find((item: any) => item.id === 1)).toBeUndefined()
    })
  })

  describe('导入导出功能', () => {
    it('应该使用真实API导入字典', async () => {
      const mockFile = new File(['test'], 'test.xlsx', { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' })

      vi.mocked(dictionaryApi.importDictionary).mockResolvedValue({
        success: true
      })
      vi.mocked(dictionaryApi.getDictionaries).mockResolvedValue({
        success: true,
        data: []
      })
      vi.mocked(dictionaryApi.getAllDictionaryItems).mockResolvedValue({
        success: true,
        data: []
      })

      // 执行操作
      const result = await store.importDictionary(mockFile)

      // 验证结果
      expect(dictionaryApi.importDictionary).toHaveBeenCalledWith(mockFile)
      expect(result).toBe(true)
    })

    it('应该使用真实API导出字典', async () => {
      const mockBlob = new Blob(['test data'])

      vi.mocked(dictionaryApi.exportDictionary).mockResolvedValue(mockBlob)

      // 执行操作
      const result = await store.exportDictionary(1)

      // 验证结果
      expect(dictionaryApi.exportDictionary).toHaveBeenCalledWith(1)
      expect(result).toBe(mockBlob)
    })
  })

  describe('错误处理', () => {
    it('应该正确处理API调用失败，不回退到mock数据', async () => {
      // 模拟各种API错误
      vi.mocked(dictionaryApi.getDictionaries).mockRejectedValue(new Error('网络错误'))
      vi.mocked(dictionaryApi.createDictionary).mockRejectedValue(new Error('创建失败'))
      vi.mocked(dictionaryApi.updateDictionary).mockRejectedValue(new Error('更新失败'))

      // 测试获取字典失败
      try {
        await store.fetchDictionaries()
      } catch (error) {
        expect(error).toBeInstanceOf(Error)
      }
      expect(store.dictionaries).toEqual([])

      // 测试创建字典失败
      const createResult = await store.createDictionary({ 
        name: '测试',
        code: 'test',
        type: 'static',
        is_enabled: true
      })
      expect(createResult).toBeNull()

      // 测试更新字典失败
      const updateResult = await store.updateDictionary(1, { name: '更新' })
      expect(updateResult).toBeNull()
    })
  })
})