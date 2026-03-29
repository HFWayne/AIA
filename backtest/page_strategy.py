# -*- coding: utf-8 -*-
"""
策略管理页面
"""

import streamlit as st
from backtest.strategy_manager import StrategyManager, StrategyTemplate, StrategyParams


def render_strategy_manager():
    """渲染策略管理页面"""
    st.markdown('<div class="section-header">🎯 策略管理</div>', unsafe_allow_html=True)

    sm = StrategyManager()
    groups = sm.get_groups()
    all_strategies = sm.list_strategies()

    tabs = st.tabs(groups + ["新建策略"])

    group_map = {g: idx for idx, g in enumerate(groups)}

    for group, tab_idx in group_map.items():
        strategies = sm.list_strategies(group)
        with tabs[tab_idx]:
            render_strategy_list(sm, strategies, group)

    with tabs[-1]:
        render_create_strategy(sm, groups)


def render_strategy_list(sm: StrategyManager, strategies: list, current_group: str):
    """渲染策略列表"""
    if not strategies:
        st.markdown(f"""
        <div class="empty-state">
            <h4>📭 暂无 {current_group} 策略</h4>
            <p>点击上方"新建策略"创建一个</p>
        </div>
        """, unsafe_allow_html=True)
        return

    for strategy in strategies:
        with st.container():
            col_left, col_right = st.columns([4, 1])

            with col_left:
                color = strategy.params.enable_stop_loss or strategy.params.enable_take_profit
                icon = "🛡️" if color else "📊"
                st.markdown(f"{icon} **{strategy.name}**")
                st.caption(f"参数: {strategy.params.get_summary()}")

            with col_right:
                col_edit, col_del = st.columns(2)
                with col_edit:
                    if st.button("✏️", key=f"edit_{strategy.id}"):
                        st.session_state[f'edit_strategy_{strategy.id}'] = True
                with col_del:
                    if st.button("🗑️", key=f"del_{strategy.id}"):
                        sm.delete_strategy(strategy.id)
                        st.rerun()

            st.markdown("---")

        if st.session_state.get(f'edit_strategy_{strategy.id}', False):
            render_strategy_editor(sm, strategy, is_new=False)


def render_strategy_editor(sm: StrategyManager, strategy: StrategyTemplate = None, is_new: bool = True):
    """渲染策略编辑器"""
    st.markdown("### " + ("编辑策略" if not is_new else "新建策略"))

    name = st.text_input("策略名称", value=strategy.name if strategy else "")
    group = st.selectbox(
        "策略分组",
        ["我的策略", "保守型", "激进型", "增强型"],
        index=["我的策略", "保守型", "激进型", "增强型"].index(strategy.group) if strategy else 0
    )
    description = st.text_area("策略描述", value=strategy.description if strategy else "")

    st.markdown("#### 投资设置")
    col1, col2 = st.columns(2)

    freq_options = {"每月": "monthly", "每周": "weekly", "每日": "daily"}
    freq_display = list(freq_options.keys())

    with col1:
        freq_index = 0
        if strategy:
            for i, v in enumerate(["monthly", "weekly", "daily"]):
                if strategy.params.frequency == v:
                    freq_index = i
                    break
        freq = st.selectbox("投资频率", freq_display, index=freq_index)
        frequency = freq_options[freq]

    with col2:
        amount = st.number_input(
            "每次投资金额(元)",
            min_value=100,
            value=int(strategy.params.investment_amount) if strategy else 500,
            step=100
        )

    if frequency == "monthly":
        day_of_month = st.selectbox(
            "每月定投日期",
            list(range(1, 29)),
            index=(strategy.params.day_of_month - 1) if strategy else 0
        )
        day_of_week = 0
    else:
        day_of_month = 1
        week_map = {"周一": 0, "周二": 1, "周三": 2, "周四": 3, "周五": 4}
        week_display = list(week_map.keys())
        week_index = strategy.params.day_of_week if strategy else 0
        week_day = st.selectbox("每周定投日", week_display, index=week_index)
        day_of_week = week_map[week_day]

    st.markdown("#### 风控设置")

    enable_stop_loss = st.checkbox("启用止损", value=strategy.params.enable_stop_loss if strategy else False)
    stop_loss_rate = 0.10
    stop_loss_sell_ratio = 1.0

    if enable_stop_loss:
        col1, col2 = st.columns(2)
        with col1:
            stop_loss_rate = st.slider("止损率(%)", 5, 30,
                                       value=int(strategy.params.stop_loss_rate * 100) if strategy else 10) / 100
        with col2:
            stop_loss_sell_ratio = st.slider("止损卖出比例(%)", 50, 100,
                                            value=int(strategy.params.stop_loss_sell_ratio * 100) if strategy else 100) / 100

    enable_take_profit = st.checkbox("启用止盈", value=strategy.params.enable_take_profit if strategy else False)
    take_profit_rate = 0.20
    max_drawdown_threshold = 0.10
    take_profit_sell_ratio = 0.5

    if enable_take_profit:
        col1, col2, col3 = st.columns(3)
        with col1:
            take_profit_rate = st.slider("止盈收益率(%)", 5, 50,
                                         value=int(strategy.params.take_profit_rate * 100) if strategy else 20) / 100
        with col2:
            max_drawdown_threshold = st.slider("最大回撤阈值(%)", 5, 30,
                                               value=int(strategy.params.max_drawdown_threshold * 100) if strategy else 10) / 100
        with col3:
            take_profit_sell_ratio = st.slider("卖出比例(%)", 10, 100,
                                               value=int(strategy.params.take_profit_sell_ratio * 100) if strategy else 50) / 100

    st.markdown("#### 补仓设置")

    enable_dip_buy = st.checkbox("启用单日大跌补仓", value=strategy.params.enable_dip_buy if strategy else False)
    dip_buy_tier1_threshold = -0.03
    dip_buy_tier1_amount = 1000.0
    dip_buy_tier2_threshold = -0.05
    dip_buy_tier2_amount = 1000.0
    dip_buy_tier3_threshold = -0.07
    dip_buy_tier3_amount = 1000.0

    if enable_dip_buy:
        col_labels, col_t1, col_t2, col_t3 = st.columns([1, 1, 1, 1])
        with col_labels:
            st.write("**跌幅阈值**")
            st.write("**补仓金额**")
        with col_t1:
            tier1 = st.selectbox("t1", ["3%", "5%", "7%"], index=0, key="dip1_editor")
            tier_map = {"3%": -0.03, "5%": -0.05, "7%": -0.07}
            dip_buy_tier1_threshold = tier_map.get(tier1, -0.03)
        with col_t2:
            tier2 = st.selectbox("t2", ["3%", "5%", "7%"], index=1, key="dip2_editor")
            dip_buy_tier2_threshold = tier_map.get(tier2, -0.05)
        with col_t3:
            tier3 = st.selectbox("t3", ["3%", "5%", "7%"], index=2, key="dip3_editor")
            dip_buy_tier3_threshold = tier_map.get(tier3, -0.07)

        col_amt1, col_amt2, col_amt3 = st.columns(3)
        with col_amt1:
            dip_buy_tier1_amount = st.number_input("金额1", min_value=100, value=1000, step=100, key="dip_amt1_editor")
        with col_amt2:
            dip_buy_tier2_amount = st.number_input("金额2", min_value=100, value=1000, step=100, key="dip_amt2_editor")
        with col_amt3:
            dip_buy_tier3_amount = st.number_input("金额3", min_value=100, value=1000, step=100, key="dip_amt3_editor")

    st.markdown("#### 收益增强设置")

    enable_yield_boost = st.checkbox("启用累计收益率增额", value=strategy.params.enable_yield_boost if strategy else False)
    yield_boost_trigger = -0.20
    yield_boost_recover = -0.10
    yield_boost_amount = 500.0

    if enable_yield_boost:
        col1, col2, col3 = st.columns(3)
        with col1:
            yield_boost_trigger = st.slider("累计收益率低于(%)", -30, -5,
                                            value=int(strategy.params.yield_boost_trigger * 100) if strategy else -20) / 100
        with col2:
            yield_boost_amount = st.number_input("每次增额(元)", min_value=100, value=500, step=100)
        with col3:
            yield_boost_recover = st.slider("收益率回升到(%)", -30, -5,
                                            value=int(strategy.params.yield_boost_recover * 100) if strategy else -10) / 100

        if yield_boost_recover >= yield_boost_trigger:
            st.error("恢复阈值必须大于触发阈值")

    st.markdown("---")

    col_save, col_cancel = st.columns(2)
    with col_save:
        if st.button("💾 保存策略", type="primary", width='stretch'):
            params = StrategyParams(
                frequency=frequency,
                day_of_month=day_of_month,
                day_of_week=day_of_week,
                investment_amount=float(amount),
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

            if is_new:
                sm.create_strategy(name, group, description, params)
                st.success("策略已创建")
            else:
                sm.update_strategy(strategy.id, name=name, group=group,
                                 description=description, params=params)
                st.success("策略已更新")
                st.session_state[f'edit_strategy_{strategy.id}'] = False
            st.rerun()

    with col_cancel:
        if st.button("取消", width='stretch'):
            if strategy:
                st.session_state[f'edit_strategy_{strategy.id}'] = False
            st.rerun()


def render_create_strategy(sm: StrategyManager, existing_groups: list):
    """渲染创建新策略"""
    st.subheader("➕ 创建新策略")
    render_strategy_editor(sm, None, is_new=True)
