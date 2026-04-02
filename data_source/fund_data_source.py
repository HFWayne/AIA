# -*- coding: utf-8 -*-
"""
统一数据源接口
支持：MySQL数据库(分表存储) -> Redis(热缓存) -> akshare/tushare(原始数据)
分表存储：daily_kline_akshare, daily_kline_tushare
回退机制：主数据源失败时自动切换到备用数据源
"""

import logging
import time
import random
import pandas as pd
from datetime import datetime
from typing import Optional, List

import tushare as ts
import akshare as ak
from sqlalchemy import text

from data_source.config import (
    DATA_SOURCE, TU_SHARE_TOKEN, REQUEST_DELAY, MAX_RETRIES,
    AVAILABLE_SOURCES, ENABLE_MYSQL, AKSHARE_CONFIG
)
from data_source.db.connection import get_db_session, get_engine
from data_source.db.models import Stock, DailyKlineAkShare, DailyKlineTushare
from data_source.cache import get_cache, CacheKeys
from data_source.sync.akshare_sync import AkshareSync
from data_source.sync.tushare_sync import TushareSync

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


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
        """获取数据源优先级回退链
        
        用户选择哪个数据源，哪个就是主数据源，失败后回退到另一个
        """
        if self.current_source == "akshare":
            return ["akshare", "tushare"]
        elif self.current_source == "tushare":
            return ["tushare", "akshare"]
        elif self.current_source == "auto":
            return ["akshare", "tushare"]
        return [self.current_source]

    def _get_kline_model(self, source: str):
        """根据数据源获取对应的模型类"""
        if source == "akshare":
            return DailyKlineAkShare
        return DailyKlineTushare

    def _get_table_name(self, source: str) -> str:
        """获取表名"""
        if source == "akshare":
            return "daily_kline_akshare"
        return "daily_kline_tushare"

    def get_fund_data(
        self,
        fund_code: str,
        start_date: str,
        end_date: str
    ) -> Optional[pd.DataFrame]:
        """获取基金数据，支持回退机制
        
        1. 优先从本地数据库查询
        2. 未命中则从 API 获取
        3. API 失败时自动回退到备用数据源
        """
        start_dt = datetime.strptime(start_date, '%Y%m%d') if start_date else datetime(2000, 1, 1)
        end_dt = datetime.strptime(end_date, '%Y%m%d') if end_date else datetime.now()

        sources = self._get_source_priority()
        
        for source in sources:
            df = self._query_local(fund_code, start_dt, end_dt, source)
            if df is not None and not df.empty:
                logger.info(f"从本地数据库({source})获取 {fund_code}: {len(df)} 条")
                return df

        for source in sources:
            df = self._fetch_from_api(fund_code, start_date, end_date, source)
            if df is not None and not df.empty:
                self._save_to_database(fund_code, df, source, start_date, end_date)
                logger.info(f"从 API({source})获取并存储 {fund_code}: {len(df)} 条")
                return df

        logger.error(f"所有数据源都无法获取 {fund_code}")
        return None

    def get_fund_nav(self, fund_code: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
        """获取基金净值数据（get_fund_data 的别名）"""
        return self.get_fund_data(fund_code, start_date, end_date)

    def _query_local(
        self,
        fund_code: str,
        start_dt: datetime,
        end_dt: datetime,
        source: str
    ) -> Optional[pd.DataFrame]:
        """从本地数据库查询"""
        if not self._db_available:
            return None

        cache_key = CacheKeys.kline_range(fund_code, str(start_dt.strftime('%Y%m%d')), 
                                           str(end_dt.strftime('%Y%m%d')), source)
        
        if self.cache:
            cached = self.cache.get(cache_key)
            if cached is not None:
                return pd.DataFrame(cached)

        try:
            with get_db_session() as session:
                Model = self._get_kline_model(source)
                klines = session.query(Model).filter(
                    Model.code == fund_code,
                    Model.trade_date >= start_dt.date(),
                    Model.trade_date <= end_dt.date()
                ).order_by(Model.trade_date).all()

                if klines:
                    df = pd.DataFrame([k.to_dict() for k in klines])
                    if self.cache:
                        self.cache.set(cache_key, df.to_dict('records'), expire=3600)
                    return df
        except Exception as e:
            logger.warning(f"查询本地数据库({source})失败: {e}")
        return None

    def _fetch_from_api(
        self,
        fund_code: str,
        start_date: str,
        end_date: str,
        source: str
    ) -> Optional[pd.DataFrame]:
        """从 API 获取数据，带指数退避重试"""
        if source == "akshare":
            return self._fetch_from_akshare_with_retry(fund_code, start_date, end_date)
        elif source == "tushare":
            return self._fetch_from_tushare_with_retry(fund_code, start_date, end_date)
        return None

    def _fetch_from_akshare_with_retry(
        self,
        fund_code: str,
        start_date: str,
        end_date: str
    ) -> Optional[pd.DataFrame]:
        """从 AkShare 获取数据，带指数退避重试"""
        config = AKSHARE_CONFIG
        max_retries = config["max_retries"]
        backoff_base = config["retry_backoff"]
        max_delay = config["max_retry_delay"]
        
        for retry in range(max_retries):
            try:
                self._apply_delay_akshare()
                df = self._get_fund_from_akshare(fund_code, start_date, end_date)
                if df is not None and not df.empty:
                    if retry > 0:
                        logger.info(f"AkShare {fund_code} 重试 {retry} 次后成功")
                    return df
            except Exception as e:
                error_type = self._get_error_type(str(e))
                if retry < max_retries - 1:
                    delay = min(backoff_base ** retry + random.uniform(0, 1), max_delay)
                    logger.warning(
                        f"AkShare 获取 {fund_code} 失败 (尝试 {retry+1}/{max_retries}): "
                        f"{error_type}, {delay:.1f}秒后重试..."
                    )
                    time.sleep(delay)
                else:
                    logger.error(f"AkShare {fund_code} 重试 {max_retries} 次后仍失败: {error_type}")
        
        return None

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

    def _apply_delay_akshare(self):
        """AkShare 专用请求延时"""
        delay = AKSHARE_CONFIG["request_delay"] + random.uniform(0, 0.3)
        time.sleep(delay)

    def _save_to_database(self, fund_code: str, df: pd.DataFrame, source: str, 
                          start_date: str = None, end_date: str = None):
        """保存数据到本地数据库"""
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

    def _get_fund_from_akshare(self, fund_code: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
        """从 akshare 获取数据"""
        start_dt = datetime.strptime(start_date, '%Y%m%d')
        end_dt = datetime.strptime(end_date, '%Y%m%d')
        
        for retry in range(self.max_retries):
            try:
                self._apply_delay()
                
                if fund_code.startswith('5'):
                    df = ak.fund_etf_hist_em(symbol=fund_code)
                else:
                    df = ak.stock_zh_a_hist(symbol=fund_code, start_date=start_date, end_date=end_date, adjust="qfq")
                
                if df is None or df.empty:
                    continue

                df['日期'] = pd.to_datetime(df['日期'], errors='coerce')
                df = df.dropna(subset=['日期'])
                df = df[df['日期'] >= start_dt]
                df = df[df['日期'] <= end_dt]

                if df.empty:
                    continue

                df['nav'] = pd.to_numeric(df['收盘'], errors='coerce')
                df = df.dropna(subset=['nav'])
                df = df[df['nav'] > 0]

                result = pd.DataFrame()
                result['date'] = df['日期'].dt.strftime('%Y%m%d')
                result['nav'] = df['nav']
                result['accum_nav'] = df['nav']
                
                for col, name in [('开盘', 'open'), ('最高', 'high'), ('最低', 'low')]:
                    if col in df.columns:
                        result[name] = pd.to_numeric(df[col], errors='coerce')
                    else:
                        result[name] = df['nav']

                return result.dropna(subset=['nav']).sort_values('date').reset_index(drop=True)
                
            except Exception as e:
                logger.warning(f"akshare 获取失败 (retry {retry+1}): {e}")
                time.sleep(1)
        
        return None

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
        
        try:
            if self.current_source == "akshare":
                df = ak.stock_info_a_code_name()
                if df is not None:
                    row = df[df['code'] == fund_code]
                    if not row.empty:
                        return row.iloc[0]['name']
        except:
            pass
        
        return fund_code

    def sync_stock_list(self, source: str = "akshare") -> int:
        """同步股票列表"""
        if source == "akshare":
            sync = AkshareSync()
            return sync.sync_stock_list()
        else:
            sync = TushareSync()
            return sync.sync_all_stocks().get("stocks", 0) + sync.sync_all_stocks().get("etfs", 0)

    def sync_daily_kline(self, fund_code: str, source: str = None) -> int:
        """同步日线数据"""
        if source is None:
            source = self.current_source
            
        if source == "akshare":
            sync = AkshareSync()
            return sync.sync_daily_kline(fund_code)
        else:
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
