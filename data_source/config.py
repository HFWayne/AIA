# -*- coding: utf-8 -*-
"""
数据源配置（业务配置，允许提交到远程仓库）
"""

import os

# API 配置
DATA_SOURCE = "akshare"
REQUEST_DELAY = 0.5
MAX_RETRIES = 5
AVAILABLE_SOURCES = ["akshare", "tushare", "auto"]

# AkShare 稳定性配置
AKSHARE_CONFIG = {
    "request_delay": 1.0,        # 请求间隔（秒）
    "max_retries": 5,           # 最大重试次数
    "retry_backoff": 2.0,       # 指数退避基数（失败后延迟时间翻倍）
    "max_retry_delay": 60,     # 最大重试延迟（秒）
    "connection_timeout": 30,    # 连接超时（秒）
    "read_timeout": 60,         # 读取超时（秒）
}

# 从 apikey.py 导入敏感信息
try:
    from data_source.apikey import TU_SHARE_TOKEN
except ImportError:
    TU_SHARE_TOKEN = os.getenv("TU_SHARE_TOKEN", "")

# MySQL 数据库配置
# ENABLE_MYSQL = False  # 关闭后可跳过数据库连接，用于测试数据源稳定性
ENABLE_MYSQL = True
MYSQL_CONFIG = {
    "host": os.getenv("MYSQL_HOST", "localhost"),
    "port": int(os.getenv("MYSQL_PORT", 3306)),
    "user": os.getenv("MYSQL_USER", "root"),
    "password": os.getenv("MYSQL_PASSWORD", "root123456"),
    "database": os.getenv("MYSQL_DATABASE", "stock_data"),
    "charset": "utf8mb4",
    "pool_size": 10,
    "max_overflow": 20,
    "pool_recycle": 3600,
}

# Redis 缓存配置
# ENABLE_REDIS = False  # 关闭后可跳过 Redis 连接，用于测试数据源稳定性
ENABLE_REDIS = True
REDIS_CONFIG = {
    "host": os.getenv("REDIS_HOST", "localhost"),
    "port": int(os.getenv("REDIS_PORT", 6379)),
    "db": int(os.getenv("REDIS_DB", 0)),
    "password": os.getenv("REDIS_PASSWORD", None),
    "decode_responses": True,
}

# 缓存过期时间（秒）
CACHE_EXPIRE = {
    "stock_info": 86400,      # 股票信息: 1天
    "daily_kline": 604800,     # 日线数据: 7天
    "kline_range": 86400,      # 区间K线: 1天
    "backtest_result": 1800,   # 回测结果: 30分钟
    "search_result": 3600,      # 搜索结果: 1小时
}

# 数据同步配置
SYNC_CONFIG = {
    "full_sync_days": 0,       # 0表示全部历史，>0表示只同步最近N天
    "batch_size": 5000,        # 批量插入大小
    "retry_interval": 300,     # 失败重试间隔（秒）
}
