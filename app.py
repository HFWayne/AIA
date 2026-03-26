# -*- coding: utf-8 -*-
"""
股票定投回测 Web 应用 (Streamlit)
"""

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from datetime import date

from backtest import FundBacktester, BacktestConfig
from backtest.dca_backtest import BacktestResult
from backtest.visualization import BacktestVisualizer
from data_source.config import DATA_SOURCE, AVAILABLE_SOURCES
from backtest.report_manager import ReportManager


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


def get_report_manager():
    return ReportManager()


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
    
    col5, col6, col7, col8 = st.columns(4)
    with col5:
        st.metric("最大回撤(%)", f"{result.max_drawdown:.2f}%")
    with col6:
        st.metric("定投次数(次)", f"{result.investment_count}")
    with col7:
        st.metric("止损次数(次)", f"{result.stop_loss_count}")
    with col8:
        st.metric("止盈次数(次)", f"{result.take_profit_count}")


def render_report_metrics(report):
    """渲染报告指标卡片"""
    col1, col2, col3, col4 = st.columns(4)
    r = report.result
    
    with col1:
        st.metric("总投入(元)", f"¥{r['total_invested']:,.0f}")
    with col2:
        st.metric("最终价值(元)", f"¥{r['final_value']:,.0f}")
    with col3:
        delta_color = "normal" if r['return_rate'] >= 0 else "inverse"
        st.metric("总收益(%)", f"{r['return_rate']:+.2f}%", delta=f"{r['total_return']:+,.0f}元", delta_color=delta_color)
    with col4:
        delta_color = "normal" if r['annual_return'] >= 0 else "inverse"
        st.metric("年化收益(%)", f"{r['annual_return']:+.2f}%", delta_color=delta_color)
    
    col5, col6, col7, col8 = st.columns(4)
    with col5:
        st.metric("最大回撤(%)", f"{r['max_drawdown']:.2f}%")
    with col6:
        st.metric("定投次数(次)", f"{r['investment_count']}")
    with col7:
        st.metric("止损次数(次)", f"{r['stop_loss_count']}")
    with col8:
        st.metric("止盈次数(次)", f"{r['take_profit_count']}")


def sidebar_params():
    """侧边栏参数"""
    st.sidebar.title("⚙️ 参数设置")
    
    st.sidebar.markdown("---")
    st.sidebar.subheader("📅 回测时间")
    start_date = st.sidebar.date_input("开始日期", value=date(2022, 1, 1), key="sidebar_start")
    end_date = st.sidebar.date_input("结束日期", value=date(2024, 12, 31), key="sidebar_end")
    
    st.sidebar.markdown("---")
    st.sidebar.subheader("💰 投资设置")
    amount = st.sidebar.number_input("每次定投金额(元)", min_value=100, value=1000, step=100)
    
    frequency = st.sidebar.selectbox("定投频率", ["每月", "每周", "每日"], index=0)
    freq_map = {"每月": "monthly", "每周": "weekly", "每日": "daily"}
    frequency = freq_map[frequency]
    
    day_of_month: int = 1
    day_of_week: int = 0
    if frequency == "monthly":
        day_of_month = st.sidebar.selectbox("每月定投日期", list(range(1, 29)), index=0)
    elif frequency == "weekly":
        day_of_week_str: str = st.sidebar.selectbox("每周定投日", ["周一", "周二", "周三", "周四", "周五"], index=0)
        day_of_week_map = {"周一": 0, "周二": 1, "周三": 2, "周四": 3, "周五": 4}
        day_of_week = day_of_week_map[day_of_week_str]
    
    st.sidebar.markdown("---")
    st.sidebar.subheader("📉 止损设置")
    enable_stop_loss = st.sidebar.checkbox("启用止损", value=False)
    
    stop_loss_rate = 0.15
    stop_loss_sell_ratio = 1.0
    if enable_stop_loss:
        stop_loss_rate = st.sidebar.slider("止损率(%)", min_value=5, max_value=30, value=15) / 100
        stop_loss_sell_ratio = st.sidebar.slider("止损卖出比例(%)", min_value=50, max_value=100, value=100) / 100
    
    st.sidebar.markdown("---")
    st.sidebar.subheader("📈 止盈设置")
    enable_take_profit = st.sidebar.checkbox("启用止盈", value=False)
    
    take_profit_rate = 0.20
    max_drawdown_threshold = 0.10
    take_profit_sell_ratio = 0.5
    if enable_take_profit:
        take_profit_rate = st.sidebar.slider("止盈收益率(%)", min_value=5, max_value=50, value=20) / 100
        max_drawdown_threshold = st.sidebar.slider("最大回撤阈值(%)", min_value=5, max_value=30, value=10) / 100
        take_profit_sell_ratio = st.sidebar.slider("卖出比例(%)", min_value=10, max_value=100, value=50) / 100
    
    st.sidebar.markdown("---")
    st.sidebar.subheader("📉 补仓设置")
    
    enable_dip_buy = st.sidebar.checkbox("启用单日大跌补仓", value=False)
    dip_buy_tier1_threshold = -0.03
    dip_buy_tier1_amount = 1000.0
    dip_buy_tier2_threshold = -0.05
    dip_buy_tier2_amount = 1000.0
    dip_buy_tier3_threshold = -0.07
    dip_buy_tier3_amount = 1000.0
    
    if enable_dip_buy:
        col1, col2 = st.sidebar.columns(2)
        with col1:
            st.write("档位1: 跌幅>")
            st.write("档位2: 跌幅>")
            st.write("档位3: 跌幅>")
        with col2:
            tier1 = st.selectbox("t1", ["3%", "5%", "7%"], index=0, key="dip1")
            tier2 = st.selectbox("t2", ["3%", "5%", "7%"], index=1, key="dip2")
            tier3 = st.selectbox("t3", ["3%", "5%", "7%"], index=2, key="dip3")
            tier_map = {"3%": -0.03, "5%": -0.05, "7%": -0.07}
            dip_buy_tier1_threshold = tier_map.get(tier1, -0.03)
            dip_buy_tier2_threshold = tier_map.get(tier2, -0.05)
            dip_buy_tier3_threshold = tier_map.get(tier3, -0.07)
        
        col3, col4 = st.sidebar.columns(2)
        with col3:
            st.write("补仓金额:")
        with col4:
            dip_buy_tier1_amount = st.number_input("1", min_value=100, value=1000, step=100, key="dip_amt1")
            dip_buy_tier2_amount = st.number_input("2", min_value=100, value=1000, step=100, key="dip_amt2")
            dip_buy_tier3_amount = st.number_input("3", min_value=100, value=1000, step=100, key="dip_amt3")
    
    enable_yield_boost = st.sidebar.checkbox("启用累计收益率增额", value=False)
    yield_boost_trigger = -0.20
    yield_boost_recover = -0.10
    yield_boost_amount = 1000.0
    
    if enable_yield_boost:
        yield_boost_trigger = st.sidebar.slider("累计收益率低于(%)", min_value=-30, max_value=-5, value=-20) / 100
        yield_boost_amount = st.sidebar.number_input("每次增额(元)", min_value=100, value=1000, step=100)
        yield_boost_recover = st.sidebar.slider("收益率回升到(%)", min_value=-30, max_value=-5, value=-10) / 100
        
        if yield_boost_recover >= yield_boost_trigger:
            st.sidebar.error("恢复阈值必须大于触发阈值")
    
    st.sidebar.markdown("---")
    st.sidebar.subheader("📡 数据源")
    data_source = st.sidebar.selectbox("选择数据源", AVAILABLE_SOURCES, index=0)
    
    return (start_date, end_date, amount, frequency, day_of_month, day_of_week, data_source,
            enable_stop_loss, stop_loss_rate, stop_loss_sell_ratio,
            enable_take_profit, take_profit_rate, max_drawdown_threshold, take_profit_sell_ratio,
            enable_dip_buy, dip_buy_tier1_threshold, dip_buy_tier1_amount,
            dip_buy_tier2_threshold, dip_buy_tier2_amount,
            dip_buy_tier3_threshold, dip_buy_tier3_amount,
            enable_yield_boost, yield_boost_trigger, yield_boost_recover, yield_boost_amount)


def plot_report_trades(report):
    """绘制报告的交易曲线"""
    trades = pd.DataFrame(report.trades)
    trades['date'] = pd.to_datetime(trades['date'])
    trades = trades.sort_values('date')
    trades['total_invested'] = [report.investment_amount * i for i in range(1, len(trades) + 1)]
    
    fig, axes = plt.subplots(2, 1, figsize=(10, 8), dpi=100)
    
    ax1 = axes[0]
    ax1.plot(trades['date'], trades['total_invested'], label='累计投入', color='blue', linewidth=2)
    ax1.plot(trades['date'], trades['portfolio_value'], label='资产总值', color='green', linewidth=2)
    ax1.fill_between(trades['date'], trades['total_invested'], trades['portfolio_value'],
                    where=trades['portfolio_value'] >= trades['total_invested'],
                    alpha=0.3, color='green', label='盈利')
    ax1.fill_between(trades['date'], trades['total_invested'], trades['portfolio_value'],
                    where=trades['portfolio_value'] < trades['total_invested'],
                    alpha=0.3, color='red', label='亏损')
    ax1.set_title(f'{report.name} - 投入与收益曲线', fontsize=12)
    ax1.set_xlabel('日期')
    ax1.set_ylabel('金额(元)')
    ax1.legend(loc='upper left')
    ax1.grid(True, alpha=0.3)
    
    ax2 = axes[1]
    ax2.plot(trades['date'], trades['return_rate'], color='purple', linewidth=2)
    ax2.axhline(y=0, color='black', linestyle='--', alpha=0.5)
    ax2.fill_between(trades['date'], 0, trades['return_rate'],
                     where=trades['return_rate'] >= 0, alpha=0.3, color='green')
    ax2.fill_between(trades['date'], 0, trades['return_rate'],
                     where=trades['return_rate'] < 0, alpha=0.3, color='red')
    ax2.set_title(f'{report.name} - 收益率走势', fontsize=12)
    ax2.set_xlabel('日期')
    ax2.set_ylabel('收益率(%)')
    ax2.grid(True, alpha=0.3)
    
    plt.tight_layout()
    return fig


def page_single_backtest(sd, ed, amt, freq, day_of_month, day_of_week, ds, esl, slr, slsr, etp, tpr, mdt, tpsr,
                        edb, dt1, da1, dt2, da2, dt3, da3, eyb, ybt, ybr, yba):
    """单股票回测页面"""
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
                tester = FundBacktester(data_source=ds)
                
                config = BacktestConfig(
                    fund_code=fund_code,
                    fund_name=fund_name,
                    start_date=str(sd),
                    end_date=str(ed),
                    investment_amount=amt,
                    frequency=freq,
                    day_of_month=day_of_month,
                    day_of_week=day_of_week,
                    data_source=ds,
                    enable_stop_loss=esl,
                    stop_loss_rate=slr,
                    stop_loss_sell_ratio=slsr,
                    enable_take_profit=etp,
                    take_profit_rate=tpr,
                    max_drawdown_threshold=mdt,
                    take_profit_sell_ratio=tpsr,
                    enable_dip_buy=edb,
                    dip_buy_tier1_threshold=dt1,
                    dip_buy_tier1_amount=da1,
                    dip_buy_tier2_threshold=dt2,
                    dip_buy_tier2_amount=da2,
                    dip_buy_tier3_threshold=dt3,
                    dip_buy_tier3_amount=da3,
                    enable_yield_boost=eyb,
                    yield_boost_trigger=ybt,
                    yield_boost_recover=ybr,
                    yield_boost_amount=yba
                )
                
                result = tester.single_fund(config)
                
                if result:
                    result.strategy_params = {
                        'fund_code': fund_code,
                        'fund_name': fund_name,
                        'start_date': str(sd),
                        'end_date': str(ed),
                        'frequency': freq,
                        'day_of_month': day_of_month,
                        'day_of_week': day_of_week,
                        'enable_stop_loss': esl,
                        'stop_loss_rate': slr,
                        'stop_loss_sell_ratio': slsr,
                        'enable_take_profit': etp,
                        'take_profit_rate': tpr,
                        'max_drawdown_threshold': mdt,
                        'take_profit_sell_ratio': tpsr,
                        'enable_dip_buy': edb,
                        'enable_yield_boost': eyb
                    }
                    st.session_state['current_result'] = result
                    st.session_state['current_fund_name'] = fund_name
        
        current_result = st.session_state.get('current_result')
        current_fund_name = st.session_state.get('current_fund_name', fund_name)
        
        if current_result:
            st.success(f"✅ 回测完成 - {current_fund_name}")
            
            render_metrics(current_result)
            
            if st.button("💾 保存报告", key="save_report_btn", use_container_width=True):
                rm = get_report_manager()
                report_id = rm.save_report(current_result)
                st.session_state['last_save_id'] = report_id
                st.session_state['refresh_reports'] = True
                st.rerun()
            
            if 'last_save_id' in st.session_state:
                st.success(f"报告已保存! ID: {st.session_state['last_save_id']}")
            
            st.markdown("### ")
            visualizer = BacktestVisualizer()
            fig = visualizer.plot_single_fund(current_result, current_fund_name)
            st.pyplot(fig)
            
            with st.expander("📋 查看交易记录", expanded=False):
                trades_display = current_result.trades.copy()
                trades_display['date'] = pd.to_datetime(trades_display['date']).astype(str).str[:10]
                
                display_cols = ['date', 'action', 'nav', 'shares', 'total_shares', 'portfolio_value', 'return_rate', 'reason']
                if 'invest_amount' in trades_display.columns:
                    display_cols.insert(5, 'invest_amount')
                
                trades_display = trades_display[display_cols].copy()
                trades_display.columns = ['日期', '操作', '净值(元)', '份额变化(份)', '累计份额(份)', '投入金额(元)', '组合价值(元)', '收益率(%)', '原因']
                trades_display['份额变化(份)'] = trades_display['份额变化(份)'].round(2)
                if '投入金额(元)' in trades_display.columns:
                    trades_display['投入金额(元)'] = trades_display['投入金额(元)'].round(0).astype(int)
                trades_display['累计份额(份)'] = trades_display['累计份额(份)'].round(2)
                trades_display['组合价值(元)'] = trades_display['组合价值(元)'].round(0).astype(int)
                st.dataframe(trades_display, width='stretch', height=300)
        elif run_btn:
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


def page_compare(sd2, ed2, amt2, esl, slr, etp, tpr, mdt, tpsr, ds):
    """多股票对比页面"""
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
        
        amount2 = st.number_input("每次定投金额(元)", min_value=100, value=1000, step=100, key="amt2")
        
        compare_btn = st.button("🔍 开始对比", type="primary", use_container_width=True)
    
    with col_right:
        if compare_btn:
            with st.spinner("正在获取数据并计算..."):
                codes = [c.strip() for c in compare_funds.split(',') if c.strip()]
                fund_list = [{'fund_code': c, 'name': get_fund_name(c)} for c in codes]
                
                tester = FundBacktester(data_source=ds)
                results = tester.compare(
                    fund_list, str(start_date2), str(end_date2), amount2,
                    enable_stop_loss=esl,
                    stop_loss_rate=slr,
                    enable_take_profit=etp,
                    take_profit_rate=tpr,
                    max_drawdown_threshold=mdt,
                    sell_ratio=tpsr
                )
                
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
                            '定投次数(次)': r.investment_count,
                            '止损(次)': r.stop_loss_count,
                            '止盈(次)': r.take_profit_count
                        }
                        for name, r in results.items()
                    ])
                    
                    st.dataframe(comp_df, width='stretch', hide_index=True)
                    
                    st.markdown("### ")
                    visualizer = BacktestVisualizer()
                    fig = visualizer.plot_comparison(results)
                    st.pyplot(fig)
                else:
                    st.error("获取数据失败，请检查股票代码或尝试其他数据源")
        else:
            st.info("👈 请输入股票代码并点击开始对比")


def page_reports():
    """报告管理页面"""
    if 'refresh_reports' not in st.session_state:
        st.session_state['refresh_reports'] = True
    
    rm = ReportManager()
    
    if st.session_state.get('refresh_reports', False):
        st.cache_data.clear()
        st.session_state['refresh_reports'] = False
    
    reports = rm.list_reports()
    
    tab1, tab2, tab3 = st.tabs(["📋 报告列表", "📊 报告详情", "📈 报告对比"])
    
    with tab1:
        st.markdown('<div class="section-header">📋 已保存的报告</div>', unsafe_allow_html=True)
        
        if not reports:
            st.info("暂无保存的报告，请先进行回测并保存报告")
        else:
            col_search, col_filter = st.columns([2, 1])
            with col_search:
                search = st.text_input("搜索报告", "", key="search_reports")
            with col_filter:
                fund_codes = list(set(r.fund_code for r in reports))
                filter_code = st.selectbox("筛选股票", ["全部"] + fund_codes, key="filter_reports")
            
            filtered_reports = rm.list_reports(
                fund_code=filter_code if filter_code != "全部" else None,
                search=search if search else None
            )
            
            if filtered_reports:
                for report in filtered_reports:
                    with st.container():
                        col_name, col_rate, col_actions = st.columns([4, 1, 1])
                        with col_name:
                            st.markdown(f"**{report.name}**")
                            st.caption(f"ID: {report.id} | 创建: {report.created_at[:19]}")
                        with col_rate:
                            delta = "🔼" if report.result['return_rate'] >= 0 else "🔽"
                            st.write(f"{delta} {report.result['return_rate']:+.2f}%")
                        with col_actions:
                            col_v, col_d = st.columns(2)
                            with col_v:
                                if st.button("查看", key=f"view_{report.id}"):
                                    st.session_state['selected_report_id'] = report.id
                                    st.rerun()
                            with col_d:
                                if st.button("删除", key=f"del_{report.id}"):
                                    rm.delete_report(report.id)
                                    st.rerun()
                        
                        st.markdown("---")
            else:
                st.info("没有找到匹配的报告")
    
    with tab2:
        st.markdown('<div class="section-header">📊 报告详情</div>', unsafe_allow_html=True)
        
        reports = rm.list_reports()
        
        if not reports:
            st.info("暂无报告")
        else:
            default_idx = 0
            selected_id = st.session_state.get('selected_report_id')
            if selected_id:
                for i, r in enumerate(reports):
                    if r.id == selected_id:
                        default_idx = i
                        break
            
            report_options = [f"{r.name} ({r.created_at[:10]})" for r in reports]
            report_ids = [r.id for r in reports]
            
            selected_idx = st.selectbox(
                "选择报告",
                range(len(reports)),
                index=default_idx,
                format_func=lambda x: report_options[x],
                key="select_report_detail"
            )
            
            report_id = report_ids[selected_idx]
            report = rm.load_report(report_id)
            
            if report:
                st.subheader(report.name)
                st.caption(f"创建时间: {report.created_at}")
                
                render_report_metrics(report)
                
                st.markdown("### ")
                fig = plot_report_trades(report)
                st.pyplot(fig)
                
                if st.button("🗑️ 删除报告", key="delete_from_detail"):
                    rm.delete_report(report_id)
                    st.session_state['selected_report_id'] = None
                    st.rerun()
                
                with st.expander("📋 查看交易记录"):
                    trades_df = pd.DataFrame(report.trades)
                    trades_df['date'] = pd.to_datetime(trades_df['date']).dt.strftime('%Y-%m-%d')
                    
                    display_cols = ['date', 'action', 'nav', 'shares', 'total_shares', 'portfolio_value', 'return_rate', 'reason']
                    if 'invest_amount' in trades_df.columns:
                        display_cols.insert(5, 'invest_amount')
                    
                    trades_display = trades_df[display_cols].copy()
                    trades_display.columns = ['日期', '操作', '净值(元)', '份额变化(份)', '累计份额(份)', '投入金额(元)', '组合价值(元)', '收益率(%)', '原因']
                    trades_display['份额变化(份)'] = trades_display['份额变化(份)'].round(2)
                    if '投入金额(元)' in trades_display.columns:
                        trades_display['投入金额(元)'] = trades_display['投入金额(元)'].round(0).astype(int)
                    trades_display['累计份额(份)'] = trades_display['累计份额(份)'].round(2)
                    trades_display['组合价值(元)'] = trades_display['组合价值(元)'].round(0).astype(int)
                    st.dataframe(trades_display, width='stretch', height=300)
    
    with tab3:
        st.markdown('<div class="section-header">📈 报告对比</div>', unsafe_allow_html=True)
        
        if len(reports) < 2:
            st.info("需要至少2个报告才能进行对比")
        else:
            selected_ids = st.multiselect("选择要对比的报告（至少选择2个）",
                                         options=[r.id for r in reports],
                                         default=[r.id for r in reports[:2]] if len(reports) >= 2 else [],
                                         format_func=lambda x: next((r.name for r in reports if r.id == x), ""))
            
            if len(selected_ids) >= 2:
                selected_reports = [rm.load_report(rid) for rid in selected_ids]
                valid_reports = [r for r in selected_reports if r is not None]
                
                comp_df = pd.DataFrame([
                    {
                        '报告': r.name,
                        '股票': r.fund_name,
                        '日期范围': f"{r.start_date} ~ {r.end_date}",
                        '总投入(元)': f"¥{r.result['total_invested']:,.0f}",
                        '最终价值(元)': f"¥{r.result['final_value']:,.0f}",
                        '总收益(%)': f"{r.result['return_rate']:+.2f}%",
                        '年化收益(%)': f"{r.result['annual_return']:+.2f}%",
                        '最大回撤(%)': f"{r.result['max_drawdown']:.2f}%",
                        '定投次数': r.result['investment_count'],
                        '止损次数': r.result['stop_loss_count'],
                        '止盈次数': r.result['take_profit_count']
                    }
                    for r in valid_reports
                ])
                
                st.dataframe(comp_df, width='stretch', hide_index=True)
                
                st.markdown("### ")
                
                fig, axes = plt.subplots(2, 2, figsize=(14, 10), dpi=100)
                
                names = [r.name for r in valid_reports]
                
                ax1 = axes[0, 0]
                x = range(len(names))
                invested = [r.result['total_invested'] for r in valid_reports]
                final = [r.result['final_value'] for r in valid_reports]
                width = 0.35
                ax1.bar([i - width/2 for i in x], invested, width, label='总投入', color='steelblue')
                ax1.bar([i + width/2 for i in x], final, width, label='最终价值', color='coral')
                ax1.set_xticks(x)
                ax1.set_xticklabels(names, rotation=15)
                ax1.set_ylabel('金额(元)')
                ax1.set_title('投入与价值对比')
                ax1.legend()
                ax1.grid(True, alpha=0.3)
                
                ax2 = axes[0, 1]
                returns = [r.result['return_rate'] for r in valid_reports]
                colors = ['green' if r >= 0 else 'red' for r in returns]
                ax2.bar(names, returns, color=colors)
                ax2.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
                ax2.set_ylabel('收益率(%)')
                ax2.set_title('总收益率对比')
                ax2.grid(True, alpha=0.3)
                for i, v in enumerate(returns):
                    ax2.text(i, v + 1 if v >= 0 else v - 3, f'{v:.1f}%', ha='center', fontsize=9)
                
                ax3 = axes[1, 0]
                annual = [r.result['annual_return'] for r in valid_reports]
                colors = ['green' if r >= 0 else 'red' for r in annual]
                ax3.bar(names, annual, color=colors)
                ax3.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
                ax3.set_ylabel('年化收益(%)')
                ax3.set_title('年化收益率对比')
                ax3.grid(True, alpha=0.3)
                
                ax4 = axes[1, 1]
                drawdowns = [r.result['max_drawdown'] for r in valid_reports]
                ax4.barh(names, drawdowns, color='orange')
                ax4.set_xlabel('最大回撤(%)')
                ax4.set_title('最大回撤对比')
                
                plt.tight_layout()
                st.pyplot(fig)
            else:
                st.info("请至少选择2个报告进行对比")


def main():
    st.markdown('<div class="main-header">📈 股票定投回测工具</div>', unsafe_allow_html=True)
    
    params = sidebar_params()
    (start_date, end_date, amount, frequency, day_of_month, day_of_week, data_source,
     enable_stop_loss, stop_loss_rate, stop_loss_sell_ratio,
     enable_take_profit, take_profit_rate, max_drawdown_threshold, take_profit_sell_ratio,
     enable_dip_buy, dip_buy_tier1_threshold, dip_buy_tier1_amount,
     dip_buy_tier2_threshold, dip_buy_tier2_amount,
     dip_buy_tier3_threshold, dip_buy_tier3_amount,
     enable_yield_boost, yield_boost_trigger, yield_boost_recover, yield_boost_amount) = params
    
    tab1, tab2, tab3 = st.tabs(["📊 单股票回测", "📈 多股票对比", "📁 报告管理"])
    
    with tab1:
        page_single_backtest(start_date, end_date, amount, frequency, day_of_month, day_of_week, data_source,
                           enable_stop_loss, stop_loss_rate, stop_loss_sell_ratio,
                           enable_take_profit, take_profit_rate, max_drawdown_threshold, take_profit_sell_ratio,
                           enable_dip_buy, dip_buy_tier1_threshold, dip_buy_tier1_amount,
                           dip_buy_tier2_threshold, dip_buy_tier2_amount,
                           dip_buy_tier3_threshold, dip_buy_tier3_amount,
                           enable_yield_boost, yield_boost_trigger, yield_boost_recover, yield_boost_amount)
    
    with tab2:
        page_compare(start_date, end_date, amount, enable_stop_loss, stop_loss_rate,
                    enable_take_profit, take_profit_rate, max_drawdown_threshold,
                    take_profit_sell_ratio, data_source)
    
    with tab3:
        page_reports()


if __name__ == "__main__":
    main()
