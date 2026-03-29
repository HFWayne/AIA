# -*- coding: utf-8 -*-
"""
回测结果分析模块

提供:
- 风险指标计算 (夏普比率、卡玛比率、索提诺比率)
- 多策略/多标的对比分析
- 统计显著性检验
"""

import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class AnalysisMetrics:
    """分析指标数据类"""
    sharpe_ratio: float
    calmar_ratio: float
    sortino_ratio: float
    max_drawdown: float
    max_drawdown_duration: int
    volatility: float
    downside_volatility: float
    win_rate: float
    profit_loss_ratio: float
    avg_holding_period: float
    annual_return: float
    annual_volatility: float


class BacktestAnalyzer:
    """回测结果分析器"""

    def __init__(self, risk_free_rate: float = 0.03):
        self.risk_free_rate = risk_free_rate

    def analyze_trades(self, trades_df: pd.DataFrame, days_per_period: int = 21) -> AnalysisMetrics:
        """分析交易记录，计算各项指标

        Args:
            trades_df: 交易记录 DataFrame
            days_per_period: 每年交易日数 (默认21*12=252)

        Returns:
            AnalysisMetrics 对象
        """
        if trades_df is None or trades_df.empty:
            return self._empty_metrics()

        trades = trades_df.copy()

        returns = trades['return_rate'].dropna() if 'return_rate' in trades.columns else pd.Series([0])

        sharpe = self._calc_sharpe_ratio(returns, days_per_period)
        sortino = self._calc_sortino_ratio(returns, days_per_period)
        max_dd, dd_duration = self._calc_max_drawdown(trades)
        calmar = self._calc_calmar_ratio(returns, max_dd, days_per_period)

        volatility = returns.std() * np.sqrt(days_per_period) if len(returns) > 1 else 0
        downside_vol = returns[returns < 0].std() * np.sqrt(days_per_period) if len(returns[returns < 0]) > 0 else 0

        win_rate = self._calc_win_rate(trades)
        pl_ratio = self._calc_profit_loss_ratio(trades)

        annual_return = returns.mean() * days_per_period if len(returns) > 0 else 0
        annual_volatility = volatility

        return AnalysisMetrics(
            sharpe_ratio=sharpe,
            calmar_ratio=calmar,
            sortino_ratio=sortino,
            max_drawdown=max_dd,
            max_drawdown_duration=dd_duration,
            volatility=volatility,
            downside_volatility=downside_vol,
            win_rate=win_rate,
            profit_loss_ratio=pl_ratio,
            avg_holding_period=days_per_period,
            annual_return=annual_return,
            annual_volatility=annual_volatility
        )

    def _empty_metrics(self) -> AnalysisMetrics:
        """返回空指标"""
        return AnalysisMetrics(
            sharpe_ratio=0, calmar_ratio=0, sortino_ratio=0,
            max_drawdown=0, max_drawdown_duration=0, volatility=0,
            downside_volatility=0, win_rate=0, profit_loss_ratio=0,
            avg_holding_period=0, annual_return=0, annual_volatility=0
        )

    def _calc_sharpe_ratio(self, returns: pd.Series, periods: int) -> float:
        """计算夏普比率"""
        if len(returns) < 2 or returns.std() == 0:
            return 0

        excess_returns = returns.mean() - self.risk_free_rate / periods
        return excess_returns / returns.std() * np.sqrt(periods)

    def _calc_sortino_ratio(self, returns: pd.Series, periods: int) -> float:
        """计算索提诺比率"""
        if len(returns) < 2:
            return 0

        downside_returns = returns[returns < 0]
        if len(downside_returns) == 0 or downside_returns.std() == 0:
            return 0

        excess_returns = returns.mean() - self.risk_free_rate / periods
        return excess_returns / downside_returns.std() * np.sqrt(periods)

    def _calc_calmar_ratio(self, returns: pd.Series, max_dd: float, periods: int) -> float:
        """计算卡玛比率"""
        if max_dd == 0 or abs(max_dd) < 0.001:
            return 0

        annual_return = returns.mean() * periods
        return annual_return / abs(max_dd)

    def _calc_max_drawdown(self, trades: pd.DataFrame) -> tuple:
        """计算最大回撤及持续时间"""
        if 'portfolio_value' not in trades.columns or trades.empty:
            return 0, 0

        portfolio = trades['portfolio_value'].values
        running_max = np.maximum.accumulate(portfolio)
        drawdown = (portfolio - running_max) / running_max

        max_dd = abs(drawdown.min()) * 100

        dd_start = np.argmax(running_max)
        dd_end = np.argmin(portfolio)
        dd_duration = dd_end - dd_start

        return max_dd, dd_duration

    def _calc_win_rate(self, trades: pd.DataFrame) -> float:
        """计算胜率"""
        if 'return_rate' not in trades.columns or trades.empty:
            return 0

        wins = (trades['return_rate'] > 0).sum()
        return wins / len(trades) * 100 if len(trades) > 0 else 0

    def _calc_profit_loss_ratio(self, trades: pd.DataFrame) -> float:
        """计算盈亏比"""
        if 'return_rate' not in trades.columns or trades.empty:
            return 0

        gains = trades[trades['return_rate'] > 0]['return_rate'].mean()
        losses = abs(trades[trades['return_rate'] < 0]['return_rate'].mean())

        if losses == 0:
            return gains if gains > 0 else 0

        return gains / losses if losses > 0 else 0

    def get_metrics_summary(self, trades_df: pd.DataFrame) -> Dict[str, float]:
        """获取指标摘要字典"""
        metrics = self.analyze_trades(trades_df)

        return {
            '夏普比率': f"{metrics.sharpe_ratio:.2f}",
            '卡玛比率': f"{metrics.calmar_ratio:.2f}",
            '索提诺比率': f"{metrics.sortino_ratio:.2f}",
            '最大回撤': f"{metrics.max_drawdown:.2f}%",
            '年化收益率': f"{metrics.annual_return * 100:.2f}%",
            '年化波动率': f"{metrics.annual_volatility * 100:.2f}%",
            '胜率': f"{metrics.win_rate:.1f}%",
            '盈亏比': f"{metrics.profit_loss_ratio:.2f}",
        }


class ComparisonAnalyzer:
    """多策略/多标的对比分析器"""

    def __init__(self):
        self.analyzer = BacktestAnalyzer()

    def compare_results(self, results: Dict[str, Any]) -> pd.DataFrame:
        """对比多个回测结果

        Args:
            results: {名称: BacktestResult 或 trades_df}

        Returns:
            对比分析 DataFrame
        """
        comparison_data = []

        for name, result in results.items():
            if hasattr(result, 'trades'):
                trades = result.trades
            elif isinstance(result, pd.DataFrame):
                trades = result
            else:
                continue

            metrics = self.analyzer.analyze_trades(trades)

            row = {
                '名称': name,
                '总收益率': f"{result.return_rate:.2f}%" if hasattr(result, 'return_rate') else f"{trades['return_rate'].iloc[-1]:.2f}%",
                '年化收益率': f"{metrics.annual_return * 100:.2f}%",
                '夏普比率': f"{metrics.sharpe_ratio:.2f}",
                '卡玛比率': f"{metrics.calmar_ratio:.2f}",
                '最大回撤': f"{metrics.max_drawdown:.2f}%",
                '胜率': f"{metrics.win_rate:.1f}%",
            }
            comparison_data.append(row)

        return pd.DataFrame(comparison_data)

    def rank_strategies(self, results: Dict[str, Any], metric: str = 'sharpe') -> List[str]:
        """根据指标排名策略

        Args:
            results: 回测结果字典
            metric: 排序指标 ('sharpe', 'return', 'max_dd', 'calmar')

        Returns:
            策略名称列表（从高到低）
        """
        rankings = []

        for name, result in results.items():
            if hasattr(result, 'trades'):
                trades = result.trades
            elif isinstance(result, pd.DataFrame):
                trades = result
            else:
                continue

            metrics = self.analyzer.analyze_trades(trades)

            if metric == 'sharpe':
                score = metrics.sharpe_ratio
            elif metric == 'return':
                score = metrics.annual_return
            elif metric == 'max_dd':
                score = -metrics.max_drawdown
            elif metric == 'calmar':
                score = metrics.calmar_ratio
            else:
                score = 0

            rankings.append((name, score))

        rankings.sort(key=lambda x: x[1], reverse=True)
        return [name for name, _ in rankings]


def analyze_backtest(result, risk_free_rate: float = 0.03) -> Dict[str, float]:
    """便捷分析函数

    Args:
        result: BacktestResult 对象
        risk_free_rate: 无风险利率 (默认 3%)

    Returns:
        指标字典
    """
    analyzer = BacktestAnalyzer(risk_free_rate)
    return analyzer.get_metrics_summary(result.trades)


def compare_backtests(results: Dict[str, Any]) -> pd.DataFrame:
    """便捷对比函数

    Args:
        results: {名称: BacktestResult}

    Returns:
        对比 DataFrame
    """
    comp = ComparisonAnalyzer()
    return comp.compare_results(results)
