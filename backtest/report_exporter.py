# -*- coding: utf-8 -*-
"""
回测报告导出模块

支持导出格式:
- Excel (.xlsx): 多sheet，包含汇总、交易记录、图表数据
- PDF (.pdf): 格式化的报告文档
- CSV (.csv): 纯数据导出
"""

import os
import io
import logging
from datetime import datetime
from typing import Optional, List
from dataclasses import asdict

import pandas as pd

logger = logging.getLogger(__name__)


class ReportExporter:
    """回测报告导出器"""

    def __init__(self, reports_dir: str = "reports"):
        self.reports_dir = reports_dir
        os.makedirs(reports_dir, exist_ok=True)

    def _prepare_summary_data(self, report) -> dict:
        """准备汇总数据"""
        result = report.result if isinstance(report.result, dict) else {}

        return {
            "报告名称": report.name,
            "基金代码": report.fund_code,
            "基金名称": report.fund_name,
            "回测开始日期": report.start_date,
            "回测结束日期": report.end_date,
            "定投金额": f"{report.investment_amount:.2f}",
            "定投频率": report.frequency,
            "生成时间": report.created_at,
            "": "",
            "=== 回测结果 ===": "",
            "总投入金额": f"{result.get('total_invested', 0):.2f}",
            "最终价值": f"{result.get('final_value', 0):.2f}",
            "总收益": f"{result.get('total_return', 0):.2f}",
            "收益率": f"{result.get('return_rate', 0):.2f}%",
            "年化收益率": f"{result.get('annual_return', 0):.2f}%",
            "最大回撤": f"{result.get('max_drawdown', 0):.2f}%",
            "定投次数": result.get('investment_count', 0),
            "止损次数": result.get('stop_loss_count', 0),
            "止盈次数": result.get('take_profit_count', 0),
        }

    def _prepare_trades_data(self, report) -> pd.DataFrame:
        """准备交易记录数据"""
        trades = report.trades if isinstance(report.trades, list) else []

        if not trades:
            return pd.DataFrame()

        if isinstance(trades[0], dict):
            df = pd.DataFrame(trades)
        else:
            return pd.DataFrame()

        return df

    def _prepare_strategy_params(self, report) -> dict:
        """准备策略参数"""
        params = report.strategy_params if isinstance(report.strategy_params, dict) else {}

        return {
            "参数名称": list(params.keys()),
            "参数值": list(params.values())
        }

    def export_excel(self, report, filename: Optional[str] = None) -> str:
        """导出为 Excel 文件

        Args:
            report: ReportData 对象
            filename: 输出文件名，None 则自动生成

        Returns:
            导出文件路径
        """
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{report.fund_code}_{report.name}_{timestamp}.xlsx"

        filepath = os.path.join(self.reports_dir, filename)

        with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
            summary_data = self._prepare_summary_data(report)
            pd.DataFrame([summary_data]).T.to_excel(writer, sheet_name='汇总', header=False)

            trades_df = self._prepare_trades_data(report)
            if not trades_df.empty:
                trades_df.to_excel(writer, sheet_name='交易记录', index=False)

            params = self._prepare_strategy_params(report)
            if params.get('参数名称'):
                pd.DataFrame(params).to_excel(writer, sheet_name='策略参数', index=False)

        logger.info(f"Excel 报告已导出: {filepath}")
        return filepath

    def export_csv(self, report, filename: Optional[str] = None) -> str:
        """导出为 CSV 文件

        Args:
            report: ReportData 对象
            filename: 输出文件名，None 则自动生成

        Returns:
            导出文件路径
        """
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{report.fund_code}_{report.name}_{timestamp}.csv"

        filepath = os.path.join(self.reports_dir, filename)

        trades_df = self._prepare_trades_data(report)
        if not trades_df.empty:
            trades_df.to_csv(filepath, index=False, encoding='utf-8-sig')
        else:
            pd.DataFrame([self._prepare_summary_data(report)]).T.to_csv(
                filepath, header=False, encoding='utf-8-sig'
            )

        logger.info(f"CSV 报告已导出: {filepath}")
        return filepath

    def export_excel_bytes(self, report) -> bytes:
        """导出为 Excel 字节数据（用于下载）

        Args:
            report: ReportData 对象

        Returns:
            Excel 文件字节数据
        """
        buffer = io.BytesIO()

        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            summary_data = self._prepare_summary_data(report)
            pd.DataFrame([summary_data]).T.to_excel(writer, sheet_name='汇总', header=False)

            trades_df = self._prepare_trades_data(report)
            if not trades_df.empty:
                trades_df.to_excel(writer, sheet_name='交易记录', index=False)

            params = self._prepare_strategy_params(report)
            if params.get('参数名称'):
                pd.DataFrame(params).to_excel(writer, sheet_name='策略参数', index=False)

        buffer.seek(0)
        return buffer.getvalue()


class MultiReportExporter:
    """多报告对比导出器"""

    def export_comparison_excel(self, reports: List, filename: Optional[str] = None) -> str:
        """导出多报告对比 Excel

        Args:
            reports: ReportData 对象列表
            filename: 输出文件名

        Returns:
            导出文件路径
        """
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"对比报告_{timestamp}.xlsx"

        filepath = os.path.join("reports", filename)
        os.makedirs("reports", exist_ok=True)

        with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
            comparison_data = []
            for report in reports:
                result = report.result if isinstance(report.result, dict) else {}
                comparison_data.append({
                    "基金代码": report.fund_code,
                    "基金名称": report.fund_name,
                    "回测期间": f"{report.start_date} ~ {report.end_date}",
                    "总投入": result.get('total_invested', 0),
                    "最终价值": result.get('final_value', 0),
                    "总收益": result.get('total_return', 0),
                    "收益率": result.get('return_rate', 0),
                    "年化收益": result.get('annual_return', 0),
                    "最大回撤": result.get('max_drawdown', 0),
                    "定投次数": result.get('investment_count', 0),
                })

            comparison_df = pd.DataFrame(comparison_data)
            comparison_df.to_excel(writer, sheet_name='对比汇总', index=False)

            all_trades = []
            for i, report in enumerate(reports):
                trades_df = ReportExporter()._prepare_trades_data(report)
                if not trades_df.empty:
                    trades_df['基金代码'] = report.fund_code
                    trades_df['基金名称'] = report.fund_name
                    all_trades.append(trades_df)

            if all_trades:
                combined_trades = pd.concat(all_trades, ignore_index=True)
                combined_trades.to_excel(writer, sheet_name='交易记录', index=False)

        logger.info(f"对比报告已导出: {filepath}")
        return filepath


def export_report(report, format: str = 'excel', filename: Optional[str] = None) -> str:
    """便捷导出函数

    Args:
        report: ReportData 对象
        format: 导出格式 ('excel', 'csv')
        filename: 输出文件名

    Returns:
        导出文件路径
    """
    exporter = ReportExporter()

    if format == 'excel':
        return exporter.export_excel(report, filename)
    elif format == 'csv':
        return exporter.export_csv(report, filename)
    else:
        raise ValueError(f"不支持的格式: {format}")


def export_comparison(reports: List, filename: Optional[str] = None) -> str:
    """便捷对比导出函数

    Args:
        reports: ReportData 对象列表
        filename: 输出文件名

    Returns:
        导出文件路径
    """
    exporter = MultiReportExporter()
    return exporter.export_comparison_excel(reports, filename)
