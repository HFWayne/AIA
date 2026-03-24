# -*- coding: utf-8 -*-
"""
回测报告管理器
"""

import json
import os
import uuid
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import Optional, List
from pathlib import Path


@dataclass
class Report:
    """回测报告"""
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
    def from_dict(cls, data: dict) -> 'Report':
        return cls(**data)

    def to_dict(self) -> dict:
        return asdict(self)


class ReportManager:
    """报告管理器"""

    def __init__(self, reports_dir: str = None):
        if reports_dir is None:
            reports_dir = Path(__file__).parent.parent / "reports"
        else:
            reports_dir = Path(reports_dir)
        self.reports_dir = reports_dir
        self.reports_dir.mkdir(parents=True, exist_ok=True)

    def _get_report_path(self, report_id: str) -> Path:
        return self.reports_dir / f"{report_id}.json"

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

    def save_report(self, result, name: str = None) -> str:
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
                'total_shares': float(row['total_shares']),
                'portfolio_value': float(row['portfolio_value']),
                'return_rate': float(row['return_rate']),
                'reason': row.get('reason', '')
            })

        report_data = {
            'id': report_id,
            'name': name,
            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'fund_code': result.strategy_params.get('fund_code', ''),
            'fund_name': result.strategy_params.get('fund_name', ''),
            'start_date': result.strategy_params.get('start_date', ''),
            'end_date': result.strategy_params.get('end_date', ''),
            'investment_amount': float(result.total_invested / result.investment_count) if result.investment_count > 0 else 0,
            'frequency': result.strategy_params.get('frequency', 'monthly'),
            'strategy_params': result.strategy_params,
            'result': {
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
            'trades': trades_list
        }

        report_path = self._get_report_path(report_id)
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2)

        return report_id

    def load_report(self, report_id: str) -> Optional[Report]:
        """加载报告"""
        report_path = self._get_report_path(report_id)
        if not report_path.exists():
            return None

        with open(report_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        return Report.from_dict(data)

    def list_reports(self, fund_code: str = None, search: str = None) -> List[Report]:
        """列出所有报告"""
        reports = []

        for file_path in self.reports_dir.glob("*.json"):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                report = Report.from_dict(data)

                if fund_code and report.fund_code != fund_code:
                    continue
                if search and search.lower() not in report.name.lower():
                    continue

                reports.append(report)
            except Exception:
                continue

        reports.sort(key=lambda x: x.created_at, reverse=True)
        return reports

    def delete_report(self, report_id: str) -> bool:
        """删除报告"""
        report_path = self._get_report_path(report_id)
        if report_path.exists():
            report_path.unlink()
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
