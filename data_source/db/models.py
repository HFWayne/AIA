# -*- coding: utf-8 -*-
"""
SQLAlchemy 数据模型
"""

import json
from datetime import datetime
from sqlalchemy import (
    Column, Integer, BigInteger, String, Date, DateTime,
    DECIMAL, Text, Index, UniqueConstraint, ForeignKey, Boolean
)
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class Stock(Base):
    """股票基本信息表"""
    __tablename__ = "stocks"

    code = Column(String(10), primary_key=True, comment="股票代码")
    name = Column(String(100), nullable=False, comment="股票名称")
    market = Column(String(10), nullable=False, comment="市场: SH/SZ")
    industry = Column(String(50), comment="所属行业")
    list_date = Column(Date, comment="上市日期")
    delist_date = Column(Date, comment="退市日期")
    stock_type = Column(String(20), comment="类型: ETF/股票/基金")
    full_code = Column(String(20), comment="完整代码如 600036.SH")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    def to_dict(self):
        return {
            "code": self.code,
            "name": self.name,
            "market": self.market,
            "industry": self.industry,
            "list_date": str(self.list_date) if self.list_date else None,
            "stock_type": self.stock_type,
        }


class DailyKlineAkShare(Base):
    """AkShare 日线行情表"""
    __tablename__ = "daily_kline_akshare"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    code = Column(String(10), nullable=False, comment="股票代码")
    trade_date = Column(Date, nullable=False, comment="交易日期")
    open = Column(DECIMAL(10, 3), comment="开盘价")
    high = Column(DECIMAL(10, 3), comment="最高价")
    low = Column(DECIMAL(10, 3), comment="最低价")
    close = Column(DECIMAL(10, 3), comment="收盘价")
    volume = Column(DECIMAL(20, 2), comment="成交量")
    amount = Column(DECIMAL(20, 2), comment="成交额")
    adj_close = Column(DECIMAL(10, 3), comment="复权收盘价")
    turn = Column(DECIMAL(10, 4), comment="换手率")
    pct_chg = Column(DECIMAL(10, 4), comment="涨跌幅")
    created_at = Column(DateTime, default=datetime.now)

    __table_args__ = (
        UniqueConstraint("code", "trade_date", name="uk_akshare_code_date"),
        Index("idx_akshare_trade_date", "trade_date"),
        Index("idx_akshare_code", "code"),
    )

    def to_dict(self):
        return {
            "code": self.code,
            "date": str(self.trade_date) if self.trade_date else None,
            "open": float(self.open) if self.open else 0,
            "high": float(self.high) if self.high else 0,
            "low": float(self.low) if self.low else 0,
            "close": float(self.close) if self.close else 0,
            "volume": float(self.volume) if self.volume else 0,
            "adj_close": float(self.adj_close) if self.adj_close else 0,
        }


class DailyKlineTushare(Base):
    """Tushare 日线行情表"""
    __tablename__ = "daily_kline_tushare"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    code = Column(String(10), nullable=False, comment="股票代码")
    trade_date = Column(Date, nullable=False, comment="交易日期")
    open = Column(DECIMAL(10, 3), comment="开盘价")
    high = Column(DECIMAL(10, 3), comment="最高价")
    low = Column(DECIMAL(10, 3), comment="最低价")
    close = Column(DECIMAL(10, 3), comment="收盘价")
    volume = Column(DECIMAL(20, 2), comment="成交量")
    amount = Column(DECIMAL(20, 2), comment="成交额")
    adj_close = Column(DECIMAL(10, 3), comment="复权收盘价")
    turn = Column(DECIMAL(10, 4), comment="换手率")
    pct_chg = Column(DECIMAL(10, 4), comment="涨跌幅")
    created_at = Column(DateTime, default=datetime.now)

    __table_args__ = (
        UniqueConstraint("code", "trade_date", name="uk_tushare_code_date"),
        Index("idx_tushare_trade_date", "trade_date"),
        Index("idx_tushare_code", "code"),
    )

    def to_dict(self):
        return {
            "code": self.code,
            "date": str(self.trade_date) if self.trade_date else None,
            "open": float(self.open) if self.open else 0,
            "high": float(self.high) if self.high else 0,
            "low": float(self.low) if self.low else 0,
            "close": float(self.close) if self.close else 0,
            "volume": float(self.volume) if self.volume else 0,
            "adj_close": float(self.adj_close) if self.adj_close else 0,
        }


class Income(Base):
    """利润表"""
    __tablename__ = "income"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    code = Column(String(10), nullable=False, comment="股票代码")
    ann_date = Column(Date, comment="公告日期")
    end_date = Column(Date, nullable=False, comment="报告期")
    report_type = Column(Integer, comment="报告类型: 1-年报 2-季报 3-半年报 4-三季报")
    total_revenue = Column(DECIMAL(20, 2), comment="营业总收入")
    oper_profit = Column(DECIMAL(20, 2), comment="营业利润")
    net_profit = Column(DECIMAL(20, 2), comment="净利润")
    total_revenue_yoy = Column(DECIMAL(10, 4), comment="营收同比")
    net_profit_yoy = Column(DECIMAL(10, 4), comment="净利润同比")
    created_at = Column(DateTime, default=datetime.now)

    __table_args__ = (
        UniqueConstraint("code", "end_date", "report_type", name="uk_code_end_report"),
        Index("idx_end_date", "end_date"),
    )


class FinaIndicator(Base):
    """主要财务指标表"""
    __tablename__ = "fina_indicator"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    code = Column(String(10), nullable=False, comment="股票代码")
    ann_date = Column(Date, comment="公告日期")
    end_date = Column(Date, nullable=False, comment="报告期")
    roe = Column(DECIMAL(10, 4), comment="净资产收益率")
    net_profit_margin = Column(DECIMAL(10, 4), comment="净利率")
    gross_profit_margin = Column(DECIMAL(10, 4), comment="毛利率")
    debt_to_assets = Column(DECIMAL(10, 4), comment="资产负债率")
    current_ratio = Column(DECIMAL(10, 4), comment="流动比率")
    quick_ratio = Column(DECIMAL(10, 4), comment="速动比率")
    pe_ttm = Column(DECIMAL(12, 4), comment="市盈率TTM")
    pb = Column(DECIMAL(10, 4), comment="市净率")
    ps_ttm = Column(DECIMAL(10, 4), comment="市销率TTM")
    created_at = Column(DateTime, default=datetime.now)

    __table_args__ = (
        UniqueConstraint("code", "end_date", name="uk_code_end_fina"),
        Index("idx_ann_date", "ann_date"),
    )


class SyncLog(Base):
    """数据同步记录表"""
    __tablename__ = "sync_log"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    table_name = Column(String(50), nullable=False, comment="表名")
    source = Column(String(20), comment="数据源: akshare/tushare")
    code = Column(String(10), comment="股票代码")
    start_date = Column(Date, comment="开始日期")
    end_date = Column(Date, comment="结束日期")
    status = Column(String(20), default="running", comment="状态: running/success/failed")
    records = Column(Integer, default=0, comment="同步记录数")
    error_msg = Column(Text, comment="错误信息")
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    __table_args__ = (
        Index("idx_status", "status"),
        Index("idx_created_at", "created_at"),
    )


class Report(Base):
    """回测报告表"""
    __tablename__ = "reports"

    id = Column(String(8), primary_key=True, comment="报告ID")
    name = Column(String(200), nullable=False, comment="报告名称")
    created_at = Column(DateTime, nullable=False, comment="创建时间")
    fund_code = Column(String(10), nullable=False, comment="基金代码")
    fund_name = Column(String(100), comment="基金名称")
    start_date = Column(Date, nullable=False, comment="开始日期")
    end_date = Column(Date, nullable=False, comment="结束日期")
    investment_amount = Column(DECIMAL(12, 2), comment="每次投入金额")
    frequency = Column(String(20), comment="频率")
    strategy_params = Column(Text, comment="策略参数JSON")
    result = Column(Text, comment="回测结果JSON")
    trades = Column(Text, comment="交易记录JSON")

    __table_args__ = (
        Index("idx_fund_code", "fund_code"),
        Index("idx_created_at", "created_at"),
    )

    def to_dict(self):
        data = {
            "id": self.id,
            "name": self.name,
            "created_at": str(self.created_at) if self.created_at else None,
            "fund_code": self.fund_code,
            "fund_name": self.fund_name,
            "start_date": str(self.start_date) if self.start_date else None,
            "end_date": str(self.end_date) if self.end_date else None,
            "investment_amount": float(self.investment_amount) if self.investment_amount else 0,
            "frequency": self.frequency,
        }
        if self.strategy_params:
            data["strategy_params"] = json.loads(self.strategy_params)
        if self.result:
            data["result"] = json.loads(self.result)
        if self.trades:
            data["trades"] = json.loads(self.trades)
        return data


class Watchlist(Base):
    """自选股列表表"""
    __tablename__ = "watchlists"

    id = Column(String(8), primary_key=True, comment="列表ID")
    name = Column(String(100), nullable=False, comment="列表名称")
    description = Column(String(500), comment="描述")
    created_at = Column(DateTime, nullable=False, comment="创建时间")
    updated_at = Column(DateTime, nullable=False, comment="更新时间")

    __table_args__ = (
        Index("idx_created_at", "created_at"),
    )


class WatchlistStock(Base):
    """自选股列表中的股票"""
    __tablename__ = "watchlist_stocks"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    watchlist_id = Column(String(8), ForeignKey("watchlists.id", ondelete="CASCADE"), nullable=False)
    code = Column(String(10), nullable=False, comment="股票代码")
    name = Column(String(100), comment="股票名称")
    market = Column(String(20), default="A股", comment="市场")
    type = Column(String(20), default="ETF", comment="类型")
    notes = Column(String(500), comment="备注")
    tags = Column(Text, comment="标签JSON")

    __table_args__ = (
        UniqueConstraint("watchlist_id", "code", name="uk_watchlist_code"),
        Index("idx_watchlist_id", "watchlist_id"),
    )

    def to_dict(self):
        return {
            "code": self.code,
            "name": self.name,
            "market": self.market,
            "type": self.type,
            "notes": self.notes,
            "tags": json.loads(self.tags) if self.tags else [],
        }


class StrategyTemplateModel(Base):
    """策略模板表"""
    __tablename__ = "strategy_templates"

    id = Column(String(8), primary_key=True, comment="策略ID")
    name = Column(String(100), nullable=False, comment="策略名称")
    group_name = Column(String(50), nullable=False, comment="分组")
    description = Column(String(500), comment="描述")
    params = Column(Text, comment="策略参数JSON")
    color = Column(String(20), default="#1f77b4", comment="颜色")
    is_default = Column(Boolean, default=False, comment="是否默认")
    created_at = Column(DateTime, nullable=False, comment="创建时间")
    updated_at = Column(DateTime, nullable=False, comment="更新时间")

    __table_args__ = (
        Index("idx_group_name", "group_name"),
        Index("idx_is_default", "is_default"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "group": self.group_name,
            "description": self.description,
            "params": json.loads(self.params) if self.params else {},
            "color": self.color,
            "is_default": self.is_default,
            "created_at": str(self.created_at) if self.created_at else None,
            "updated_at": str(self.updated_at) if self.updated_at else None,
        }
