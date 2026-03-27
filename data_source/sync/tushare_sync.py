# -*- coding: utf-8 -*-
"""
tushare 数据同步服务
"""

import logging
import time
from datetime import datetime, timedelta
from typing import Optional, List, Dict

import tushare as ts
import pandas as pd

from data_source.config import TU_SHARE_TOKEN, REQUEST_DELAY, SYNC_CONFIG
from data_source.db.connection import get_db_session
from data_source.db.models import Stock, DailyKline, Income, FinaIndicator, SyncLog
from data_source.cache import get_cache, CacheKeys

logger = logging.getLogger(__name__)


class TushareSync:
    """tushare 数据同步器"""

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

    def sync_all_stocks(self) -> Dict[str, int]:
        """同步所有股票列表"""
        result = {"stocks": 0, "etfs": 0}
        
        try:
            self._apply_delay()
            
            df = self.pro.stock_basic(list_status='L')
            if df is not None and not df.empty:
                stocks = []
                for _, row in df.iterrows():
                    ts_code = row['ts_code']
                    code = ts_code.split('.')[0]
                    market = ts_code.split('.')[1]
                    
                    stock = Stock(
                        code=code,
                        name=row['name'],
                        market=market,
                        industry=row.get('industry', ''),
                        list_date=row.get('list_date'),
                        stock_type='股票'
                    )
                    stocks.append(stock)
                
                with get_db_session() as session:
                    for stock in stocks:
                        existing = session.query(Stock).filter(Stock.code == stock.code).first()
                        if existing:
                            existing.name = stock.name
                            existing.industry = stock.industry
                        else:
                            session.add(stock)
                    result["stocks"] = len(stocks)
                logger.info(f"同步股票列表: {result['stocks']} 只")

            self._apply_delay()
            
            df_etf = self.pro.fund_basic(market='E')
            if df_etf is not None and not df_etf.empty:
                etfs = []
                for _, row in df_etf.iterrows():
                    ts_code = row['ts_code']
                    code = ts_code.split('.')[0]
                    market = ts_code.split('.')[1]
                    
                    etf = Stock(
                        code=code,
                        name=row['name'],
                        market=market,
                        list_date=row.get('found_date'),
                        stock_type='ETF'
                    )
                    etfs.append(etf)
                
                with get_db_session() as session:
                    for etf in etfs:
                        existing = session.query(Stock).filter(Stock.code == etf.code).first()
                        if existing:
                            existing.name = etf.name
                            existing.stock_type = 'ETF'
                        else:
                            session.add(etf)
                    result["etfs"] = len(etfs)
                logger.info(f"同步ETF列表: {result['etfs']} 只")
                
        except Exception as e:
            logger.error(f"同步股票列表失败: {e}")
        
        self.cache.delete(CacheKeys.stock_list())
        return result

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
        
        try:
            self._apply_delay()
            df = self.pro.daily(ts_code=ts_code, start_date=start_date, end_date=end_date, adj='hfq')
            
            if df is not None and not df.empty:
                df = df.rename(columns={
                    'trade_date': 'trade_date_str',
                    'pct_chg': 'pct_chg'
                })
                
                klines = []
                for _, row in df.iterrows():
                    trade_date = datetime.strptime(row['trade_date_str'], '%Y%m%d').date()
                    
                    kline = DailyKline(
                        code=code,
                        trade_date=trade_date,
                        open=row['open'],
                        high=row['high'],
                        low=row['low'],
                        close=row['close'],
                        volume=row['vol'],
                        amount=row.get('amount', 0),
                        adj_close=row['close'],
                        turn=row.get('turnover', 0),
                        pct_chg=row['pct_chg'] / 100 if row.get('pct_chg') else 0
                    )
                    klines.append(kline)
                
                with get_db_session() as session:
                    for kline in klines:
                        existing = session.query(DailyKline).filter(
                            DailyKline.code == kline.code,
                            DailyKline.trade_date == kline.trade_date
                        ).first()
                        if existing:
                            existing.open = kline.open
                            existing.high = kline.high
                            existing.low = kline.low
                            existing.close = kline.close
                            existing.volume = kline.volume
                            existing.adj_close = kline.adj_close
                        else:
                            session.add(kline)
                    records = len(klines)
                
                cache_key = CacheKeys.kline_range(code, start_date, end_date)
                self.cache.delete(cache_key)
                
                logger.info(f"同步 {code} 日线数据: {records} 条")
            else:
                logger.warning(f"未获取到 {code} 的日线数据")
                
        except Exception as e:
            logger.error(f"同步 {code} 日线数据失败: {e}")
        
        return records

    def sync_income(self, code: str) -> int:
        """同步利润表数据"""
        if self.pro is None:
            return 0
        
        records = 0
        exchange = "SH" if code.startswith(("5", "6", "9")) else "SZ"
        ts_code = f"{code}.{exchange}"
        
        try:
            self._apply_delay()
            df = self.pro.income(ts_code=ts_code)
            
            if df is not None and not df.empty:
                incomes = []
                for _, row in df.iterrows():
                    income = Income(
                        code=code,
                        ann_date=row.get('ann_date'),
                        end_date=row.get('end_date'),
                        report_type=row.get('report_type'),
                        total_revenue=row.get('total_revenue'),
                        oper_profit=row.get('oper_profit'),
                        net_profit=row.get('net_profit'),
                        total_revenue_yoy=row.get('total_revenue_yoy'),
                        net_profit_yoy=row.get('net_profit_yoy')
                    )
                    incomes.append(income)
                
                with get_db_session() as session:
                    for income in incomes:
                        existing = session.query(Income).filter(
                            Income.code == income.code,
                            Income.end_date == income.end_date,
                            Income.report_type == income.report_type
                        ).first()
                        if existing:
                            existing.total_revenue = income.total_revenue
                            existing.oper_profit = income.oper_profit
                            existing.net_profit = income.net_profit
                        else:
                            session.add(income)
                    records = len(incomes)
                
                logger.info(f"同步 {code} 利润表: {records} 条")
                
        except Exception as e:
            logger.warning(f"同步 {code} 利润表失败: {e}")
        
        return records

    def sync_fina_indicator(self, code: str) -> int:
        """同步主要财务指标"""
        if self.pro is None:
            return 0
        
        records = 0
        exchange = "SH" if code.startswith(("5", "6", "9")) else "SZ"
        ts_code = f"{code}.{exchange}"
        
        try:
            self._apply_delay()
            df = self.pro.fina_indicator(ts_code=ts_code)
            
            if df is not None and not df.empty:
                indicators = []
                for _, row in df.iterrows():
                    indicator = FinaIndicator(
                        code=code,
                        ann_date=row.get('ann_date'),
                        end_date=row.get('end_date'),
                        roe=row.get('roe'),
                        net_profit_margin=row.get('netprofit_margin'),
                        gross_profit_margin=row.get('gross_margin'),
                        debt_to_assets=row.get('debt_to_assets'),
                        current_ratio=row.get('current_ratio'),
                        quick_ratio=row.get('quick_ratio'),
                        pe_ttm=row.get('pe'),
                        pb=row.get('pb'),
                        ps_ttm=row.get('ps')
                    )
                    indicators.append(indicator)
                
                with get_db_session() as session:
                    for indicator in indicators:
                        existing = session.query(FinaIndicator).filter(
                            FinaIndicator.code == indicator.code,
                            FinaIndicator.end_date == indicator.end_date
                        ).first()
                        if existing:
                            existing.roe = indicator.roe
                            existing.pe_ttm = indicator.pe_ttm
                            existing.pb = indicator.pb
                        else:
                            session.add(indicator)
                    records = len(indicators)
                
                logger.info(f"同步 {code} 财务指标: {records} 条")
                
        except Exception as e:
            logger.warning(f"同步 {code} 财务指标失败: {e}")
        
        return records

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


def sync_all_stocks() -> Dict[str, int]:
    """便捷函数：同步所有股票"""
    sync = TushareSync()
    return sync.sync_all_stocks()


def sync_stock_daily(code: str, start_date: str = None) -> int:
    """便捷函数：同步单只股票日线"""
    sync = TushareSync()
    return sync.sync_daily_kline(code, start_date)
