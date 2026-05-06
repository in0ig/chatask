import { describe, it, expect, beforeEach, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useChatStore } from '@/store/modules/chat'
import type { ChatMessage } from '@/types/chat'

describe('Home Component - Message Display Fix', () => {
  beforeEach(() => {
    // 为每个测试创建新的 Pinia 实例
    setActivePinia(createPinia())
  })

  describe('Chat Store - Message Management', () => {
    it('应该能够创建新会话', () => {
      const chatStore = useChatStore()
      
      expect(chatStore.currentSessionId).toBeNull()
      
      const sessionId = chatStore.createSession('测试会话')
      
      expect(chatStore.currentSessionId).toBe(sessionId)
      expect(chatStore.sessions[sessionId]).toBeDefined()
      expect(chatStore.sessions[sessionId].messages).toHaveLength(0)
    })

    it('应该能够添加消息到会话', () => {
      const chatStore = useChatStore()
      
      // 创建会话
      chatStore.createSession('测试会话')
      
      // 添加用户消息
      const messageId = chatStore.addMessage({
        role: 'user',
        type: 'text',
        content: '张三下了几单',
        status: 'sent'
      })
      
      expect(messageId).toBeDefined()
      expect(chatStore.currentMessages).toHaveLength(1)
      expect(chatStore.currentMessages[0].content).toBe('张三下了几单')
      expect(chatStore.currentMessages[0].role).toBe('user')
    })

    it('应该能够通过 currentMessages getter 获取消息', () => {
      const chatStore = useChatStore()
      
      // 创建会话
      chatStore.createSession('测试会话')
      
      // 添加消息
      chatStore.addMessage({
        role: 'user',
        type: 'text',
        content: '测试消息',
        status: 'sent'
      })
      
      // 通过 getter 获取消息
      const messages = chatStore.currentMessages
      
      expect(messages).toHaveLength(1)
      expect(messages[0].content).toBe('测试消息')
    })

    it('应该能够添加多条消息', () => {
      const chatStore = useChatStore()
      
      // 创建会话
      chatStore.createSession('测试会话')
      
      // 添加多条消息
      chatStore.addMessage({
        role: 'user',
        type: 'text',
        content: '第一条消息',
        status: 'sent'
      })
      
      chatStore.addMessage({
        role: 'assistant',
        type: 'text',
        content: 'AI 回复',
        status: 'completed'
      })
      
      chatStore.addMessage({
        role: 'user',
        type: 'text',
        content: '第二条消息',
        status: 'sent'
      })
      
      expect(chatStore.currentMessages).toHaveLength(3)
      expect(chatStore.currentMessages[0].content).toBe('第一条消息')
      expect(chatStore.currentMessages[1].content).toBe('AI 回复')
      expect(chatStore.currentMessages[2].content).toBe('第二条消息')
    })

    it('应该能够更新消息', () => {
      const chatStore = useChatStore()
      
      // 创建会话
      chatStore.createSession('测试会话')
      
      // 添加消息
      const messageId = chatStore.addMessage({
        role: 'user',
        type: 'text',
        content: '原始内容',
        status: 'sent'
      })
      
      // 更新消息
      chatStore.updateMessage(messageId, {
        content: '更新后的内容',
        status: 'completed'
      })
      
      expect(chatStore.currentMessages[0].content).toBe('更新后的内容')
      expect(chatStore.currentMessages[0].status).toBe('completed')
    })

    it('应该能够追加消息内容（流式输出）', () => {
      const chatStore = useChatStore()
      
      // 创建会话
      chatStore.createSession('测试会话')
      
      // 添加消息
      const messageId = chatStore.addMessage({
        role: 'assistant',
        type: 'text',
        content: '这是',
        status: 'streaming'
      })
      
      // 追加内容
      chatStore.appendMessageContent(messageId, '流式')
      chatStore.appendMessageContent(messageId, '输出')
      
      expect(chatStore.currentMessages[0].content).toBe('这是流式输出')
    })

    it('应该能够清空会话消息', () => {
      const chatStore = useChatStore()
      
      // 创建会话
      chatStore.createSession('测试会话')
      
      // 添加消息
      chatStore.addMessage({
        role: 'user',
        type: 'text',
        content: '消息1',
        status: 'sent'
      })
      
      chatStore.addMessage({
        role: 'user',
        type: 'text',
        content: '消息2',
        status: 'sent'
      })
      
      expect(chatStore.currentMessages).toHaveLength(2)
      
      // 清空消息
      chatStore.clearCurrentSession()
      
      expect(chatStore.currentMessages).toHaveLength(0)
    })
  })

  describe('Message Display Logic', () => {
    it('应该正确判断是否有活跃会话', () => {
      const chatStore = useChatStore()
      
      // 初始状态：无会话
      expect(chatStore.currentMessages.length > 0).toBe(false)
      
      // 创建会话但无消息
      chatStore.createSession('测试会话')
      expect(chatStore.currentMessages.length > 0).toBe(false)
      
      // 添加消息后
      chatStore.addMessage({
        role: 'user',
        type: 'text',
        content: '测试',
        status: 'sent'
      })
      expect(chatStore.currentMessages.length > 0).toBe(true)
    })

    it('应该在添加消息后立即显示', () => {
      const chatStore = useChatStore()
      
      // 创建会话
      chatStore.createSession('测试会话')
      
      // 模拟 Home.vue 中的 messages 计算属性
      const messages = () => chatStore.currentMessages
      const hasActiveSession = () => messages().length > 0
      
      // 初始状态
      expect(hasActiveSession()).toBe(false)
      
      // 添加消息
      chatStore.addMessage({
        role: 'user',
        type: 'text',
        content: '张三下了几单',
        status: 'sent'
      })
      
      // 应该立即显示
      expect(hasActiveSession()).toBe(true)
      expect(messages()).toHaveLength(1)
      expect(messages()[0].content).toBe('张三下了几单')
    })

    it('应该支持多个会话的消息隔离', () => {
      const chatStore = useChatStore()
      
      // 创建第一个会话
      const session1Id = chatStore.createSession('会话1')
      chatStore.addMessage({
        role: 'user',
        type: 'text',
        content: '会话1的消息',
        status: 'sent'
      })
      
      // 创建第二个会话
      const session2Id = chatStore.createSession('会话2')
      chatStore.addMessage({
        role: 'user',
        type: 'text',
        content: '会话2的消息',
        status: 'sent'
      })
      
      // 验证当前会话是第二个
      expect(chatStore.currentSessionId).toBe(session2Id)
      expect(chatStore.currentMessages).toHaveLength(1)
      expect(chatStore.currentMessages[0].content).toBe('会话2的消息')
      
      // 切换到第一个会话
      chatStore.switchSession(session1Id)
      expect(chatStore.currentSessionId).toBe(session1Id)
      expect(chatStore.currentMessages).toHaveLength(1)
      expect(chatStore.currentMessages[0].content).toBe('会话1的消息')
    })
  })

  describe('Message Types and Status', () => {
    it('应该支持不同的消息类型', () => {
      const chatStore = useChatStore()
      chatStore.createSession('测试会话')
      
      // 文本消息
      const textMsgId = chatStore.addMessage({
        role: 'user',
        type: 'text',
        content: '文本消息',
        status: 'sent'
      })
      
      // SQL 消息
      const sqlMsgId = chatStore.addMessage({
        role: 'assistant',
        type: 'sql',
        content: 'SELECT * FROM users',
        status: 'completed'
      })
      
      // 表格消息
      const tableMsgId = chatStore.addMessage({
        role: 'assistant',
        type: 'table',
        content: '查询结果',
        status: 'completed',
        metadata: {
          columns: ['id', 'name'],
          data: [{ id: 1, name: '张三' }]
        }
      })
      
      expect(chatStore.currentMessages).toHaveLength(3)
      expect(chatStore.currentMessages[0].type).toBe('text')
      expect(chatStore.currentMessages[1].type).toBe('sql')
      expect(chatStore.currentMessages[2].type).toBe('table')
    })

    it('应该支持不同的消息状态', () => {
      const chatStore = useChatStore()
      chatStore.createSession('测试会话')
      
      // 发送中
      const sendingMsgId = chatStore.addMessage({
        role: 'user',
        type: 'text',
        content: '消息',
        status: 'sending'
      })
      
      // 已发送
      const sentMsgId = chatStore.addMessage({
        role: 'user',
        type: 'text',
        content: '消息',
        status: 'sent'
      })
      
      // 流式输出中
      const streamingMsgId = chatStore.addMessage({
        role: 'assistant',
        type: 'text',
        content: '流式',
        status: 'streaming'
      })
      
      // 已完成
      const completedMsgId = chatStore.addMessage({
        role: 'assistant',
        type: 'text',
        content: '完成',
        status: 'completed'
      })
      
      // 错误
      const errorMsgId = chatStore.addMessage({
        role: 'system',
        type: 'error',
        content: '错误信息',
        status: 'error'
      })
      
      expect(chatStore.currentMessages[0].status).toBe('sending')
      expect(chatStore.currentMessages[1].status).toBe('sent')
      expect(chatStore.currentMessages[2].status).toBe('streaming')
      expect(chatStore.currentMessages[3].status).toBe('completed')
      expect(chatStore.currentMessages[4].status).toBe('error')
    })
  })

  describe('Edge Cases', () => {
    it('应该处理空消息内容', () => {
      const chatStore = useChatStore()
      chatStore.createSession('测试会话')
      
      const messageId = chatStore.addMessage({
        role: 'user',
        type: 'text',
        content: '',
        status: 'sent'
      })
      
      expect(chatStore.currentMessages).toHaveLength(1)
      expect(chatStore.currentMessages[0].content).toBe('')
    })

    it('应该处理很长的消息内容', () => {
      const chatStore = useChatStore()
      chatStore.createSession('测试会话')
      
      const longContent = 'A'.repeat(10000)
      const messageId = chatStore.addMessage({
        role: 'user',
        type: 'text',
        content: longContent,
        status: 'sent'
      })
      
      expect(chatStore.currentMessages[0].content).toBe(longContent)
      expect(chatStore.currentMessages[0].content.length).toBe(10000)
    })

    it('应该处理特殊字符', () => {
      const chatStore = useChatStore()
      chatStore.createSession('测试会话')
      
      const specialContent = '测试 <script>alert("xss")</script> & "quotes" \'single\''
      const messageId = chatStore.addMessage({
        role: 'user',
        type: 'text',
        content: specialContent,
        status: 'sent'
      })
      
      expect(chatStore.currentMessages[0].content).toBe(specialContent)
    })

    it('应该处理 Unicode 字符', () => {
      const chatStore = useChatStore()
      chatStore.createSession('测试会话')
      
      const unicodeContent = '你好 🎉 مرحبا 🌍 Привет'
      const messageId = chatStore.addMessage({
        role: 'user',
        type: 'text',
        content: unicodeContent,
        status: 'sent'
      })
      
      expect(chatStore.currentMessages[0].content).toBe(unicodeContent)
    })
  })
})
