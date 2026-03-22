import akshare as ak
import pandas as pd


def get_sina_data():
    try:
        print("🌐 尝试通过 AkShare (新浪数据源) 获取...")

        # 新浪接口通常不需要复杂的参数，且对反爬较宽松
        # 注意：新浪接口返回的列名可能不同
        df = ak.stock_zh_a_hist_sina(symbol="600036")

        if df is not None and not df.empty:
            # 筛选 2024 年数据 (因为新浪通常返回近期所有数据)
            df['day'] = pd.to_datetime(df['day'])
            df_2024 = df[(df['day'] >= '2024-01-01') & (df['day'] <= '2024-12-31')]

            print(f"✅ 成功获取 {len(df_2024)} 条 2024 年数据！")
            print(df_2024[['day', 'open', 'close', 'volume']].head())
            return df_2024
        else:
            print("❌ 新浪接口返回空数据")
            return None

    except Exception as e:
        print(f"❌ 新浪接口失败: {e}")
        return None


if __name__ == "__main__":
    get_sina_data()