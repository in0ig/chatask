from typing import Dict, Any
import json
import redis

class CacheService:
    def __init__(self):
        self.redis_client = redis.Redis(
            host='localhost',
            port=6379,
            db=0,
            decode_responses=True
        )

    def get(self, key: str) -> Any:
        """
        从缓存获取数据
        """
        value = self.redis_client.get(key)
        if value:
            return json.loads(value)
        return None

    def set(self, key: str, value: Any, expire: int = 3600):
        """
        设置缓存数据
        """
        self.redis_client.setex(key, expire, json.dumps(value))

    def delete(self, key: str):
        """
        删除缓存
        """
        self.redis_client.delete(key)

    def clear_all(self):
        """
        清除所有缓存
        """
        self.redis_client.flushdb()