# -*- coding: utf-8 -*-
"""
批量数据同步脚本 - 将 akshare/tushare 数据缓存到本地数据库

使用方法:
    python scripts/sync_to_local.py                  # 同步默认股票列表
    python scripts/sync_to_local.py --codes 600036 # 同步指定股票
    python scripts/sync_to_local.py --all           # 同步所有股票
    python scripts/sync_to_local.py --etf           # 同步 ETF
"""

import argparse
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from data_source.fund_data_source import FundDataSource
from data_source.config import DATA_SOURCE

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

DEFAULT_STOCKS = [
    '600036', '601318', '600519', '000858', '601888',
    '300750', '000001', '000002', '600276', '601166',
    '600030', '600887', '000333', '002594', '600009',
    '601012', '600028', '601398', '601288', '600000',
]

DEFAULT_ETFS = [
    '510300', '510500', '159915', '512000', '513500',
    '510050', '159919', '512100', '512880', '159920',
]


def sync_stock(code: str, days: int = 3650, source: str = None) -> bool:
    """同步单只股票数据到本地数据库"""
    ds = FundDataSource(preferred_source=source or DATA_SOURCE)
    
    end_date = datetime.now().strftime('%Y%m%d')
    start_date = (datetime.now() - timedelta(days=days)).strftime('%Y%m%d')
    
    try:
        logger.info(f"正在同步 {code} ({start_date} ~ {end_date})...")
        df = ds.get_fund_data(code, start_date, end_date)
        
        if df is not None and not df.empty:
            logger.info(f"✅ {code} 同步完成: {len(df)} 条数据")
            return True
        else:
            logger.warning(f"⚠️ {code} 无数据")
            return False
    except Exception as e:
        logger.error(f"❌ {code} 同步失败: {e}")
        return False


def sync_batch(codes: list, days: int = 3650, source: str = None, delay: float = 0.3) -> dict:
    """批量同步股票数据"""
    import time
    
    results = {'success': 0, 'failed': 0, 'failed_codes': []}
    
    total = len(codes)
    for i, code in enumerate(codes, 1):
        logger.info(f"[{i}/{total}] 进度: {i*100//total}%")
        
        if sync_stock(code, days, source):
            results['success'] += 1
        else:
            results['failed'] += 1
            results['failed_codes'].append(code)
        
        if i < total:
            time.sleep(delay)
    
    return results


def main():
    parser = argparse.ArgumentParser(description='批量数据同步工具')
    parser.add_argument('--codes', nargs='+', help='指定股票代码')
    parser.add_argument('--all', action='store_true', help='同步所有股票（耗时较长）')
    parser.add_argument('--etf', action='store_true', help='同步 ETF')
    parser.add_argument('--days', type=int, default=3650, help='同步天数（默认3650天/10年）')
    parser.add_argument('--source', choices=['akshare', 'tushare', 'auto'], 
                        default=None, help='数据源')
    
    args = parser.parse_args()
    
    if args.all:
        codes = DEFAULT_STOCKS + DEFAULT_ETFS
        logger.info(f"将同步 {len(codes)} 只股票/ETF...")
    elif args.etf:
        codes = DEFAULT_ETFS
        logger.info(f"将同步 {len(codes)} 只 ETF...")
    elif args.codes:
        codes = args.codes
        logger.info(f"将同步 {len(codes)} 只股票: {codes}")
    else:
        codes = DEFAULT_STOCKS
        logger.info(f"将同步默认 {len(codes)} 只股票...")
    
    logger.info(f"同步天数: {args.days} 天")
    logger.info(f"数据源: {args.source or 'auto (akshare 优先)'}")
    logger.info("-" * 50)
    
    results = sync_batch(codes, args.days, args.source)
    
    logger.info("-" * 50)
    logger.info(f"同步完成! 成功: {results['success']}, 失败: {results['failed']}")
    
    if results['failed_codes']:
        logger.info(f"失败的股票: {results['failed_codes']}")


if __name__ == '__main__':
    main()
