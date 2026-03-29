# -*- coding: utf-8 -*-
"""
缓存 Key 统一管理
"""

from typing import List


class CacheKeys:
    """缓存 Key 定义"""

    @staticmethod
    def report_list() -> str:
        return "reports:list"

    @staticmethod
    def report(id: str) -> str:
        return f"report:{id}"

    @staticmethod
    def watchlist_list() -> str:
        return "watchlists:list"

    @staticmethod
    def watchlist(id: str) -> str:
        return f"watchlist:{id}"

    @staticmethod
    def strategy_list() -> str:
        return "strategies:list"

    @staticmethod
    def strategy(id: str) -> str:
        return f"strategy:{id}"


class CacheTTL:
    """缓存 TTL 定义（秒）"""

    REPORT_LIST = 300
    WATCHLIST_LIST = 600
    STRATEGY_LIST = 600
