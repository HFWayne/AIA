# -*- coding: utf-8 -*-
"""
English language pack
"""

en_US = {
    # App title
    "app_title": "Stock DCA Backtesting Tool",
    "app_description": "Professional DCA Investment Backtesting System",
    
    # Tab labels
    "tab_single_backtest": "📊 Single Stock",
    "tab_multi_comparison": "📈 Multi Comparison",
    "tab_watchlist": "⭐ Watchlist",
    "tab_strategy": "🎯 Strategies",
    "tab_auto_backtest": "📋 Auto Backtest",
    "tab_reports": "📁 Reports",
    
    # Sidebar
    "sidebar_title": "⚙️ Settings",
    "sidebar_date_range": "📅 Date Range",
    "sidebar_start_date": "Start Date",
    "sidebar_end_date": "End Date",
    "sidebar_investment": "💰 Investment",
    "sidebar_amount": "Amount per Investment (CNY)",
    "sidebar_frequency": "Frequency",
    "sidebar_monthly_day": "Day of Month",
    "sidebar_weekly_day": "Day of Week",
    "sidebar_stop_loss": "🛡️ Stop Loss",
    "sidebar_enable_stop_loss": "Enable Stop Loss",
    "sidebar_stop_loss_rate": "Stop Loss Rate (%)",
    "sidebar_stop_loss_ratio": "Sell Ratio (%)",
    "sidebar_take_profit": "🎯 Take Profit",
    "sidebar_enable_take_profit": "Enable Take Profit",
    "sidebar_take_profit_rate": "Target Return (%)",
    "sidebar_max_drawdown_threshold": "Max Drawdown Threshold (%)",
    "sidebar_sell_ratio": "Sell Ratio (%)",
    "sidebar_dip_buy": "📉 Dip Buy",
    "sidebar_enable_dip_buy": "Enable Dip Buy on Big Drop",
    "sidebar_yield_boost": "📈 Yield Boost",
    "sidebar_enable_yield_boost": "Enable Yield Boost",
    "sidebar_trigger_threshold": "When Yield Below (%)",
    "sidebar_boost_amount": "Boost Amount (CNY)",
    "sidebar_recover_threshold": "Recover at Yield (%)",
    "sidebar_data_source": "📡 Data Source",
    "sidebar_select_source": "Select Data Source",
    "sidebar_version": "v1.5.0",
    
    # Frequency options
    "freq_monthly": "Monthly",
    "freq_weekly": "Weekly",
    "freq_daily": "Daily",
    
    # Weekday options
    "week_monday": "Monday",
    "week_tuesday": "Tuesday",
    "week_wednesday": "Wednesday",
    "week_thursday": "Thursday",
    "week_friday": "Friday",
    
    # Single stock backtest page
    "stock_selection": "📝 Stock Selection",
    "stock_code": "Stock Code",
    "stock_code_help": "e.g., 600036",
    "stock_name": "Stock Name",
    "stock_name_help": "Leave empty for auto-detect",
    "current_selection": "Current Selection",
    "btn_start_backtest": "🚀 Start Backtest",
    "btn_save_report": "💾 Save Report",
    
    # Metric cards
    "metric_total_invested": "💰 Total Invested",
    "metric_final_value": "📈 Final Value",
    "metric_total_return": "📊 Total Return",
    "metric_annual_return": "📅 Annual Return",
    "metric_max_drawdown": "⬇️ Max Drawdown",
    "metric_investment_count": "🔄 Investments",
    "metric_stop_loss_count": "🛡️ Stop Losses",
    "metric_take_profit_count": "🎯 Take Profits",
    
    # Trade records
    "trades_title": "📋 Trade Records",
    "col_date": "Date",
    "col_action": "Action",
    "col_nav": "NAV (CNY)",
    "col_shares_change": "Shares Δ",
    "col_total_shares": "Total Shares",
    "col_invest_amount": "Invest (CNY)",
    "col_portfolio_value": "Value (CNY)",
    "col_return_rate": "Return (%)",
    "col_reason": "Reason",
    
    # Empty states
    "empty_state_hint": "👈 Enter stock code on the left and click Start Backtest",
    "empty_state_compare_hint": "👈 Enter stock codes and click Start Comparison",
    "quick_codes": "💡 Common Stock Codes",
    
    # Errors and warnings
    "error_data_fetch_failed": "❌ Failed to fetch data",
    "error_recovery_threshold": "Recovery threshold must be greater than trigger threshold",
    "troubleshoot_title": "💡 Troubleshooting",
    "troubleshoot_possible_causes": "Possible causes:",
    "troubleshoot_suggestions": "Suggestions:",
    "cause_wrong_code": "Wrong stock code - Please verify the code (e.g., 600036)",
    "cause_no_permission": "Tushare permission insufficient - Free version may not have data for this stock",
    "cause_network_error": "Network error - Cannot connect to data source server",
    "cause_data_not_synced": "Data not synced - No historical data in local database",
    "suggest_change_code": "Try a different stock code",
    "suggest_change_source": "Switch data source (akshare/baostock)",
    "suggest_sync_data": "Sync stock data to local database first",
    
    # Success messages
    "success_backtest_complete": "✅ Backtest Complete",
    "success_report_saved": "✅ Report Saved!",
    "success_compare_complete": "✅ Comparison Complete",
    "success_report_exported": "✅ Report Exported",
    
    # Multi-stock comparison
    "multi_compare_title": "📈 Multi-Stock Comparison",
    "input_settings": "📝 Input Settings",
    "stock_codes_input": "Stock Codes (comma separated)",
    "stock_codes_help": "Separate multiple codes with comma, e.g., 600036,601318,600519",
    "btn_start_compare": "🔍 Start Comparison",
    "compare_result": "Comparison Result",
    "recommend_compare": "Recommended: Select 2-5 stocks for comparison",
    
    # Report management
    "reports_title": "📋 Saved Reports",
    "search_report": "🔍 Search Reports",
    "filter_stock": "📂 Filter by Stock",
    "all": "All",
    "no_reports": "No saved reports. Run a backtest and save the report first.",
    "report_detail_title": "📊 Report Details",
    "select_report": "📋 Select Report",
    "created_time": "Created",
    "btn_delete_report": "🗑️ Delete",
    "btn_export_report": "📥 Export Report",
    "report_compare_title": "📈 Report Comparison",
    "select_compare_reports": "📊 Select reports to compare (at least 2)",
    "btn_export_compare": "📥 Export Comparison",
    "need_two_reports": "Need at least 2 reports for comparison",
    "need_more_reports": "Save more reports first to use this feature",
    "select_at_least_two": "Please select at least 2 reports to compare",
    
    # Strategy management
    "strategy_title": "🎯 Strategy Management",
    "strategy_create": "Create Strategy",
    "strategy_edit": "Edit Strategy",
    "strategy_name": "Strategy Name",
    "strategy_group": "Strategy Group",
    "strategy_description": "Description",
    "strategy_my": "My Strategies",
    "strategy_conservative": "Conservative",
    "strategy_aggressive": "Aggressive",
    "strategy_enhanced": "Enhanced",
    
    # Watchlist management
    "watchlist_title": "⭐ Watchlist Management",
    "watchlist_create": "Create New List",
    "watchlist_name": "List Name",
    "watchlist_desc": "Description",
    "watchlist_settings": "⚙️ List Settings",
    "btn_save_changes": "💾 Save Changes",
    "btn_add_stock": "➕ Add Stock",
    "btn_remove": "Remove",
    "stock_code_col": "Code",
    "stock_name_col": "Name",
    "stock_market_col": "Market",
    "stock_type_col": "Type",
    "stock_notes_col": "Notes",
    "empty_watchlist": "No watchlists. Create one first.",
    
    # Auto backtest
    "auto_backtest_title": "📋 Auto Backtest Tasks",
    "task_create": "Create Task",
    "task_name": "Task Name",
    "task_select_watchlist": "Select Watchlist",
    "task_select_strategies": "Select Strategies",
    "task_progress": "Progress",
    "task_status": "Status",
    "btn_create_task": "🚀 Create & Execute Task",
    "btn_start_task": "▶️ Start",
    "btn_pause_task": "⏸️ Pause",
    "btn_resume_task": "▶️ Resume",
    "btn_cancel_task": "⏹️ Cancel",
    
    # Task statuses
    "status_created": "Created",
    "status_running": "Running",
    "status_paused": "Paused",
    "status_completed": "Completed",
    "status_cancelled": "Cancelled",
    "status_pending": "Pending",
    "status_failed": "Failed",
    
    # Language selector
    "language_title": "🌐 Language",
    "current_language": "Current",
    
    # Chart titles
    "chart_invest_vs_profit": "Investment vs Profit",
    "chart_return_trend": "Return Trend",
    "chart_investment_value": "Investment vs Value",
    "chart_return_comparison": "Total Return Comparison",
    "chart_annual_return": "Annual Return Comparison",
    "chart_max_drawdown": "Max Drawdown Comparison",
    
    # Chart labels
    "label_total_invested": "Total Invested",
    "label_portfolio_value": "Portfolio Value",
    "label_profit": "Profit",
    "label_loss": "Loss",
    "label_date": "Date",
    "label_amount": "Amount (CNY)",
    "label_return_rate": "Return (%)",
    "label_total_invested_en": "Total Invested",
    "label_final_value": "Final Value",
    
    # Page titles
    "page_title": "Stock DCA Backtesting Tool",
    "page_single_backtest": "📊 Single Stock Backtest",
    "page_multi_compare": "Multi-Stock Comparison",
    "page_reports": "Report Management",
    
    # Expander labels
    "expander_date_range": "📅 Date Range",
    "expander_investment": "💰 Investment",
    "expander_stop_loss": "🛡️ Stop Loss",
    "expander_take_profit": "🎯 Take Profit",
    "expander_dip_buy": "📉 Dip Buy",
    "expander_yield_boost": "📈 Yield Boost",
    "expander_data_source": "📡 Data Source",
    
    # Dip buy tiers
    "dip_tier_label": "Tier",
    "dip_fall_label": "Drop >",
    "dip_amount_label": "Amount:",
    
    # Dip tier options
    "dip_3pct": "3%",
    "dip_5pct": "5%",
    "dip_7pct": "7%",
    
    # Frequency and weekday options
    "weekday_monday": "Monday",
    "weekday_tuesday": "Tuesday",
    "weekday_wednesday": "Wednesday",
    "weekday_thursday": "Thursday",
    "weekday_friday": "Friday",
    
    # Report list tabs
    "tab_report_list": "📋 Report List",
    "tab_report_detail": "📊 Report Detail",
    "tab_report_compare": "📈 Report Compare",
    
    # Empty states
    "empty_no_trades": "No trade records",
    "empty_trades_missing_date": "Trade records missing date field",
    "empty_no_reports_list": "No saved reports",
    "empty_no_reports_detail": "📭 No reports yet",
    "empty_no_reports_compare": "📭 Need at least 2 reports for comparison",
    
    # Spinner messages
    "spinner_fetching_data": "⏳ Fetching data and calculating...",
    
    # Button labels
    "btn_view_detail": "👁️",
    "btn_delete": "🗑️",
    
    # Chart titles
    "chart_title_invest_profit": "{name} - Investment & Profit",
    "chart_title_return_trend": "{name} - Return Trend",
    
    # Report comparison table headers
    "col_stock": "Stock",
    "col_date_range": "Date Range",
    "col_total_invested": "Invested (CNY)",
    "col_final_value": "Final Value (CNY)",
    "col_total_return_pct": "Total Return (%)",
    "col_annual_return_pct": "Annual Return (%)",
    "col_max_drawdown_pct": "Max Drawdown (%)",
    "col_invest_count": "Investments",
    "col_stop_loss_count": "Stop Losses",
    "col_take_profit_count": "Take Profits",
    
    # Report list
    "report_id_label": "ID",
    "report_created_label": "Created",
    "report_rate_label": "Return",
    
    # Quick stock codes
    "quick_stock_600036": "CMB",
    "quick_stock_601318": "Ping An",
    "quick_stock_600519": "Kweichow Moutai",
    "quick_stock_000858": "Wuliangye",
    "quick_stock_510300": "CSI 300 ETF",
    "quick_stock_510500": "CSI 500 ETF",
    
    # Watchlist
    "watchlist_etf": "ETF Funds",
    "watchlist_stocks": "Blue Chips",
    "watchlist_banks": "Bank Stocks",
    
    # Message patterns
    "msg_backtest_complete": "✅ Backtest Complete - {name}",
    "msg_report_saved": "✅ Report Saved! ID: {id}",
    "msg_compare_complete": "✅ Comparison Complete - {count} stocks",
    "msg_report_exported": "✅ Report Exported: {path}",
    "msg_compare_exported": "✅ Comparison Exported: {path}",
    "msg_need_more_reports": "Save more reports first to use this feature",
    "msg_select_at_least_two": "👆 Please select at least 2 reports to compare",
}
