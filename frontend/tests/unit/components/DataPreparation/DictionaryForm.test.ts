import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import DictionaryForm from '@/components/DataPreparation/DictionaryForm.vue'
import type { Dictionary } from '@/store/modules/dataPreparation'

// Mock Element Plus 组件
vi.mock('element-plus', () => ({
  ElForm: { name: 'ElForm', template: '<form class="el-form"><slot /></form>' },
  ElFormItem: { name: 'ElFormItem', template: '<div class="el-form-item"><slot /></div>' },
  ElInput: { name: 'ElInput', template: '<input class="el-input" />' },
  ElTreeSelect: { name: 'ElTreeSelect', template: '<select class="el-tree-select" />' },
  ElRadioGroup: { name: 'ElRadioGroup', template: '<div class="el-radio-group"><slot /></div>' },
  ElRadio: { name: 'ElRadio', template: '<label class="el-radio"><slot /></label>' },
  ElButton: { name: 'ElButton', template: '<button class="el-button"><slot /></button>' }
}))

// Mock 数据
const mockDictionaries: Dictionary[] = [
  {
    id: '1',
    name: '系统字典',
    code: 'system',
    parentId: null,
    status: 'ENABLED',
    description: '系统字典',
    createdAt: '2024-01-01',
    updatedAt: '2024-01-01'
  },
  {
    id: '2',
    name: '业务字典',
    code: 'business',
    parentId: '1',
    status: 'ENABLED',
    description: '业务字典',
    createdAt: '2024-01-01',
    updatedAt: '2024-01-01'
  }
]

describe('DictionaryForm', () => {
  let wrapper: any

  beforeEach(() => {
    wrapper = mount(DictionaryForm, {
      props: {
        mode: 'create',
        dictionaries: mockDictionaries,
        loading: false
      }
    })
  })

  it('应该正确渲染表单结构', () => {
    expect(wrapper.find('.dictionary-form').exists()).toBe(true)
    expect(wrapper.find('.el-form').exists()).toBe(true)
  })

  it('应该在创建模式下初始化空表单', () => {
    expect(wrapper.vm.form.name).toBe('')
    expect(wrapper.vm.form.code).toBe('')
    expect(wrapper.vm.form.status).toBe('ENABLED')
    expect(wrapper.vm.form.parentId).toBe(null)
  })

  it('应该在编辑模式下填充表单数据', async () => {
    const dictionary = mockDictionaries[0]
    await wrapper.setProps({
      mode: 'edit',
      dictionary
    })

    // 等待 Vue 更新
    await wrapper.vm.$nextTick()

    // 检查表单数据是否正确填充
    expect(wrapper.vm.form.name).toBe(dictionary.name)
    expect(wrapper.vm.form.code).toBe(dictionary.code)
    expect(wrapper.vm.form.status).toBe(dictionary.status)
    expect(wrapper.vm.form.description).toBe(dictionary.description)
  })

  it('应该正确生成父级字典选项', () => {
    // 检查父级字典选项是否正确生成
    expect(wrapper.vm.parentOptions).toBeDefined()
    expect(Array.isArray(wrapper.vm.parentOptions)).toBe(true)
  })

  it('应该防止循环依赖', async () => {
    const dictionary = mockDictionaries[1] // 子字典
    await wrapper.setProps({
      mode: 'edit',
      dictionary
    })

    // 在编辑模式下，父级选项不应包含当前字典及其子字典
    const parentOptions = wrapper.vm.parentOptions
    const currentDictionaryOption = parentOptions.find((opt: any) => opt.id === dictionary.id)
    expect(currentDictionaryOption).toBeUndefined()
  })

  it('应该正确处理表单提交', async () => {
    // 模拟表单验证通过
    wrapper.vm.$refs.formRef = {
      validate: vi.fn().mockResolvedValue(true)
    }

    // 填充表单数据
    wrapper.vm.form.name = '测试字典'
    wrapper.vm.form.code = 'test'

    // 触发提交
    await wrapper.vm.handleSubmit()

    expect(wrapper.emitted('submit')).toBeTruthy()
    expect(wrapper.emitted('submit')[0][0]).toEqual(
      expect.objectContaining({
        name: '测试字典',
        code: 'test'
      })
    )
  })

  it('应该正确处理取消操作', async () => {
    await wrapper.vm.handleCancel()
    expect(wrapper.emitted('cancel')).toBeTruthy()
  })

  it('应该有正确的表单验证规则', () => {
    expect(wrapper.vm.rules.name).toBeDefined()
    expect(wrapper.vm.rules.code).toBeDefined()
    expect(wrapper.vm.rules.status).toBeDefined()
    
    // 检查必填验证
    expect(wrapper.vm.rules.name[0].required).toBe(true)
    expect(wrapper.vm.rules.code[0].required).toBe(true)
  })

  it('应该在表单重置时清空数据', async () => {
    // 填充一些数据
    wrapper.vm.form.name = '测试'
    wrapper.vm.form.code = 'test'
    
    // 重置表单
    wrapper.vm.resetForm()
    
    expect(wrapper.vm.form.name).toBe('')
    expect(wrapper.vm.form.code).toBe('')
    expect(wrapper.vm.form.parentId).toBe(null)
    expect(wrapper.vm.form.status).toBe('ENABLED')
  })
})