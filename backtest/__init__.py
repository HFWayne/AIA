from typing import Optional, List, Dict, Any
from dataclasses import dataclass

from data_source.fund_data_source import FundDataSource
from backtest.dca_backtest import DCABacktest, DCAParams, BacktestResult
from backtest.visualization import BacktestVisualizer
from backtest.watchlist_manager import WatchlistManager, Watchlist, StockInfo
from backtest.strategy_manager import StrategyManager, StrategyTemplate, StrategyParams
from backtest.report_manager import ReportManager, ReportData


@dataclass
class BacktestConfig:
    """回测配置"""
    fund_code: str
    fund_name: str
    start_date: str
    end_date: str
    investment_amount: float
    frequency: str = 'monthly'
    day_of_month: int = 1
    day_of_week: int = 0
    data_source: str = None
    
    enable_stop_loss: bool = False
    stop_loss_rate: float = 0.15
    stop_loss_sell_ratio: float = 1.0
    
    enable_take_profit: bool = False
    take_profit_rate: float = 0.20
    max_drawdown_threshold: float = 0.10
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


class FundBacktester:
    """股票定投回测主类"""
    
    def __init__(self, data_source: Optional[str] = None):
        from data_source.config import DATA_SOURCE
        self.data_source = data_source or DATA_SOURCE
        self.ds = FundDataSource(preferred_source=self.data_source)
        self.backtest = DCABacktest(self.ds)
        self.visualizer = BacktestVisualizer()
    
    def single_fund(self, config: BacktestConfig) -> Optional[BacktestResult]:
        """单个股票回测"""
        params = DCAParams(
            fund_code=config.fund_code,
            fund_name=config.fund_name,
            start_date=config.start_date,
            end_date=config.end_date,
            investment_amount=config.investment_amount,
            frequency=config.frequency,
            day_of_month=config.day_of_month,
            day_of_week=config.day_of_week,
            enable_stop_loss=config.enable_stop_loss,
            stop_loss_rate=config.stop_loss_rate,
            stop_loss_sell_ratio=config.stop_loss_sell_ratio,
            enable_take_profit=config.enable_take_profit,
            take_profit_rate=config.take_profit_rate,
            max_drawdown_threshold=config.max_drawdown_threshold,
            take_profit_sell_ratio=config.take_profit_sell_ratio,
            enable_dip_buy=config.enable_dip_buy,
            dip_buy_tier1_threshold=config.dip_buy_tier1_threshold,
            dip_buy_tier1_amount=config.dip_buy_tier1_amount,
            dip_buy_tier2_threshold=config.dip_buy_tier2_threshold,
            dip_buy_tier2_amount=config.dip_buy_tier2_amount,
            dip_buy_tier3_threshold=config.dip_buy_tier3_threshold,
            dip_buy_tier3_amount=config.dip_buy_tier3_amount,
            enable_yield_boost=config.enable_yield_boost,
            yield_boost_trigger=config.yield_boost_trigger,
            yield_boost_recover=config.yield_boost_recover,
            yield_boost_amount=config.yield_boost_amount
        )
        return self.backtest.run(params)
    
    def portfolio(self, funds: List[Dict[str, Any]], start_date: str, end_date: str, 
                  total_amount: float, frequency: str = 'monthly') -> Dict[str, Any]:
        """组合回测"""
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
    
    def compare(self, funds: List[Dict[str, Any]], start_date: str, end_date: str, 
                amount: float, frequency: str = 'monthly',
                enable_stop_loss: bool = False, stop_loss_rate: float = 0.15,
                enable_take_profit: bool = False, take_profit_rate: float = 0.20,
                max_drawdown_threshold: float = 0.10, sell_ratio: float = 0.5) -> Dict[str, BacktestResult]:
        """对比多个股票"""
        results = {}
        for f in funds:
            config = BacktestConfig(
                fund_code=f['fund_code'],
                fund_name=f['name'],
                start_date=start_date,
                end_date=end_date,
                investment_amount=amount,
                frequency=frequency,
                data_source=self.data_source,
                enable_stop_loss=enable_stop_loss,
                stop_loss_rate=stop_loss_rate,
                enable_take_profit=enable_take_profit,
                take_profit_rate=take_profit_rate,
                max_drawdown_threshold=max_drawdown_threshold,
                take_profit_sell_ratio=sell_ratio
            )
            result = self.single_fund(config)
            if result:
                results[f['name']] = result
        return results
    
    def visualize_single(self, result: BacktestResult, title: Optional[str] = None, save_path: Optional[str] = None):
        """可视化单个股票结果"""
        return self.visualizer.plot_single_fund(result, title, save_path)
    
    def visualize_portfolio(self, results: Dict[str, BacktestResult], save_path: Optional[str] = None):
        """可视化组合结果"""
        return self.visualizer.plot_portfolio(results, save_path)
    
    def visualize_comparison(self, results: Dict[str, BacktestResult], save_path: str = None):
        """可视化对比结果"""
        return self.visualizer.plot_comparison(results, save_path)


def quick_backtest(fund_code: str, fund_name: Optional[str] = None, 
                   start_date: str = '2022-01-01', 
                   end_date: str = '2024-12-31',
                   amount: float = 1000,
                   data_source: Optional[str] = None,
                   **strategy_kwargs: Any) -> Optional[BacktestResult]:
    """快速回测函数"""
    from data_source.config import DATA_SOURCE
    name_map = {
        '600036': '招商银行', '601318': '中国平安', '000858': '五粮液',
        '600519': '贵州茅台', '601888': '中国中免', '300750': '宁德时代',
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
        data_source=data_source,
        **strategy_kwargs
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
        print(f"止损次数: {result.stop_loss_count}")
        print(f"止盈次数: {result.take_profit_count}")
        
        tester.visualize_single(result, fund_name)
        return result
    else:
        print("获取数据失败，请尝试其他数据源 (akshare/tushare)")
        return None


if __name__ == "__main__":
    quick_backtest('600036', start_date='2022-01-01', end_date='2024-12-31', amount=1000)
