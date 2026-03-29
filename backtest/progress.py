# -*- coding: utf-8 -*-
"""
回测进度追踪模块

功能:
- 实时进度回调
- Streamlit 进度条支持
- 多任务并发进度追踪
"""

import logging
import time
from typing import Optional, Callable, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime
from threading import Lock

logger = logging.getLogger(__name__)


@dataclass
class BacktestProgress:
    """回测进度数据"""
    task_id: str
    total_steps: int
    current_step: int = 0
    current_phase: str = ""
    message: str = ""
    start_time: float = field(default_factory=time.time)
    result: Any = None
    error: Optional[str] = None

    @property
    def percent(self) -> float:
        if self.total_steps == 0:
            return 100.0
        return (self.current_step / self.total_steps) * 100

    @property
    def elapsed_seconds(self) -> float:
        return time.time() - self.start_time

    @property
    def eta_seconds(self) -> float:
        if self.current_step == 0:
            return 0
        elapsed = self.elapsed_seconds
        rate = self.current_step / elapsed
        remaining = self.total_steps - self.current_step
        return remaining / rate if rate > 0 else 0

    def __str__(self) -> str:
        return f"[{self.task_id}] {self.current_phase}: {self.current_step}/{self.total_steps} ({self.percent:.1f}%)"


class ProgressTracker:
    """进度追踪器"""

    def __init__(self, task_id: str, total_steps: int):
        self.progress = BacktestProgress(task_id=task_id, total_steps=total_steps)
        self._lock = Lock()
        self._callbacks: list = []

    def add_callback(self, callback: Callable[['BacktestProgress'], None]):
        """添加进度回调函数"""
        self._callbacks.append(callback)

    def update(self, step: int, phase: str = "", message: str = ""):
        """更新进度"""
        with self._lock:
            self.progress.current_step = min(step, self.progress.total_steps)
            if phase:
                self.progress.current_phase = phase
            if message:
                self.progress.message = message

            for callback in self._callbacks:
                try:
                    callback(self.progress)
                except Exception as e:
                    logger.warning(f"进度回调失败: {e}")

    def set_result(self, result: Any):
        """设置结果"""
        with self._lock:
            self.progress.result = result

    def set_error(self, error: str):
        """设置错误"""
        with self._lock:
            self.progress.error = error

    def complete(self):
        """标记完成"""
        self.update(self.progress.total_steps, "完成", "回测已完成")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.set_error(str(exc_val))
        else:
            self.complete()


class MultiTaskProgressTracker:
    """多任务进度追踪器"""

    def __init__(self):
        self._trackers: Dict[str, ProgressTracker] = {}
        self._lock = Lock()

    def create_task(self, task_id: str, total_steps: int) -> ProgressTracker:
        """创建任务追踪器"""
        with self._lock:
            tracker = ProgressTracker(task_id, total_steps)
            self._trackers[task_id] = tracker
            return tracker

    def get_tracker(self, task_id: str) -> Optional[ProgressTracker]:
        """获取任务追踪器"""
        return self._trackers.get(task_id)

    def get_overall_progress(self) -> float:
        """获取整体进度"""
        if not self._trackers:
            return 0.0

        total = sum(t.progress.total_steps for t in self._trackers.values())
        completed = sum(t.progress.current_step for t in self._trackers.values())

        return (completed / total * 100) if total > 0 else 0.0

    def get_summary(self) -> Dict[str, Any]:
        """获取进度摘要"""
        return {
            "total_tasks": len(self._trackers),
            "overall_progress": self.get_overall_progress(),
            "tasks": {
                task_id: {
                    "phase": tracker.progress.current_phase,
                    "percent": tracker.progress.percent,
                    "message": tracker.progress.message,
                    "elapsed": tracker.progress.elapsed_seconds,
                }
                for task_id, tracker in self._trackers.items()
            }
        }


def create_steamlit_callback(st, key: str = "backtest_progress"):
    """创建 Streamlit 进度条回调

    Usage:
        import streamlit as st
        from backtest.progress import create_steamlit_callback

        progress_bar = st.progress(0)
        status_text = st.empty()

        def on_progress(progress):
            progress_bar.progress(progress.percent / 100)
            status_text.text(str(progress))

        callback = create_steamlit_callback(st, "my_progress")
    """
    def callback(progress: BacktestProgress):
        try:
            if hasattr(progress, '_st_progress_bar') and progress._st_progress_bar:
                progress._st_progress_bar.progress(min(progress.percent / 100, 1.0))
            if hasattr(progress, '_st_status') and progress._st_status:
                progress._st_status.text(str(progress))
        except Exception:
            pass

    return callback


_global_tracker = None


def get_global_tracker() -> MultiTaskProgressTracker:
    """获取全局进度追踪器"""
    global _global_tracker
    if _global_tracker is None:
        _global_tracker = MultiTaskProgressTracker()
    return _global_tracker
