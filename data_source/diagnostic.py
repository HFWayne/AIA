# -*- coding: utf-8 -*-
"""
数据源诊断模块

测试各数据源连通性和可用数据权限
"""

import logging
import time
import json
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import Optional, List, Dict
from pathlib import Path

import tushare as ts
import akshare as ak

from data_source.config import TU_SHARE_TOKEN

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class SourceStatus:
    """数据源状态"""
    name: str
    display_name: str
    connected: bool
    latency_ms: Optional[float]
    error_message: Optional[str]
    capabilities: List[str]
    supported_types: List[str]
    limitations: List[str]


@dataclass
class DiagnosticResult:
    """诊断结果"""
    timestamp: str
    overall_status: str
    sources: List[SourceStatus]
    summary: Dict


class DataSourceDiagnostic:
    """数据源诊断器"""

    def __init__(self):
        self.results: List[SourceStatus] = []
        self._test_stocks = ['600036', '000001', '510300']

    def run_all(self) -> DiagnosticResult:
        """运行所有诊断"""
        logger.info("开始数据源诊断...")
        
        self._diagnose_tushare()
        self._diagnose_akshare()
        
        return DiagnosticResult(
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            overall_status="healthy" if any(s.connected for s in self.results) else "unhealthy",
            sources=self.results,
            summary=self._generate_summary()
        )

    def _measure_latency(self, func, *args, **kwargs) -> tuple[bool, Optional[float], Optional[str]]:
        """测量函数执行时间和成功率"""
        start = time.time()
        try:
            result = func(*args, **kwargs)
            latency = (time.time() - start) * 1000
            return True, latency, None
        except Exception as e:
            latency = (time.time() - start) * 1000
            return False, latency, str(e)

    def _diagnose_tushare(self):
        """诊断 Tushare"""
        logger.info("诊断 Tushare...")
        status = SourceStatus(
            name="tushare",
            display_name="Tushare Pro",
            connected=False,
            latency_ms=None,
            error_message=None,
            capabilities=[],
            supported_types=[],
            limitations=[]
        )

        try:
            ts.set_token(TU_SHARE_TOKEN)
            pro = ts.pro_api()
            
            def test_api():
                return pro.fund_nav(ts_code='510300.OF', start_date='20240101', end_date='20240110')

            connected, latency, error = self._measure_latency(test_api)
            status.connected = connected
            status.latency_ms = latency
            
            if connected:
                status.capabilities = [
                    "股票日线行情",
                    "基金净值数据",
                    "股票基本信息",
                    "指数数据",
                    "财务数据",
                ]
                status.supported_types = [
                    "A股（沪深）",
                    "ETF基金",
                    "LOF基金",
                    "指数成分股",
                ]
                status.limitations = [
                    "需要注册并获取Token",
                    "免费版有API调用频率限制",
                    "部分高级数据需要付费权限",
                ]
                
                try:
                    pro.fina_indicator(ts_code='600036.SH', start_date='20240101', end_date='20240110')
                    status.capabilities.append("财务指标")
                except:
                    pass
            else:
                status.error_message = error
                
        except Exception as e:
            status.connected = False
            status.error_message = str(e)

        self.results.append(status)

    def _diagnose_akshare(self):
        """诊断 AkShare"""
        logger.info("诊断 AkShare...")
        status = SourceStatus(
            name="akshare",
            display_name="AkShare",
            connected=False,
            latency_ms=None,
            error_message=None,
            capabilities=[],
            supported_types=[],
            limitations=[]
        )

        try:
            def test_api():
                return ak.stock_zh_a_hist(symbol='600036', start_date='20240101', end_date='20240110')

            connected, latency, error = self._measure_latency(test_api)
            status.connected = connected
            status.latency_ms = latency

            if connected:
                status.capabilities = [
                    "A股实时行情",
                    "A股历史行情",
                    "股票基本信息",
                    "指数行情",
                    "基金ETF数据",
                    "期货数据",
                    "宏观数据",
                ]
                status.supported_types = [
                    "A股（沪深京）",
                    "ETF基金",
                    "LOF基金",
                    "债券",
                    "期货",
                    "期权",
                ]
                status.limitations = [
                    "完全免费开源",
                    "数据来源于东方财富等",
                    "部分接口可能不稳定",
                ]
            else:
                status.error_message = error

        except Exception as e:
            status.connected = False
            status.error_message = str(e)

        self.results.append(status)

    def _generate_summary(self) -> Dict:
        """生成摘要"""
        connected = [s for s in self.results if s.connected]
        
        return {
            "total_sources": len(self.results),
            "available_sources": len(connected),
            "recommended_source": connected[0].name if connected else None,
            "fallback_chain": [s.name for s in self.results if s.connected],
        }

    def to_markdown(self) -> str:
        """生成 Markdown 格式报告"""
        result = self.run_all()
        
        md = f"""# 数据源诊断报告

> 生成时间: {result.timestamp}

## 总体状态

- **状态**: {"✅ 正常" if result.overall_status == "healthy" else "❌ 异常"}
- **可用数据源**: {result.summary['available_sources']}/{result.summary['total_sources']}
- **推荐数据源**: {result.summary['recommended_source'] or '无'}

## 数据源详情

"""
        for source in result.sources:
            md += f"""### {source.display_name} ({source.name})

| 项目 | 值 |
|------|-----|
| 连接状态 | {"✅ 已连接" if source.connected else "❌ 连接失败"} |
| 响应延迟 | {f"{source.latency_ms:.0f}ms" if source.latency_ms else "N/A"} |
| 错误信息 | {source.error_message or "无"} |

"""
            if source.connected:
                md += f"""**支持的数据类型:**
{chr(10).join(f"- {c}" for c in source.capabilities)}

**支持的品种:**
{chr(10).join(f"- {t}" for t in source.supported_types)}

**限制说明:**
{chr(10).join(f"- {l}" for l in source.limitations)}

"""

        md += f"""## 推荐使用方案

### 自动切换模式（推荐）

系统默认使用 **akshare** 作为主数据源，当主数据源不可用时自动切换到 **tushare**。

### 回退链路

```
{chr(10).join(f"{i+1}. {s}" for i, s in enumerate(result.summary['fallback_chain']))}
```

## 使用说明

1. **AkShare**: 完全免费，数据来源于东方财富，建议作为主力数据源
2. **Tushare**: 需要配置 `TU_SHARE_TOKEN` 环境变量，免费版有调用频率限制

---
*此报告由系统自动生成*
"""
        return md

    def to_html(self) -> str:
        """生成 HTML 格式报告"""
        result = self.run_all()
        
        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>数据源诊断报告</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; max-width: 900px; margin: 0 auto; padding: 20px; }}
        h1 {{ color: #1E3A5F; }}
        h2 {{ color: #2D5A87; border-bottom: 2px solid #4F8CFF; padding-bottom: 8px; }}
        table {{ width: 100%; border-collapse: collapse; margin: 15px 0; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #E2E8F0; }}
        th {{ background: #F8FAFC; font-weight: 600; }}
        .status-ok {{ color: #10B981; font-weight: bold; }}
        .status-error {{ color: #EF4444; font-weight: bold; }}
        .card {{ background: #F8FAFC; border-radius: 8px; padding: 20px; margin: 15px 0; }}
        .tag {{ display: inline-block; background: #E0E7FF; color: #4F8CFF; padding: 4px 12px; border-radius: 16px; margin: 4px; }}
        .tag-green {{ background: #D1FAE5; color: #059669; }}
        .tag-red {{ background: #FEE2E2; color: #DC2626; }}
    </style>
</head>
<body>
    <h1>📊 数据源诊断报告</h1>
    <p>生成时间: {result.timestamp}</p>
    
    <div class="card">
        <h2>总体状态</h2>
        <p><strong>状态:</strong> <span class="{'status-ok' if result.overall_status == 'healthy' else 'status-error'}">{"✅ 正常" if result.overall_status == "healthy" else "❌ 异常"}</span></p>
        <p><strong>可用数据源:</strong> {result.summary['available_sources']}/{result.summary['total_sources']}</p>
        <p><strong>推荐数据源:</strong> {result.summary['recommended_source'] or '无'}</p>
    </div>
"""
        for source in result.sources:
            status_class = 'status-ok' if source.connected else 'status-error'
            status_text = '✅ 已连接' if source.connected else '❌ 连接失败'
            
            html += f"""
    <div class="card">
        <h2>{source.display_name} ({source.name})</h2>
        <table>
            <tr><th>项目</th><th>值</th></tr>
            <tr><td>连接状态</td><td class="{status_class}">{status_text}</td></tr>
            <tr><td>响应延迟</td><td>{f"{source.latency_ms:.0f}ms" if source.latency_ms else "N/A"}</td></tr>
            <tr><td>错误信息</td><td>{source.error_message or "无"}</td></tr>
        </table>
"""
            if source.connected:
                caps_html = ''.join(f'<span class="tag tag-green">{c}</span>' for c in source.capabilities)
                types_html = ''.join(f'<span class="tag">{t}</span>' for t in source.supported_types)
                limits_html = ''.join(f'<span class="tag tag-red">{l}</span>' for l in source.limitations)
                
                html += f"""
        <p><strong>支持的数据类型:</strong><br>{caps_html}</p>
        <p><strong>支持的品种:</strong><br>{types_html}</p>
        <p><strong>限制说明:</strong><br>{limits_html}</p>
"""
            html += "</div>"

        html += """
    <div class="card">
        <h2>推荐使用方案</h2>
        <p><strong>自动切换模式（推荐）</strong></p>
        <p>系统默认使用 <strong>akshare</strong> 作为主数据源，当主数据源不可用时自动切换到 <strong>tushare</strong>。</p>
        <p><strong>回退链路:</strong></p>
        <ol>
""" + ''.join(f'<li>{s}</li>' for s in result.summary['fallback_chain']) + """
        </ol>
    </div>
    
    <div class="card">
        <h2>使用说明</h2>
        <p><strong>AkShare:</strong> 完全免费，数据来源于东方财富，建议作为主力数据源</p>
        <p><strong>Tushare:</strong> 需要配置 TU_SHARE_TOKEN 环境变量，免费版有调用频率限制</p>
    </div>
    
    <footer style="text-align: center; color: #64748B; margin-top: 40px;">
        <p>此报告由系统自动生成</p>
    </footer>
</body>
</html>"""
        return html

    def save_report(self, output_dir: str = "reports") -> dict:
        """保存报告到文件"""
        result = self.run_all()
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        md_file = output_path / f"datasource_diagnostic_{timestamp}.md"
        html_file = output_path / f"datasource_diagnostic_{timestamp}.html"
        json_file = output_path / f"datasource_diagnostic_{timestamp}.json"
        
        md_file.write_text(self.to_markdown(), encoding='utf-8')
        html_file.write_text(self.to_html(), encoding='utf-8')
        json_file.write_text(json.dumps(asdict(result), ensure_ascii=False, indent=2), encoding='utf-8')
        
        latest_md = output_path / "datasource_diagnostic_latest.md"
        latest_html = output_path / "datasource_diagnostic_latest.html"
        latest_md.write_text(self.to_markdown(), encoding='utf-8')
        latest_html.write_text(self.to_html(), encoding='utf-8')
        
        return {
            "timestamp": result.timestamp,
            "files": {
                "markdown": str(md_file),
                "html": str(html_file),
                "json": str(json_file),
                "latest_markdown": str(latest_md),
                "latest_html": str(latest_html),
            }
        }


def run_diagnostic():
    """运行诊断并输出结果"""
    diagnostic = DataSourceDiagnostic()
    diagnostic.save_report()
    print(diagnostic.to_markdown())


if __name__ == "__main__":
    run_diagnostic()
