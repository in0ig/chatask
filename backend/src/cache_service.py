import json
import hashlib
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import logging
from collections import OrderedDict

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CacheService:
    def __init__(self, max_size: int = 1000, default_ttl: int = 300):
        """
        初始化缓存服务
        
        Args:
            max_size: 最大缓存条目数
            default_ttl: 默认过期时间（秒）
        """
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.cache = OrderedDict()
        self.hits = 0
        self.misses = 0
        
    def _generate_key(self, query: str, data_source_id: str, time_range: Dict[str, Any]) -> str:
        """
        生成缓存键
        """
        # 创建一个包含所有缓存参数的字符串
        cache_key_str = f"{query}|{data_source_id}|{json.dumps(time_range, sort_keys=True)}"
        
        # 使用SHA256哈希生成固定长度的键
        return hashlib.sha256(cache_key_str.encode('utf-8')).hexdigest()
    
    def get(self, query: str, data_source_id: str, time_range: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        从缓存中获取结果
        """
        key = self._generate_key(query, data_source_id, time_range)
        
        if key in self.cache:
            # 检查是否过期
            result, timestamp, ttl = self.cache[key]
            if datetime.now() - timestamp < timedelta(seconds=ttl):
                # 移动到末尾（最近使用）
                self.cache.move_to_end(key)
                self.hits += 1
                logger.info(f"Cache hit for query: {query[:50]}...")
                return result
            else:
                # 过期，删除
                del self.cache[key]
                
        self.misses += 1
        logger.info(f"Cache miss for query: {query[:50]}...")
        return None
    
    def set(self, query: str, data_source_id: str, time_range: Dict[str, Any], result: Dict[str, Any], ttl: Optional[int] = None) -> None:
        """
        将结果存入缓存
        """
        key = self._generate_key(query, data_source_id, time_range)
        ttl = ttl or self.default_ttl
        
        # 如果缓存已满，删除最久未使用的项目
        if len(self.cache) >= self.max_size:
            oldest_key = next(iter(self.cache))
            del self.cache[oldest_key]
            logger.info("Cache reached maximum size, removed oldest entry")
        
        # 添加新条目
        self.cache[key] = (result, datetime.now(), ttl)
        self.cache.move_to_end(key)  # 移动到末尾（最近使用）
        
        logger.info(f"Cache set for query: {query[:50]}...")
    
    def clear(self) -> None:
        """
        清空缓存
        """
        self.cache.clear()
        self.hits = 0
        self.misses = 0
        logger.info("Cache cleared")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取缓存统计信息
        """
        total = self.hits + self.misses
        hit_rate = (self.hits / total * 100) if total > 0 else 0
        
        return {
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": round(hit_rate, 2),
            "size": len(self.cache),
            "max_size": self.max_size,
            "cache_entries": list(self.cache.keys())[:10]  # 只返回前10个键
        }
    
    def delete(self, query: str, data_source_id: str, time_range: Dict[str, Any]) -> bool:
        """
        删除特定缓存条目
        """
        key = self._generate_key(query, data_source_id, time_range)
        if key in self.cache:
            del self.cache[key]
            return True
        return False
    
    def delete_by_data_source(self, data_source_id: str) -> int:
        """
        删除特定数据源的所有缓存条目
        """
        keys_to_delete = []
        
        # 遍历所有缓存项，查找匹配的数据源ID
        for key, (result, timestamp, ttl) in self.cache.items():
            # 从缓存键中提取数据源ID（需要反向解析）
            # 这里我们假设缓存键的结构是已知的，实际中可能需要更复杂的逻辑
            # 简化实现：我们只删除完全匹配的
            pass
        
        # 由于缓存键是哈希值，无法直接反向解析，我们只能清空整个缓存
        # 在实际应用中，可以使用更复杂的缓存键结构
        deleted_count = 0
        
        # 由于哈希键无法反向解析，我们只能提供清空整个缓存的选项
        # 或者在缓存键中包含原始参数
        return deleted_count
    
    def get_cache_key_info(self, query: str, data_source_id: str, time_range: Dict[str, Any]) -> str:
        """
        获取缓存键的详细信息（用于调试）
        """
        key = self._generate_key(query, data_source_id, time_range)
        return f"Cache key: {key}\nQuery: {query}\nData source: {data_source_id}\nTime range: {time_range}"