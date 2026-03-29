# -*- coding: utf-8 -*-
"""
分级缓存策略

功能:
- L1 缓存：内存 LRU 缓存（热点数据）
- L2 缓存：Redis 分布式缓存
- 缓存预热：提前加载常用数据
- 缓存监控：命中率统计
"""

import logging
import time
from functools import lru_cache
from collections import OrderedDict
from typing import Optional, Any, Dict, Callable
from threading import Lock
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class LRUCache:
    """线程安全的 LRU 缓存"""

    def __init__(self, max_size: int = 100):
        self._cache = OrderedDict()
        self._max_size = max_size
        self._lock = Lock()
        self._hits = 0
        self._misses = 0

    def get(self, key: str) -> Optional[Any]:
        """获取缓存"""
        with self._lock:
            if key in self._cache:
                self._hits += 1
                self._cache.move_to_end(key)
                return self._cache[key]
            self._misses += 1
            return None

    def set(self, key: str, value: Any):
        """设置缓存"""
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
            else:
                if len(self._cache) >= self._max_size:
                    self._cache.popitem(last=False)
            self._cache[key] = value

    def delete(self, key: str) -> bool:
        """删除缓存"""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    def clear(self):
        """清空缓存"""
        with self._lock:
            self._cache.clear()
            self._hits = 0
            self._misses = 0

    def stats(self) -> Dict:
        """获取缓存统计"""
        with self._lock:
            total = self._hits + self._misses
            hit_rate = self._hits / total if total > 0 else 0
            return {
                "size": len(self._cache),
                "max_size": self._max_size,
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": hit_rate
            }


class TieredCache:
    """分级缓存 (L1 内存 + L2 Redis)"""

    def __init__(self, l1_size: int = 200, l1_ttl: int = 300):
        self._l1 = LRUCache(max_size=l1_size)
        self._l1_ttl = l1_ttl
        self._l1_timestamps: Dict[str, float] = {}
        self._lock = Lock()

    def get(self, key: str, l2_getter: Optional[Callable[[str], Any]] = None) -> Optional[Any]:
        """获取缓存 (L1 -> L2)"""
        value = self._l1.get(key)

        if value is not None:
            ts = self._l1_timestamps.get(key, 0)
            if time.time() - ts < self._l1_ttl:
                logger.debug(f"L1 命中: {key}")
                return value
            else:
                self._l1.delete(key)
                self._l1_timestamps.pop(key, None)

        if l2_getter:
            value = l2_getter(key)
            if value is not None:
                logger.debug(f"L2 命中: {key}")
                self._l1.set(key, value)
                self._l1_timestamps[key] = time.time()
                return value

        return None

    def set(self, key: str, value: Any, l2_setter: Optional[Callable] = None):
        """设置缓存 (L1 + L2)"""
        self._l1.set(key, value)
        self._l1_timestamps[key] = time.time()

        if l2_setter:
            l2_setter(key, value)

    def invalidate(self, key: str, l2_deleter: Optional[Callable] = None):
        """使缓存失效"""
        self._l1.delete(key)
        self._l1_timestamps.pop(key, None)

        if l2_deleter:
            l2_deleter(key)

    def stats(self) -> Dict:
        """获取缓存统计"""
        return {
            "l1": self._l1.stats()
        }


class CacheWarming:
    """缓存预热服务"""

    def __init__(self, cache, l2_cache):
        self._cache = cache
        self._l2 = l2_cache
        self._warmed_keys: set = set()

    def warm_stock_info(self, codes: list):
        """预热股票信息缓存"""
        from data_source.fund_data_source import FundDataSource

        ds = FundDataSource()
        warmed = 0

        for code in codes:
            key = f"stock:{code}"
            if key not in self._warmed_keys:
                try:
                    data = ds._get_stock_from_db(code)
                    if data:
                        self._cache.set(key, data)
                        self._warmed_keys.add(key)
                        warmed += 1
                except Exception as e:
                    logger.warning(f"预热 {code} 失败: {e}")

        logger.info(f"缓存预热完成: {warmed} 只股票")

    def warm_watchlist_klines(self, watchlist_codes: list, days: int = 30):
        """预热自选股日线缓存"""
        from data_source.fund_data_source import FundDataSource

        ds = FundDataSource()
        warmed = 0

        end_date = datetime.now().strftime('%Y%m%d')
        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y%m%d')

        for code in watchlist_codes:
            key = f"kline:{code}:{start_date}:{end_date}"
            if key not in self._warmed_keys:
                try:
                    data = ds._get_kline_from_db(code, start_date, end_date)
                    if data is not None and not data.empty:
                        self._cache.set(key, data)
                        self._warmed_keys.add(key)
                        warmed += 1
                except Exception as e:
                    logger.warning(f"预热 {code} K线失败: {e}")

        logger.info(f"K线缓存预热完成: {warmed} 只股票")


_tiered_cache = None


def get_tiered_cache() -> TieredCache:
    """获取分级缓存实例"""
    global _tiered_cache
    if _tiered_cache is None:
        from data_source.cache import get_cache
        cache = get_cache()
        _tiered_cache = TieredCache(l1_size=200, l1_ttl=300)
    return _tiered_cache
