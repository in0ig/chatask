/**
 * 缓存工具类
 * 用于在 Store 中使用通用缓存功能
 */

/**
 * 缓存条目接口
 * 定义缓存数据的基本结构
 */
interface CacheEntry<T> {
  data: T;           // 缓存的数据
  timestamp: number; // 缓存时间戳（毫秒）
  ttl: number;       // 缓存过期时间（毫秒）
}

/**
 * 缓存类
 * 提供基于键值的缓存管理功能
 */
export class Cache<T> {
  private cacheMap: Map<string, CacheEntry<T>>; // 缓存存储
  private defaultTTL: number;                   // 默认过期时间（毫秒）

  /**
   * 构造函数
   * @param defaultTTL - 默认缓存过期时间（毫秒）
   */
  constructor(defaultTTL: number) {
    this.cacheMap = new Map();
    this.defaultTTL = defaultTTL;
  }

  /**
   * 设置缓存
   * @param key - 缓存键
   * @param value - 缓存值
   * @param ttl - 可选的自定义过期时间（毫秒），若未提供则使用默认值
   */
  set(key: string, value: T, ttl?: number): void {
    const actualTTL = ttl ?? this.defaultTTL;
    this.cacheMap.set(key, {
      data: value,
      timestamp: Date.now(),
      ttl: actualTTL
    });
  }

  /**
   * 获取缓存
   * @param key - 缓存键
   * @returns 缓存数据，如果不存在或已过期则返回 null
   */
  get(key: string): T | null {
    const entry = this.cacheMap.get(key);
    if (!entry) {
      return null;
    }
    
    // 检查是否过期
    if (Date.now() - entry.timestamp > entry.ttl) {
      this.cacheMap.delete(key); // 清理过期缓存
      return null;
    }
    
    return entry.data;
  }

  /**
   * 检查缓存是否存在且未过期
   * @param key - 缓存键
   * @returns 如果缓存存在且未过期返回 true，否则返回 false
   */
  has(key: string): boolean {
    const entry = this.cacheMap.get(key);
    if (!entry) {
      return false;
    }
    
    // 检查是否过期
    if (Date.now() - entry.timestamp > entry.ttl) {
      this.cacheMap.delete(key); // 清理过期缓存
      return false;
    }
    
    return true;
  }

  /**
   * 清空所有缓存
   */
  clear(): void {
    this.cacheMap.clear();
  }

  /**
   * 删除指定缓存
   * @param key - 缓存键
   */
  delete(key: string): void {
    this.cacheMap.delete(key);
  }
}

export default Cache;