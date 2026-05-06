import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { useDataPreparationStore } from '@/store/modules/dataPreparation'

// 简化的测试，先测试 Store 集成
describe('DictionaryManager Store Integration', () => {
  let store: any

  beforeEach(() => {
    setActivePinia(createPinia())
    store = useDataPreparationStore()
  })

  it('应该正确初始化字典数据', () => {
    expect(store.dictionariesData).toEqual([])
    expect(store.dictionaryItemsData).toEqual([])
  })

  it('应该正确获取字典数据', async () => {
    const result = await store.fetchDictionaries()
    expect(result.success).toBe(true)
    expect(store.dictionariesData).toHaveLength(2)
    expect(store.dictionariesData[0].name).toBe('性别字典')
  })

  it('应该正确获取字典项数据', async () => {
    const result = await store.fetchDictionaryItems('dict-1')
    expect(result.success).toBe(true)
    expect(store.dictionaryItemsData).toHaveLength(2)
    expect(store.dictionaryItemsData[0].key).toBe('M')
  })

  it('应该正确创建字典', async () => {
    const newDict = {
      name: '新字典',
      code: 'NEW_DICT',
      type: 'STATIC' as const,
      description: '新字典描述'
    }
    
    const result = await store.createDictionary(newDict)
    expect(result.success).toBe(true)
    expect(result.data?.name).toBe('新字典')
  })

  it('应该正确更新字典', async () => {
    // 先创建字典数据
    await store.fetchDictionaries()
    
    const updateData = {
      name: '更新后的字典',
      description: '更新后的描述'
    }
    
    const result = await store.updateDictionary('dict-1', updateData)
    expect(result.success).toBe(true)
    expect(result.data?.name).toBe('更新后的字典')
  })

  it('应该正确删除字典', async () => {
    // 先创建字典数据
    await store.fetchDictionaries()
    
    const result = await store.deleteDictionary('dict-1')
    expect(result.success).toBe(true)
    expect(store.dictionariesData).toHaveLength(1)
  })

  it('应该正确创建字典项', async () => {
    const newItem = {
      dictionaryId: 'dict-1',
      key: 'NEW_KEY',
      value: '新项目',
      description: '新项目描述',
      sortOrder: 3,
      status: 'ENABLED' as const
    }
    
    const result = await store.createDictionaryItem(newItem)
    expect(result.success).toBe(true)
    expect(result.data?.key).toBe('NEW_KEY')
  })

  it('应该正确更新字典项', async () => {
    // 先创建字典项数据
    await store.fetchDictionaryItems('dict-1')
    
    const updateData = {
      value: '更新后的值',
      description: '更新后的描述'
    }
    
    const result = await store.updateDictionaryItem('item-1', updateData)
    expect(result.success).toBe(true)
    expect(result.data?.value).toBe('更新后的值')
  })

  it('应该正确删除字典项', async () => {
    // 先创建字典项数据
    await store.fetchDictionaryItems('dict-1')
    
    const result = await store.deleteDictionaryItem('item-1')
    expect(result.success).toBe(true)
    expect(store.dictionaryItemsData).toHaveLength(1)
  })

  it('应该正确过滤字典项', async () => {
    await store.fetchDictionaryItems('dict-1')
    
    const filteredItems = store.getDictionaryItems('dict-1')
    expect(filteredItems).toHaveLength(2)
    expect(filteredItems[0].dictionaryId).toBe('dict-1')
  })
})