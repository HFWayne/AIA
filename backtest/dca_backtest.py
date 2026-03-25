import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Tuple
from dataclasses import dataclass, field
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
    investment_amount: float
    frequency: str = "monthly"
    day_of_month: int = 1
    day_of_week: int = 0
    
    enable_stop_loss: bool = False
    stop_loss_rate: float = 0.15
    
    enable_take_profit: bool = False
    take_profit_rate: float = 0.20
    max_drawdown_threshold: float = 0.10
    
    stop_loss_sell_ratio: float = 1.0
    take_profit_sell_ratio: float = 0.5
    
    enable_dip_buy: bool = False
    dip_buy_tier1_threshold: float = -0.03
    dip_buy_tier1_amount: float = 1000.0
    dip_buy_tier2_threshold: float = -0.05
    dip_buy_tier2_amount: float = 1000.0
    dip_buy_tier3_threshold: float = -0.07
    dip_buy_tier3_amount: float = 1000.0
    
    enable_yield_boost: bool = False
    yield_boost_trigger: float = -0.20
    yield_boost_recover: float = -0.10
    yield_boost_amount: float = 1000.0


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
    
    stop_loss_count: int = 0
    take_profit_count: int = 0
    dip_buy_count: int = 0
    dip_buy_amount: float = 0.0
    boost_count: int = 0
    boost_amount: float = 0.0
    strategy_params: dict = field(default_factory=dict)


class DCABacktest:
    """定期定额投资回测（支持止损止盈策略）"""
    
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
        nav_data = nav_data.dropna(subset=['nav'])
        
        trades = self._run_backtest_with_strategy(nav_data, params)
        
        if trades.empty:
            logger.error("没有生成任何交易")
            return None
        
        trades = trades.sort_values('date').reset_index(drop=True)
        
        total_invested = trades['total_invested'].iloc[-1]
        final_value = trades['portfolio_value'].iloc[-1]
        total_return = final_value - total_invested
        
        years = (nav_data['date'].iloc[-1] - nav_data['date'].iloc[0]).days / 365
        return_rate = (final_value / total_invested - 1) * 100 if total_invested > 0 else 0
        annual_return = ((final_value / total_invested) ** (1/years) - 1) * 100 if years > 0 else 0
        max_drawdown = self._calculate_max_drawdown(trades['portfolio_value'])
        
        stop_loss_count = len(trades[trades['action'] == 'sell_stop'])
        take_profit_count = len(trades[trades['action'] == 'sell_profit'])
        
        strategy_params = {
            'enable_stop_loss': params.enable_stop_loss,
            'stop_loss_rate': params.stop_loss_rate,
            'stop_loss_sell_ratio': params.stop_loss_sell_ratio,
            'enable_take_profit': params.enable_take_profit,
            'take_profit_rate': params.take_profit_rate,
            'max_drawdown_threshold': params.max_drawdown_threshold,
            'take_profit_sell_ratio': params.take_profit_sell_ratio,
            'enable_dip_buy': params.enable_dip_buy,
            'enable_yield_boost': params.enable_yield_boost,
        }
        
        dip_buy_count = len(trades[trades['action'] == 'buy_dip'])
        dip_buy_amount = trades[trades['action'] == 'buy_dip']['total_invested'].sum() if dip_buy_count > 0 else 0
        boost_count = len(trades[trades['action'] == 'buy_boost'])
        boost_amount = trades[trades['action'] == 'buy_boost']['total_invested'].sum() if boost_count > 0 else 0
        
        return BacktestResult(
            total_invested=total_invested,
            final_value=final_value,
            total_return=total_return,
            return_rate=return_rate,
            annual_return=annual_return,
            max_drawdown=max_drawdown,
            investment_count=len(trades[trades['action'] == 'buy']),
            nav_data=nav_data,
            trades=trades,
            stop_loss_count=stop_loss_count,
            take_profit_count=take_profit_count,
            dip_buy_count=dip_buy_count,
            dip_buy_amount=dip_buy_amount,
            boost_count=boost_count,
            boost_amount=boost_amount,
            strategy_params=strategy_params
        )
    
    def _run_backtest_with_strategy(self, nav_data: pd.DataFrame, params: DCAParams) -> pd.DataFrame:
        """执行带止损止盈策略的回测"""
        
        trade_dates = self._get_trade_dates(nav_data, params)
        trade_dates_set = set(trade_dates)
        
        holdings = 0.0
        total_invested = 0.0
        historical_high = 0.0
        in_watch_mode = False
        boost_active = False
        prev_invested = 0.0
        
        dip_buy_tiers = [
            {'threshold': params.dip_buy_tier1_threshold, 'amount': params.dip_buy_tier1_amount},
            {'threshold': params.dip_buy_tier2_threshold, 'amount': params.dip_buy_tier2_amount},
            {'threshold': params.dip_buy_tier3_threshold, 'amount': params.dip_buy_tier3_amount},
        ] if params.enable_dip_buy else []
        
        records = []
        
        for idx, row in nav_data.iterrows():
            current_date = row['date']
            current_nav = row['nav']
            is_trade_day = current_date in trade_dates_set
            
            prev_nav = nav_data.iloc[idx - 1]['nav'] if idx > 0 else None
            
            current_value = holdings * current_nav
            current_return = (current_value - total_invested) / total_invested if total_invested > 0 else 0
            return_rate = current_return * 100
            
            action = 'hold'
            reason = ''
            shares = 0.0
            
            if params.enable_stop_loss and holdings > 0 and current_return <= -params.stop_loss_rate:
                sell_shares = holdings * params.stop_loss_sell_ratio
                if sell_shares > 0:
                    holdings -= sell_shares
                    action = 'sell_stop'
                    reason = f'止损({return_rate:.1f}%)'
                    logger.info(f"触发止损: {current_date}, 收益率={return_rate:.2f}%")
            
            if params.enable_take_profit and holdings > 0:
                if not in_watch_mode and is_trade_day and current_return >= params.take_profit_rate:
                    in_watch_mode = True
                    historical_high = current_nav
                    logger.info(f"进入观察模式: {current_date}, 收益率={return_rate:.2f}%")
                
                if in_watch_mode:
                    if current_nav > historical_high:
                        historical_high = current_nav
                    
                    drawdown = (historical_high - current_nav) / historical_high if historical_high > 0 else 0
                    
                    if drawdown >= params.max_drawdown_threshold:
                        sell_shares = holdings * params.take_profit_sell_ratio
                        if sell_shares > 0:
                            holdings -= sell_shares
                            action = 'sell_profit'
                            reason = f'止盈(回撤{int(drawdown*100)}%)'
                            logger.info(f"触发止盈: {current_date}, 回撤={drawdown*100:.2f}%")
                            
                            if holdings <= 0.01:
                                in_watch_mode = False
            
            dip_triggered = False
            dip_amount = 0.0
            invest_amount = 0.0
            
            if params.enable_dip_buy and prev_nav and holdings > 0 and action == 'hold':
                daily_change = (current_nav - prev_nav) / prev_nav
                
                for tier in dip_buy_tiers:
                    if daily_change <= tier['threshold']:
                        dip_amount = tier['amount']
                        invest_amount = dip_amount
                        buy_shares = dip_amount / current_nav
                        holdings += buy_shares
                        total_invested += dip_amount
                        dip_triggered = True
                        action = 'buy_dip'
                        reason = f'大跌补仓({daily_change*100:.1f}%)'
                        logger.info(f"触发大跌补仓: {current_date}, 跌幅={daily_change*100:.2f}%")
                        break
            
            if params.enable_yield_boost and holdings > 0 and action == 'hold':
                if current_return <= params.yield_boost_trigger and not boost_active:
                    boost_active = True
                    logger.info(f"触发增额定投: {current_date}, 收益率={return_rate:.2f}%")
                elif current_return >= params.yield_boost_recover and boost_active:
                    boost_active = False
                    logger.info(f"恢复原价投: {current_date}, 收益率={return_rate:.2f}%")
            
            if is_trade_day and action == 'hold':
                buy_amount = params.investment_amount
                if boost_active:
                    buy_amount += params.yield_boost_amount
                
                invest_amount = buy_amount
                buy_shares = buy_amount / current_nav
                holdings += buy_shares
                total_invested += buy_amount
                
                if boost_active:
                    action = 'buy_boost'
                    reason = f'增额定投({return_rate:.1f}%)'
                else:
                    action = 'buy'
                    reason = '定投'
            
            current_value = holdings * current_nav
            
            if action.startswith('buy'):
                shares = invest_amount / current_nav
            elif action.startswith('sell'):
                shares = -(records[-1]['total_shares'] - holdings) if records else 0
            else:
                shares = 0.0
            
            records.append({
                'date': current_date,
                'nav': current_nav,
                'action': action,
                'reason': reason,
                'shares': shares,
                'invest_amount': invest_amount,
                'total_shares': holdings,
                'total_invested': total_invested,
                'portfolio_value': current_value,
                'return_rate': return_rate
            })
        
        df = pd.DataFrame(records)
        df['shares'] = df['shares'].fillna(0)
        
        return df[df['action'] != 'hold']
    
    def _get_trade_dates(self, nav_data: pd.DataFrame, params: DCAParams) -> List:
        """获取定投日期列表"""
        dates = []
        
        if params.frequency == "monthly":
            dates = self._get_monthly_trade_dates(nav_data, params.day_of_month)
        elif params.frequency == "weekly":
            dates = self._get_weekly_trade_dates(nav_data, params.day_of_week)
        else:
            dates = nav_data['date'].tolist()
        
        return dates if dates else [nav_data['date'].iloc[0]]
    
    def _get_monthly_trade_dates(self, nav_data: pd.DataFrame, day_of_month: int) -> List:
        """获取每月定投日期，支持顺延到最近交易日
        
        如果指定日期（如每月1日）恰好是周末/节假日没有交易数据，
        则顺延到该月第一个可用的交易日
        """
        if nav_data.empty:
            return []
        
        nav_data = nav_data.sort_values('date').reset_index(drop=True)
        
        selected_dates = []
        
        nav_data['month_key'] = nav_data['date'].dt.to_period('M')
        
        for month_key, group in nav_data.groupby('month_key'):
            group = group.sort_values('date')
            
            target_day = group[group['date'].dt.day == day_of_month]
            if not target_day.empty:
                selected_dates.append(target_day['date'].iloc[0])
            else:
                selected_dates.append(group['date'].iloc[0])
        
        return sorted(selected_dates)
    
    def _get_weekly_trade_dates(self, nav_data: pd.DataFrame, day_of_week: int) -> List:
        """获取每周定投日期，支持顺延到最近交易日
        
        如果指定周几（如周一）恰好是节假日没有交易数据，
        则顺延到该周第一个可用的交易日
        """
        if nav_data.empty:
            return []
        
        nav_data = nav_data.sort_values('date').reset_index(drop=True)
        
        selected_dates = []
        
        nav_data['week_key'] = nav_data['date'].dt.isocalendar().week
        nav_data['year'] = nav_data['date'].dt.year
        
        for _, row in nav_data.iterrows():
            date = row['date']
            week_key = (date.year, date.isocalendar().week)
            
            if date.weekday() == day_of_week:
                selected_dates.append(date)
            elif not any(d.isocalendar().week == week_key[1] and d.year == week_key[0] for d in selected_dates):
                first_day_of_week = nav_data[
                    (nav_data['date'].dt.year == week_key[0]) & 
                    (nav_data['date'].dt.isocalendar().week == week_key[1])
                ]
                if not first_day_of_week.empty:
                    selected_dates.append(first_day_of_week['date'].iloc[0])
        
        selected_dates.sort()
        
        final_dates = []
        seen_weeks = set()
        for d in selected_dates:
            week_key = (d.year, d.isocalendar().week)
            if week_key not in seen_weeks:
                final_dates.append(d)
                seen_weeks.add(week_key)
        
        return final_dates
    
    def _calculate_max_drawdown(self, values: pd.Series) -> float:
        """计算最大回撤"""
        peak = values.expanding(min_periods=1).max()
        drawdown = (values - peak) / peak * 100
        return drawdown.min()
    
    def run_portfolio(self, portfolio: List[Dict], start_date: str, end_date: str, 
                      investment_amount: float, frequency: str = "monthly") -> Dict:
        """组合回测"""
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
                               data_source: str = None, **strategy_kwargs) -> Optional[BacktestResult]:
    """便捷函数：运行单个基金回测"""
    ds = FundDataSource(preferred_source=data_source)
    backtest = DCABacktest(ds)
    
    params = DCAParams(
        fund_code=fund_code,
        fund_name=fund_name,
        start_date=start_date,
        end_date=end_date,
        investment_amount=investment_amount,
        frequency=frequency,
        **strategy_kwargs
    )
    
    return backtest.run(params)


if __name__ == "__main__":
    result = run_single_fund_backtest(
        fund_code="600036",
        fund_name="招商银行",
        start_date="2022-01-01",
        end_date="2024-12-31",
        investment_amount=1000,
        enable_stop_loss=True,
        stop_loss_rate=0.15,
        enable_take_profit=True,
        take_profit_rate=0.20,
        max_drawdown_threshold=0.10,
        take_profit_sell_ratio=0.5
    )
    
    if result:
        print(f"总投入: {result.total_invested:.2f}")
        print(f"最终价值: {result.final_value:.2f}")
        print(f"总收益: {result.total_return:.2f}")
        print(f"收益率: {result.return_rate:.2f}%")
        print(f"年化收益: {result.annual_return:.2f}%")
        print(f"最大回撤: {result.max_drawdown:.2f}%")
        print(f"定投次数: {result.investment_count}")
        print(f"止损次数: {result.stop_loss_count}")
        print(f"止盈次数: {result.take_profit_count}")
