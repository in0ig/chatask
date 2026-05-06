import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { nextTick } from 'vue'
import DictionarySelector from '@/components/DataPreparation/DictionarySelector.vue'
import { dictionaryApi } from '@/api/dictionaryApi'

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { nextTick } from 'vue'
import DictionarySelector from '@/components/DataPreparation/DictionarySelector.vue'
import { dictionaryApi } from '@/api/dictionaryApi'

// Mock dictionaryApi
vi.mock('@/api/dictionaryApi', () => ({
  dictionaryApi: {
    getDictionaries: vi.fn()
  }
}))

// Mock Element Plus icons
vi.mock('@element-plus/icons-vue', () => ({
  ArrowDown: { name: 'ArrowDown', template: '<span>ArrowDown</span>' },
  ArrowUp: { name: 'ArrowUp', template: '<span>ArrowUp</span>' },
  Search: { name: 'Search', template: '<span>Search</span>' },
  Check: { name: 'Check', template: '<span>Check</span>' }
}))

describe('DictionarySelector', () => {
  const mockDictionaries = [
    {
      id: '1',
      name: '用户状态字典',
      code: 'USER_STATUS',
      description: '用户状态枚举值'
    },
    {
      id: '2',
      name: '订单状态字典',
      code: 'ORDER_STATUS',
      description: '订单状态枚举值'
    },
    {
      id: '3',
      name: '支付方式字典',
      code: 'PAYMENT_METHOD',
      description: '支付方式枚举值'
    }
  ]

  beforeEach(() => {
    vi.clearAllMocks()
    // Mock successful API response
    vi.mocked(dictionaryApi.getDictionaries).mockResolvedValue({
      success: true,
      data: mockDictionaries
    })
  })

  it('应该正确渲染组件', async () => {
    const wrapper = mount(DictionarySelector)
    
    expect(wrapper.find('.dictionary-selector').exists()).toBe(true)
    // Focus on testing the component structure rather than specific Element Plus components
    expect(wrapper.vm).toBeDefined()
  })

  it('应该在组件挂载时加载字典列表', async () => {
    mount(DictionarySelector)
    await nextTick()
    
    expect(dictionaryApi.getDictionaries).toHaveBeenCalledTimes(1)
  })

  it('应该在点击输入框时显示字典选择面板', async () => {
    const wrapper = mount(DictionarySelector)
    await nextTick()
    
    // 直接调用方法而不是触发DOM事件
    await wrapper.vm.handleInputClick()
    await nextTick()
    
    // 检查面板是否显示
    expect(wrapper.vm.showPopover).toBe(true)
  })

  it('应该正确显示字典列表', async () => {
    const wrapper = mount(DictionarySelector)
    await nextTick()
    
    // 打开面板
    await wrapper.vm.handleInputClick()
    await nextTick()
    
    // 检查字典数据是否正确加载
    expect(wrapper.vm.dictionaries).toHaveLength(mockDictionaries.length)
    expect(wrapper.vm.filteredDictionaries).toHaveLength(mockDictionaries.length)
  })

  it('应该支持搜索功能', async () => {
    const wrapper = mount(DictionarySelector)
    await nextTick()
    
    // 打开面板
    await wrapper.vm.handleInputClick()
    await nextTick()
    
    // 直接设置搜索查询而不是使用setData
    wrapper.vm.searchQuery = '用户'
    await wrapper.vm.handleSearch()
    await nextTick()
    
    // 检查过滤结果
    expect(wrapper.vm.filteredDictionaries).toHaveLength(1)
    expect(wrapper.vm.filteredDictionaries[0].name).toBe('用户状态字典')
  })

  it('应该能够选择字典', async () => {
    const wrapper = mount(DictionarySelector)
    await nextTick()
    
    // 打开面板
    await wrapper.vm.handleInputClick()
    await nextTick()
    
    // 选择第一个字典
    const firstDict = mockDictionaries[0]
    await wrapper.vm.handleSelectDictionary(firstDict)
    await nextTick()
    
    expect(wrapper.vm.selectedDictionaryId).toBe(firstDict.id)
  })

  it('应该正确显示选中字典的名称', async () => {
    const wrapper = mount(DictionarySelector, {
      props: {
        modelValue: '1'
      }
    })
    await nextTick()
    
    // 等待字典加载完成
    await new Promise(resolve => setTimeout(resolve, 100))
    await nextTick()
    
    expect(wrapper.vm.displayValue).toBe('用户状态字典 (USER_STATUS)')
  })

  it('应该在确认时触发change事件', async () => {
    const wrapper = mount(DictionarySelector)
    await nextTick()
    
    // 选择字典
    const firstDict = mockDictionaries[0]
    await wrapper.vm.handleSelectDictionary(firstDict)
    await wrapper.vm.handleConfirm()
    await nextTick()
    
    // 检查事件是否被触发
    const changeEvents = wrapper.emitted('change')
    expect(changeEvents).toBeTruthy()
    expect(changeEvents![0]).toEqual([firstDict.id, firstDict])
  })

  it('应该在取消时恢复原始值', async () => {
    const wrapper = mount(DictionarySelector, {
      props: {
        modelValue: '1'
      }
    })
    await nextTick()
    
    // 选择不同的字典
    const secondDict = mockDictionaries[1]
    await wrapper.vm.handleSelectDictionary(secondDict)
    
    // 取消操作
    await wrapper.vm.handleCancel()
    await nextTick()
    
    // 检查是否恢复到原始值
    expect(wrapper.vm.selectedDictionaryId).toBe('1')
    expect(wrapper.vm.showPopover).toBe(false)
  })

  it('应该支持清空选择', async () => {
    const wrapper = mount(DictionarySelector, {
      props: {
        modelValue: '1'
      }
    })
    await nextTick()
    
    // 清空选择
    await wrapper.vm.handleClear()
    await nextTick()
    
    expect(wrapper.vm.selectedDictionaryId).toBe(null)
    
    // 检查update:modelValue事件
    const updateEvents = wrapper.emitted('update:modelValue')
    expect(updateEvents).toBeTruthy()
    expect(updateEvents![updateEvents!.length - 1]).toEqual([null])
  })

  it('应该在API失败时显示空状态', async () => {
    // Mock API failure
    vi.mocked(dictionaryApi.getDictionaries).mockResolvedValue({
      success: false,
      error: 'API Error'
    })
    
    const wrapper = mount(DictionarySelector)
    await nextTick()
    
    // 等待API调用完成
    await new Promise(resolve => setTimeout(resolve, 100))
    await nextTick()
    
    expect(wrapper.vm.dictionaries).toHaveLength(0)
    expect(wrapper.vm.filteredDictionaries).toHaveLength(0)
  })

  it('应该在禁用状态下不响应点击', async () => {
    const wrapper = mount(DictionarySelector, {
      props: {
        disabled: true
      }
    })
    await nextTick()
    
    // 尝试点击输入框
    await wrapper.vm.handleInputClick()
    await nextTick()
    
    // 面板不应该显示
    expect(wrapper.vm.showPopover).toBe(false)
  })

  it('应该支持不同的尺寸', () => {
    const wrapper = mount(DictionarySelector, {
      props: {
        size: 'small'
      }
    })
    
    expect(wrapper.props('size')).toBe('small')
  })

  it('应该支持自定义占位符', () => {
    const customPlaceholder = '请选择关联字典'
    const wrapper = mount(DictionarySelector, {
      props: {
        placeholder: customPlaceholder
      }
    })
    
    expect(wrapper.props('placeholder')).toBe(customPlaceholder)
  })

  // 核心功能测试：验证API修复
  it('应该使用正确的API调用字典列表', async () => {
    const wrapper = mount(DictionarySelector)
    await nextTick()
    
    // 验证使用了正确的API而不是硬编码的fetch
    expect(dictionaryApi.getDictionaries).toHaveBeenCalledTimes(1)
    
    // 验证字典数据正确加载
    expect(wrapper.vm.dictionaries).toEqual(mockDictionaries)
    expect(wrapper.vm.filteredDictionaries).toEqual(mockDictionaries)
  })
})