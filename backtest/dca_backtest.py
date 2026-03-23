import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Callable
from dataclasses import dataclass
import logging

from data_source.fund_data_source import FundDataSource, FUND_CODES

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class DCAParams:
    """定投参数"""
    fund_code: str
    fund_name: str
    start_date: str
    end_date: str
    investment_amount: float  # 每次投入金额
    frequency: str = "monthly"  # monthly, weekly, daily
    day_of_month: int = 1  # 每月几号定投
    day_of_week: int = 1  # 周几定投 (1=Monday)


@dataclass
class BacktestResult:
    """回测结果"""
    total_invested: float
    final_value: float
    total_return: float
    return_rate: float
    annual_return: float
    max_drawdown: float
    investment_count: int
    nav_data: pd.DataFrame
    trades: pd.DataFrame


class DCABacktest:
    """定期定额投资回测"""
    
    def __init__(self, data_source: FundDataSource = None):
        self.ds = data_source or FundDataSource()
    
    def run(self, params: DCAParams) -> Optional[BacktestResult]:
        """执行回测"""
        logger.info(f"开始回测: {params.fund_name} ({params.fund_code})")
        logger.info(f"参数: 投资额={params.investment_amount}, 频率={params.frequency}")
        
        nav_data = self.ds.get_fund_nav(
            params.fund_code,
            params.start_date.replace('-', ''),
            params.end_date.replace('-', '')
        )
        
        if nav_data is None or nav_data.empty:
            logger.error(f"无法获取基金数据: {params.fund_code}")
            return None
        
        nav_data = nav_data.copy()
        nav_data['date'] = pd.to_datetime(nav_data['date'])
        nav_data = nav_data.sort_values('date').reset_index(drop=True)
        nav_data['nav'] = pd.to_numeric(nav_data['nav'], errors='coerce')
        
        trades = self._generate_trades(nav_data, params)
        
        if trades.empty:
            logger.error("没有生成任何交易")
            return None
        
        trades = trades.merge(nav_data[['date', 'nav']], on='date', how='left')
        
        trades['shares'] = params.investment_amount / trades['nav']
        trades['total_shares'] = trades['shares'].cumsum()
        trades['total_invested'] = params.investment_amount * np.arange(1, len(trades) + 1)
        trades['portfolio_value'] = trades['total_shares'] * trades['nav']
        trades['return'] = trades['portfolio_value'] - trades['total_invested']
        trades['return_rate'] = trades['return'] / trades['total_invested'] * 100
        
        total_invested = trades['total_invested'].iloc[-1]
        final_value = trades['portfolio_value'].iloc[-1]
        total_return = final_value - total_invested
        
        years = (nav_data['date'].iloc[-1] - nav_data['date'].iloc[0]).days / 365
        
        return_rate = (final_value / total_invested - 1) * 100 if total_invested > 0 else 0
        annual_return = ((final_value / total_invested) ** (1/years) - 1) * 100 if years > 0 else 0
        
        max_drawdown = self._calculate_max_drawdown(trades['portfolio_value'])
        
        return BacktestResult(
            total_invested=total_invested,
            final_value=final_value,
            total_return=total_return,
            return_rate=return_rate,
            annual_return=annual_return,
            max_drawdown=max_drawdown,
            investment_count=len(trades),
            nav_data=nav_data,
            trades=trades
        )
    
    def _generate_trades(self, nav_data: pd.DataFrame, params: DCAParams) -> pd.DataFrame:
        """生成定投交易日期"""
        dates = []
        
        if params.frequency == "monthly":
            for date in nav_data['date']:
                if date.day >= params.day_of_month:
                    dates.append(date)
        elif params.frequency == "weekly":
            for date in nav_data['date']:
                if date.weekday() == params.day_of_week:
                    dates.append(date)
        else:
            dates = nav_data['date'].tolist()
        
        if not dates:
            dates = [nav_data['date'].iloc[0]]
        
        return pd.DataFrame({'date': dates})
    
    def _calculate_max_drawdown(self, values: pd.Series) -> float:
        """计算最大回撤"""
        peak = values.expanding(min_periods=1).max()
        drawdown = (values - peak) / peak * 100
        return drawdown.min()
    
    def run_portfolio(self, portfolio: List[Dict], start_date: str, end_date: str, 
                      investment_amount: float, frequency: str = "monthly") -> Dict:
        """
        组合回测
        :param portfolio: [{"fund_code": "510300", "name": "沪深300", "weight": 0.6}, ...]
        :return: 回测结果
        """
        results = {}
        total_invested = 0
        final_value = 0
        
        for fund in portfolio:
            params = DCAParams(
                fund_code=fund['fund_code'],
                fund_name=fund['name'],
                start_date=start_date,
                end_date=end_date,
                investment_amount=investment_amount * fund.get('weight', 1.0),
                frequency=frequency
            )
            result = self.run(params)
            if result:
                results[fund['name']] = result
                total_invested += result.total_invested
                final_value += result.final_value
        
        total_return = final_value - total_invested
        return_rate = (final_value / total_invested - 1) * 100 if total_invested > 0 else 0
        
        return {
            'total_invested': total_invested,
            'final_value': final_value,
            'total_return': total_return,
            'return_rate': return_rate,
            'individual_results': results
        }


def run_single_fund_backtest(fund_code: str, fund_name: str, start_date: str, end_date: str,
                               investment_amount: float = 1000, frequency: str = "monthly",
                               data_source: str = None) -> Optional[BacktestResult]:
    """便捷函数：运行单个基金回测"""
    ds = FundDataSource(preferred_source=data_source)
    backtest = DCABacktest(ds)
    
    params = DCAParams(
        fund_code=fund_code,
        fund_name=fund_name,
        start_date=start_date,
        end_date=end_date,
        investment_amount=investment_amount,
        frequency=frequency
    )
    
    return backtest.run(params)


if __name__ == "__main__":
    result = run_single_fund_backtest(
        fund_code="510300",
        fund_name="沪深300ETF",
        start_date="2022-01-01",
        end_date="2024-12-31",
        investment_amount=1000,
        data_source="akshare"
    )
    
    if result:
        print(f"总投入: {result.total_invested:.2f}")
        print(f"最终价值: {result.final_value:.2f}")
        print(f"总收益: {result.total_return:.2f}")
        print(f"收益率: {result.return_rate:.2f}%")
        print(f"年化收益: {result.annual_return:.2f}%")
        print(f"最大回撤: {result.max_drawdown:.2f}%")
        print(f"定投次数: {result.investment_count}")