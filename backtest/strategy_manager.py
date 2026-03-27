# -*- coding: utf-8 -*-
"""
策略模板管理器
管理回测策略模板
"""

import json
import uuid
from dataclasses import dataclass, asdict, field
from datetime import datetime
from typing import Optional, List, Dict, Tuple
from pathlib import Path


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
    """策略管理器"""

    GROUPS = ["我的策略", "保守型", "激进型", "增强型"]

    def __init__(self, data_dir: Optional[str] = None):
        if data_dir is None:
            self.data_dir: Path = Path(__file__).parent.parent.parent / "reports"
        else:
            self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.file_path = self.data_dir / "strategies.json"
        self._init_default_strategies()

    def _init_default_strategies(self):
        """初始化默认策略模板"""
        if not self.file_path.exists():
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            default_strategies = [
                StrategyTemplate(
                    id="basic",
                    name="基础定投",
                    group="保守型",
                    description="最基础的定投策略，无风控",
                    params=StrategyParams(
                        frequency="monthly",
                        day_of_month=1,
                        investment_amount=500.0,
                        enable_stop_loss=False,
                        enable_take_profit=False,
                        enable_dip_buy=False,
                        enable_yield_boost=False
                    ),
                    color="#2ecc71",
                    is_default=True,
                    created_at=now,
                    updated_at=now
                ),
                StrategyTemplate(
                    id="steady",
                    name="稳健定投",
                    group="保守型",
                    description="带止损止盈的稳健策略",
                    params=StrategyParams(
                        frequency="monthly",
                        day_of_month=1,
                        investment_amount=500.0,
                        enable_stop_loss=True,
                        stop_loss_rate=0.10,
                        stop_loss_sell_ratio=1.0,
                        enable_take_profit=True,
                        take_profit_rate=0.20,
                        max_drawdown_threshold=0.10,
                        take_profit_sell_ratio=0.5,
                        enable_dip_buy=False,
                        enable_yield_boost=False
                    ),
                    color="#3498db",
                    is_default=True,
                    created_at=now,
                    updated_at=now
                ),
                StrategyTemplate(
                    id="conservative",
                    name="保守定投",
                    group="保守型",
                    description="周定投+补仓的保守策略",
                    params=StrategyParams(
                        frequency="weekly",
                        day_of_week=0,
                        investment_amount=200.0,
                        enable_stop_loss=True,
                        stop_loss_rate=0.15,
                        stop_loss_sell_ratio=1.0,
                        enable_take_profit=True,
                        take_profit_rate=0.30,
                        max_drawdown_threshold=0.15,
                        take_profit_sell_ratio=0.5,
                        enable_dip_buy=True,
                        dip_buy_tier1_threshold=-0.05,
                        dip_buy_tier1_amount=400.0,
                        enable_yield_boost=False
                    ),
                    color="#9b59b6",
                    is_default=True,
                    created_at=now,
                    updated_at=now
                ),
                StrategyTemplate(
                    id="aggressive",
                    name="积极定投",
                    group="激进型",
                    description="大额月定投+严格止损止盈",
                    params=StrategyParams(
                        frequency="monthly",
                        day_of_month=1,
                        investment_amount=1000.0,
                        enable_stop_loss=True,
                        stop_loss_rate=0.08,
                        stop_loss_sell_ratio=1.0,
                        enable_take_profit=True,
                        take_profit_rate=0.15,
                        max_drawdown_threshold=0.08,
                        take_profit_sell_ratio=0.5,
                        enable_dip_buy=True,
                        dip_buy_tier1_threshold=-0.03,
                        dip_buy_tier1_amount=2000.0,
                        dip_buy_tier2_threshold=-0.07,
                        dip_buy_tier2_amount=3000.0,
                        enable_yield_boost=False
                    ),
                    color="#e74c3c",
                    is_default=True,
                    created_at=now,
                    updated_at=now
                ),
                StrategyTemplate(
                    id="high_risk",
                    name="高风险定投",
                    group="激进型",
                    description="周定投+强化补仓",
                    params=StrategyParams(
                        frequency="weekly",
                        day_of_week=0,
                        investment_amount=500.0,
                        enable_stop_loss=True,
                        stop_loss_rate=0.05,
                        stop_loss_sell_ratio=1.0,
                        enable_take_profit=True,
                        take_profit_rate=0.10,
                        max_drawdown_threshold=0.05,
                        take_profit_sell_ratio=0.5,
                        enable_dip_buy=True,
                        dip_buy_tier1_threshold=-0.03,
                        dip_buy_tier1_amount=1000.0,
                        dip_buy_tier2_threshold=-0.05,
                        dip_buy_tier2_amount=1500.0,
                        dip_buy_tier3_threshold=-0.07,
                        dip_buy_tier3_amount=2000.0,
                        enable_yield_boost=False
                    ),
                    color="#f39c12",
                    is_default=True,
                    created_at=now,
                    updated_at=now
                ),
                StrategyTemplate(
                    id="boost",
                    name="收益增强",
                    group="增强型",
                    description="月定投+收益增强策略",
                    params=StrategyParams(
                        frequency="monthly",
                        day_of_month=1,
                        investment_amount=500.0,
                        enable_stop_loss=True,
                        stop_loss_rate=0.10,
                        stop_loss_sell_ratio=1.0,
                        enable_take_profit=False,
                        enable_dip_buy=False,
                        enable_yield_boost=True,
                        yield_boost_trigger=-0.20,
                        yield_boost_recover=-0.10,
                        yield_boost_amount=500.0
                    ),
                    color="#1abc9c",
                    is_default=True,
                    created_at=now,
                    updated_at=now
                ),
            ]
            self._save_all(default_strategies)

    def _load_all(self) -> List[StrategyTemplate]:
        """加载所有策略模板"""
        if not self.file_path.exists():
            return []
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return [StrategyTemplate.from_dict(item) for item in data]
        except (json.JSONDecodeError, KeyError):
            return []

    def _save_all(self, strategies: List[StrategyTemplate]):
        """保存所有策略模板"""
        with open(self.file_path, 'w', encoding='utf-8') as f:
            json.dump([s.to_dict() for s in strategies], f, ensure_ascii=False, indent=2)

    def list_strategies(self, group: Optional[str] = None) -> List[StrategyTemplate]:
        """获取策略模板列表"""
        strategies = self._load_all()
        if group:
            strategies = [s for s in strategies if s.group == group]
        return strategies

    def get_strategy(self, strategy_id: str) -> Optional[StrategyTemplate]:
        """获取指定策略模板"""
        strategies = self._load_all()
        for s in strategies:
            if s.id == strategy_id:
                return s
        return None

    def create_strategy(self, name: str, group: str, description: str = "",
                       params: StrategyParams = None, color: str = "#1f77b4") -> StrategyTemplate:
        """创建新的策略模板"""
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        strategy = StrategyTemplate(
            id=str(uuid.uuid4())[:8],
            name=name,
            group=group,
            description=description,
            params=params or StrategyParams(),
            color=color,
            is_default=False,
            created_at=now,
            updated_at=now
        )
        strategies = self._load_all()
        strategies.append(strategy)
        self._save_all(strategies)
        return strategy

    def update_strategy(self, strategy_id: str, **kwargs) -> Optional[StrategyTemplate]:
        """更新策略模板"""
        strategies = self._load_all()
        for s in strategies:
            if s.id == strategy_id:
                if 'name' in kwargs:
                    s.name = kwargs['name']
                if 'group' in kwargs:
                    s.group = kwargs['group']
                if 'description' in kwargs:
                    s.description = kwargs['description']
                if 'color' in kwargs:
                    s.color = kwargs['color']
                if 'params' in kwargs:
                    if isinstance(kwargs['params'], dict):
                        s.params = StrategyParams.from_dict(kwargs['params'])
                    else:
                        s.params = kwargs['params']
                s.updated_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                self._save_all(strategies)
                return s
        return None

    def delete_strategy(self, strategy_id: str) -> bool:
        """删除策略模板"""
        strategies = self._load_all()
        original_len = len(strategies)
        strategies = [s for s in strategies if s.id != strategy_id]
        if len(strategies) < original_len:
            self._save_all(strategies)
            return True
        return False

    def get_groups(self) -> List[str]:
        """获取所有策略分组"""
        strategies = self._load_all()
        groups = set(s.group for s in strategies)
        return sorted(list(groups))
