# -*- coding: utf-8 -*-
"""
自选股管理页面
"""

import streamlit as st
from backtest.watchlist_manager import WatchlistManager, Watchlist, StockInfo
from data_source.fund_data_source import FundDataSource


def render_watchlist_manager():
    """渲染自选股管理页面"""
    st.markdown('<div class="section-header">⭐ 自选股管理</div>', unsafe_allow_html=True)

    wm = WatchlistManager()
    watchlists = wm.list_watchlists()

    if not watchlists:
        st.info("暂无自选股列表，请先创建一个")
        with st.expander("创建新列表"):
            render_create_watchlist(wm, [])
        return

    tab_names = [w.name for w in watchlists] + ["➕ 新建列表"]
    tabs = st.tabs(tab_names)

    for idx, (tab, wl) in enumerate(zip(tabs[:-1], watchlists)):
        with tab:
            render_watchlist_tab(wm, wl)

    with tabs[-1]:
        render_create_watchlist(wm, watchlists)


def render_watchlist_tab(wm: WatchlistManager, watchlist: Watchlist):
    """渲染单个自选股列表"""
    wl_id = f"wl_{watchlist.id}"

    with st.expander("⚙️ 列表设置", expanded=False):
        col_name, col_desc = st.columns([2, 3])
        with col_name:
            new_name = st.text_input("列表名称", value=watchlist.name, key=f"{wl_id}_name")
        with col_desc:
            new_desc = st.text_input("描述", value=watchlist.description, key=f"{wl_id}_desc")
        
        col_save, col_del, col_count = st.columns([1, 1, 3])
        with col_save:
            if st.button("💾 保存修改", key=f"{wl_id}_save"):
                wm.update_watchlist(watchlist.id, name=new_name, description=new_desc)
                st.success("已保存")
                st.rerun()
        with col_del:
            if st.button("🗑️ 删除列表", key=f"{wl_id}_del"):
                wm.delete_watchlist(watchlist.id)
                st.rerun()
        with col_count:
            st.caption(f"共 {len(watchlist.stocks)} 只股票 | 创建: {watchlist.created_at[:10]} | 更新: {watchlist.updated_at[:10]}")

    st.markdown("---")

    col_left, col_right = st.columns([3, 1])

    with col_left:
        st.subheader("📋 股票列表")

        if not watchlist.stocks:
            st.info("暂无股票，请添加")
        else:
            data = []
            for stock in watchlist.stocks:
                data.append({
                    "代码": stock.code,
                    "名称": stock.name,
                    "市场": stock.market,
                    "类型": stock.type,
                    "标签": ", ".join(stock.tags) if stock.tags else "-",
                    "备注": stock.notes or "-"
                })
            
            st.dataframe(data, width='stretch', hide_index=True, use_container_width=True)
            
            col_del_all, col_count = st.columns([1, 4])
            with col_del_all:
                if st.button("🗑️ 清空列表", key=f"{wl_id}_clear"):
                    for s in watchlist.stocks:
                        wm.remove_stock(watchlist.id, s.code)
                    st.rerun()

    with col_right:
        st.subheader("➕ 添加股票")

        add_mode = st.radio("添加方式", ["按代码", "按名称搜索", "批量添加"], key=f"{wl_id}_mode")

        ds = FundDataSource()

        if add_mode == "按代码":
            new_code = st.text_input("股票代码", key=f"{wl_id}_code", placeholder="510300, 600036...")
            
            col_verify, col_add = st.columns([1, 1])
            with col_verify:
                if st.button("🔍 查询", key=f"{wl_id}_verify"):
                    if new_code:
                        with st.spinner("正在查询股票信息..."):
                            is_valid, name = ds.verify_stock(new_code)
                            if is_valid:
                                st.session_state[f"{wl_id}_verified_name"] = name
                                st.session_state[f"{wl_id}_verified"] = True
                                st.success(f"✅ 验证成功: {name}")
                            else:
                                st.session_state[f"{wl_id}_verified"] = False
                                st.error("❌ 股票代码无效")
                    else:
                        st.warning("请输入股票代码")
            
            if st.session_state.get(f"{wl_id}_verified"):
                st.info(f"股票名称: **{st.session_state.get(f'{wl_id}_verified_name', '')}**")
            
            with col_add:
                st.write("")
                if st.button("✅ 添加", key=f"{wl_id}_add_code"):
                    if new_code:
                        name = st.session_state.get(f"{wl_id}_verified_name") or new_code
                        info = ds.get_stock_info(new_code)
                        
                        stock = StockInfo(
                            code=new_code,
                            name=name,
                            market=info.get('market', 'A股') if info else 'A股',
                            type=info.get('type', 'ETF' if new_code.startswith(('5', '1', '15')) else '股票') if info else 'ETF',
                            tags=[info.get('industry', '')] if info and info.get('industry') else []
                        )
                        
                        if wm.add_stock(watchlist.id, stock):
                            st.success(f"已添加 {name}")
                            st.session_state[f"{wl_id}_verified"] = False
                            st.rerun()
                        else:
                            st.warning(f"{new_code} 已存在")
                    else:
                        st.error("请输入股票代码")

        elif add_mode == "按名称搜索":
            search_name = st.text_input("输入股票/ETF名称关键词", key=f"{wl_id}_search_name", placeholder="如：沪深300、芯片、医药...")
            
            if st.button("🔍 搜索", key=f"{wl_id}_search"):
                if search_name:
                    with st.spinner("搜索中..."):
                        from data_source.config import TU_SHARE_TOKEN
                        try:
                            import tushare as ts
                            ts.set_token(TU_SHARE_TOKEN)
                            pro = ts.pro_api()
                            
                            df = pro.stock_basic(list_status='L', name=search_name)
                            if df is not None and not df.empty:
                                st.session_state[f"{wl_id}_search_results"] = df.head(10).to_dict('records')
                            else:
                                df = pro.fund_basic(market='E', name=search_name)
                                if df is not None and not df.empty:
                                    st.session_state[f"{wl_id}_search_results"] = df.head(10).to_dict('records')
                                else:
                                    st.session_state[f"{wl_id}_search_results"] = []
                                    st.warning("未找到匹配的股票或ETF")
                        except Exception as e:
                            st.error(f"搜索失败: {e}")
                            st.session_state[f"{wl_id}_search_results"] = []
            
            results = st.session_state.get(f"{wl_id}_search_results", [])
            if results:
                st.write(f"找到 {len(results)} 个结果：")
                for i, item in enumerate(results):
                    name = item.get('name', item.get('fullname', '未知'))
                    code = item.get('ts_code', item.get('sec_code', ''))[:6]
                    industry = item.get('industry', item.get('management', ''))
                    
                    col_code, col_name, col_action = st.columns([1, 2, 1])
                    with col_code:
                        st.write(f"**{code}**")
                    with col_name:
                        st.write(f"{name} {f'({industry})' if industry else ''}")
                    with col_action:
                        if st.button("➕ 添加", key=f"{wl_id}_add_{i}"):
                            stock = StockInfo(code=code, name=name, tags=[industry] if industry else [])
                            if wm.add_stock(watchlist.id, stock):
                                st.success(f"已添加 {name}")
                                st.rerun()
                            else:
                                st.warning(f"{name} 已存在")

        elif add_mode == "批量添加":
            st.text_area("批量输入（每行一个，格式：代码,名称 或 只输入代码）", 
                        key=f"{wl_id}_batch",
                        placeholder="510300\n159915\n510050",
                        height=150)
            
            if st.button("🔍 验证并添加", key=f"{wl_id}_batch_verify"):
                lines = st.session_state.get(f"{wl_id}_batch", "").strip().split("\n")
                
                valid_codes = []
                invalid_codes = []
                
                with st.spinner("正在验证股票代码..."):
                    for line in lines:
                        code = line.strip()
                        if not code:
                            continue
                        code = code.split(",")[0].strip()
                        if code:
                            is_valid, name = ds.verify_stock(code)
                            if is_valid:
                                valid_codes.append((code, name))
                            else:
                                invalid_codes.append(code)
                
                if valid_codes:
                    st.success(f"✅ 有效股票: {len(valid_codes)} 只")
                    for code, name in valid_codes:
                        stock = StockInfo(code=code, name=name)
                        wm.add_stock(watchlist.id, stock)
                    st.rerun()
                
                if invalid_codes:
                    st.error(f"❌ 无效代码: {', '.join(invalid_codes)}")
            
            st.divider()
            
            col_q1, col_q2, col_q3 = st.columns(3)
            with col_q1:
                if st.button("📋 宽基ETF", key=f"{wl_id}_preset_etf"):
                    presets = [
                        StockInfo(code="510300", name="沪深300", market="A股", type="ETF", tags=["宽基", "大盘"]),
                        StockInfo(code="510500", name="中证500", market="A股", type="ETF", tags=["宽基", "中盘"]),
                        StockInfo(code="510050", name="上证50", market="A股", type="ETF", tags=["宽基", "大盘"]),
                        StockInfo(code="159915", name="创业板ETF", market="A股", type="ETF", tags=["宽基", "成长"]),
                        StockInfo(code="510880", name="红利ETF", market="A股", type="ETF", tags=["宽基", "高股息"]),
                    ]
                    added = 0
                    for stock in presets:
                        if wm.add_stock(watchlist.id, stock):
                            added += 1
                    st.success(f"已添加 {added} 只")
                    st.rerun()
            
            with col_q2:
                if st.button("📋 行业ETF", key=f"{wl_id}_preset_industry"):
                    presets = [
                        StockInfo(code="512880", name="证券ETF", market="A股", type="ETF", tags=["金融", "证券"]),
                        StockInfo(code="512760", name="芯片ETF", market="A股", type="ETF", tags=["科技", "芯片"]),
                        StockInfo(code="512660", name="军工ETF", market="A股", type="ETF", tags=["军工"]),
                        StockInfo(code="512010", name="医药ETF", market="A股", type="ETF", tags=["医药"]),
                        StockInfo(code="515050", name="5GETF", market="A股", type="ETF", tags=["科技", "5G"]),
                    ]
                    added = 0
                    for stock in presets:
                        if wm.add_stock(watchlist.id, stock):
                            added += 1
                    st.success(f"已添加 {added} 只")
                    st.rerun()
            
            with col_q3:
                if st.button("📋 红利ETF", key=f"{wl_id}_preset_dividend"):
                    presets = [
                        StockInfo(code="510880", name="红利ETF", market="A股", type="ETF", tags=["高股息", "红利"]),
                        StockInfo(code="512890", name="红利低波ETF", market="A股", type="ETF", tags=["高股息", "低波动"]),
                        StockInfo(code="515100", name="红利增强ETF", market="A股", type="ETF", tags=["高股息", "增强"]),
                    ]
                    added = 0
                    for stock in presets:
                        if wm.add_stock(watchlist.id, stock):
                            added += 1
                    st.success(f"已添加 {added} 只")
                    st.rerun()

    st.markdown("---")

    if watchlist.stocks:
        with st.expander("✏️ 编辑股票信息"):
            edit_stock_code = st.selectbox(
                "选择要编辑的股票",
                options=[s.code for s in watchlist.stocks],
                format_func=lambda x: next((f"{s.code} {s.name}" for s in watchlist.stocks if s.code == x), x),
                key=f"{wl_id}_edit_select"
            )
            
            stock_to_edit = next((s for s in watchlist.stocks if s.code == edit_stock_code), None)
            if stock_to_edit:
                col1, col2 = st.columns(2)
                with col1:
                    edit_name = st.text_input("名称", value=stock_to_edit.name, key=f"{wl_id}_edit_name")
                    edit_market = st.selectbox("市场", ["A股", "港股", "美股"], 
                                              index=["A股", "港股", "美股"].index(stock_to_edit.market) if stock_to_edit.market in ["A股", "港股", "美股"] else 0,
                                              key=f"{wl_id}_edit_market")
                with col2:
                    edit_type = st.selectbox("类型", ["ETF", "股票", "基金"],
                                            index=["ETF", "股票", "基金"].index(stock_to_edit.type) if stock_to_edit.type in ["ETF", "股票", "基金"] else 0,
                                            key=f"{wl_id}_edit_type")
                    edit_tags = st.text_input("标签（逗号分隔）", 
                                            value=", ".join(stock_to_edit.tags) if stock_to_edit.tags else "",
                                            key=f"{wl_id}_edit_tags")
                    edit_notes = st.text_input("备注", value=stock_to_edit.notes or "", key=f"{wl_id}_edit_notes")
                
                col_save, col_del = st.columns(2)
                with col_save:
                    if st.button("💾 保存修改", key=f"{wl_id}_edit_save"):
                        tags = [t.strip() for t in edit_tags.split(",") if t.strip()] if edit_tags else []
                        updated_stock = StockInfo(
                            code=stock_to_edit.code,
                            name=edit_name,
                            market=edit_market,
                            type=edit_type,
                            tags=tags,
                            notes=edit_notes
                        )
                        wm.update_stock(watchlist.id, updated_stock)
                        st.success("已保存")
                        st.rerun()
                with col_del:
                    if st.button("🗑️ 删除", key=f"{wl_id}_edit_del"):
                        wm.remove_stock(watchlist.id, stock_to_edit.code)
                        st.rerun()


def render_create_watchlist(wm: WatchlistManager, existing_lists):
    """渲染创建新列表"""
    st.subheader("➕ 创建新自选股列表")

    new_name = st.text_input("列表名称", placeholder="如：我的ETF、银行股组合")
    new_desc = st.text_area("描述（可选）", placeholder="列表用途说明", height=60)

    preset_options = {
        "不添加": [],
        "宽基ETF": [
            StockInfo(code="510300", name="沪深300", market="A股", type="ETF", tags=["宽基", "大盘"]),
            StockInfo(code="510500", name="中证500", market="A股", type="ETF", tags=["宽基", "中盘"]),
            StockInfo(code="159915", name="创业板ETF", market="A股", type="ETF", tags=["宽基", "成长"]),
            StockInfo(code="510050", name="上证50", market="A股", type="ETF", tags=["宽基", "大盘"]),
            StockInfo(code="510880", name="红利ETF", market="A股", type="ETF", tags=["宽基", "高股息"]),
        ],
        "行业ETF": [
            StockInfo(code="512880", name="证券ETF", market="A股", type="ETF", tags=["金融", "证券"]),
            StockInfo(code="512760", name="芯片ETF", market="A股", type="ETF", tags=["科技", "芯片"]),
            StockInfo(code="512660", name="军工ETF", market="A股", type="ETF", tags=["军工"]),
            StockInfo(code="512010", name="医药ETF", market="A股", type="ETF", tags=["医药"]),
            StockInfo(code="515050", name="5GETF", market="A股", type="ETF", tags=["科技", "5G"]),
        ],
        "红利基金": [
            StockInfo(code="510880", name="红利ETF", market="A股", type="ETF", tags=["高股息", "红利"]),
            StockInfo(code="512890", name="红利低波ETF", market="A股", type="ETF", tags=["高股息", "低波动"]),
            StockInfo(code="515100", name="红利增强ETF", market="A股", type="ETF", tags=["高股息", "增强"]),
        ],
    }

    preset_name = st.selectbox("预设股票", list(preset_options.keys()))

    if preset_name != "不添加":
        st.info(f"将添加 {len(preset_options[preset_name])} 只预设股票")

    if st.button("创建", type="primary", use_container_width=True):
        if new_name:
            if any(wl.name == new_name for wl in existing_lists):
                st.error("列表名称已存在")
            else:
                wl = wm.create_watchlist(new_name, new_desc)
                for stock in preset_options[preset_name]:
                    wm.add_stock(wl.id, stock)
                st.success(f"已创建 {new_name}" + (f"（含{len(preset_options[preset_name])}只预设股票）" if preset_name != "不添加" else ""))
                st.rerun()
        else:
            st.error("请输入列表名称")
