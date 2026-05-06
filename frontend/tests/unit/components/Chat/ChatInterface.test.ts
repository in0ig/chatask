/**
 * ChatInterface 组件测试
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { ElButton, ElInput, ElAvatar, ElAlert, ElIcon } from 'element-plus'
import ChatInterface from '@/components/Chat/ChatInterface.vue'
import MessageContent from '@/components/Chat/MessageContent.vue'
import { useChatStore } from '@/store/modules/chat'

// Mock WebSocket 服务
vi.mock('@/services/websocketService', () => ({
  websocketService: {
    connect: vi.fn().mockResolvedValue(undefined),
    disconnect: vi.fn(),
    send: vi.fn(),
    onMessage: vi.fn(() => vi.fn()),
    onConnection: vi.fn(() => vi.fn()),
    onError: vi.fn(() => vi.fn()),
    isConnected: vi.fn(() => true)
  }
}))

describe('ChatInterface', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('should render correctly', () => {
    const wrapper = mount(ChatInterface, {
      global: {
        components: {
          ElButton,
          ElInput,
          ElAvatar,
          ElAlert,
          ElIcon,
          MessageContent
        },
        stubs: {
          ElIcon: true,
          Loading: true
        }
      }
    })

    expect(wrapper.find('.chat-interface').exists()).toBe(true)
    expect(wrapper.find('.message-list').exists()).toBe(true)
    expect(wrapper.find('.input-area').exists()).toBe(true)
  })

  it('should display messages', async () => {
    const store = useChatStore()
    store.createSession()
    store.addMessage({
      role: 'user',
      type: 'text',
      content: 'Hello',
      status: 'sent'
    })

    const wrapper = mount(ChatInterface, {
      global: {
        components: {
          ElButton,
          ElInput,
          ElAvatar,
          ElAlert,
          ElIcon,
          MessageContent
        },
        stubs: {
          ElIcon: true,
          Loading: true,
          MessageContent: true
        }
      }
    })

    await wrapper.vm.$nextTick()

    expect(wrapper.findAll('.message-item')).toHaveLength(1)
  })

  it('should handle send message', async () => {
    const wrapper = mount(ChatInterface, {
      global: {
        components: {
          ElButton,
          ElInput,
          ElAvatar,
          ElAlert,
          ElIcon,
          MessageContent
        },
        stubs: {
          ElIcon: true,
          Loading: true,
          MessageContent: true
        }
      }
    })

    const store = useChatStore()
    const initialMessageCount = store.currentMessages.length

    // 设置输入文本
    const textarea = wrapper.find('textarea')
    await textarea.setValue('Test message')

    // 点击发送按钮
    const sendButton = wrapper.findAll('button').find(btn => 
      btn.text().includes('发送')
    )
    await sendButton?.trigger('click')

    await wrapper.vm.$nextTick()

    // 验证消息已添加
    expect(store.currentMessages.length).toBe(initialMessageCount + 1)
    expect(store.currentMessages[store.currentMessages.length - 1].content).toBe('Test message')
  })

  it('should disable send button when input is empty', async () => {
    const wrapper = mount(ChatInterface, {
      global: {
        components: {
          ElButton,
          ElInput,
          ElAvatar,
          ElAlert,
          ElIcon,
          MessageContent
        },
        stubs: {
          ElIcon: true,
          Loading: true,
          MessageContent: true
        }
      }
    })

    const sendButton = wrapper.findAll('button').find(btn => 
      btn.text().includes('发送')
    )

    expect(sendButton?.attributes('disabled')).toBeDefined()
  })

  it('should disable send button when streaming', async () => {
    const store = useChatStore()
    store.setStreaming(true)

    const wrapper = mount(ChatInterface, {
      global: {
        components: {
          ElButton,
          ElInput,
          ElAvatar,
          ElAlert,
          ElIcon,
          MessageContent
        },
        stubs: {
          ElIcon: true,
          Loading: true,
          MessageContent: true
        }
      }
    })

    const textarea = wrapper.find('textarea')
    await textarea.setValue('Test message')

    const sendButton = wrapper.findAll('button').find(btn => 
      btn.text().includes('发送')
    )

    expect(sendButton?.attributes('disabled')).toBeDefined()
  })

  it('should show streaming indicator when streaming', async () => {
    const store = useChatStore()
    store.setStreaming(true)

    const wrapper = mount(ChatInterface, {
      global: {
        components: {
          ElButton,
          ElInput,
          ElAvatar,
          ElAlert,
          ElIcon,
          MessageContent
        },
        stubs: {
          ElIcon: true,
          Loading: true,
          MessageContent: true
        }
      }
    })

    await wrapper.vm.$nextTick()

    expect(wrapper.find('.streaming-indicator').exists()).toBe(true)
  })

  it('should handle clear conversation', async () => {
    const store = useChatStore()
    store.createSession()
    store.addMessage({
      role: 'user',
      type: 'text',
      content: 'Hello',
      status: 'sent'
    })

    const wrapper = mount(ChatInterface, {
      global: {
        components: {
          ElButton,
          ElInput,
          ElAvatar,
          ElAlert,
          ElIcon,
          MessageContent
        },
        stubs: {
          ElIcon: true,
          Loading: true,
          MessageContent: true
        }
      }
    })

    expect(store.currentMessages.length).toBeGreaterThan(0)

    // 点击清空按钮
    const clearButton = wrapper.findAll('button').find(btn => 
      btn.text().includes('清空')
    )
    await clearButton?.trigger('click')

    await wrapper.vm.$nextTick()

    expect(store.currentMessages.length).toBe(0)
  })
})
