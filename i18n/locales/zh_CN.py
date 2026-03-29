# -*- coding: utf-8 -*-
"""
中文语言包
"""

zh_CN = {
    # 应用标题
    "app_title": "股票定投回测工具",
    "app_description": "专业的 DCA 定投回测分析系统",
    
    # Tab 标签
    "tab_single_backtest": "📊 单股票回测",
    "tab_multi_comparison": "📈 多股票对比",
    "tab_watchlist": "⭐ 自选股",
    "tab_strategy": "🎯 策略管理",
    "tab_auto_backtest": "📋 自动回测",
    "tab_reports": "📁 报告管理",
    
    # 侧边栏
    "sidebar_title": "⚙️ 参数设置",
    "sidebar_date_range": "📅 回测时间",
    "sidebar_start_date": "开始日期",
    "sidebar_end_date": "结束日期",
    "sidebar_investment": "💰 投资设置",
    "sidebar_amount": "每次定投金额(元)",
    "sidebar_frequency": "定投频率",
    "sidebar_monthly_day": "每月定投日期",
    "sidebar_weekly_day": "每周定投日",
    "sidebar_stop_loss": "🛡️ 止损设置",
    "sidebar_enable_stop_loss": "启用止损",
    "sidebar_stop_loss_rate": "止损率(%)",
    "sidebar_stop_loss_ratio": "止损卖出比例(%)",
    "sidebar_take_profit": "🎯 止盈设置",
    "sidebar_enable_take_profit": "启用止盈",
    "sidebar_take_profit_rate": "止盈收益率(%)",
    "sidebar_max_drawdown_threshold": "最大回撤阈值(%)",
    "sidebar_sell_ratio": "卖出比例(%)",
    "sidebar_dip_buy": "📉 补仓设置",
    "sidebar_enable_dip_buy": "启用单日大跌补仓",
    "sidebar_yield_boost": "📈 收益增强",
    "sidebar_enable_yield_boost": "启用累计收益率增额",
    "sidebar_trigger_threshold": "累计收益率低于(%)",
    "sidebar_boost_amount": "每次增额(元)",
    "sidebar_recover_threshold": "收益率回升到(%)",
    "sidebar_data_source": "📡 数据源",
    "sidebar_select_source": "选择数据源",
    "sidebar_version": "v1.5.0",
    
    # 频率选项
    "freq_monthly": "每月",
    "freq_weekly": "每周",
    "freq_daily": "每日",
    
    # 星期选项
    "week_monday": "周一",
    "week_tuesday": "周二",
    "week_wednesday": "周三",
    "week_thursday": "周四",
    "week_friday": "周五",
    
    # 单股票回测页面
    "stock_selection": "📝 股票选择",
    "stock_code": "股票代码",
    "stock_code_help": "如: 600036",
    "stock_name": "股票名称",
    "stock_name_help": "留空则自动识别",
    "current_selection": "当前选择",
    "btn_start_backtest": "🚀 开始回测",
    "btn_save_report": "💾 保存报告",
    
    # 指标卡片
    "metric_total_invested": "💰 总投入",
    "metric_final_value": "📈 最终价值",
    "metric_total_return": "📊 总收益率",
    "metric_annual_return": "📅 年化收益",
    "metric_max_drawdown": "⬇️ 最大回撤",
    "metric_investment_count": "🔄 定投次数",
    "metric_stop_loss_count": "🛡️ 止损次数",
    "metric_take_profit_count": "🎯 止盈次数",
    
    # 交易记录
    "trades_title": "📋 查看交易记录",
    "col_date": "日期",
    "col_action": "操作",
    "col_nav": "净值(元)",
    "col_shares_change": "份额变化(份)",
    "col_total_shares": "累计份额(份)",
    "col_invest_amount": "投入金额(元)",
    "col_portfolio_value": "组合价值(元)",
    "col_return_rate": "收益率(%)",
    "col_reason": "原因",
    
    # 空状态
    "empty_state_hint": "👈 请在左侧输入股票代码并点击开始回测",
    "empty_state_compare_hint": "👈 请输入股票代码并点击开始对比",
    "quick_codes": "💡 常用股票代码",
    
    # 错误和警告
    "error_data_fetch_failed": "❌ 获取数据失败",
    "error_recovery_threshold": "恢复阈值必须大于触发阈值",
    "troubleshoot_title": "💡 排查建议",
    "troubleshoot_possible_causes": "可能的原因：",
    "troubleshoot_suggestions": "建议尝试：",
    "cause_wrong_code": "股票代码错误 - 请确认股票代码是否正确（如 600036）",
    "cause_no_permission": "Tushare 权限不足 - 免费版可能没有该股票的数据权限",
    "cause_network_error": "网络问题 - 无法连接到数据源服务器",
    "cause_data_not_synced": "数据未同步 - 数据库中没有该股票的历史数据",
    "suggest_change_code": "更换股票代码",
    "suggest_change_source": "切换数据源（akshare/tushare）",
    "suggest_sync_data": "先同步股票数据到本地数据库",
    
    # 成功消息
    "success_backtest_complete": "✅ 回测完成",
    "success_report_saved": "✅ 报告已保存!",
    "success_compare_complete": "✅ 对比完成",
    "success_report_exported": "✅ 报告已导出",
    
    # 多股票对比
    "multi_compare_title": "📈 多股票对比分析",
    "input_settings": "📝 输入设置",
    "stock_codes_input": "股票代码（逗号分隔）",
    "stock_codes_help": "多个代码用逗号分隔，如: 600036,601318,600519",
    "btn_start_compare": "🔍 开始对比",
    "compare_result": "对比结果",
    "recommend_compare": "建议选择 2-5 个股票进行对比分析",
    
    # 报告管理
    "reports_title": "📋 已保存的报告",
    "search_report": "🔍 搜索报告",
    "filter_stock": "📂 筛选股票",
    "all": "全部",
    "no_reports": "暂无保存的报告，请先进行回测并保存报告",
    "report_detail_title": "📊 报告详情",
    "select_report": "📋 选择报告",
    "created_time": "创建时间",
    "btn_delete_report": "🗑️ 删除报告",
    "btn_export_report": "📥 导出报告",
    "report_compare_title": "📈 报告对比",
    "select_compare_reports": "📊 选择要对比的报告（至少选择2个）",
    "btn_export_compare": "📥 导出对比报告",
    "need_two_reports": "需要至少2个报告才能进行对比",
    "need_more_reports": "请先保存更多报告后再使用此功能",
    "select_at_least_two": "请至少选择2个报告进行对比",
    
    # 策略管理
    "strategy_title": "🎯 策略管理",
    "strategy_create": "新建策略",
    "strategy_edit": "编辑策略",
    "strategy_name": "策略名称",
    "strategy_group": "策略分组",
    "strategy_description": "策略描述",
    "strategy_my": "我的策略",
    "strategy_conservative": "保守型",
    "strategy_aggressive": "激进型",
    "strategy_enhanced": "增强型",
    
    # 自选股管理
    "watchlist_title": "⭐ 自选股管理",
    "watchlist_create": "创建新列表",
    "watchlist_name": "列表名称",
    "watchlist_desc": "描述",
    "watchlist_settings": "⚙️ 列表设置",
    "btn_save_changes": "💾 保存修改",
    "btn_add_stock": "➕ 添加股票",
    "btn_remove": "移除",
    "stock_code_col": "代码",
    "stock_name_col": "名称",
    "stock_market_col": "市场",
    "stock_type_col": "类型",
    "stock_notes_col": "备注",
    "empty_watchlist": "暂无自选股列表，请先创建一个",
    
    # 自动回测
    "auto_backtest_title": "📋 自动回测任务",
    "task_create": "创建任务",
    "task_name": "任务名称",
    "task_select_watchlist": "选择自选股列表",
    "task_select_strategies": "选择策略",
    "task_progress": "任务进度",
    "task_status": "状态",
    "btn_create_task": "🚀 创建并执行任务",
    "btn_start_task": "▶️ 开始",
    "btn_pause_task": "⏸️ 暂停",
    "btn_resume_task": "▶️ 继续",
    "btn_cancel_task": "⏹️ 取消",
    
    # 任务状态
    "status_created": "已创建",
    "status_running": "执行中",
    "status_paused": "已暂停",
    "status_completed": "已完成",
    "status_cancelled": "已取消",
    "status_pending": "等待中",
    "status_failed": "失败",
    
    # 语言选择
    "language_title": "🌐 语言",
    "current_language": "当前",
    
    # 图表标题
    "chart_invest_vs_profit": "投入与收益曲线",
    "chart_return_trend": "收益率走势",
    "chart_investment_value": "Investment vs Value",
    "chart_return_comparison": "Total Return Comparison",
    "chart_annual_return": "Annual Return Comparison",
    "chart_max_drawdown": "Max Drawdown Comparison",
    
    # 图表标签
    "label_total_invested": "累计投入",
    "label_portfolio_value": "资产总值",
    "label_profit": "盈利",
    "label_loss": "亏损",
    "label_date": "日期",
    "label_amount": "金额(元)",
    "label_return_rate": "收益率(%)",
    "label_total_invested_en": "Total Invested",
    "label_final_value": "Final Value",
    
    # Page titles
    "page_title": "股票定投回测工具",
    "page_single_backtest": "📊 单股票回测",
    "page_multi_compare": "多股票对比页面",
    "page_reports": "报告管理页面",
    
    # Expander labels
    "expander_date_range": "📅 回测时间",
    "expander_investment": "💰 投资设置",
    "expander_stop_loss": "🛡️ 止损设置",
    "expander_take_profit": "🎯 止盈设置",
    "expander_dip_buy": "📉 补仓设置",
    "expander_yield_boost": "📈 收益增强",
    "expander_data_source": "📡 数据源",
    
    # Dip buy tiers
    "dip_tier_label": "档位",
    "dip_fall_label": "跌幅>",
    "dip_amount_label": "补仓金额:",
    
    # Dip tier options
    "dip_3pct": "3%",
    "dip_5pct": "5%",
    "dip_7pct": "7%",
    
    # Frequency and weekday options
    "weekday_monday": "周一",
    "weekday_tuesday": "周二",
    "weekday_wednesday": "周三",
    "weekday_thursday": "周四",
    "weekday_friday": "周五",
    
    # Report list tabs
    "tab_report_list": "📋 报告列表",
    "tab_report_detail": "📊 报告详情",
    "tab_report_compare": "📈 报告对比",
    
    # Empty states
    "empty_no_trades": "暂无交易记录",
    "empty_trades_missing_date": "交易记录缺少日期字段",
    "empty_no_reports_list": "暂无保存的报告",
    "empty_no_reports_detail": "📭 暂无报告",
    "empty_no_reports_compare": "📭 需要至少2个报告才能进行对比",
    
    # Spinner messages
    "spinner_fetching_data": "⏳ 正在获取数据并计算，请稍候...",
    
    # Button labels
    "btn_view_detail": "👁️",
    "btn_delete": "🗑️",
    
    # Chart titles
    "chart_title_invest_profit": "{name} - 投入与收益曲线",
    "chart_title_return_trend": "{name} - 收益率走势",
    
    # Report comparison table headers
    "col_stock": "股票",
    "col_date_range": "日期范围",
    "col_total_invested": "总投入(元)",
    "col_final_value": "最终价值(元)",
    "col_total_return_pct": "总收益(%)",
    "col_annual_return_pct": "年化收益(%)",
    "col_max_drawdown_pct": "最大回撤(%)",
    "col_invest_count": "定投次数",
    "col_stop_loss_count": "止损次数",
    "col_take_profit_count": "止盈次数",
    
    # Report list
    "report_id_label": "ID",
    "report_created_label": "创建",
    "report_rate_label": "收益率",
    
    # Quick stock codes
    "quick_stock_600036": "招商银行",
    "quick_stock_601318": "中国平安",
    "quick_stock_600519": "贵州茅台",
    "quick_stock_000858": "五粮液",
    "quick_stock_510300": "沪深300ETF",
    "quick_stock_510500": "中证500ETF",
    
    # Watchlist
    "watchlist_etf": "ETF基金",
    "watchlist_stocks": "蓝筹股",
    "watchlist_banks": "银行股",
    
    # Message patterns
    "msg_backtest_complete": "✅ 回测完成 - {name}",
    "msg_report_saved": "✅ 报告已保存! ID: {id}",
    "msg_compare_complete": "✅ 对比完成 - {count} 个股票",
    "msg_report_exported": "✅ 报告已导出: {path}",
    "msg_compare_exported": "✅ 对比报告已导出: {path}",
    "msg_need_more_reports": "请先保存更多报告后再使用此功能",
    "msg_select_at_least_two": "👆 请至少选择2个报告进行对比",
}
