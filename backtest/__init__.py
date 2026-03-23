from typing import Optional, List, Dict
from dataclasses import dataclass
import pandas as pd
import matplotlib.pyplot as plt

from data_source.fund_data_source import FundDataSource
from backtest.dca_backtest import DCABacktest, DCAParams, BacktestResult
from backtest.visualization import BacktestVisualizer


@dataclass
class BacktestConfig:
    """回测配置"""
    fund_code: str
    fund_name: str
    start_date: str
    end_date: str
    investment_amount: float
    frequency: str = 'monthly'
    data_source: str = None


class FundBacktester:
    """基金定投回测主类"""
    
    def __init__(self, data_source: str = None):
        from data_source.config import DATA_SOURCE
        self.data_source = data_source or DATA_SOURCE
        self.ds = FundDataSource(preferred_source=self.data_source)
        self.backtest = DCABacktest(self.ds)
        self.visualizer = BacktestVisualizer()
        print(f"使用数据源: {self.data_source}")
    
    def single_fund(self, config: BacktestConfig) -> Optional[BacktestResult]:
        """单个基金回测"""
        params = DCAParams(
            fund_code=config.fund_code,
            fund_name=config.fund_name,
            start_date=config.start_date,
            end_date=config.end_date,
            investment_amount=config.investment_amount,
            frequency=config.frequency
        )
        return self.backtest.run(params)
    
    def portfolio(self, funds: List[Dict], start_date: str, end_date: str, 
                  total_amount: float, frequency: str = 'monthly') -> Dict:
        """
        组合回测
        :param funds: [{"fund_code": "510300", "name": "沪深300", "weight": 0.5}, ...]
        """
        portfolio = []
        for f in funds:
            portfolio.append({
                'fund_code': f['fund_code'],
                'name': f['name'],
                'weight': f.get('weight', 1.0 / len(funds))
            })
        
        return self.backtest.run_portfolio(
            portfolio=portfolio,
            start_date=start_date,
            end_date=end_date,
            investment_amount=total_amount,
            frequency=frequency
        )
    
    def compare(self, funds: List[Dict], start_date: str, end_date: str, 
                amount: float, frequency: str = 'monthly') -> Dict[str, BacktestResult]:
        """对比多个基金"""
        results = {}
        for f in funds:
            config = BacktestConfig(
                fund_code=f['fund_code'],
                fund_name=f['name'],
                start_date=start_date,
                end_date=end_date,
                investment_amount=amount,
                frequency=frequency,
                data_source=self.data_source
            )
            result = self.single_fund(config)
            if result:
                results[f['name']] = result
        return results
    
    def visualize_single(self, result: BacktestResult, title: str = None, save_path: str = None):
        """可视化单个基金结果"""
        return self.visualizer.plot_single_fund(result, title, save_path)
    
    def visualize_portfolio(self, results: Dict, save_path: str = None):
        """可视化组合结果"""
        return self.visualizer.plot_portfolio(results, save_path)
    
    def visualize_comparison(self, results: Dict[str, BacktestResult], save_path: str = None):
        """可视化对比结果"""
        return self.visualizer.plot_comparison(results, save_path)


def quick_backtest(fund_code: str, fund_name: str = None, 
                   start_date: str = '2022-01-01', 
                   end_date: str = '2024-12-31',
                   amount: float = 1000,
                   data_source: str = None) -> Optional[BacktestResult]:
    """快速回测函数"""
    from data_source.config import DATA_SOURCE
    name_map = {
        '510300': '沪深300ETF', '510050': '上证50ETF', '510500': '中证500ETF',
        '159915': '创业板ETF', '588000': '科创50ETF', '518880': '黄金ETF',
        '159934': '易方达黄金ETF', '511010': '中债ETF', '161039': '纯债基金',
    }
    fund_name = fund_name or name_map.get(fund_code, fund_code)
    source = data_source or DATA_SOURCE
    
    tester = FundBacktester(data_source=source)
    config = BacktestConfig(
        fund_code=fund_code,
        fund_name=fund_name,
        start_date=start_date,
        end_date=end_date,
        investment_amount=amount,
        data_source=data_source
    )
    
    result = tester.single_fund(config)
    
    if result:
        print(f"\n{'='*50}")
        print(f"【{fund_name}】定投回测")
        print(f"{'='*50}")
        print(f"回测期: {start_date} ~ {end_date}")
        print(f"月定投: ¥{amount}")
        print(f"总投入: ¥{result.total_invested:,.0f}")
        print(f"最终值: ¥{result.final_value:,.0f}")
        print(f"总收益: {result.total_return:+,.0f} ({result.return_rate:+.2f}%)")
        print(f"年化收益: {result.annual_return:+.2f}%")
        print(f"最大回撤: {result.max_drawdown:.2f}%")
        
        tester.visualize_single(result, fund_name)
        return result
    else:
        print("获取数据失败，请尝试其他数据源 (akshare/baostock)")
        return None


if __name__ == "__main__":
    # 快速测试
    quick_backtest('510300', start_date='2022-01-01', end_date='2024-12-31', amount=1000)