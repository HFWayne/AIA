# -*- coding: utf-8 -*-
"""
定时任务调度器
"""

import logging
import threading
from datetime import datetime, time
from typing import Callable, Optional

logger = logging.getLogger(__name__)


class Scheduler:
    """简单的定时任务调度器"""

    def __init__(self):
        self._tasks = []
        self._running = False
        self._thread = None

    def add_daily_task(self, task_id: str, run_time: time, func: Callable, *args, **kwargs):
        """添加每日定时任务"""
        self._tasks.append({
            'id': task_id,
            'time': run_time,
            'func': func,
            'args': args,
            'kwargs': kwargs,
            'last_run': None
        })
        logger.info(f"添加每日任务: {task_id}, 时间: {run_time}")

    def start(self):
        """启动调度器"""
        if self._running:
            logger.warning("调度器已在运行")
            return

        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        logger.info("调度器已启动")

    def stop(self):
        """停止调度器"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("调度器已停止")

    def _run_loop(self):
        """调度循环"""
        while self._running:
            now = datetime.now()
            current_time = now.time()

            for task in self._tasks:
                task_time = task['time']
                last_run = task['last_run']

                should_run = False
                if last_run is None:
                    should_run = True
                else:
                    last_run_date = last_run.date()
                    if last_run_date < now.date() and current_time >= task_time:
                        should_run = True

                if should_run:
                    try:
                        logger.info(f"执行任务: {task['id']}")
                        task['func'](*task['args'], **task['kwargs'])
                        task['last_run'] = now
                        logger.info(f"任务完成: {task['id']}")
                    except Exception as e:
                        logger.error(f"任务执行失败 {task['id']}: {e}")

            threading.Event().wait(30)

    def get_status(self) -> dict:
        """获取调度器状态"""
        return {
            'running': self._running,
            'tasks': [
                {
                    'id': t['id'],
                    'time': str(t['time']),
                    'last_run': t['last_run'].isoformat() if t['last_run'] else None
                }
                for t in self._tasks
            ]
        }


_scheduler = None


def get_scheduler() -> Scheduler:
    """获取调度器实例"""
    global _scheduler
    if _scheduler is None:
        _scheduler = Scheduler()
    return _scheduler
