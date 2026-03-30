# -*- coding: utf-8 -*-
"""
数据同步命令行工具

用法:
    # 初始化数据库
    python -m data_source.db.migrations --init

    # 同步股票列表
    python -m data_source.db.migrations --sync-stocks --source akshare

    # 同步单只股票（全量，按年分段）
    python -m data_source.db.migrations --full --code 600036 --source akshare

    # 批量同步多只股票
    python -m data_source.db.migrations --batch --codes 600036,601318,600519 --source akshare

    # 批量同步所有股票（从数据库读取）
    python -m data_source.db.migrations --batch-all --source akshare

    # 增量同步（每日定时任务）
    python -m data_source.db.migrations --incremental --source akshare

    # 按日期范围同步
    python -m data_source.db.migrations --range 20200101 20241231 --codes 600036 --source akshare

    # 查看统计
    python -m data_source.db.migrations --stats

    # 检查缺失数据
    python -m data_source.db.migrations --check-missing --source akshare
"""

import argparse
import logging
import sys
import time
from datetime import datetime, timedelta
from typing import List, Optional

sys.path.insert(0, '.')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_year_ranges(start_year: int = 2010, end_year: Optional[int] = None) -> List[tuple]:
    """生成按年分段的时间范围"""
    if end_year is None:
        end_year = datetime.now().year
    ranges = []
    for year in range(start_year, end_year + 1):
        if year == end_year:
            ranges.append((f"{year}0101", datetime.now().strftime('%Y%m%d')))
        else:
            ranges.append((f"{year}0101", f"{year}1231"))
    return ranges


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


def sync_stocks(source: str = "akshare"):
    """同步股票列表"""
    logger.info("=" * 50)
    logger.info(f"开始同步股票列表 (数据源: {source})...")
    
    try:
        if source == "akshare":
            from data_source.sync.akshare_sync import AkshareSync
            sync = AkshareSync()
            result = sync.sync_stock_list()
            logger.info(f"✅ 同步完成! 股票: {result} 只")
        else:
            from data_source.sync.tushare_sync import TushareSync
            sync = TushareSync()
            result = sync.sync_all_stocks()
            logger.info(f"✅ 同步完成! 股票: {result['stocks']} 只, ETF: {result['etfs']} 只")
        return True
    except Exception as e:
        logger.error(f"❌ 同步失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def sync_single_stock_yearly(code: str, source: str = "akshare", start_year: int = 2010):
    """按年分段同步单只股票历史数据"""
    logger.info("=" * 50)
    logger.info(f"开始同步股票 {code} (数据源: {source})...")
    logger.info(f"从 {start_year} 年开始，按年分段查询...")
    
    try:
        from data_source.fund_data_source import FundDataSource
        
        ds = FundDataSource(preferred_source=source)
        
        year_ranges = get_year_ranges(start_year)
        total_records = 0
        success_years = 0
        
        for i, (start_date, end_date) in enumerate(year_ranges, 1):
            logger.info(f"[{i}/{len(year_ranges)}] {code}: {start_date} ~ {end_date}")
            
            try:
                df = ds.get_fund_data(code, start_date, end_date)
                if df is not None and len(df) > 0:
                    total_records += len(df)
                    success_years += 1
                    logger.info(f"  ✅ {len(df)} 条数据")
                else:
                    logger.info(f"  ⚠️ 无数据")
            except Exception as e:
                logger.error(f"  ❌ 失败: {e}")
            
            if i < len(year_ranges):
                time.sleep(0.5)
        
        logger.info("=" * 50)
        logger.info(f"✅ {code} 同步完成!")
        logger.info(f"   成功年份: {success_years}/{len(year_ranges)}")
        logger.info(f"   总记录数: {total_records}")
        
        return True
    except Exception as e:
        logger.error(f"❌ 同步失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def sync_batch(codes: List[str], source: str = "akshare", start_year: int = 2010):
    """批量同步多只股票"""
    logger.info("=" * 50)
    logger.info(f"开始批量同步 {len(codes)} 只股票 (数据源: {source})...")
    
    total = len(codes)
    success = 0
    failed = 0
    total_records = 0
    
    for i, code in enumerate(codes, 1):
        logger.info(f"\n[{i}/{total}] 进度: {i*100//total}%")
        
        try:
            from data_source.fund_data_source import FundDataSource
            ds = FundDataSource(preferred_source=source)
            
            year_ranges = get_year_ranges(start_year)
            code_records = 0
            
            for start_date, end_date in year_ranges:
                df = ds.get_fund_data(code, start_date, end_date)
                if df is not None and len(df) > 0:
                    code_records += len(df)
                time.sleep(0.3)
            
            if code_records > 0:
                success += 1
                total_records += code_records
                logger.info(f"✅ {code}: {code_records} 条")
            else:
                failed += 1
                logger.warning(f"⚠️ {code}: 无数据")
                
        except Exception as e:
            failed += 1
            logger.error(f"❌ {code}: {e}")
    
    logger.info("=" * 50)
    logger.info(f"✅ 批量同步完成!")
    logger.info(f"   成功: {success}/{total}")
    logger.info(f"   失败: {failed}/{total}")
    logger.info(f"   总记录: {total_records}")
    
    return success > 0


def sync_batch_all(source: str = "akshare", start_year: int = 2010):
    """从数据库读取所有股票，批量同步"""
    logger.info("=" * 50)
    logger.info(f"批量同步所有股票 (数据源: {source})...")
    
    try:
        from data_source.db.connection import get_db_session
        from data_source.db.models import Stock
        
        with get_db_session() as session:
            stocks = session.query(Stock).all()
            codes = [s.code for s in stocks]
        
        logger.info(f"共 {len(codes)} 只股票，开始批量同步...")
        
        return sync_batch(codes, source, start_year)
    except Exception as e:
        logger.error(f"❌ 批量同步失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def incremental_sync(source: str = "akshare"):
    """增量同步（每日调用）"""
    logger.info("=" * 50)
    logger.info(f"开始增量同步 (数据源: {source})...")
    
    try:
        from data_source.db.connection import get_db_session
        from data_source.db.models import Stock
        from data_source.fund_data_source import FundDataSource
        
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y%m%d')
        
        ds = FundDataSource(preferred_source=source)
        
        with get_db_session() as session:
            stocks = session.query(Stock).all()
            codes = [s.code for s in stocks]
        
        total = len(codes)
        success = 0
        total_records = 0
        
        logger.info(f"同步日期: {yesterday}, 股票数: {total}")
        
        for i, code in enumerate(codes, 1):
            try:
                df = ds.get_fund_data(code, yesterday, yesterday)
                if df is not None and len(df) > 0:
                    success += 1
                    total_records += len(df)
            except:
                pass
            
            if i % 100 == 0:
                logger.info(f"进度: [{i}/{total}] 成功: {success}")
                time.sleep(0.5)
        
        logger.info("=" * 50)
        logger.info(f"✅ 增量同步完成!")
        logger.info(f"   更新股票: {success}/{total}")
        logger.info(f"   新增记录: {total_records}")
        
        return True
    except Exception as e:
        logger.error(f"❌ 增量同步失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def sync_by_range(codes: List[str], start_date: str, end_date: str, source: str = "akshare"):
    """按日期范围同步"""
    logger.info("=" * 50)
    logger.info(f"按日期范围同步 {len(codes)} 只股票...")
    logger.info(f"日期范围: {start_date} ~ {end_date} (数据源: {source})")
    
    try:
        from data_source.fund_data_source import FundDataSource
        
        ds = FundDataSource(preferred_source=source)
        
        total = len(codes)
        success = 0
        total_records = 0
        
        for i, code in enumerate(codes, 1):
            try:
                df = ds.get_fund_data(code, start_date, end_date)
                if df is not None and len(df) > 0:
                    success += 1
                    total_records += len(df)
                    logger.info(f"[{i}/{total}] ✅ {code}: {len(df)} 条")
                else:
                    logger.info(f"[{i}/{total}] ⚠️ {code}: 无数据")
            except Exception as e:
                logger.error(f"[{i}/{total}] ❌ {code}: {e}")
            
            if i < total:
                time.sleep(0.3)
        
        logger.info("=" * 50)
        logger.info(f"✅ 同步完成! 成功: {success}/{total}, 记录: {total_records}")
        return True
    except Exception as e:
        logger.error(f"❌ 同步失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def check_missing(source: str = "akshare", days: int = 30):
    """检查缺失的数据"""
    logger.info("=" * 50)
    logger.info(f"检查最近 {days} 天的缺失数据...")
    
    try:
        from data_source.db.connection import get_db_session
        from data_source.db.models import DailyKlineAkShare, DailyKlineTushare
        from sqlalchemy import func
        
        end_date = datetime.now().date()
        start_date = (end_date - timedelta(days=days))
        
        if source == "akshare":
            Model = DailyKlineAkShare
        else:
            Model = DailyKlineTushare
        
        with get_db_session() as session:
            result = session.query(
                func.count(func.distinct(Model.code))
            ).filter(
                Model.trade_date >= start_date,
                Model.trade_date <= end_date
            ).scalar()
            
            total_stocks = session.query(func.count(func.distinct(Model.code))).scalar()
            total_records = session.query(func.count(Model.id)).scalar()
            
            date_count = session.query(
                func.count(func.distinct(Model.trade_date))
            ).filter(
                Model.trade_date >= start_date,
                Model.trade_date <= end_date
            ).scalar()
        
        logger.info(f"数据源: {source}")
        logger.info(f"检查范围: {start_date} ~ {end_date}")
        logger.info(f"数据库总记录: {total_records:,}")
        logger.info(f"数据库总股票: {total_stocks:,}")
        logger.info(f"近 {days} 天有数据的股票: {result:,}")
        
        return True
    except Exception as e:
        logger.error(f"❌ 检查失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def show_stats():
    """显示数据统计"""
    logger.info("=" * 50)
    logger.info("数据统计")
    
    try:
        from data_source.db.connection import get_db_session
        from data_source.db.models import Stock, DailyKlineAkShare, DailyKlineTushare
        from sqlalchemy import func
        
        with get_db_session() as session:
            stock_count = session.query(func.count(Stock.code)).scalar()
            
            akshare_count = session.query(func.count(DailyKlineAkShare.id)).scalar()
            akshare_stocks = session.query(func.count(func.distinct(DailyKlineAkShare.code))).scalar()
            
            tushare_count = session.query(func.count(DailyKlineTushare.id)).scalar()
            tushare_stocks = session.query(func.count(func.distinct(DailyKlineTushare.code))).scalar()
        
        logger.info(f"股票列表: {stock_count:,} 只")
        logger.info(f"AkShare 日线: {akshare_count:,} 条, {akshare_stocks:,} 只股票")
        logger.info(f"Tushare 日线: {tushare_count:,} 条, {tushare_stocks:,} 只股票")
        
        return True
    except Exception as e:
        logger.error(f"❌ 获取统计失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    parser = argparse.ArgumentParser(description='数据同步工具')
    parser.add_argument('--init', action='store_true', help='初始化数据库')
    parser.add_argument('--sync-stocks', action='store_true', help='同步股票列表')
    parser.add_argument('--full', action='store_true', help='全量同步单只股票（按年分段）')
    parser.add_argument('--batch', action='store_true', help='批量同步多只股票')
    parser.add_argument('--batch-all', action='store_true', help='批量同步所有股票')
    parser.add_argument('--incremental', action='store_true', help='增量同步（每日调用）')
    parser.add_argument('--range', nargs=2, metavar=('START', 'END'), help='按日期范围同步')
    parser.add_argument('--stats', action='store_true', help='显示数据统计')
    parser.add_argument('--check-missing', action='store_true', help='检查缺失数据')
    parser.add_argument('--source', choices=['akshare', 'tushare'], default='akshare',
                        help='数据源 (默认: akshare)')
    parser.add_argument('--code', type=str, help='股票代码')
    parser.add_argument('--codes', type=str, help='股票代码列表 (逗号分隔)')
    parser.add_argument('--start-year', type=int, default=2010, help='起始年份 (默认: 2010)')
    
    args = parser.parse_args()
    
    if args.init:
        init_database()
    elif args.sync_stocks:
        sync_stocks(source=args.source)
    elif args.full:
        if not args.code:
            logger.error("❌ --full 需要 --code 参数")
            return
        sync_single_stock_yearly(args.code, source=args.source, start_year=args.start_year)
    elif args.batch:
        if not args.codes:
            logger.error("❌ --batch 需要 --codes 参数")
            return
        codes = [c.strip() for c in args.codes.split(',') if c.strip()]
        sync_batch(codes, source=args.source, start_year=args.start_year)
    elif args.batch_all:
        sync_batch_all(source=args.source, start_year=args.start_year)
    elif args.incremental:
        incremental_sync(source=args.source)
    elif args.range:
        codes = [args.code] if args.code else []
        if not codes:
            from data_source.db.connection import get_db_session
            from data_source.db.models import Stock
            with get_db_session() as session:
                stocks = session.query(Stock).limit(100).all()
                codes = [s.code for s in stocks]
        sync_by_range(codes, args.range[0], args.range[1], source=args.source)
    elif args.stats:
        show_stats()
    elif args.check_missing:
        check_missing(source=args.source)
    else:
        parser.print_help()
        print("\n" + "=" * 50)
        print("示例:")
        print("  # 初始化数据库")
        print("  python -m data_source.db.migrations --init")
        print("")
        print("  # 同步股票列表")
        print("  python -m data_source.db.migrations --sync-stocks --source akshare")
        print("")
        print("  # 同步单只股票（按年分段）")
        print("  python -m data_source.db.migrations --full --code 600036 --source akshare")
        print("")
        print("  # 批量同步多只股票")
        print("  python -m data_source.db.migrations --batch --codes 600036,601318,600519 --source akshare")
        print("")
        print("  # 批量同步所有股票（耗时较长）")
        print("  python -m data_source.db.migrations --batch-all --source akshare")
        print("")
        print("  # 增量同步（每日定时任务）")
        print("  python -m data_source.db.migrations --incremental --source akshare")
        print("")
        print("  # 按日期范围同步")
        print("  python -m data_source.db.migrations --range 20240101 20241231 --code 600036 --source akshare")
        print("")
        print("  # 查看统计")
        print("  python -m data_source.db.migrations --stats")
        print("")
        print("  # 检查缺失数据")
        print("  python -m data_source.db.migrations --check-missing --source akshare")


if __name__ == "__main__":
    main()
