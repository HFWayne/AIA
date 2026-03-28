# -*- coding: utf-8 -*-
"""
数据同步命令行工具

用法:
    python -m data_source.db.migrations --init                  # 初始化数据库
    python -m data_source.db.migrations --sync-stocks         # 同步股票列表
    python -m data_source.db.migrations --code 510300         # 同步单只股票
    python -m data_source.db.migrations --full                 # 全量同步（高效方式）
    python -m data_source.db.migrations --incremental         # 每日增量同步
    python -m data_source.db.migrations --date 20240325        # 按日期同步所有股票
    python -m data_source.db.migrations --range 20200101 20241231  # 按日期范围同步
    python -m data_source.db.migrations --stats                 # 查看数据统计
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


def sync_stocks(use_free: bool = False):
    """同步股票列表"""
    logger.info("=" * 50)
    logger.info(f"开始同步股票列表 (免费数据源: {use_free})...")
    
    try:
        if use_free:
            from data_source.sync import FreeDataSync
            sync = FreeDataSync()
            result = sync.sync_all_stocks()
            logger.info(f"✅ 同步完成!")
            logger.info(f"   股票: {result['stocks']} 只")
        else:
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


def sync_single_stock(code: str, use_free: bool = False):
    """同步单只股票"""
    logger.info("=" * 50)
    logger.info(f"开始同步股票 {code} (免费数据源: {use_free})...")
    
    try:
        if use_free:
            from data_source.sync import FreeDataSync
            sync = FreeDataSync()
        else:
            from data_source.sync import TushareSync
            sync = TushareSync()
        
        records = sync.sync_daily_kline(code)
        
        logger.info(f"✅ 同步完成! 共 {records} 条数据")
        return True
    except Exception as e:
        logger.error(f"❌ 同步失败: {e}")
        return False


def full_sync():
    """全量同步：按日期批量获取所有股票（高效方式）"""
    logger.info("=" * 50)
    logger.info("⚠️ 开始全量同步（按日期批量获取，高效模式）...")
    logger.info("   这将获取所有股票从2000年至今的历史数据")
    logger.info("   预计需要数小时，请耐心等待")
    
    try:
        from data_source.sync import TushareSync
        
        sync = TushareSync()
        
        start_date = "20000101"
        end_date = datetime.now().strftime('%Y%m%d')
        
        result = sync.sync_daily_date_range(start_date, end_date)
        
        logger.info("=" * 50)
        logger.info(f"✅ 全量同步完成!")
        logger.info(f"   交易日数: {result['dates']} 天")
        logger.info(f"   记录数: {result['records']:,} 条")
        
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
        
        sync = TushareSync()
        
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y%m%d')
        records = sync.sync_daily_by_date(yesterday)
        
        logger.info(f"✅ 增量同步完成! 更新 {records} 条数据")
        return True
    except Exception as e:
        logger.error(f"❌ 增量同步失败: {e}")
        return False


def sync_missing(days: int = 30):
    """自动检测并补齐缺失的数据"""
    logger.info("=" * 50)
    logger.info(f"开始检测并补齐最近 {days} 天的缺失数据...")
    
    try:
        from data_source.sync import TushareSync
        
        sync = TushareSync()
        
        result = sync.sync_missing_data(days_back=days)
        
        if result["dates"] == 0:
            logger.info("✅ 没有缺失数据需要补齐")
        else:
            logger.info("=" * 50)
            logger.info(f"✅ 补齐完成!")
            logger.info(f"   补齐天数: {result['dates']} 天")
            logger.info(f"   新增记录: {result['records']:,} 条")
        
        return True
    except Exception as e:
        logger.error(f"❌ 补齐失败: {e}")
        return False


def check_missing(days: int = 30):
    """检查缺失的数据"""
    logger.info("=" * 50)
    logger.info(f"检查最近 {days} 天的缺失数据...")
    
    try:
        from data_source.sync import TushareSync
        
        sync = TushareSync()
        
        end_date = datetime.now().strftime('%Y%m%d')
        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y%m%d')
        
        missing_dates = sync.get_missing_trade_dates(start_date, end_date)
        
        if not missing_dates:
            logger.info("✅ 没有缺失数据")
        else:
            logger.info(f"❌ 缺失 {len(missing_dates)} 天的数据:")
            for d in missing_dates[:20]:
                logger.info(f"   - {d}")
            if len(missing_dates) > 20:
                logger.info(f"   ... 还有 {len(missing_dates) - 20} 天")
        
        return True
    except Exception as e:
        logger.error(f"❌ 检查失败: {e}")
        return False


def sync_by_date(trade_date: str):
    """按指定日期同步所有股票"""
    logger.info("=" * 50)
    logger.info(f"同步日期 {trade_date} 的所有股票...")
    
    try:
        from data_source.sync import TushareSync
        
        sync = TushareSync()
        records = sync.sync_daily_by_date(trade_date)
        
        logger.info(f"✅ 完成! 共 {records} 条记录")
        return True
    except Exception as e:
        logger.error(f"❌ 同步失败: {e}")
        return False


def sync_by_date_range(start_date: str, end_date: str):
    """按日期范围同步所有股票"""
    logger.info("=" * 50)
    logger.info(f"同步日期范围 {start_date} ~ {end_date} 的所有股票...")
    
    try:
        from data_source.sync import TushareSync
        
        sync = TushareSync()
        result = sync.sync_daily_date_range(start_date, end_date)
        
        logger.info(f"✅ 完成! {result['dates']} 天, {result['records']:,} 条记录")
        return True
    except Exception as e:
        logger.error(f"❌ 同步失败: {e}")
        return False


def show_stats():
    """显示数据统计"""
    logger.info("=" * 50)
    logger.info("数据统计")
    
    try:
        from data_source.sync import TushareSync
        
        sync = TushareSync()
        
        stock_count = sync.get_stock_count()
        kline_count = sync.get_kline_count()
        
        logger.info(f"   股票数量: {stock_count:,} 只")
        logger.info(f"   日线数据: {kline_count:,} 条")
        
        if kline_count > 0 and stock_count > 0:
            avg_days = kline_count // stock_count
            logger.info(f"   平均每只: {avg_days} 交易日")
        
        return True
    except Exception as e:
        logger.error(f"获取统计失败: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description='数据同步工具')
    parser.add_argument('--init', action='store_true', help='初始化数据库')
    parser.add_argument('--sync-stocks', action='store_true', help='同步股票列表')
    parser.add_argument('--code', type=str, help='同步单只股票代码')
    parser.add_argument('--full', action='store_true', help='全量同步所有股票（高效模式）')
    parser.add_argument('--incremental', action='store_true', help='增量同步（每日调用）')
    parser.add_argument('--date', type=str, help='按日期同步所有股票 (YYYYMMDD)')
    parser.add_argument('--range', nargs=2, metavar=('START', 'END'), help='按日期范围同步 (YYYYMMDD YYYYMMDD)')
    parser.add_argument('--stats', action='store_true', help='显示数据统计')
    parser.add_argument('--missing', type=int, nargs='?', const=30, metavar='DAYS', 
                       help='检测并补齐缺失数据（默认最近30天）')
    parser.add_argument('--check-missing', type=int, nargs='?', const=30, metavar='DAYS',
                       help='检查缺失的数据（默认最近30天）')
    parser.add_argument('--free', action='store_true', help='使用免费数据源 (akshare/baostock)')
    
    args = parser.parse_args()
    
    if args.init:
        init_database()
    elif args.sync_stocks:
        sync_stocks(use_free=args.free)
    elif args.code:
        sync_single_stock(args.code, use_free=args.free)
    elif args.full:
        full_sync()
    elif args.incremental:
        incremental_sync()
    elif args.date:
        sync_by_date(args.date)
    elif args.range:
        sync_by_date_range(args.range[0], args.range[1])
    elif args.stats:
        show_stats()
    elif args.missing is not None:
        sync_missing(args.missing)
    elif args.check_missing is not None:
        check_missing(args.check_missing)
    else:
        parser.print_help()
        print("\n示例:")
        print("  python -m data_source.db.migrations --init                        # 初始化数据库")
        print("  python -m data_source.db.migrations --sync-stocks --free           # 免费数据源同步股票列表")
        print("  python -m data_source.db.migrations --code 510300 --free            # 免费数据源同步单只股票")
        print("  python -m data_source.db.migrations --code 000001                   # 使用tushare同步单只股票")
        print("  python -m data_source.db.migrations --full                          # 全量同步（需tushare）")
        print("  python -m data_source.db.migrations --incremental                  # 每日增量同步")
        print("  python -m data_source.db.migrations --missing                      # 检测并补齐缺失数据")
        print("  python -m data_source.db.migrations --stats                         # 数据统计")


if __name__ == "__main__":
    main()


if __name__ == "__main__":
    main()
