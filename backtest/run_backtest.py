from data_source.fund_data_source import FundDataSource, FUND_CODES
from backtest.dca_backtest import DCABacktest, DCAParams
from backtest.visualization import BacktestVisualizer

# 常用基金代码
INDEX_FUNDS = {
    '沪深300ETF': '510300',
    '上证50ETF': '510050',
    '创业板ETF': '159915',
    '中证500ETF': '510500',
    '科创50ETF': '588000',
}

BOND_FUNDS = {
    '中债ETF': '511010',
    '纯债基金': '161039',
}

GOLD_FUNDS = {
    '黄金ETF': '518880',
    '易方达黄金ETF': '159934',
}


def run_index_fund_backtest():
    """指数基金回测示例"""
    ds = FundDataSource("tushare")  # 优先使用tushare
    backtest = DCABacktest(ds)
    
    params = DCAParams(
        fund_code='510300',
        fund_name='沪深300ETF',
        start_date='2022-01-01',
        end_date='2024-12-31',
        investment_amount=1000,
        frequency='monthly'
    )
    
    result = backtest.run(params)
    
    if result:
        print("=" * 50)
        print("回测结果")
        print("=" * 50)
        print(f"基金: {params.fund_name}")
        print(f"回测期间: {params.start_date} ~ {params.end_date}")
        print(f"定投金额: ¥{params.investment_amount}/月")
        print(f"定投次数: {result.investment_count}")
        print(f"总投入: ¥{result.total_invested:,.2f}")
        print(f"最终价值: ¥{result.final_value:,.2f}")
        print(f"总收益: ¥{result.total_return:+,.2f}")
        print(f"总收益率: {result.return_rate:+.2f}%")
        print(f"年化收益: {result.annual_return:+.2f}%")
        print(f"最大回撤: {result.max_drawdown:.2f}%")
        
        vis = BacktestVisualizer()
        vis.plot_single_fund(result, params.fund_name)


def run_portfolio_backtest():
    """组合回测示例：指数基金 + 债券基金 + 黄金ETF"""
    ds = FundDataSource("tushare")
    backtest = DCABacktest(ds)
    
    portfolio = [
        {'fund_code': '510300', 'name': '沪深300ETF', 'weight': 0.5},
        {'fund_code': '511010', 'name': '中债ETF', 'weight': 0.3},
        {'fund_code': '518880', 'name': '黄金ETF', 'weight': 0.2},
    ]
    
    result = backtest.run_portfolio(
        portfolio=portfolio,
        start_date='2022-01-01',
        end_date='2024-12-31',
        investment_amount=3000,
        frequency='monthly'
    )
    
    print("=" * 50)
    print("组合回测结果")
    print("=" * 50)
    print(f"总投入: ¥{result['total_invested']:,.2f}")
    print(f"最终价值: ¥{result['final_value']:,.2f}")
    print(f"总收益: ¥{result['total_return']:+,.2f}")
    print(f"总收益率: {result['return_rate']:+.2f}%")
    print("\n各基金详情:")
    for name, r in result['individual_results'].items():
        print(f"  {name}: 收益率 {r.return_rate:+.2f}%, 年化 {r.annual_return:+.2f}%")
    
    vis = BacktestVisualizer()
    vis.plot_portfolio(result['individual_results'])


def run_custom_backtest(fund_code: str, fund_name: str, start_date: str, end_date: str,
                        amount: float = 1000, freq: str = 'monthly', source: str = 'tushare'):
    """自定义回测"""
    ds = FundDataSource(source)
    backtest = DCABacktest(ds)
    
    params = DCAParams(
        fund_code=fund_code,
        fund_name=fund_name,
        start_date=start_date,
        end_date=end_date,
        investment_amount=amount,
        frequency=freq
    )
    
    result = backtest.run(params)
    
    if result:
        print(f"\n{'='*50}")
        print(f"回测结果: {fund_name}")
        print(f"{'='*50}")
        print(f"投入: {result.total_invested:,.0f} | 最终: {result.final_value:,.0f}")
        print(f"收益: {result.total_return:+,.0f} ({result.return_rate:+.2f}%)")
        print(f"年化: {result.annual_return:+.2f}% | 最大回撤: {result.max_drawdown:.2f}%")
        
        vis = BacktestVisualizer()
        vis.plot_single_fund(result, fund_name)
        return result
    else:
        print("获取数据失败，请尝试切换数据源 (akshare/baostock)")
        return None


if __name__ == "__main__":
    # 示例1: 单基金回测
    run_custom_backtest(
        fund_code='510300',
        fund_name='沪深300ETF',
        start_date='2022-01-01',
        end_date='2024-12-31',
        amount=1000,
        source='tushare'  # 可选: tushare, akshare, baostock
    )
    
    # 示例2: 组合回测
    # run_portfolio_backtest()