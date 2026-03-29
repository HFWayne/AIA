# -*- coding: utf-8 -*-
"""
回测报告管理器 (数据库 + Redis 缓存)
"""

import json
import uuid
import logging
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import Optional, List

from data_source.db.connection import get_db_session
from data_source.db.models import Report as DBReport
from data_source.cache import get_cache
from backtest.cache_keys import CacheKeys, CacheTTL
from backtest.dca_backtest import BacktestResult

logger = logging.getLogger(__name__)


@dataclass
class ReportData:
    """回测报告数据"""
    id: str
    name: str
    created_at: str
    fund_code: str
    fund_name: str
    start_date: str
    end_date: str
    investment_amount: float
    frequency: str
    strategy_params: dict
    result: dict
    trades: list

    @classmethod
    def from_dict(cls, data: dict) -> 'ReportData':
        return cls(**data)

    def to_dict(self) -> dict:
        return asdict(self)


class ReportManager:
    """报告管理器 (DB + Redis)"""

    def __init__(self):
        self.cache = get_cache()
        self._cache_ttl = CacheTTL.REPORT_LIST

    def _invalidate_cache(self):
        """清除缓存"""
        self.cache.delete(CacheKeys.report_list())

    def generate_name(self, fund_name: str, fund_code: str, start_date: str,
                      end_date: str, strategy_params: dict) -> str:
        """生成报告名称"""
        parts = [f"{fund_name}_{fund_code}", f"{start_date}-{end_date}"]

        if strategy_params.get('enable_take_profit') or strategy_params.get('enable_stop_loss'):
            strategy_parts = []
            if strategy_params.get('enable_take_profit'):
                rate = int(strategy_params.get('take_profit_rate', 0) * 100)
                strategy_parts.append(f"止盈{rate}%")
            if strategy_params.get('enable_stop_loss'):
                rate = int(strategy_params.get('stop_loss_rate', 0) * 100)
                strategy_parts.append(f"止损{rate}%")
            parts.append("".join(strategy_parts))
        else:
            parts.append("无策略")

        return "_".join(parts)

    def save_report(self, result: BacktestResult, name: Optional[str] = None) -> str:
        """保存报告，返回报告ID"""
        report_id = str(uuid.uuid4())[:8]

        if name is None:
            fund_name = result.strategy_params.get('fund_name', '未知')
            fund_code = result.strategy_params.get('fund_code', 'UNKNOWN')
            start_date = result.strategy_params.get('start_date', '')
            end_date = result.strategy_params.get('end_date', '')
            name = self.generate_name(fund_name, fund_code, start_date, end_date, result.strategy_params)

        trades_list = []
        for _, row in result.trades.iterrows():
            trades_list.append({
                'date': str(row['date'])[:10] if hasattr(row['date'], 'strftime') else str(row['date'])[:10],
                'action': row['action'],
                'nav': float(row['nav']),
                'shares': float(row['shares']) if 'shares' in row else 0,
                'invest_amount': float(row['invest_amount']) if 'invest_amount' in row else 0,
                'total_shares': float(row['total_shares']),
                'portfolio_value': float(row['portfolio_value']),
                'return_rate': float(row['return_rate']),
                'reason': row.get('reason', '')
            })

        strategy_params = result.strategy_params
        start_date_str = strategy_params.get('start_date', '')
        end_date_str = strategy_params.get('end_date', '')

        report = ReportData(
            id=report_id,
            name=name,
            created_at=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            fund_code=strategy_params.get('fund_code', ''),
            fund_name=strategy_params.get('fund_name', ''),
            start_date=start_date_str,
            end_date=end_date_str,
            investment_amount=float(result.total_invested / result.investment_count) if result.investment_count > 0 else 0,
            frequency=strategy_params.get('frequency', 'monthly'),
            strategy_params=strategy_params,
            result={
                'total_invested': float(result.total_invested),
                'final_value': float(result.final_value),
                'total_return': float(result.total_return),
                'return_rate': float(result.return_rate),
                'annual_return': float(result.annual_return),
                'max_drawdown': float(result.max_drawdown),
                'investment_count': int(result.investment_count),
                'stop_loss_count': int(result.stop_loss_count),
                'take_profit_count': int(result.take_profit_count)
            },
            trades=trades_list
        )

        with get_db_session() as session:
            db_report = DBReport(
                id=report.id,
                name=report.name,
                created_at=datetime.strptime(report.created_at, '%Y-%m-%d %H:%M:%S'),
                fund_code=report.fund_code,
                fund_name=report.fund_name,
                start_date=datetime.strptime(report.start_date, '%Y-%m-%d').date() if report.start_date else None,
                end_date=datetime.strptime(report.end_date, '%Y-%m-%d').date() if report.end_date else None,
                investment_amount=report.investment_amount,
                frequency=report.frequency,
                strategy_params=json.dumps(report.strategy_params, ensure_ascii=False),
                result=json.dumps(report.result, ensure_ascii=False),
                trades=json.dumps(report.trades, ensure_ascii=False)
            )
            session.add(db_report)

        self._invalidate_cache()
        logger.info(f"报告已保存: {report_id}")
        return report_id

    def load_report(self, report_id: str) -> Optional[ReportData]:
        """加载报告"""
        with get_db_session() as session:
            db_report = session.query(DBReport).filter(DBReport.id == report_id).first()
            if db_report:
                return ReportData.from_dict(db_report.to_dict())
        return None

    def list_reports(self, fund_code: Optional[str] = None, search: Optional[str] = None) -> List[ReportData]:
        """列出所有报告"""
        cache_key = CacheKeys.report_list()
        cached = self.cache.get(cache_key)
        if cached:
            reports = [ReportData.from_dict(r) for r in cached]
        else:
            with get_db_session() as session:
                query = session.query(DBReport).order_by(DBReport.created_at.desc())
                reports = [ReportData.from_dict(r.to_dict()) for r in query.all()]
            self.cache.set(cache_key, [r.to_dict() for r in reports], expire=self._cache_ttl)

        if fund_code:
            reports = [r for r in reports if r.fund_code == fund_code]
        if search:
            reports = [r for r in reports if search.lower() in r.name.lower()]

        return reports

    def delete_report(self, report_id: str) -> bool:
        """删除报告"""
        with get_db_session() as session:
            db_report = session.query(DBReport).filter(DBReport.id == report_id).first()
            if db_report:
                session.delete(db_report)
                self._invalidate_cache()
                logger.info(f"报告已删除: {report_id}")
                return True
        return False

    def get_report_summary(self) -> dict:
        """获取报告统计"""
        reports = self.list_reports()
        return {
            'total': len(reports),
            'funds': len(set(r.fund_code for r in reports)),
            'reports': reports
        }
