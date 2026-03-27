# -*- coding: utf-8 -*-
"""
缓存模块
"""

from data_source.cache.redis_client import RedisCache, get_cache

__all__ = ["RedisCache", "get_cache"]
