# -*- coding: utf-8 -*-
"""
akshare 数据同步服务
将 akshare 数据同步到本地数据库（daily_kline_akshare 表）
"""

import logging
import time
import random
from datetime import datetime, timedelta
from typing import Optional, List, Dict

import akshare as ak
import pandas as pd

from data_source.config import REQUEST_DELAY, SYNC_CONFIG, ENABLE_MYSQL, AKSHARE_CONFIG
from data_source.cache import get_cache, CacheKeys

logger = logging.getLogger(__name__)


class AkshareSync:
    """akshare 数据同步器"""

    def __init__(self):
        self.cache = get_cache() if ENABLE_MYSQL else None

    def _apply_delay(self):
        """请求延时"""
        delay = AKSHARE_CONFIG.get("request_delay", 1.0) + random.uniform(0, 0.3)
        time.sleep(delay)

    def _retry_with_backoff(self, func, *args, **kwargs):
        """带指数退避的重试装饰器"""
        config = AKSHARE_CONFIG
        max_retries = config.get("max_retries", 5)
        backoff_base = config.get("retry_backoff", 2.0)
        max_delay = config.get("max_retry_delay", 60)
        
        last_exception = None
        for retry in range(max_retries):
            try:
                self._apply_delay()
                return func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                if retry < max_retries - 1:
                    delay = min(backoff_base ** retry + random.uniform(0, 1), max_delay)
                    logger.warning(f"重试 {retry+1}/{max_retries}, {delay:.1f}秒后重试... ({e})")
                    time.sleep(delay)
        
        logger.error(f"重试 {max_retries} 次后仍失败: {last_exception}")
        return None

    def sync_all_lists(self) -> dict:
        """同步所有列表（股票、ETF、债券、货币基金、指数等）"""
        results = {
            'stock': 0,
            'etf': 0,
            'bond': 0,
            'money_fund': 0,
            'fund': 0,
            'index': 0,
        }
        
        results['stock'] = self.sync_stock_list()
        results['etf'] = self.sync_etf_list()
        results['bond'] = self.sync_bond_list()
        results['money_fund'] = self.sync_money_fund_list()
        results['fund'] = self.sync_fund_list()
        results['index'] = self.sync_index_list()
        
        return results

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
        
        # 首先尝试 API 获取，如果失败则使用备用列表
        try:
            self._apply_delay()
            df = ak.fund_etf_spot_em()
            if df is not None and not df.empty:
                return self._save_etf_list(df)
        except Exception as e:
            logger.warning(f"ETF API 失败: {e}")
        
        # 使用备用列表
        logger.info("使用备用 ETF 列表...")
        return self._sync_etf_list_fallback()
    
    def _save_etf_list(self, df: pd.DataFrame) -> int:
        """保存 ETF 列表到数据库"""
        from data_source.db.connection import get_db_session
        from data_source.db.models import Stock

        added = 0
        with get_db_session() as session:
            for _, row in df.iterrows():
                code = str(row['代码']).zfill(6)
                name = str(row['名称'])
                
                existing = session.query(Stock).filter(Stock.code == code).first()
                if existing:
                    existing.name = name
                    existing.stock_type = 'ETF'
                    if code.startswith(('5', '1')):
                        existing.market = 'SH'
                    else:
                        existing.market = 'SZ'
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

    def _sync_etf_list_fallback(self) -> int:
        """备用 ETF 列表同步"""
        from data_source.db.connection import get_db_session
        from data_source.db.models import Stock

        etf_codes = [
            '510300', '510500', '510050', '159915', '512660', '512760',
            '515000', '512170', '512980', '510880', '159919', '510180',
            '512100', '512000', '512880', '159920', '513500', '513100',
            '588000', '588080', '159788', '588050', '159995', '515050',
            '159869', '159819', '159825', '512010', '512200', '512800',
            '512900', '159992', '159628', '511010', '511260', '515220',
            '159766', '159605', '515790', '159611',
        ]
        
        etf_names = {
            '510300': '沪深300ETF', '510500': '中证500ETF', '510050': '上证50ETF',
            '159915': '创业板ETF', '512660': '军工ETF', '512760': '芯片ETF',
            '515000': '科技ETF', '512170': '医疗ETF', '512980': '传媒ETF',
            '510880': '红利ETF', '159919': '深100ETF', '510180': '180ETF',
            '512100': '中证100ETF', '512000': '券商ETF', '512880': '证券ETF',
            '159920': '恒生ETF', '513500': '纳指ETF', '513100': '纳指ETF',
            '588000': '科创50ETF', '588080': '科创50ETF', '159788': '双创50ETF',
            '588050': '科创50ETF', '159995': '芯片ETF', '515050': '5GETF',
            '159869': '云计算ETF', '159819': '人工智能ETF', '159825': '农业ETF',
            '512010': '医药ETF', '512200': '房地产ETF', '512800': '银行ETF',
            '512900': '中证医疗ETF', '159992': '创新药ETF', '159628': '短债ETF',
            '511010': '国债ETF', '511260': '上海国企ETF', '515220': '煤炭ETF',
            '159766': '旅游ETF', '159605': '油气ETF', '515790': '光伏ETF',
            '159611': '电力ETF',
        }
        
        added = 0
        try:
            with get_db_session() as session:
                for code in etf_codes:
                    code = code.zfill(6)
                    existing = session.query(Stock).filter(Stock.code == code).first()
                    if existing:
                        existing.name = etf_names.get(code, code)
                        existing.stock_type = 'ETF'
                    else:
                        stock = Stock(
                            code=code,
                            name=etf_names.get(code, code),
                            market='SH' if code.startswith(('5', '1')) else 'SZ',
                            stock_type='ETF'
                        )
                        session.add(stock)
                        added += 1
            logger.info(f"同步ETF列表(备用)完成: 新增 {added} 只")
        except Exception as e:
            logger.error(f"同步ETF列表(备用)失败: {e}")
        return added

    def sync_bond_list(self) -> int:
        """同步债券列表到数据库"""
        if not ENABLE_MYSQL:
            logger.warning("MySQL is disabled, skipping bond list sync")
            return 0
            
        try:
            self._apply_delay()
            df = ak.bond_zh_hs_spot()
            if df is None or df.empty:
                logger.warning("获取债券列表失败")
                return 0
            
            from data_source.db.connection import get_db_session
            from data_source.db.models import Stock

            added = 0
            with get_db_session() as session:
                for _, row in df.iterrows():
                    code = str(row['代码']).zfill(6)
                    name = str(row['名称'])
                    
                    existing = session.query(Stock).filter(Stock.code == code).first()
                    if existing:
                        existing.name = name
                        existing.stock_type = '债券'
                        existing.market = 'SH' if code.startswith('9') else 'SZ'
                    else:
                        stock = Stock(
                            code=code,
                            name=name,
                            market='SH' if code.startswith('9') else 'SZ',
                            stock_type='债券'
                        )
                        session.add(stock)
                        added += 1

            if self.cache:
                self.cache.delete(CacheKeys.stock_list())
            
            logger.info(f"同步债券列表完成: 新增 {added} 只")
            return added

        except Exception as e:
            logger.error(f"同步债券列表失败: {e}")
            return 0

    def sync_money_fund_list(self) -> int:
        """同步货币基金列表到数据库"""
        if not ENABLE_MYSQL:
            logger.warning("MySQL is disabled, skipping money fund list sync")
            return 0
            
        try:
            self._apply_delay()
            df = ak.fund_money_fund_info_em()
            if df is None or df.empty:
                logger.warning("获取货币基金列表失败")
                return 0
            
            from data_source.db.connection import get_db_session
            from data_source.db.models import Stock

            added = 0
            with get_db_session() as session:
                for _, row in df.iterrows():
                    code = str(row['代码']).zfill(6)
                    name = str(row['名称'])
                    
                    existing = session.query(Stock).filter(Stock.code == code).first()
                    if existing:
                        existing.name = name
                        existing.stock_type = '货币基金'
                    else:
                        stock = Stock(
                            code=code,
                            name=name,
                            market='SH' if code.startswith(('5', '1')) else 'SZ',
                            stock_type='货币基金'
                        )
                        session.add(stock)
                        added += 1

            if self.cache:
                self.cache.delete(CacheKeys.stock_list())
            
            logger.info(f"同步货币基金列表完成: 新增 {added} 只")
            return added

        except Exception as e:
            logger.error(f"同步货币基金列表失败: {e}")
            return 0

    def sync_fund_list(self) -> int:
        """同步普通基金（非货币、非ETF）列表到数据库"""
        if not ENABLE_MYSQL:
            logger.warning("MySQL is disabled, skipping fund list sync")
            return 0
            
        try:
            self._apply_delay()
            df = ak.fund_open_fund_info_em()
            if df is None or df.empty:
                logger.warning("获取基金列表失败")
                return 0
            
            from data_source.db.connection import get_db_session
            from data_source.db.models import Stock

            added = 0
            with get_db_session() as session:
                for _, row in df.iterrows():
                    code = str(row['代码']).zfill(6)
                    name = str(row['简称'])
                    
                    existing = session.query(Stock).filter(Stock.code == code).first()
                    if existing:
                        existing.name = name
                        existing.stock_type = '基金'
                    else:
                        stock = Stock(
                            code=code,
                            name=name,
                            market='SH' if code.startswith(('5', '1')) else 'SZ',
                            stock_type='基金'
                        )
                        session.add(stock)
                        added += 1

            if self.cache:
                self.cache.delete(CacheKeys.stock_list())
            
            logger.info(f"同步基金列表完成: 新增 {added} 只")
            return added

        except Exception as e:
            logger.error(f"同步基金列表失败: {e}")
            return 0

    def sync_daily_kline(self, code: str, start_date: str = None, end_date: str = None) -> int:
        """同步单只股票的日线数据到 daily_kline_akshare 表"""
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

                from data_source.db.connection import get_db_session
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

                with get_db_session() as session:
                    for kline in klines_data:
                        sql = text("""
                            INSERT IGNORE INTO daily_kline_akshare 
                            (code, trade_date, open, high, low, close, volume, amount, adj_close, turn, pct_chg)
                            VALUES (:code, :trade_date, :open, :high, :low, :close, :volume, :amount, :adj_close, :turn, :pct_chg)
                        """)
                        session.execute(sql, kline)

                records = len(klines_data)
                
                if self.cache:
                    cache_key = CacheKeys.kline_range(code, start_date, end_date, source="akshare")
                    self.cache.delete(cache_key)
                
                logger.info(f"同步 {code} 日线数据(akshare): {records} 条")
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

    def sync_index_list(self) -> int:
        """同步指数列表到数据库"""
        if not ENABLE_MYSQL:
            logger.warning("MySQL is disabled, skipping index list sync")
            return 0
        
        try:
            self._apply_delay()
            df = ak.stock_zh_index_spot_em()
            if df is None or df.empty:
                logger.warning("获取指数列表失败")
                return self._sync_index_list_fallback()
            
            from data_source.db.connection import get_db_session
            from data_source.db.models import Stock

            added = 0
            with get_db_session() as session:
                for _, row in df.iterrows():
                    code = str(row['代码']).zfill(6)
                    name = str(row['名称'])
                    
                    existing = session.query(Stock).filter(Stock.code == code).first()
                    if existing:
                        existing.name = name
                        existing.stock_type = '指数'
                        if code.startswith('000') or code.startswith('399'):
                            existing.market = 'SZ' if code.startswith('399') else 'SH'
                    else:
                        stock = Stock(
                            code=code,
                            name=name,
                            market='SZ' if code.startswith('399') else 'SH',
                            stock_type='指数'
                        )
                        session.add(stock)
                        added += 1

            if self.cache:
                self.cache.delete(CacheKeys.stock_list())
            
            logger.info(f"同步指数列表完成: 新增 {added} 只")
            return added

        except Exception as e:
            logger.warning(f"同步指数列表失败: {e}")
            return self._sync_index_list_fallback()

    def _sync_index_list_fallback(self) -> int:
        """备用指数列表"""
        from data_source.db.connection import get_db_session
        from data_source.db.models import Stock

        index_codes = [
            ('000001', '上证指数'), ('399001', '深证成指'), ('399006', '创业板指'),
            ('000300', '沪深300'), ('000016', '上证50'), ('000905', '中证500'),
            ('000852', '中证1000'), ('399005', '中小板指'), ('399106', '深证综指'),
            ('000688', '科创50'), ('000010', '上证180'), ('000009', '上证380'),
            ('399106', '深证综指'), ('399673', '创业板50'), ('000015', '上证红利'),
            ('000922', '中证红利'), ('931643', '科创100'), ('931439', '科创50'),
            ('000852', '中证1000'), ('399673', '创业板50'), ('932000', '科创200'),
        ]
        
        added = 0
        try:
            with get_db_session() as session:
                for code, name in index_codes:
                    code = code.zfill(6)
                    existing = session.query(Stock).filter(Stock.code == code).first()
                    if existing:
                        existing.name = name
                        existing.stock_type = '指数'
                    else:
                        stock = Stock(
                            code=code,
                            name=name,
                            market='SZ' if code.startswith('399') else 'SH',
                            stock_type='指数'
                        )
                        session.add(stock)
                        added += 1
            logger.info(f"同步指数列表(备用)完成: 新增 {added} 只")
        except Exception as e:
            logger.error(f"同步指数列表(备用)失败: {e}")
        return added

    def get_latest_date(self, code: str) -> Optional[str]:
        """获取数据库中某股票最新日期"""
        if not ENABLE_MYSQL:
            return None
            
        try:
            from data_source.db.connection import get_db_session
            from data_source.db.models import DailyKlineAkShare
            
            code = code.zfill(6)
            with get_db_session() as session:
                latest = session.query(DailyKlineAkShare).filter(
                    DailyKlineAkShare.code == code
                ).order_by(DailyKlineAkShare.trade_date.desc()).first()
                
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
            from data_source.db.models import DailyKlineAkShare
            
            with get_db_session() as session:
                oldest = session.query(DailyKlineAkShare.trade_date).order_by(DailyKlineAkShare.trade_date.asc()).first()
                newest = session.query(DailyKlineAkShare.trade_date).order_by(DailyKlineAkShare.trade_date.desc()).first()
                
            return {
                "start": str(oldest[0]) if oldest else None,
                "end": str(newest[0]) if newest else None
            }
        except Exception as e:
            logger.warning(f"获取数据范围失败: {e}")
            return {"start": None, "end": None}

    def get_kline_count(self) -> int:
        """获取数据库中日线数据数量"""
        if not ENABLE_MYSQL:
            return 0
        try:
            from data_source.db.connection import get_db_session
            from data_source.db.models import DailyKlineAkShare
            with get_db_session() as session:
                return session.query(DailyKlineAkShare).count()
        except:
            return 0


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


def sync_index_list() -> int:
    """便捷函数：同步指数列表"""
    sync = AkshareSync()
    return sync.sync_index_list()
