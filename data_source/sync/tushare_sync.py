# -*- coding: utf-8 -*-
"""
tushare 数据同步服务
优化版：按日期批量获取数据，效率更高
"""

import logging
import time
from datetime import datetime, timedelta
from typing import Optional, List, Dict
from concurrent.futures import ThreadPoolExecutor, as_completed

import tushare as ts
import pandas as pd
from sqlalchemy import text

from data_source.config import TU_SHARE_TOKEN, REQUEST_DELAY, SYNC_CONFIG
from data_source.db.connection import get_db_session, get_engine
from data_source.db.models import Stock, DailyKline, Income, FinaIndicator, SyncLog
from data_source.cache import get_cache, CacheKeys

logger = logging.getLogger(__name__)


class TushareSync:
    """tushare 数据同步器（优化版）"""

    def __init__(self):
        self.token = TU_SHARE_TOKEN
        self.pro = None
        self.cache = get_cache()
        self._init_pro()

    def _init_pro(self):
        """初始化 tushare pro"""
        try:
            ts.set_token(self.token)
            self.pro = ts.pro_api()
            logger.info("tushare pro API 初始化成功")
        except Exception as e:
            logger.error(f"tushare pro API 初始化失败: {e}")

    def _apply_delay(self):
        """请求延时"""
        if REQUEST_DELAY > 0:
            time.sleep(REQUEST_DELAY)

    def _retry_get(self, func, *args, max_retries: int = 3, **kwargs):
        """带重试的获取"""
        for i in range(max_retries):
            try:
                self._apply_delay()
                return func(*args, **kwargs)
            except Exception as e:
                if i < max_retries - 1:
                    time.sleep(1)
                    logger.warning(f"重试 {i+1}: {e}")
                else:
                    logger.error(f"获取失败: {e}")
                    return None

    def get_trade_cal(self, start_date: str, end_date: str) -> List[str]:
        """获取交易日历"""
        df = self._retry_get(self.pro.trade_cal, 
                           exchange='SSE', 
                           start_date=start_date, 
                           end_date=end_date,
                           is_open='1')
        if df is not None and not df.empty:
            return df['cal_date'].tolist()
        return []

    def sync_all_stocks(self) -> Dict[str, int]:
        """同步所有股票列表"""
        result = {"stocks": 0, "etfs": 0}
        
        try:
            df = self._retry_get(self.pro.stock_basic, list_status='L')
            if df is not None and not df.empty:
                stocks_data = []
                for _, row in df.iterrows():
                    ts_code = row['ts_code']
                    code = ts_code.split('.')[0]
                    market = ts_code.split('.')[1]
                    stocks_data.append({
                        'code': code,
                        'name': row['name'],
                        'market': market,
                        'industry': row.get('industry', ''),
                        'list_date': row.get('list_date'),
                        'stock_type': '股票'
                    })
                
                df_stocks = pd.DataFrame(stocks_data)
                df_stocks.to_sql('stocks', get_engine(), if_exists='replace', index=False)
                result["stocks"] = len(df_stocks)
                logger.info(f"同步股票列表: {result['stocks']} 只")

            df_etf = self._retry_get(self.pro.fund_basic, market='E')
            if df_etf is not None and not df_etf.empty:
                etfs_data = []
                for _, row in df_etf.iterrows():
                    ts_code = row['ts_code']
                    code = ts_code.split('.')[0]
                    market = ts_code.split('.')[1]
                    etfs_data.append({
                        'code': code,
                        'name': row['name'],
                        'market': market,
                        'list_date': row.get('found_date'),
                        'stock_type': 'ETF'
                    })
                
                df_etfs = pd.DataFrame(etfs_data)
                for _, row in df_etfs.iterrows():
                    with get_db_session() as session:
                        existing = session.query(Stock).filter(Stock.code == row['code']).first()
                        if existing:
                            existing.name = row['name']
                            existing.stock_type = 'ETF'
                        else:
                            stock = Stock(
                                code=row['code'],
                                name=row['name'],
                                market=row['market'],
                                list_date=row.get('list_date'),
                                stock_type='ETF'
                            )
                            session.add(stock)
                result["etfs"] = len(df_etfs)
                logger.info(f"同步ETF列表: {result['etfs']} 只")
                
        except Exception as e:
            logger.error(f"同步股票列表失败: {e}")
        
        self.cache.delete(CacheKeys.stock_list())
        return result

    def sync_daily_by_date(self, trade_date: str) -> int:
        """按日期获取所有股票的日线数据（高效方式）"""
        df = self._retry_get(self.pro.daily, trade_date=trade_date)
        if df is None or df.empty:
            return 0
        
        records = 0
        klines_data = []
        
        for _, row in df.iterrows():
            ts_code = row['ts_code']
            code = ts_code.split('.')[0]
            trade_date_dt = datetime.strptime(str(row['trade_date']), '%Y%m%d').date()
            
            klines_data.append({
                'code': code,
                'trade_date': trade_date_dt,
                'open': row.get('open', 0),
                'high': row.get('high', 0),
                'low': row.get('low', 0),
                'close': row.get('close', 0),
                'volume': row.get('vol', 0),
                'amount': row.get('amount', 0),
                'adj_close': row.get('close', 0),
                'turn': row.get('turnover', 0),
                'pct_chg': row.get('pct_chg', 0) / 100 if row.get('pct_chg') else 0
            })
        
        if klines_data:
            df_kline = pd.DataFrame(klines_data)
            df_kline.to_sql('daily_kline', get_engine(), if_exists='append', index=False, chunksize=5000)
            records = len(df_kline)
            
            for code in df_kline['code'].unique():
                cache_key = CacheKeys.kline_range(code, trade_date, trade_date)
                self.cache.delete(cache_key)
        
        return records

    def sync_daily_kline(self, code: str, start_date: str = None, end_date: str = None) -> int:
        """同步单只股票的日线数据"""
        if self.pro is None:
            logger.error("tushare pro API 未初始化")
            return 0
        
        records = 0
        exchange = "SH" if code.startswith(("5", "6", "9")) else "SZ"
        ts_code = f"{code}.{exchange}"
        
        if end_date is None:
            end_date = datetime.now().strftime('%Y%m%d')
        if start_date is None:
            start_date = "20000101"
        
        df = self._retry_get(self.pro.daily, ts_code=ts_code, start_date=start_date, end_date=end_date, adj='hfq')
        
        if df is not None and not df.empty:
            klines_data = []
            for _, row in df.iterrows():
                trade_date_dt = datetime.strptime(str(row['trade_date']), '%Y%m%d').date()
                klines_data.append({
                    'code': code,
                    'trade_date': trade_date_dt,
                    'open': row.get('open', 0),
                    'high': row.get('high', 0),
                    'low': row.get('low', 0),
                    'close': row.get('close', 0),
                    'volume': row.get('vol', 0),
                    'amount': row.get('amount', 0),
                    'adj_close': row.get('close', 0),
                    'turn': row.get('turnover', 0),
                    'pct_chg': row.get('pct_chg', 0) / 100 if row.get('pct_chg') else 0
                })
            
            df_kline = pd.DataFrame(klines_data)
            df_kline.to_sql('daily_kline', get_engine(), if_exists='append', index=False, chunksize=5000)
            records = len(df_kline)
            
            cache_key = CacheKeys.kline_range(code, start_date, end_date)
            self.cache.delete(cache_key)
            logger.info(f"同步 {code} 日线数据: {records} 条")
        else:
            logger.warning(f"未获取到 {code} 的日线数据")
        
        return records

    def sync_daily_date_range(self, start_date: str, end_date: str, workers: int = 5) -> Dict[str, int]:
        """按日期范围批量同步所有股票日线数据（推荐方式）"""
        logger.info(f"开始批量同步: {start_date} ~ {end_date}")
        
        trade_dates = self.get_trade_cal(start_date, end_date)
        if not trade_dates:
            logger.warning("未获取到交易日历")
            return {"dates": 0, "records": 0}
        
        total_records = 0
        total_dates = len(trade_dates)
        
        for i, date in enumerate(trade_dates, 1):
            try:
                records = self.sync_daily_by_date(date)
                total_records += records
                if i % 50 == 0:
                    logger.info(f"进度: {i}/{total_dates} ({i*100//total_dates}%) - {records} 条")
            except Exception as e:
                logger.warning(f"同步 {date} 失败: {e}")
        
        logger.info(f"批量同步完成: {total_dates} 天, {total_records} 条记录")
        return {"dates": total_dates, "records": total_records}

    def sync_income(self, code: str) -> int:
        """同步利润表数据"""
        if self.pro is None:
            return 0
        
        exchange = "SH" if code.startswith(("5", "6", "9")) else "SZ"
        ts_code = f"{code}.{exchange}"
        
        df = self._retry_get(self.pro.income, ts_code=ts_code)
        
        if df is not None and not df.empty:
            income_data = []
            for _, row in df.iterrows():
                income_data.append({
                    'code': code,
                    'ann_date': row.get('ann_date'),
                    'end_date': row.get('end_date'),
                    'report_type': row.get('report_type'),
                    'total_revenue': row.get('total_revenue'),
                    'oper_profit': row.get('oper_profit'),
                    'net_profit': row.get('net_profit'),
                    'total_revenue_yoy': row.get('total_revenue_yoy'),
                    'net_profit_yoy': row.get('net_profit_yoy'),
                })
            
            df_income = pd.DataFrame(income_data)
            df_income.to_sql('income', get_engine(), if_exists='append', index=False, chunksize=5000)
            logger.info(f"同步 {code} 利润表: {len(df_income)} 条")
            return len(df_income)
        
        return 0

    def sync_fina_indicator(self, code: str) -> int:
        """同步主要财务指标"""
        if self.pro is None:
            return 0
        
        exchange = "SH" if code.startswith(("5", "6", "9")) else "SZ"
        ts_code = f"{code}.{exchange}"
        
        df = self._retry_get(self.pro.fina_indicator, ts_code=ts_code)
        
        if df is not None and not df.empty:
            indicator_data = []
            for _, row in df.iterrows():
                indicator_data.append({
                    'code': code,
                    'ann_date': row.get('ann_date'),
                    'end_date': row.get('end_date'),
                    'roe': row.get('roe'),
                    'net_profit_margin': row.get('netprofit_margin'),
                    'gross_profit_margin': row.get('gross_margin'),
                    'debt_to_assets': row.get('debt_to_assets'),
                    'current_ratio': row.get('current_ratio'),
                    'quick_ratio': row.get('quick_ratio'),
                    'pe_ttm': row.get('pe'),
                    'pb': row.get('pb'),
                    'ps_ttm': row.get('ps'),
                })
            
            df_indicator = pd.DataFrame(indicator_data)
            df_indicator.to_sql('fina_indicator', get_engine(), if_exists='append', index=False, chunksize=5000)
            logger.info(f"同步 {code} 财务指标: {len(df_indicator)} 条")
            return len(df_indicator)
        
        return 0

    def get_latest_date(self, code: str) -> Optional[str]:
        """获取数据库中最新日期"""
        try:
            with get_db_session() as session:
                latest = session.query(DailyKline).filter(
                    DailyKline.code == code
                ).order_by(DailyKline.trade_date.desc()).first()
                if latest:
                    return str(latest.trade_date)
        except Exception as e:
            logger.warning(f"获取 {code} 最新日期失败: {e}")
        return None

    def get_stock_count(self) -> int:
        """获取数据库中股票数量"""
        try:
            with get_db_session() as session:
                return session.query(Stock).count()
        except:
            return 0

    def get_kline_count(self) -> int:
        """获取数据库中日线数据数量"""
        try:
            with get_db_session() as session:
                return session.query(DailyKline).count()
        except:
            return 0


def sync_all_stocks() -> Dict[str, int]:
    """便捷函数：同步所有股票"""
    sync = TushareSync()
    return sync.sync_all_stocks()


def sync_stock_daily(code: str, start_date: str = None) -> int:
    """便捷函数：同步单只股票日线"""
    sync = TushareSync()
    return sync.sync_daily_kline(code, start_date)


def sync_daily_by_date(trade_date: str) -> int:
    """便捷函数：按日期同步所有股票"""
    sync = TushareSync()
    return sync.sync_daily_by_date(trade_date)
