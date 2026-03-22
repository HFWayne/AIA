import baostock as bs
import pandas as pd


def debug_baostock():
    # 1. 登录
    lg = bs.login()
    if lg.error_code != '0':
        print(f"❌ 登录失败: {lg.error_msg}")
        return

    print("✅ 登录成功！")

    # 【关键点】代码格式必须是 sh. 或 sz. 开头，且全小写
    stock_code = "sh.600036"
    start_date = "2024-01-01"
    end_date = "2024-12-31"

    print(f"🚀 正在查询: {stock_code} ({start_date} 至 {end_date})...")

    # 2. 获取数据
    # fields 中不要包含 time (日线数据通常不需要具体时间)，避免兼容性问题
    fields = "date,open,high,low,close,volume,amount,adjustflag"
    rs = bs.query_history_k_data_plus(
        stock_code,
        fields,
        start_date=start_date,
        end_date=end_date,
        frequency="d",
        adjustflag="3"  # 3=前复权
    )

    # 3. 【关键检查】打印接口返回的错误码和错误信息
    if rs.error_code != '0':
        print(f"❌ 查询接口报错! 错误码: {rs.error_code}, 信息: {rs.error_msg}")
        print("💡 常见原因：代码格式不对，或者日期格式应为 YYYY-MM-DD")
        bs.logout()
        return

    # 4. 提取数据
    data_list = []
    while rs.error_code == '0' and rs.next():
        data_list.append(rs.get_row_data())

    # 再次检查循环结束后是否有错误
    if rs.error_code != '0':
        print(f"❌ 遍历数据时出错: {rs.error_msg}")

    if len(data_list) == 0:
        print("❌ 仍无数据。可能原因：")
        print("   1. 该时间段股票停牌。")
        print("   2. 服务器暂时没同步到最新数据（尝试把结束日期往前推一个月）。")
        print("   3. 代码格式依然不匹配。")
        # 尝试打印一个已知有效的测试
        print("\n🧪 尝试测试另一个代码 (sz.000001)...")
        rs_test = bs.query_history_k_data_plus("sz.000001", fields, "2024-01-01", "2024-01-31", "d", "3")
        if rs_test.error_code == '0':
            count = 0
            while rs_test.next(): count += 1
            print(f"   测试结果显示平安银行有 {count} 条数据。说明库正常，可能是 600036 的问题或网络波动。")
        else:
            print(f"   测试也失败: {rs_test.error_msg}")
    else:
        df = pd.DataFrame(data_list, columns=rs.fields)
        print(f"✅ 成功获取 {len(df)} 条数据！")
        print(df.head())

    bs.logout()


if __name__ == "__main__":
    debug_baostock()