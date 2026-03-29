# -*- coding: utf-8 -*-
"""
Redis 缓存客户端
"""

import json
import hashlib
import logging
from typing import Optional, Any, List
from datetime import datetime

import redis

from data_source.config import REDIS_CONFIG, CACHE_EXPIRE, ENABLE_REDIS

logger = logging.getLogger(__name__)

_redis_client = None


class RedisCache:
    """Redis 缓存封装"""

    def __init__(self):
        self._client = None
        if ENABLE_REDIS:
            self._connect()
        else:
            logger.info("Redis is disabled by config")

    def _connect(self):
        """建立 Redis 连接"""
        try:
            self._client = redis.Redis(**REDIS_CONFIG)
            self._client.ping()
            logger.info(f"Redis 已连接: {REDIS_CONFIG['host']}:{REDIS_CONFIG['port']}")
        except redis.ConnectionError as e:
            logger.warning(f"Redis 连接失败: {e}，缓存功能将不可用")
            self._client = None

    @property
    def client(self) -> Optional[redis.Redis]:
        """获取 Redis 客户端"""
        if not ENABLE_REDIS:
            return None
        if self._client is None:
            self._connect()
        return self._client

    def is_available(self) -> bool:
        """检查 Redis 是否可用"""
        if not ENABLE_REDIS:
            return False
        if self._client is None:
            return False
        try:
            self._client.ping()
            return True
        except:
            return False

    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        if not self.is_available():
            return None
        try:
            value = self._client.get(key)
            if value:
                return json.loads(value)
        except Exception as e:
            logger.warning(f"缓存获取失败 {key}: {e}")
        return None

    def set(self, key: str, value: Any, expire: int = None) -> bool:
        """设置缓存值"""
        if not self.is_available():
            return False
        try:
            expire = expire or CACHE_EXPIRE.get("default", 3600)
            self._client.setex(key, expire, json.dumps(value, ensure_ascii=False))
            return True
        except Exception as e:
            logger.warning(f"缓存设置失败 {key}: {e}")
            return False

    def delete(self, key: str) -> bool:
        """删除缓存"""
        if not self.is_available():
            return False
        try:
            self._client.delete(key)
            return True
        except Exception as e:
            logger.warning(f"缓存删除失败 {key}: {e}")
            return False

    def exists(self, key: str) -> bool:
        """检查 key 是否存在"""
        if not self.is_available():
            return False
        return bool(self._client.exists(key))

    def get_many(self, keys: List[str]) -> dict:
        """批量获取缓存"""
        if not self.is_available():
            return {}
        try:
            values = self._client.mget(keys)
            result = {}
            for key, value in zip(keys, values):
                if value:
                    result[key] = json.loads(value)
            return result
        except Exception as e:
            logger.warning(f"批量缓存获取失败: {e}")
            return {}

    def set_many(self, data: dict, expire: int = None) -> bool:
        """批量设置缓存"""
        if not self.is_available():
            return False
        try:
            pipe = self._client.pipeline()
            expire = expire or CACHE_EXPIRE.get("default", 3600)
            for key, value in data.items():
                pipe.setex(key, expire, json.dumps(value, ensure_ascii=False))
            pipe.execute()
            return True
        except Exception as e:
            logger.warning(f"批量缓存设置失败: {e}")
            return False

    def clear_pattern(self, pattern: str) -> int:
        """清除匹配模式的所有 key"""
        if not self.is_available():
            return 0
        try:
            keys = self._client.keys(pattern)
            if keys:
                return self._client.delete(*keys)
            return 0
        except Exception as e:
            logger.warning(f"清除缓存失败 {pattern}: {e}")
            return 0

    def incr(self, key: str, amount: int = 1) -> Optional[int]:
        """递增计数器"""
        if not self.is_available():
            return None
        try:
            return self._client.incr(key, amount)
        except Exception as e:
            logger.warning(f"计数器递增失败 {key}: {e}")
            return None

    def get_stats(self) -> dict:
        """获取缓存统计信息"""
        if not self.is_available():
            return {"status": "unavailable"}
        try:
            info = self._client.info("stats")
            db_info = self._client.info("keyspace")
            return {
                "status": "ok",
                "hits": info.get("keyspace_hits", 0),
                "misses": info.get("keyspace_misses", 0),
                "keys": db_info.get("db0", {}).get("keys", 0),
                "memory": info.get("used_memory_human", "N/A"),
            }
        except Exception as e:
            logger.warning(f"获取缓存统计失败: {e}")
            return {"status": "error", "error": str(e)}


class CacheKeys:
    """缓存 Key 命名空间"""

    @staticmethod
    def stock_info(code: str) -> str:
        return f"stock:{code}"

    @staticmethod
    def daily_kline(code: str, date: str) -> str:
        return f"kline:{code}:{date}"

    @staticmethod
    def kline_range(code: str, start: str, end: str) -> str:
        return f"kline:{code}:range:{start}:{end}"

    @staticmethod
    def backtest(hash_key: str) -> str:
        return f"backtest:{hash_key}"

    @staticmethod
    def search(query: str) -> str:
        return f"search:{hashlib.md5(query.encode()).hexdigest()[:8]}"

    @staticmethod
    def stock_list() -> str:
        return "stocks:all"

    @staticmethod
    def sync_status(table: str) -> str:
        return f"sync:{table}:status"


_cache_instance = None


def get_cache() -> RedisCache:
    """获取缓存实例（单例）"""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = RedisCache()
    return _cache_instance
