# -*- coding: utf-8 -*-
"""
股票定投回测 Web 应用 (Streamlit)
"""

import streamlit as st
import pandas as pd
from datetime import date
import logging
import threading

from backtest import FundBacktester, BacktestConfig
from backtest.dca_backtest import BacktestResult
from backtest.plotly_visualization import PlotlyVisualizer
from data_source.config import DATA_SOURCE, AVAILABLE_SOURCES
from backtest.report_manager import ReportManager
from backtest.page_watchlist import render_watchlist_manager
from backtest.page_strategy import render_strategy_manager
from backtest.page_task import render_task_manager
from backtest.page_diagnostic import render_diagnostic_page
from i18n import t, render_language_selector, get_locale
from data_source.logger import setup_logger
from data_source.sync.scheduler import get_scheduler
from data_source.sync.auto_sync import (
    sync_on_startup,
    sync_watchlist_task,
    sync_incremental_task,
)
from datetime import time as dt_time

logger = setup_logger('app')

_scheduler_initialized = False


def render_sync_status():
    """渲染数据同步状态区块"""
    global _scheduler_initialized

    if 'scheduler' not in st.session_state:
        st.session_state['scheduler'] = get_scheduler()

    scheduler = st.session_state['scheduler']

    if not _scheduler_initialized:
        scheduler.add_daily_task(
            "daily_morning_sync",
            dt_time(8, 30),
            sync_incremental_task
        )
        scheduler.add_daily_task(
            "daily_afternoon_sync",
            dt_time(16, 0),
            sync_incremental_task
        )
        scheduler.add_interval_task(
            "watchlist_interval_sync",
            30,
            sync_watchlist_task
        )
        scheduler.start()

        # 后台线程执行启动同步，不阻塞 UI
        def background_sync():
            try:
                sync_on_startup()
            except Exception as e:
                logger.error(f"启动同步失败: {e}")

        sync_thread = threading.Thread(target=background_sync, daemon=True)
        sync_thread.start()

        _scheduler_initialized = True

    status = scheduler.get_status()

    col1, col2 = st.columns([1, 1])
    with col1:
        if status['running']:
            st.success("🟢 运行中")
        else:
            st.error("🔴 已停止")
    with col2:
        if st.button("🔄 立即同步", key="sync_now", help="立即触发增量同步"):
            with st.spinner("正在同步..."):
                result = sync_incremental_task()
                if result:
                    st.success(f"✅ 同步完成: {result}")
                else:
                    st.error("❌ 同步失败")

    st.markdown("---")
    st.markdown("**📅 定时任务**")

    for task in status['tasks']:
        task_type = task['type']
        task_id = task['id']
        next_run = task.get('next_run')
        last_run = task.get('last_run')

        if task_type == 'daily':
            task_name = "早盘同步 (8:30)" if "morning" in task_id else "收盘同步 (16:00)"
        else:
            task_name = "自选股同步 (30分钟)"

        col1, col2, col3 = st.columns([2, 2, 1])
        with col1:
            st.write(f"• {task_name}")
        with col2:
            if last_run:
                from datetime import datetime as dt
                last_dt = dt.fromisoformat(last_run)
                st.caption(f"上次: {last_dt.strftime('%H:%M:%S')}")
            else:
                st.caption("未执行过")
        with col3:
            if st.button("▶️", key=f"run_{task_id}", help=f"立即执行 {task_name}"):
                with st.spinner(f"正在执行 {task_name}..."):
                    scheduler.run_task_now(task_id)
                    st.rerun()

    with st.expander("📊 调度详情"):
        st.json(status)


def clear_all_data():
    """清空所有数据：MySQL 和 Redis"""
    st.warning("⚠️ 即将清空所有数据！这将删除 MySQL 数据库表中的数据和 Redis 缓存。")
    
    confirm = st.text_input("输入 'CLEAR' 确认清空:", key="clear_confirm")
    
    if confirm == "CLEAR":
        try:
            from data_source.cache import get_cache
            cache = get_cache()
            if cache.is_available():
                cache.clear_pattern("*")
                st.success("✅ Redis 缓存已清空")
                logger.info("Redis cache cleared")
            
            from data_source.db.connection import get_db_session, get_engine
            from sqlalchemy import text
            
            engine = get_engine()
            tables_to_clear = [
'daily_kline_tushare',
                'reports',
                'watchlists',
                'watchlist_stocks',
                'strategy_templates',
                'stocks',
                'sync_logs'
            ]
            
            with engine.connect() as conn:
                for table in tables_to_clear:
                    try:
                        conn.execute(text(f"TRUNCATE TABLE {table}"))
                        st.success(f"✅ {table} 表已清空")
                        logger.info(f"Table {table} truncated")
                    except Exception as e:
                        st.error(f"❌ 清空 {table} 失败: {e}")
                        logger.error(f"Failed to truncate {table}: {e}")
                conn.commit()
            
            st.cache_data.clear()
            st.success("🎉 所有数据已清空！请刷新页面或重新启动应用。")
            return True
            
        except Exception as e:
            st.error(f"清空数据失败: {e}")
            logger.error(f"Clear all data failed: {e}")
            return False
    else:
        if confirm:
            st.info("请输入 'CLEAR' 进行确认")
        return False


st.set_page_config(
    page_title=t("page_title"),
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

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
    if code in NAME_MAP:
        return NAME_MAP[code]
    try:
        from data_source.db.connection import get_db_session
        from data_source.db.models import Stock
        with get_db_session() as session:
            stock = session.query(Stock).filter(Stock.code == code).first()
            if stock is not None:
                name = stock.name
                if name is not None and str(name).strip():
                    return str(name).strip()
    except Exception:
        pass
    return code


def get_report_manager():
    return ReportManager()


def render_metrics(result):
    """渲染指标卡片"""
    # 调试日志
    logger.info("=" * 60)
    logger.info("render_metrics - 接收到的 result:")
    logger.info(f"  result 类型: {type(result)}")
    logger.info(f"  total_invested: {result.total_invested}")
    logger.info(f"  final_value: {result.final_value}")
    logger.info(f"  return_rate: {result.return_rate}")
    logger.info(f"  annual_return: {result.annual_return}")
    logger.info("=" * 60)
    
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
    
    with st.sidebar.expander(t("expander_data_source"), expanded=False):
        default_idx = AVAILABLE_SOURCES.index(DATA_SOURCE) if DATA_SOURCE in AVAILABLE_SOURCES else 0
        data_source = st.selectbox(t("sidebar_select_source"), AVAILABLE_SOURCES, index=default_idx)
    
    with st.sidebar.expander("🗑️ 系统工具", expanded=False):
        if st.button("清空所有数据", help="清空 MySQL 和 Redis 中的所有数据（谨慎操作）"):
            clear_all_data()

    st.sidebar.markdown("---")

    with st.sidebar.expander("📡 数据同步状态", expanded=True):
        render_sync_status()

    with st.sidebar.container():
        render_language_selector()
    
    st.sidebar.markdown(f"""
    <div style="text-align: center; color: #64748B; font-size: 0.8rem; padding: 0.5rem;">
        📈 Stock DCA Backtesting {t("sidebar_version")}
    </div>
    """, unsafe_allow_html=True)
    
    return (start_date, end_date, amount, frequency, day_of_month, day_of_week, data_source)


def plot_report_trades_plotly(report):
    """使用 Plotly 绘制报告的交易曲线"""
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    
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
    
    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=(t("chart_title_invest_profit").format(name=report.name), 
                       t("chart_title_return_trend").format(name=report.name)),
        vertical_spacing=0.15,
        row_heights=[0.5, 0.5]
    )
    
    fig.add_trace(
        go.Scatter(
            x=trades['date'],
            y=trades['total_invested'],
            name=t("label_total_invested"),
            line=dict(color='blue', width=2),
            hovertemplate='%{x|%Y-%m-%d}<br>' + t("label_total_invested") + ': ¥%{y:,.0f}<extra></extra>'
        ),
        row=1, col=1
    )
    
    fig.add_trace(
        go.Scatter(
            x=trades['date'],
            y=trades['portfolio_value'],
            name=t("label_portfolio_value"),
            line=dict(color='green', width=2),
            fill='tonexty',
            fillcolor='rgba(0, 200, 0, 0.1)',
            hovertemplate='%{x|%Y-%m-%d}<br>' + t("label_portfolio_value") + ': ¥%{y:,.0f}<extra></extra>'
        ),
        row=1, col=1
    )
    
    fig.add_trace(
        go.Scatter(
            x=trades['date'],
            y=trades['return_rate'],
            name=t("label_return_rate"),
            line=dict(color='purple', width=2),
            fill='tozeroy',
            fillcolor='rgba(128, 0, 128, 0.2)',
            hovertemplate='%{x|%Y-%m-%d}<br>' + t("label_return_rate") + ': %{y:.2f}%<extra></extra>'
        ),
        row=2, col=1
    )
    
    fig.update_layout(
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hovermode='x unified',
        height=600,
        template='plotly_white'
    )
    
    fig.update_yaxes(title_text=t("label_amount"), gridcolor='#f0f0f0', row=1, col=1)
    fig.update_yaxes(title_text=t("label_return_rate"), gridcolor='#f0f0f0', row=2, col=1)
    fig.update_xaxes(title_text=t("label_date"), tickformat='%Y-%m', dtick='M3', row=2, col=1)
    
    return fig


def render_strategy_section(sm, key_prefix: str = "strategy"):
    """渲染策略选择器组件"""
    strategy_options = {s.id: s.name for s in sm.list_strategies()}
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        if strategy_options:
            selected_strategy_id = st.selectbox(
                "选择策略",
                options=list(strategy_options.keys()),
                format_func=lambda x: strategy_options.get(x) or x,
                key=f"{key_prefix}_selector"
            )
        else:
            st.info("暂无策略，请创建新策略")
            selected_strategy_id = None
    
    with col2:
        st.write("")
        if st.button("+ 新建策略", key=f"{key_prefix}_new_btn", use_container_width=True):
            st.session_state[f'{key_prefix}_show_editor'] = True
    
    params = None
    strategy_name = None
    
    if selected_strategy_id and selected_strategy_id in strategy_options:
        strategy = sm.get_strategy(selected_strategy_id)
        if strategy:
            params = strategy.params
            strategy_name = strategy.name
    
    if st.session_state.get(f'{key_prefix}_show_editor', False):
        with st.expander("✏️ 新建策略", expanded=True):
            from backtest.page_strategy import render_strategy_editor
            new_strategy = render_strategy_editor(sm, None, is_new=True)
            
            col_done, col_cancel = st.columns(2)
            with col_done:
                if st.button("完成创建", key=f"{key_prefix}_done_new", use_container_width=True):
                    st.session_state[f'{key_prefix}_show_editor'] = False
                    st.rerun()
            with col_cancel:
                if st.button("取消", key=f"{key_prefix}_cancel_new", use_container_width=True):
                    st.session_state[f'{key_prefix}_show_editor'] = False
                    st.rerun()
    
    show_details = st.checkbox("显示/编辑参数", value=False, key=f"{key_prefix}_show_details")
    
    if show_details:
        with st.expander("策略参数详情", expanded=True):
            if params is None:
                params = render_strategy_params_form(key_prefix)
            else:
                st.info(f"当前策略: {strategy_name}")
                render_params_display(params)
    
    if params is None:
        params = render_strategy_params_form(key_prefix)
    
    col_save, col_space = st.columns([1, 3])
    with col_save:
        if st.button("💾 保存为策略", key=f"{key_prefix}_save_btn", use_container_width=True):
            st.session_state[f'{key_prefix}_show_save_dialog'] = True
    
    if st.session_state.get(f'{key_prefix}_show_save_dialog', False):
        with st.form(f"{key_prefix}_save_form"):
            st.markdown("### 保存策略")
            new_name = st.text_input("策略名称", key=f"{key_prefix}_save_name")
            new_group = st.selectbox("策略分组", ["我的策略", "保守型", "激进型", "增强型"], key=f"{key_prefix}_save_group")
            new_desc = st.text_area("策略描述", key=f"{key_prefix}_save_desc")
            
            col_submit, col_cancel = st.columns(2)
            with col_submit:
                submitted = st.form_submit_button("保存", key=f"{key_prefix}_save_submit", use_container_width=True)
            with col_cancel:
                if st.form_submit_button("取消", key=f"{key_prefix}_save_cancel", use_container_width=True):
                    st.session_state[f'{key_prefix}_show_save_dialog'] = False
                    st.rerun()
            
            if submitted and new_name:
                new_strategy = sm.create_strategy(
                    name=new_name,
                    group=new_group,
                    description=new_desc,
                    params=params
                )
                st.success(f"策略 '{new_name}' 已保存!")
                st.session_state[f'{key_prefix}_show_save_dialog'] = False
                if selected_strategy_id:
                    st.session_state[f'{key_prefix}_selector'] = new_strategy.id
                st.rerun()
    
    return params, strategy_name


def render_params_display(params):
    """以可读格式显示策略参数"""
    p = params
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**止损设置**")
        st.write(f"启用: {'是' if p.enable_stop_loss else '否'}")
        if p.enable_stop_loss:
            st.write(f"阈值: {int(p.stop_loss_rate * 100)}%")
            st.write(f"卖出比例: {int(p.stop_loss_sell_ratio * 100)}%")
        
        st.markdown("**止盈设置**")
        st.write(f"启用: {'是' if p.enable_take_profit else '否'}")
        if p.enable_take_profit:
            st.write(f"阈值: {int(p.take_profit_rate * 100)}%")
            st.write(f"回撤阈值: {int(p.max_drawdown_threshold * 100)}%")
            st.write(f"卖出比例: {int(p.take_profit_sell_ratio * 100)}%")
        
        st.markdown("**补仓设置**")
        st.write(f"启用: {'是' if p.enable_dip_buy else '否'}")
    
    with col2:
        if p.enable_dip_buy:
            st.write(f"一档: {int(p.dip_buy_tier1_threshold * 100)}% 跌幅，+¥{p.dip_buy_tier1_amount:.0f}")
            st.write(f"二档: {int(p.dip_buy_tier2_threshold * 100)}% 跌幅，+¥{p.dip_buy_tier2_amount:.0f}")
            st.write(f"三档: {int(p.dip_buy_tier3_threshold * 100)}% 跌幅，+¥{p.dip_buy_tier3_amount:.0f}")
        
        st.markdown("**收益增强设置**")
        st.write(f"启用: {'是' if p.enable_yield_boost else '否'}")
        if p.enable_yield_boost:
            st.write(f"触发阈值: {int(p.yield_boost_trigger * 100)}%")
            st.write(f"恢复阈值: {int(p.yield_boost_recover * 100)}%")
            st.write(f"增强金额: ¥{p.yield_boost_amount:.0f}")


def render_strategy_params_form(key_prefix: str = "strategy"):
    """渲染策略参数表单，返回 StrategyParams"""
    from backtest.strategy_manager import StrategyParams
    
    with st.expander("策略参数设置", expanded=True):
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**止损设置**")
            enable_stop_loss = st.checkbox("启用止损", value=False, key=f"{key_prefix}_esl")
            stop_loss_rate = 0.20
            stop_loss_sell_ratio = 1.0
            if enable_stop_loss:
                stop_loss_rate = st.slider("止损阈值", 5, 50, 20, key=f"{key_prefix}_slr") / 100
                stop_loss_sell_ratio = st.slider("止损卖出比例", 50, 100, 100, key=f"{key_prefix}_slsr") / 100
            
            st.markdown("**止盈设置**")
            enable_take_profit = st.checkbox("启用止盈", value=False, key=f"{key_prefix}_etp")
            take_profit_rate = 0.30
            max_drawdown_threshold = 0.15
            take_profit_sell_ratio = 0.5
            if enable_take_profit:
                take_profit_rate = st.slider("止盈阈值", 5, 50, 30, key=f"{key_prefix}_tpr") / 100
                max_drawdown_threshold = st.slider("最大回撤阈值", 5, 30, 15, key=f"{key_prefix}_mdt") / 100
                take_profit_sell_ratio = st.slider("止盈卖出比例", 10, 100, 50, key=f"{key_prefix}_tpsr") / 100
        
        with col2:
            st.markdown("**补仓设置**")
            enable_dip_buy = st.checkbox("启用补仓", value=False, key=f"{key_prefix}_edb")
            dip_buy_tier1_threshold = -0.03
            dip_buy_tier1_amount = 1000.0
            dip_buy_tier2_threshold = -0.05
            dip_buy_tier2_amount = 1000.0
            dip_buy_tier3_threshold = -0.07
            dip_buy_tier3_amount = 1000.0
            
            if enable_dip_buy:
                tier1_opt = st.selectbox("一档跌幅", [-3, -5, -7], index=0, key=f"{key_prefix}_dt1",
                                        format_func=lambda x: f"{x}%")
                tier2_opt = st.selectbox("二档跌幅", [-3, -5, -7], index=1, key=f"{key_prefix}_dt2",
                                        format_func=lambda x: f"{x}%")
                tier3_opt = st.selectbox("三档跌幅", [-3, -5, -7], index=2, key=f"{key_prefix}_dt3",
                                        format_func=lambda x: f"{x}%")
                dip_buy_tier1_threshold = tier1_opt / 100
                dip_buy_tier2_threshold = tier2_opt / 100
                dip_buy_tier3_threshold = tier3_opt / 100
                
                dip_buy_tier1_amount = st.number_input("一档补仓金额", 100, 10000, 1000, 100, key=f"{key_prefix}_da1")
                dip_buy_tier2_amount = st.number_input("二档补仓金额", 100, 10000, 1000, 100, key=f"{key_prefix}_da2")
                dip_buy_tier3_amount = st.number_input("三档补仓金额", 100, 10000, 1000, 100, key=f"{key_prefix}_da3")
            
            st.markdown("**收益增强设置**")
            enable_yield_boost = st.checkbox("启用收益增强", value=False, key=f"{key_prefix}_eyb")
            yield_boost_trigger = -0.20
            yield_boost_recover = -0.10
            yield_boost_amount = 1000.0
            
            if enable_yield_boost:
                yield_boost_trigger = st.slider("触发阈值", -30, -5, -20, key=f"{key_prefix}_ybt") / 100
                yield_boost_amount = st.number_input("增强金额", 100, 10000, 1000, 100, key=f"{key_prefix}_yba")
                yield_boost_recover = st.slider("恢复阈值", -30, -5, -10, key=f"{key_prefix}_ybr") / 100
                
                if yield_boost_recover >= yield_boost_trigger:
                    st.error("恢复阈值必须小于触发阈值")
    
    return StrategyParams(
        frequency="monthly",
        day_of_month=1,
        day_of_week=0,
        investment_amount=1000.0,
        enable_stop_loss=enable_stop_loss,
        stop_loss_rate=stop_loss_rate,
        stop_loss_sell_ratio=stop_loss_sell_ratio,
        enable_take_profit=enable_take_profit,
        take_profit_rate=take_profit_rate,
        max_drawdown_threshold=max_drawdown_threshold,
        take_profit_sell_ratio=take_profit_sell_ratio,
        enable_dip_buy=enable_dip_buy,
        dip_buy_tier1_threshold=dip_buy_tier1_threshold,
        dip_buy_tier1_amount=dip_buy_tier1_amount,
        dip_buy_tier2_threshold=dip_buy_tier2_threshold,
        dip_buy_tier2_amount=dip_buy_tier2_amount,
        dip_buy_tier3_threshold=dip_buy_tier3_threshold,
        dip_buy_tier3_amount=dip_buy_tier3_amount,
        enable_yield_boost=enable_yield_boost,
        yield_boost_trigger=yield_boost_trigger,
        yield_boost_recover=yield_boost_recover,
        yield_boost_amount=yield_boost_amount
    )


def page_single_backtest_tab1(sd, ed, amt, freq, day_of_month, day_of_week, ds):
    """单股票回测 Tab 1: 单策略回测"""
    from backtest.strategy_manager import StrategyManager

    sm = StrategyManager()

    current_start = str(sd)
    current_end = str(ed)

    last_start = st.session_state.get('last_start_date', '')
    last_end = st.session_state.get('last_end_date', '')

    if last_start != current_start or last_end != current_end:
        if 'current_result' in st.session_state:
            del st.session_state['current_result']

    col1, col2 = st.columns([1, 2.5])

    with col1:
        st.markdown("""
        <div class="card">
            <h4>股票选择</h4>
        </div>
        """, unsafe_allow_html=True)

        fund_code = st.text_input("股票代码", value="600036", key="single_fund_code")
        fund_name_input = st.text_input("股票名称", value="", key="single_fund_name", help="留空自动获取")

        if not fund_name_input:
            fund_name_input = get_fund_name(fund_code)
        
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, #EEF2FF 0%, #E0E7FF 100%); 
                    padding: 1rem; border-radius: 10px; margin: 1rem 0;">
            <strong>当前选择:</strong> {fund_name_input} ({fund_code})
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("---")
        st.markdown("### 策略设置")
        
        params, strategy_name = render_strategy_section(sm, key_prefix="single")
        
        st.markdown("")
        run_btn = st.button("🚀 开始回测", type="primary", use_container_width=True)
    
    with col2:
        if run_btn:
            with st.spinner("正在获取数据..."):
                tester = FundBacktester(data_source=ds)
                
                config = BacktestConfig(
                    fund_code=fund_code,
                    fund_name=fund_name_input,
                    start_date=str(sd),
                    end_date=str(ed),
                    investment_amount=amt,
                    frequency=freq,
                    day_of_month=day_of_month,
                    day_of_week=day_of_week,
                    data_source=ds,
                    enable_stop_loss=params.enable_stop_loss,
                    stop_loss_rate=params.stop_loss_rate,
                    stop_loss_sell_ratio=params.stop_loss_sell_ratio,
                    enable_take_profit=params.enable_take_profit,
                    take_profit_rate=params.take_profit_rate,
                    max_drawdown_threshold=params.max_drawdown_threshold,
                    take_profit_sell_ratio=params.take_profit_sell_ratio,
                    enable_dip_buy=params.enable_dip_buy,
                    dip_buy_tier1_threshold=params.dip_buy_tier1_threshold,
                    dip_buy_tier1_amount=params.dip_buy_tier1_amount,
                    dip_buy_tier2_threshold=params.dip_buy_tier2_threshold,
                    dip_buy_tier2_amount=params.dip_buy_tier2_amount,
                    dip_buy_tier3_threshold=params.dip_buy_tier3_threshold,
                    dip_buy_tier3_amount=params.dip_buy_tier3_amount,
                    enable_yield_boost=params.enable_yield_boost,
                    yield_boost_trigger=params.yield_boost_trigger,
                    yield_boost_recover=params.yield_boost_recover,
                    yield_boost_amount=params.yield_boost_amount
                )
                
                result = tester.single_fund(config)
                
                # 调试日志
                logger.info("=" * 60)
                logger.info("app.py - 回测结果:")
                logger.info(f"  result 类型: {type(result)}")
                if result:
                    logger.info(f"  total_invested: {result.total_invested}")
                    logger.info(f"  final_value: {result.final_value}")
                    logger.info(f"  investment_count: {result.investment_count}")
                logger.info("=" * 60)
                
                if result:
                    result.strategy_params = {
                        'fund_code': fund_code,
                        'fund_name': fund_name_input,
                        'start_date': str(sd),
                        'end_date': str(ed),
                        'strategy_name': strategy_name or "自定义",
                        **params.to_dict()
                    }
                    st.session_state['current_result'] = result
                    st.session_state['current_fund_name'] = fund_name_input
                    st.session_state['current_strategy_name'] = strategy_name
                    logger.info(f"已保存到 session_state, final_value={result.final_value}")
        
        current_result = st.session_state.get('current_result')
        current_fund_name = st.session_state.get('current_fund_name', fund_code)
        current_strategy_name = st.session_state.get('current_strategy_name', '自定义')
        
        # 调试日志
        logger.info("=" * 60)
        logger.info("app.py - 从 session_state 读取:")
        logger.info(f"  current_result: {current_result}")
        if current_result:
            logger.info(f"  current_result 类型: {type(current_result)}")
            logger.info(f"  current_result.final_value: {current_result.final_value}")
            logger.info(f"  current_result.total_invested: {current_result.total_invested}")
        logger.info("=" * 60)
        
        if current_result:
            st.success(f"✅ 回测完成 - {current_fund_name} (策略: {current_strategy_name})")
            
            st.markdown("")
            render_metrics(current_result)
            st.markdown("")
            
            col_save1, col_save2 = st.columns([1, 3])
            with col_save1:
                if st.button("💾 保存报告", key="save_single_report", use_container_width=True):
                    rm = get_report_manager()
                    report_id = rm.save_report(current_result)
                    st.session_state['last_save_id'] = report_id
                    st.session_state['refresh_reports'] = True
                    st.rerun()
            
            if 'last_save_id' in st.session_state:
                st.success(f"报告已保存，ID: {st.session_state['last_save_id']}")
            
            st.markdown("---")
            visualizer = PlotlyVisualizer()
            fig = visualizer.plot_single_fund(current_result, f"{current_fund_name} - {current_strategy_name}")
            st.plotly_chart(fig, use_container_width=True)
            
            with st.expander("交易明细", expanded=False):
                trades_display = current_result.trades.copy()
                trades_display['date'] = pd.to_datetime(trades_display['date']).astype(str).str[:10]
                
                display_cols = ['date', 'action', 'nav', 'shares', 'total_shares', 'portfolio_value', 'return_rate', 'reason']
                if 'invest_amount' in trades_display.columns:
                    display_cols.insert(5, 'invest_amount')
                
                trades_display = trades_display[[c for c in display_cols if c in trades_display.columns]].copy()
                trades_display.columns = [t("col_date"), t("col_action"), t("col_nav"), t("col_shares_change"), 
                                        t("col_total_shares"), t("col_invest_amount"), t("col_portfolio_value"), 
                                        t("col_return_rate"), t("col_reason")][:len(trades_display.columns)]
                st.dataframe(trades_display, width='stretch', height=300, hide_index=True)
        elif run_btn:
            st.error("数据获取失败，请检查股票代码或数据源")


def page_single_backtest_tab2(sd, ed, amt, freq, day_of_month, day_of_week, ds):
    """单股票回测 Tab 2: 策略对比"""
    from backtest.strategy_manager import StrategyManager
    
    sm = StrategyManager()
    strategies = sm.list_strategies()
    
    col1, col2 = st.columns([1, 2.5])
    
    with col1:
        st.markdown("""
        <div class="card">
            <h4>策略对比</h4>
            <p>对比多个策略在同一股票上的表现</p>
        </div>
        """, unsafe_allow_html=True)
        
        fund_code = st.text_input("股票代码", value="600036", key="compare_fund_code")
        fund_name_input = st.text_input("股票名称", value="", key="compare_fund_name")
        
        if not fund_name_input:
            fund_name_input = get_fund_name(fund_code)
        
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, #EEF2FF 0%, #E0E7FF 100%); 
                    padding: 1rem; border-radius: 10px; margin: 1rem 0;">
            <strong>股票:</strong> {fund_name_input} ({fund_code})
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("---")
        st.markdown("### 选择要对比的策略")
        
        if strategies:
            strategy_names = [s.name for s in strategies]
            selected_indices = st.multiselect(
                "选择策略（可多选）",
                options=range(len(strategies)),
                default=[0] if len(strategies) > 0 else [],
                format_func=lambda x: strategy_names[x]
            )
            selected_strategies = [strategies[i] for i in selected_indices]
        else:
            st.warning("暂无策略，请先创建策略")
            selected_strategies = []
        
        st.markdown("")
        run_btn = st.button("🚀 开始对比", type="primary", use_container_width=True)
    
    with col2:
        if run_btn and selected_strategies:
            results = {}
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            for i, strategy in enumerate(selected_strategies):
                status_text.text(f"正在回测: {strategy.name}...")
                
                tester = FundBacktester(data_source=ds)
                params = strategy.params
                
                config = BacktestConfig(
                    fund_code=fund_code,
                    fund_name=fund_name_input,
                    start_date=str(sd),
                    end_date=str(ed),
                    investment_amount=amt,
                    frequency=freq,
                    day_of_month=day_of_month,
                    day_of_week=day_of_week,
                    data_source=ds,
                    enable_stop_loss=params.enable_stop_loss,
                    stop_loss_rate=params.stop_loss_rate,
                    stop_loss_sell_ratio=params.stop_loss_sell_ratio,
                    enable_take_profit=params.enable_take_profit,
                    take_profit_rate=params.take_profit_rate,
                    max_drawdown_threshold=params.max_drawdown_threshold,
                    take_profit_sell_ratio=params.take_profit_sell_ratio,
                    enable_dip_buy=params.enable_dip_buy,
                    dip_buy_tier1_threshold=params.dip_buy_tier1_threshold,
                    dip_buy_tier1_amount=params.dip_buy_tier1_amount,
                    dip_buy_tier2_threshold=params.dip_buy_tier2_threshold,
                    dip_buy_tier2_amount=params.dip_buy_tier2_amount,
                    dip_buy_tier3_threshold=params.dip_buy_tier3_threshold,
                    dip_buy_tier3_amount=params.dip_buy_tier3_amount,
                    enable_yield_boost=params.enable_yield_boost,
                    yield_boost_trigger=params.yield_boost_trigger,
                    yield_boost_recover=params.yield_boost_recover,
                    yield_boost_amount=params.yield_boost_amount
                )
                
                result = tester.single_fund(config)
                if result:
                    results[strategy.name] = result
                
                progress_bar.progress((i + 1) / len(selected_strategies))
            
            status_text.text("对比完成!")
            
            if results:
                st.success(f"✅ 策略对比完成 - {fund_name_input}")
                
                st.markdown("---")
                st.markdown("### 对比结果")
                
                comparison_data = []
                for name, result in results.items():
                    comparison_data.append({
                        "策略": name,
                        "总投入": f"¥{result.total_invested:,.0f}",
                        "最终价值": f"¥{result.final_value:,.0f}",
                        "总收益率": f"{result.return_rate:+.2f}%",
                        "年化收益": f"{result.annual_return:+.2f}%",
                        "最大回撤": f"{result.max_drawdown:.2f}%",
                        "交易次数": result.investment_count,
                        "止损次数": result.stop_loss_count,
                        "止盈次数": result.take_profit_count
                    })
                
                st.dataframe(pd.DataFrame(comparison_data), width='stretch', hide_index=True)
                
                st.markdown("")
                visualizer = PlotlyVisualizer()
                fig = visualizer.plot_comparison(results)
                st.plotly_chart(fig, use_container_width=True)
                
                st.markdown("")
                col_save_all = st.columns([1])
                with col_save_all[0]:
                    if st.button("💾 保存所有报告", key="save_all_comparison", use_container_width=True):
                        rm = get_report_manager()
                        saved_ids = []
                        for name, result in results.items():
                            result.strategy_params = {
                                'fund_code': fund_code,
                                'fund_name': fund_name_input,
                                'start_date': str(sd),
                                'end_date': str(ed),
                                'strategy_name': name,
                                'comparison_mode': True
                            }
                            report_id = rm.save_report(result)
                            saved_ids.append(report_id)
                        st.success(f"已保存 {len(saved_ids)} 个报告，ID: {saved_ids}")
                        st.session_state['refresh_reports'] = True
        elif run_btn and not selected_strategies:
            st.warning("请至少选择一个策略进行对比")


def page_single_backtest(sd, ed, amt, freq, day_of_month, day_of_week, ds):
    """单股票回测页面 - Tab 布局"""
    st.markdown(f'<div class="section-header">{t("page_single_backtest")}</div>', unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["📊 单策略回测", "⚔️ 策略对比"])
    
    with tab1:
        page_single_backtest_tab1(sd, ed, amt, freq, day_of_month, day_of_week, ds)
    
    with tab2:
        page_single_backtest_tab2(sd, ed, amt, freq, day_of_month, day_of_week, ds)


def page_compare(sd2, ed2, amt2, ds):
    """多股票对比页面 - 简化为只支持策略选择"""
    from backtest.strategy_manager import StrategyManager
    
    st.markdown(f'<div class="section-header">{t("multi_compare_title")}</div>', unsafe_allow_html=True)
    
    sm = StrategyManager()
    
    col_left, col_right = st.columns([1, 2.5])
    
    with col_left:
        st.markdown("""
        <div class="card">
            <h4>多股票对比</h4>
            <p>对比多只股票在同一策略下的表现</p>
        </div>
        """, unsafe_allow_html=True)
        
        compare_funds = st.text_area(
            "股票代码（逗号分隔）", 
            value="600036,601318,600519", 
            height=100,
            help="例如: 600036,601318,600519"
        )
        
        st.caption(f"📅 回测时间: {sd2} ~ {ed2}")
        
        amount2 = st.number_input("每次投入金额", min_value=100, value=int(amt2), step=100, key="amt2_multi")
        
        st.markdown("---")
        st.markdown("### 选择策略")
        
        strategy_options = {s.id: s.name for s in sm.list_strategies()}
        if strategy_options:
            selected_strategy_id = st.selectbox(
                "选择策略",
                options=list(strategy_options.keys()),
                format_func=lambda x: strategy_options.get(x) or x,
                key="multi_strategy_selector"
            )
            selected_strategy = sm.get_strategy(selected_strategy_id)
        else:
            st.warning("暂无策略，请先创建策略")
            selected_strategy = None
        
        compare_btn = st.button("🚀 开始对比", type="primary", key="multi_compare_btn", use_container_width=True)
    
    with col_right:
        if compare_btn:
            codes = [c.strip() for c in compare_funds.split(',') if c.strip()]
            
            if not codes:
                st.warning("请输入至少一个股票代码")
                return
            
            if selected_strategy is None:
                st.warning("请先选择一个策略")
                return
            
            with st.spinner(f"正在对比 {len(codes)} 只股票..."):
                fund_list = [{'fund_code': c, 'name': get_fund_name(c)} for c in codes]
                
                tester = FundBacktester(data_source=ds)
                params = selected_strategy.params
                
                results = tester.compare(
                    fund_list, str(sd2), str(ed2), amount2,
                    enable_stop_loss=params.enable_stop_loss,
                    stop_loss_rate=params.stop_loss_rate,
                    enable_take_profit=params.enable_take_profit,
                    take_profit_rate=params.take_profit_rate,
                    max_drawdown_threshold=params.max_drawdown_threshold,
                    sell_ratio=params.take_profit_sell_ratio
                )
                
                if results:
                    st.success(f"✅ 对比完成 - {selected_strategy.name} 策略")
                    
                    comp_df = pd.DataFrame([
                        {
                            "股票": name,
                            "总投入": f"¥{r.total_invested:,.0f}",
                            "最终价值": f"¥{r.final_value:,.0f}",
                            "总收益率": f"{r.return_rate:+.2f}%",
                            "年化收益": f"{r.annual_return:+.2f}%",
                            "最大回撤": f"{r.max_drawdown:.2f}%",
                            "交易次数": r.investment_count,
                            "止损次数": r.stop_loss_count,
                            "止盈次数": r.take_profit_count
                        }
                        for name, r in results.items()
                    ])
                    
                    st.dataframe(comp_df, width='stretch', hide_index=True)
                    
                    st.markdown("")
                    visualizer = PlotlyVisualizer()
                    fig = visualizer.plot_comparison(results)
                    st.plotly_chart(fig, use_container_width=True)
                    
                    st.markdown("")
                    col_save = st.columns([1])
                    with col_save[0]:
                        if st.button("💾 保存所有报告", key="save_multi_reports", use_container_width=True):
                            rm = get_report_manager()
                            saved_ids = []
                            for name, result in results.items():
                                result.strategy_params = {
                                    'fund_name': name,
                                    'start_date': str(sd2),
                                    'end_date': str(ed2),
                                    'strategy_name': selected_strategy.name,
                                    'investment_amount': amount2
                                }
                                report_id = rm.save_report(result)
                                saved_ids.append(report_id)
                            st.success(f"已保存 {len(saved_ids)} 个报告，ID: {saved_ids}")
                            st.session_state['refresh_reports'] = True
                else:
                    st.error("数据获取失败")
        else:
            st.markdown("""
            <div class="empty-state">
                <h3>选择股票和策略开始对比</h3>
                <p>多股票对比会展示不同股票在相同策略下的表现差异</p>
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
                                if st.button(t("btn_view_detail"), key=f"view_{report.id}", help="View", use_container_width=True):
                                    st.session_state['selected_report_id'] = report.id
                            with col_d:
                                if st.button(t("btn_delete"), key=f"del_{report.id}", help="Delete", use_container_width=True):
                                    rm.delete_report(report.id)
                                    st.rerun()
                    
                    # 显示选中报告的详情
                    if st.session_state.get('selected_report_id') == report.id:
                        with st.container():
                            st.markdown("---")
                            loaded_report = rm.load_report(report.id)
                            if loaded_report:
                                st.markdown(f"### {loaded_report.name}")
                                st.caption(f"ID: {loaded_report.id} | 创建时间: {loaded_report.created_at}")
                                
                                render_report_metrics(loaded_report)
                                
                                fig = plot_report_trades_plotly(loaded_report)
                                if fig is not None:
                                    st.plotly_chart(fig, use_container_width=True)
                                
                                col_d, col_e = st.columns(2)
                                with col_d:
                                    if st.button("删除", key=f"delete_{report.id}", use_container_width=True):
                                        rm.delete_report(report.id)
                                        st.session_state['selected_report_id'] = None
                                        st.rerun()
                                with col_e:
                                    if st.button("关闭", key=f"close_{report.id}", use_container_width=True):
                                        st.session_state['selected_report_id'] = None
                                        st.rerun()
                            
                            st.markdown("---")
                        
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
                fig = plot_report_trades_plotly(report)
                if fig is not None:
                    st.plotly_chart(fig, use_container_width=True)
                
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
                
                names = [r.name for r in valid_reports]
                invested = [r.result['total_invested'] for r in valid_reports]
                final = [r.result['final_value'] for r in valid_reports]
                returns = [r.result['return_rate'] for r in valid_reports]
                annual = [r.result['annual_return'] for r in valid_reports]
                drawdowns = [r.result['max_drawdown'] for r in valid_reports]
                
                fig = PlotlyVisualizer.plot_portfolio_comparison(
                    names, invested, final, returns, annual, drawdowns
                )
                st.plotly_chart(fig, use_container_width=True)
                
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
    (start_date, end_date, amount, frequency, day_of_month, day_of_week, data_source) = params
    
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
        page_single_backtest(start_date, end_date, amount, frequency, day_of_month, day_of_week, data_source)
    
    with tab2:
        page_compare(start_date, end_date, amount, data_source)
    
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
