# -*- coding: utf-8 -*-
"""
数据同步命令行工具

用法:
    python -m data_source.db.migrations.init_db         # 初始化数据库
    python -m data_source.db.migrations.sync_data       # 同步股票列表
    python -m data_source.db.migrations.sync_data --code 510300  # 同步单只股票
    python -m data_source.db.migrations.sync_data --full  # 全量同步（需要较长时间）
"""

import argparse
import logging
import sys
import time
from datetime import datetime, timedelta

sys.path.insert(0, '.')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def init_database():
    """初始化数据库"""
    logger.info("=" * 50)
    logger.info("开始初始化数据库...")
    
    try:
        from data_source.db.connection import create_database_if_not_exists, init_database
        
        create_database_if_not_exists()
        init_database()
        
        logger.info("✅ 数据库初始化完成!")
        return True
    except Exception as e:
        logger.error(f"❌ 数据库初始化失败: {e}")
        return False


def sync_stocks():
    """同步股票列表"""
    logger.info("=" * 50)
    logger.info("开始同步股票列表...")
    
    try:
        from data_source.sync import TushareSync
        
        sync = TushareSync()
        result = sync.sync_all_stocks()
        
        logger.info(f"✅ 同步完成!")
        logger.info(f"   股票: {result['stocks']} 只")
        logger.info(f"   ETF: {result['etfs']} 只")
        return True
    except Exception as e:
        logger.error(f"❌ 同步失败: {e}")
        return False


def sync_single_stock(code: str):
    """同步单只股票"""
    logger.info("=" * 50)
    logger.info(f"开始同步股票 {code} ...")
    
    try:
        from data_source.sync import TushareSync
        
        sync = TushareSync()
        records = sync.sync_daily_kline(code)
        
        logger.info(f"✅ 同步完成! 共 {records} 条数据")
        return True
    except Exception as e:
        logger.error(f"❌ 同步失败: {e}")
        return False


def full_sync():
    """全量同步所有股票"""
    logger.info("=" * 50)
    logger.info("⚠️ 开始全量同步，这可能需要较长时间...")
    
    try:
        from data_source.sync import TushareSync
        from data_source.db.connection import get_db_session
        from data_source.db.models import Stock
        
        sync = TushareSync()
        
        with get_db_session() as session:
            stocks = session.query(Stock).all()
        
        total = len(stocks)
        success = 0
        failed = []
        
        logger.info(f"共 {total} 只股票/ETF 需要同步")
        
        for i, stock in enumerate(stocks, 1):
            try:
                logger.info(f"[{i}/{total}] 同步 {stock.code} {stock.name}...")
                records = sync.sync_daily_kline(stock.code)
                if records > 0:
                    success += 1
                else:
                    failed.append(stock.code)
            except Exception as e:
                logger.warning(f"同步失败: {stock.code} - {e}")
                failed.append(stock.code)
            
            if i % 10 == 0:
                logger.info(f"进度: {i}/{total} ({i*100//total}%)")
            
            time.sleep(0.5)
        
        logger.info("=" * 50)
        logger.info(f"✅ 全量同步完成!")
        logger.info(f"   成功: {success} 只")
        if failed:
            logger.info(f"   失败: {len(failed)} 只")
            logger.info(f"   失败代码: {', '.join(failed[:20])}{'...' if len(failed) > 20 else ''}")
        
        return True
    except Exception as e:
        logger.error(f"❌ 全量同步失败: {e}")
        return False


def incremental_sync():
    """增量同步（每日调用）"""
    logger.info("=" * 50)
    logger.info("开始增量同步...")
    
    try:
        from data_source.sync import TushareSync
        from data_source.db.connection import get_db_session
        from data_source.db.models import Stock, DailyKline
        from datetime import date
        
        sync = TushareSync()
        
        yesterday = (date.today() - timedelta(days=1)).strftime('%Y%m%d')
        
        with get_db_session() as session:
            stocks = session.query(Stock).all()
        
        total = len(stocks)
        success = 0
        failed = []
        
        for i, stock in enumerate(stocks, 1):
            try:
                records = sync.sync_daily_kline(stock.code, start_date=yesterday)
                if records > 0:
                    success += 1
                    logger.info(f"[{i}/{total}] {stock.code} 更新 {records} 条")
            except Exception as e:
                logger.warning(f"增量同步失败: {stock.code} - {e}")
                failed.append(stock.code)
            
            if i % 50 == 0:
                logger.info(f"进度: {i}/{total}")
            
            time.sleep(0.3)
        
        logger.info("=" * 50)
        logger.info(f"✅ 增量同步完成! 更新 {success}/{total} 只股票")
        
        return True
    except Exception as e:
        logger.error(f"❌ 增量同步失败: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description='数据同步工具')
    parser.add_argument('--init', action='store_true', help='初始化数据库')
    parser.add_argument('--sync-stocks', action='store_true', help='同步股票列表')
    parser.add_argument('--code', type=str, help='同步单只股票代码')
    parser.add_argument('--full', action='store_true', help='全量同步所有股票')
    parser.add_argument('--incremental', action='store_true', help='增量同步（每日调用）')
    
    args = parser.parse_args()
    
    if args.init:
        init_database()
    elif args.sync_stocks:
        sync_stocks()
    elif args.code:
        sync_single_stock(args.code)
    elif args.full:
        full_sync()
    elif args.incremental:
        incremental_sync()
    else:
        parser.print_help()
        print("\n示例:")
        print("  python -m data_source.db.migrations.init_db           # 初始化数据库")
        print("  python -m data_source.db.migrations.init_db --sync-stocks  # 初始化并同步股票")
        print("  python -m data_source.db.migrations.init_db --code 510300   # 同步单只股票")


if __name__ == "__main__":
    main()
