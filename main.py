# -*- coding: utf-8 -*-
"""
基金定投回测工具
使用方法:
    python main.py --fund 510300 --name 沪深300ETF --start 2022-01-01 --end 2024-12-31 --amount 1000
    python main.py --compare --funds 510300,518880,511010 --start 2022-01-01 --end 2024-12-31 --amount 1000
"""

import argparse
import sys

from backtest import FundBacktester, quick_backtest
from data_source.config import DATA_SOURCE


def main():
    parser = argparse.ArgumentParser(description='基金定投回测工具')
    parser.add_argument('--fund', type=str, help='基金代码')
    parser.add_argument('--name', type=str, help='基金名称')
    parser.add_argument('--start', type=str, default='2022-01-01', help='开始日期 YYYY-MM-DD')
    parser.add_argument('--end', type=str, default='2024-12-31', help='结束日期 YYYY-MM-DD')
    parser.add_argument('--amount', type=float, default=1000, help='每次定投金额')
    parser.add_argument('--source', type=str, default=None, 
                        choices=['tushare', 'akshare', 'baostock', None], 
                        help='数据源 (默认读取config.py)')
    
    parser.add_argument('--compare', action='store_true', help='对比模式')
    parser.add_argument('--funds', type=str, help='对比模式: 多个基金代码逗号分隔, 如 510300,518880,511010')
    
    args = parser.parse_args()
    
    if args.compare and args.funds:
        fund_codes = args.funds.split(',')
        fund_list = []
        name_map = {
            '510300': '沪深300ETF', '510050': '上证50ETF', '510500': '中证500ETF',
            '159915': '创业板ETF', '588000': '科创50ETF', '518880': '黄金ETF',
            '159934': '易方达黄金ETF', '511010': '中债ETF', '161039': '纯债基金',
        }
        for code in fund_codes:
            fund_list.append({'fund_code': code.strip(), 'name': name_map.get(code.strip(), code.strip())})
        
        source = args.source or DATA_SOURCE
        tester = FundBacktester(data_source=source)
        results = tester.compare(fund_list, args.start, args.end, args.amount)
        
        print(f"\n{'='*60}")
        print(f"多基金对比回测 ({args.start} ~ {args.end})")
        print(f"{'='*60}")
        
        for name, result in results.items():
            print(f"\n{name}:")
            print(f"  投入: {result.total_invested:,.0f} | 价值: {result.final_value:,.0f}")
            print(f"  收益: {result.return_rate:+.2f}% | 年化: {result.annual_return:+.2f}% | 回撤: {result.max_drawdown:.2f}%")
        
        tester.visualize_comparison(results)
        
    elif args.fund:
        print(f"DEBUG: fund={args.fund}, name={args.name}")
        quick_backtest(args.fund, args.name, args.start, args.end, args.amount, args.source or DATA_SOURCE)
    
    else:
        parser.print_help()
        print("\n示例:")
        print("  python main.py --fund 510300 --name 沪深300ETF")
        print("  python main.py --compare --funds 510300,518880,511010")


if __name__ == "__main__":
    main()