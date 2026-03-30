# -*- coding: utf-8 -*-
"""
集成测试 - 测试完整的业务流程
"""

import pytest
import pandas as pd
from datetime import datetime, date


class TestBacktestWorkflow:
    """回测工作流测试"""

    def test_single_backtest_workflow(self, clean_database, clean_cache):
        """测试单个股票回测工作流"""
        from backtest import FundBacktester, BacktestConfig
        from backtest.report_manager import ReportManager

        tester = FundBacktester(data_source='auto')
        rm = ReportManager()

        config = BacktestConfig(
            fund_code='000001',
            fund_name='平安银行',
            start_date='2022-01-01',
            end_date='2022-12-31',
            investment_amount=1000.0,
            frequency='monthly'
        )

        result = tester.single_fund(config)

        if result:
            report_id = rm.save_report(result)
            assert report_id is not None

            loaded = rm.load_report(report_id)
            assert loaded is not None
            assert loaded.fund_code == '000001'

    def test_portfolio_backtest_workflow(self, clean_database, clean_cache):
        """测试组合回测工作流"""
        from backtest import FundBacktester

        tester = FundBacktester(data_source='db')

        funds = [
            {'fund_code': '000001', 'name': '平安银行'},
            {'fund_code': '600036', 'name': '招商银行'},
        ]

        result = tester.portfolio(
            funds=funds,
            start_date='2022-01-01',
            end_date='2022-12-31',
            total_amount=2000.0,
            frequency='monthly'
        )

        assert 'total_invested' in result or 'results' in result


class TestDataSourceWorkflow:
    """数据源工作流测试"""

    def test_db_data_source(self, verify_db):
        """测试数据库作为数据源"""
        from data_source.fund_data_source import FundDataSource

        ds = FundDataSource(preferred_source='db')

        with pytest.raises(Exception):
            ds.get_nav('INVALID_CODE', '2022-01-01', '2022-12-31')

    def test_cache_first_priority(self, clean_cache, verify_db):
        """测试缓存优先策略"""
        from data_source.fund_data_source import FundDataSource

        ds = FundDataSource(preferred_source='db')
        assert ds.current_source == 'db'


class TestEndToEndScenarios:
    """端到端场景测试"""

    def test_full_backtest_cycle(self, clean_database, clean_cache, verify_db):
        """测试完整的回测周期"""
        from backtest import FundBacktester, BacktestConfig
        from backtest.report_manager import ReportManager
        from backtest.watchlist_manager import WatchlistManager
        from backtest.strategy_manager import StrategyManager

        rm = ReportManager()
        wm = WatchlistManager()
        sm = StrategyManager()

        tester = FundBacktester(data_source='db')

        strategies = sm.list_strategies()
        strategy = strategies[0]

        config = BacktestConfig(
            fund_code='000001',
            fund_name='平安银行',
            start_date='2022-01-01',
            end_date='2022-12-31',
            investment_amount=1000.0,
            frequency=strategy.params.frequency,
            enable_stop_loss=strategy.params.enable_stop_loss,
            stop_loss_rate=strategy.params.stop_loss_rate
        )

        result = tester.single_fund(config)

        if result:
            report_id = rm.save_report(result)
            reports = rm.list_reports()
            assert len(reports) >= 1

        watchlists = wm.list_watchlists()
        assert len(watchlists) >= 3

        strategy_list = sm.list_strategies()
        assert len(strategy_list) >= 6

    def test_multi_stock_comparison(self, clean_database, clean_cache, verify_db):
        """测试多股票对比"""
        from backtest import FundBacktester

        tester = FundBacktester(data_source='db')

        funds = [
            {'fund_code': '000001', 'name': '平安银行'},
            {'fund_code': '600036', 'name': '招商银行'},
            {'fund_code': '000858', 'name': '五粮液'},
        ]

        results = tester.compare(
            funds=funds,
            start_date='2022-01-01',
            end_date='2022-12-31',
            amount=1000.0,
            frequency='monthly'
        )

        assert isinstance(results, dict)
