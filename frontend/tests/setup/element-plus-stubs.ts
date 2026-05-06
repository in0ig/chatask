import { defineComponent } from 'vue'

// 定义一个简单的 mock 组件，渲染为 div
const mockElementPlusComponent = (name: string) => {
  return defineComponent({
    template: `<div class="el-${name.toLowerCase()}">${name}</div>`
  })
}

// Element Plus 组件列表
const elementPlusComponents = [
  'el-form',
  'el-form-item',
  'el-input',
  'el-select',
  'el-option',
  'el-button',
  'el-tabs',
  'el-tab-pane',
  'el-card',
  'el-alert',
  'el-progress',
  'el-tag',
  'el-switch',
  'el-tree',
  'el-drawer',
  'el-radio-group',
  'el-radio',
  'el-message',
  'el-notification',
  'el-icon'
]

// 注册所有 Element Plus 组件为 mock
export function registerElementPlusStubs() {
  elementPlusComponents.forEach(component => {
    // 使用 Vue 的全局组件注册
    ;(global as any).component = (global as any).component || {}
    ;(global as any).component[component] = mockElementPlusComponent(component)
  })
}

// 为表单组件提供 mock 方法
export function mockFormMethods() {
  // 创建一个 mock 表单引用对象
  const mockFormRef = {
    validate: vi.fn().mockResolvedValue(true),
    validateField: vi.fn().mockResolvedValue(true),
    resetFields: vi.fn(),
    clearValidate: vi.fn()
  }
  
  // 将 mock 表单引用添加到全局作用域，供测试使用
  ;(global as any).mockFormRef = mockFormRef
}

// 导出一个函数来设置所有 Element Plus 模拟
export function setupElementPlusMocks() {
  registerElementPlusStubs()
  mockFormMethods()
}

// 立即调用设置函数以确保模拟已注册
setupElementPlusMocks()