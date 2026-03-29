# -*- coding: utf-8 -*-
"""
策略模板管理器 (数据库 + Redis 缓存)
"""

import json
import uuid
import logging
from dataclasses import dataclass, asdict, field
from datetime import datetime
from typing import Optional, List, Dict

from data_source.db.connection import get_db_session
from data_source.db.models import StrategyTemplateModel
from data_source.cache import get_cache
from backtest.cache_keys import CacheKeys, CacheTTL

logger = logging.getLogger(__name__)


@dataclass
class StrategyParams:
    """策略参数"""
    frequency: str = "monthly"
    day_of_month: int = 1
    day_of_week: int = 0
    investment_amount: float = 500.0
    enable_stop_loss: bool = False
    stop_loss_rate: float = 0.10
    stop_loss_sell_ratio: float = 1.0
    enable_take_profit: bool = False
    take_profit_rate: float = 0.20
    max_drawdown_threshold: float = 0.10
    take_profit_sell_ratio: float = 0.5
    enable_dip_buy: bool = False
    dip_buy_tier1_threshold: float = -0.03
    dip_buy_tier1_amount: float = 1000.0
    dip_buy_tier2_threshold: float = -0.05
    dip_buy_tier2_amount: float = 1000.0
    dip_buy_tier3_threshold: float = -0.07
    dip_buy_tier3_amount: float = 1000.0
    enable_yield_boost: bool = False
    yield_boost_trigger: float = -0.20
    yield_boost_recover: float = -0.10
    yield_boost_amount: float = 500.0

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> 'StrategyParams':
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

    def get_summary(self) -> str:
        """获取参数摘要"""
        parts = []
        freq_map = {"monthly": "月", "weekly": "周", "daily": "日"}
        parts.append(f"{freq_map.get(self.frequency, self.frequency)}定投{self.investment_amount:.0f}元")
        if self.enable_stop_loss:
            parts.append(f"止损{int(self.stop_loss_rate*100)}%")
        if self.enable_take_profit:
            parts.append(f"止盈{int(self.take_profit_rate*100)}%")
        if self.enable_dip_buy:
            parts.append("补仓")
        if self.enable_yield_boost:
            parts.append("收益增强")
        return " ".join(parts) if parts else "基础定投"


@dataclass
class StrategyTemplate:
    """策略模板"""
    id: str
    name: str
    group: str
    description: str = ""
    params: StrategyParams = field(default_factory=StrategyParams)
    color: str = "#1f77b4"
    is_default: bool = False
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'name': self.name,
            'group': self.group,
            'description': self.description,
            'params': self.params.to_dict(),
            'color': self.color,
            'is_default': self.is_default,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'StrategyTemplate':
        params = StrategyParams.from_dict(data.get('params', {}))
        return cls(
            id=data['id'],
            name=data['name'],
            group=data.get('group', ''),
            description=data.get('description', ''),
            params=params,
            color=data.get('color', '#1f77b4'),
            is_default=data.get('is_default', False),
            created_at=data.get('created_at', ''),
            updated_at=data.get('updated_at', '')
        )


class StrategyManager:
    """策略管理器 (DB + Redis)"""

    GROUPS = ["我的策略", "保守型", "激进型", "增强型"]

    def __init__(self):
        self.cache = get_cache()
        self._cache_ttl = CacheTTL.STRATEGY_LIST
        self._init_default_strategies()

    def _invalidate_cache(self):
        """清除缓存"""
        self.cache.delete(CacheKeys.strategy_list())

    def _init_default_strategies(self):
        """初始化默认策略模板"""
        with get_db_session() as session:
            count = session.query(StrategyTemplateModel).count()
            if count == 0:
                now = datetime.now()
                default_strategies = [
                    {
                        "id": "st_basic",
                        "name": "基础定投",
                        "group": "保守型",
                        "description": "最基础的定投策略，无风控",
                        "params": {
                            "frequency": "monthly",
                            "day_of_month": 1,
                            "investment_amount": 500.0,
                            "enable_stop_loss": False,
                            "enable_take_profit": False,
                            "enable_dip_buy": False,
                            "enable_yield_boost": False
                        },
                        "color": "#2ecc71",
                        "is_default": True
                    },
                    {
                        "id": "st_wj",
                        "name": "稳健定投",
                        "group": "保守型",
                        "description": "带止损止盈的稳健策略",
                        "params": {
                            "frequency": "monthly",
                            "day_of_month": 1,
                            "investment_amount": 500.0,
                            "enable_stop_loss": True,
                            "stop_loss_rate": 0.10,
                            "stop_loss_sell_ratio": 1.0,
                            "enable_take_profit": True,
                            "take_profit_rate": 0.20,
                            "max_drawdown_threshold": 0.10,
                            "take_profit_sell_ratio": 0.5,
                            "enable_dip_buy": False,
                            "enable_yield_boost": False
                        },
                        "color": "#3498db",
                        "is_default": True
                    },
                    {
                        "id": "st_consv",
                        "name": "保守定投",
                        "group": "保守型",
                        "description": "周定投+补仓的保守策略",
                        "params": {
                            "frequency": "weekly",
                            "day_of_week": 0,
                            "investment_amount": 200.0,
                            "enable_stop_loss": True,
                            "stop_loss_rate": 0.15,
                            "stop_loss_sell_ratio": 1.0,
                            "enable_take_profit": True,
                            "take_profit_rate": 0.30,
                            "max_drawdown_threshold": 0.15,
                            "take_profit_sell_ratio": 0.5,
                            "enable_dip_buy": True,
                            "dip_buy_tier1_threshold": -0.05,
                            "dip_buy_tier1_amount": 400.0,
                            "enable_yield_boost": False
                        },
                        "color": "#9b59b6",
                        "is_default": True
                    },
                    {
                        "id": "st_agg",
                        "name": "积极定投",
                        "group": "激进型",
                        "description": "大额月定投+严格止损止盈",
                        "params": {
                            "frequency": "monthly",
                            "day_of_month": 1,
                            "investment_amount": 1000.0,
                            "enable_stop_loss": True,
                            "stop_loss_rate": 0.08,
                            "stop_loss_sell_ratio": 1.0,
                            "enable_take_profit": True,
                            "take_profit_rate": 0.15,
                            "max_drawdown_threshold": 0.08,
                            "take_profit_sell_ratio": 0.5,
                            "enable_dip_buy": True,
                            "dip_buy_tier1_threshold": -0.03,
                            "dip_buy_tier1_amount": 2000.0,
                            "dip_buy_tier2_threshold": -0.07,
                            "dip_buy_tier2_amount": 3000.0,
                            "enable_yield_boost": False
                        },
                        "color": "#e74c3c",
                        "is_default": True
                    },
                    {
                        "id": "st_hr",
                        "name": "高风险定投",
                        "group": "激进型",
                        "description": "周定投+强化补仓",
                        "params": {
                            "frequency": "weekly",
                            "day_of_week": 0,
                            "investment_amount": 500.0,
                            "enable_stop_loss": True,
                            "stop_loss_rate": 0.05,
                            "stop_loss_sell_ratio": 1.0,
                            "enable_take_profit": True,
                            "take_profit_rate": 0.10,
                            "max_drawdown_threshold": 0.05,
                            "take_profit_sell_ratio": 0.5,
                            "enable_dip_buy": True,
                            "dip_buy_tier1_threshold": -0.03,
                            "dip_buy_tier1_amount": 1000.0,
                            "dip_buy_tier2_threshold": -0.05,
                            "dip_buy_tier2_amount": 1500.0,
                            "dip_buy_tier3_threshold": -0.07,
                            "dip_buy_tier3_amount": 2000.0,
                            "enable_yield_boost": False
                        },
                        "color": "#f39c12",
                        "is_default": True
                    },
                    {
                        "id": "st_boost",
                        "name": "收益增强",
                        "group": "增强型",
                        "description": "月定投+收益增强策略",
                        "params": {
                            "frequency": "monthly",
                            "day_of_month": 1,
                            "investment_amount": 500.0,
                            "enable_stop_loss": True,
                            "stop_loss_rate": 0.10,
                            "stop_loss_sell_ratio": 1.0,
                            "enable_take_profit": False,
                            "enable_dip_buy": False,
                            "enable_yield_boost": True,
                            "yield_boost_trigger": -0.20,
                            "yield_boost_recover": -0.10,
                            "yield_boost_amount": 500.0
                        },
                        "color": "#1abc9c",
                        "is_default": True
                    },
                ]

                for s in default_strategies:
                    strategy = StrategyTemplateModel(
                        id=s['id'],
                        name=s['name'],
                        group_name=s['group'],
                        description=s['description'],
                        params=json.dumps(s['params'], ensure_ascii=False),
                        color=s['color'],
                        is_default=s['is_default'],
                        created_at=now,
                        updated_at=now
                    )
                    session.add(strategy)

                logger.info("默认策略模板初始化完成")

    def list_strategies(self, group: Optional[str] = None) -> List[StrategyTemplate]:
        """获取策略模板列表"""
        cache_key = CacheKeys.strategy_list()
        cached = self.cache.get(cache_key)
        if cached:
            strategies = [StrategyTemplate.from_dict(s) for s in cached]
        else:
            with get_db_session() as session:
                query = session.query(StrategyTemplateModel)
                db_strategies = query.all()
                strategies = [StrategyTemplate.from_dict(s.to_dict()) for s in db_strategies]
            self.cache.set(cache_key, [s.to_dict() for s in strategies], expire=self._cache_ttl)

        if group:
            strategies = [s for s in strategies if s.group == group]
        return strategies

    def get_strategy(self, strategy_id: str) -> Optional[StrategyTemplate]:
        """获取指定策略模板"""
        with get_db_session() as session:
            db_strategy = session.query(StrategyTemplateModel).filter(
                StrategyTemplateModel.id == strategy_id
            ).first()
            if db_strategy:
                return StrategyTemplate.from_dict(db_strategy.to_dict())
        return None

    def create_strategy(self, name: str, group: str, description: str = "",
                       params: StrategyParams = None, color: str = "#1f77b4") -> StrategyTemplate:
        """创建新的策略模板"""
        now = datetime.now()
        strategy_id = str(uuid.uuid4())[:8]

        with get_db_session() as session:
            strategy = StrategyTemplateModel(
                id=strategy_id,
                name=name,
                group_name=group,
                description=description,
                params=json.dumps((params or StrategyParams()).to_dict(), ensure_ascii=False),
                color=color,
                is_default=False,
                created_at=now,
                updated_at=now
            )
            session.add(strategy)

        self._invalidate_cache()
        return StrategyTemplate(
            id=strategy_id,
            name=name,
            group=group,
            description=description,
            params=params or StrategyParams(),
            color=color,
            is_default=False,
            created_at=now.strftime('%Y-%m-%d %H:%M:%S'),
            updated_at=now.strftime('%Y-%m-%d %H:%M:%S')
        )

    def update_strategy(self, strategy_id: str, **kwargs) -> Optional[StrategyTemplate]:
        """更新策略模板"""
        with get_db_session() as session:
            db_strategy = session.query(StrategyTemplateModel).filter(
                StrategyTemplateModel.id == strategy_id
            ).first()

            if db_strategy:
                if 'name' in kwargs:
                    db_strategy.name = kwargs['name']
                if 'group' in kwargs:
                    db_strategy.group_name = kwargs['group']
                if 'description' in kwargs:
                    db_strategy.description = kwargs['description']
                if 'color' in kwargs:
                    db_strategy.color = kwargs['color']
                if 'params' in kwargs:
                    if isinstance(kwargs['params'], dict):
                        db_strategy.params = json.dumps(kwargs['params'], ensure_ascii=False)
                    else:
                        db_strategy.params = json.dumps(kwargs['params'].to_dict(), ensure_ascii=False)
                db_strategy.updated_at = datetime.now()

                self._invalidate_cache()
                return StrategyTemplate.from_dict(db_strategy.to_dict())
        return None

    def delete_strategy(self, strategy_id: str) -> bool:
        """删除策略模板"""
        with get_db_session() as session:
            db_strategy = session.query(StrategyTemplateModel).filter(
                StrategyTemplateModel.id == strategy_id
            ).first()
            if db_strategy:
                session.delete(db_strategy)
                self._invalidate_cache()
                return True
        return False

    def get_groups(self) -> List[str]:
        """获取所有策略分组"""
        strategies = self.list_strategies()
        groups = set(s.group for s in strategies)
        return sorted(list(groups))
