# -*- coding: utf-8 -*-
"""
akshare 数据同步服务
将 akshare 数据同步到本地数据库
"""

import logging
import time
from datetime import datetime, timedelta
from typing import Optional, List, Dict

import akshare as ak
import pandas as pd

from data_source.config import REQUEST_DELAY, SYNC_CONFIG, ENABLE_MYSQL
from data_source.cache import get_cache, CacheKeys

logger = logging.getLogger(__name__)


class AkshareSync:
    """akshare 数据同步器"""

    def __init__(self):
        self.cache = get_cache() if ENABLE_MYSQL else None

    def _apply_delay(self):
        """请求延时"""
        if REQUEST_DELAY > 0:
            time.sleep(REQUEST_DELAY)

    def sync_stock_list(self) -> int:
        """同步 A 股股票列表到数据库"""
        if not ENABLE_MYSQL:
            logger.warning("MySQL is disabled, skipping stock list sync")
            return 0
            
        try:
            df = ak.stock_info_a_code_name()
            if df is None or df.empty:
                logger.warning("获取股票列表失败")
                return 0

            from data_source.db.connection import get_db_session
            from data_source.db.models import Stock

            added = 0
            with get_db_session() as session:
                for _, row in df.iterrows():
                    code = str(row['code']).zfill(6)
                    
                    existing = session.query(Stock).filter(Stock.code == code).first()
                    if existing:
                        existing.name = row['name']
                        existing.stock_type = '股票'
                        if code.startswith('6'):
                            existing.market = 'SH'
                        else:
                            existing.market = 'SZ'
                    else:
                        stock = Stock(
                            code=code,
                            name=row['name'],
                            market='SH' if code.startswith('6') else 'SZ',
                            stock_type='股票'
                        )
                        session.add(stock)
                        added += 1

            if self.cache:
                self.cache.delete(CacheKeys.stock_list())
            
            logger.info(f"同步股票列表完成: 新增 {added} 只")
            return added

        except Exception as e:
            logger.error(f"同步股票列表失败: {e}")
            return 0

    def sync_etf_list(self) -> int:
        """同步 ETF 列表到数据库"""
        if not ENABLE_MYSQL:
            logger.warning("MySQL is disabled, skipping ETF list sync")
            return 0
            
        try:
            from data_source.db.connection import get_db_session
            from data_source.db.models import Stock

            added = 0
            etf_codes = [
                ('510300', '沪深300ETF'), ('510500', '中证500ETF'),
                ('510050', '上证50ETF'), ('159915', '创业板ETF'),
                ('512660', '军工ETF'), ('512760', '芯片ETF'),
                ('515000', '科技ETF'), ('512170', '医疗ETF'),
                ('512980', '传媒ETF'), ('510880', '红利ETF'),
            ]
            
            with get_db_session() as session:
                for code, name in etf_codes:
                    code = code.zfill(6)
                    existing = session.query(Stock).filter(Stock.code == code).first()
                    if existing:
                        existing.name = name
                        existing.stock_type = 'ETF'
                    else:
                        stock = Stock(
                            code=code,
                            name=name,
                            market='SH' if code.startswith(('5', '1')) else 'SZ',
                            stock_type='ETF'
                        )
                        session.add(stock)
                        added += 1

            if self.cache:
                self.cache.delete(CacheKeys.stock_list())
            
            logger.info(f"同步ETF列表完成: 新增 {added} 只")
            return added

        except Exception as e:
            logger.error(f"同步ETF列表失败: {e}")
            return 0

    def sync_daily_kline(self, code: str, start_date: str = None, end_date: str = None) -> int:
        """同步单只股票的日线数据到数据库"""
        if not ENABLE_MYSQL:
            logger.warning("MySQL is disabled, skipping daily kline sync")
            return 0
            
        if end_date is None:
            end_date = datetime.now().strftime('%Y%m%d')
        if start_date is None:
            start_date = "20000101"

        records = 0
        for retry in range(3):
            try:
                self._apply_delay()
                
                if code.startswith('5'):
                    df = ak.fund_etf_hist_em(symbol=code)
                else:
                    df = ak.stock_zh_a_hist(symbol=code, start_date=start_date, end_date=end_date, adjust="qfq")
                
                if df is None or df.empty:
                    logger.warning(f"未获取到 {code} 的数据")
                    return 0

                df['日期'] = pd.to_datetime(df['日期'], errors='coerce')
                df = df.dropna(subset=['日期'])
                df = df[df['日期'] >= pd.to_datetime(start_date)]
                df = df[df['日期'] <= pd.to_datetime(end_date)]
                
                if df.empty:
                    return 0

                df['nav'] = pd.to_numeric(df['收盘'], errors='coerce')
                df = df.dropna(subset=['nav'])
                df = df[df['nav'] > 0]

                if df.empty:
                    return 0

                from data_source.db.connection import get_engine
                from sqlalchemy import text

                klines_data = []
                for _, row in df.iterrows():
                    klines_data.append({
                        'code': code.zfill(6),
                        'trade_date': row['日期'].date(),
                        'open': float(row.get('开盘', row['收盘'])),
                        'high': float(row.get('最高', row['收盘'])),
                        'low': float(row.get('最低', row['收盘'])),
                        'close': float(row['收盘']),
                        'volume': float(row.get('成交量', 0)),
                        'amount': float(row.get('成交额', 0)),
                        'adj_close': float(row['收盘']),
                        'turn': float(row.get('换手率', 0)) / 100 if '换手率' in row else 0,
                        'pct_chg': float(row.get('涨跌幅', 0)) / 100 if '涨跌幅' in row else 0,
                    })

                df_kline = pd.DataFrame(klines_data)
                
                with get_engine().connect() as conn:
                    for _, row in df_kline.iterrows():
                        sql = text("""
                            INSERT IGNORE INTO daily_kline 
                            (code, trade_date, open, high, low, close, volume, amount, adj_close, turn, pct_chg)
                            VALUES (:code, :trade_date, :open, :high, :low, :close, :volume, :amount, :adj_close, :turn, :pct_chg)
                        """)
                        conn.execute(sql, row.to_dict())
                    conn.commit()

                records = len(df_kline)
                
                if self.cache:
                    cache_key = CacheKeys.kline_range(code, start_date, end_date)
                    self.cache.delete(cache_key)
                
                logger.info(f"同步 {code} 日线数据: {records} 条")
                return records

            except Exception as e:
                logger.warning(f"同步 {code} 失败 (retry {retry+1}): {e}")
                time.sleep(1)

        return records

    def sync_batch(self, codes: List[str], start_date: str = None, end_date: str = None) -> Dict[str, int]:
        """批量同步多只股票"""
        if end_date is None:
            end_date = datetime.now().strftime('%Y%m%d')
        if start_date is None:
            start_date = "20200101"

        results = {}
        total = len(codes)
        
        for i, code in enumerate(codes, 1):
            code = code.strip().zfill(6)
            try:
                records = self.sync_daily_kline(code, start_date, end_date)
                results[code] = records
                if i % 10 == 0:
                    logger.info(f"批量同步进度: {i}/{total} ({i*100//total}%)")
            except Exception as e:
                logger.warning(f"同步 {code} 失败: {e}")
                results[code] = 0

        return results

    def get_latest_date(self, code: str) -> Optional[str]:
        """获取数据库中某股票最新日期"""
        if not ENABLE_MYSQL:
            return None
            
        try:
            from data_source.db.connection import get_db_session
            from data_source.db.models import DailyKline
            
            code = code.zfill(6)
            with get_db_session() as session:
                latest = session.query(DailyKline).filter(
                    DailyKline.code == code
                ).order_by(DailyKline.trade_date.desc()).first()
                
                if latest:
                    return str(latest.trade_date)
        except Exception as e:
            logger.warning(f"获取 {code} 最新日期失败: {e}")
        return None

    def sync_watchlist(self, watchlist_codes: List[str]) -> Dict[str, int]:
        """同步自选股列表"""
        return self.sync_batch(watchlist_codes)

    def get_data_range(self) -> Dict[str, str]:
        """获取数据库中数据的日期范围"""
        if not ENABLE_MYSQL:
            return {"start": None, "end": None}
            
        try:
            from data_source.db.connection import get_db_session
            from data_source.db.models import DailyKline
            
            with get_db_session() as session:
                oldest = session.query(DailyKline.trade_date).order_by(DailyKline.trade_date.asc()).first()
                newest = session.query(DailyKline.trade_date).order_by(DailyKline.trade_date.desc()).first()
                
            return {
                "start": str(oldest[0]) if oldest else None,
                "end": str(newest[0]) if newest else None
            }
        except Exception as e:
            logger.warning(f"获取数据范围失败: {e}")
            return {"start": None, "end": None}


def sync_stock_list() -> int:
    """便捷函数：同步股票列表"""
    sync = AkshareSync()
    return sync.sync_stock_list()


def sync_etf_list() -> int:
    """便捷函数：同步ETF列表"""
    sync = AkshareSync()
    return sync.sync_etf_list()


def sync_stock(code: str, start_date: str = None) -> int:
    """便捷函数：同步单只股票"""
    sync = AkshareSync()
    return sync.sync_daily_kline(code, start_date)
