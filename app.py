# -*- coding: utf-8 -*-
"""
股票定投回测 Web 应用 (Streamlit)
"""

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from datetime import date

from backtest import FundBacktester, BacktestConfig
from backtest.visualization import BacktestVisualizer
from data_source.config import DATA_SOURCE, AVAILABLE_SOURCES


st.set_page_config(
    page_title="股票定投回测工具",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)


plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'SimSun', 'Arial']
plt.rcParams['axes.unicode_minus'] = False


st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        text-align: center;
        padding: 1rem;
        background: linear-gradient(90deg, #1e3c72, #2a5298);
        color: white;
        border-radius: 10px;
        margin-bottom: 1.5rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 10px;
        border-left: 4px solid #4e8cff;
    }
    .metric-positive {
        color: #28a745;
    }
    .metric-negative {
        color: #dc3545;
    }
    .section-header {
        font-size: 1.3rem;
        font-weight: bold;
        padding: 0.5rem;
        border-bottom: 2px solid #4e8cff;
        margin-bottom: 1rem;
    }
    .stButton > button {
        width: 100%;
        border-radius: 8px;
        padding: 0.8rem;
    }
    div[data-testid="stMetric"] {
        background-color: #f8f9fa;
        padding: 10px;
        border-radius: 8px;
    }
</style>
""", unsafe_allow_html=True)


NAME_MAP = {
    '600036': '招商银行', '601318': '中国平安', '000858': '五粮液',
    '600519': '贵州茅台', '601888': '中国中免', '300750': '宁德时代',
    '000001': '上证指数', '399001': '深证成指', '399006': '创业板指',
    '000300': '沪深300', '000905': '中证500', '000016': '上证50',
}


def get_fund_name(code: str) -> str:
    return NAME_MAP.get(code, code)


def render_metrics(result):
    """渲染指标卡片"""
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("总投入(元)", f"¥{result.total_invested:,.0f}")
    with col2:
        st.metric("最终价值(元)", f"¥{result.final_value:,.0f}")
    with col3:
        delta_color = "normal" if result.return_rate >= 0 else "inverse"
        st.metric("总收益(%)", f"{result.return_rate:+.2f}%", delta=f"{result.total_return:+,.0f}元", delta_color=delta_color)
    with col4:
        delta_color = "normal" if result.annual_return >= 0 else "inverse"
        st.metric("年化收益(%)", f"{result.annual_return:+.2f}%", delta_color=delta_color)
    
    col5, col6 = st.columns(2)
    with col5:
        st.metric("最大回撤(%)", f"{result.max_drawdown:.2f}%")
    with col6:
        st.metric("定投次数(次)", f"{result.investment_count}")


def sidebar_params():
    """侧边栏参数"""
    st.sidebar.title("⚙️ 参数设置")
    
    st.sidebar.markdown("---")
    st.sidebar.subheader("📅 回测时间")
    start_date = st.sidebar.date_input("开始日期", value=date(2022, 1, 1), key="sidebar_start")
    end_date = st.sidebar.date_input("结束日期", value=date(2024, 12, 31), key="sidebar_end")
    
    st.sidebar.markdown("---")
    st.sidebar.subheader("💰 投资设置")
    amount = st.sidebar.number_input("每次定投金额", min_value=100, value=1000, step=100)
    
    frequency = st.sidebar.selectbox("定投频率", ["每月", "每周", "每日"], index=0)
    freq_map = {"每月": "monthly", "每周": "weekly", "每日": "daily"}
    frequency = freq_map[frequency]
    
    st.sidebar.markdown("---")
    st.sidebar.subheader("📡 数据源")
    data_source = st.sidebar.selectbox("选择数据源", AVAILABLE_SOURCES, index=0)
    
    return start_date, end_date, amount, frequency, data_source


def main():
    st.markdown('<div class="main-header">📈 股票定投回测工具</div>', unsafe_allow_html=True)
    
    start_date, end_date, amount, frequency, data_source = sidebar_params()
    
    tab1, tab2 = st.tabs(["📊 单股票回测", "📈 多股票对比"])
    
    with tab1:
        col1, col2 = st.columns([1, 2.5])
        
        with col1:
            with st.container():
                st.markdown('<div class="section-header">📝 股票选择</div>', unsafe_allow_html=True)
                fund_code = st.text_input("股票代码", value="600036", help="如: 600036")
                fund_name = st.text_input("股票名称", value="", help="留空则自动识别")
                
                if not fund_name:
                    fund_name = get_fund_name(fund_code)
                
                st.info(f"当前选择: **{fund_name}** ({fund_code})")
                
                st.markdown("### ")
                run_btn = st.button("🚀 开始回测", type="primary", use_container_width=True)
        
        with col2:
            if run_btn:
                with st.spinner("正在获取数据并计算..."):
                    tester = FundBacktester(data_source=data_source)
                    
                    config = BacktestConfig(
                        fund_code=fund_code,
                        fund_name=fund_name,
                        start_date=str(start_date),
                        end_date=str(end_date),
                        investment_amount=amount,
                        frequency=frequency,
                        data_source=data_source
                    )
                    
                    result = tester.single_fund(config)
                    
                    if result:
                        st.success(f"✅ 回测完成 - {fund_name}")
                        
                        render_metrics(result)
                        
                        st.markdown("### ")
                        visualizer = BacktestVisualizer()
                        fig = visualizer.plot_single_fund(result, fund_name)
                        st.pyplot(fig)
                        
                        with st.expander("📋 查看交易记录", expanded=False):
                            trades_display = result.trades[['date', 'nav', 'shares', 'total_shares', 'portfolio_value', 'return_rate']].copy()
                            trades_display.columns = ['日期', '净值(元)', '买入份额(份)', '累计份额(份)', '组合价值(元)', '收益率(%)']
                            trades_display['日期'] = pd.to_datetime(trades_display['日期']).astype(str).str[:10]
                            st.dataframe(trades_display, use_container_width=True, height=300)
                    else:
                        st.error("获取数据失败，请检查股票代码或尝试其他数据源")
            else:
                st.info("👈 请在左侧输入股票代码并点击开始回测")
                
                st.markdown("---")
                st.markdown("### 💡 常用股票代码")
                col_q1, col_q2, col_q3 = st.columns(3)
                with col_q1:
                    st.code("600036 - 招商银行")
                    st.code("601318 - 中国平安")
                with col_q2:
                    st.code("600519 - 贵州茅台")
                    st.code("000858 - 五粮液")
                with col_q3:
                    st.code("000001 - 上证指数")
                    st.code("399001 - 深证成指")
    
    with tab2:
        st.markdown('<div class="section-header">📈 多股票对比分析</div>', unsafe_allow_html=True)
        
        col_left, col_right = st.columns([1, 2.5])
        
        with col_left:
            compare_funds = st.text_area("股票代码（逗号分隔）", value="600036,601318,600519", height=100,
                                         help="多个代码用逗号分隔，如: 600036,601318,600519")
            
            col_start2, col_end2 = st.columns(2)
            with col_start2:
                start_date2 = st.date_input("开始日期", value=date(2022, 1, 1), key="start2")
            with col_end2:
                end_date2 = st.date_input("结束日期", value=date(2024, 12, 31), key="end2")
            
            amount2 = st.number_input("每次定投金额", min_value=100, value=1000, step=100, key="amt2")
            
            compare_btn = st.button("🔍 开始对比", type="primary", use_container_width=True)
        
        with col_right:
            if compare_btn:
                with st.spinner("正在获取数据并计算..."):
                    codes = [c.strip() for c in compare_funds.split(',') if c.strip()]
                    fund_list = [{'fund_code': c, 'name': get_fund_name(c)} for c in codes]
                    
                    tester = FundBacktester(data_source=data_source)
                    results = tester.compare(fund_list, str(start_date2), str(end_date2), amount2)
                    
                    if results:
                        st.success(f"✅ 对比完成 - {len(results)} 个股票")
                        
                        comp_df = pd.DataFrame([
                            {
                                '股票': name,
                                '总投入(元)': f"¥{r.total_invested:,.0f}",
                                '最终价值(元)': f"¥{r.final_value:,.0f}",
                                '总收益(%)': f"{r.return_rate:+.2f}%",
                                '年化收益(%)': f"{r.annual_return:+.2f}%",
                                '最大回撤(%)': f"{r.max_drawdown:.2f}%",
                                '定投次数(次)': r.investment_count
                            }
                            for name, r in results.items()
                        ])
                        
                        st.dataframe(comp_df, use_container_width=True, hide_index=True)
                        
                        st.markdown("### ")
                        visualizer = BacktestVisualizer()
                        fig = visualizer.plot_comparison(results)
                        st.pyplot(fig)
                    else:
                        st.error("获取数据失败，请检查股票代码或尝试其他数据源")
            else:
                st.info("👈 请输入股票代码并点击开始对比")


if __name__ == "__main__":
    main()
