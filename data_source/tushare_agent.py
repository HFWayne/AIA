

import tushare as ts
import pandas as pd
from config import TU_SHARE_TOKEN

# 1. 设置你的 Token (替换为你自己的)
ts.set_token(TU_SHARE_TOKEN)
pro = ts.pro_api()


def get_tushare_data():
    try:
        print("🚀 正在通过 Tushare Pro 获取数据...")
        # 获取招商银行 (600036.SH) 2024年日线数据
        # 注意：Tushare 代码格式为 "代码.交易所" (如 600036.SH, 000001.SZ)
        df = pro.daily(
            ts_code='600036.SH',
            start_date='20240101',
            end_date='20241231'
        )

        if df is not None and not df.empty:
            print(f"✅ 成功获取 {len(df)} 条数据")
            # 重命名列以符合习惯
            df = df.rename(columns={
                'trade_date': '日期', 'open': '开盘', 'close': '收盘',
                'high': '最高', 'low': '最低', 'vol': '成交量', 'amount': '成交额'
            })
            print(df[['日期', '开盘', '收盘', '成交量']].head())
            return df
        else:
            print("❌ 未获取到数据，请检查 Token 权限或股票代码格式")
            return None

    except Exception as e:
        print(f"❌ Tushare 接口报错: {e}")
        return None


if __name__ == "__main__":
    get_tushare_data()