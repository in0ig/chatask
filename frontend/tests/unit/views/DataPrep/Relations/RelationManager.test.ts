import { describe, it, expect, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia } from 'pinia'
import RelationManager from '@/views/DataPrep/Relations/RelationManager.vue'

describe('RelationManager', () => {
  let wrapper: any
  let pinia: any

  beforeEach(() => {
    pinia = createPinia()
    wrapper = mount(RelationManager, {
      global: {
        plugins: [pinia],
        stubs: {
          'RelationList': true,
          'RelationTable': true,
          'RelationGraph': true
        }
      }
    })
  })

  describe('基础渲染', () => {
    it('应该正确渲染关联管理容器', () => {
      expect(wrapper.find('.relation-manager-container').exists()).toBe(true)
      expect(wrapper.find('.header').exists()).toBe(true)
      expect(wrapper.find('.content').exists()).toBe(true)
    })

    it('应该显示正确的标题', () => {
      expect(wrapper.find('.title').text()).toBe('表关联管理')
    })

    it('应该有视图切换按钮组', () => {
      const buttonGroup = wrapper.find('.view-switcher')
      expect(buttonGroup.exists()).toBe(true)
      
      const buttons = buttonGroup.findAll('button')
      expect(buttons.length).toBe(2)
      expect(buttons[0].text()).toBe('列表视图')
      expect(buttons[1].text()).toBe('图形视图')
    })
  })

  describe('视图切换功能', () => {
    it('应该默认显示列表视图', () => {
      expect(wrapper.vm.currentView).toBe('list')
      expect(wrapper.find('relationlist-stub').exists()).toBe(true)
      expect(wrapper.find('.graph-view-placeholder').exists()).toBe(false)
    })

    it('应该能够切换到图形视图', async () => {
      const graphButton = wrapper.findAll('button')[1]
      await graphButton.trigger('click')
      
      expect(wrapper.vm.currentView).toBe('graph')
      expect(wrapper.find('relationlist-stub').exists()).toBe(false)
      expect(wrapper.find('.graph-view-placeholder').exists()).toBe(true)
    })

    it('应该能够从图形视图切换回列表视图', async () => {
      // 先切换到图形视图
      const graphButton = wrapper.findAll('button')[1]
      await graphButton.trigger('click')
      expect(wrapper.vm.currentView).toBe('graph')
      
      // 再切换回列表视图
      const listButton = wrapper.findAll('button')[0]
      await listButton.trigger('click')
      
      expect(wrapper.vm.currentView).toBe('list')
      expect(wrapper.find('relationlist-stub').exists()).toBe(true)
      expect(wrapper.find('.graph-view-placeholder').exists()).toBe(false)
    })

    it('应该正确高亮当前选中的视图按钮', async () => {
      // 默认列表视图按钮应该是 primary 类型
      let buttons = wrapper.findAll('button')
      expect(buttons[0].attributes('type')).toBe('primary')
      expect(buttons[1].attributes('type')).toBe('default')
      
      // 切换到图形视图后，图形视图按钮应该是 primary 类型
      await buttons[1].trigger('click')
      buttons = wrapper.findAll('button')
      expect(buttons[0].attributes('type')).toBe('default')
      expect(buttons[1].attributes('type')).toBe('primary')
    })
  })

  describe('响应式设计', () => {
    it('应该有正确的样式类', () => {
      expect(wrapper.find('.relation-manager-container').exists()).toBe(true)
      expect(wrapper.find('.header').exists()).toBe(true)
      expect(wrapper.find('.content').exists()).toBe(true)
    })

    it('应该有正确的布局结构', () => {
      const header = wrapper.find('.header')
      expect(header.find('.title').exists()).toBe(true)
      expect(header.find('.view-switcher').exists()).toBe(true)
    })
  })

  describe('组件集成', () => {
    it('应该正确传递 props 给子组件', () => {
      // 当前是列表视图时，应该渲染 RelationList 组件
      expect(wrapper.find('relationlist-stub').exists()).toBe(true)
    })

    it('应该在图形视图时显示占位符', async () => {
      const graphButton = wrapper.findAll('button')[1]
      await graphButton.trigger('click')
      
      const placeholder = wrapper.find('.graph-view-placeholder')
      expect(placeholder.exists()).toBe(true)
      expect(placeholder.text()).toContain('图形视图将在后续实现')
    })
  })
})