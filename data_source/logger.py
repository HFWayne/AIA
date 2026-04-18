# -*- coding: utf-8 -*-
"""
统一日志配置模块
"""

import logging
import os
from datetime import datetime
from typing import Optional

LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

LOG_FILE = os.path.join(LOG_DIR, f"{datetime.now().strftime('%Y%m%d')}.log")


def setup_logger(
    name: str, level: int = logging.DEBUG, log_file: Optional[str] = None
) -> logging.Logger:
    """配置日志记录器，同时输出到文件和控制台"""
    logger = logging.getLogger(name)
    logger.setLevel(level)

    if logger.handlers:
        return logger

    log_path = log_file or LOG_FILE

    # 文件处理器 - DEBUG级别，记录所有日志
    fh = logging.FileHandler(log_path, mode="a", encoding="utf-8")
    fh.setLevel(logging.DEBUG)

    # 终端处理器 - INFO级别
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)

    # 格式化
    fmt = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    formatter = logging.Formatter(fmt)
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)

    logger.addHandler(fh)
    logger.addHandler(ch)

    return logger


def get_logger(name: str) -> logging.Logger:
    """获取已配置的日志记录器"""
    return logging.getLogger(name)


def log_result(name: str, result) -> None:
    """打印回测结果的详细日志"""
    logger = get_logger(name)
    logger.info("=" * 50)
    logger.info(f"回测结果:")
    logger.info(f"  total_invested: {result.total_invested}")
    logger.info(f"  final_value: {result.final_value}")
    logger.info(f"  total_return: {result.total_return}")
    logger.info(f"  return_rate: {result.return_rate}%")
    logger.info(f"  annual_return: {result.annual_return}%")
    logger.info(f"  max_drawdown: {result.max_drawdown}%")
    logger.info(f"  investment_count: {result.investment_count}")
    logger.info(f"  stop_loss_count: {result.stop_loss_count}")
    logger.info(f"  take_profit_count: {result.take_profit_count}")
    logger.info("=" * 50)


def log_config(name: str, config) -> None:
    """打印配置参数的详细日志"""
    logger = get_logger(name)
    logger.info("=" * 50)
    logger.info(f"回测配置:")
    logger.info(f"  fund_code: {config.fund_code}")
    logger.info(f"  fund_name: {config.fund_name}")
    logger.info(f"  start_date: {config.start_date}")
    logger.info(f"  end_date: {config.end_date}")
    logger.info(f"  investment_amount: {config.investment_amount}")
    logger.info(f"  frequency: {config.frequency}")
    logger.info(f"  day_of_month: {config.day_of_month}")
    logger.info(f"  data_source: {config.data_source}")
    logger.info("=" * 50)
