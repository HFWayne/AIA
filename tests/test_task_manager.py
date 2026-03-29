# -*- coding: utf-8 -*-
"""
任务管理模块测试

包含:
- AutoTask 数据类测试
- StockResult 数据类测试
- 任务序列化/反序列化测试
- TaskManager 测试
"""

import pytest
import os
import sys
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

sys_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, sys_path)


class TestAutoTask:
    """AutoTask 数据类测试"""

    def test_auto_task_creation(self):
        """测试 AutoTask 创建"""
        from backtest.page_task import AutoTask, TaskStatus

        task = AutoTask(
            id="task001",
            name="测试任务",
            stock_codes=["600036", "600519"],
            strategy_ids=["st_basic"],
            start_date="2022-01-01",
            end_date="2024-12-31",
            status=TaskStatus.CREATED
        )

        assert task.id == "task001"
        assert task.name == "测试任务"
        assert len(task.stock_codes) == 2
        assert task.status == TaskStatus.CREATED

    def test_auto_task_to_dict(self):
        """测试 AutoTask 转字典（关键测试：修复前会报错）"""
        from backtest.page_task import AutoTask, TaskStatus, StockResult, StockStatus

        task = AutoTask(
            id="task001",
            name="测试任务",
            stock_codes=["600036"],
            strategy_ids=["st_basic"],
            start_date="2022-01-01",
            end_date="2024-12-31",
            status=TaskStatus.RUNNING,
            results={
                "600036_st_basic": StockResult(
                    code="600036",
                    name="招商银行",
                    status=StockStatus.COMPLETED,
                    return_rate=15.5,
                    annual_return=7.2,
                    max_drawdown=-10.5
                )
            }
        )

        task_dict = task.to_dict()

        assert task_dict['id'] == "task001"
        assert task_dict['name'] == "测试任务"
        assert task_dict['status'] == "running"
        assert "600036_st_basic" in task_dict['results']
        assert task_dict['results']['600036_st_basic']['return_rate'] == 15.5

    def test_auto_task_from_dict(self):
        """测试从字典创建 AutoTask"""
        from backtest.page_task import AutoTask, TaskStatus, StockStatus

        data = {
            'id': 'task002',
            'name': '反序列化测试',
            'stock_codes': ['600036', '601318'],
            'strategy_ids': ['st_basic', 'st_agg'],
            'start_date': '2022-01-01',
            'end_date': '2024-12-31',
            'status': 'completed',
            'created_at': '2024-01-01 10:00:00',
            'started_at': '2024-01-01 10:01:00',
            'completed_at': '2024-01-01 10:05:00',
            'results': {
                '600036_st_basic': {
                    'code': '600036',
                    'name': '招商银行',
                    'status': 'completed',
                    'return_rate': 15.5,
                    'annual_return': 7.2,
                    'max_drawdown': -10.5,
                    'error': None,
                    'report_id': 'report001'
                }
            }
        }

        task = AutoTask.from_dict(data)

        assert task.id == "task002"
        assert task.name == "反序列化测试"
        assert task.status == TaskStatus.COMPLETED
        assert len(task.stock_codes) == 2
        assert "600036_st_basic" in task.results
        assert task.results["600036_st_basic"].code == "600036"
        assert task.results["600036_st_basic"].return_rate == 15.5

    def test_auto_task_round_trip(self):
        """测试序列化-反序列化往返"""
        from backtest.page_task import AutoTask, TaskStatus, StockResult, StockStatus

        original = AutoTask(
            id="round_trip_test",
            name="往返测试任务",
            stock_codes=["600036", "000001", "600519"],
            strategy_ids=["st_basic", "st_agg"],
            start_date="2022-01-01",
            end_date="2024-12-31",
            status=TaskStatus.COMPLETED,
            created_at="2024-01-01 10:00:00",
            completed_at="2024-01-01 11:00:00",
            results={
                "600036_st_basic": StockResult(
                    code="600036",
                    name="招商银行",
                    status=StockStatus.COMPLETED,
                    return_rate=20.5,
                    annual_return=9.5,
                    max_drawdown=-8.5
                ),
                "000001_st_agg": StockResult(
                    code="000001",
                    name="平安银行",
                    status=StockStatus.FAILED,
                    error="数据获取失败",
                    return_rate=None
                )
            }
        )

        task_dict = original.to_dict()
        restored = AutoTask.from_dict(task_dict)

        assert restored.id == original.id
        assert restored.name == original.name
        assert restored.status == original.status
        assert len(restored.stock_codes) == len(original.stock_codes)
        assert len(restored.results) == len(original.results)

        for key in original.results:
            assert key in restored.results
            assert restored.results[key].code == original.results[key].code
            assert restored.results[key].return_rate == original.results[key].return_rate

    def test_auto_task_empty_results(self):
        """测试空结果列表"""
        from backtest.page_task import AutoTask, TaskStatus

        task = AutoTask(
            id="empty_results",
            name="空结果任务",
            stock_codes=[],
            strategy_ids=[],
            start_date="2022-01-01",
            end_date="2024-12-31"
        )

        task_dict = task.to_dict()
        assert task_dict['results'] == {}
        assert len(task_dict['results']) == 0

        restored = AutoTask.from_dict(task_dict)
        assert restored.results == {}


class TestStockResult:
    """StockResult 数据类测试"""

    def test_stock_result_creation(self):
        """测试 StockResult 创建"""
        from backtest.page_task import StockResult, StockStatus

        result = StockResult(
            code="600036",
            name="招商银行",
            status=StockStatus.PENDING
        )

        assert result.code == "600036"
        assert result.name == "招商银行"
        assert result.status == StockStatus.PENDING
        assert result.return_rate is None

    def test_stock_result_with_values(self):
        """测试带值的 StockResult"""
        from backtest.page_task import StockResult, StockStatus

        result = StockResult(
            code="600519",
            name="贵州茅台",
            status=StockStatus.COMPLETED,
            return_rate=50.5,
            annual_return=20.0,
            max_drawdown=-15.5,
            report_id="report_001"
        )

        assert result.return_rate == 50.5
        assert result.annual_return == 20.0
        assert result.max_drawdown == -15.5
        assert result.report_id == "report_001"

    def test_stock_result_error(self):
        """测试失败的 StockResult"""
        from backtest.page_task import StockResult, StockStatus

        result = StockResult(
            code="000000",
            name="无效股票",
            status=StockStatus.FAILED,
            error="股票代码不存在"
        )

        assert result.status == StockStatus.FAILED
        assert result.error == "股票代码不存在"
        assert result.return_rate is None


class TestTaskStatus:
    """任务状态枚举测试"""

    def test_task_status_values(self):
        """测试任务状态枚举值"""
        from backtest.page_task import TaskStatus

        assert TaskStatus.CREATED.value == "created"
        assert TaskStatus.RUNNING.value == "running"
        assert TaskStatus.PAUSED.value == "paused"
        assert TaskStatus.COMPLETED.value == "completed"
        assert TaskStatus.CANCELLED.value == "cancelled"

    def test_task_status_from_string(self):
        """测试从字符串创建任务状态"""
        from backtest.page_task import TaskStatus

        assert TaskStatus["CREATED"] == TaskStatus.CREATED
        assert TaskStatus["RUNNING"] == TaskStatus.RUNNING
        assert TaskStatus["COMPLETED"] == TaskStatus.COMPLETED


class TestStockStatus:
    """股票状态枚举测试"""

    def test_stock_status_values(self):
        """测试股票状态枚举值"""
        from backtest.page_task import StockStatus

        assert StockStatus.PENDING.value == "pending"
        assert StockStatus.RUNNING.value == "running"
        assert StockStatus.COMPLETED.value == "completed"
        assert StockStatus.FAILED.value == "failed"


class TestTaskManager:
    """TaskManager 测试"""

    def test_create_task(self):
        """测试创建任务"""
        from backtest.page_task import TaskManager

        with patch('builtins.open', MagicMock()):
            with patch('json.load', MagicMock(return_value=[])):
                with patch('json.dump', MagicMock()):
                    tm = TaskManager()
                    
                    task = tm.create_task(
                        name="测试任务",
                        stock_codes=["600036"],
                        strategy_ids=["st_basic"],
                        start_date="2022-01-01",
                        end_date="2024-12-31"
                    )

                    assert task.name == "测试任务"
                    assert "600036" in task.stock_codes
                    assert task.status.value == "created"

    def test_task_id_generation(self):
        """测试任务 ID 生成"""
        from backtest.page_task import TaskManager

        with patch('builtins.open', MagicMock()):
            with patch('json.load', MagicMock(return_value=[])):
                with patch('json.dump', MagicMock()):
                    tm = TaskManager()
                    
                    task = tm.create_task(
                        name="ID测试",
                        stock_codes=["600036"],
                        strategy_ids=["st_basic"],
                        start_date="2022-01-01",
                        end_date="2024-12-31"
                    )

                    assert task.id is not None
                    assert len(task.id) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
