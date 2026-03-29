# -*- coding: utf-8 -*-
"""
免费数据源同步服务 (akshare/baostock)

功能:
- 增量同步：自动检测数据库最新日期，只同步新增数据
- 批量同步：支持进度回调
- 自动降级：akshare 失败自动切换 baostock
- 定时调度：支持每日自动同步
"""

import logging
import time
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Callable

import pandas as pd
import baostock as bs
import akshare as ak

from data_source.config import REQUEST_DELAY, SYNC_CONFIG
from data_source.db.connection import get_db_session, get_engine
from data_source.db.models import Stock, DailyKline
from data_source.cache import get_cache, CacheKeys

logger = logging.getLogger(__name__)


class SyncProgress:
    """同步进度追踪"""

    def __init__(self, total: int, callback: Optional[Callable] = None):
        self.total = total
        self.current = 0
        self.success = 0
        self.failed = 0
        self.callback = callback

    def update(self, success: bool = True):
        self.current += 1
        if success:
            self.success += 1
        else:
            self.failed += 1

        if self.callback:
            self.callback(self)

    @property
    def percent(self) -> float:
        if self.total == 0:
            return 100.0
        return self.current / self.total * 100

    def __str__(self) -> str:
        return f"进度: {self.current}/{self.total} ({self.percent:.1f}%) 成功: {self.success} 失败: {self.failed}"


class FreeDataSync:
    """免费数据源同步器 (akshare + baostock)"""

    def __init__(self):
        self.cache = get_cache()
        self._bs_logged_in = False
        self._engine = get_engine()

    def _apply_delay(self):
        """请求延时"""
        if REQUEST_DELAY > 0:
            time.sleep(REQUEST_DELAY)

    def _bs_login(self):
        """登录 baostock"""
        if not self._bs_logged_in:
            bs.login()
            self._bs_logged_in = True

    def _bs_logout(self):
        """登出 baostock"""
        if self._bs_logged_in:
            bs.logout()
            self._bs_logged_in = False

    def get_stock_list_ak(self) -> pd.DataFrame:
        """使用 akshare 获取股票列表"""
        try:
            self._apply_delay()
            df = ak.stock_info_a_code_name()
            if df is not None and not df.empty:
                df.columns = ['code', 'name']
                df['market'] = df['code'].apply(
                    lambda x: 'SH' if x.startswith(('6', '5')) else 'SZ'
                )
                logger.info(f"akshare 获取股票列表: {len(df)} 只")
                return df
        except Exception as e:
            logger.error(f"akshare 获取股票列表失败: {e}")
        return pd.DataFrame()

    def sync_all_stocks(self) -> Dict[str, int]:
        """同步所有股票列表"""
        result = {"stocks": 0, "etfs": 0}

        try:
            df = self.get_stock_list_ak()
            if df.empty:
                logger.error("无法获取股票列表")
                return result

            stocks_added = 0
            with get_db_session() as session:
                for _, row in df.iterrows():
                    code = row['code']

                    existing = session.query(Stock).filter(Stock.code == code).first()
                    if existing:
                        existing.name = row['name']
                        existing.stock_type = '股票'
                    else:
                        stock = Stock(
                            code=code,
                            name=row['name'],
                            market=row['market'],
                            stock_type='股票'
                        )
                        session.add(stock)
                        stocks_added += 1

            result["stocks"] = stocks_added
            logger.info(f"同步股票列表: 新增 {stocks_added} 只")

            self.cache.delete(CacheKeys.stock_list())

        except Exception as e:
            logger.error(f"同步股票列表失败: {e}")

        return result

    def _get_ak_hist_data(self, code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """使用 akshare 获取日线数据"""
        try:
            self._apply_delay()
            df = ak.stock_zh_a_hist(
                symbol=code,
                start_date=start_date,
                end_date=end_date,
                adjust='hfq'
            )
            if df is not None and not df.empty:
                df = df.rename(columns={
                    'date': 'date',
                    'code': 'code',
                    'open': 'open',
                    'close': 'close',
                    'high': 'high',
                    'low': 'low',
                    'volume': 'volume',
                    'amount': 'amount',
                    'turnover': 'turn',
                    'pct_chg': 'pct_chg'
                })
                df['date'] = pd.to_datetime(df['date']).dt.date
                df['pct_chg'] = df['pct_chg'] / 100 if 'pct_chg' in df.columns else 0
                return df[['code', 'date', 'open', 'high', 'low', 'close', 'volume', 'amount', 'pct_chg', 'turn']]
        except Exception as e:
            logger.warning(f"akshare 获取 {code} 日线失败: {e}")
        return pd.DataFrame()

    def _get_baostock_hist_data(self, code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """使用 baostock 获取日线数据"""
        try:
            self._bs_login()

            exchange = 'sh' if code.startswith(('6', '5')) else 'sz'
            bs_code = f"{exchange}.{code}"

            rs = bs.query_history_k_data_plus(
                bs_code,
                'date,code,open,high,low,close,volume,amount,turn,pctChg',
                start_date=start_date,
                end_date=end_date,
                frequency='d',
                adjustprice='hfq'
            )

            data_list = []
            while (rs.error_code == '0') and rs.next():
                data_list.append(rs.get_row_data())

            if data_list:
                df = pd.DataFrame(data_list, columns=rs.fields)
                df['date'] = pd.to_datetime(df['date']).dt.date
                df['pct_chg'] = pd.to_numeric(df['pctChg'], errors='coerce') / 100
                df['open'] = pd.to_numeric(df['open'], errors='coerce')
                df['high'] = pd.to_numeric(df['high'], errors='coerce')
                df['low'] = pd.to_numeric(df['low'], errors='coerce')
                df['close'] = pd.to_numeric(df['close'], errors='coerce')
                df['volume'] = pd.to_numeric(df['volume'], errors='coerce')
                df['amount'] = pd.to_numeric(df['amount'], errors='coerce')
                df['turn'] = pd.to_numeric(df['turn'], errors='coerce')
                return df[['code', 'date', 'open', 'high', 'low', 'close', 'volume', 'amount', 'pct_chg', 'turn']]
        except Exception as e:
            logger.warning(f"baostock 获取 {code} 日线失败: {e}")
        return pd.DataFrame()

    def get_latest_date(self, code: str) -> Optional[str]:
        """获取数据库中某股票的最新日期"""
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

    def sync_daily_kline_incremental(self, code: str, lookback_days: int = 5) -> int:
        """增量同步日线数据（只同步新增数据）
        
        Args:
            code: 股票代码
            lookback_days: 回溯天数（用于处理补充历史数据）
        """
        latest_date = self.get_latest_date(code)

        if latest_date:
            latest_dt = datetime.strptime(latest_date, '%Y-%m-%d')
            today = datetime.now().date()

            if latest_dt.date() >= today:
                logger.debug(f"{code} 数据已是最新")
                return 0

            start_date = (latest_dt + timedelta(days=1)).strftime('%Y%m%d')
        else:
            start_date = (datetime.now() - timedelta(days=lookback_days * 10)).strftime('%Y%m%d')

        end_date = datetime.now().strftime('%Y%m%d')
        return self.sync_daily_kline(code, start_date, end_date)

    def sync_daily_kline(self, code: str, start_date: str = None, end_date: str = None) -> int:
        """同步单只股票的日线数据（优先 akshare，失败则用 baostock）"""
        if end_date is None:
            end_date = datetime.now().strftime('%Y%m%d')
        if start_date is None:
            start_date = "20200101"

        start_dt = datetime.strptime(start_date, '%Y%m%d').strftime('%Y-%m-%d')
        end_dt = datetime.strptime(end_date, '%Y%m%d').strftime('%Y-%m-%d')

        df = self._get_ak_hist_data(code, start_dt, end_dt)

        if df.empty:
            logger.info(f"akshare 失败，尝试 baostock: {code}")
            df = self._get_baostock_hist_data(code, start_dt, end_dt)

        if df.empty:
            logger.warning(f"未获取到 {code} 的日线数据")
            return 0

        df = df.rename(columns={'date': 'trade_date'})
        df = df.drop_duplicates(subset=['code', 'trade_date'])

        try:
            df.to_sql('daily_kline', self._engine, if_exists='append', index=False, chunksize=5000)
            records = len(df)

            cache_key = CacheKeys.kline_range(code, start_date, end_date)
            self.cache.delete(cache_key)
            logger.info(f"同步 {code} 日线数据: {records} 条")
            return records
        except Exception as e:
            logger.error(f"保存 {code} 日线数据失败: {e}")
            return 0

    def sync_daily_kline_batch(
        self,
        codes: List[str],
        start_date: str = None,
        end_date: str = None,
        progress_callback: Optional[Callable[[SyncProgress], None]] = None,
        incremental: bool = True
    ) -> Dict[str, int]:
        """批量同步多只股票的日线数据

        Args:
            codes: 股票代码列表
            start_date: 开始日期 (YYYYMMDD)，None 表示自动
            end_date: 结束日期 (YYYYMMDD)，None 表示今天
            progress_callback: 进度回调函数
            incremental: 是否启用增量同步
        """
        results = {}
        progress = SyncProgress(len(codes), progress_callback)

        if end_date is None:
            end_date = datetime.now().strftime('%Y%m%d')
        if start_date is None and not incremental:
            start_date = "20200101"

        logger.info(f"开始批量同步 {len(codes)} 只股票" + 
                   (" (增量模式)" if incremental else f": {start_date} ~ {end_date}"))

        for code in codes:
            try:
                if incremental:
                    records = self.sync_daily_kline_incremental(code)
                else:
                    records = self.sync_daily_kline(code, start_date, end_date)
                results[code] = records
                progress.update(success=(records > 0))

                logger.info(f"{progress} - {code}")

            except Exception as e:
                logger.warning(f"同步 {code} 失败: {e}")
                results[code] = 0
                progress.update(success=False)

        total = sum(results.values())
        logger.info(f"批量同步完成: {len(codes)} 只, {total} 条, 成功 {progress.success}, 失败 {progress.failed}")

        return results

    def sync_watchlist_stocks(self, watchlist_codes: List[str], lookback_days: int = 30) -> Dict[str, int]:
        """同步自选股列表的日线数据（增量更新）

        Args:
            watchlist_codes: 自选股代码列表
            lookback_days: 回溯天数
        """
        start_date = (datetime.now() - timedelta(days=lookback_days)).strftime('%Y%m%d')
        end_date = datetime.now().strftime('%Y%m%d')

        return self.sync_daily_kline_batch(
            watchlist_codes,
            start_date=start_date,
            end_date=end_date,
            incremental=True
        )

    def get_stock_count(self) -> int:
        """获取数据库中股票数量"""
        try:
            with get_db_session() as session:
                return session.query(Stock).count()
        except Exception:
            return 0

    def get_kline_count(self) -> int:
        """获取数据库中日线数据数量"""
        try:
            with get_db_session() as session:
                return session.query(DailyKline).count()
        except Exception:
            return 0

    def get_data_range(self) -> Dict[str, str]:
        """获取数据库中数据的日期范围"""
        try:
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

    def get_sync_stats(self) -> Dict:
        """获取同步统计信息"""
        return {
            "stock_count": self.get_stock_count(),
            "kline_count": self.get_kline_count(),
            "data_range": self.get_data_range()
        }

    def __del__(self):
        """析构时确保登出"""
        self._bs_logout()


def sync_all_stocks() -> Dict[str, int]:
    """便捷函数：同步所有股票"""
    sync = FreeDataSync()
    return sync.sync_all_stocks()


def sync_stock_daily(code: str, start_date: str = None) -> int:
    """便捷函数：同步单只股票日线"""
    sync = FreeDataSync()
    return sync.sync_daily_kline(code, start_date)


def sync_watchlist_incremental(watchlist_codes: List[str]) -> Dict[str, int]:
    """便捷函数：增量同步自选股"""
    sync = FreeDataSync()
    return sync.sync_watchlist_stocks(watchlist_codes)
