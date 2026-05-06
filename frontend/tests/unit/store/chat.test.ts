/**
 * 聊天 Store 测试
 */
import { describe, it, expect, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useChatStore } from '@/store/modules/chat'

describe('Chat Store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('should initialize with default state', () => {
    const store = useChatStore()

    expect(store.currentSessionId).toBeNull()
    expect(store.sessions).toEqual({})
    expect(store.isConnected).toBe(false)
    expect(store.isStreaming).toBe(false)
    expect(store.error).toBeNull()
  })

  it('should create a new session', () => {
    const store = useChatStore()
    const sessionId = store.createSession('Test Session')

    expect(sessionId).toBeTruthy()
    expect(store.currentSessionId).toBe(sessionId)
    expect(store.sessions[sessionId]).toBeDefined()
    expect(store.sessions[sessionId].title).toBe('Test Session')
    expect(store.sessions[sessionId].messages).toEqual([])
  })

  it('should switch between sessions', () => {
    const store = useChatStore()
    const session1 = store.createSession('Session 1')
    const session2 = store.createSession('Session 2')

    expect(store.currentSessionId).toBe(session2)

    store.switchSession(session1)
    expect(store.currentSessionId).toBe(session1)
  })

  it('should delete a session', () => {
    const store = useChatStore()
    const sessionId = store.createSession('Test Session')

    expect(store.sessions[sessionId]).toBeDefined()

    store.deleteSession(sessionId)
    expect(store.sessions[sessionId]).toBeUndefined()
    expect(store.currentSessionId).toBeNull()
  })

  it('should add a message to current session', () => {
    const store = useChatStore()
    store.createSession()

    const messageId = store.addMessage({
      role: 'user',
      type: 'text',
      content: 'Hello',
      status: 'sent'
    })

    expect(messageId).toBeTruthy()
    expect(store.currentMessages).toHaveLength(1)
    expect(store.currentMessages[0].content).toBe('Hello')
  })

  it('should update a message', () => {
    const store = useChatStore()
    store.createSession()

    const messageId = store.addMessage({
      role: 'user',
      type: 'text',
      content: 'Hello',
      status: 'sending'
    })

    store.updateMessage(messageId, { status: 'sent' })

    const message = store.currentMessages.find(m => m.id === messageId)
    expect(message?.status).toBe('sent')
  })

  it('should append content to a message', () => {
    const store = useChatStore()
    store.createSession()

    const messageId = store.addMessage({
      role: 'assistant',
      type: 'text',
      content: 'Hello',
      status: 'streaming'
    })

    store.appendMessageContent(messageId, ' World')

    const message = store.currentMessages.find(m => m.id === messageId)
    expect(message?.content).toBe('Hello World')
  })

  it('should set connection status', () => {
    const store = useChatStore()

    store.setConnected(true)
    expect(store.isConnected).toBe(true)

    store.setConnected(false)
    expect(store.isConnected).toBe(false)
  })

  it('should set streaming status', () => {
    const store = useChatStore()

    store.setStreaming(true)
    expect(store.isStreaming).toBe(true)

    store.setStreaming(false)
    expect(store.isStreaming).toBe(false)
  })

  it('should set error', () => {
    const store = useChatStore()

    store.setError('Test error')
    expect(store.error).toBe('Test error')

    store.setError(null)
    expect(store.error).toBeNull()
  })

  it('should clear current session', () => {
    const store = useChatStore()
    store.createSession()

    store.addMessage({
      role: 'user',
      type: 'text',
      content: 'Hello',
      status: 'sent'
    })

    expect(store.currentMessages).toHaveLength(1)

    store.clearCurrentSession()
    expect(store.currentMessages).toHaveLength(0)
  })

  it('should get session list sorted by update time', async () => {
    const store = useChatStore()
    
    const session1 = store.createSession('Session 1')
    // 等待一小段时间确保时间戳不同
    await new Promise(resolve => setTimeout(resolve, 10))
    const session2 = store.createSession('Session 2')

    const sessionList = store.sessionList
    expect(sessionList).toHaveLength(2)
    // 最新的会话应该在前面
    expect(sessionList[0].id).toBe(session2)
    expect(sessionList[1].id).toBe(session1)
  })
})
