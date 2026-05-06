/**
 * MessageContent 组件测试
 */
import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import { ElTable, ElTableColumn, ElAlert } from 'element-plus'
import MessageContent from '@/components/Chat/MessageContent.vue'
import type { ChatMessage } from '@/types/chat'

describe('MessageContent', () => {
  it('should render text message', () => {
    const message: ChatMessage = {
      id: 'msg_1',
      role: 'user',
      type: 'text',
      content: 'Hello World',
      status: 'sent',
      timestamp: Date.now()
    }

    const wrapper = mount(MessageContent, {
      props: { message },
      global: {
        components: {
          ElTable,
          ElTableColumn,
          ElAlert
        }
      }
    })

    expect(wrapper.find('.text-content').exists()).toBe(true)
    expect(wrapper.find('.text-content').text()).toBe('Hello World')
  })

  it('should render thinking message', () => {
    const message: ChatMessage = {
      id: 'msg_1',
      role: 'assistant',
      type: 'thinking',
      content: 'Thinking...',
      status: 'streaming',
      timestamp: Date.now()
    }

    const wrapper = mount(MessageContent, {
      props: { message },
      global: {
        components: {
          ElTable,
          ElTableColumn,
          ElAlert
        }
      }
    })

    expect(wrapper.find('.text-content').exists()).toBe(true)
    expect(wrapper.find('.text-content').text()).toBe('Thinking...')
  })

  it('should render SQL message', () => {
    const message: ChatMessage = {
      id: 'msg_1',
      role: 'assistant',
      type: 'sql',
      content: 'SELECT * FROM users',
      status: 'completed',
      timestamp: Date.now()
    }

    const wrapper = mount(MessageContent, {
      props: { message },
      global: {
        components: {
          ElTable,
          ElTableColumn,
          ElAlert
        }
      }
    })

    expect(wrapper.find('.sql-content').exists()).toBe(true)
    expect(wrapper.find('code').text()).toBe('SELECT * FROM users')
  })

  it('should render table message', () => {
    const message: ChatMessage = {
      id: 'msg_1',
      role: 'assistant',
      type: 'table',
      content: '',
      status: 'completed',
      timestamp: Date.now(),
      metadata: {
        columns: ['id', 'name'],
        data: [
          { id: 1, name: 'Alice' },
          { id: 2, name: 'Bob' }
        ]
      }
    }

    const wrapper = mount(MessageContent, {
      props: { message },
      global: {
        components: {
          ElTable,
          ElTableColumn,
          ElAlert
        },
        stubs: {
          ElTable: true,
          ElTableColumn: true
        }
      }
    })

    expect(wrapper.find('.table-content').exists()).toBe(true)
  })

  it('should render error message', () => {
    const message: ChatMessage = {
      id: 'msg_1',
      role: 'system',
      type: 'error',
      content: 'An error occurred',
      status: 'error',
      timestamp: Date.now()
    }

    const wrapper = mount(MessageContent, {
      props: { message },
      global: {
        components: {
          ElTable,
          ElTableColumn,
          ElAlert
        },
        stubs: {
          ElAlert: true
        }
      }
    })

    expect(wrapper.find('.error-content').exists()).toBe(true)
  })
})
