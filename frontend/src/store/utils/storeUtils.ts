/**
 * 状态管理工具函数
 */
import type { AsyncState, OperationResult, ApiResponse } from '../types/common'

/**
 * 异步操作包装器
 * 自动处理 loading 状态和错误处理
 */
export async function withAsyncState<T, R>(
  state: AsyncState<T>,
  operation: () => Promise<R>,
  options: {
    /** 是否在操作前清除错误 */
    clearError?: boolean
    /** 是否更新最后更新时间 */
    updateTimestamp?: boolean
    /** 错误处理函数 */
    onError?: (error: any) => void
    /** 成功处理函数 */
    onSuccess?: (result: R) => void
  } = {}
): Promise<R | null> {
  const {
    clearError = true,
    updateTimestamp = true,
    onError,
    onSuccess
  } = options

  // 设置加载状态
  state.loading = true
  if (clearError) {
    state.error = null
  }

  try {
    const result = await operation()
    
    if (updateTimestamp) {
      state.lastUpdated = new Date().toISOString()
    }
    
    if (onSuccess) {
      onSuccess(result)
    }
    
    return result
  } catch (error: any) {
    const errorMessage = error.message || '操作失败'
    state.error = errorMessage
    
    if (onError) {
      onError(error)
    } else {
      console.error('Store operation error:', error)
    }
    
    return null
  } finally {
    state.loading = false
  }
}

/**
 * 处理 API 响应
 */
export function handleApiResponse<T>(response: ApiResponse<T>): OperationResult<T> {
  if (response.success && response.code === 200) {
    return {
      success: true,
      data: response.data,
      message: response.message
    }
  } else {
    return {
      success: false,
      message: response.message || '请求失败',
      code: response.code?.toString()
    }
  }
}

/**
 * 创建乐观更新函数
 * 先更新本地状态，如果 API 调用失败则回滚
 */
export function createOptimisticUpdate<T>(
  state: T[],
  getId: (item: T) => string
) {
  return {
    /**
     * 乐观添加
     */
    add: async (
      item: T,
      apiCall: () => Promise<T>
    ): Promise<boolean> => {
      // 先添加到本地状态
      state.push(item)
      
      try {
        // 调用 API
        const result = await apiCall()
        
        // 更新本地状态为服务器返回的数据
        const index = state.findIndex(i => getId(i) === getId(item))
        if (index !== -1) {
          state[index] = result
        }
        
        return true
      } catch (error) {
        // 回滚：移除添加的项
        const index = state.findIndex(i => getId(i) === getId(item))
        if (index !== -1) {
          state.splice(index, 1)
        }
        throw error
      }
    },

    /**
     * 乐观更新
     */
    update: async (
      id: string,
      updates: Partial<T>,
      apiCall: () => Promise<T>
    ): Promise<boolean> => {
      // 保存原始数据
      const index = state.findIndex(i => getId(i) === id)
      if (index === -1) return false
      
      const original = { ...state[index] }
      
      // 先更新本地状态
      state[index] = { ...state[index], ...updates }
      
      try {
        // 调用 API
        const result = await apiCall()
        
        // 更新本地状态为服务器返回的数据
        state[index] = result
        
        return true
      } catch (error) {
        // 回滚：恢复原始数据
        state[index] = original
        throw error
      }
    },

    /**
     * 乐观删除
     */
    remove: async (
      id: string,
      apiCall: () => Promise<void>
    ): Promise<boolean> => {
      // 保存原始数据和位置
      const index = state.findIndex(i => getId(i) === id)
      if (index === -1) return false
      
      const original = state[index]
      
      // 先从本地状态移除
      state.splice(index, 1)
      
      try {
        // 调用 API
        await apiCall()
        return true
      } catch (error) {
        // 回滚：恢复删除的项
        state.splice(index, 0, original)
        throw error
      }
    }
  }
}

/**
 * 防抖函数
 * 用于防止频繁的状态更新
 */
export function debounce<T extends (...args: any[]) => any>(
  func: T,
  wait: number
): (...args: Parameters<T>) => void {
  let timeout: number | null = null
  
  return (...args: Parameters<T>) => {
    if (timeout) {
      clearTimeout(timeout)
    }
    
    timeout = setTimeout(() => {
      func(...args)
    }, wait)
  }
}

/**
 * 节流函数
 * 用于限制状态更新频率
 */
export function throttle<T extends (...args: any[]) => any>(
  func: T,
  wait: number
): (...args: Parameters<T>) => void {
  let lastTime = 0
  
  return (...args: Parameters<T>) => {
    const now = Date.now()
    
    if (now - lastTime >= wait) {
      lastTime = now
      func(...args)
    }
  }
}

/**
 * 深度克隆对象
 * 用于避免状态突变
 */
export function deepClone<T>(obj: T): T {
  if (obj === null || typeof obj !== 'object') {
    return obj
  }
  
  if (obj instanceof Date) {
    return new Date(obj.getTime()) as unknown as T
  }
  
  if (obj instanceof Array) {
    return obj.map(item => deepClone(item)) as unknown as T
  }
  
  if (typeof obj === 'object') {
    const cloned = {} as T
    for (const key in obj) {
      if (obj.hasOwnProperty(key)) {
        cloned[key] = deepClone(obj[key])
      }
    }
    return cloned
  }
  
  return obj
}

/**
 * 比较两个对象是否相等
 * 用于优化状态更新
 */
export function isEqual(a: any, b: any): boolean {
  if (a === b) return true
  
  if (a == null || b == null) return false
  
  if (typeof a !== typeof b) return false
  
  if (typeof a !== 'object') return false
  
  const keysA = Object.keys(a)
  const keysB = Object.keys(b)
  
  if (keysA.length !== keysB.length) return false
  
  for (const key of keysA) {
    if (!keysB.includes(key)) return false
    if (!isEqual(a[key], b[key])) return false
  }
  
  return true
}

/**
 * 创建状态快照
 * 用于撤销/重做功能
 */
export class StateSnapshot<T> {
  private snapshots: T[] = []
  private currentIndex = -1
  private maxSnapshots = 50

  /**
   * 保存快照
   */
  save(state: T): void {
    // 移除当前位置之后的快照
    this.snapshots = this.snapshots.slice(0, this.currentIndex + 1)
    
    // 添加新快照
    this.snapshots.push(deepClone(state))
    this.currentIndex++
    
    // 限制快照数量
    if (this.snapshots.length > this.maxSnapshots) {
      this.snapshots.shift()
      this.currentIndex--
    }
  }

  /**
   * 撤销
   */
  undo(): T | null {
    if (this.currentIndex > 0) {
      this.currentIndex--
      return deepClone(this.snapshots[this.currentIndex])
    }
    return null
  }

  /**
   * 重做
   */
  redo(): T | null {
    if (this.currentIndex < this.snapshots.length - 1) {
      this.currentIndex++
      return deepClone(this.snapshots[this.currentIndex])
    }
    return null
  }

  /**
   * 是否可以撤销
   */
  canUndo(): boolean {
    return this.currentIndex > 0
  }

  /**
   * 是否可以重做
   */
  canRedo(): boolean {
    return this.currentIndex < this.snapshots.length - 1
  }

  /**
   * 清除所有快照
   */
  clear(): void {
    this.snapshots = []
    this.currentIndex = -1
  }
}