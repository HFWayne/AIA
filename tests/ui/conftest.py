# -*- coding: utf-8 -*-
"""
Streamlit UI 自动化测试框架

使用方法:
    pytest tests/ui/ -v              # 运行所有UI测试
    pytest tests/ui/ -v -k single    # 只运行单页面测试
    pytest tests/ui/ --html=report.html  # 生成HTML报告
"""

import pytest
import sys
import os
import time
import logging
from datetime import datetime, date
from typing import Dict, Any, Optional, List
from unittest.mock import Mock, patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class StreamlitTestHelper:
    """Streamlit 测试辅助类"""

    def __init__(self):
        self.session_state = {}
        self.messages = []
        self._component_counters = {}

    def reset(self):
        """重置测试状态"""
        self.session_state = {}
        self.messages = []
        self._component_counters = {}

    def set_session_state(self, key: str, value: Any):
        """设置 session state"""
        self.session_state[key] = value
        logger.debug(f"Session state set: {key} = {value}")

    def get_session_state(self, key: str, default: Any = None) -> Any:
        """获取 session state"""
        return self.session_state.get(key, default)

    def add_message(self, level: str, message: str):
        """记录消息"""
        self.messages.append({
            'level': level,
            'message': message,
            'timestamp': datetime.now()
        })

    def get_messages(self, level: Optional[str] = None) -> List[Dict]:
        """获取消息"""
        if level:
            return [m for m in self.messages if m['level'] == level]
        return self.messages

    def assert_message_exists(self, text: str, level: str = None):
        """断言消息存在"""
        msgs = self.get_messages(level)
        found = any(text in m['message'] for m in msgs)
        assert found, f"Message '{text}' not found in {msgs}"

    def increment_counter(self, component: str) -> int:
        """组件计数器，用于追踪组件渲染"""
        if component not in self._component_counters:
            self._component_counters[component] = 0
        self._component_counters[component] += 1
        return self._component_counters[component]


class BacktestTestHelper:
    """回测功能测试辅助类"""

    @staticmethod
    def create_mock_backtest_result(
        fund_code: str = "000001",
        fund_name: str = "平安银行",
        total_invested: float = 12000.0,
        final_value: float = 15000.0,
        investment_count: int = 12,
        return_rate: float = 25.0,
        annual_return: float = 8.5,
        max_drawdown: float = 15.0,
        stop_loss_count: int = 0,
        take_profit_count: int = 2
    ):
        """创建模拟回测结果"""
        import pandas as pd
        from backtest.dca_backtest import BacktestResult

        trades = pd.DataFrame({
            'date': pd.date_range('2022-01-01', periods=investment_count, freq='MS'),
            'action': ['buy'] * investment_count,
            'nav': [10.0 + i * 0.5 for i in range(investment_count)],
            'shares': [100.0] * investment_count,
            'invest_amount': [1000.0] * investment_count,
            'total_shares': [100.0 * (i + 1) for i in range(investment_count)],
            'portfolio_value': [1000.0 * (i + 1) * (10.0 + i * 0.5) for i in range(investment_count)],
            'return_rate': [5.0 * i for i in range(investment_count)],
            'reason': [''] * investment_count
        })

        return BacktestResult(
            total_invested=total_invested,
            final_value=final_value,
            total_return=final_value - total_invested,
            return_rate=return_rate,
            annual_return=annual_return,
            max_drawdown=max_drawdown,
            investment_count=investment_count,
            stop_loss_count=stop_loss_count,
            take_profit_count=take_profit_count,
            nav_data=trades,
            trades=trades,
            strategy_params={
                'fund_code': fund_code,
                'fund_name': fund_name,
                'start_date': '2022-01-01',
                'end_date': '2022-12-31',
                'investment_amount': 1000.0,
                'frequency': 'monthly'
            }
        )


class DatabaseTestHelper:
    """数据库测试辅助类"""

    @staticmethod
    def clear_test_data():
        """清理测试数据"""
        from data_source.db.connection import get_db_session
        from data_source.db.models import Report, Watchlist, WatchlistStock, StrategyTemplateModel

        with get_db_session() as session:
            session.query(Report).delete()
            session.query(WatchlistStock).delete()
            session.query(Watchlist).delete()
            session.query(StrategyTemplateModel).delete(synchronize_session=False)

    @staticmethod
    def verify_tables_exist() -> bool:
        """验证表是否存在"""
        from data_source.db.connection import get_engine
        from sqlalchemy import text

        engine = get_engine()
        required_tables = [
            'reports', 'watchlists', 'watchlist_stocks',
            'strategy_templates', 'stocks', 'daily_kline'
        ]

        with engine.connect() as conn:
            result = conn.execute(text("SHOW TABLES"))
            existing_tables = [row[0] for row in result]

        missing = [t for t in required_tables if t not in existing_tables]
        if missing:
            logger.error(f"Missing tables: {missing}")
            return False
        return True


class CacheTestHelper:
    """缓存测试辅助类"""

    @staticmethod
    def clear_all_cache():
        """清空所有缓存"""
        from data_source.cache import get_cache

        cache = get_cache()
        if cache.is_available():
            cache.clear_pattern("*")

    @staticmethod
    def get_cache_stats() -> Dict[str, Any]:
        """获取缓存统计"""
        from data_source.cache import get_cache

        cache = get_cache()
        if cache.is_available():
            return cache.get_stats()
        return {'status': 'unavailable'}


@pytest.fixture(scope="session")
def test_helper():
    """测试辅助实例"""
    return StreamlitTestHelper()


@pytest.fixture(scope="session")
def backtest_helper():
    """回测辅助实例"""
    return BacktestTestHelper()


@pytest.fixture(scope="function")
def clean_database():
    """每个测试前清理数据库"""
    DatabaseTestHelper.clear_test_data()
    yield
    DatabaseTestHelper.clear_test_data()


@pytest.fixture(scope="function")
def clean_cache():
    """每个测试前清空缓存"""
    CacheTestHelper.clear_all_cache()
    yield


@pytest.fixture(scope="session")
def verify_db():
    """验证数据库配置"""
    assert DatabaseTestHelper.verify_tables_exist(), "数据库表未正确创建"
    return True


@pytest.fixture
def mock_tushare():
    """Mock Tushare API"""
    with patch('data_source.fund_data_source.tushare') as mock:
        mock_pro = Mock()
        mock_pro.fund_nav.return_value = Mock(
            code='200',
            data=Mock(
                items=[['2022-01-01', '1.0'], ['2022-02-01', '1.1']],
                fields=['date', 'nav']
            )
        )
        mock.pro.return_value = mock_pro
        yield mock


@pytest.fixture
def mock_akshare():
    """Mock AkShare"""
    with patch('data_source.fund_data_source.ak') as mock:
        mock.stock_zh_a_hist.return_value = Mock(
            empty=False,
            __iter__=Mock(return_value=iter([]))
        )
        yield mock


def pytest_configure(config):
    """Pytest 配置"""
    config.addinivalue_line(
        "markers", "ui: UI页面测试"
    )
    config.addinivalue_line(
        "markers", "db: 数据库测试"
    )
    config.addinivalue_line(
        "markers", "cache: 缓存测试"
    )
    config.addinivalue_line(
        "markers", "integration: 集成测试"
    )


def pytest_collection_modifyitems(config, items):
    """修改测试收集"""
    for item in items:
        if "ui" in item.nodeid:
            item.add_marker(pytest.mark.ui)
        if "db" in item.nodeid:
            item.add_marker(pytest.mark.db)
        if "cache" in item.nodeid:
            item.add_marker(pytest.mark.cache)
        if "integration" in item.nodeid:
            item.add_marker(pytest.mark.integration)
