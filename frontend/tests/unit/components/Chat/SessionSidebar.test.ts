import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import SessionSidebar from '@/components/Chat/SessionSidebar.vue'
import { useChatStore } from '@/store/modules/chat'
import axios from 'axios'

// Mock axios
vi.mock('axios')

// Mock ElMessage and ElMessageBox
vi.mock('element-plus', () => ({
  ElMessage: {
    success: vi.fn(),
    error: vi.fn(),
    warning: vi.fn()
  },
  ElMessageBox: {
    confirm: vi.fn()
  }
}))

describe('SessionSidebar', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  describe('基础渲染', () => {
    it('应该正确渲染侧边栏', () => {
      const wrapper = mount(SessionSidebar)
      expect(wrapper.find('.session-sidebar').exists()).toBe(true)
      expect(wrapper.find('.sidebar-header').exists()).toBe(true)
    })

    it('应该显示标题', () => {
      const wrapper = mount(SessionSidebar)
      expect(wrapper.find('.sidebar-header h3').text()).toBe('对话历史')
    })

    it('应该有新建会话按钮', () => {
      const wrapper = mount(SessionSidebar)
      expect(wrapper.find('.new-session-btn').exists()).toBe(true)
      expect(wrapper.find('.new-session-btn span').text()).toBe('新建对话')
    })

    it('应该有折叠/展开按钮', () => {
      const wrapper = mount(SessionSidebar)
      expect(wrapper.find('.toggle-btn').exists()).toBe(true)
    })
  })

  describe('折叠功能', () => {
    it('应该支持折叠侧边栏', async () => {
      const wrapper = mount(SessionSidebar)
      const toggleBtn = wrapper.find('.toggle-btn')
      
      await toggleBtn.trigger('click')
      expect(wrapper.find('.session-sidebar').classes()).toContain('collapsed')
    })

    it('折叠时应该隐藏内容', async () => {
      const wrapper = mount(SessionSidebar, {
        props: { collapsed: true }
      })
      
      expect(wrapper.find('.session-sidebar').classes()).toContain('collapsed')
    })

    it('应该触发toggle事件', async () => {
      const wrapper = mount(SessionSidebar)
      const toggleBtn = wrapper.find('.toggle-btn')
      
      await toggleBtn.trigger('click')
      expect(wrapper.emitted('toggle')).toBeTruthy()
      expect(wrapper.emitted('toggle')?.[0]).toEqual([true])
    })
  })

  describe('新建会话', () => {
    it('点击新建按钮应该创建会话', async () => {
      const wrapper = mount(SessionSidebar)
      const chatStore = useChatStore()
      
      const newSessionBtn = wrapper.find('.new-session-btn')
      await newSessionBtn.trigger('click')
      
      expect(chatStore.currentSessionId).toBeTruthy()
      expect(wrapper.emitted('session-created')).toBeTruthy()
    })
  })

  describe('会话列表', () => {
    it('应该显示会话列表', async () => {
      // Mock axios response
      vi.mocked(axios.get).mockResolvedValue({
        data: {
          success: true,
          data: {
            sessions: [
              {
                session_id: 'session1',
                title: '测试会话1',
                message_count: 5,
                last_activity_at: new Date().toISOString()
              }
            ]
          }
        }
      })

      const wrapper = mount(SessionSidebar)
      await wrapper.vm.$nextTick()
      await new Promise(resolve => setTimeout(resolve, 100))
      
      expect(axios.get).toHaveBeenCalledWith(
        'http://localhost:8000/api/sessions/',
        expect.objectContaining({
          params: { limit: 50, offset: 0 }
        })
      )
    })

    it('空列表时应该显示空状态', () => {
      const wrapper = mount(SessionSidebar)
      expect(wrapper.find('.empty-state').exists()).toBe(true)
      expect(wrapper.find('.empty-state p').text()).toContain('暂无对话历史')
    })
  })

  describe('时间格式化', () => {
    it('应该正确格式化时间', () => {
      const wrapper = mount(SessionSidebar)
      const vm = wrapper.vm as any
      
      // 刚刚
      const now = new Date()
      expect(vm.formatTime(now.toISOString())).toBe('刚刚')
      
      // 几分钟前
      const minutesAgo = new Date(now.getTime() - 5 * 60 * 1000)
      expect(vm.formatTime(minutesAgo.toISOString())).toContain('分钟前')
      
      // 几小时前
      const hoursAgo = new Date(now.getTime() - 2 * 60 * 60 * 1000)
      expect(vm.formatTime(hoursAgo.toISOString())).toContain('小时前')
      
      // 几天前
      const daysAgo = new Date(now.getTime() - 2 * 24 * 60 * 60 * 1000)
      expect(vm.formatTime(daysAgo.toISOString())).toContain('天前')
    })
  })
})
