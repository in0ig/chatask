"""
字典缓存服务
使用Redis实现字典数据的缓存机制，支持字典树结构缓存和批量缓存
"""
import logging
import json
import time
import os
from typing import Dict, List, Optional, Any
from redis import Redis, ConnectionError
from redis.exceptions import RedisError
from src.models.data_preparation_model import Dictionary, DictionaryItem

# 创建日志记录器
logger = logging.getLogger(__name__)

class DictionaryCache:
    """
    字典缓存服务类
    使用Redis实现字典数据的缓存机制
    """
    
    def __init__(self):
        """初始化字典缓存服务"""
        self.redis_client = None
        # 使用环境变量配置Redis
        self.is_enabled = os.getenv('DICTIONARY_CACHE_ENABLED', 'false').lower() == 'true'
        self.cache_ttl = int(os.getenv('DICTIONARY_CACHE_TTL', '3600'))  # 缓存过期时间（秒）
        self.cache_version_key = "dictionary:cache_version"  # 缓存版本控制键
        self._connect()
        
    def _connect(self):
        """连接Redis服务器"""
        if not self.is_enabled:
            logger.info("Dictionary cache is disabled")
            return
        
        try:
            # 使用环境变量配置Redis连接
            self.redis_client = Redis(
                host=os.getenv('REDIS_HOST', '127.0.0.1'),
                port=int(os.getenv('REDIS_PORT', '6379')),
                db=int(os.getenv('REDIS_DB', '0')),
                password=os.getenv('REDIS_PASSWORD', None) or None,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
                max_connections=20
            )
            # 测试连接
            self.redis_client.ping()
            logger.info("Successfully connected to Redis for dictionary cache")
        except ConnectionError as e:
            logger.error(f"Failed to connect to Redis for dictionary cache: {str(e)}")
            self.is_enabled = False
            self.redis_client = None
        except Exception as e:
            logger.error(f"Unexpected error connecting to Redis: {str(e)}")
            self.is_enabled = False
            self.redis_client = None
    
    def _get_cache_key(self, key_type: str, key_id: str = None, version: str = None) -> str:
        """
        生成缓存键
        
        Args:
            key_type: 缓存类型（dictionaries, tree, items, batch）
            key_id: 键ID（字典ID、字典项ID等）
            version: 缓存版本
            
        Returns:
            缓存键字符串
        """
        if version is None:
            version = self.get_cache_version()
        
        if key_id:
            return f"dictionary:{key_type}:{key_id}:v{version}"
        else:
            return f"dictionary:{key_type}:v{version}"
    
    def get_cache_version(self) -> str:
        """
        获取当前缓存版本
        
        Returns:
            缓存版本字符串
        """
        if not self.is_enabled:
            return "0"
        
        try:
            version = self.redis_client.get(self.cache_version_key)
            if version:
                return version.decode('utf-8')
            else:
                # 如果版本不存在，初始化为1
                self.redis_client.set(self.cache_version_key, "1", ex=self.cache_ttl)
                return "1"
        except RedisError as e:
            logger.error(f"Error getting cache version: {str(e)}")
            return "0"
    
    def set_cache_version(self, version: str):
        """
        设置缓存版本
        
        Args:
            version: 缓存版本字符串
        """
        if not self.is_enabled:
            return
        
        try:
            self.redis_client.set(self.cache_version_key, version, ex=self.cache_ttl)
            logger.info(f"Cache version set to {version}")
        except RedisError as e:
            logger.error(f"Error setting cache version: {str(e)}")
    
    def increment_cache_version(self) -> str:
        """
        增加缓存版本号
        
        Returns:
            新的缓存版本字符串
        """
        if not self.is_enabled:
            return "0"
        
        try:
            # 使用Redis的INCR命令原子性地增加版本号
            new_version = self.redis_client.incr(self.cache_version_key)
            # 设置过期时间
            self.redis_client.expire(self.cache_version_key, self.cache_ttl)
            new_version_str = str(new_version)
            logger.info(f"Cache version incremented to {new_version_str}")
            return new_version_str
        except RedisError as e:
            logger.error(f"Error incrementing cache version: {str(e)}")
            return "0"
    
    def get_dictionaries(self, page: int = 1, page_size: int = 10, search: str = None, status: bool = None, parent_id: str = None) -> Optional[Dict[str, Any]]:
        """
        获取字典列表（带缓存）
        
        Args:
            page: 页码
            page_size: 每页数量
            search: 搜索关键词
            status: 启用状态
            parent_id: 父字典ID
            
        Returns:
            缓存的字典列表或None（如果缓存未命中）
        """
        if not self.is_enabled:
            return None
        
        # 构建缓存键
        cache_key = self._get_cache_key("dictionaries", version=self.get_cache_version())
        
        try:
            cached_data = self.redis_client.get(cache_key)
            if cached_data:
                logger.info(f"Dictionary list cache hit for key: {cache_key}")
                return json.loads(cached_data.decode('utf-8'))
            else:
                logger.info(f"Dictionary list cache miss for key: {cache_key}")
                return None
        except RedisError as e:
            logger.error(f"Error getting dictionary list from cache: {str(e)}")
            return None
    
    def set_dictionaries(self, data: Dict[str, Any]):
        """
        设置字典列表缓存
        
        Args:
            data: 字典列表数据
        """
        if not self.is_enabled:
            return
        
        cache_key = self._get_cache_key("dictionaries", version=self.get_cache_version())
        
        try:
            # 序列化数据
            json_data = json.dumps(data, ensure_ascii=False)
            # 设置缓存，使用配置的过期时间
            self.redis_client.setex(cache_key, self.cache_ttl, json_data)
            logger.info(f"Dictionary list cached successfully with key: {cache_key}")
        except (RedisError, TypeError) as e:
            logger.error(f"Error setting dictionary list in cache: {str(e)}")
    
    def get_dictionaries_tree(self) -> Optional[List[Dict[str, Any]]]:
        """
        获取字典树形结构（带缓存）
        
        Returns:
            缓存的字典树或None（如果缓存未命中）
        """
        if not self.is_enabled:
            return None
        
        cache_key = self._get_cache_key("tree", version=self.get_cache_version())
        
        try:
            cached_data = self.redis_client.get(cache_key)
            if cached_data:
                logger.info(f"Dictionary tree cache hit for key: {cache_key}")
                return json.loads(cached_data.decode('utf-8'))
            else:
                logger.info(f"Dictionary tree cache miss for key: {cache_key}")
                return None
        except RedisError as e:
            logger.error(f"Error getting dictionary tree from cache: {str(e)}")
            return None
    
    def set_dictionaries_tree(self, data: List[Dict[str, Any]]):
        """
        设置字典树形结构缓存
        
        Args:
            data: 字典树数据
        """
        if not self.is_enabled:
            return
        
        cache_key = self._get_cache_key("tree", version=self.get_cache_version())
        
        try:
            json_data = json.dumps(data, ensure_ascii=False)
            self.redis_client.setex(cache_key, self.cache_ttl, json_data)
            logger.info(f"Dictionary tree cached successfully with key: {cache_key}")
        except (RedisError, TypeError) as e:
            logger.error(f"Error setting dictionary tree in cache: {str(e)}")
    
    def get_dictionary_items(self, dictionary_id: str, page: int = 1, page_size: int = 10, search: str = None, status: bool = None) -> Optional[Dict[str, Any]]:
        """
        获取字典项列表（带缓存）
        
        Args:
            dictionary_id: 字典ID
            page: 页码
            page_size: 每页数量
            search: 搜索关键词
            status: 启用状态
            
        Returns:
            缓存的字典项列表或None（如果缓存未命中）
        """
        if not self.is_enabled:
            return None
        
        # 构建缓存键，包含所有查询参数
        params = f"p{page}_ps{page_size}_s{search or 'none'}_st{status or 'none'}"
        cache_key = self._get_cache_key("items", f"{dictionary_id}_{params}", version=self.get_cache_version())
        
        try:
            cached_data = self.redis_client.get(cache_key)
            if cached_data:
                logger.info(f"Dictionary items cache hit for key: {cache_key}")
                return json.loads(cached_data.decode('utf-8'))
            else:
                logger.info(f"Dictionary items cache miss for key: {cache_key}")
                return None
        except RedisError as e:
            logger.error(f"Error getting dictionary items from cache: {str(e)}")
            return None
    
    def set_dictionary_items(self, dictionary_id: str, data: Dict[str, Any]):
        """
        设置字典项列表缓存
        
        Args:
            dictionary_id: 字典ID
            data: 字典项列表数据
        """
        if not self.is_enabled:
            return
        
        # 构建缓存键，包含所有查询参数
        # 注意：这里需要根据实际的查询参数来构建，但为了简化，我们假设是默认参数
        # 在实际使用中，应该根据具体的查询参数来构建缓存键
        cache_key = self._get_cache_key("items", f"{dictionary_id}_p1_ps10_snone_stnone", version=self.get_cache_version())
        
        try:
            json_data = json.dumps(data, ensure_ascii=False)
            self.redis_client.setex(cache_key, self.cache_ttl, json_data)
            logger.info(f"Dictionary items cached successfully with key: {cache_key}")
        except (RedisError, TypeError) as e:
            logger.error(f"Error setting dictionary items in cache: {str(e)}")
    
    def get_dictionary(self, dict_id: str) -> Optional[Dict[str, Any]]:
        """
        获取单个字典详情（带缓存）
        
        Args:
            dict_id: 字典ID
            
        Returns:
            缓存的字典详情或None（如果缓存未命中）
        """
        if not self.is_enabled:
            return None
        
        cache_key = self._get_cache_key("dict", dict_id, version=self.get_cache_version())
        
        try:
            cached_data = self.redis_client.get(cache_key)
            if cached_data:
                logger.info(f"Dictionary cache hit for key: {cache_key}")
                return json.loads(cached_data.decode('utf-8'))
            else:
                logger.info(f"Dictionary cache miss for key: {cache_key}")
                return None
        except RedisError as e:
            logger.error(f"Error getting dictionary from cache: {str(e)}")
            return None
    
    def set_dictionary(self, dict_id: str, data: Dict[str, Any]):
        """
        设置单个字典详情缓存
        
        Args:
            dict_id: 字典ID
            data: 字典详情数据
        """
        if not self.is_enabled:
            return
        
        cache_key = self._get_cache_key("dict", dict_id, version=self.get_cache_version())
        
        try:
            json_data = json.dumps(data, ensure_ascii=False)
            self.redis_client.setex(cache_key, self.cache_ttl, json_data)
            logger.info(f"Dictionary cached successfully with key: {cache_key}")
        except (RedisError, TypeError) as e:
            logger.error(f"Error setting dictionary in cache: {str(e)}")
    
    def get_dictionary_item(self, item_id: str) -> Optional[Dict[str, Any]]:
        """
        获取单个字典项（带缓存）
        
        Args:
            item_id: 字典项ID
            
        Returns:
            缓存的字典项或None（如果缓存未命中）
        """
        if not self.is_enabled:
            return None
        
        cache_key = self._get_cache_key("item", item_id, version=self.get_cache_version())
        
        try:
            cached_data = self.redis_client.get(cache_key)
            if cached_data:
                logger.info(f"Dictionary item cache hit for key: {cache_key}")
                return json.loads(cached_data.decode('utf-8'))
            else:
                logger.info(f"Dictionary item cache miss for key: {cache_key}")
                return None
        except RedisError as e:
            logger.error(f"Error getting dictionary item from cache: {str(e)}")
            return None
    
    def set_dictionary_item(self, item_id: str, data: Dict[str, Any]):
        """
        设置单个字典项缓存
        
        Args:
            item_id: 字典项ID
            data: 字典项数据
        """
        if not self.is_enabled:
            return
        
        cache_key = self._get_cache_key("item", item_id, version=self.get_cache_version())
        
        try:
            json_data = json.dumps(data, ensure_ascii=False)
            self.redis_client.setex(cache_key, self.cache_ttl, json_data)
            logger.info(f"Dictionary item cached successfully with key: {cache_key}")
        except (RedisError, TypeError) as e:
            logger.error(f"Error setting dictionary item in cache: {str(e)}")
    
    def clear_dictionary_cache(self, dict_id: str = None):
        """
        清除字典缓存
        
        Args:
            dict_id: 字典ID，如果为None则清除所有字典相关缓存
        """
        if not self.is_enabled:
            return
        
        try:
            if dict_id:
                # 清除特定字典的缓存
                keys_to_delete = []
                
                # 获取所有匹配的键
                pattern = f"dictionary:*:{dict_id}:*"
                for key in self.redis_client.scan_iter(pattern):
                    keys_to_delete.append(key.decode('utf-8'))
                
                # 删除所有匹配的键
                if keys_to_delete:
                    self.redis_client.delete(*keys_to_delete)
                    logger.info(f"Cleared {len(keys_to_delete)} cache entries for dictionary {dict_id}")
                
                # 清除字典树缓存（因为字典树包含所有字典）
                tree_key = self._get_cache_key("tree", version=self.get_cache_version())
                self.redis_client.delete(tree_key)
                logger.info(f"Cleared dictionary tree cache")
                
                # 清除字典列表缓存
                list_key = self._get_cache_key("dictionaries", version=self.get_cache_version())
                self.redis_client.delete(list_key)
                logger.info(f"Cleared dictionary list cache")
                
            else:
                # 清除所有字典缓存
                # 增加缓存版本号，这将使所有现有缓存失效
                new_version = self.increment_cache_version()
                logger.info(f"Cleared all dictionary caches by incrementing version to {new_version}")
                
        except RedisError as e:
            logger.error(f"Error clearing dictionary cache: {str(e)}")
    
    def clear_all_cache(self):
        """
        清除所有字典缓存
        """
        if not self.is_enabled:
            return
        
        try:
            # 增加缓存版本号，这将使所有现有缓存失效
            new_version = self.increment_cache_version()
            logger.info(f"Cleared all dictionary caches by incrementing version to {new_version}")
        except RedisError as e:
            logger.error(f"Error clearing all dictionary caches: {str(e)}")
    
    def warm_up_cache(self, dict_ids: List[str] = None):
        """
        预热缓存
        
        Args:
            dict_ids: 要预热的字典ID列表，如果为None则预热所有字典
        """
        if not self.is_enabled:
            return
        
        try:
            if dict_ids:
                # 预热指定的字典
                for dict_id in dict_ids:
                    # 预热字典详情
                    # 这里需要调用实际的数据服务来获取数据
                    # 由于缓存服务不应该直接依赖数据服务，所以这个方法需要在外部调用
                    pass
                logger.info(f"Warm-up initiated for {len(dict_ids)} dictionaries")
            else:
                # 预热所有字典
                # 同样，需要外部调用数据服务获取数据
                logger.info("Warm-up initiated for all dictionaries")
        except RedisError as e:
            logger.error(f"Error warming up cache: {str(e)}")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        获取缓存统计信息
        
        Returns:
            缓存统计信息字典
        """
        if not self.is_enabled:
            return {
                "enabled": False,
                "connected": False,
                "cache_version": "0",
                "total_keys": 0,
                "hit_rate": 0,
                "ttl": self.cache_ttl
            }
        
        try:
            # 获取缓存版本
            cache_version = self.get_cache_version()
            
            # 获取Redis统计信息
            info = self.redis_client.info()
            
            # 计算命中率（如果可用）
            hits = int(info.get('keyspace_hits', 0))
            misses = int(info.get('keyspace_misses', 0))
            total = hits + misses
            hit_rate = (hits / total * 100) if total > 0 else 0
            
            # 获取键数量
            key_count = self.redis_client.dbsize()
            
            return {
                "enabled": True,
                "connected": True,
                "cache_version": cache_version,
                "total_keys": key_count,
                "hit_rate": round(hit_rate, 2),
                "ttl": self.cache_ttl,
                "redis_info": {
                    "connected_clients": info.get('connected_clients'),
                    "used_memory": info.get('used_memory_human'),
                    "total_connections_received": info.get('total_connections_received'),
                    "total_commands_processed": info.get('total_commands_processed')
                }
            }
        except RedisError as e:
            logger.error(f"Error getting cache stats: {str(e)}")
            return {
                "enabled": True,
                "connected": False,
                "cache_version": "0",
                "total_keys": 0,
                "hit_rate": 0,
                "ttl": self.cache_ttl
            }

# 创建全局实例
dictionary_cache = DictionaryCache()
