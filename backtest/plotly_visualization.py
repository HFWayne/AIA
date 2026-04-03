# -*- coding: utf-8 -*-
"""
基于 Plotly 的交互式图表模块
支持在浏览器中直接渲染，无需保存为图片
"""
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from typing import Optional, Dict, Any, List

from backtest.dca_backtest import BacktestResult


class PlotlyVisualizer:
    """基于 Plotly 的回测结果可视化"""

    @staticmethod
    def plot_single_fund(result: BacktestResult, title: Optional[str] = None) -> go.Figure:
        """绘制单个基金回测结果 (4子图布局)"""
        title = title or result.fund_name or result.fund_code

        trades = result.trades.copy()
        trades['date'] = pd.to_datetime(trades['date'])

        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=('投入与收益曲线', '收益率走势', '净值走势', 'K线图'),
            vertical_spacing=0.12,
            horizontal_spacing=0.08,
            specs=[
                [{"type": "scatter"}, {"type": "scatter"}],
                [{"type": "scatter"}, {"type": "Candlestick"} if result.nav_data is not None and all(col in result.nav_data.columns for col in ['open', 'high', 'low', 'close']) else [{"type": "scatter"}]]
            ]
        )

        fig.update_layout(
            title=dict(text=f'定投回测分析 - {title}', font=dict(size=16)),
            template='plotly_white',
            showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            height=700,
            hovermode='x unified'
        )

        fig.add_trace(
            go.Scatter(
                x=trades['date'],
                y=trades['total_invested'],
                name='累计投入',
                line=dict(color='blue', width=2),
                hovertemplate='日期: %{x|%Y-%m-%d}<br>累计投入: ¥%{y:,.2f}<extra></extra>'
            ),
            row=1, col=1
        )

        fig.add_trace(
            go.Scatter(
                x=trades['date'],
                y=trades['portfolio_value'],
                name='资产总值',
                line=dict(color='green', width=2),
                fill='tonexty' if 'total_invested' in trades.columns else None,
                hovertemplate='日期: %{x|%Y-%m-%d}<br>资产总值: ¥%{y:,.2f}<extra></extra>'
            ),
            row=1, col=1
        )

        fig.add_trace(
            go.Scatter(
                x=trades['date'],
                y=trades['return_rate'],
                name='收益率(%)',
                line=dict(color='purple', width=2),
                fill='tozeroy',
                fillcolor='rgba(128, 0, 128, 0.2)',
                hovertemplate='日期: %{x|%Y-%m-%d}<br>收益率: %{y:.2f}%<extra></extra>'
            ),
            row=1, col=2
        )

        fig.add_hline(y=0, line_dash="dash", line_color="gray", row=1, col=2)

        if result.nav_data is not None and 'date' in result.nav_data.columns:
            nav_df = result.nav_data.copy()
            nav_df['date'] = pd.to_datetime(nav_df['date'])

            fig.add_trace(
                go.Scatter(
                    x=nav_df['date'],
                    y=nav_df['nav'],
                    name='净值',
                    line=dict(color='orange', width=1.5),
                    hovertemplate='日期: %{x|%Y-%m-%d}<br>净值: ¥%{y:.4f}<extra></extra>'
                ),
                row=2, col=1
            )

        if result.nav_data is not None:
            if all(col in result.nav_data.columns for col in ['open', 'high', 'low', 'close']):
                kline_df = result.nav_data.copy()
                kline_df['date'] = pd.to_datetime(kline_df['date'])
                kline_df = kline_df.sort_values('date')

                fig.add_trace(
                    go.Candlestick(
                        x=kline_df['date'],
                        open=kline_df['open'],
                        high=kline_df['high'],
                        low=kline_df['low'],
                        close=kline_df['close'],
                        name='K线',
                        increasing_line_color='#ef5350',
                        decreasing_line_color='#26a69a',
                        increasing_fillcolor='#ef5350',
                        decreasing_fillcolor='#26a69a',
                        hovertemplate='日期: %{x|%Y-%m-%d}<br>开: %{open:.2f}<br>高: %{high:.2f}<br>低: %{low:.2f}<br>收: %{close:.2f}<extra></extra>'
                    ),
                    row=2, col=2
                )

                fig.update_xaxes(rangeslider_visible=False, row=2, col=2)
            else:
                fig.add_trace(
                    go.Scatter(
                        x=nav_df['date'],
                        y=nav_df['nav'],
                        name='净值',
                        line=dict(color='orange', width=1.5),
                        hovertemplate='日期: %{x|%Y-%m-%d}<br>净值: ¥%{y:.4f}<extra></extra>'
                    ),
                    row=2, col=2
                )

        for i in range(1, 3):
            for j in range(1, 3):
                fig.update_xaxes(tickformat='%Y-%m', dtick='M3', tickangle=45, row=i, col=j)
                fig.update_yaxes(gridcolor='#f0f0f0', row=i, col=j)

        return fig

    @staticmethod
    def plot_portfolio(portfolio_results: Dict[str, BacktestResult]) -> go.Figure:
        """绘制组合回测结果 (柱状图)"""
        names = list(portfolio_results.keys())
        invested = [portfolio_results[n].total_invested for n in names]
        final_values = [portfolio_results[n].final_value for n in names]
        return_rates = [portfolio_results[n].return_rate for n in names]

        fig = make_subplots(
            rows=1, cols=2,
            subplot_titles=('各股票投入与收益对比', '各股票收益率对比')
        )

        fig.add_trace(
            go.Bar(
                x=names,
                y=invested,
                name='总投入',
                marker_color='#4c78a8',
                text=[f'¥{v:,.0f}' for v in invested],
                textposition='outside',
                hovertemplate='股票: %{x}<br>总投入: ¥%{y:,.2f}<extra></extra>'
            ),
            row=1, col=1
        )

        fig.add_trace(
            go.Bar(
                x=names,
                y=final_values,
                name='最终价值',
                marker_color='#54a24b',
                text=[f'¥{v:,.0f}' for v in final_values],
                textposition='outside',
                hovertemplate='股票: %{x}<br>最终价值: ¥%{y:,.2f}<extra></extra>'
            ),
            row=1, col=1
        )

        colors = ['#54a24b' if r > 0 else '#e45756' for r in return_rates]
        fig.add_trace(
            go.Bar(
                x=names,
                y=return_rates,
                name='收益率',
                marker_color=colors,
                text=[f'{r:.2f}%' for r in return_rates],
                textposition='outside',
                hovertemplate='股票: %{x}<br>收益率: %{y:.2f}%<extra></extra>'
            ),
            row=1, col=2
        )

        fig.add_hline(y=0, line_dash="dash", line_color="gray", row=1, col=2)

        fig.update_layout(
            title=dict(text='股票组合定投回测分析', font=dict(size=16)),
            template='plotly_white',
            showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="right", x=1),
            height=450,
            hovermode='x unified'
        )

        fig.update_xaxes(tickangle=45, row=1, col=1)
        fig.update_xaxes(tickangle=45, row=1, col=2)
        fig.update_yaxes(title_text='金额(元)', gridcolor='#f0f0f0', row=1, col=1)
        fig.update_yaxes(title_text='收益率(%)', gridcolor='#f0f0f0', row=1, col=2)

        return fig

    @staticmethod
    def plot_comparison(results: Dict[str, BacktestResult]) -> go.Figure:
        """对比多个基金 (多图布局)"""
        names = list(results.keys())
        colors = ['#636efa', '#ef553b', '#00cc96', '#ab63fa', '#ffa15a', '#19d3f3']

        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=('资产总值对比', '收益率对比', '收益对比', '最大回撤对比'),
            vertical_spacing=0.15,
            horizontal_spacing=0.1
        )

        for i, (name, result) in enumerate(results.items()):
            trades = result.trades.copy()
            trades['date'] = pd.to_datetime(trades['date'])

            fig.add_trace(
                go.Scatter(
                    x=trades['date'],
                    y=trades['portfolio_value'],
                    name=name,
                    mode='lines',
                    line=dict(color=colors[i % len(colors)], width=2),
                    hovertemplate=f'{name}<br>日期: %{{x|%Y-%m-%d}}<br>资产: ¥%{{y:,.2f}}<extra></extra>'
                ),
                row=1, col=1
            )

            fig.add_trace(
                go.Scatter(
                    x=trades['date'],
                    y=trades['return_rate'],
                    name=name,
                    mode='lines',
                    line=dict(color=colors[i % len(colors)], width=2),
                    showlegend=False,
                    hovertemplate=f'{name}<br>日期: %{{x|%Y-%m-%d}}<br>收益率: %{{y:.2f}}%<extra></extra>'
                ),
                row=1, col=2
            )

        fig.add_hline(y=0, line_dash="dash", line_color="gray", row=1, col=2)

        return_rates = [results[n].return_rate for n in names]
        annual_returns = [results[n].annual_return for n in names]
        x = np.arange(len(names))

        fig.add_trace(
            go.Bar(
                x=names,
                y=return_rates,
                name='总收益率',
                marker_color='#4c78a8',
                text=[f'{r:.2f}%' for r in return_rates],
                textposition='outside',
                hovertemplate='股票: %{x}<br>总收益率: %{y:.2f}%<extra></extra>'
            ),
            row=2, col=1
        )

        fig.add_trace(
            go.Bar(
                x=names,
                y=annual_returns,
                name='年化收益率',
                marker_color='#f58518',
                text=[f'{r:.2f}%' for r in annual_returns],
                textposition='outside',
                hovertemplate='股票: %{x}<br>年化收益率: %{y:.2f}%<extra></extra>'
            ),
            row=2, col=1
        )

        max_drawdowns = [results[n].max_drawdown for n in names]
        colors_dd = ['#54a24b' if v <= 5 else '#f58518' if v <= 15 else '#e45756' for v in max_drawdowns]

        fig.add_trace(
            go.Bar(
                x=names,
                y=max_drawdowns,
                name='最大回撤',
                marker_color=colors_dd,
                text=[f'{v:.2f}%' for v in max_drawdowns],
                textposition='outside',
                hovertemplate='股票: %{x}<br>最大回撤: %{y:.2f}%<extra></extra>'
            ),
            row=2, col=2
        )

        fig.update_layout(
            title=dict(text='多股票定投对比分析', font=dict(size=16)),
            template='plotly_white',
            showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            height=650,
            hovermode='x unified'
        )

        for i in range(1, 3):
            for j in range(1, 3):
                fig.update_xaxes(tickangle=45, row=i, col=j)
                fig.update_yaxes(gridcolor='#f0f0f0', row=i, col=j)

        fig.update_yaxes(title_text='金额(元)', row=1, col=1)
        fig.update_yaxes(title_text='收益率(%)', row=1, col=2)
        fig.update_yaxes(title_text='收益率(%)', row=2, col=1)
        fig.update_yaxes(title_text='最大回撤(%)', row=2, col=2)

        return fig

    @staticmethod
    def plot_drawdown(trades: pd.DataFrame, name: str = '') -> go.Figure:
        """绘制回撤图"""
        trades = trades.copy()
        trades['date'] = pd.to_datetime(trades['date'])

        trades['peak'] = trades['portfolio_value'].cummax()
        trades['drawdown'] = (trades['portfolio_value'] - trades['peak']) / trades['peak'] * 100

        fig = go.Figure()

        fig.add_trace(
            go.Scatter(
                x=trades['date'],
                y=trades['drawdown'],
                name='回撤',
                mode='lines',
                fill='tozeroy',
                fillcolor='rgba(229, 87, 86, 0.3)',
                line=dict(color='#e45756', width=2),
                hovertemplate='日期: %{x|%Y-%m-%d}<br>回撤: %{y:.2f}%<extra></extra>'
            )
        )

        fig.update_layout(
            title=dict(text=f'回撤分析 - {name}' if name else '回撤分析', font=dict(size=14)),
            template='plotly_white',
            showlegend=False,
            height=300,
            hovermode='x unified',
            yaxis_title='回撤(%)',
            xaxis=dict(tickformat='%Y-%m', dtick='M3', tickangle=45)
        )

        fig.add_hline(y=0, line_dash="dash", line_color="gray")

        return fig

    @staticmethod
    def plot_portfolio_comparison(
        names: List[str],
        invested: List[float],
        final: List[float],
        returns: List[float],
        annual: List[float],
        drawdowns: List[float]
    ) -> go.Figure:
        """绘制报告对比图表 (用于 page_compare)"""
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=('投入与最终价值对比', '总收益率对比', '年化收益率对比', '最大回撤对比'),
            vertical_spacing=0.15,
            horizontal_spacing=0.1
        )

        fig.add_trace(
            go.Bar(
                x=names,
                y=invested,
                name='总投入',
                marker_color='#4c78a8',
                text=[f'¥{v:,.0f}' for v in invested],
                textposition='outside',
                hovertemplate='股票: %{x}<br>总投入: ¥%{y:,.2f}<extra></extra>'
            ),
            row=1, col=1
        )

        fig.add_trace(
            go.Bar(
                x=names,
                y=final,
                name='最终价值',
                marker_color='#54a24b',
                text=[f'¥{v:,.0f}' for v in final],
                textposition='outside',
                hovertemplate='股票: %{x}<br>最终价值: ¥%{y:,.2f}<extra></extra>'
            ),
            row=1, col=1
        )

        colors_ret = ['#54a24b' if r >= 0 else '#e45756' for r in returns]
        fig.add_trace(
            go.Bar(
                x=names,
                y=returns,
                name='总收益率',
                marker_color=colors_ret,
                text=[f'{r:.2f}%' for r in returns],
                textposition='outside',
                hovertemplate='股票: %{x}<br>总收益率: %{y:.2f}%<extra></extra>'
            ),
            row=1, col=2
        )

        fig.add_hline(y=0, line_dash="dash", line_color="gray", row=1, col=2)

        colors_annual = ['#54a24b' if r >= 0 else '#e45756' for r in annual]
        fig.add_trace(
            go.Bar(
                x=names,
                y=annual,
                name='年化收益率',
                marker_color=colors_annual,
                text=[f'{r:.2f}%' for r in annual],
                textposition='outside',
                hovertemplate='股票: %{x}<br>年化收益率: %{y:.2f}%<extra></extra>'
            ),
            row=2, col=1
        )

        fig.add_hline(y=0, line_dash="dash", line_color="gray", row=2, col=1)

        colors_dd = ['#54a24b' if v <= 5 else '#f58518' if v <= 15 else '#e45756' for v in drawdowns]
        fig.add_trace(
            go.Bar(
                x=names,
                y=drawdowns,
                name='最大回撤',
                marker_color=colors_dd,
                text=[f'{v:.2f}%' for v in drawdowns],
                textposition='outside',
                hovertemplate='股票: %{x}<br>最大回撤: %{y:.2f}%<extra></extra>'
            ),
            row=2, col=2
        )

        fig.update_layout(
            title=dict(text='报告对比分析', font=dict(size=16)),
            template='plotly_white',
            showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            height=600,
            hovermode='x unified'
        )

        for i in range(1, 3):
            for j in range(1, 3):
                fig.update_xaxes(tickangle=15, row=i, col=j)
                fig.update_yaxes(gridcolor='#f0f0f0', row=i, col=j)

        fig.update_yaxes(title_text='金额(元)', row=1, col=1)
        fig.update_yaxes(title_text='收益率(%)', row=1, col=2)
        fig.update_yaxes(title_text='收益率(%)', row=2, col=1)
        fig.update_yaxes(title_text='最大回撤(%)', row=2, col=2)

        return fig


def visualize_backtest_plotly(result: BacktestResult, title: Optional[str] = None) -> go.Figure:
    """便捷函数：使用 Plotly 可视化单个基金回测结果"""
    return PlotlyVisualizer.plot_single_fund(result, title)


if __name__ == "__main__":
    from backtest.dca_backtest import run_single_fund_backtest

    result = run_single_fund_backtest(
        fund_code="600036",
        fund_name="招商银行",
        start_date="2022-01-01",
        end_date="2024-12-31",
        investment_amount=1000,
        data_source="tushare"
    )

    if result:
        fig = visualize_backtest_plotly(result, "招商银行")
        fig.show()
