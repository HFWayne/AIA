# -*- coding: utf-8 -*-
"""
数据库连接管理
"""

import logging
from contextlib import contextmanager
from typing import Optional, Generator

import pymysql
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool

from data_source.config import MYSQL_CONFIG, ENABLE_MYSQL
from data_source.db.models import Base

logger = logging.getLogger(__name__)

_engine = None
_SessionLocal = None


def _check_enabled():
    """检查 MySQL 是否启用"""
    if not ENABLE_MYSQL:
        raise RuntimeError("MySQL is disabled. Set ENABLE_MYSQL=True in config.py to enable.")


def get_engine():
    """获取数据库引擎（单例）"""
    global _engine
    if _engine is None:
        _check_enabled()
        connection_string = (
            f"mysql+pymysql://{MYSQL_CONFIG['user']}:{MYSQL_CONFIG['password']}"
            f"@{MYSQL_CONFIG['host']}:{MYSQL_CONFIG['port']}/{MYSQL_CONFIG['database']}"
            f"?charset={MYSQL_CONFIG['charset']}"
        )
        _engine = create_engine(
            connection_string,
            poolclass=QueuePool,
            pool_size=MYSQL_CONFIG.get("pool_size", 10),
            max_overflow=MYSQL_CONFIG.get("max_overflow", 20),
            pool_recycle=MYSQL_CONFIG.get("pool_recycle", 3600),
            pool_pre_ping=True,
            echo=False,
        )
        logger.info(f"数据库引擎已创建: {MYSQL_CONFIG['host']}:{MYSQL_CONFIG['port']}/{MYSQL_CONFIG['database']}")
    return _engine


def get_session_factory():
    """获取 Session 工厂（单例）"""
    global _SessionLocal
    if _SessionLocal is None:
        engine = get_engine()
        _SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    return _SessionLocal


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """获取数据库会话的上下文管理器"""
    _check_enabled()
    SessionLocal = get_session_factory()
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"数据库操作失败: {e}")
        raise
    finally:
        session.close()


def init_database(drop_existing: bool = False):
    """初始化数据库表结构"""
    engine = get_engine()
    
    if drop_existing:
        logger.warning("删除所有表...")
        Base.metadata.drop_all(engine)
    
    logger.info("创建所有表...")
    Base.metadata.create_all(engine)
    logger.info("数据库初始化完成")


def check_connection() -> bool:
    """检查数据库连接"""
    if not ENABLE_MYSQL:
        logger.warning("MySQL is disabled")
        return False
    try:
        engine = get_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error(f"数据库连接失败: {e}")
        return False


def create_database_if_not_exists():
    """创建数据库（如果不存在）"""
    try:
        conn = pymysql.connect(
            host=MYSQL_CONFIG['host'],
            port=MYSQL_CONFIG['port'],
            user=MYSQL_CONFIG['user'],
            password=MYSQL_CONFIG['password'],
            charset=MYSQL_CONFIG['charset'],
        )
        cursor = conn.cursor()
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {MYSQL_CONFIG['database']} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        cursor.close()
        conn.close()
        logger.info(f"数据库 {MYSQL_CONFIG['database']} 已就绪")
    except Exception as e:
        logger.error(f"创建数据库失败: {e}")
        raise
