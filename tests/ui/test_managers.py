# -*- coding: utf-8 -*-
"""
数据库管理器测试

测试报告、自选股、策略模板的数据库操作
"""

import pytest
import json
from datetime import datetime, date
from tests.ui.conftest import DatabaseTestHelper, CacheTestHelper


class TestReportManager:
    """报告管理器测试"""

    def test_save_and_load_report(self, clean_database, clean_cache):
        """测试保存和加载报告"""
        from backtest.report_manager import ReportManager, ReportData
        from backtest.dca_backtest import BacktestResult
        import pandas as pd

        rm = ReportManager()

        result = BacktestResult(
            total_invested=12000.0,
            final_value=15000.0,
            total_return=3000.0,
            return_rate=25.0,
            annual_return=8.5,
            max_drawdown=15.0,
            investment_count=12,
            stop_loss_count=1,
            take_profit_count=2,
            nav_data=pd.DataFrame(),
            trades=pd.DataFrame({
                'date': ['2022-01-01'],
                'action': ['buy'],
                'nav': [10.0],
                'shares': [100.0],
                'invest_amount': [1000.0],
                'total_shares': [100.0],
                'portfolio_value': [1000.0],
                'return_rate': [0.0],
                'reason': ['']
            }),
            strategy_params={
                'fund_code': '000001',
                'fund_name': '平安银行',
                'start_date': '2022-01-01',
                'end_date': '2022-12-31',
                'frequency': 'monthly'
            }
        )

        report_id = rm.save_report(result)
        assert report_id is not None
        assert len(report_id) == 8

        loaded = rm.load_report(report_id)
        assert loaded is not None
        assert loaded.id == report_id
        assert loaded.fund_code == '000001'
        assert loaded.fund_name == '平安银行'

    def test_list_reports(self, clean_database, clean_cache):
        """测试列出报告"""
        from backtest.report_manager import ReportManager
        from backtest.dca_backtest import BacktestResult
        import pandas as pd

        rm = ReportManager()

        for i in range(3):
            result = BacktestResult(
                total_invested=1000.0 * (i + 1),
                final_value=1200.0 * (i + 1),
                total_return=200.0 * (i + 1),
                return_rate=20.0,
                annual_return=8.0,
                max_drawdown=10.0,
                investment_count=12,
                stop_loss_count=0,
                take_profit_count=0,
                nav_data=pd.DataFrame(),
                trades=pd.DataFrame(),
                strategy_params={
                    'fund_code': f'00000{i}',
                    'fund_name': f'股票{i}',
                    'start_date': '2022-01-01',
                    'end_date': '2022-12-31'
                }
            )
            rm.save_report(result)

        reports = rm.list_reports()
        assert len(reports) == 3

    def test_delete_report(self, clean_database, clean_cache):
        """测试删除报告"""
        from backtest.report_manager import ReportManager
        from backtest.dca_backtest import BacktestResult
        import pandas as pd

        rm = ReportManager()

        result = BacktestResult(
            total_invested=12000.0,
            final_value=15000.0,
            total_return=3000.0,
            return_rate=25.0,
            annual_return=8.5,
            max_drawdown=15.0,
            investment_count=12,
            stop_loss_count=0,
            take_profit_count=0,
            nav_data=pd.DataFrame(),
            trades=pd.DataFrame(),
            strategy_params={
                'fund_code': '000001',
                'fund_name': '测试',
                'start_date': '2022-01-01',
                'end_date': '2022-12-31'
            }
        )

        report_id = rm.save_report(result)
        assert rm.delete_report(report_id) is True
        assert rm.load_report(report_id) is None

    def test_search_reports(self, clean_database, clean_cache):
        """测试搜索报告"""
        from backtest.report_manager import ReportManager
        from backtest.dca_backtest import BacktestResult
        import pandas as pd

        rm = ReportManager()

        result1 = BacktestResult(
            total_invested=12000.0, final_value=15000.0, total_return=3000.0,
            return_rate=25.0, annual_return=8.5, max_drawdown=15.0,
            investment_count=12, stop_loss_count=0, take_profit_count=0,
            nav_data=pd.DataFrame(), trades=pd.DataFrame(),
            strategy_params={
                'fund_code': '000001', 'fund_name': '平安银行',
                'start_date': '2022-01-01', 'end_date': '2022-12-31'
            }
        )
        result2 = BacktestResult(
            total_invested=24000.0, final_value=28000.0, total_return=4000.0,
            return_rate=16.7, annual_return=6.0, max_drawdown=20.0,
            investment_count=24, stop_loss_count=0, take_profit_count=0,
            nav_data=pd.DataFrame(), trades=pd.DataFrame(),
            strategy_params={
                'fund_code': '600036', 'fund_name': '招商银行',
                'start_date': '2022-01-01', 'end_date': '2024-12-31'
            }
        )

        rm.save_report(result1)
        rm.save_report(result2)

        reports = rm.list_reports(search='平安')
        assert len(reports) == 1
        assert reports[0].fund_name == '平安银行'


class TestWatchlistManager:
    """自选股管理器测试"""

    def test_default_watchlists_created(self, verify_db, clean_database, clean_cache):
        """测试默认自选股列表是否创建"""
        from backtest.watchlist_manager import WatchlistManager

        wm = WatchlistManager()
        watchlists = wm.list_watchlists()

        assert len(watchlists) >= 3
        names = [w.name for w in watchlists]
        assert '宽基ETF' in names
        assert '行业ETF' in names
        assert '红利基金' in names

    def test_create_watchlist(self, clean_database, clean_cache):
        """测试创建自选股列表"""
        from backtest.watchlist_manager import WatchlistManager

        wm = WatchlistManager()
        wl = wm.create_watchlist('我的自选', '我的测试列表')

        assert wl.name == '我的自选'
        assert wl.description == '我的测试列表'
        assert len(wl.stocks) == 0

    def test_add_stock_to_watchlist(self, clean_database, clean_cache):
        """测试添加股票到自选股列表"""
        from backtest.watchlist_manager import WatchlistManager, StockInfo

        wm = WatchlistManager()
        watchlists = wm.list_watchlists()
        wl = watchlists[0]

        stock = StockInfo(
            code='600519',
            name='贵州茅台',
            market='A股',
            type='股票'
        )

        result = wm.add_stock(wl.id, stock)
        assert result is True

        updated_wl = wm.get_watchlist(wl.id)
        assert any(s.code == '600519' for s in updated_wl.stocks)

    def test_remove_stock_from_watchlist(self, clean_database, clean_cache):
        """测试从自选股列表移除股票"""
        from backtest.watchlist_manager import WatchlistManager, StockInfo

        wm = WatchlistManager()
        watchlists = wm.list_watchlists()
        wl = watchlists[0]

        stock = StockInfo(code='600519', name='贵州茅台')
        wm.add_stock(wl.id, stock)

        result = wm.remove_stock(wl.id, '600519')
        assert result is True

        updated_wl = wm.get_watchlist(wl.id)
        assert not any(s.code == '600519' for s in updated_wl.stocks)

    def test_update_watchlist(self, clean_database, clean_cache):
        """测试更新自选股列表"""
        from backtest.watchlist_manager import WatchlistManager

        wm = WatchlistManager()
        watchlists = wm.list_watchlists()
        wl = watchlists[0]

        updated = wm.update_watchlist(wl.id, name='新名称', description='新描述')
        assert updated.name == '新名称'
        assert updated.description == '新描述'

    def test_delete_watchlist(self, clean_database, clean_cache):
        """测试删除自选股列表"""
        from backtest.watchlist_manager import WatchlistManager

        wm = WatchlistManager()
        wl = wm.create_watchlist('待删除')

        result = wm.delete_watchlist(wl.id)
        assert result is True
        assert wm.get_watchlist(wl.id) is None

    def test_get_all_stocks(self, clean_database, clean_cache):
        """测试获取所有自选股"""
        from backtest.watchlist_manager import WatchlistManager, StockInfo

        wm = WatchlistManager()

        wl1 = wm.create_watchlist('列表1')
        wl2 = wm.create_watchlist('列表2')

        wm.add_stock(wl1.id, StockInfo(code='600519', name='茅台'))
        wm.add_stock(wl1.id, StockInfo(code='000001', name='平安'))
        wm.add_stock(wl2.id, StockInfo(code='600036', name='招行'))

        all_stocks = wm.get_all_stocks()
        assert len(all_stocks) >= 3

        codes = [s.code for s in all_stocks]
        assert '600519' in codes
        assert '000001' in codes
        assert '600036' in codes


class TestStrategyManager:
    """策略管理器测试"""

    def test_default_strategies_created(self, verify_db, clean_database, clean_cache):
        """测试默认策略是否创建"""
        from backtest.strategy_manager import StrategyManager

        sm = StrategyManager()
        strategies = sm.list_strategies()

        assert len(strategies) >= 6

        names = [s.name for s in strategies]
        assert '基础定投' in names
        assert '稳健定投' in names

    def test_get_strategy(self, clean_database, clean_cache):
        """测试获取策略"""
        from backtest.strategy_manager import StrategyManager

        sm = StrategyManager()
        strategies = sm.list_strategies()

        strategy = sm.get_strategy(strategies[0].id)
        assert strategy is not None
        assert strategy.id == strategies[0].id

    def test_create_strategy(self, clean_database, clean_cache):
        """测试创建策略"""
        from backtest.strategy_manager import StrategyManager, StrategyParams

        sm = StrategyManager()

        params = StrategyParams(
            frequency='monthly',
            investment_amount=2000.0,
            enable_stop_loss=True,
            stop_loss_rate=0.15
        )

        strategy = sm.create_strategy(
            name='自定义策略',
            group='我的策略',
            description='测试策略',
            params=params
        )

        assert strategy.name == '自定义策略'
        assert strategy.group == '我的策略'
        assert strategy.params.investment_amount == 2000.0
        assert strategy.params.enable_stop_loss is True

    def test_update_strategy(self, clean_database, clean_cache):
        """测试更新策略"""
        from backtest.strategy_manager import StrategyManager

        sm = StrategyManager()

        strategy = sm.create_strategy('待更新', '测试')

        updated = sm.update_strategy(
            strategy.id,
            name='已更新',
            description='新描述',
            params={'investment_amount': 3000.0}
        )

        assert updated.name == '已更新'
        assert updated.params.investment_amount == 3000.0

    def test_delete_strategy(self, clean_database, clean_cache):
        """测试删除策略"""
        from backtest.strategy_manager import StrategyManager

        sm = StrategyManager()

        strategy = sm.create_strategy('待删除', '测试')
        result = sm.delete_strategy(strategy.id)

        assert result is True
        assert sm.get_strategy(strategy.id) is None

    def test_filter_by_group(self, clean_database, clean_cache):
        """测试按分组筛选策略"""
        from backtest.strategy_manager import StrategyManager

        sm = StrategyManager()

        strategies = sm.list_strategies(group='保守型')
        assert all(s.group == '保守型' for s in strategies)

    def test_get_groups(self, clean_database, clean_cache):
        """测试获取所有分组"""
        from backtest.strategy_manager import StrategyManager

        sm = StrategyManager()
        groups = sm.get_groups()

        assert '保守型' in groups
        assert '激进型' in groups


class TestCache:
    """缓存功能测试"""

    def test_cache_invalidation_on_save(self, clean_database, clean_cache):
        """测试保存时缓存失效"""
        from backtest.report_manager import ReportManager
        from backtest.dca_backtest import BacktestResult
        import pandas as pd

        rm = ReportManager()

        result = BacktestResult(
            total_invested=12000.0, final_value=15000.0, total_return=3000.0,
            return_rate=25.0, annual_return=8.5, max_drawdown=15.0,
            investment_count=12, stop_loss_count=0, take_profit_count=0,
            nav_data=pd.DataFrame(), trades=pd.DataFrame(),
            strategy_params={
                'fund_code': '000001', 'fund_name': '测试',
                'start_date': '2022-01-01', 'end_date': '2022-12-31'
            }
        )

        reports1 = rm.list_reports()
        rm.save_report(result)
        reports2 = rm.list_reports()

        assert len(reports1) + 1 == len(reports2)


class TestDatabaseIntegration:
    """数据库集成测试"""

    def test_database_connection(self, verify_db):
        """测试数据库连接"""
        from data_source.db.connection import get_engine

        engine = get_engine()
        assert engine is not None

    def test_tables_structure(self, verify_db):
        """测试表结构"""
        assert DatabaseTestHelper.verify_tables_exist() is True

    def test_foreign_keys(self, verify_db, clean_database):
        """测试外键约束"""
        from data_source.db.connection import get_db_session
        from data_source.db.models import Watchlist, WatchlistStock

        with get_db_session() as session:
            wl = Watchlist(
                id='test_wl',
                name='测试',
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            session.add(wl)
            session.flush()

            ws = WatchlistStock(
                watchlist_id='test_wl',
                code='000001',
                name='测试'
            )
            session.add(ws)
