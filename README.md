# 📈 股票定投回测工具

一个基于 Python 的股票/基金 DCA（定期定额投资）回测系统，支持 Streamlit Web 界面。

## 功能特性

- ✅ **本地数据库存储**：MySQL 存储历史数据，支持多年回测
- ✅ **Redis 缓存加速**：热点数据缓存，大幅减少 API 调用
- ✅ **分级缓存**：L1 内存 + L2 Redis 多级缓存策略
- ✅ **多种数据源**：支持 tushare、akshare、baostock，自动切换
- ✅ **单股票/多股票回测**：支持单只股票分析和多只股票对比
- ✅ **灵活定投设置**：
  - 支持月/周/日定投频率
  - 月定投可选每月1-28日
  - 周定投可选周一至周五
  - 支持顺延：指定日期无交易数据时自动顺延到最近交易日
- ✅ **止损止盈策略**：
  - 止损：收益率低于阈值时触发，按比例卖出
  - 止盈（最大回撤法）：达到目标收益率后进入观察期，从高点回撤超过阈值时卖出
- ✅ **补仓策略**：支持多档位下跌补仓
- ✅ **收益增强**：浮亏指定幅度后恢复定投金额
- ✅ **可视化图表**：净值走势、投入收益曲线、K线图、收益对比等
- ✅ **报告管理**：保存、加载、对比历史回测报告
- ✅ **报告导出**：Excel/CSV 多格式导出
- ✅ **高级分析**：夏普比率、卡玛比率、索提诺比率、最大回撤等风险指标
- ✅ **自动回测任务**：多股票多策略批量回测
- ✅ **进度追踪**：实时进度显示
- ✅ **自选股管理**：股票池管理，支持分组
- ✅ **策略模板**：预设多种策略，快速复用
- ✅ **增量同步**：自动检测最新数据，只同步新增内容
- ✅ **自动化测试**：63+ 单元测试，覆盖核心功能

## 快速开始

### 1. 安装依赖

```bash
pip install streamlit pandas matplotlib tushare akshare baostock sqlalchemy pymysql redis openpyxl
```

### 2. 配置数据库（可选，推荐）

需要先安装 MySQL 和 Redis：

```bash
# MySQL
# 下载地址: https://dev.mysql.com/downloads/mysql/

# Redis
# Windows: https://github.com/tporadowski/redis/releases
# 或使用 Docker: docker run -d -p 6379:6379 redis
```

配置环境变量（或编辑 `data_source/config.py`）：

```bash
export MYSQL_PASSWORD=your_password
export REDIS_HOST=localhost
export REDIS_PORT=6379
```

### 3. 初始化数据库

```bash
# 初始化数据库表结构
python -m data_source.db.migrations --init

# 同步股票列表（股票和ETF基础信息）
python -m data_source.db.migrations --sync-stocks

# 查看数据统计
python -m data_source.db.migrations --stats
```

### 4. 启动 Web 应用

```bash
streamlit run app.py
```

浏览器打开 http://localhost:8501

## 数据同步功能

### 数据同步概述

系统支持将免费数据源（akshare/baostock）同步到本地 MySQL 数据库，并使用 Redis 缓存热点数据：

```
请求 → L1内存缓存 → L2 Redis缓存 → MySQL数据库 → akshare/baostock API
```

### 基本命令

```bash
# 初始化数据库
python -m data_source.db.migrations --init

# 同步股票列表
python -m data_source.db.migrations --sync-stocks

# 同步单只股票历史数据
python -m data_source.db.migrations --code 510300

# 全量同步（首次运行，获取所有股票历史数据）
python -m data_source.db.migrations --full

# 每日增量同步（建议每天定时执行）
python -m data_source.db.migrations --incremental

# 查看数据统计
python -m data_source.db.migrations --stats
```

### 增量同步 API

```python
from data_source.sync.free_sync import FreeDataSync

sync = FreeDataSync()

# 增量同步单只股票（自动检测最新日期）
sync.sync_daily_kline_incremental(code='600036')

# 批量增量同步
sync.sync_daily_kline_batch(
    codes=['600036', '000001'],
    incremental=True
)

# 同步自选股
sync.sync_watchlist_stocks(watchlist_codes=['600036', '000001'])
```

## 回测分析功能

### 风险指标计算

```python
from backtest.analysis import BacktestAnalyzer, analyze_backtest

# 分析回测结果
analyzer = BacktestAnalyzer(risk_free_rate=0.03)
metrics = analyzer.analyze_trades(trades_df)

print(f"夏普比率: {metrics.sharpe_ratio:.2f}")
print(f"卡玛比率: {metrics.calmar_ratio:.2f}")
print(f"索提诺比率: {metrics.sortino_ratio:.2f}")
print(f"最大回撤: {metrics.max_drawdown:.2f}%")
print(f"年化收益率: {metrics.annual_return * 100:.2f}%")
print(f"胜率: {metrics.win_rate:.1f}%")
```

### 多策略对比

```python
from backtest.analysis import compare_backtests

results = {
    "保守策略": result1,
    "激进策略": result2
}
df = compare_backtests(results)
```

## 报告导出功能

```python
from backtest.report_exporter import ReportExporter, export_report, export_comparison

# 导出单个报告
exporter = ReportExporter()
exporter.export_excel(report)    # Excel 格式
exporter.export_csv(report)      # CSV 格式

# 多报告对比导出
comp_exporter = MultiReportExporter()
comp_exporter.export_comparison_excel([report1, report2])
```

## 项目结构

```
E:\code\AIA\
├── app.py                      # Streamlit Web 应用入口
├── data_source/
│   ├── config.py              # 配置文件
│   ├── fund_data_source.py    # 数据源接口
│   ├── cache/
│   │   ├── redis_client.py    # Redis 缓存客户端
│   │   └── tiered_cache.py    # 分级缓存 (L1+L2)
│   ├── db/
│   │   ├── models.py          # SQLAlchemy 模型
│   │   ├── connection.py      # 数据库连接
│   │   └── migrations/        # 数据库迁移
│   └── sync/
│       ├── free_sync.py       # 免费数据同步
│       └── scheduler.py        # 定时任务调度器
├── backtest/
│   ├── dca_backtest.py       # DCA 回测引擎
│   ├── visualization.py       # 可视化图表
│   ├── analysis.py            # 回测分析 (夏普/卡玛比率)
│   ├── report_manager.py      # 报告管理器
│   ├── report_exporter.py     # 报告导出 (Excel/CSV)
│   ├── watchlist_manager.py   # 自选股管理器
│   ├── strategy_manager.py    # 策略管理器
│   ├── progress.py            # 进度追踪
│   └── page_*.py             # Streamlit 页面组件
├── tasks/
│   └── task_manager.py        # 任务管理器
├── tests/                     # 测试 (63+ 测试用例)
│   ├── test_dca_backtest.py  # DCA 回测测试
│   ├── test_new_features.py  # 新功能测试
│   └── ui/                    # UI 集成测试
└── reports/                   # 导出的报告
```

## 数据库表结构

| 表名 | 说明 |
|------|------|
| reports | 回测报告 |
| watchlists | 自选股列表 |
| watchlist_stocks | 自选股关联 |
| strategy_templates | 策略模板 |
| stocks | 股票基础信息 |
| daily_kline | 日线数据 |
| backtest_tasks | 回测任务 |

## 运行测试

```bash
# 运行所有测试
pytest tests/ -v

# 生成 HTML 测试报告
pytest tests/ --html=tests/report.html --self-contained-html

# 带覆盖率
pytest tests/ --cov=. --cov-report=html
```

## 常用股票代码

| 代码 | 名称 |
|------|------|
| 510300 | 沪深300ETF |
| 510500 | 中证500ETF |
| 159915 | 创业板ETF |
| 510050 | 上证50ETF |
| 510880 | 红利ETF |
| 600036 | 招商银行 |
| 601318 | 中国平安 |
| 600519 | 贵州茅台 |

## 注意事项

1. akshare/baostock 为免费数据源，无 API 调用限制
2. 首次使用建议执行 `--full` 全量同步
3. 建议每天定时执行 `--incremental` 增量同步
4. 回测结果仅供参考，不构成投资建议

## License

MIT
