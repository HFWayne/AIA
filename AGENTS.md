# AGENTS.md - AI 开发者指南

## 项目概述

这是一个 Python 股票/基金数据分析和 DCA（定期定额投资）回测项目，提供：
- 统一数据源接口，支持 tushare、akshare、baostock
- 带可视化功能的 DCA 回测引擎
- 支持止损止盈、定投加大、收益增强策略
- Web UI 界面 (Streamlit)
- MySQL 数据库 + Redis 缓存持久化
- 自选股管理、策略管理、报告管理
- 自动化测试框架

## 构建/测试/运行命令

### 运行 Web UI (Streamlit)
```bash
streamlit run app.py
```

### 测试
```bash
# 运行所有测试
pytest tests/ -v

# 运行单个测试文件
pytest tests/test_dca_backtest.py -v

# 运行单个测试
pytest tests/test_dca_backtest.py::TestDCABacktest::test_simple_dca_basic -v

# 生成 HTML 测试报告
pytest tests/ --html=tests/report.html --self-contained-html

# 带覆盖率运行
pytest tests/ --cov=. --cov-report=html
```

### 代码质量
```bash
# flake8 检查
flake8 .

# black 格式化
black .

# isort 排序导入
isort .
```

## 项目架构

### 文件结构
```
project/
├── app.py                    # Streamlit Web UI (唯一入口)
├── data_source/              # 数据源接口
│   ├── config.py             # 配置 (数据库、Redis、数据源)
│   ├── fund_data_source.py   # 统一数据源
│   ├── db/
│   │   ├── models.py         # SQLAlchemy 模型
│   │   ├── connection.py     # 数据库连接
│   │   └── migrations/       # SQL 迁移脚本
│   └── cache/
│       └── redis_client.py   # Redis 客户端
├── backtest/                 # 回测逻辑
│   ├── dca_backtest.py       # DCA 回测引擎
│   ├── visualization.py      # 可视化
│   ├── report_manager.py     # 报告管理器 (DB + Redis)
│   ├── watchlist_manager.py  # 自选股管理器
│   ├── strategy_manager.py   # 策略管理器
│   ├── cache_keys.py         # 缓存 key 定义
│   └── __init__.py
├── tasks/                    # 任务相关
│   └── task_manager.py       # 任务管理器
├── tests/                   # 测试
│   ├── conftest.py          # 共享 fixtures
│   ├── test_dca_backtest.py # DCA 回测测试
│   ├── ui/
│   │   ├── conftest.py      # UI 测试辅助类和 fixtures
│   │   ├── test_managers.py # Manager 集成测试
│   │   └── test_integration.py # 端到端测试
│   └── report.html          # HTML 测试报告
└── reports/                 # 保存的报告
```

### 数据库表
| 表名 | 说明 |
|------|------|
| `reports` | 回测报告 |
| `watchlists` | 自选股列表 |
| `watchlist_stocks` | 自选股关联 |
| `strategy_templates` | 策略模板 |
| `stocks` | 股票基础信息 |
| `daily_kline` | 日线数据 |
| `backtest_tasks` | 回测任务 |

### 核心类

| 类 | 模块 | 说明 |
|---|------|------|
| `ReportManager` | backtest/report_manager.py | 报告管理 (DB + Redis) |
| `WatchlistManager` | backtest/watchlist_manager.py | 自选股管理 |
| `StrategyManager` | backtest/strategy_manager.py | 策略管理 |
| `TaskManager` | tasks/task_manager.py | 任务管理 |
| `FundDataSource` | data_source/fund_data_source.py | 数据源 |
| `DCABacktest` | backtest/dca_backtest.py | DCA 回测引擎 |
| `FundBacktester` | backtest/__init__.py | 回测包装器 |

## 代码风格指南

### 通用原则
- 保持函数小而专注（最多约50行）
- 为所有公共函数编写文档字符串
- 函数参数和返回值必须使用类型注解
- 优雅处理异常，不要让程序默默崩溃

### 导入顺序
```python
# 第一：标准库
import os
import sys
from datetime import datetime
from typing import Optional, List, Dict

# 第二：第三方库
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# 最后：本地模块
from data_source.fund_data_source import FundDataSource
from backtest.dca_backtest import DCABacktest
```

### 命名规范
- **变量/函数**：snake_case（如 `fund_code`、`get_fund_data`）
- **类**：PascalCase（如 `FundDataSource`、`DCABacktest`）
- **常量**：UPPER_SNAKE_CASE（如 `DATA_SOURCE`、`TU_SHARE_TOKEN`）
- **私有方法**：以下划线开头（如 `_get_fund_from_tushare`）

### 异常处理
```python
# 使用特定异常类型的 try-except
try:
    result = self._fetch_data(fund_code)
except ConnectionError as e:
    logger.warning(f"网络错误: {e}")
    return None
except ValueError as e:
    logger.error(f"参数错误: {e}")
    raise

# 始终使用适当的日志级别
# - DEBUG: 详细诊断信息
# - INFO: 确认工作正常
# - WARNING: 发生意外情况，但程序可以继续
# - ERROR: 严重问题，函数无法执行
# - CRITICAL: 程序可能崩溃
```

### 日志记录
```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 使用适当的日志级别
logger.info("开始回测基金: %s", fund_code)
logger.warning("数据源不可用，尝试备用源")
logger.error("获取数据失败: %s", error_message)
```

### DataFrame 操作
```python
# 优先使用方法链
df = (
    df.rename(columns={'old': 'new'})
    .dropna()
    .sort_values('date')
)

# 避免链式索引
df.loc[df['col'] > 0, 'result'] = 1  # 正确
```

### 可视化
```python
# 使用英文标签避免字体问题
ax.set_title('Portfolio Value')
ax.set_xlabel('Date')
ax.set_ylabel('Amount')

# 使用 tight_layout
plt.tight_layout()

# 带 dpi 保存图片
plt.savefig('chart.png', dpi=150, bbox_inches='tight')
```

### 配置
- 所有配置放在 `data_source/config.py`
- 使用环境变量或配置文件存储密钥
- 永远不要在源代码中硬编码 API 令牌

## Git 工作流
- 提交信息：使用conventional格式（feat:、fix:、refactor:等）
- 保持提交原子性和专注性
- 完成功能后推送到远程

## 常见模式

### 数据源降级
```python
def get_data(self, fund_code: str) -> Optional[pd.DataFrame]:
    sources = ['tushare', 'akshare', 'baostock']
    
    for source in sources:
        try:
            data = self._fetch_from_source(source, fund_code)
            if data is not None:
                return data
        except Exception as e:
            logger.warning(f"{source} 失败: {e}")
            continue
    
    return None  # 所有数据源都失败
```

### 缓存使用
```python
from backtest.cache_keys import CacheKeys, CacheTTL

# 设置缓存
cache.set(CacheKeys.report(report_id), data, ttl=CacheTTL.REPORT)

# 获取缓存
data = cache.get(CacheKeys.report(report_id))
```

### 报告保存
```python
from backtest.report_manager import ReportManager, ReportData

rm = ReportManager()
report_id = rm.save_report(backtest_result)

# 生成报告名称示例
# 招商银行_600036_2022-01-01-2024-12-31_止盈20%止损15%
```

## 测试框架

### 测试分类
- **单元测试**：DCA 回测核心逻辑 (`tests/test_dca_backtest.py`)
- **Manager 测试**：各管理器的 CRUD 操作 (`tests/ui/test_managers.py`)
- **集成测试**：端到端工作流 (`tests/ui/test_integration.py`)

### Fixtures
| Fixture | 说明 |
|---------|------|
| `clean_database` | 每个测试前清理数据库 |
| `clean_cache` | 每个测试前清空缓存 |
| `verify_db` | 验证数据库配置 |
| `mock_tushare` | Mock Tushare API |
| `mock_akshare` | Mock AkShare |

## 运行单个测试
```bash
# 使用 pytest
pytest tests/test_dca_backtest.py::TestDCABacktest::test_simple_dca_basic -v

# 运行管理器测试
pytest tests/ui/test_managers.py -v

# 运行集成测试
pytest tests/ui/test_integration.py -v
```

## VS Code / IDE 推荐设置
```json
{
    "python.linting.flake8Enabled": true,
    "python.formatting.provider": "black",
    "python.analysis.typeCheckingMode": "basic",
    "editor.formatOnSave": true,
    "files.exclude": {
        "**/__pycache__": true,
        "**/*.pyc": true
    }
}
```
