# -*- coding: utf-8 -*-
"""
报告管理器单元测试
"""

import pytest
import json
import os
import tempfile
from pathlib import Path

from backtest.report_manager import ReportManager, Report


class TestReportManager:
    """ReportManager 测试"""
    
    def setup_method(self):
        """每个测试前创建临时目录"""
        self.temp_dir = tempfile.mkdtemp()
        self.rm = ReportManager(reports_dir=self.temp_dir)
    
    def teardown_method(self):
        """每个测试后清理"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_generate_name_no_strategy(self):
        """测试：无策略时报告名称"""
        name = self.rm.generate_name(
            fund_name="招商银行",
            fund_code="600036",
            start_date="2022-01-01",
            end_date="2024-12-31",
            strategy_params={'enable_stop_loss': False, 'enable_take_profit': False}
        )
        assert "招商银行" in name
        assert "600036" in name
        assert "无策略" in name
        print(f"✅ 无策略报告名称: {name}")
    
    def test_generate_name_with_take_profit(self):
        """测试：仅止盈时报告名称"""
        name = self.rm.generate_name(
            fund_name="招商银行",
            fund_code="600036",
            start_date="2022-01-01",
            end_date="2024-12-31",
            strategy_params={'enable_stop_loss': False, 'enable_take_profit': True, 'take_profit_rate': 0.20}
        )
        assert "止盈20%" in name
        print(f"✅ 止盈报告名称: {name}")
    
    def test_generate_name_with_stop_loss(self):
        """测试：仅止损时报告名称"""
        name = self.rm.generate_name(
            fund_name="招商银行",
            fund_code="600036",
            start_date="2022-01-01",
            end_date="2024-12-31",
            strategy_params={'enable_stop_loss': True, 'stop_loss_rate': 0.15, 'enable_take_profit': False}
        )
        assert "止损15%" in name
        print(f"✅ 止损报告名称: {name}")
    
    def test_generate_name_with_both(self):
        """测试：止盈止损都有时报告名称"""
        name = self.rm.generate_name(
            fund_name="招商银行",
            fund_code="600036",
            start_date="2022-01-01",
            end_date="2024-12-31",
            strategy_params={
                'enable_stop_loss': True, 'stop_loss_rate': 0.15,
                'enable_take_profit': True, 'take_profit_rate': 0.20
            }
        )
        assert "止盈20%" in name
        assert "止损15%" in name
        print(f"✅ 止盈止损报告名称: {name}")
    
    def test_save_and_load_report(self):
        """测试：保存和加载报告"""
        class MockResult:
            total_invested = 36000
            final_value = 42000
            total_return = 6000
            return_rate = 16.67
            annual_return = 7.8
            max_drawdown = -12.5
            investment_count = 36
            stop_loss_count = 0
            take_profit_count = 2
            trades = __import__('pandas').DataFrame({
                'date': ['2022-01-05', '2022-02-05'],
                'action': ['buy', 'buy'],
                'nav': [10.0, 10.5],
                'shares': [100, 95],
                'total_shares': [100, 195],
                'portfolio_value': [1000, 2047.5],
                'return_rate': [0, 4.75],
                'reason': ['定投', '定投']
            })
            strategy_params = {
                'fund_code': '600036',
                'fund_name': '招商银行',
                'start_date': '2022-01-01',
                'end_date': '2024-12-31',
                'frequency': 'monthly',
                'enable_stop_loss': False,
                'enable_take_profit': True,
                'take_profit_rate': 0.20
            }
        
        result = MockResult()
        report_id = self.rm.save_report(result)
        
        assert report_id is not None
        assert len(report_id) == 8
        
        report = self.rm.load_report(report_id)
        assert report is not None
        assert report.fund_code == "600036"
        assert report.fund_name == "招商银行"
        assert report.result['total_invested'] == 36000
        assert report.result['return_rate'] == 16.67
        assert len(report.trades) == 2
        print(f"✅ 保存加载报告成功: {report.name}")
    
    def test_list_reports(self):
        """测试：列出报告"""
        class MockResult:
            total_invested = 36000
            final_value = 42000
            total_return = 6000
            return_rate = 16.67
            annual_return = 7.8
            max_drawdown = -12.5
            investment_count = 36
            stop_loss_count = 0
            take_profit_count = 2
            trades = __import__('pandas').DataFrame({
                'date': ['2022-01-05'], 'action': ['buy'], 'nav': [10.0],
                'shares': [100], 'total_shares': [100], 'portfolio_value': [1000],
                'return_rate': [0], 'reason': ['定投']
            })
            strategy_params = {'fund_code': '600036', 'fund_name': '招商银行',
                            'start_date': '2022-01-01', 'end_date': '2024-12-31', 'frequency': 'monthly',
                            'enable_take_profit': True, 'take_profit_rate': 0.20}
        
        self.rm.save_report(MockResult())
        self.rm.save_report(MockResult())
        
        reports = self.rm.list_reports()
        assert len(reports) == 2
        print(f"✅ 列出报告: {len(reports)} 个")
    
    def test_list_reports_filter_by_code(self):
        """测试：按股票代码筛选报告"""
        class MockResult1:
            total_invested = 36000; final_value = 42000; total_return = 6000
            return_rate = 16.67; annual_return = 7.8; max_drawdown = -12.5
            investment_count = 36; stop_loss_count = 0; take_profit_count = 2
            trades = __import__('pandas').DataFrame({
                'date': ['2022-01-05'], 'action': ['buy'], 'nav': [10.0],
                'shares': [100], 'total_shares': [100], 'portfolio_value': [1000],
                'return_rate': [0], 'reason': ['定投']
            })
            strategy_params = {'fund_code': '600036', 'fund_name': '招商银行',
                            'start_date': '2022-01-01', 'end_date': '2024-12-31', 'frequency': 'monthly'}
        
        MockResult2 = type('MockResult2', (), {
            'total_invested': 36000, 'final_value': 42000, 'total_return': 6000,
            'return_rate': 16.67, 'annual_return': 7.8, 'max_drawdown': -12.5,
            'investment_count': 36, 'stop_loss_count': 0, 'take_profit_count': 2,
            'trades': __import__('pandas').DataFrame({
                'date': ['2022-01-05'], 'action': ['buy'], 'nav': [10.0],
                'shares': [100], 'total_shares': [100], 'portfolio_value': [1000],
                'return_rate': [0], 'reason': ['定投']
            }),
            'strategy_params': {'fund_code': '601318', 'fund_name': '中国平安',
                            'start_date': '2022-01-01', 'end_date': '2024-12-31', 'frequency': 'monthly'}
        })
        
        self.rm.save_report(MockResult1())
        self.rm.save_report(MockResult2())
        
        reports = self.rm.list_reports(fund_code='600036')
        assert len(reports) == 1
        assert reports[0].fund_code == '600036'
        print(f"✅ 按代码筛选报告成功")
    
    def test_delete_report(self):
        """测试：删除报告"""
        class MockResult:
            total_invested = 36000; final_value = 42000; total_return = 6000
            return_rate = 16.67; annual_return = 7.8; max_drawdown = -12.5
            investment_count = 36; stop_loss_count = 0; take_profit_count = 2
            trades = __import__('pandas').DataFrame({
                'date': ['2022-01-05'], 'action': ['buy'], 'nav': [10.0],
                'shares': [100], 'total_shares': [100], 'portfolio_value': [1000],
                'return_rate': [0], 'reason': ['定投']
            })
            strategy_params = {'fund_code': '600036', 'fund_name': '招商银行',
                            'start_date': '2022-01-01', 'end_date': '2024-12-31', 'frequency': 'monthly'}
        
        report_id = self.rm.save_report(MockResult())
        
        assert self.rm.load_report(report_id) is not None
        
        result = self.rm.delete_report(report_id)
        assert result is True
        
        assert self.rm.load_report(report_id) is None
        print(f"✅ 删除报告成功")
    

    
    def test_load_nonexistent_report(self):
        """测试：加载不存在的报告"""
        report = self.rm.load_report("nonexistent_id")
        assert report is None
        print(f"✅ 加载不存在报告返回None")


class TestReport:
    """Report 数据类测试"""
    
    def test_report_from_dict(self):
        """测试：从字典创建Report"""
        data = {
            'id': 'abc123',
            'name': '测试报告',
            'created_at': '2024-01-01 10:00:00',
            'fund_code': '600036',
            'fund_name': '招商银行',
            'start_date': '2022-01-01',
            'end_date': '2024-12-31',
            'investment_amount': 1000,
            'frequency': 'monthly',
            'strategy_params': {},
            'result': {'total_invested': 36000},
            'trades': []
        }
        
        report = Report.from_dict(data)
        assert report.id == 'abc123'
        assert report.fund_code == '600036'
        print(f"✅ Report.from_dict 成功")
    
    def test_report_to_dict(self):
        """测试：Report转字典"""
        report = Report(
            id='abc123',
            name='测试报告',
            created_at='2024-01-01 10:00:00',
            fund_code='600036',
            fund_name='招商银行',
            start_date='2022-01-01',
            end_date='2024-12-31',
            investment_amount=1000,
            frequency='monthly',
            strategy_params={},
            result={},
            trades=[]
        )
        
        data = report.to_dict()
        assert data['id'] == 'abc123'
        assert data['fund_code'] == '600036'
        print(f"✅ Report.to_dict 成功")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
