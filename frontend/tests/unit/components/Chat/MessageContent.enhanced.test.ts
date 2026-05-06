/**
 * MessageContent 增强功能测试
 * 测试消息类型渲染、操作工具栏、编辑、导出、分享等功能
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { ElButton, ElInput, ElTable, ElAlert, ElDialog } from 'element-plus'
import MessageContent from '@/components/Chat/MessageContent.vue'
import type { ChatMessage } from '@/types/chat'

describe('MessageContent Enhanced Features', () => {
  // 测试1: 文本消息渲染
  describe('Text Message Rendering', () => {
    it('should render plain text message', () => {
      const message: ChatMessage = {
        id: 'msg1',
        role: 'user',
        type: 'text',
        content: 'Hello World',
        status: 'sent',
        timestamp: Date.now()
      }

      const wrapper = mount(MessageContent, {
        props: { message },
        global: {
          components: { ElButton, ElInput }
        }
      })

      expect(wrapper.find('.text-content').exists()).toBe(true)
      expect(wrapper.text()).toContain('Hello World')
    })

    it('should render formatted text with markdown-like syntax', () => {
      const message: ChatMessage = {
        id: 'msg2',
        role: 'assistant',
        type: 'text',
        content: '**Bold** and `code`',
        status: 'completed',
        timestamp: Date.now()
      }

      const wrapper = mount(MessageContent, {
        props: { message },
        global: {
          components: { ElButton, ElInput }
        }
      })

      const html = wrapper.find('.text-content').html()
      expect(html).toContain('<strong>Bold</strong>')
      expect(html).toContain('<code>code</code>')
    })
  })

  // 测试2: SQL消息渲染和语法高亮
  describe('SQL Message Rendering', () => {
    it('should render SQL message with syntax highlighting', () => {
      const message: ChatMessage = {
        id: 'msg3',
        role: 'assistant',
        type: 'sql',
        content: 'SELECT * FROM users WHERE id = 1',
        status: 'completed',
        timestamp: Date.now()
      }

      const wrapper = mount(MessageContent, {
        props: { message },
        global: {
          components: { ElButton }
        }
      })

      expect(wrapper.find('.sql-content').exists()).toBe(true)
      expect(wrapper.find('.sql-header').exists()).toBe(true)
      expect(wrapper.find('pre code').exists()).toBe(true)
      
      const sqlHtml = wrapper.find('pre code').html()
      expect(sqlHtml).toContain('SELECT')
      expect(sqlHtml).toContain('FROM')
      expect(sqlHtml).toContain('WHERE')
    })

    it('should have copy SQL button', async () => {
      const message: ChatMessage = {
        id: 'msg4',
        role: 'assistant',
        type: 'sql',
        content: 'SELECT 1',
        status: 'completed',
        timestamp: Date.now()
      }

      // Mock clipboard API
      Object.assign(navigator, {
        clipboard: {
          writeText: vi.fn().mockResolvedValue(undefined)
        }
      })

      const wrapper = mount(MessageContent, {
        props: { message },
        global: {
          components: { ElButton }
        }
      })

      const copyButton = wrapper.findAll('.el-button').find(btn => 
        btn.text().includes('复制')
      )
      expect(copyButton).toBeDefined()
    })
  })

  // 测试3: 表格消息渲染
  describe('Table Message Rendering', () => {
    it('should render table with data and columns', () => {
      const message: ChatMessage = {
        id: 'msg5',
        role: 'assistant',
        type: 'table',
        content: '',
        status: 'completed',
        timestamp: Date.now(),
        metadata: {
          columns: ['id', 'name', 'age'],
          data: [
            { id: 1, name: 'Alice', age: 25 },
            { id: 2, name: 'Bob', age: 30 }
          ]
        }
      }

      const wrapper = mount(MessageContent, {
        props: { message },
        global: {
          components: { ElButton, ElTable }
        }
      })

      expect(wrapper.find('.table-content').exists()).toBe(true)
      expect(wrapper.find('.table-header').exists()).toBe(true)
      expect(wrapper.text()).toContain('共 2 行数据')
    })

    it('should have export buttons for CSV and Excel', () => {
      const message: ChatMessage = {
        id: 'msg6',
        role: 'assistant',
        type: 'table',
        content: '',
        status: 'completed',
        timestamp: Date.now(),
        metadata: {
          columns: ['id'],
          data: [{ id: 1 }]
        }
      }

      const wrapper = mount(MessageContent, {
        props: { message },
        global: {
          components: { ElButton, ElTable }
        }
      })

      const buttons = wrapper.findAll('.el-button')
      const exportButtons = buttons.filter(btn => 
        btn.text().includes('导出CSV') || btn.text().includes('导出Excel')
      )
      expect(exportButtons.length).toBeGreaterThanOrEqual(2)
    })
  })

  // 测试4: 图表消息渲染（占位符）
  describe('Chart Message Rendering', () => {
    it('should render chart placeholder', () => {
      const message: ChatMessage = {
        id: 'msg7',
        role: 'assistant',
        type: 'chart',
        content: '',
        status: 'completed',
        timestamp: Date.now()
      }

      const wrapper = mount(MessageContent, {
        props: { message }
      })

      expect(wrapper.find('.chart-content').exists()).toBe(true)
      expect(wrapper.find('.chart-placeholder').exists()).toBe(true)
      expect(wrapper.text()).toContain('Task 6.2')
    })
  })

  // 测试5: 错误消息渲染
  describe('Error Message Rendering', () => {
    it('should render error message with alert', () => {
      const message: ChatMessage = {
        id: 'msg8',
        role: 'system',
        type: 'error',
        content: 'Database connection failed',
        status: 'error',
        timestamp: Date.now()
      }

      const wrapper = mount(MessageContent, {
        props: { message },
        global: {
          components: { ElAlert }
        }
      })

      expect(wrapper.find('.error-content').exists()).toBe(true)
      expect(wrapper.text()).toContain('Database connection failed')
    })

    it('should render error details if provided', () => {
      const message: ChatMessage = {
        id: 'msg9',
        role: 'system',
        type: 'error',
        content: 'Query failed',
        status: 'error',
        timestamp: Date.now(),
        metadata: {
          details: 'Connection timeout after 30s'
        }
      }

      const wrapper = mount(MessageContent, {
        props: { message },
        global: {
          components: { ElAlert }
        }
      })

      expect(wrapper.text()).toContain('Connection timeout')
    })
  })

  // 测试6: 消息操作工具栏
  describe('Message Action Toolbar', () => {
    it('should show action toolbar when showActions is true', () => {
      const message: ChatMessage = {
        id: 'msg10',
        role: 'user',
        type: 'text',
        content: 'Test',
        status: 'sent',
        timestamp: Date.now()
      }

      const wrapper = mount(MessageContent, {
        props: { 
          message,
          showActions: true
        },
        global: {
          components: { ElButton }
        }
      })

      expect(wrapper.find('.message-actions').exists()).toBe(true)
    })

    it('should hide action toolbar when showActions is false', () => {
      const message: ChatMessage = {
        id: 'msg11',
        role: 'user',
        type: 'text',
        content: 'Test',
        status: 'sent',
        timestamp: Date.now()
      }

      const wrapper = mount(MessageContent, {
        props: { 
          message,
          showActions: false
        },
        global: {
          components: { ElButton }
        }
      })

      expect(wrapper.find('.message-actions').exists()).toBe(false)
    })

    it('should show edit button when canEdit is true', () => {
      const message: ChatMessage = {
        id: 'msg12',
        role: 'user',
        type: 'text',
        content: 'Test',
        status: 'sent',
        timestamp: Date.now()
      }

      const wrapper = mount(MessageContent, {
        props: { 
          message,
          showActions: true,
          canEdit: true
        },
        global: {
          components: { ElButton }
        }
      })

      const buttons = wrapper.findAll('.el-button')
      expect(buttons.length).toBeGreaterThan(0)
    })
  })

  // 测试7: 编辑消息功能
  describe('Edit Message Functionality', () => {
    it('should enter edit mode when edit button clicked', async () => {
      const message: ChatMessage = {
        id: 'msg13',
        role: 'user',
        type: 'text',
        content: 'Original content',
        status: 'sent',
        timestamp: Date.now()
      }

      const wrapper = mount(MessageContent, {
        props: { 
          message,
          showActions: true,
          canEdit: true
        },
        global: {
          components: { ElButton, ElInput }
        }
      })

      // 触发编辑
      await wrapper.vm.handleEdit()
      await wrapper.vm.$nextTick()

      expect(wrapper.vm.isEditing).toBe(true)
      expect(wrapper.vm.editContent).toBe('Original content')
    })

    it('should emit edit event when save button clicked', async () => {
      const message: ChatMessage = {
        id: 'msg14',
        role: 'user',
        type: 'text',
        content: 'Original',
        status: 'sent',
        timestamp: Date.now()
      }

      const wrapper = mount(MessageContent, {
        props: { 
          message,
          showActions: true,
          canEdit: true
        },
        global: {
          components: { ElButton, ElInput }
        }
      })

      // 进入编辑模式
      await wrapper.vm.handleEdit()
      wrapper.vm.editContent = 'Updated content'
      
      // 保存编辑
      await wrapper.vm.saveEdit()

      expect(wrapper.emitted('edit')).toBeTruthy()
      expect(wrapper.emitted('edit')?.[0]).toEqual(['Updated content'])
      expect(wrapper.vm.isEditing).toBe(false)
    })

    it('should cancel edit mode without emitting event', async () => {
      const message: ChatMessage = {
        id: 'msg15',
        role: 'user',
        type: 'text',
        content: 'Original',
        status: 'sent',
        timestamp: Date.now()
      }

      const wrapper = mount(MessageContent, {
        props: { 
          message,
          showActions: true,
          canEdit: true
        },
        global: {
          components: { ElButton, ElInput }
        }
      })

      // 进入编辑模式并修改
      await wrapper.vm.handleEdit()
      wrapper.vm.editContent = 'Changed'
      
      // 取消编辑
      await wrapper.vm.cancelEdit()

      expect(wrapper.emitted('edit')).toBeFalsy()
      expect(wrapper.vm.isEditing).toBe(false)
      expect(wrapper.vm.editContent).toBe('')
    })
  })

  // 测试8: 重发消息功能
  describe('Resend Message Functionality', () => {
    it('should emit resend event when resend button clicked', async () => {
      const message: ChatMessage = {
        id: 'msg16',
        role: 'user',
        type: 'text',
        content: 'Test',
        status: 'error',
        timestamp: Date.now()
      }

      const wrapper = mount(MessageContent, {
        props: { 
          message,
          showActions: true,
          canResend: true
        },
        global: {
          components: { ElButton }
        }
      })

      await wrapper.vm.handleResend()

      expect(wrapper.emitted('resend')).toBeTruthy()
    })
  })

  // 测试9: 回溯功能
  describe('Rollback Functionality', () => {
    it('should emit rollback event when rollback button clicked', async () => {
      const message: ChatMessage = {
        id: 'msg17',
        role: 'assistant',
        type: 'text',
        content: 'Response',
        status: 'completed',
        timestamp: Date.now()
      }

      const wrapper = mount(MessageContent, {
        props: { 
          message,
          showActions: true,
          canRollback: true
        },
        global: {
          components: { ElButton }
        }
      })

      await wrapper.vm.handleRollback()

      expect(wrapper.emitted('rollback')).toBeTruthy()
    })
  })

  // 测试10: 导出功能
  describe('Export Functionality', () => {
    it('should emit export event with format', async () => {
      const message: ChatMessage = {
        id: 'msg18',
        role: 'assistant',
        type: 'text',
        content: 'Content to export',
        status: 'completed',
        timestamp: Date.now()
      }

      const wrapper = mount(MessageContent, {
        props: { 
          message,
          showActions: true
        },
        global: {
          components: { ElButton }
        }
      })

      await wrapper.vm.handleExport()

      expect(wrapper.emitted('export')).toBeTruthy()
      expect(wrapper.emitted('export')?.[0]).toEqual(['text'])
    })

    it('should emit export event with excel format for table', async () => {
      const message: ChatMessage = {
        id: 'msg19',
        role: 'assistant',
        type: 'table',
        content: '',
        status: 'completed',
        timestamp: Date.now(),
        metadata: {
          columns: ['id'],
          data: [{ id: 1 }]
        }
      }

      const wrapper = mount(MessageContent, {
        props: { 
          message,
          showActions: true
        },
        global: {
          components: { ElButton, ElTable }
        }
      })

      await wrapper.vm.exportTable('excel')

      expect(wrapper.emitted('export')).toBeTruthy()
      expect(wrapper.emitted('export')?.[0]).toEqual(['excel'])
    })
  })

  // 测试11: 分享功能
  describe('Share Functionality', () => {
    it('should open share dialog when share button clicked', async () => {
      const message: ChatMessage = {
        id: 'msg20',
        role: 'assistant',
        type: 'text',
        content: 'Shareable content',
        status: 'completed',
        timestamp: Date.now()
      }

      const wrapper = mount(MessageContent, {
        props: { 
          message,
          showActions: true
        },
        global: {
          components: { ElButton, ElDialog }
        }
      })

      await wrapper.vm.handleShare()

      expect(wrapper.vm.shareDialogVisible).toBe(true)
      expect(wrapper.vm.shareLink).toContain(message.id)
    })

    it('should copy share link to clipboard', async () => {
      const message: ChatMessage = {
        id: 'msg21',
        role: 'assistant',
        type: 'text',
        content: 'Content',
        status: 'completed',
        timestamp: Date.now()
      }

      // Mock clipboard API
      Object.assign(navigator, {
        clipboard: {
          writeText: vi.fn().mockResolvedValue(undefined)
        }
      })

      const wrapper = mount(MessageContent, {
        props: { 
          message,
          showActions: true
        },
        global: {
          components: { ElButton, ElDialog }
        }
      })

      await wrapper.vm.handleShare()
      await wrapper.vm.copyShareLink()

      expect(navigator.clipboard.writeText).toHaveBeenCalled()
    })
  })

  // 测试12: 分阶段显示和动态更新
  describe('Staged Display and Dynamic Updates', () => {
    it('should handle streaming status', () => {
      const message: ChatMessage = {
        id: 'msg22',
        role: 'assistant',
        type: 'text',
        content: 'Streaming...',
        status: 'streaming',
        timestamp: Date.now()
      }

      const wrapper = mount(MessageContent, {
        props: { message },
        global: {
          components: { ElButton }
        }
      })

      expect(wrapper.find('.text-content').exists()).toBe(true)
    })

    it('should update content when message prop changes', async () => {
      const message: ChatMessage = {
        id: 'msg23',
        role: 'assistant',
        type: 'text',
        content: 'Initial',
        status: 'streaming',
        timestamp: Date.now()
      }

      const wrapper = mount(MessageContent, {
        props: { message },
        global: {
          components: { ElButton }
        }
      })

      expect(wrapper.text()).toContain('Initial')

      // 更新消息内容
      await wrapper.setProps({
        message: {
          ...message,
          content: 'Initial Updated',
          status: 'completed'
        }
      })

      expect(wrapper.text()).toContain('Updated')
    })
  })
})
