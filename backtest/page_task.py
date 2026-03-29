# -*- coding: utf-8 -*-
"""
任务管理页面
支持多股票多策略自动回测
"""

import time
import uuid
import threading
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional, List, Dict, Tuple
from enum import Enum
import streamlit as st
import pandas as pd

from backtest import FundBacktester, BacktestConfig
from backtest.watchlist_manager import WatchlistManager, StockInfo
from backtest.strategy_manager import StrategyManager, StrategyTemplate
from backtest.report_manager import ReportManager


class TaskStatus(Enum):
    CREATED = "created"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class StockStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class StockResult:
    """单只股票回测结果"""
    code: str
    name: str
    status: StockStatus = StockStatus.PENDING
    return_rate: Optional[float] = None
    annual_return: Optional[float] = None
    max_drawdown: Optional[float] = None
    error: Optional[str] = None
    report_id: Optional[str] = None


@dataclass
class AutoTask:
    """自动回测任务"""
    id: str
    name: str
    stock_codes: List[str]
    strategy_ids: List[str]
    start_date: str
    end_date: str
    status: TaskStatus = TaskStatus.CREATED
    created_at: str = ""
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    results: Dict[str, Dict[str, StockResult]] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'name': self.name,
            'stock_codes': self.stock_codes,
            'strategy_ids': self.strategy_ids,
            'start_date': self.start_date,
            'end_date': self.end_date,
            'status': self.status.value,
            'created_at': self.created_at,
            'started_at': self.started_at,
            'completed_at': self.completed_at,
            'results': {
                code_sid: {
                    'code': r.code,
                    'name': r.name,
                    'status': r.status.value,
                    'return_rate': r.return_rate,
                    'annual_return': r.annual_return,
                    'max_drawdown': r.max_drawdown,
                    'error': r.error,
                    'report_id': r.report_id
                }
                for code_sid, r in self.results.items()
            }
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'AutoTask':
        results = {}
        for key, val in data.get('results', {}).items():
            results[key] = StockResult(
                code=val['code'],
                name=val['name'],
                status=StockStatus[val['status'].upper()],
                return_rate=val.get('return_rate'),
                annual_return=val.get('annual_return'),
                max_drawdown=val.get('max_drawdown'),
                error=val.get('error'),
                report_id=val.get('report_id')
            )
        return cls(
            id=data['id'],
            name=data['name'],
            stock_codes=data['stock_codes'],
            strategy_ids=data['strategy_ids'],
            start_date=data['start_date'],
            end_date=data['end_date'],
            status=TaskStatus[data['status'].upper()],
            created_at=data.get('created_at', ''),
            started_at=data.get('started_at'),
            completed_at=data.get('completed_at'),
            results=results
        )


class TaskManager:
    """任务管理器"""

    def __init__(self, data_dir: Optional[str] = None):
        from pathlib import Path
        if data_dir is None:
            self.data_dir: Path = Path(__file__).parent.parent.parent / "reports" / "auto"
        else:
            self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.tasks_file = self.data_dir / "tasks.json"

    def _load_tasks(self) -> List[AutoTask]:
        if not self.tasks_file.exists():
            return []
        import json
        try:
            with open(self.tasks_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return [AutoTask.from_dict(t) for t in data]
        except:
            return []

    def _save_tasks(self, tasks: List[AutoTask]):
        import json
        with open(self.tasks_file, 'w', encoding='utf-8') as f:
            json.dump([t.to_dict() for t in tasks], f, ensure_ascii=False, indent=2)

    def create_task(self, name: str, stock_codes: List[str], strategy_ids: List[str],
                   start_date: str, end_date: str) -> AutoTask:
        task = AutoTask(
            id=str(uuid.uuid4())[:8],
            name=name,
            stock_codes=stock_codes,
            strategy_ids=strategy_ids,
            start_date=start_date,
            end_date=end_date,
            status=TaskStatus.CREATED,
            created_at=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        )
        tasks = self._load_tasks()
        tasks.append(task)
        self._save_tasks(tasks)
        return task

    def update_task(self, task: AutoTask):
        tasks = self._load_tasks()
        for i, t in enumerate(tasks):
            if t.id == task.id:
                tasks[i] = task
                break
        else:
            tasks.append(task)
        self._save_tasks(tasks)

    def get_task(self, task_id: str) -> Optional[AutoTask]:
        tasks = self._load_tasks()
        for t in tasks:
            if t.id == task_id:
                return t
        return None

    def list_tasks(self) -> List[AutoTask]:
        return self._load_tasks()


def run_backtest_for_stock(stock: StockInfo, strategy: StrategyTemplate,
                          start_date: str, end_date: str, tm: TaskManager,
                          task: AutoTask, data_source: str = 'tushare'):
    """执行单只股票单个策略的回测"""
    key = f"{stock.code}_{strategy.id}"

    result = StockResult(code=stock.code, name=stock.name, status=StockStatus.RUNNING)
    task.results[key] = result
    tm.update_task(task)

    try:
        tester = FundBacktester(data_source=data_source)
        config = BacktestConfig(
            fund_code=stock.code,
            fund_name=stock.name,
            start_date=start_date,
            end_date=end_date,
            investment_amount=strategy.params.investment_amount,
            frequency=strategy.params.frequency,
            day_of_month=strategy.params.day_of_month,
            day_of_week=strategy.params.day_of_week,
            data_source=data_source,
            enable_stop_loss=strategy.params.enable_stop_loss,
            stop_loss_rate=strategy.params.stop_loss_rate,
            stop_loss_sell_ratio=strategy.params.stop_loss_sell_ratio,
            enable_take_profit=strategy.params.enable_take_profit,
            take_profit_rate=strategy.params.take_profit_rate,
            max_drawdown_threshold=strategy.params.max_drawdown_threshold,
            take_profit_sell_ratio=strategy.params.take_profit_sell_ratio,
            enable_dip_buy=strategy.params.enable_dip_buy,
            dip_buy_tier1_threshold=strategy.params.dip_buy_tier1_threshold,
            dip_buy_tier1_amount=strategy.params.dip_buy_tier1_amount,
            dip_buy_tier2_threshold=strategy.params.dip_buy_tier2_threshold,
            dip_buy_tier2_amount=strategy.params.dip_buy_tier2_amount,
            dip_buy_tier3_threshold=strategy.params.dip_buy_tier3_threshold,
            dip_buy_tier3_amount=strategy.params.dip_buy_tier3_amount,
            enable_yield_boost=strategy.params.enable_yield_boost,
            yield_boost_trigger=strategy.params.yield_boost_trigger,
            yield_boost_recover=strategy.params.yield_boost_recover,
            yield_boost_amount=strategy.params.yield_boost_amount
        )

        backtest_result = tester.single_fund(config)

        if backtest_result:
            backtest_result.strategy_params = {
                'fund_code': stock.code,
                'fund_name': stock.name,
                'start_date': start_date,
                'end_date': end_date,
                'strategy_id': strategy.id,
                'strategy_name': strategy.name,
                'frequency': strategy.params.frequency,
            }

            rm = ReportManager()
            report_id = rm.save_report(backtest_result)

            result.status = StockStatus.COMPLETED
            result.return_rate = backtest_result.return_rate
            result.annual_return = backtest_result.annual_return
            result.max_drawdown = backtest_result.max_drawdown
            result.report_id = report_id
        else:
            result.status = StockStatus.FAILED
            result.error = "获取数据失败"

    except Exception as e:
        result.status = StockStatus.FAILED
        result.error = str(e)

    task.results[key] = result
    tm.update_task(task)


def render_task_manager():
    """渲染任务管理页面"""
    st.markdown('<div class="section-header">📊 自动回测任务</div>', unsafe_allow_html=True)

    wm = WatchlistManager()
    sm = StrategyManager()
    tm = TaskManager()

    col_left, col_right = st.columns([1, 1])

    with col_left:
        st.subheader("📝 选择股票")

        watchlists = wm.list_watchlists()
        watchlist_options = {wl.name: wl for wl in watchlists}
        selected_wl_name = st.selectbox("从自选股选择", ["-- 不选择 --"] + list(watchlist_options.keys()))

        selected_stocks = []
        if selected_wl_name != "-- 不选择 --":
            selected_wl = watchlist_options[selected_wl_name]
            for s in selected_wl.stocks:
                selected_stocks.append(s)

        col1, col2 = st.columns([3, 1])
        with col1:
            custom_codes = st.text_input("或直接输入股票代码（逗号分隔）", placeholder="510300,159915,510050")
        with col2:
            if custom_codes:
                codes = [c.strip() for c in custom_codes.split(",") if c.strip()]
                for code in codes:
                    if not any(s.code == code for s in selected_stocks):
                        selected_stocks.append(StockInfo(code=code, name=code))

        if selected_stocks:
            st.write(f"已选择 **{len(selected_stocks)}** 只股票:")
            for s in selected_stocks[:5]:
                st.write(f"- {s.code} {s.name}")
            if len(selected_stocks) > 5:
                st.write(f"... 还有 {len(selected_stocks) - 5} 只")

    with col_right:
        st.subheader("🎯 选择策略")

        all_strategies = sm.list_strategies()
        strategy_options = {s.id: s for s in all_strategies}

        selected_strategy_ids = st.multiselect(
            "选择策略（可多选）",
            options=list(strategy_options.keys()),
            format_func=lambda x: f"{strategy_options[x].name} ({strategy_options[x].params.get_summary()})",
            default=[s.id for s in all_strategies[:2]] if len(all_strategies) >= 2 else []
        )

    st.markdown("---")

    col_date1, col_date2, col_source = st.columns(3)
    from datetime import date
    with col_date1:
        start_date = st.date_input("开始日期", value=date(2022, 1, 1))
    with col_date2:
        end_date = st.date_input("结束日期", value=date(2024, 12, 31))
    with col_source:
        data_source = st.selectbox("数据源", ["akshare", "tushare"])

    if not selected_stocks:
        st.warning("请先选择股票")
        return

    if not selected_strategy_ids:
        st.warning("请先选择策略")
        return

    total_backtests = len(selected_stocks) * len(selected_strategy_ids)

    st.info(f"📊 将执行 **{len(selected_stocks)}** 只股票 × **{len(selected_strategy_ids)}** 个策略 = **{total_backtests}** 个回测")

    col_btn1, col_btn2 = st.columns([1, 1])

    with col_btn1:
        task_name = st.text_input("任务名称（可选）", placeholder="留空自动生成")

    with col_btn2:
        pass

    if st.button("▶️ 开始回测", type="primary", width='stretch'):
        if not task_name:
            task_name = f"回测_{datetime.now().strftime('%m%d_%H%M')}"

        task = tm.create_task(
            name=task_name,
            stock_codes=[s.code for s in selected_stocks],
            strategy_ids=selected_strategy_ids,
            start_date=str(start_date),
            end_date=str(end_date)
        )

        task.status = TaskStatus.RUNNING
        task.started_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        tm.update_task(task)

        st.session_state['current_task_id'] = task.id
        st.session_state['task_running'] = True
        st.rerun()

    if st.session_state.get('task_running') and st.session_state.get('current_task_id'):
        render_task_progress(
            tm, wm, sm,
            st.session_state['current_task_id'],
            str(start_date), str(end_date),
            data_source
        )


def render_task_progress(tm: TaskManager, wm: WatchlistManager, sm: StrategyManager,
                         task_id: str, start_date: str, end_date: str, data_source: str):
    """渲染任务进度"""
    task = tm.get_task(task_id)
    if not task:
        st.error("任务不存在")
        return

    st.markdown("---")
    st.subheader(f"📊 任务进度: {task.name}")

    if task.status == TaskStatus.RUNNING:
        completed = sum(1 for r in task.results.values() if r.status == StockStatus.COMPLETED)
        failed = sum(1 for r in task.results.values() if r.status == StockStatus.FAILED)
        total = len(task.stock_codes) * len(task.strategy_ids)

        progress = (completed + failed) / total if total > 0 else 0
        st.progress(progress)

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("已完成", f"{completed}/{total}")
        with col2:
            st.metric("失败", failed)
        with col3:
            if task.started_at:
                elapsed = datetime.now() - datetime.strptime(task.started_at, '%Y-%m-%d %H:%M:%S')
                st.metric("已用时", f"{elapsed.seconds // 60}分{elapsed.seconds % 60}秒")

        strategy_map = {s.id: s for s in sm.list_strategies()}

        with st.expander("📋 查看结果", expanded=True):
            for code in task.stock_codes:
                for sid in task.strategy_ids:
                    key = f"{code}_{sid}"
                    if key in task.results:
                        r = task.results[key]
                        status_icon = {"pending": "⏳", "running": "🔄", "completed": "✅", "failed": "❌"}
                        icon = status_icon.get(r.status.value, "❓")

                        col_code, col_name, col_rate, col_status = st.columns([1, 1, 1, 1])
                        with col_code:
                            st.write(f"**{r.code}**")
                        with col_name:
                            st.write(r.name)
                        with col_rate:
                            if r.return_rate is not None:
                                color = "green" if r.return_rate >= 0 else "red"
                                st.markdown(f":{color}[{r.return_rate:+.2f}%]")
                            else:
                                st.write("-")
                        with col_status:
                            st.write(f"{icon} {r.status.value}")

        if completed + failed < len(task.stock_codes) * len(task.strategy_ids):
            for stock in wm.get_all_stocks():
                if stock.code in task.stock_codes:
                    for sid in task.strategy_ids:
                        key = f"{stock.code}_{sid}"
                        if key not in task.results or task.results[key].status == StockStatus.PENDING:
                            strategy = strategy_map.get(sid)
                            if strategy:
                                st.info(f"正在回测: {stock.code} {stock.name} - {strategy.name}")
                                run_backtest_for_stock(stock, strategy, start_date, end_date, tm, task, data_source)
                                time.sleep(1)
                                st.rerun()
        else:
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            tm.update_task(task)
            st.session_state['task_running'] = False
            st.success("✅ 所有回测已完成!")
            st.rerun()

    elif task.status == TaskStatus.COMPLETED:
        st.success("✅ 任务已完成")

        completed = sum(1 for r in task.results.values() if r.status == StockStatus.COMPLETED)
        failed = sum(1 for r in task.results.values() if r.status == StockStatus.FAILED)
        total = len(task.results)

        col1, col2 = st.columns(2)
        with col1:
            st.metric("成功", completed)
        with col2:
            st.metric("失败", failed)

        with st.expander("📋 查看结果详情", expanded=True):
            strategy_map = {s.id: s for s in sm.list_strategies()}
            data = []
            for code in task.stock_codes:
                for sid in task.strategy_ids:
                    key = f"{code}_{sid}"
                    if key in task.results:
                        r = task.results[key]
                        data.append({
                            "股票": f"{r.code} {r.name}",
                            "策略": strategy_map.get(sid, StrategyTemplate(id=sid, name=sid, group="")).name,
                            "收益率": f"{r.return_rate:+.2f}%" if r.return_rate else "-",
                            "年化收益": f"{r.annual_return:+.2f}%" if r.annual_return else "-",
                            "最大回撤": f"{r.max_drawdown:.2f}%" if r.max_drawdown else "-",
                            "状态": r.status.value
                        })

            if data:
                df = pd.DataFrame(data)
                st.dataframe(df, width='stretch', hide_index=True)
