/**
 * WebSocket 服务测试
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { WebSocketService } from '@/services/websocketService'

// Mock WebSocket
class MockWebSocket {
  static OPEN = 1
  static CLOSED = 3

  readyState = MockWebSocket.CLOSED
  onopen: (() => void) | null = null
  onmessage: ((event: any) => void) | null = null
  onerror: ((event: any) => void) | null = null
  onclose: (() => void) | null = null

  constructor(public url: string) {
    // 模拟异步连接
    setTimeout(() => {
      this.readyState = MockWebSocket.OPEN
      if (this.onopen) {
        this.onopen()
      }
    }, 10)
  }

  send(data: string) {
    if (this.readyState !== MockWebSocket.OPEN) {
      throw new Error('WebSocket is not open')
    }
  }

  close() {
    this.readyState = MockWebSocket.CLOSED
    if (this.onclose) {
      this.onclose()
    }
  }
}

// 替换全局 WebSocket
global.WebSocket = MockWebSocket as any

describe('WebSocketService', () => {
  let service: WebSocketService

  beforeEach(() => {
    service = new WebSocketService('ws://localhost:8000/ws')
  })

  it('should create WebSocketService instance', () => {
    expect(service).toBeDefined()
    expect(service.isConnected()).toBe(false)
  })

  it('should connect to WebSocket', async () => {
    await service.connect()
    expect(service.isConnected()).toBe(true)
  })

  it('should handle connection status changes', async () => {
    const handler = vi.fn()
    service.onConnection(handler)

    await service.connect()
    expect(handler).toHaveBeenCalledWith(true)
  })

  it('should send messages when connected', async () => {
    await service.connect()

    expect(() => {
      service.send({ type: 'test', content: 'Hello' })
    }).not.toThrow()
  })

  it('should throw error when sending while disconnected', () => {
    expect(() => {
      service.send({ type: 'test', content: 'Hello' })
    }).toThrow('WebSocket is not connected')
  })

  it('should disconnect WebSocket', async () => {
    await service.connect()
    expect(service.isConnected()).toBe(true)

    service.disconnect()
    expect(service.isConnected()).toBe(false)
  })

  it('should handle incoming messages', async () => {
    const handler = vi.fn()
    service.onMessage(handler)

    await service.connect()

    // 模拟接收消息
    const ws = (service as any).ws
    if (ws && ws.onmessage) {
      ws.onmessage({
        data: JSON.stringify({ type: 'message', content: 'Test' })
      })
    }

    expect(handler).toHaveBeenCalledWith({
      type: 'message',
      content: 'Test'
    })
  })

  it('should unregister message handler', async () => {
    const handler = vi.fn()
    const unregister = service.onMessage(handler)

    await service.connect()

    // 取消注册
    unregister()

    // 模拟接收消息
    const ws = (service as any).ws
    if (ws && ws.onmessage) {
      ws.onmessage({
        data: JSON.stringify({ type: 'message', content: 'Test' })
      })
    }

    expect(handler).not.toHaveBeenCalled()
  })
})
