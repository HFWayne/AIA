# -*- coding: utf-8 -*-
"""
统一数据源接口
支持：MySQL数据库(分表存储) -> Redis(热缓存) -> tushare(付费API)
只使用付费的 tushare 数据源
"""

import logging
import time
import random
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, List

import tushare as ts
from sqlalchemy import text

from data_source.config import (
    DATA_SOURCE, TU_SHARE_TOKEN, REQUEST_DELAY, MAX_RETRIES,
    AVAILABLE_SOURCES, ENABLE_MYSQL
)
from data_source.db.connection import get_db_session, get_engine
from data_source.db.models import Stock, DailyKlineTushare, FundNav
from data_source.cache import get_cache, CacheKeys
from data_source.sync.tushare_sync import TushareSync
from data_source.logger import setup_logger

logger = setup_logger('fund_data_source')

CODE_TYPE_FUND = 'fund'
CODE_TYPE_ETF = 'etf'
CODE_TYPE_STOCK = 'stock'


class FundDataSource:
    """统一的数据源接口，支持多数据源切换和缓存"""

    def __init__(self, preferred_source: Optional[str] = None, use_cache: bool = True):
        self.current_source = preferred_source or DATA_SOURCE
        self.request_delay = REQUEST_DELAY
        self.max_retries = MAX_RETRIES
        self.use_cache = use_cache and ENABLE_MYSQL
        self.cache = get_cache() if self.use_cache else None
        self._init_tushare()
        self._db_available = self._check_db() if ENABLE_MYSQL else False

    def _check_db(self) -> bool:
        """检查数据库是否可用"""
        try:
            with get_db_session() as session:
                session.execute(text("SELECT 1"))
            return True
        except Exception as e:
            logger.warning(f"数据库不可用: {e}")
            return False

    def _get_code_type(self, fund_code: str) -> str:
        """判断代码类型

        Returns:
            'fund': 场外基金 (以 16 开头)
            'etf': 场内ETF (以 5/1/4 开头)
            'stock': 股票 (其他)
        """
        if fund_code.startswith('16'):
            return CODE_TYPE_FUND
        elif fund_code.startswith(('5', '1', '4')):
            return CODE_TYPE_ETF
        else:
            return CODE_TYPE_STOCK

    def _init_tushare(self):
        """初始化 tushare"""
        self.pro = None
        if TU_SHARE_TOKEN:
            try:
                ts.set_token(TU_SHARE_TOKEN)
                self.pro = ts.pro_api()
                logger.debug("tushare pro API 初始化成功")
            except Exception as e:
                logger.warning(f"tushare pro API 初始化失败: {e}")

    def _apply_delay(self):
        """请求延时"""
        if self.request_delay > 0:
            time.sleep(self.request_delay)

    def _get_source_priority(self) -> List[str]:
        """获取数据源优先级 - 只使用 tushare"""
        return ["tushare"]

    def _get_kline_model(self, source: str):
        """根据数据源获取对应的模型类"""
        return DailyKlineTushare

    def _get_table_name(self, source: str) -> str:
        """获取表名"""
        return "daily_kline_tushare"

    def get_fund_data(
        self,
        fund_code: str,
        start_date: str,
        end_date: str
    ) -> Optional[pd.DataFrame]:
        """三级缓存获取数据：
        1. Redis 缓存（快速返回）
        2. MySQL 数据库（检查完整性，不完整则补充）
        3. Tushare API（最终数据源）
        """
        start_dt = datetime.strptime(start_date, '%Y%m%d') if start_date else datetime(2000, 1, 1)
        end_dt = datetime.strptime(end_date, '%Y%m%d') if end_date else datetime.now()

        df = self._query_database(fund_code, start_dt, end_dt)

        if df is not None and not df.empty:
            expected_days = self._estimate_trading_days(start_date, end_date)
            actual_days = len(df)

            if actual_days >= expected_days * 0.8:
                logger.info(f"从数据库获取 {fund_code}: {len(df)} 条（基本完整）")
                return df

            if actual_days < expected_days * 0.8:
                logger.info(f"从数据库获取 {fund_code}: {len(df)} 条，缺失较多，从 Tushare 补充")

                df_tushare = self._fetch_fund_nav_from_api(fund_code, start_date, end_date)
                if df_tushare is None or df_tushare.empty:
                    df_tushare = self._fetch_from_tushare_with_retry(fund_code, start_date, end_date)

                if df_tushare is not None and not df_tushare.empty:
                    self._save_to_database(fund_code, df_tushare)
                    logger.info(f"从 Tushare 补充后共 {len(df_tushare)} 条")
                    return df_tushare

        df_tushare = self._fetch_fund_nav_from_api(fund_code, start_date, end_date)
        if df_tushare is None or df_tushare.empty:
            df_tushare = self._fetch_from_tushare_with_retry(fund_code, start_date, end_date)

        if df_tushare is not None and not df_tushare.empty:
            self._save_to_database(fund_code, df_tushare)
            logger.info(f"从 Tushare 获取 {fund_code}: {len(df_tushare)} 条")
            return df_tushare

        logger.error(f"所有数据源都无法获取 {fund_code}")
        return None

    def get_fund_nav(self, fund_code: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
        """获取基金净值数据（get_fund_data 的别名）"""
        return self.get_fund_data(fund_code, start_date, end_date)

    def _estimate_trading_days(self, start_date: str, end_date: str) -> int:
        """估算交易日数量（约65%的日历天数）"""
        start = datetime.strptime(start_date, '%Y%m%d')
        end = datetime.strptime(end_date, '%Y%m%d')
        days = (end - start).days + 1
        return int(days * 0.65)

    def _find_missing_dates(
        self,
        df: pd.DataFrame,
        start_date: str,
        end_date: str
    ) -> List[str]:
        """查找缺失的日期"""
        if df is None or df.empty:
            return [start_date, end_date]

        existing_dates = set(df['date'].astype(str).str[:8].tolist())

        start = datetime.strptime(start_date, '%Y%m%d')
        end = datetime.strptime(end_date, '%Y%m%d')
        all_dates = []
        current = start
        while current <= end:
            all_dates.append(current.strftime('%Y%m%d'))
            current += timedelta(days=1)

        return [d for d in all_dates if d not in existing_dates]

    def _query_database(
        self,
        fund_code: str,
        start_dt: datetime,
        end_dt: datetime
    ) -> Optional[pd.DataFrame]:
        """查询数据库（fund_nav 或 daily_kline）"""
        if not self._db_available:
            return None

        cache_key = f"fund:{fund_code}:{start_dt.strftime('%Y%m%d')}:{end_dt.strftime('%Y%m%d')}"

        if self.cache:
            cached = self.cache.get(cache_key)
            if cached is not None:
                return pd.DataFrame(cached)

        df_fund = self._query_fund_nav_local(fund_code, start_dt, end_dt)
        if df_fund is not None and not df_fund.empty:
            df = df_fund
        else:
            df_stock = self._query_local(fund_code, start_dt, end_dt, "tushare")
            df = df_stock

        if df is not None and not df.empty:
            if self.cache:
                self.cache.set(cache_key, df.to_dict('records'), expire=3600)
            return df

        return None

    def _save_to_database(self, fund_code: str, df: pd.DataFrame):
        """保存数据到数据库"""
        if not self._db_available or df is None or df.empty:
            return

        try:
            is_fund = 'accum_nav' in df.columns

            if is_fund:
                self._save_fund_nav_to_database(fund_code, df)
            else:
                self._save_to_database_legacy(fund_code, df, "tushare", None, None)

            cache_key = f"fund:{fund_code}"
            if self.cache:
                self.cache.delete(cache_key)

        except Exception as e:
            logger.warning(f"保存数据失败: {e}")

    def _query_fund_nav_local(
        self,
        fund_code: str,
        start_dt: datetime,
        end_dt: datetime
    ) -> Optional[pd.DataFrame]:
        """从 fund_nav 表查询场外基金数据"""
        if not self._db_available:
            return None

        cache_key = f"fund_nav:{fund_code}:{start_dt.strftime('%Y%m%d')}:{end_dt.strftime('%Y%m%d')}"

        if self.cache:
            cached = self.cache.get(cache_key)
            if cached is not None:
                return pd.DataFrame(cached)

        try:
            with get_db_session() as session:
                navs = session.query(FundNav).filter(
                    FundNav.code == fund_code,
                    FundNav.nav_date >= start_dt.date(),
                    FundNav.nav_date <= end_dt.date()
                ).order_by(FundNav.nav_date).all()

                if navs:
                    df = pd.DataFrame([{
                        'date': n.nav_date.strftime('%Y%m%d') if hasattr(n.nav_date, 'strftime') else str(n.nav_date),
                        'nav': float(n.unit_nav) if n.unit_nav else 0.0,
                        'accum_nav': float(n.accum_nav) if n.accum_nav else 0.0,
                    } for n in navs])
                    if self.cache:
                        self.cache.set(cache_key, df.to_dict('records'), expire=3600)
                    return df
        except Exception as e:
            logger.warning(f"查询 fund_nav 表失败: {e}")
        return None

    def _fetch_fund_nav_from_api(
        self,
        fund_code: str,
        start_date: str,
        end_date: str
    ) -> Optional[pd.DataFrame]:
        """从 tushare pro.fund_nav() 获取场外基金数据"""
        if self.pro is None:
            logger.warning("tushare pro API 未初始化")
            return None

        for retry in range(self.max_retries):
            try:
                self._apply_delay()
                df = self.pro.fund_nav(
                    ts_code=f"{fund_code}.OF",
                    start_date=start_date,
                    end_date=end_date
                )

                if df is None or df.empty:
                    continue

                result = pd.DataFrame()
                result['date'] = df['nav_date'].astype(str)
                result['nav'] = df['unit_nav'].astype(float)
                result['accum_nav'] = df['accum_nav'].astype(float)

                return result.sort_values('date').reset_index(drop=True)

            except Exception as e:
                logger.warning(f"获取场外基金 {fund_code} 失败 (retry {retry+1}): {e}")
                time.sleep(1)

        return None

    def _save_fund_nav_to_database(self, fund_code: str, df: pd.DataFrame):
        """保存场外基金数据到 fund_nav 表"""
        if not self._db_available or df is None or df.empty:
            return

        try:
            with get_db_session() as session:
                for _, row in df.iterrows():
                    nav_date = row['date']
                    if isinstance(nav_date, str):
                        nav_date = datetime.strptime(nav_date[:8], '%Y%m%d').date()

                    sql = text("""
                        INSERT IGNORE INTO fund_nav
                        (code, ts_code, nav_date, unit_nav, accum_nav, update_flag)
                        VALUES (:code, :ts_code, :nav_date, :unit_nav, :accum_nav, :update_flag)
                    """)
                    session.execute(sql, {
                        'code': fund_code,
                        'ts_code': f"{fund_code}.OF",
                        'nav_date': nav_date,
                        'unit_nav': float(row.get('nav', 0)),
                        'accum_nav': float(row.get('accum_nav', 0)),
                        'update_flag': 'N'
                    })

            cache_key = f"fund_nav:{fund_code}"
            if self.cache:
                self.cache.delete(cache_key)

        except Exception as e:
            logger.warning(f"保存 fund_nav 失败: {e}")

    def _fetch_from_api(
        self,
        fund_code: str,
        start_date: str,
        end_date: str,
        source: str
    ) -> Optional[pd.DataFrame]:
        """从 API 获取数据，带重试"""
        return self._fetch_from_tushare_with_retry(fund_code, start_date, end_date)

    def _fetch_from_tushare_with_retry(
        self,
        fund_code: str,
        start_date: str,
        end_date: str
    ) -> Optional[pd.DataFrame]:
        """从 Tushare 获取数据，带重试"""
        for retry in range(self.max_retries):
            try:
                self._apply_delay()
                return self._get_fund_from_tushare(fund_code, start_date, end_date)
            except Exception as e:
                logger.warning(f"Tushare 获取 {fund_code} 失败 (retry {retry+1}): {e}")
                if retry < self.max_retries - 1:
                    time.sleep(1)
        return None

    def _get_error_type(self, error_msg: str) -> str:
        """识别错误类型"""
        error_msg_lower = error_msg.lower()
        if "connection" in error_msg_lower or "remote" in error_msg_lower:
            return "连接被断开"
        elif "timeout" in error_msg_lower or "timed out" in error_msg_lower:
            return "请求超时"
        elif "403" in error_msg_lower or "forbidden" in error_msg_lower:
            return "IP被封禁"
        elif "429" in error_msg_lower or "too many" in error_msg_lower:
            return "请求过于频繁"
        else:
            return "其他错误"

    def _save_to_database_legacy(self, fund_code: str, df: pd.DataFrame, source: str, 
                          start_date: str = None, end_date: str = None):
        """保存数据到本地数据库（legacy）"""
        if not self._db_available or df is None or df.empty:
            return

        try:
            table_name = self._get_table_name(source)
            klines_data = []
            
            for _, row in df.iterrows():
                trade_date = row['date']
                if isinstance(trade_date, str):
                    trade_date = datetime.strptime(trade_date[:8], '%Y%m%d').date()
                elif isinstance(trade_date, pd.Timestamp):
                    trade_date = trade_date.date()
                
                klines_data.append({
                    'code': fund_code,
                    'trade_date': trade_date,
                    'open': float(row.get('open', row.get('nav', 0))),
                    'high': float(row.get('high', row.get('nav', 0))),
                    'low': float(row.get('low', row.get('nav', 0))),
                    'close': float(row.get('nav', row.get('close', 0))),
                    'volume': float(row.get('volume', 0)),
                    'amount': float(row.get('amount', 0)),
                    'adj_close': float(row.get('nav', row.get('close', 0))),
                    'turn': 0.0,
                    'pct_chg': 0.0,
                })

            with get_db_session() as session:
                for kline in klines_data:
                    sql = text(f"""
                        INSERT IGNORE INTO {table_name} 
                        (code, trade_date, open, high, low, close, volume, amount, adj_close, turn, pct_chg)
                        VALUES (:code, :trade_date, :open, :high, :low, :close, :volume, :amount, :adj_close, :turn, :pct_chg)
                    """)
                    session.execute(sql, kline)

            cache_key = CacheKeys.kline_range(fund_code, 
                                               df['date'].min()[:8] if len(df) > 0 else start_date,
                                               df['date'].max()[:8] if len(df) > 0 else end_date, 
                                               source)
            if self.cache:
                self.cache.delete(cache_key)
                
        except Exception as e:
            logger.warning(f"保存数据到数据库({source})失败: {e}")

    def _get_fund_from_tushare(self, fund_code: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
        """从 tushare 获取数据"""
        if self.pro is None:
            logger.warning("tushare pro API 未初始化")
            return None

        for retry in range(self.max_retries):
            try:
                exchange = "SH" if fund_code.startswith(("5", "6", "9")) else "SZ"
                ts_code = f"{fund_code}.{exchange}"
                
                self._apply_delay()
                df = self.pro.daily(ts_code=ts_code, start_date=start_date, end_date=end_date, adj='qfq')
                
                if df is None or df.empty:
                    continue

                df['trade_date'] = pd.to_datetime(df['trade_date'], errors='coerce')
                df = df.dropna(subset=['trade_date'])
                df['nav'] = df['close']
                
                result = pd.DataFrame()
                result['date'] = df['trade_date'].dt.strftime('%Y%m%d')
                result['nav'] = df['nav']
                result['accum_nav'] = df['nav']
                result['open'] = df['open']
                result['high'] = df['high']
                result['low'] = df['low']

                return result.sort_values('date').reset_index(drop=True)
                
            except Exception as e:
                logger.warning(f"tushare 获取失败 (retry {retry+1}): {e}")
                time.sleep(1)
        
        return None

    def get_fund_name(self, fund_code: str) -> str:
        """获取基金名称"""
        try:
            with get_db_session() as session:
                stock = session.query(Stock).filter(Stock.code == fund_code).first()
                if stock:
                    return stock.name
        except:
            pass
        
        return fund_code

    def sync_stock_list(self, source: str = "tushare") -> int:
        """同步股票列表"""
        sync = TushareSync()
        return sync.sync_all_stocks().get("stocks", 0) + sync.sync_all_stocks().get("etfs", 0)

    def sync_daily_kline(self, fund_code: str, source: str = None) -> int:
        """同步日线数据"""
        sync = TushareSync()
        return sync.sync_daily_kline(fund_code)

    def get_data_range(self, source: str = None) -> dict:
        """获取数据日期范围"""
        if source is None:
            source = self.current_source
            
        try:
            with get_db_session() as session:
                Model = self._get_kline_model(source)
                oldest = session.query(Model.trade_date).order_by(Model.trade_date.asc()).first()
                newest = session.query(Model.trade_date).order_by(Model.trade_date.desc()).first()
                return {
                    "start": str(oldest[0]) if oldest else None,
                    "end": str(newest[0]) if newest else None
                }
        except Exception as e:
            logger.warning(f"获取数据范围失败: {e}")
            return {"start": None, "end": None}


def get_fund_data(fund_code: str, start_date: str, end_date: str, data_source: str = None) -> Optional[pd.DataFrame]:
    """便捷函数：获取基金数据"""
    ds = FundDataSource(preferred_source=data_source)
    return ds.get_fund_data(fund_code, start_date, end_date)


def get_fund_name(fund_code: str) -> str:
    """便捷函数：获取基金名称"""
    ds = FundDataSource()
    return ds.get_fund_name(fund_code)
