# -*- coding: utf-8 -*-
"""
自选股管理器
管理用户的自选股列表
"""

import json
import uuid
from dataclasses import dataclass, asdict, field
from datetime import datetime
from typing import Optional, List, Dict
from pathlib import Path


@dataclass
class StockInfo:
    """股票信息"""
    code: str
    name: str
    market: str = "A股"
    type: str = "ETF"
    notes: str = ""
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> 'StockInfo':
        return cls(**data)


@dataclass
class Watchlist:
    """自选股列表"""
    id: str
    name: str
    description: str = ""
    stocks: List[StockInfo] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'stocks': [s.to_dict() for s in self.stocks],
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Watchlist':
        stocks = [StockInfo.from_dict(s) for s in data.get('stocks', [])]
        return cls(
            id=data['id'],
            name=data['name'],
            description=data.get('description', ''),
            stocks=stocks,
            created_at=data.get('created_at', ''),
            updated_at=data.get('updated_at', '')
        )


class WatchlistManager:
    """自选股管理器"""

    def __init__(self, data_dir: Optional[str] = None):
        if data_dir is None:
            self.data_dir: Path = Path(__file__).parent.parent.parent / "reports"
        else:
            self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.file_path = self.data_dir / "watchlists.json"
        self._init_default_watchlists()

    def _init_default_watchlists(self):
        """初始化默认自选股列表"""
        if not self.file_path.exists():
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            default_lists = [
                Watchlist(
                    id="default_etf",
                    name="宽基ETF",
                    description="主要宽基指数ETF",
                    stocks=[
                        StockInfo(code="510300", name="沪深300", market="A股", type="ETF", tags=["宽基", "大盘"]),
                        StockInfo(code="510500", name="中证500", market="A股", type="ETF", tags=["宽基", "中盘"]),
                        StockInfo(code="159915", name="创业板ETF", market="A股", type="ETF", tags=["宽基", "成长"]),
                        StockInfo(code="510050", name="上证50", market="A股", type="ETF", tags=["宽基", "大盘"]),
                        StockInfo(code="510880", name="红利ETF", market="A股", type="ETF", tags=["宽基", "高股息"]),
                    ],
                    created_at=now,
                    updated_at=now
                ),
                Watchlist(
                    id="default_industry",
                    name="行业ETF",
                    description="热门行业ETF",
                    stocks=[
                        StockInfo(code="512880", name="证券ETF", market="A股", type="ETF", tags=["金融", "证券"]),
                        StockInfo(code="512760", name="芯片ETF", market="A股", type="ETF", tags=["科技", "芯片"]),
                        StockInfo(code="512660", name="军工ETF", market="A股", type="ETF", tags=["军工"]),
                        StockInfo(code="512010", name="医药ETF", market="A股", type="ETF", tags=["医药"]),
                        StockInfo(code="515050", name="5GETF", market="A股", type="ETF", tags=["科技", "5G"]),
                    ],
                    created_at=now,
                    updated_at=now
                ),
                Watchlist(
                    id="default_dividend",
                    name="红利基金",
                    description="高股息ETF",
                    stocks=[
                        StockInfo(code="510880", name="红利ETF", market="A股", type="ETF", tags=["高股息", "红利"]),
                        StockInfo(code="512890", name="红利低波ETF", market="A股", type="ETF", tags=["高股息", "低波动"]),
                        StockInfo(code="515100", name="红利增强ETF", market="A股", type="ETF", tags=["高股息", "增强"]),
                    ],
                    created_at=now,
                    updated_at=now
                ),
            ]
            self._save_all(default_lists)

    def _load_all(self) -> List[Watchlist]:
        """加载所有自选股列表"""
        if not self.file_path.exists():
            return []
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return [Watchlist.from_dict(item) for item in data]
        except (json.JSONDecodeError, KeyError):
            return []

    def _save_all(self, watchlists: List[Watchlist]):
        """保存所有自选股列表"""
        with open(self.file_path, 'w', encoding='utf-8') as f:
            json.dump([w.to_dict() for w in watchlists], f, ensure_ascii=False, indent=2)

    def list_watchlists(self) -> List[Watchlist]:
        """获取所有自选股列表"""
        return self._load_all()

    def get_watchlist(self, watchlist_id: str) -> Optional[Watchlist]:
        """获取指定自选股列表"""
        watchlists = self._load_all()
        for w in watchlists:
            if w.id == watchlist_id:
                return w
        return None

    def create_watchlist(self, name: str, description: str = "") -> Watchlist:
        """创建新的自选股列表"""
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        watchlist = Watchlist(
            id=str(uuid.uuid4())[:8],
            name=name,
            description=description,
            stocks=[],
            created_at=now,
            updated_at=now
        )
        watchlists = self._load_all()
        watchlists.append(watchlist)
        self._save_all(watchlists)
        return watchlist

    def update_watchlist(self, watchlist_id: str, name: Optional[str] = None, description: Optional[str] = None) -> Optional[Watchlist]:
        """更新自选股列表"""
        watchlists = self._load_all()
        for w in watchlists:
            if w.id == watchlist_id:
                if name is not None:
                    w.name = name
                if description is not None:
                    w.description = description
                w.updated_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                self._save_all(watchlists)
                return w
        return None

    def delete_watchlist(self, watchlist_id: str) -> bool:
        """删除自选股列表"""
        watchlists = self._load_all()
        original_len = len(watchlists)
        watchlists = [w for w in watchlists if w.id != watchlist_id]
        if len(watchlists) < original_len:
            self._save_all(watchlists)
            return True
        return False

    def add_stock(self, watchlist_id: str, stock: StockInfo) -> bool:
        """添加股票到自选股列表"""
        watchlists = self._load_all()
        for w in watchlists:
            if w.id == watchlist_id:
                if not any(s.code == stock.code for s in w.stocks):
                    w.stocks.append(stock)
                    w.updated_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    self._save_all(watchlists)
                    return True
        return False

    def remove_stock(self, watchlist_id: str, stock_code: str) -> bool:
        """从自选股列表移除股票"""
        watchlists = self._load_all()
        for w in watchlists:
            if w.id == watchlist_id:
                original_len = len(w.stocks)
                w.stocks = [s for s in w.stocks if s.code != stock_code]
                if len(w.stocks) < original_len:
                    w.updated_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    self._save_all(watchlists)
                    return True
        return False

    def update_stock(self, watchlist_id: str, stock: StockInfo) -> bool:
        """更新股票信息"""
        watchlists = self._load_all()
        for w in watchlists:
            if w.id == watchlist_id:
                for i, s in enumerate(w.stocks):
                    if s.code == stock.code:
                        w.stocks[i] = stock
                        w.updated_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        self._save_all(watchlists)
                        return True
        return False

    def get_all_stocks(self) -> List[StockInfo]:
        """获取所有自选股（去重）"""
        watchlists = self._load_all()
        seen = set()
        all_stocks = []
        for w in watchlists:
            for s in w.stocks:
                if s.code not in seen:
                    seen.add(s.code)
                    all_stocks.append(s)
        return all_stocks

    def search_stock(self, keyword: str) -> List[StockInfo]:
        """搜索股票"""
        all_stocks = self.get_all_stocks()
        keyword = keyword.lower()
        return [
            s for s in all_stocks
            if keyword in s.code.lower() or keyword in s.name.lower()
        ]
