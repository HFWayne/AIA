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
from backtest.page_watchlist import render_watchlist_manager
from backtest.page_strategy import render_strategy_manager
from backtest.page_task import render_task_manager
from backtest.page_diagnostic import render_diagnostic_page
from i18n import t, render_language_selector, get_locale


st.set_page_config(
    page_title=t("page_title"),
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)


plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'SimSun', 'Arial']
plt.rcParams['axes.unicode_minus'] = False


st.markdown("""
<style>
    /* ===== 主题变量 ===== */
    :root {
        --primary: #4F8CFF;
        --primary-dark: #3a6fd8;
        --success: #10B981;
        --warning: #F59E0B;
        --danger: #EF4444;
        --bg-card: #FFFFFF;
        --bg-main: #F8FAFC;
        --text-primary: #1E293B;
        --text-secondary: #64748B;
        --border-color: #E2E8F0;
    }

    /* ===== 主标题 ===== */
    .main-header {
        font-size: 2rem;
        font-weight: 700;
        text-align: center;
        padding: 1.2rem;
        background: linear-gradient(135deg, #1E3A5F 0%, #2D5A87 50%, #4F8CFF 100%);
        color: white;
        border-radius: 16px;
        margin-bottom: 1.5rem;
        box-shadow: 0 4px 20px rgba(79, 140, 255, 0.3);
        letter-spacing: 1px;
    }

    /* ===== 区块标题 ===== */
    .section-header {
        font-size: 1.2rem;
        font-weight: 600;
        color: var(--text-primary);
        padding: 0.75rem 1rem;
        background: linear-gradient(90deg, rgba(79, 140, 255, 0.1) 0%, transparent 100%);
        border-left: 4px solid var(--primary);
        border-radius: 0 8px 8px 0;
        margin-bottom: 1rem;
    }

    /* ===== 指标卡片容器 ===== */
    div[data-testid="stHorizontalBlock"] > div[data-testid="stVerticalBlock"] {
        gap: 0.75rem;
    }

    /* ===== 指标卡片样式 ===== */
    div[data-testid="stMetric"] {
        background: var(--bg-card);
        border: 1px solid var(--border-color);
        border-radius: 12px;
        padding: 1rem;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
        transition: all 0.2s ease;
    }
    div[data-testid="stMetric"]:hover {
        box-shadow: 0 4px 16px rgba(79, 140, 255, 0.15);
        border-color: var(--primary);
    }
    div[data-testid="stMetricLabel"] {
        color: var(--text-secondary);
        font-size: 0.85rem;
        font-weight: 500;
    }
    div[data-testid="stMetricValue"] {
        color: var(--text-primary);
        font-size: 1.5rem;
        font-weight: 700;
    }

    /* ===== 主按钮样式 ===== */
    .stButton > button[kind="primary"],
    .st-emotion-cache-1gptmug > button[kind="primary"] {
        background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%);
        color: white;
        border: none;
        border-radius: 10px;
        padding: 0.75rem 1.5rem;
        font-weight: 600;
        transition: all 0.2s ease;
        box-shadow: 0 2px 8px rgba(79, 140, 255, 0.3);
    }
    .stButton > button[kind="primary"]:hover,
    .st-emotion-cache-1gptmug > button[kind="primary"]:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 16px rgba(79, 140, 255, 0.4);
    }

    /* ===== 次要按钮样式 ===== */
    .stButton > button {
        border-radius: 8px;
        padding: 0.5rem 1rem;
        transition: all 0.2s ease;
    }

    /* ===== Tab 样式 ===== */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0.5rem;
        background: var(--bg-main);
        padding: 0.5rem;
        border-radius: 12px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px;
        padding: 0.75rem 1.25rem;
        font-weight: 500;
    }
    .stTabs [aria-selected="true"] {
        background: var(--bg-card) !important;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
    }

    /* ===== 卡片容器 ===== */
    .card {
        background: var(--bg-card);
        border: 1px solid var(--border-color);
        border-radius: 12px;
        padding: 1.25rem;
        margin-bottom: 1rem;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
    }

    /* ===== 成功/错误/警告消息 ===== */
    .stAlert {
        border-radius: 10px;
        padding: 1rem;
    }

    /* ===== 表格样式 ===== */
    .dataframe {
        border: none !important;
    }
    .dataframe thead th {
        background: linear-gradient(135deg, #f1f5f9 0%, #e2e8f0 100%) !important;
        color: var(--text-primary) !important;
        font-weight: 600 !important;
        padding: 0.75rem 1rem !important;
        border-bottom: 2px solid var(--border-color) !important;
    }
    .dataframe tbody tr:nth-child(even) {
        background: #F8FAFC !important;
    }
    .dataframe tbody tr:hover {
        background: rgba(79, 140, 255, 0.08) !important;
    }
    .dataframe tbody td {
        padding: 0.75rem 1rem !important;
        border-bottom: 1px solid var(--border-color) !important;
    }

    /* ===== 侧边栏样式 ===== */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #F8FAFC 0%, #FFFFFF 100%);
        border-right: 1px solid var(--border-color);
    }
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h1,
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h2 {
        color: var(--text-primary);
    }

    /* ===== Divider 分隔线 ===== */
    hr {
        border: none;
        border-top: 1px solid var(--border-color);
        margin: 1rem 0;
    }

    /* ===== 输入框样式 ===== */
    .stTextInput > div > div > input,
    .stNumberInput > div > div > input,
    .stTextArea > div > div > textarea,
    .stSelectbox > div > div {
        border-radius: 8px;
        border: 1px solid var(--border-color);
    }
    .stTextInput > div > div > input:focus,
    .stNumberInput > div > div > input:focus,
    .stTextArea > div > div > textarea:focus {
        border-color: var(--primary);
        box-shadow: 0 0 0 3px rgba(79, 140, 255, 0.1);
    }

    /* ===== 进度条样式 ===== */
    .stProgress > div > div > div > div {
        background: linear-gradient(90deg, var(--primary) 0%, var(--primary-dark) 100%);
        border-radius: 8px;
    }

    /* ===== 折叠面板 ===== */
    .streamlit-expanderHeader {
        background: var(--bg-card);
        border: 1px solid var(--border-color);
        border-radius: 10px;
        padding: 0.75rem 1rem;
    }
    .streamlit-expanderHeader:hover {
        border-color: var(--primary);
    }

    /* ===== 负收益高亮 ===== */
    .negative-value {
        color: var(--danger);
        font-weight: 600;
    }
    .positive-value {
        color: var(--success);
        font-weight: 600;
    }

    /* ===== 空状态样式 ===== */
    .empty-state {
        text-align: center;
        padding: 3rem;
        color: var(--text-secondary);
    }

    /* ===== 数字卡片特殊样式 ===== */
    .metric-positive {
        border-left: 4px solid var(--success);
    }
    .metric-negative {
        border-left: 4px solid var(--danger);
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
        st.metric("💰 总投入", f"¥{result.total_invested:,.0f}")
    with col2:
        st.metric("📈 最终价值", f"¥{result.final_value:,.0f}")
    with col3:
        delta_color = "normal" if result.return_rate >= 0 else "inverse"
        st.metric("📊 总收益率", f"{result.return_rate:+.2f}%", delta=f"{result.total_return:+,.0f}元", delta_color=delta_color)
    with col4:
        delta_color = "normal" if result.annual_return >= 0 else "inverse"
        st.metric("📅 年化收益", f"{result.annual_return:+.2f}%", delta_color=delta_color)
    
    col5, col6, col7, col8 = st.columns(4)
    with col5:
        delta_color = "inverse" if result.max_drawdown > 0 else "normal"
        st.metric("⬇️ 最大回撤", f"{result.max_drawdown:.2f}%", delta_color=delta_color)
    with col6:
        st.metric("🔄 定投次数", f"{result.investment_count} 次")
    with col7:
        st.metric("🛡️ 止损次数", f"{result.stop_loss_count} 次")
    with col8:
        st.metric("🎯 止盈次数", f"{result.take_profit_count} 次")


def render_report_metrics(report):
    """渲染报告指标卡片"""
    col1, col2, col3, col4 = st.columns(4)
    r = report.result
    
    with col1:
        st.metric("💰 总投入", f"¥{r['total_invested']:,.0f}")
    with col2:
        st.metric("📈 最终价值", f"¥{r['final_value']:,.0f}")
    with col3:
        delta_color = "normal" if r['return_rate'] >= 0 else "inverse"
        st.metric("📊 总收益率", f"{r['return_rate']:+.2f}%", delta=f"{r['total_return']:+,.0f}元", delta_color=delta_color)
    with col4:
        delta_color = "normal" if r['annual_return'] >= 0 else "inverse"
        st.metric("📅 年化收益", f"{r['annual_return']:+.2f}%", delta_color=delta_color)
    
    col5, col6, col7, col8 = st.columns(4)
    with col5:
        st.metric("⬇️ 最大回撤", f"{r['max_drawdown']:.2f}%")
    with col6:
        st.metric("🔄 定投次数", f"{r['investment_count']} 次")
    with col7:
        st.metric("🛡️ 止损次数", f"{r['stop_loss_count']} 次")
    with col8:
        st.metric("🎯 止盈次数", f"{r['take_profit_count']} 次")


def sidebar_params():
    """侧边栏参数"""
    st.sidebar.markdown(f"""
    <div style="text-align: center; padding: 1rem 0;">
        <h2 style="margin: 0; color: #1E3A5F;">{t("sidebar_title")}</h2>
    </div>
    """, unsafe_allow_html=True)
    
    with st.sidebar.expander(t("expander_date_range"), expanded=True):
        start_date = st.date_input(t("sidebar_start_date"), value=date(2022, 1, 1), key="sidebar_start")
        end_date = st.date_input(t("sidebar_end_date"), value=date(2024, 12, 31), key="sidebar_end")
    
    with st.sidebar.expander(t("expander_investment"), expanded=True):
        amount = st.number_input(t("sidebar_amount"), min_value=100, value=1000, step=100)
        
        frequency = st.selectbox(t("sidebar_frequency"), [t("freq_monthly"), t("freq_weekly"), t("freq_daily")], index=0)
        freq_map = {t("freq_monthly"): "monthly", t("freq_weekly"): "weekly", t("freq_daily"): "daily"}
        frequency = freq_map[frequency]
        
        day_of_month: int = 1
        day_of_week: int = 0
        if frequency == "monthly":
            day_of_month = st.selectbox(t("sidebar_monthly_day"), list(range(1, 29)), index=0)
        elif frequency == "weekly":
            day_of_week_str: str = st.selectbox(t("sidebar_weekly_day"), 
                [t("weekday_monday"), t("weekday_tuesday"), t("weekday_wednesday"), 
                 t("weekday_thursday"), t("weekday_friday")], index=0)
            day_of_week_map = {t("weekday_monday"): 0, t("weekday_tuesday"): 1, 
                               t("weekday_wednesday"): 2, t("weekday_thursday"): 3, 
                               t("weekday_friday"): 4}
            day_of_week = day_of_week_map[day_of_week_str]
    
    with st.sidebar.expander(t("expander_stop_loss"), expanded=False):
        enable_stop_loss = st.checkbox(t("sidebar_enable_stop_loss"), value=False)
        
        stop_loss_rate = 0.15
        stop_loss_sell_ratio = 1.0
        if enable_stop_loss:
            stop_loss_rate = st.slider(t("sidebar_stop_loss_rate"), min_value=5, max_value=30, value=15) / 100
            stop_loss_sell_ratio = st.slider(t("sidebar_stop_loss_ratio"), min_value=50, max_value=100, value=100) / 100
    
    with st.sidebar.expander(t("expander_take_profit"), expanded=False):
        enable_take_profit = st.checkbox(t("sidebar_enable_take_profit"), value=False)
        
        take_profit_rate = 0.20
        max_drawdown_threshold = 0.10
        take_profit_sell_ratio = 0.5
        if enable_take_profit:
            take_profit_rate = st.slider(t("sidebar_take_profit_rate"), min_value=5, max_value=50, value=20) / 100
            max_drawdown_threshold = st.slider(t("sidebar_max_drawdown_threshold"), min_value=5, max_value=30, value=10) / 100
            take_profit_sell_ratio = st.slider(t("sidebar_sell_ratio"), min_value=10, max_value=100, value=50) / 100
    
    with st.sidebar.expander(t("expander_dip_buy"), expanded=False):
        enable_dip_buy = st.checkbox(t("sidebar_enable_dip_buy"), value=False)
        dip_buy_tier1_threshold = -0.03
        dip_buy_tier1_amount = 1000.0
        dip_buy_tier2_threshold = -0.05
        dip_buy_tier2_amount = 1000.0
        dip_buy_tier3_threshold = -0.07
        dip_buy_tier3_amount = 1000.0
        
        if enable_dip_buy:
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"{t('dip_tier_label')}1: {t('dip_fall_label')}")
                st.write(f"{t('dip_tier_label')}2: {t('dip_fall_label')}")
                st.write(f"{t('dip_tier_label')}3: {t('dip_fall_label')}")
            with col2:
                tier1 = st.selectbox("t1", [t("dip_3pct"), t("dip_5pct"), t("dip_7pct")], index=0, key="dip1")
                tier2 = st.selectbox("t2", [t("dip_3pct"), t("dip_5pct"), t("dip_7pct")], index=1, key="dip2")
                tier3 = st.selectbox("t3", [t("dip_3pct"), t("dip_5pct"), t("dip_7pct")], index=2, key="dip3")
                tier_map = {t("dip_3pct"): -0.03, t("dip_5pct"): -0.05, t("dip_7pct"): -0.07}
                dip_buy_tier1_threshold = tier_map.get(tier1, -0.03)
                dip_buy_tier2_threshold = tier_map.get(tier2, -0.05)
                dip_buy_tier3_threshold = tier_map.get(tier3, -0.07)
            
            col3, col4 = st.columns(2)
            with col3:
                st.write(t("dip_amount_label"))
            with col4:
                dip_buy_tier1_amount = st.number_input("1", min_value=100, value=1000, step=100, key="dip_amt1")
                dip_buy_tier2_amount = st.number_input("2", min_value=100, value=1000, step=100, key="dip_amt2")
                dip_buy_tier3_amount = st.number_input("3", min_value=100, value=1000, step=100, key="dip_amt3")
    
    with st.sidebar.expander(t("expander_yield_boost"), expanded=False):
        enable_yield_boost = st.checkbox(t("sidebar_enable_yield_boost"), value=False)
        yield_boost_trigger = -0.20
        yield_boost_recover = -0.10
        yield_boost_amount = 1000.0
        
        if enable_yield_boost:
            yield_boost_trigger = st.slider(t("sidebar_trigger_threshold"), min_value=-30, max_value=-5, value=-20) / 100
            yield_boost_amount = st.number_input(t("sidebar_boost_amount"), min_value=100, value=1000, step=100)
            yield_boost_recover = st.slider(t("sidebar_recover_threshold"), min_value=-30, max_value=-5, value=-10) / 100
            
            if yield_boost_recover >= yield_boost_trigger:
                st.error(t("error_recovery_threshold"))
    
    with st.sidebar.expander(t("expander_data_source"), expanded=False):
        default_idx = AVAILABLE_SOURCES.index(DATA_SOURCE) if DATA_SOURCE in AVAILABLE_SOURCES else 0
        data_source = st.selectbox(t("sidebar_select_source"), AVAILABLE_SOURCES, index=default_idx)
    
    st.sidebar.markdown("---")
    with st.sidebar.container():
        render_language_selector()
    
    st.sidebar.markdown(f"""
    <div style="text-align: center; color: #64748B; font-size: 0.8rem; padding: 0.5rem;">
        📈 Stock DCA Backtesting {t("sidebar_version")}
    </div>
    """, unsafe_allow_html=True)
    
    return (start_date, end_date, amount, frequency, day_of_month, day_of_week, data_source,
            enable_stop_loss, stop_loss_rate, stop_loss_sell_ratio,
            enable_take_profit, take_profit_rate, max_drawdown_threshold, take_profit_sell_ratio,
            enable_dip_buy, dip_buy_tier1_threshold, dip_buy_tier1_amount,
            dip_buy_tier2_threshold, dip_buy_tier2_amount,
            dip_buy_tier3_threshold, dip_buy_tier3_amount,
            enable_yield_boost, yield_boost_trigger, yield_boost_recover, yield_boost_amount)


def plot_report_trades(report):
    """绘制报告的交易曲线"""
    try:
        if report.trades is None or len(report.trades) == 0:
            st.warning(t("empty_no_trades"))
            return None
        
        if isinstance(report.trades, pd.DataFrame):
            trades = report.trades.copy()
        else:
            trades = pd.DataFrame(report.trades)
        
        if 'date' not in trades.columns:
            st.warning(t("empty_trades_missing_date"))
            return None
        
        trades['date'] = pd.to_datetime(trades['date'], errors='coerce')
        trades = trades.dropna(subset=['date'])
        trades = trades.sort_values('date')
        trades['total_invested'] = [report.investment_amount * i for i in range(1, len(trades) + 1)]
    except Exception as e:
        st.error(f"Plot error: {str(e)}")
        return None
    
    fig, axes = plt.subplots(2, 1, figsize=(10, 8), dpi=100)
    
    ax1 = axes[0]
    ax1.plot(trades['date'], trades['total_invested'], label=t("label_total_invested"), color='blue', linewidth=2)
    ax1.plot(trades['date'], trades['portfolio_value'], label=t("label_portfolio_value"), color='green', linewidth=2)
    ax1.fill_between(trades['date'], trades['total_invested'], trades['portfolio_value'],
                    where=trades['portfolio_value'] >= trades['total_invested'],
                    alpha=0.3, color='green', label=t("label_profit"))
    ax1.fill_between(trades['date'], trades['total_invested'], trades['portfolio_value'],
                    where=trades['portfolio_value'] < trades['total_invested'],
                    alpha=0.3, color='red', label=t("label_loss"))
    ax1.set_title(t("chart_title_invest_profit").format(name=report.name), fontsize=12)
    ax1.set_xlabel(t("label_date"))
    ax1.set_ylabel(t("label_amount"))
    ax1.legend(loc='upper left')
    ax1.grid(True, alpha=0.3)
    
    ax2 = axes[1]
    ax2.plot(trades['date'], trades['return_rate'], color='purple', linewidth=2)
    ax2.axhline(y=0, color='black', linestyle='--', alpha=0.5)
    ax2.fill_between(trades['date'], 0, trades['return_rate'],
                     where=trades['return_rate'] >= 0, alpha=0.3, color='green')
    ax2.fill_between(trades['date'], 0, trades['return_rate'],
                     where=trades['return_rate'] < 0, alpha=0.3, color='red')
    ax2.set_title(t("chart_title_return_trend").format(name=report.name), fontsize=12)
    ax2.set_xlabel(t("label_date"))
    ax2.set_ylabel(t("label_return_rate"))
    ax2.grid(True, alpha=0.3)
    
    plt.tight_layout()
    return fig


def page_single_backtest(sd, ed, amt, freq, day_of_month, day_of_week, ds, esl, slr, slsr, etp, tpr, mdt, tpsr,
                        edb, dt1, da1, dt2, da2, dt3, da3, eyb, ybt, ybr, yba):
    """单股票回测页面"""
    st.markdown(f'<div class="section-header">{t("page_single_backtest")}</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns([1, 2.5])
    
    with col1:
        with st.container():
            st.markdown(f"""
            <div class="card">
                <h4>{t("stock_selection")}</h4>
            </div>
            """, unsafe_allow_html=True)
            
            fund_code = st.text_input(t("stock_code"), value="600036", help=t("stock_code_help"))
            fund_name = st.text_input(t("stock_name"), value="", help=t("stock_name_help"))
            
            if not fund_name:
                fund_name = get_fund_name(fund_code)
            
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, #EEF2FF 0%, #E0E7FF 100%); 
                        padding: 1rem; border-radius: 10px; margin: 1rem 0;">
                <strong>{t("current_selection")}:</strong> {fund_name} ({fund_code})
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown("")
            run_btn = st.button(t("btn_start_backtest"), type="primary", use_container_width=True)
    
    with col2:
        if run_btn:
            with st.spinner(t("spinner_fetching_data")):
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
            st.success(t("msg_backtest_complete").format(name=current_fund_name))
            
            st.markdown("")
            render_metrics(current_result)
            st.markdown("")
            
            col_save1, col_save2 = st.columns([1, 3])
            with col_save1:
                if st.button(t("btn_save_report"), key="save_report_btn", use_container_width=True):
                    rm = get_report_manager()
                    report_id = rm.save_report(current_result)
                    st.session_state['last_save_id'] = report_id
                    st.session_state['refresh_reports'] = True
                    st.rerun()
            
            if 'last_save_id' in st.session_state:
                st.success(t("msg_report_saved").format(id=st.session_state['last_save_id']))
            
            st.markdown("---")
            visualizer = BacktestVisualizer()
            fig = visualizer.plot_single_fund(current_result, current_fund_name)
            st.pyplot(fig)
            
            with st.expander(t("trades_title"), expanded=False):
                trades_display = current_result.trades.copy()
                trades_display['date'] = pd.to_datetime(trades_display['date']).astype(str).str[:10]
                
                display_cols = ['date', 'action', 'nav', 'shares', 'total_shares', 'portfolio_value', 'return_rate', 'reason']
                if 'invest_amount' in trades_display.columns:
                    display_cols.insert(5, 'invest_amount')
                
                trades_display = trades_display[display_cols].copy()
                trades_display.columns = [t("col_date"), t("col_action"), t("col_nav"), t("col_shares_change"), 
                                        t("col_total_shares"), t("col_invest_amount"), t("col_portfolio_value"), 
                                        t("col_return_rate"), t("col_reason")]
                trades_display[t("col_shares_change")] = trades_display[t("col_shares_change")].round(2)
                if t("col_invest_amount") in trades_display.columns:
                    trades_display[t("col_invest_amount")] = trades_display[t("col_invest_amount")].round(0).astype(int)
                trades_display[t("col_total_shares")] = trades_display[t("col_total_shares")].round(2)
                trades_display[t("col_portfolio_value")] = trades_display[t("col_portfolio_value")].round(0).astype(int)
                st.dataframe(trades_display, width='stretch', height=300, hide_index=True)
        elif run_btn:
            st.error(t("error_data_fetch_failed"))
            with st.expander(t("troubleshoot_title")):
                st.markdown(f"""
                **{t("troubleshoot_possible_causes")}**
                1. **{t("cause_wrong_code")}**
                2. **{t("cause_no_permission")}**
                3. **{t("cause_network_error")}**
                4. **{t("cause_data_not_synced")}**
                
                **{t("troubleshoot_suggestions")}**
                - {t("suggest_change_code")}
                - {t("suggest_change_source")}
                - {t("suggest_sync_data")}
                """)
        else:
            st.markdown(f"""
            <div class="empty-state">
                <h3>{t("empty_state_hint")}</h3>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown("---")
            st.markdown(f"### {t('quick_codes')}")
            
            quick_codes = [
                ("600036", t("quick_stock_600036")),
                ("601318", t("quick_stock_601318")),
                ("600519", t("quick_stock_600519")),
                ("000858", t("quick_stock_000858")),
                ("510300", t("quick_stock_510300")),
                ("510500", t("quick_stock_510500")),
            ]
            
            cols = st.columns(3)
            for i, (code, name) in enumerate(quick_codes):
                with cols[i % 3]:
                    st.code(f"{code} - {name}")


def page_compare(sd2, ed2, amt2, esl, slr, etp, tpr, mdt, tpsr, ds):
    """多股票对比页面"""
    st.markdown(f'<div class="section-header">{t("multi_compare_title")}</div>', unsafe_allow_html=True)
    
    col_left, col_right = st.columns([1, 2.5])
    
    with col_left:
        with st.container():
            st.markdown(f"""
            <div class="card">
                <h4>{t("input_settings")}</h4>
            </div>
            """, unsafe_allow_html=True)
            
            compare_funds = st.text_area(
                t("stock_codes_input"), 
                value="600036,601318,600519", 
                height=100,
                help=t("stock_codes_help")
            )
            
            col_start2, col_end2 = st.columns(2)
            with col_start2:
                start_date2 = st.date_input(t("sidebar_start_date"), value=date(2022, 1, 1), key="start2")
            with col_end2:
                end_date2 = st.date_input(t("sidebar_end_date"), value=date(2024, 12, 31), key="end2")
            
            amount2 = st.number_input(t("sidebar_amount"), min_value=100, value=1000, step=100, key="amt2")
            
            compare_btn = st.button(t("btn_start_compare"), type="primary", use_container_width=True)
    
    with col_right:
        if compare_btn:
            with st.spinner(t("spinner_fetching_data")):
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
                    st.success(t("msg_compare_complete").format(count=len(results)))
                    
                    comp_df = pd.DataFrame([
                        {
                            t("col_stock"): name,
                            t("col_total_invested"): f"¥{r.total_invested:,.0f}",
                            t("col_final_value"): f"¥{r.final_value:,.0f}",
                            t("col_total_return_pct"): f"{r.return_rate:+.2f}%",
                            t("col_annual_return_pct"): f"{r.annual_return:+.2f}%",
                            t("col_max_drawdown_pct"): f"{r.max_drawdown:.2f}%",
                            t("col_invest_count"): r.investment_count,
                            t("col_stop_loss_count"): r.stop_loss_count,
                            t("col_take_profit_count"): r.take_profit_count
                        }
                        for name, r in results.items()
                    ])
                    
                    st.dataframe(comp_df, width='stretch', hide_index=True)
                    
                    st.markdown("")
                    visualizer = BacktestVisualizer()
                    fig = visualizer.plot_comparison(results)
                    st.pyplot(fig)
                else:
                    st.error(t("error_data_fetch_failed"))
                    with st.expander(t("troubleshoot_title")):
                        st.markdown(f"""
                        **{t("troubleshoot_possible_causes")}**
                        1. **{t("cause_wrong_code")}**
                        2. **{t("cause_no_permission")}**
                        3. **{t("cause_network_error")}**
                        
                        **{t("troubleshoot_suggestions")}**
                        - {t("suggest_change_code")}
                        - {t("suggest_change_source")}
                        """)
        else:
            st.markdown(f"""
            <div class="empty-state">
                <h3>{t("empty_state_compare_hint")}</h3>
                <p>{t("recommend_compare")}</p>
            </div>
            """, unsafe_allow_html=True)


def page_reports():
    """报告管理页面"""
    if 'refresh_reports' not in st.session_state:
        st.session_state['refresh_reports'] = True
    
    rm = ReportManager()
    
    if st.session_state.get('refresh_reports', False):
        st.cache_data.clear()
        st.session_state['refresh_reports'] = False
    
    reports = rm.list_reports()
    
    tab1, tab2, tab3 = st.tabs([t("tab_report_list"), t("tab_report_detail"), t("tab_report_compare")])
    
    with tab1:
        st.markdown(f'<div class="section-header">{t("reports_title")}</div>', unsafe_allow_html=True)
        
        if not reports:
            st.markdown(f"""
            <div class="empty-state">
                <h3>{t("empty_no_reports_list")}</h3>
                <p>{t("no_reports")}</p>
            </div>
            """, unsafe_allow_html=True)
        else:
            col_search, col_filter = st.columns([2, 1])
            with col_search:
                search = st.text_input(t("search_report"), "", key="search_reports")
            with col_filter:
                fund_codes = list(set(r.fund_code for r in reports))
                filter_code = st.selectbox(t("filter_stock"), [t("all")] + fund_codes, key="filter_reports")
            
            filtered_reports = rm.list_reports(
                fund_code=filter_code if filter_code != t("all") else None,
                search=search if search else None
            )
            
            if filtered_reports:
                for report in filtered_reports:
                    with st.container():
                        st.markdown("""
                        <div class="card">
                        """, unsafe_allow_html=True)
                        
                        col_name, col_rate, col_actions = st.columns([4, 1, 1])
                        with col_name:
                            st.markdown(f"**{report.name}**")
                            st.caption(f"📌 {t('report_id_label')}: {report.id} | 🕐 {t('report_created_label')}: {report.created_at[:19]}")
                        with col_rate:
                            delta = "📈" if report.result['return_rate'] >= 0 else "📉"
                            delta_color = "normal" if report.result['return_rate'] >= 0 else "inverse"
                            st.metric(t("report_rate_label"), f"{report.result['return_rate']:+.2f}%", delta=delta, delta_color=delta_color)
                        with col_actions:
                            col_v, col_d = st.columns(2)
                            with col_v:
                                if st.button(t("btn_view_detail"), key=f"view_{report.id}", help="View"):
                                    st.session_state['selected_report_id'] = report.id
                                    st.rerun()
                            with col_d:
                                if st.button(t("btn_delete"), key=f"del_{report.id}", help="Delete"):
                                    rm.delete_report(report.id)
                                    st.rerun()
                        
                        st.markdown("</div>", unsafe_allow_html=True)
                        st.markdown("")
            else:
                st.info(t("no_reports"))
    
    with tab2:
        st.markdown(f'<div class="section-header">{t("report_detail_title")}</div>', unsafe_allow_html=True)
        
        reports = rm.list_reports()
        
        if not reports:
            st.markdown(f"""
            <div class="empty-state">
                <h3>{t("empty_no_reports_detail")}</h3>
            </div>
            """, unsafe_allow_html=True)
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
                t("select_report"),
                range(len(reports)),
                index=default_idx,
                format_func=lambda x: report_options[x],
                key="select_report_detail"
            )
            
            report_id = report_ids[selected_idx]
            report = rm.load_report(report_id)
            
            if report:
                st.markdown(f"### {report.name}")
                st.caption(f"🕐 {t('created_time')}: {report.created_at}")
                
                st.markdown("")
                render_report_metrics(report)
                
                st.markdown("")
                fig = plot_report_trades(report)
                if fig is not None:
                    st.pyplot(fig)
                
                col_del, col_exp, col_trades = st.columns([1, 1, 4])
                with col_del:
                    if st.button(t("btn_delete_report"), key="delete_from_detail", use_container_width=True):
                        rm.delete_report(report_id)
                        st.session_state['selected_report_id'] = None
                        st.rerun()
                
                with col_exp:
                    from backtest.report_exporter import ReportExporter
                    if st.button(t("btn_export_report"), key="export_report", use_container_width=True):
                        exporter = ReportExporter()
                        filepath = exporter.export_excel(report)
                        st.success(t("msg_report_exported").format(path=filepath))
                
                with st.expander(t("trades_title")):
                    trades_df = pd.DataFrame(report.trades)
                    trades_df['date'] = pd.to_datetime(trades_df['date']).dt.strftime('%Y-%m-%d')
                    
                    display_cols = ['date', 'action', 'nav', 'shares', 'total_shares', 'portfolio_value', 'return_rate', 'reason']
                    if 'invest_amount' in trades_df.columns:
                        display_cols.insert(5, 'invest_amount')
                    
                    trades_display = trades_df[display_cols].copy()
                    trades_display.columns = [t("col_date"), t("col_action"), t("col_nav"), t("col_shares_change"), 
                                            t("col_total_shares"), t("col_invest_amount"), t("col_portfolio_value"), 
                                            t("col_return_rate"), t("col_reason")]
                    trades_display[t("col_shares_change")] = trades_display[t("col_shares_change")].round(2)
                    if t("col_invest_amount") in trades_display.columns:
                        trades_display[t("col_invest_amount")] = trades_display[t("col_invest_amount")].round(0).astype(int)
                    trades_display[t("col_total_shares")] = trades_display[t("col_total_shares")].round(2)
                    trades_display[t("col_portfolio_value")] = trades_display[t("col_portfolio_value")].round(0).astype(int)
                    st.dataframe(trades_display, width='stretch', height=300, hide_index=True)
    
    with tab3:
        st.markdown(f'<div class="section-header">{t("report_compare_title")}</div>', unsafe_allow_html=True)
        
        if len(reports) < 2:
            st.markdown(f"""
            <div class="empty-state">
                <h3>{t("empty_no_reports_compare")}</h3>
                <p>{t("msg_need_more_reports")}</p>
            </div>
            """, unsafe_allow_html=True)
        else:
            selected_ids = st.multiselect(
                t("select_compare_reports"),
                options=[r.id for r in reports],
                default=[r.id for r in reports[:2]] if len(reports) >= 2 else [],
                format_func=lambda x: next((r.name for r in reports if r.id == x), "")
            )
            
            if len(selected_ids) >= 2:
                selected_reports = [rm.load_report(rid) for rid in selected_ids]
                valid_reports = [r for r in selected_reports if r is not None]
                
                comp_df = pd.DataFrame([
                    {
                        t("col_stock"): r.name,
                        t("col_stock"): r.fund_name,
                        t("col_date_range"): f"{r.start_date} ~ {r.end_date}",
                        t("col_total_invested"): f"¥{r.result['total_invested']:,.0f}",
                        t("col_final_value"): f"¥{r.result['final_value']:,.0f}",
                        t("col_total_return_pct"): f"{r.result['return_rate']:+.2f}%",
                        t("col_annual_return_pct"): f"{r.result['annual_return']:+.2f}%",
                        t("col_max_drawdown_pct"): f"{r.result['max_drawdown']:.2f}%",
                        t("col_invest_count"): r.result['investment_count'],
                        t("col_stop_loss_count"): r.result['stop_loss_count'],
                        t("col_take_profit_count"): r.result['take_profit_count']
                    }
                    for r in valid_reports
                ])
                
                st.dataframe(comp_df, width='stretch', hide_index=True)
                
                st.markdown("")
                
                fig, axes = plt.subplots(2, 2, figsize=(14, 10), dpi=100)
                
                names = [r.name for r in valid_reports]
                
                ax1 = axes[0, 0]
                x = range(len(names))
                invested = [r.result['total_invested'] for r in valid_reports]
                final = [r.result['final_value'] for r in valid_reports]
                width = 0.35
                ax1.bar([i - width/2 for i in x], invested, width, label=t("label_total_invested_en"), color='steelblue')
                ax1.bar([i + width/2 for i in x], final, width, label=t("label_final_value"), color='coral')
                ax1.set_xticks(x)
                ax1.set_xticklabels(names, rotation=15)
                ax1.set_ylabel('Amount (CNY)')
                ax1.set_title(t("chart_investment_value"))
                ax1.legend()
                ax1.grid(True, alpha=0.3)
                
                ax2 = axes[0, 1]
                returns = [r.result['return_rate'] for r in valid_reports]
                colors = ['green' if r >= 0 else 'red' for r in returns]
                ax2.bar(names, returns, color=colors)
                ax2.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
                ax2.set_ylabel('Return Rate (%)')
                ax2.set_title(t("chart_return_comparison"))
                ax2.grid(True, alpha=0.3)
                for i, v in enumerate(returns):
                    ax2.text(i, v + 1 if v >= 0 else v - 3, f'{v:.1f}%', ha='center', fontsize=9)
                
                ax3 = axes[1, 0]
                annual = [r.result['annual_return'] for r in valid_reports]
                colors = ['green' if r >= 0 else 'red' for r in annual]
                ax3.bar(names, annual, color=colors)
                ax3.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
                ax3.set_ylabel('Annual Return (%)')
                ax3.set_title(t("chart_annual_return"))
                ax3.grid(True, alpha=0.3)
                
                ax4 = axes[1, 1]
                drawdowns = [r.result['max_drawdown'] for r in valid_reports]
                ax4.barh(names, drawdowns, color='orange')
                ax4.set_xlabel('Max Drawdown (%)')
                ax4.set_title(t("chart_max_drawdown"))
                
                plt.tight_layout()
                st.pyplot(fig)
                
                st.markdown("")
                from backtest.report_exporter import MultiReportExporter
                if st.button(t("btn_export_compare"), use_container_width=True):
                    exporter = MultiReportExporter()
                    filepath = exporter.export_comparison_excel(valid_reports)
                    st.success(t("msg_compare_exported").format(path=filepath))
            else:
                st.info(t("msg_select_at_least_two"))


def main():
    st.markdown("""
    <div class="main-header">
        📈 """ + t("app_title") + """
    </div>
    """, unsafe_allow_html=True)
    
    if 'task_running' not in st.session_state:
        st.session_state['task_running'] = False
    if 'current_task_id' not in st.session_state:
        st.session_state['current_task_id'] = None

    params = sidebar_params()
    (start_date, end_date, amount, frequency, day_of_month, day_of_week, data_source,
     enable_stop_loss, stop_loss_rate, stop_loss_sell_ratio,
     enable_take_profit, take_profit_rate, max_drawdown_threshold, take_profit_sell_ratio,
     enable_dip_buy, dip_buy_tier1_threshold, dip_buy_tier1_amount,
     dip_buy_tier2_threshold, dip_buy_tier2_amount,
     dip_buy_tier3_threshold, dip_buy_tier3_amount,
     enable_yield_boost, yield_boost_trigger, yield_boost_recover, yield_boost_amount) = params
    
    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
        t("tab_single_backtest"),
        t("tab_multi_comparison"),
        t("tab_watchlist"),
        t("tab_strategy"),
        t("tab_auto_backtest"),
        t("tab_reports"),
        "📡 数据源"
    ])
    
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
        render_watchlist_manager()
    
    with tab4:
        render_strategy_manager()
    
    with tab5:
        render_task_manager()
    
    with tab6:
        page_reports()
    
    with tab7:
        render_diagnostic_page()


if __name__ == "__main__":
    main()
