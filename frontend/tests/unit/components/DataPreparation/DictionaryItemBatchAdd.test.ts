import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import DictionaryItemBatchAdd from '@/components/DataPreparation/DictionaryItemBatchAdd.vue'

// Mock Element Plus 组件
vi.mock('element-plus', () => ({
  ElAlert: { name: 'ElAlert', template: '<div class="el-alert"><slot /></div>' },
  ElForm: { name: 'ElForm', template: '<form class="el-form"><slot /></form>' },
  ElFormItem: { name: 'ElFormItem', template: '<div class="el-form-item"><slot /></div>' },
  ElInput: { name: 'ElInput', template: '<textarea class="el-input" />' },
  ElButton: { name: 'ElButton', template: '<button class="el-button"><slot /></button>' },
  ElMessage: { success: vi.fn(), error: vi.fn() }
}))

describe('DictionaryItemBatchAdd', () => {
  it('应该正确渲染批量添加表单', () => {
    const wrapper = mount(DictionaryItemBatchAdd, {
      props: {
        loading: false
      }
    })

    expect(wrapper.find('.batch-add-form').exists()).toBe(true)
    expect(wrapper.find('.el-alert').exists()).toBe(true)
    expect(wrapper.find('.el-form').exists()).toBe(true)
  })

  it('应该正确解析文本数据', () => {
    const wrapper = mount(DictionaryItemBatchAdd, {
      props: {
        loading: false
      }
    })

    // 设置测试数据
    wrapper.vm.form.textData = 'male,男,表示男性\nfemale,女,表示女性\nother,其他'

    // 调用解析方法
    const result = wrapper.vm.parseTextData()

    expect(result).toHaveLength(3)
    expect(result[0]).toEqual({
      key: 'male',
      value: '男',
      description: '表示男性'
    })
    expect(result[1]).toEqual({
      key: 'female',
      value: '女',
      description: '表示女性'
    })
    expect(result[2]).toEqual({
      key: 'other',
      value: '其他',
      description: ''
    })
  })

  it('应该正确处理提交事件', async () => {
    const wrapper = mount(DictionaryItemBatchAdd, {
      props: {
        loading: false
      }
    })

    // 设置测试数据
    wrapper.vm.form.textData = 'test1,测试1,描述1\ntest2,测试2,描述2'

    // 触发提交
    await wrapper.vm.handleSubmit()

    // 检查是否触发了 submit 事件
    expect(wrapper.emitted('submit')).toBeTruthy()
    expect(wrapper.emitted('submit')[0][0]).toHaveLength(2)
  })

  it('应该正确处理取消事件', async () => {
    const wrapper = mount(DictionaryItemBatchAdd, {
      props: {
        loading: false
      }
    })

    // 触发取消事件
    wrapper.vm.$emit('cancel')

    expect(wrapper.emitted('cancel')).toBeTruthy()
  })

  it('应该在加载状态下禁用提交按钮', () => {
    const wrapper = mount(DictionaryItemBatchAdd, {
      props: {
        loading: true
      }
    })

    // 检查加载状态是否正确传递
    expect(wrapper.props('loading')).toBe(true)
  })

  it('应该正确处理空数据', () => {
    const wrapper = mount(DictionaryItemBatchAdd, {
      props: {
        loading: false
      }
    })

    // 设置空数据
    wrapper.vm.form.textData = ''

    const result = wrapper.vm.parseTextData()
    expect(result).toHaveLength(0)
  })

  it('应该正确处理格式错误的数据', () => {
    const wrapper = mount(DictionaryItemBatchAdd, {
      props: {
        loading: false
      }
    })

    // 设置格式错误的数据（缺少值）
    wrapper.vm.form.textData = 'key1\nkey2,value2'

    const result = wrapper.vm.parseTextData()
    
    // 应该只解析出格式正确的行
    expect(result).toHaveLength(1)
    expect(result[0]).toEqual({
      key: 'key2',
      value: 'value2',
      description: ''
    })
  })
})