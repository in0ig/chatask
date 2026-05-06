/**
 * 流式输出配置模块
 * 
 * 从环境变量读取流式输出配置
 * 提供统一的配置访问接口
 */

/**
 * 流式输出配置接口
 */
export interface StreamingConfig {
  /** 是否启用流式输出 */
  enabled: boolean
  /** 流式输出超时时间（毫秒） */
  timeout: number
}

/**
 * 从环境变量加载流式输出配置
 * 
 * @returns 流式输出配置对象
 */
function loadStreamingConfig(): StreamingConfig {
  // 从环境变量读取配置，默认启用流式输出
  const enabled = import.meta.env.VITE_ENABLE_STREAMING !== 'false'
  
  // 流式输出超时时间，默认60秒
  const timeout = parseInt(import.meta.env.VITE_STREAMING_TIMEOUT || '60000', 10)
  
  return {
    enabled,
    timeout
  }
}

/**
 * 全局流式输出配置实例
 */
export const streamingConfig: StreamingConfig = loadStreamingConfig()

/**
 * 检查是否启用流式输出
 * 
 * @returns 如果启用流式输出返回 true，否则返回 false
 */
export function isStreamingEnabled(): boolean {
  return streamingConfig.enabled
}

/**
 * 获取流式输出超时时间
 * 
 * @returns 超时时间（毫秒）
 */
export function getStreamingTimeout(): number {
  return streamingConfig.timeout
}

/**
 * 获取配置摘要（用于调试）
 * 
 * @returns 配置摘要对象
 */
export function getStreamingConfigSummary(): Record<string, any> {
  return {
    enabled: streamingConfig.enabled,
    timeout: streamingConfig.timeout,
    source: 'environment'
  }
}

// 在开发模式下打印配置信息
if (import.meta.env.DEV) {
  console.log('🌊 流式输出配置:', getStreamingConfigSummary())
}
