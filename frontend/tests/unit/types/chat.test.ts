/**
 * 聊天类型定义测试
 */
import { describe, it, expect } from 'vitest'
import type { ChatMessage, ChatSession, WSMessage, ChatState } from '@/types/chat'

describe('Chat Types', () => {
  it('should define ChatMessage interface correctly', () => {
    const message: ChatMessage = {
      id: 'msg_1',
      role: 'user',
      type: 'text',
      content: 'Hello',
      status: 'sent',
      timestamp: Date.now()
    }

    expect(message).toHaveProperty('id')
    expect(message).toHaveProperty('role')
    expect(message).toHaveProperty('type')
    expect(message).toHaveProperty('content')
    expect(message).toHaveProperty('status')
    expect(message).toHaveProperty('timestamp')
  })

  it('should define ChatSession interface correctly', () => {
    const session: ChatSession = {
      id: 'session_1',
      title: 'Test Session',
      createdAt: Date.now(),
      updatedAt: Date.now(),
      messages: []
    }

    expect(session).toHaveProperty('id')
    expect(session).toHaveProperty('title')
    expect(session).toHaveProperty('createdAt')
    expect(session).toHaveProperty('updatedAt')
    expect(session).toHaveProperty('messages')
    expect(Array.isArray(session.messages)).toBe(true)
  })

  it('should define WSMessage interface correctly', () => {
    const wsMessage: WSMessage = {
      type: 'message',
      content: 'Test content'
    }

    expect(wsMessage).toHaveProperty('type')
    expect(wsMessage).toHaveProperty('content')
  })

  it('should define ChatState interface correctly', () => {
    const state: ChatState = {
      currentSessionId: null,
      sessions: {},
      isConnected: false,
      isStreaming: false,
      error: null
    }

    expect(state).toHaveProperty('currentSessionId')
    expect(state).toHaveProperty('sessions')
    expect(state).toHaveProperty('isConnected')
    expect(state).toHaveProperty('isStreaming')
    expect(state).toHaveProperty('error')
  })
})
