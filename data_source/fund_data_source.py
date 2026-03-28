# -*- coding: utf-8 -*-
"""
统一数据源接口
支持：MySQL数据库(缓存) -> Redis(热缓存) -> tushare(原始数据)
"""

import logging
import pandas as pd
from datetime import datetime
from typing import Optional, List

import tushare as ts
import akshare as ak
import baostock as bs
from sqlalchemy import text

from data_source.config import (
    DATA_SOURCE, TU_SHARE_TOKEN, REQUEST_DELAY, MAX_RETRIES,
    AVAILABLE_SOURCES
)
from data_source.db.connection import get_db_session
from data_source.db.models import Stock, DailyKline
from data_source.cache import get_cache, CacheKeys
from data_source.sync import TushareSync

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class FundDataSource:
    """统一的数据源接口，支持多数据源切换和缓存"""

    def __init__(self, preferred_source: Optional[str] = None, use_cache: bool = True):
        self.current_source = preferred_source or DATA_SOURCE
        self.request_delay = REQUEST_DELAY
        self.max_retries = MAX_RETRIES
        self.use_cache = use_cache
        self.cache = get_cache()
        self._init_tushare()
        self._db_available = self._check_db()

    def _check_db(self) -> bool:
        """检查数据库是否可用"""
        try:
            with get_db_session() as session:
                session.execute(text("SELECT 1"))
            return True
        except Exception as e:
            logger.warning(f"数据库不可用: {e}")
            return False

    def _apply_delay(self):
        """请求延时，防止触发频率限制"""
        if self.request_delay > 0:
            import time
            time.sleep(self.request_delay)

    def _init_tushare(self):
        """初始化tushare"""
        try:
            ts.set_token(TU_SHARE_TOKEN)
            self.pro = ts.pro_api()
            logger.info("Tushare initialized successfully")
        except Exception as e:
            logger.warning(f"Tushare init failed: {e}")
            self.pro = None

    def get_fund_nav(self, fund_code: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
        """
        获取基金净值数据
        优先级：Redis缓存 -> MySQL数据库 -> tushare API
        """
        start_str = start_date.replace("-", "")
        end_str = end_date.replace("-", "")

        cache_key = CacheKeys.kline_range(fund_code, start_str, end_str)
        if self.use_cache and self.cache.is_available():
            cached_data = self.cache.get(cache_key)
            if cached_data is not None:
                logger.info(f"缓存命中: {fund_code} {start_str}-{end_str}")
                df = pd.DataFrame(cached_data)
                if not df.empty:
                    df['date'] = df['date'].astype(str)
                    return df

        if self._db_available:
            db_data = self._get_from_db(fund_code, start_str, end_str)
            if db_data is not None and not db_data.empty:
                logger.info(f"数据库命中: {fund_code} {len(db_data)}条")
                if self.use_cache and self.cache.is_available():
                    self.cache.set(cache_key, db_data.to_dict('records'))
                return db_data

        data = None
        sources = self._get_source_priority()
        for source in sources:
            try:
                if source == "tushare":
                    data = self._get_fund_from_tushare(fund_code, start_str, end_str)
                elif source == "akshare":
                    data = self._get_fund_from_akshare(fund_code, start_str, end_str)
                elif source == "baostock":
                    data = self._get_fund_from_baostock(fund_code, start_str, end_str)

                if data is not None and not data.empty:
                    logger.info(f"从 {source} 获取数据: {len(data)} 条")
                    data['source'] = source

                    if self._db_available:
                        self._save_to_db(fund_code, data)

                    if self.use_cache and self.cache.is_available():
                        self.cache.set(cache_key, data.to_dict('records'))

                    return data
            except Exception as e:
                logger.warning(f"{source} failed for {fund_code}: {e}")
                continue

        return None

    def _get_from_db(self, fund_code: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
        """从数据库获取数据"""
        try:
            start_dt = datetime.strptime(start_date, '%Y%m%d').date()
            end_dt = datetime.strptime(end_date, '%Y%m%d').date()

            with get_db_session() as session:
                klines = session.query(DailyKline).filter(
                    DailyKline.code == fund_code,
                    DailyKline.trade_date >= start_dt,
                    DailyKline.trade_date <= end_dt
                ).order_by(DailyKline.trade_date).all()

                if klines:
                    data = []
                    for k in klines:
                        data.append({
                            'date': k.trade_date.strftime('%Y%m%d'),
                            'nav': float(k.close) if k.close else 0,
                            'accum_nav': float(k.adj_close) if k.adj_close else float(k.close) if k.close else 0,
                            'open': float(k.open) if k.open else 0,
                            'high': float(k.high) if k.high else 0,
                            'low': float(k.low) if k.low else 0,
                        })
                    return pd.DataFrame(data)
        except Exception as e:
            logger.warning(f"数据库查询失败: {e}")
        return None

    def _save_to_db(self, fund_code: str, df: pd.DataFrame):
        """保存数据到数据库"""
        try:
            with get_db_session() as session:
                for _, row in df.iterrows():
                    trade_date = datetime.strptime(str(row['date']), '%Y%m%d').date()

                    existing = session.query(DailyKline).filter(
                        DailyKline.code == fund_code,
                        DailyKline.trade_date == trade_date
                    ).first()

                    if existing:
                        continue

                    kline = DailyKline(
                        code=fund_code,
                        trade_date=trade_date,
                        open=row.get('open', 0),
                        high=row.get('high', 0),
                        low=row.get('low', 0),
                        close=row.get('nav', 0),
                        volume=0,
                        amount=0,
                        adj_close=row.get('accum_nav', row.get('nav', 0)),
                    )
                    session.add(kline)
            logger.info(f"已保存 {fund_code} {len(df)} 条数据到数据库")
        except Exception as e:
            logger.warning(f"保存数据库失败: {e}")

    def _get_source_priority(self) -> List[str]:
        """获取数据源优先级"""
        if self.current_source == "auto":
            return ["tushare", "akshare", "baostock"]
        return [self.current_source]

    def _get_fund_from_tushare(self, fund_code: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
        """从tushare获取基金/ETF数据"""
        if self.pro is None:
            return None

        for retry in range(self.max_retries):
            try:
                self._apply_delay()
                df = self.pro.fund_nav(ts_code=f"{fund_code}.OF", start_date=start_date, end_date=end_date)
                if df is not None and not df.empty:
                    df = df.rename(columns={
                        'nav_date': 'date',
                        'nav': 'nav',
                        'accum_nav': 'accum_nav',
                        'fund_name': 'name'
                    })
                    df = df[['date', 'nav', 'accum_nav', 'name']].sort_values('date')
                    return df
            except Exception as e:
                logger.warning(f"Tushare fund_nav error (retry {retry+1}): {e}")

        for retry in range(self.max_retries):
            for exchange in ['SH', 'SZ']:
                try:
                    self._apply_delay()
                    logger.info(f"Trying tushare daily {fund_code}.{exchange}")
                    df = self.pro.daily(ts_code=f"{fund_code}.{exchange}", start_date=start_date, end_date=end_date, adj='hfq')

                    if df is not None and not df.empty:
                        df = df.rename(columns={
                            'trade_date': 'date',
                            'close': 'nav'
                        })
                        df = df[['date', 'open', 'high', 'low', 'nav']].sort_values('date')
                        df['accum_nav'] = df['nav']
                        return df
                except Exception as e:
                    logger.warning(f"Tushare daily error (retry {retry+1}): {e}")

        return None

    def _get_fund_from_akshare(self, fund_code: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
        """从akshare获取基金数据"""
        funcs_to_try = [
            ('stock_zh_a_hist_sina', {'symbol': fund_code}),
            ('fund_etf_hist_sina', {'symbol': fund_code}),
            ('fund_etf_hist_em', {'symbol': fund_code}),
        ]

        for retry in range(self.max_retries):
            for func_name, kwargs in funcs_to_try:
                try:
                    self._apply_delay()
                    logger.info(f"Trying ak.{func_name}({fund_code}) retry {retry+1}")
                    func = getattr(ak, func_name, None)
                    if func is None:
                        continue

                    df = func(**kwargs)

                    if df is not None and not df.empty:
                        logger.info(f"Got data from {func_name}")

                        for date_col in ['day', '日期', 'date']:
                            if date_col in df.columns:
                                df['day'] = pd.to_datetime(df[date_col])
                                break

                        for price_col in ['close', '收盘', 'close_x', '单位净值']:
                            if price_col in df.columns:
                                df['price'] = df[price_col]
                                break

                        start_dt = pd.to_datetime(start_date)
                        end_dt = pd.to_datetime(end_date)
                        df = df[(df['day'] >= start_dt) & (df['day'] <= end_dt)]

                        result = pd.DataFrame()
                        result['date'] = df['day'].dt.strftime('%Y%m%d')
                        result['nav'] = df['price']
                        result['accum_nav'] = df['price']

                        logger.info(f"Got {len(result)} rows")
                        return result.sort_values('date')
                except Exception as e:
                    logger.warning(f"ak.{func_name} error: {e}")
        return None

    def _get_fund_from_baostock(self, fund_code: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
        """从baostock获取基金数据"""
        try:
            bs.login()
            if '-' in start_date:
                start_str = start_date
                end_str = end_date
            else:
                start_str = f"{start_date[:4]}-{start_date[4:6]}-{start_date[6:]}"
                end_str = f"{end_date[:4]}-{end_date[4:6]}-{end_date[6:]}"

            code_formats = [f"of.{fund_code}", f"sh.{fund_code}", f"sz.{fund_code}"]

            for retry in range(self.max_retries):
                for code in code_formats:
                    try:
                        self._apply_delay()
                        logger.info(f"Trying Baostock with {code}")
                        rs = bs.query_history_k_data_plus(
                            code,
                            "date,open,high,low,close",
                            start_date=start_str,
                            end_date=end_str,
                            frequency="d",
                            adjustflag="2"
                        )

                        logger.info(f"Baostock result: error_code={rs.error_code}")

                        if rs.error_code == '0':
                            data_list = []
                            while rs.error_code == '0' and rs.next():
                                data_list.append(rs.get_row_data())

                            if data_list:
                                df = pd.DataFrame(data_list, columns=rs.fields)
                                logger.info(f"Got {len(df)} rows from Baostock")
                                df = df.rename(columns={'close': 'nav'})
                                df['accum_nav'] = df['nav']
                                bs.logout()
                                return df[['date', 'nav', 'accum_nav']]
                        else:
                            logger.warning(f"Baostock query failed: {rs.error_msg}")
                    except Exception as e:
                        logger.warning(f"Baostock error for {code}: {e}")

            bs.logout()
        except Exception as e:
            logger.warning(f"Baostock fund error: {e}")
        return None

    def get_stock_info(self, stock_code: str) -> Optional[dict]:
        """获取股票/ETF基本信息"""
        cache_key = CacheKeys.stock_info(stock_code)
        if self.use_cache and self.cache.is_available():
            cached = self.cache.get(cache_key)
            if cached:
                return cached

        stock_info = None
        if self._db_available:
            stock_info = self._get_stock_from_db(stock_code)

        if stock_info is None and self.pro:
            stock_info = self._get_stock_info_tushare(stock_code)

        if stock_info is None:
            stock_info = self._get_stock_info_akshare(stock_code)

        if stock_info and self.use_cache and self.cache.is_available():
            self.cache.set(cache_key, stock_info, expire=86400)

        return stock_info

    def _get_stock_from_db(self, stock_code: str) -> Optional[dict]:
        """从数据库获取股票信息"""
        try:
            with get_db_session() as session:
                stock = session.query(Stock).filter(Stock.code == stock_code).first()
                if stock:
                    return {
                        'code': stock.code,
                        'name': stock.name,
                        'market': stock.market,
                        'industry': stock.industry,
                        'type': stock.stock_type,
                    }
        except Exception as e:
            logger.warning(f"数据库查询股票信息失败: {e}")
        return None

    def _get_stock_info_tushare(self, stock_code: str) -> Optional[dict]:
        """从tushare获取股票信息"""
        if self.pro is None:
            return None

        exchange = "SH" if stock_code.startswith(("5", "6", "9")) else "SZ"
        ts_code = f"{stock_code}.{exchange}"

        try:
            self._apply_delay()
            df = self.pro.stock_basic(ts_code=ts_code, list_status='L')
            if df is not None and not df.empty:
                row = df.iloc[0]
                return {
                    'code': stock_code,
                    'name': row.get('name', stock_code),
                    'market': 'SH' if exchange == 'SH' else 'SZ',
                    'industry': row.get('industry', ''),
                }
        except Exception as e:
            logger.warning(f"Tushare stock_basic error: {e}")

        try:
            self._apply_delay()
            df = self.pro.fund_basic(market='E', ts_code=ts_code)
            if df is not None and not df.empty:
                row = df.iloc[0]
                return {
                    'code': stock_code,
                    'name': row.get('name', stock_code),
                    'type': 'ETF',
                    'market': 'SH' if exchange == 'SH' else 'SZ',
                }
        except Exception as e:
            logger.warning(f"Tushare fund_basic error: {e}")

        return None

    def _get_stock_info_akshare(self, stock_code: str) -> Optional[dict]:
        """从akshare获取股票信息"""
        try:
            self._apply_delay()
            info = ak.stock_individual_info_em(symbol=stock_code)
            if info is not None and not info.empty:
                info_dict = dict(zip(info['item'], info['value']))
                return {
                    'code': stock_code,
                    'name': info_dict.get('股票简称', stock_code),
                    'market': 'SH' if stock_code.startswith(('5', '6', '9')) else 'SZ',
                    'industry': info_dict.get('行业', ''),
                }
        except Exception as e:
            logger.warning(f"AkShare stock_info error: {e}")
        return None

    def verify_stock(self, stock_code: str) -> tuple[bool, Optional[str]]:
        """验证股票代码是否有效"""
        info = self.get_stock_info(stock_code)
        if info:
            return True, info.get('name', stock_code)
        return False, None

    def set_source(self, source: str):
        """设置数据源"""
        self.current_source = source
        logger.info(f"Data source changed to: {source}")

    def get_cache_stats(self) -> dict:
        """获取缓存统计"""
        return self.cache.get_stats()


FUND_CODES = {
    '沪深300ETF': '510300',
    '上证50ETF': '510050',
    '创业板ETF': '159915',
    '中证500ETF': '510500',
    '科创50ETF': '588000',
    '纯债基金': '161039',
    '中债ETF': '511010',
    '黄金ETF': '518880',
    '易方达黄金ETF': '159934',
}


def get_fund_data(fund_code: str, start_date: str, end_date: str, source: str = None) -> Optional[pd.DataFrame]:
    """便捷函数：获取基金数据"""
    ds = FundDataSource(preferred_source=source)
    return ds.get_fund_nav(fund_code, start_date, end_date)


if __name__ == "__main__":
    ds = FundDataSource(DATA_SOURCE)
    df = ds.get_fund_nav("510300", "20240101", "20240630")
    print(df)
