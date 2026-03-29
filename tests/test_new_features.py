# -*- coding: utf-8 -*-
"""
新功能测试

包含:
- 回测分析模块测试
- 报告导出模块测试
- 进度追踪模块测试
- 分级缓存模块测试
"""

import pytest
import os
import tempfile
from datetime import datetime
from typing import Dict
import pandas as pd
from unittest.mock import Mock, patch

sys_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
import sys
sys.path.insert(0, sys_path)


class TestBacktestAnalyzer:
    """回测分析器测试"""

    def test_sharpe_ratio_calculation(self):
        """测试夏普比率计算"""
        from backtest.analysis import BacktestAnalyzer

        trades = pd.DataFrame({
            'date': pd.date_range('2022-01-01', periods=100),
            'return_rate': [0.01, -0.005, 0.015, 0.02, -0.01] * 20,
            'portfolio_value': [10000 + i * 100 for i in range(100)]
        })

        analyzer = BacktestAnalyzer(risk_free_rate=0.03)
        metrics = analyzer.analyze_trades(trades)

        assert metrics.sharpe_ratio > 0
        assert metrics.sharpe_ratio != 0

    def test_max_drawdown_calculation(self):
        """测试最大回撤计算"""
        from backtest.analysis import BacktestAnalyzer

        trades = pd.DataFrame({
            'date': pd.date_range('2022-01-01', periods=10),
            'return_rate': [0] * 10,
            'portfolio_value': [10000, 10500, 11000, 9000, 9500, 10000, 10200, 9800, 10300, 10000]
        })

        analyzer = BacktestAnalyzer()
        metrics = analyzer.analyze_trades(trades)

        assert metrics.max_drawdown > 0
        assert metrics.max_drawdown < 100

    def test_win_rate_calculation(self):
        """测试胜率计算"""
        from backtest.analysis import BacktestAnalyzer

        trades = pd.DataFrame({
            'date': pd.date_range('2022-01-01', periods=10),
            'return_rate': [0.01, 0.02, -0.01, 0.03, -0.02, 0.01, 0.02, -0.01, 0.01, 0.02],
            'portfolio_value': [10000 + i * 100 for i in range(10)]
        })

        analyzer = BacktestAnalyzer()
        metrics = analyzer.analyze_trades(trades)

        assert metrics.win_rate == 70.0

    def test_empty_trades(self):
        """测试空交易记录"""
        from backtest.analysis import BacktestAnalyzer

        trades = pd.DataFrame()

        analyzer = BacktestAnalyzer()
        metrics = analyzer.analyze_trades(trades)

        assert metrics.sharpe_ratio == 0
        assert metrics.max_drawdown == 0

    def test_compare_results(self):
        """测试多结果对比"""
        from backtest.analysis import compare_backtests

        result1 = Mock()
        result1.return_rate = 15.5
        result1.return_rate = 15.5
        result1.trades = pd.DataFrame({
            'date': pd.date_range('2022-01-01', periods=10),
            'return_rate': [0.01, -0.005] * 5,
            'portfolio_value': [10000 + i * 50 for i in range(10)]
        })

        result2 = Mock()
        result2.return_rate = 20.0
        result2.trades = pd.DataFrame({
            'date': pd.date_range('2022-01-01', periods=10),
            'return_rate': [0.015, -0.003] * 5,
            'portfolio_value': [10000 + i * 60 for i in range(10)]
        })

        results = {"策略A": result1, "策略B": result2}
        df = compare_backtests(results)

        assert len(df) == 2
        assert "策略A" in df['名称'].values
        assert "策略B" in df['名称'].values


class TestReportExporter:
    """报告导出测试"""

    def setup_method(self):
        """测试前创建临时目录"""
        self.temp_dir = tempfile.mkdtemp()

    def teardown_method(self):
        """测试后清理"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_export_excel(self):
        """测试 Excel 导出"""
        from backtest.report_exporter import ReportExporter
        from backtest.report_manager import ReportData

        report = ReportData(
            id='test123',
            name='测试报告',
            created_at='2024-01-01 10:00:00',
            fund_code='600036',
            fund_name='招商银行',
            start_date='2022-01-01',
            end_date='2024-12-31',
            investment_amount=1000,
            frequency='monthly',
            strategy_params={'enable_stop_loss': False, 'enable_take_profit': True},
            result={
                'total_invested': 36000,
                'final_value': 42000,
                'total_return': 6000,
                'return_rate': 16.67,
                'annual_return': 7.8,
                'max_drawdown': -12.5,
                'investment_count': 36
            },
            trades=[
                {'date': '2022-01-05', 'action': 'buy', 'return_rate': 0}
            ]
        )

        exporter = ReportExporter(reports_dir=self.temp_dir)
        filepath = exporter.export_excel(report, 'test_report.xlsx')

        assert os.path.exists(filepath)
        assert filepath.endswith('.xlsx')

    def test_export_csv(self):
        """测试 CSV 导出"""
        from backtest.report_exporter import ReportExporter
        from backtest.report_manager import ReportData

        report = ReportData(
            id='test123',
            name='测试报告',
            created_at='2024-01-01 10:00:00',
            fund_code='600036',
            fund_name='招商银行',
            start_date='2022-01-01',
            end_date='2024-12-31',
            investment_amount=1000,
            frequency='monthly',
            strategy_params={},
            result={'total_invested': 36000},
            trades=[
                {'date': '2022-01-05', 'action': 'buy', 'return_rate': 0}
            ]
        )

        exporter = ReportExporter(reports_dir=self.temp_dir)
        filepath = exporter.export_csv(report, 'test_report.csv')

        assert os.path.exists(filepath)
        assert filepath.endswith('.csv')

    def test_export_comparison_excel(self):
        """测试多报告对比导出"""
        from backtest.report_exporter import MultiReportExporter
        from backtest.report_manager import ReportData

        report1 = ReportData(
            id='test1', name='报告1', created_at='2024-01-01',
            fund_code='600036', fund_name='招商银行',
            start_date='2022-01-01', end_date='2024-12-31',
            investment_amount=1000, frequency='monthly',
            strategy_params={},
            result={'total_invested': 36000, 'final_value': 42000, 'return_rate': 16.67, 'annual_return': 7.8, 'max_drawdown': -12.5, 'investment_count': 36},
            trades=[]
        )

        report2 = ReportData(
            id='test2', name='报告2', created_at='2024-01-01',
            fund_code='000001', fund_name='平安银行',
            start_date='2022-01-01', end_date='2024-12-31',
            investment_amount=1000, frequency='monthly',
            strategy_params={},
            result={'total_invested': 36000, 'final_value': 45000, 'return_rate': 25.0, 'annual_return': 9.5, 'max_drawdown': -15.0, 'investment_count': 36},
            trades=[]
        )

        exporter = MultiReportExporter()
        filepath = exporter.export_comparison_excel([report1, report2], 'comparison.xlsx')

        assert os.path.exists(filepath)


class TestProgressTracker:
    """进度追踪测试"""

    def test_progress_update(self):
        """测试进度更新"""
        from backtest.progress import ProgressTracker, BacktestProgress

        tracker = ProgressTracker("test_task", total_steps=100)

        tracker.update(50, "处理中", "已完成50%")
        progress = tracker.progress

        assert progress.current_step == 50
        assert progress.current_phase == "处理中"
        assert progress.percent == 50.0

    def test_progress_complete(self):
        """测试进度完成"""
        from backtest.progress import ProgressTracker

        tracker = ProgressTracker("test_task", total_steps=100)
        tracker.complete()

        assert tracker.progress.current_step == 100
        assert tracker.progress.percent == 100.0

    def test_progress_callback(self):
        """测试进度回调"""
        from backtest.progress import ProgressTracker

        callback_values = []

        def on_progress(progress):
            callback_values.append(progress.percent)

        tracker = ProgressTracker("test_task", total_steps=10)
        tracker.add_callback(on_progress)

        tracker.update(5, "测试")
        tracker.update(10, "完成")

        assert len(callback_values) == 2
        assert callback_values[0] == 50.0
        assert callback_values[1] == 100.0

    def test_multi_task_tracker(self):
        """测试多任务追踪"""
        from backtest.progress import MultiTaskProgressTracker

        multi = MultiTaskProgressTracker()

        tracker1 = multi.create_task("task1", 100)
        tracker2 = multi.create_task("task2", 50)

        tracker1.update(50)
        tracker2.update(25)

        summary = multi.get_summary()
        assert summary["total_tasks"] == 2
        assert summary["overall_progress"] == 50.0


class TestLRUCache:
    """LRU 缓存测试"""

    def test_lru_cache_basic(self):
        """测试 LRU 缓存基本功能"""
        from data_source.cache.tiered_cache import LRUCache

        cache = LRUCache(max_size=3)

        cache.set("a", 1)
        cache.set("b", 2)
        cache.set("c", 3)

        assert cache.get("a") == 1
        assert cache.get("b") == 2
        assert cache.get("c") == 3

    def test_lru_eviction(self):
        """测试 LRU 淘汰"""
        from data_source.cache.tiered_cache import LRUCache

        cache = LRUCache(max_size=3)

        cache.set("a", 1)
        cache.set("b", 2)
        cache.set("c", 3)
        cache.set("d", 4)

        assert cache.get("a") is None
        assert cache.get("d") == 4
        assert cache.get("b") == 2

    def test_lru_hit_rate(self):
        """测试缓存命中率"""
        from data_source.cache.tiered_cache import LRUCache

        cache = LRUCache(max_size=5)

        cache.set("a", 1)
        cache.get("a")
        cache.get("a")
        cache.get("nonexistent")

        stats = cache.stats()
        assert stats["hits"] == 2
        assert stats["misses"] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
