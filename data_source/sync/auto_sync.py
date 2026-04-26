# -*- coding: utf-8 -*-
"""
自动数据同步任务模块
包含启动同步、定时全量同步、自选股间隔同步功能
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from data_source.sync.tushare_sync import TushareSync

logger = logging.getLogger(__name__)

SYNC_STARTUP_DAYS = 7
SYNC_INTERVAL_DAYS = 3
SYNC_WATCHLIST_DAYS = 3


def get_watchlist_codes() -> List[str]:
    """获取自选股代码列表"""
    try:
        from backtest.watchlist_manager import WatchlistManager
        wm = WatchlistManager()
        all_stocks = wm.get_all_stocks()
        codes = [s.code for s in all_stocks if s.code]
        logger.info(f"获取到 {len(codes)} 只自选股")
        return codes
    except Exception as e:
        logger.error(f"获取自选股列表失败: {e}")
        return []


def sync_watchlist_task() -> Optional[Dict]:
    """自选股间隔同步任务（30分钟）"""
    try:
        codes = get_watchlist_codes()
        if not codes:
            logger.info("自选股列表为空，跳过同步")
            return None

        sync = TushareSync()
        start_date = (datetime.now() - timedelta(days=SYNC_WATCHLIST_DAYS)).strftime('%Y%m%d')
        end_date = datetime.now().strftime('%Y%m%d')

        results = {'synced': 0, 'failed': 0, 'records': 0}
        for code in codes:
            try:
                if code.startswith(('5', '1', '4')):
                    records = sync.sync_etf_daily(code, start_date=start_date, end_date=end_date)
                elif len(code) == 6 and code.isdigit():
                    records = sync.sync_fund_nav(code, start_date=start_date, end_date=end_date)
                else:
                    records = sync.sync_daily_kline(code, start_date=start_date, end_date=end_date)
                results['synced'] += 1
                results['records'] += records
            except Exception as e:
                logger.warning(f"同步自选股 {code} 失败: {e}")
                results['failed'] += 1

        logger.info(f"自选股同步完成: {results}")
        return results
    except Exception as e:
        logger.error(f"自选股同步任务失败: {e}")
        return None


def sync_incremental_task() -> Optional[Dict]:
    """增量同步任务（8:30/16:00）检测并补齐缺失数据"""
    try:
        sync = TushareSync()
        start_date = (datetime.now() - timedelta(days=SYNC_INTERVAL_DAYS)).strftime('%Y%m%d')

        logger.info(f"开始增量同步，数据范围: {start_date} - 今天")
        result = sync.sync_missing_data(days_back=SYNC_INTERVAL_DAYS)

        logger.info(f"增量同步完成: {result}")
        return result
    except Exception as e:
        logger.error(f"增量同步任务失败: {e}")
        return None


def sync_on_startup() -> Optional[Dict]:
    """启动时同步任务 - 确保缺失数据都同步"""
    try:
        sync = TushareSync()
        start_date = (datetime.now() - timedelta(days=SYNC_STARTUP_DAYS)).strftime('%Y%m%d')

        logger.info(f"启动时同步，数据范围: {start_date} - 今天")
        result = sync.sync_missing_data(days_back=SYNC_STARTUP_DAYS)

        logger.info(f"启动同步完成: {result}")
        return result
    except Exception as e:
        logger.error(f"启动同步任务失败: {e}")
        return None


def sync_missing_days(days_back: int = 7) -> Optional[Dict]:
    """同步指定天数的数据（对外暴露的便捷函数）"""
    try:
        sync = TushareSync()
        result = sync.sync_missing_data(days_back=days_back)
        logger.info(f"同步 {days_back} 天数据完成: {result}")
        return result
    except Exception as e:
        logger.error(f"同步失败: {e}")
        return None