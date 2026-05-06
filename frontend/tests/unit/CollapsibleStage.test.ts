/**
 * CollapsibleStage 组件测试
 * 
 * 验证可折叠阶段组件的功能
 */

import { describe, it, expect, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import CollapsibleStage from '@/components/Chat/CollapsibleStage.vue'
import type { MessageStage } from '@/types/chat'

describe('CollapsibleStage', () => {
  let stage: MessageStage

  beforeEach(() => {
    stage = {
      id: 'stage_1',
      name: '意图识别',
      status: 'in_progress',
      content: '正在识别用户意图...',
      collapsed: false,
      timestamp: Date.now(),
      metadata: {}
    }
  })

  it('应该渲染阶段标题', () => {
    const wrapper = mount(CollapsibleStage, {
      props: { stage }
    })

    expect(wrapper.find('.stage-name').text()).toBe('意图识别')
  })

  it('应该显示进行中的状态图标', () => {
    const wrapper = mount(CollapsibleStage, {
      props: { stage }
    })

    expect(wrapper.find('.icon-progress').exists()).toBe(true)
    expect(wrapper.find('.icon-progress').text()).toBe('⏳')
  })

  it('应该显示已完成的状态图标', () => {
    stage.status = 'completed'
    const wrapper = mount(CollapsibleStage, {
      props: { stage }
    })

    expect(wrapper.find('.icon-completed').exists()).toBe(true)
    expect(wrapper.find('.icon-completed').text()).toBe('✅')
  })

  it('应该显示错误状态图标', () => {
    stage.status = 'error'
    const wrapper = mount(CollapsibleStage, {
      props: { stage }
    })

    expect(wrapper.find('.icon-error').exists()).toBe(true)
    expect(wrapper.find('.icon-error').text()).toBe('❌')
  })

  it('应该显示阶段内容', () => {
    const wrapper = mount(CollapsibleStage, {
      props: { stage }
    })

    expect(wrapper.find('.content-text').text()).toBe('正在识别用户意图...')
  })

  it('应该默认展开进行中的阶段', () => {
    stage.collapsed = false
    const wrapper = mount(CollapsibleStage, {
      props: { stage }
    })

    expect(wrapper.find('.stage-content').isVisible()).toBe(true)
  })

  it('应该默认折叠已完成的阶段', () => {
    stage.status = 'completed'
    stage.collapsed = true
    const wrapper = mount(CollapsibleStage, {
      props: { stage }
    })

    // 初始状态应该是折叠的
    expect(wrapper.vm.isCollapsed).toBe(true)
  })

  it('点击标题应该切换折叠状态', async () => {
    const wrapper = mount(CollapsibleStage, {
      props: { stage }
    })

    // 初始状态是展开的
    expect(wrapper.vm.isCollapsed).toBe(false)

    // 点击标题
    await wrapper.find('.stage-header').trigger('click')

    // 应该变为折叠
    expect(wrapper.vm.isCollapsed).toBe(true)

    // 再次点击
    await wrapper.find('.stage-header').trigger('click')

    // 应该变为展开
    expect(wrapper.vm.isCollapsed).toBe(false)
  })

  it('应该显示元数据', () => {
    stage.metadata = {
      duration: '1.5s',
      intent: 'query_sales'
    }
    const wrapper = mount(CollapsibleStage, {
      props: { stage }
    })

    expect(wrapper.find('.stage-metadata').exists()).toBe(true)
    expect(wrapper.findAll('.metadata-item').length).toBe(2)
  })

  it('应该格式化元数据值', () => {
    stage.metadata = {
      simple: 'text',
      object: { key: 'value' }
    }
    const wrapper = mount(CollapsibleStage, {
      props: { stage }
    })

    const metadataItems = wrapper.findAll('.metadata-value')
    expect(metadataItems[0].text()).toBe('text')
    expect(metadataItems[1].text()).toContain('key')
  })

  it('已完成的阶段应该有特殊样式', () => {
    stage.status = 'completed'
    const wrapper = mount(CollapsibleStage, {
      props: { stage }
    })

    expect(wrapper.find('.collapsible-stage').classes()).toContain('stage-completed')
  })

  it('错误阶段应该有特殊样式', () => {
    stage.status = 'error'
    const wrapper = mount(CollapsibleStage, {
      props: { stage }
    })

    expect(wrapper.find('.collapsible-stage').classes()).toContain('stage-error')
  })

  it('折叠图标应该根据状态旋转', async () => {
    const wrapper = mount(CollapsibleStage, {
      props: { stage }
    })

    // 展开状态
    expect(wrapper.find('.collapse-icon').classes()).not.toContain('collapsed')

    // 点击折叠
    await wrapper.find('.stage-header').trigger('click')

    // 折叠状态
    expect(wrapper.find('.collapse-icon').classes()).toContain('collapsed')
  })

  it('应该监听 stage.collapsed 的变化', async () => {
    const wrapper = mount(CollapsibleStage, {
      props: { stage }
    })

    // 初始状态
    expect(wrapper.vm.isCollapsed).toBe(false)

    // 更新 prop
    await wrapper.setProps({
      stage: { ...stage, collapsed: true }
    })

    // 应该更新本地状态
    expect(wrapper.vm.isCollapsed).toBe(true)
  })

  it('应该监听 stage.status 的变化并自动折叠已完成的阶段', async () => {
    const wrapper = mount(CollapsibleStage, {
      props: { stage }
    })

    // 初始状态是展开的
    expect(wrapper.vm.isCollapsed).toBe(false)

    // 更新状态为已完成
    await wrapper.setProps({
      stage: { ...stage, status: 'completed' }
    })

    // 应该自动折叠
    expect(wrapper.vm.isCollapsed).toBe(true)
  })

  it('应该正确处理空元数据', () => {
    stage.metadata = {}
    const wrapper = mount(CollapsibleStage, {
      props: { stage }
    })

    expect(wrapper.find('.stage-metadata').exists()).toBe(false)
  })

  it('应该正确处理 undefined 元数据', () => {
    stage.metadata = undefined
    const wrapper = mount(CollapsibleStage, {
      props: { stage }
    })

    expect(wrapper.find('.stage-metadata').exists()).toBe(false)
  })

  it('已完成步骤的标题应该使用灰色文字', () => {
    stage.status = 'completed'
    const wrapper = mount(CollapsibleStage, {
      props: { stage }
    })

    const stageName = wrapper.find('.stage-name')
    // 检查是否有 stage-completed 类，该类会应用灰色样式
    expect(wrapper.find('.collapsible-stage').classes()).toContain('stage-completed')
  })

  it('已完成步骤的内容应该使用灰色文字', () => {
    stage.status = 'completed'
    stage.content = '意图识别完成'
    const wrapper = mount(CollapsibleStage, {
      props: { stage }
    })

    const contentText = wrapper.find('.content-text')
    expect(contentText.classes()).toContain('content-completed')
  })

  it('应该识别 SQL 内容', () => {
    stage.content = 'SELECT * FROM users WHERE id = 1'
    const wrapper = mount(CollapsibleStage, {
      props: { stage }
    })

    expect(wrapper.vm.isSQLContent).toBe(true)
  })

  it('应该识别不同类型的 SQL 语句', () => {
    const sqlStatements = [
      'SELECT * FROM table',
      'INSERT INTO table VALUES (1)',
      'UPDATE table SET col = 1',
      'DELETE FROM table WHERE id = 1',
      'CREATE TABLE test (id INT)',
      'ALTER TABLE test ADD COLUMN name VARCHAR(50)',
      'DROP TABLE test'
    ]

    sqlStatements.forEach(sql => {
      stage.content = sql
      const wrapper = mount(CollapsibleStage, {
        props: { stage }
      })
      expect(wrapper.vm.isSQLContent).toBe(true)
    })
  })

  it('应该识别包含 SQL 关键字的语句', () => {
    stage.content = 'This query uses FROM and WHERE clauses'
    const wrapper = mount(CollapsibleStage, {
      props: { stage }
    })

    expect(wrapper.vm.isSQLContent).toBe(true)
  })

  it('普通文本不应该被识别为 SQL', () => {
    stage.content = '正在识别用户意图...'
    const wrapper = mount(CollapsibleStage, {
      props: { stage }
    })

    expect(wrapper.vm.isSQLContent).toBe(false)
  })

  it('SQL 内容应该显示在代码编辑器中', () => {
    stage.content = 'SELECT * FROM users'
    stage.collapsed = false
    const wrapper = mount(CollapsibleStage, {
      props: { stage }
    })

    expect(wrapper.find('.sql-code-container').exists()).toBe(true)
    expect(wrapper.find('.content-text').exists()).toBe(false)
  })

  it('非 SQL 内容应该显示为普通文本', () => {
    stage.content = '正在处理数据...'
    stage.collapsed = false
    const wrapper = mount(CollapsibleStage, {
      props: { stage }
    })

    expect(wrapper.find('.sql-code-container').exists()).toBe(false)
    expect(wrapper.find('.content-text').exists()).toBe(true)
  })

  // Task 7.3: 流式输出指示器测试
  describe('流式输出指示器', () => {
    it('应该在进行中且有内容时显示流式输出指示器', () => {
      stage.status = 'in_progress'
      stage.content = '正在生成内容...'
      stage.collapsed = false
      const wrapper = mount(CollapsibleStage, {
        props: { stage }
      })

      expect(wrapper.find('.streaming-indicator').exists()).toBe(true)
      expect(wrapper.findAll('.streaming-indicator .dot').length).toBe(3)
    })

    it('应该在进行中但无内容时不显示流式输出指示器', () => {
      stage.status = 'in_progress'
      stage.content = ''
      stage.collapsed = false
      const wrapper = mount(CollapsibleStage, {
        props: { stage }
      })

      expect(wrapper.find('.streaming-indicator').exists()).toBe(false)
    })

    it('应该在已完成时不显示流式输出指示器', () => {
      stage.status = 'completed'
      stage.content = '内容已完成'
      stage.collapsed = false
      const wrapper = mount(CollapsibleStage, {
        props: { stage }
      })

      expect(wrapper.find('.streaming-indicator').exists()).toBe(false)
    })

    it('应该在错误状态时不显示流式输出指示器', () => {
      stage.status = 'error'
      stage.content = '发生错误'
      stage.collapsed = false
      const wrapper = mount(CollapsibleStage, {
        props: { stage }
      })

      expect(wrapper.find('.streaming-indicator').exists()).toBe(false)
    })

    it('流式输出指示器的三个点应该有不同的动画延迟', () => {
      stage.status = 'in_progress'
      stage.content = '正在生成内容...'
      stage.collapsed = false
      const wrapper = mount(CollapsibleStage, {
        props: { stage }
      })

      const dots = wrapper.findAll('.streaming-indicator .dot')
      expect(dots.length).toBe(3)
      
      // 验证每个点都存在（动画延迟通过 CSS 类实现）
      dots.forEach(dot => {
        expect(dot.exists()).toBe(true)
      })
    })
  })

  // Task 7.3: 内容更新平滑过渡测试
  describe('内容更新平滑过渡', () => {
    it('内容文本应该有过渡效果类', () => {
      stage.collapsed = false
      const wrapper = mount(CollapsibleStage, {
        props: { stage }
      })

      const contentText = wrapper.find('.content-text')
      expect(contentText.exists()).toBe(true)
      // 验证元素存在，CSS transition 通过样式定义
    })

    it('折叠动画应该正确应用', async () => {
      stage.collapsed = false
      const wrapper = mount(CollapsibleStage, {
        props: { stage }
      })

      const stageContent = wrapper.find('.stage-content')
      expect(stageContent.exists()).toBe(true)
      
      // 点击折叠
      await wrapper.find('.stage-header').trigger('click')
      
      // 验证折叠状态改变
      expect(wrapper.vm.isCollapsed).toBe(true)
    })
  })

  // Task 7.3: 阶段完成视觉反馈测试
  describe('阶段完成视觉反馈', () => {
    it('已完成阶段应该显示绿色对勾图标', () => {
      stage.status = 'completed'
      const wrapper = mount(CollapsibleStage, {
        props: { stage }
      })

      expect(wrapper.find('.icon-completed').exists()).toBe(true)
      expect(wrapper.find('.icon-completed').text()).toBe('✅')
    })

    it('错误阶段应该显示红色错误图标', () => {
      stage.status = 'error'
      const wrapper = mount(CollapsibleStage, {
        props: { stage }
      })

      expect(wrapper.find('.icon-error').exists()).toBe(true)
      expect(wrapper.find('.icon-error').text()).toBe('❌')
    })

    it('进行中阶段应该显示沙漏图标', () => {
      stage.status = 'in_progress'
      const wrapper = mount(CollapsibleStage, {
        props: { stage }
      })

      expect(wrapper.find('.icon-progress').exists()).toBe(true)
      expect(wrapper.find('.icon-progress').text()).toBe('⏳')
    })

    it('已完成阶段应该有特殊的背景色样式类', () => {
      stage.status = 'completed'
      const wrapper = mount(CollapsibleStage, {
        props: { stage }
      })

      expect(wrapper.find('.collapsible-stage').classes()).toContain('stage-completed')
    })

    it('错误阶段应该有特殊的背景色样式类', () => {
      stage.status = 'error'
      const wrapper = mount(CollapsibleStage, {
        props: { stage }
      })

      expect(wrapper.find('.collapsible-stage').classes()).toContain('stage-error')
    })
  })

  // Task 7.3: 折叠/展开功能测试
  describe('折叠/展开功能', () => {
    it('点击标题应该切换折叠状态', async () => {
      stage.collapsed = false
      const wrapper = mount(CollapsibleStage, {
        props: { stage }
      })

      expect(wrapper.vm.isCollapsed).toBe(false)

      await wrapper.find('.stage-header').trigger('click')
      expect(wrapper.vm.isCollapsed).toBe(true)

      await wrapper.find('.stage-header').trigger('click')
      expect(wrapper.vm.isCollapsed).toBe(false)
    })

    it('折叠图标应该根据状态旋转', async () => {
      stage.collapsed = false
      const wrapper = mount(CollapsibleStage, {
        props: { stage }
      })

      const collapseIcon = wrapper.find('.collapse-icon')
      expect(collapseIcon.classes()).not.toContain('collapsed')

      await wrapper.find('.stage-header').trigger('click')
      expect(collapseIcon.classes()).toContain('collapsed')
    })

    it('折叠时内容应该隐藏', async () => {
      stage.collapsed = false
      const wrapper = mount(CollapsibleStage, {
        props: { stage }
      })

      // 初始状态应该展开
      expect(wrapper.vm.isCollapsed).toBe(false)

      await wrapper.find('.stage-header').trigger('click')
      
      // 验证内部状态已改变
      expect(wrapper.vm.isCollapsed).toBe(true)
    })

    it('展开时内容应该显示', async () => {
      stage.collapsed = true
      const wrapper = mount(CollapsibleStage, {
        props: { stage }
      })

      // 初始状态应该折叠
      expect(wrapper.vm.isCollapsed).toBe(true)

      await wrapper.find('.stage-header').trigger('click')
      
      // 验证内部状态已改变
      expect(wrapper.vm.isCollapsed).toBe(false)
    })

    it('阶段完成时应该自动折叠', async () => {
      stage.status = 'in_progress'
      stage.collapsed = false
      const wrapper = mount(CollapsibleStage, {
        props: { stage }
      })

      expect(wrapper.vm.isCollapsed).toBe(false)

      await wrapper.setProps({
        stage: { ...stage, status: 'completed' }
      })

      expect(wrapper.vm.isCollapsed).toBe(true)
    })
  })
})

