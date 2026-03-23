import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
import numpy as np
from typing import Optional, List, Dict
from datetime import datetime
import os

from backtest.dca_backtest import BacktestResult, DCAParams

plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'SimSun']
plt.rcParams['axes.unicode_minus'] = False
plt.rcParams['figure.facecolor'] = 'white'
plt.rcParams['axes.facecolor'] = 'white'


class BacktestVisualizer:
    """回测结果可视化"""
    
    def __init__(self, output_dir: str = "output"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
    
    def plot_single_fund(self, result: BacktestResult, title: str = None, save_path: str = None):
        """绘制单个基金回测结果"""
        fig = plt.figure(figsize=(16, 12))
        
        title = title or result.trades['date'].iloc[0].strftime('%Y-%m-%d')
        
        trades = result.trades.copy()
        trades['date'] = pd.to_datetime(trades['date'])
        
        grid = fig.add_gridspec(3, 2, hspace=0.3, wspace=0.25)
        
        ax1 = fig.add_subplot(grid[0, 0])
        ax1.plot(trades['date'], trades['total_invested'], label='累计投入', color='blue', linewidth=2)
        ax1.plot(trades['date'], trades['portfolio_value'], label='资产总值', color='green', linewidth=2)
        ax1.fill_between(trades['date'], trades['total_invested'], trades['portfolio_value'], 
                         where=trades['portfolio_value'] >= trades['total_invested'],
                         alpha=0.3, color='green', label='盈利')
        ax1.fill_between(trades['date'], trades['total_invested'], trades['portfolio_value'],
                         where=trades['portfolio_value'] < trades['total_invested'],
                         alpha=0.3, color='red', label='亏损')
        ax1.set_title('投入与收益曲线', fontsize=12)
        ax1.set_xlabel('日期')
        ax1.set_ylabel('金额')
        ax1.legend(loc='upper left')
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
        ax1.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
        plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45)
        ax1.grid(True, alpha=0.3)
        
        ax2 = fig.add_subplot(grid[0, 1])
        ax2.plot(trades['date'], trades['return_rate'], color='purple', linewidth=2)
        ax2.axhline(y=0, color='black', linestyle='--', alpha=0.5)
        ax2.fill_between(trades['date'], 0, trades['return_rate'], 
                         where=trades['return_rate'] >= 0, alpha=0.3, color='green')
        ax2.fill_between(trades['date'], 0, trades['return_rate'],
                         where=trades['return_rate'] < 0, alpha=0.3, color='red')
        ax2.set_title('收益率走势', fontsize=12)
        ax2.set_xlabel('日期')
        ax2.set_ylabel('收益率 (%)')
        ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
        ax2.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
        plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45)
        ax2.grid(True, alpha=0.3)
        
        ax3 = fig.add_subplot(grid[1, 0])
        ax3.plot(result.nav_data['date'], result.nav_data['nav'], color='orange', linewidth=1.5)
        ax3.set_title(f'{title} 净值走势', fontsize=12)
        ax3.set_xlabel('日期')
        ax3.set_ylabel('价格')
        ax3.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
        ax3.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
        plt.setp(ax3.xaxis.get_majorticklabels(), rotation=45)
        ax3.grid(True, alpha=0.3)
        
        ax4 = fig.add_subplot(grid[1, 1])
        if 'high' in result.nav_data.columns and 'low' in result.nav_data.columns:
            self._plot_kline(ax4, result.nav_data)
            ax4.set_title(f'{title} K线图', fontsize=12)
        else:
            ax4.text(0.5, 0.5, 'K线数据不可用\n(仅支持股票代码)', ha='center', va='center', fontsize=12)
            ax4.axis('off')
        
        stats_text = f"""回测统计
    
起始日期: {trades['date'].iloc[0].strftime('%Y-%m-%d')}
结束日期: {trades['date'].iloc[-1].strftime('%Y-%m-%d')}
定投次数: {result.investment_count}
总投入金额: {result.total_invested:,.2f}
最终资产: {result.final_value:,.2f}
总收益: {result.total_return:+,.2f}
总收益率: {result.return_rate:+.2f}%
年化收益率: {result.annual_return:+.2f}%
最大回撤: {result.max_drawdown:.2f}%"""
        
        ax5 = fig.add_subplot(grid[2, :])
        ax5.text(0.5, 0.5, stats_text, fontsize=12, ha='center', va='center',
                transform=ax5.transAxes,
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5),
                family='sans-serif')
        ax5.axis('off')
        
        fig.suptitle(f'定投回测分析 - {title}', fontsize=14, fontweight='bold')
        
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
            print(f"图表已保存: {save_path}")
        
        plt.show()
        return fig
    
    def _plot_kline(self, ax, nav_data):
        """绘制K线图"""
        try:
            df = nav_data.copy()
            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values('date')
            
            if 'open' not in df.columns or 'high' not in df.columns:
                ax.text(0.5, 0.5, 'K线数据不完整', ha='center', va='center')
                ax.axis('off')
                return
            
            df['high'] = pd.to_numeric(df['high'], errors='coerce')
            df['low'] = pd.to_numeric(df['low'], errors='coerce')
            df['open'] = pd.to_numeric(df['open'], errors='coerce')
            df['close'] = pd.to_numeric(df.get('close', df['nav']), errors='coerce')
            
            width = 0.6
            up = df[df['close'] >= df['open']]
            down = df[df['close'] < df['open']]
            
            ax.plot(df['date'], df['high'], color='#333333', linewidth=0.5)
            ax.plot(df['date'], df['low'], color='#333333', linewidth=0.5)
            
            ax.bar(up['date'], up['close'] - up['open'], width, bottom=up['open'], color='red', alpha=0.8)
            ax.bar(up['date'], up['high'] - up['close'], width*0.2, bottom=up['close'], color='red', alpha=0.8)
            ax.bar(up['date'], up['open'] - up['low'], width*0.2, bottom=up['low'], color='red', alpha=0.8)
            
            ax.bar(down['date'], down['close'] - down['open'], width, bottom=down['open'], color='green', alpha=0.8)
            ax.bar(down['date'], down['high'] - down['open'], width*0.2, bottom=down['open'], color='green', alpha=0.8)
            ax.bar(down['date'], down['low'] - down['close'], width*0.2, bottom=down['close'], color='green', alpha=0.8)
            
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
            ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
            plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)
            ax.grid(True, alpha=0.3)
            ax.set_xlabel('日期')
            ax.set_ylabel('价格')
        except Exception as e:
            ax.text(0.5, 0.5, f'K线绘制失败: {str(e)}', ha='center', va='center')
            ax.axis('off')
    
    def plot_portfolio(self, portfolio_results: Dict, save_path: str = None):
        """绘制组合回测结果"""
        fig, axes = plt.subplots(1, 2, figsize=(14, 6))
        
        names = list(portfolio_results.keys())
        invested = [portfolio_results[n].total_invested for n in names]
        final_values = [portfolio_results[n].final_value for n in names]
        
        x = np.arange(len(names))
        width = 0.35
        
        ax1 = axes[0]
        bars1 = ax1.bar(x - width/2, invested, width, label='总投入', color='steelblue')
        bars2 = ax1.bar(x + width/2, final_values, width, label='最终价值', color='seagreen')
        ax1.set_xlabel('基金')
        ax1.set_ylabel('金额 (元)')
        ax1.set_title('各基金投入与收益对比')
        ax1.set_xticks(x)
        ax1.set_xticklabels(names, rotation=45, ha='right')
        ax1.legend()
        for bar in bars1 + bars2:
            height = bar.get_height()
            ax1.annotate(f'{height:,.0f}',
                        xy=(bar.get_x() + bar.get_width() / 2, height),
                        xytext=(0, 3), textcoords="offset points",
                        ha='center', va='bottom', fontsize=8)
        
        return_rates = [portfolio_results[n].return_rate for n in names]
        colors = ['green' if r > 0 else 'red' for r in return_rates]
        
        ax2 = axes[1]
        bars = ax2.bar(names, return_rates, color=colors, alpha=0.7)
        ax2.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
        ax2.set_xlabel('基金')
        ax2.set_ylabel('收益率 (%)')
        ax2.set_title('各基金收益率对比')
        plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45, ha='right')
        
        for bar, rate in zip(bars, return_rates):
            height = bar.get_height()
            ax2.annotate(f'{rate:+.2f}%',
                        xy=(bar.get_x() + bar.get_width() / 2, height),
                        xytext=(0, 3 if height >= 0 else -12), textcoords="offset points",
                        ha='center', va='bottom' if height >= 0 else 'top', fontsize=9)
        
        fig.suptitle('基金组合定投回测分析', fontsize=14, fontweight='bold')
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
            print(f"图表已保存: {save_path}")
        
        plt.show()
        return fig
    
    def plot_comparison(self, results: Dict[str, BacktestResult], save_path: str = None):
        """对比多个基金"""
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        
        names = list(results.keys())
        colors = plt.cm.Set2(np.linspace(0, 1, len(names)))
        
        ax1 = axes[0, 0]
        for i, (name, result) in enumerate(results.items()):
            trades = result.trades.copy()
            trades['date'] = pd.to_datetime(trades['date'])
            ax1.plot(trades['date'], trades['portfolio_value'], 
                    label=name, color=colors[i], linewidth=1.5)
        ax1.set_title('资产总值对比')
        ax1.set_xlabel('日期')
        ax1.set_ylabel('金额 (元)')
        ax1.legend()
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
        plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45)
        
        ax2 = axes[0, 1]
        for i, (name, result) in enumerate(results.items()):
            trades = result.trades.copy()
            trades['date'] = pd.to_datetime(trades['date'])
            ax2.plot(trades['date'], trades['return_rate'],
                    label=name, color=colors[i], linewidth=1.5)
        ax2.axhline(y=0, color='black', linestyle='--', alpha=0.5)
        ax2.set_title('收益率对比')
        ax2.set_xlabel('日期')
        ax2.set_ylabel('收益率 (%)')
        ax2.legend()
        ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
        plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45)
        
        return_rates = [results[n].return_rate for n in names]
        annual_returns = [results[n].annual_return for n in names]
        
        x = np.arange(len(names))
        width = 0.35
        
        ax3 = axes[1, 0]
        ax3.bar(x - width/2, return_rates, width, label='总收益率', color='steelblue')
        ax3.bar(x + width/2, annual_returns, width, label='年化收益率', color='coral')
        ax3.set_xlabel('基金')
        ax3.set_ylabel('收益率 (%)')
        ax3.set_title('收益对比')
        ax3.set_xticks(x)
        ax3.set_xticklabels(names, rotation=45, ha='right')
        ax3.legend()
        
        max_drawdowns = [results[n].max_drawdown for n in names]
        
        ax4 = axes[1, 1]
        ax4.barh(names, max_drawdowns, color='indianred', alpha=0.7)
        ax4.set_xlabel('最大回撤 (%)')
        ax4.set_title('最大回撤对比')
        for i, v in enumerate(max_drawdowns):
            ax4.text(v + 0.5, i, f'{v:.2f}%', va='center')
        
        fig.suptitle('多基金定投对比分析', fontsize=14, fontweight='bold')
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
            print(f"图表已保存: {save_path}")
        
        plt.show()
        return fig


def visualize_backtest(result: BacktestResult, title: str = None, save_path: str = None):
    """便捷函数：可视化单个基金回测结果"""
    vis = BacktestVisualizer()
    return vis.plot_single_fund(result, title, save_path)


if __name__ == "__main__":
    from backtest.dca_backtest import run_single_fund_backtest
    
    result = run_single_fund_backtest(
        fund_code="600036",
        fund_name="600036",
        start_date="2022-01-01",
        end_date="2024-12-31",
        investment_amount=1000,
        data_source="tushare"
    )
    
    if result:
        visualize_backtest(result, "600036")