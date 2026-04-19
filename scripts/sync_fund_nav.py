#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基金净值同步脚本
用于在后台持续同步场外基金净值数据
"""

import sys
import os
import time

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data_source.db.connection import get_db_session
from data_source.db.models import Stock, FundNav
from data_source.sync.tushare_sync import TushareSync
import pandas as pd
from datetime import datetime


def get_remaining_funds():
    """获取待同步的基金列表"""
    with get_db_session() as session:
        all_codes = [f[0] for f in session.query(Stock.code).filter(Stock.stock_type == '基金').all()]
        synced = set(f[0] for f in session.query(FundNav.code).distinct().all())
        remaining = [c for c in all_codes if c not in synced]
    return remaining


def sync_fund_nav(code: str, start_date: str = '20240401', end_date: str = '20260418') -> int:
    """同步单只基金净值"""
    ts = TushareSync()
    ts_code = f'{code}.OF'
    
    try:
        df = ts._retry_get(ts.pro.fund_nav, ts_code=ts_code, start_date=start_date, end_date=end_date)
        
        if df is None or df.empty:
            return 0
        
        count = 0
        for _, row in df.iterrows():
            try:
                def safe_float(v):
                    return float(v) if pd.notna(v) else None
                
                nav_date = datetime.strptime(str(row['nav_date']), '%Y%m%d').date() if pd.notna(row.get('nav_date')) else None
                if nav_date is None:
                    continue
                
                rec = {
                    'code': code,
                    'ts_code': ts_code,
                    'ann_date': datetime.strptime(str(row['ann_date']), '%Y%m%d').date() if pd.notna(row.get('ann_date')) else None,
                    'nav_date': nav_date,
                    'unit_nav': safe_float(row.get('unit_nav')),
                    'accum_nav': safe_float(row.get('accum_nav')),
                    'accum_div': safe_float(row.get('accum_div')),
                    'net_asset': safe_float(row.get('net_asset')),
                    'total_netasset': safe_float(row.get('total_netasset')),
                    'adj_nav': safe_float(row.get('adj_nav')),
                    'update_flag': str(row.get('update_flag', '')),
                }
                
                with get_db_session() as session:
                    from sqlalchemy import text
                    session.execute(text('''
                        INSERT INTO fund_nav (code, ts_code, ann_date, nav_date, unit_nav, accum_nav, accum_div, net_asset, total_netasset, adj_nav, update_flag)
                        VALUES (:code, :ts_code, :ann_date, :nav_date, :unit_nav, :accum_nav, :accum_div, :net_asset, :total_netasset, :adj_nav, :update_flag)
                        ON DUPLICATE KEY UPDATE unit_nav=VALUES(unit_nav)
                    '''), rec)
                    session.commit()
                
                count += 1
            except Exception:
                continue
        
        return count
        
    except Exception:
        return 0


def main():
    print('=' * 50, flush=True)
    print('基金净值同步脚本', flush=True)
    print('=' * 50, flush=True)
    print('正在加载...', flush=True)
    
    # 获取待同步列表
    remaining = get_remaining_funds()
    total = len(remaining)
    
    if total == 0:
        print('所有基金已同步完成!', flush=True)
        return
    
    print(f'待同步基金: {total}', flush=True)
    print('按 Ctrl+C 可停止', flush=True)
    print('-' * 50, flush=True)
    print('开始同步...', flush=True)
    
    synced_count = 0
    total_records = 0
    start_time = time.time()
    
    for i, code in enumerate(remaining):
        records = sync_fund_nav(code)
        
        if records > 0:
            synced_count += 1
            total_records += records
        
        # 每100个报告一次进度
        if (i + 1) % 100 == 0:
            elapsed = time.time() - start_time
            rate = (i + 1) / elapsed * 60  # 每分钟处理数
            eta = (total - i - 1) / rate if rate > 0 else 0
            
            print(f'进度: {i+1}/{total} ({int((i+1)*100/total)}%) | '
                  f'已同步 {synced_count} 基金 | '
                  f'记录 {total_records:,} | '
                  f'预计剩余 {int(eta)} 分钟')
    
    # 最终统计
    with get_db_session() as session:
        final_nav = session.query(FundNav).count()
        final_funds = session.query(FundNav.code).distinct().count()
    
    elapsed = time.time() - start_time
    print('-' * 50)
    print(f'同步完成!')
    print(f'耗时: {int(elapsed/60)} 分钟')
    print(f'本次同步: {synced_count} 基金, {total_records:,} 记录')
    print(f'总记录: {final_nav:,}')
    print(f'总基金: {final_funds}')


if __name__ == '__main__':
    main()