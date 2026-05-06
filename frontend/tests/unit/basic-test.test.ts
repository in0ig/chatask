import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia } from 'pinia'

// 创建一个简单的 Vue 组件用于测试
const SimpleComponent = {
  template: '<div class="test-component">Hello World</div>'
}

describe('Basic Vue Component Test', () => {
  it('should render a simple component correctly', () => {
    const pinia = createPinia()
    const wrapper = mount(SimpleComponent, {
      global: {
        plugins: [pinia]
      }
    })
    
    expect(wrapper.find('.test-component').exists()).toBe(true)
    expect(wrapper.text()).toContain('Hello World')
  })
})