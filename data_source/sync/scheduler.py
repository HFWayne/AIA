# -*- coding: utf-8 -*-
"""
定时任务调度器
支持每日定时任务和间隔任务
"""

import logging
import threading
from datetime import datetime, timedelta
from typing import Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class Scheduler:
    """定时任务调度器"""

    def __init__(self):
        self._tasks: List[Dict] = []
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

    def add_daily_task(self, task_id: str, run_time: "time", func: Callable, *args, **kwargs):
        """添加每日定时任务

        Args:
            task_id: 任务唯一标识
            run_time: 每日执行时间
            func: 要执行的函数
            *args: 位置参数
            **kwargs: 关键字参数
        """
        with self._lock:
            if any(t['id'] == task_id for t in self._tasks):
                logger.warning(f"任务已存在: {task_id}")
                return
            self._tasks.append({
                'id': task_id,
                'type': 'daily',
                'time': run_time,
                'interval_minutes': None,
                'func': func,
                'args': args,
                'kwargs': kwargs,
                'last_run': None,
                'last_interval_run': None
            })
            logger.info(f"添加每日任务: {task_id}, 时间: {run_time}")

    def add_interval_task(self, task_id: str, interval_minutes: int, func: Callable, *args, **kwargs):
        """添加间隔任务

        Args:
            task_id: 任务唯一标识
            interval_minutes: 间隔分钟数
            func: 要执行的函数
            *args: 位置参数
            **kwargs: 关键字参数
        """
        with self._lock:
            if any(t['id'] == task_id for t in self._tasks):
                logger.warning(f"任务已存在: {task_id}")
                return
            self._tasks.append({
                'id': task_id,
                'type': 'interval',
                'time': None,
                'interval_minutes': interval_minutes,
                'func': func,
                'args': args,
                'kwargs': kwargs,
                'last_run': None,
                'last_interval_run': None
            })
            logger.info(f"添加间隔任务: {task_id}, 间隔: {interval_minutes}分钟")

    def remove_task(self, task_id: str):
        """移除任务"""
        with self._lock:
            self._tasks = [t for t in self._tasks if t['id'] != task_id]
            logger.info(f"移除任务: {task_id}")

    def run_task_now(self, task_id: str):
        """立即执行任务"""
        with self._lock:
            task = next((t for t in self._tasks if t['id'] == task_id), None)
        if task:
            try:
                logger.info(f"手动执行任务: {task_id}")
                task['func'](*task['args'], **task['kwargs'])
                task['last_run'] = datetime.now()
                if task['type'] == 'interval':
                    task['last_interval_run'] = datetime.now()
                logger.info(f"手动任务完成: {task_id}")
            except Exception as e:
                logger.error(f"手动任务执行失败 {task_id}: {e}")

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

            with self._lock:
                tasks_to_run = []
                for task in self._tasks:
                    should_run = False

                    if task['type'] == 'daily':
                        task_time = task['time']
                        last_run = task['last_run']
                        if last_run is None:
                            should_run = True
                        else:
                            last_run_date = last_run.date()
                            if last_run_date < now.date() and current_time >= task_time:
                                should_run = True
                    elif task['type'] == 'interval':
                        interval_minutes = task['interval_minutes']
                        last_run = task.get('last_interval_run') or task['last_run']
                        if last_run is None:
                            should_run = True
                        else:
                            elapsed = now - last_run
                            if elapsed >= timedelta(minutes=interval_minutes):
                                should_run = True

                    if should_run:
                        tasks_to_run.append(task)

            for task in tasks_to_run:
                try:
                    logger.info(f"执行任务: {task['id']}")
                    task['func'](*task['args'], **task['kwargs'])
                    task['last_run'] = now
                    if task['type'] == 'interval':
                        task['last_interval_run'] = now
                    logger.info(f"任务完成: {task['id']}")
                except Exception as e:
                    logger.error(f"任务执行失败 {task['id']}: {e}")

            threading.Event().wait(30)

    def get_status(self) -> dict:
        """获取调度器状态"""
        with self._lock:
            return {
                'running': self._running,
                'tasks': [
                    {
                        'id': t['id'],
                        'type': t['type'],
                        'time': str(t['time']) if t['time'] else None,
                        'interval_minutes': t['interval_minutes'],
                        'last_run': t['last_run'].isoformat() if t['last_run'] else None,
                        'next_run': self._get_next_run(t)
                    }
                    for t in self._tasks
                ]
            }

    def _get_next_run(self, task: dict) -> Optional[str]:
        """计算任务下次执行时间"""
        now = datetime.now()

        if task['type'] == 'daily':
            task_time = task['time']
            last_run = task['last_run']
            if last_run is None or last_run.date() < now.date():
                today_target = now.replace(hour=task_time.hour, minute=task_time.minute, second=0, microsecond=0)
                if now < today_target:
                    return today_target.isoformat()
                else:
                    return (today_target + timedelta(days=1)).isoformat()
            return None

        elif task['type'] == 'interval':
            interval_minutes = task['interval_minutes']
            last_run = task.get('last_interval_run') or task['last_run']
            if last_run is None:
                return now.isoformat()
            next_run = last_run + timedelta(minutes=interval_minutes)
            if next_run < now:
                return now.isoformat()
            return next_run.isoformat()

        return None


_scheduler = None


def get_scheduler() -> Scheduler:
    """获取调度器实例"""
    global _scheduler
    if _scheduler is None:
        _scheduler = Scheduler()
    return _scheduler
