/**
 * Chat Store - Toggle Mode 测试
 */
import { describe, it, expect, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useChatStore } from '@/store/modules/chat'

describe('Chat Store - Toggle Mode', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('should have default chatMode as query', () => {
    const chatStore = useChatStore()
    expect(chatStore.chatMode).toBe('query')
  })

  it('should toggle chatMode from query to report', () => {
    const chatStore = useChatStore()
    expect(chatStore.chatMode).toBe('query')
    
    chatStore.toggleChatMode()
    expect(chatStore.chatMode).toBe('report')
  })

  it('should toggle chatMode from report to query', () => {
    const chatStore = useChatStore()
    chatStore.chatMode = 'report'
    
    chatStore.toggleChatMode()
    expect(chatStore.chatMode).toBe('query')
  })

  it('should set dataSource correctly', () => {
    const chatStore = useChatStore()
    const dataSourceIds = ['ds1', 'ds2', 'ds3']
    
    chatStore.setDataSource(dataSourceIds)
    expect(chatStore.dataSource).toEqual(dataSourceIds)
  })

  it('should update dataSource when changed', () => {
    const chatStore = useChatStore()
    
    chatStore.setDataSource(['ds1'])
    expect(chatStore.dataSource).toEqual(['ds1'])
    
    chatStore.setDataSource(['ds2', 'ds3'])
    expect(chatStore.dataSource).toEqual(['ds2', 'ds3'])
  })
})
