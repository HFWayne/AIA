# -*- coding: utf-8 -*-
"""
自选股管理器 (数据库 + Redis 缓存)
"""

import json
import uuid
import logging
from dataclasses import dataclass, asdict, field
from datetime import datetime
from typing import Optional, List, Dict

from data_source.db.connection import get_db_session
from data_source.db.models import Watchlist as DBWatchlist, WatchlistStock as DBWatchlistStock
from data_source.cache import get_cache
from backtest.cache_keys import CacheKeys, CacheTTL

logger = logging.getLogger(__name__)


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
    """自选股管理器 (DB + Redis)"""

    def __init__(self):
        self.cache = get_cache()
        self._cache_ttl = CacheTTL.WATCHLIST_LIST
        self._init_default_watchlists()

    def _invalidate_cache(self):
        """清除缓存"""
        self.cache.delete(CacheKeys.watchlist_list())

    def _init_default_watchlists(self):
        """初始化默认自选股列表"""
        with get_db_session() as session:
            count = session.query(DBWatchlist).count()
            if count == 0:
                now = datetime.now()
                default_lists = [
                    {
                        "id": "wl_etf",
                        "name": "宽基ETF",
                        "description": "主要宽基指数ETF",
                        "stocks": [
                            {"code": "510300", "name": "沪深300", "market": "A股", "type": "ETF", "tags": ["宽基", "大盘"]},
                            {"code": "510500", "name": "中证500", "market": "A股", "type": "ETF", "tags": ["宽基", "中盘"]},
                            {"code": "159915", "name": "创业板ETF", "market": "A股", "type": "ETF", "tags": ["宽基", "成长"]},
                            {"code": "510050", "name": "上证50", "market": "A股", "type": "ETF", "tags": ["宽基", "大盘"]},
                            {"code": "510880", "name": "红利ETF", "market": "A股", "type": "ETF", "tags": ["宽基", "高股息"]},
                        ]
                    },
                    {
                        "id": "wl_ind",
                        "name": "行业ETF",
                        "description": "热门行业ETF",
                        "stocks": [
                            {"code": "512880", "name": "证券ETF", "market": "A股", "type": "ETF", "tags": ["金融", "证券"]},
                            {"code": "512760", "name": "芯片ETF", "market": "A股", "type": "ETF", "tags": ["科技", "芯片"]},
                            {"code": "512660", "name": "军工ETF", "market": "A股", "type": "ETF", "tags": ["军工"]},
                            {"code": "512010", "name": "医药ETF", "market": "A股", "type": "ETF", "tags": ["医药"]},
                            {"code": "515050", "name": "5GETF", "market": "A股", "type": "ETF", "tags": ["科技", "5G"]},
                        ]
                    },
                    {
                        "id": "wl_div",
                        "name": "红利基金",
                        "description": "高股息ETF",
                        "stocks": [
                            {"code": "510880", "name": "红利ETF", "market": "A股", "type": "ETF", "tags": ["高股息", "红利"]},
                            {"code": "512890", "name": "红利低波ETF", "market": "A股", "type": "ETF", "tags": ["高股息", "低波动"]},
                            {"code": "515100", "name": "红利增强ETF", "market": "A股", "type": "ETF", "tags": ["高股息", "增强"]},
                        ]
                    },
                ]

                for wl_data in default_lists:
                    wl = DBWatchlist(
                        id=wl_data['id'],
                        name=wl_data['name'],
                        description=wl_data['description'],
                        created_at=now,
                        updated_at=now
                    )
                    session.add(wl)
                    session.flush()

                    for s in wl_data['stocks']:
                        stock = DBWatchlistStock(
                            watchlist_id=wl.id,
                            code=s['code'],
                            name=s['name'],
                            market=s.get('market', 'A股'),
                            type=s.get('type', 'ETF'),
                            notes=s.get('notes', ''),
                            tags=json.dumps(s.get('tags', []), ensure_ascii=False)
                        )
                        session.add(stock)

                logger.info("默认自选股列表初始化完成")

    def _load_watchlist_with_stocks(self, db_watchlist: DBWatchlist) -> Watchlist:
        """加载自选股及其包含的股票"""
        with get_db_session() as session:
            stocks = session.query(DBWatchlistStock).filter(
                DBWatchlistStock.watchlist_id == db_watchlist.id
            ).all()
            stock_list = [StockInfo.from_dict(s.to_dict()) for s in stocks]
            return Watchlist(
                id=db_watchlist.id,
                name=db_watchlist.name,
                description=db_watchlist.description or '',
                stocks=stock_list,
                created_at=str(db_watchlist.created_at) if db_watchlist.created_at else '',
                updated_at=str(db_watchlist.updated_at) if db_watchlist.updated_at else ''
            )

    def list_watchlists(self) -> List[Watchlist]:
        """获取所有自选股列表"""
        cache_key = CacheKeys.watchlist_list()
        cached = self.cache.get(cache_key)
        if cached:
            return [Watchlist.from_dict(w) for w in cached]

        with get_db_session() as session:
            watchlists = session.query(DBWatchlist).all()
            result = [self._load_watchlist_with_stocks(w) for w in watchlists]

        self.cache.set(cache_key, [w.to_dict() for w in result], expire=self._cache_ttl)
        return result

    def get_watchlist(self, watchlist_id: str) -> Optional[Watchlist]:
        """获取指定自选股列表"""
        with get_db_session() as session:
            wl = session.query(DBWatchlist).filter(DBWatchlist.id == watchlist_id).first()
            if wl:
                return self._load_watchlist_with_stocks(wl)
        return None

    def create_watchlist(self, name: str, description: str = "") -> Watchlist:
        """创建新的自选股列表"""
        now = datetime.now()
        watchlist_id = str(uuid.uuid4())[:8]

        with get_db_session() as session:
            wl = DBWatchlist(
                id=watchlist_id,
                name=name,
                description=description,
                created_at=now,
                updated_at=now
            )
            session.add(wl)

        self._invalidate_cache()
        return Watchlist(
            id=watchlist_id,
            name=name,
            description=description,
            stocks=[],
            created_at=now.strftime('%Y-%m-%d %H:%M:%S'),
            updated_at=now.strftime('%Y-%m-%d %H:%M:%S')
        )

    def update_watchlist(self, watchlist_id: str, name: Optional[str] = None, description: Optional[str] = None) -> Optional[Watchlist]:
        """更新自选股列表"""
        with get_db_session() as session:
            wl = session.query(DBWatchlist).filter(DBWatchlist.id == watchlist_id).first()
            if wl:
                if name is not None:
                    wl.name = name
                if description is not None:
                    wl.description = description
                wl.updated_at = datetime.now()
                self._invalidate_cache()
                return self._load_watchlist_with_stocks(wl)
        return None

    def delete_watchlist(self, watchlist_id: str) -> bool:
        """删除自选股列表"""
        with get_db_session() as session:
            wl = session.query(DBWatchlist).filter(DBWatchlist.id == watchlist_id).first()
            if wl:
                session.delete(wl)
                self._invalidate_cache()
                return True
        return False

    def add_stock(self, watchlist_id: str, stock: StockInfo) -> bool:
        """添加股票到自选股列表"""
        with get_db_session() as session:
            existing = session.query(DBWatchlistStock).filter(
                DBWatchlistStock.watchlist_id == watchlist_id,
                DBWatchlistStock.code == stock.code
            ).first()

            if existing:
                return False

            wl = session.query(DBWatchlist).filter(DBWatchlist.id == watchlist_id).first()
            if wl:
                ws = DBWatchlistStock(
                    watchlist_id=watchlist_id,
                    code=stock.code,
                    name=stock.name,
                    market=stock.market,
                    type=stock.type,
                    notes=stock.notes,
                    tags=json.dumps(stock.tags, ensure_ascii=False)
                )
                session.add(ws)
                wl.updated_at = datetime.now()
                self._invalidate_cache()
                return True
        return False

    def remove_stock(self, watchlist_id: str, stock_code: str) -> bool:
        """从自选股列表移除股票"""
        with get_db_session() as session:
            ws = session.query(DBWatchlistStock).filter(
                DBWatchlistStock.watchlist_id == watchlist_id,
                DBWatchlistStock.code == stock_code
            ).first()

            if ws:
                session.delete(ws)
                wl = session.query(DBWatchlist).filter(DBWatchlist.id == watchlist_id).first()
                if wl:
                    wl.updated_at = datetime.now()
                self._invalidate_cache()
                return True
        return False

    def update_stock(self, watchlist_id: str, stock: StockInfo) -> bool:
        """更新股票信息"""
        with get_db_session() as session:
            ws = session.query(DBWatchlistStock).filter(
                DBWatchlistStock.watchlist_id == watchlist_id,
                DBWatchlistStock.code == stock.code
            ).first()

            if ws:
                ws.name = stock.name
                ws.market = stock.market
                ws.type = stock.type
                ws.notes = stock.notes
                ws.tags = json.dumps(stock.tags, ensure_ascii=False)
                wl = session.query(DBWatchlist).filter(DBWatchlist.id == watchlist_id).first()
                if wl:
                    wl.updated_at = datetime.now()
                self._invalidate_cache()
                return True
        return False

    def get_all_stocks(self) -> List[StockInfo]:
        """获取所有自选股（去重）"""
        watchlists = self.list_watchlists()
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
