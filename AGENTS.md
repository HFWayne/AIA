# AGENTS.md - AI 开发者指南

## 项目概述

这是一个 Python 股票/基金数据分析和 DCA（定期定额投资）回测项目，提供：
- 统一数据源接口，支持 tushare、akshare、baostock
- 带可视化功能的 DCA 回测引擎
- 运行回测的命令行工具

## 构建/测试/运行命令

### 运行应用程序
```bash
# 单基金回测
python main.py --fund 600036 --name 招商银行

# 多基金对比
python main.py --compare --funds 600036,000001 --start 2022-01-01 --end 2024-12-31

# 指定数据源
python main.py --fund 600036 --source tushare
```

### 运行 Web UI (Streamlit)
```bash
streamlit run app.py
```

### 测试
```bash
# 运行 pytest（如果存在测试）
pytest

# 运行单个测试
pytest tests/test_file.py::test_function

# 带覆盖率运行
pytest --cov=. --cov-report=html
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

### 类型注解
```python
def get_fund_nav(
    fund_code: str,
    start_date: str,
    end_date: str
) -> Optional[pd.DataFrame]:
    """获取基金净值数据。
    
    参数:
        fund_code: 基金代码（如 "510300"）
        start_date: 开始日期，YYYYMMDD 格式
        end_date: 结束日期，YYYYMMDD 格式
        
    返回:
        包含 date, nav, accum_nav 列的 DataFrame，失败返回 None
    """
    pass
```

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

# 谨慎使用 inplace
df.dropna(inplace=True)  # 大数据集可以

# 避免链式索引
df.loc[df['col'] > 0, 'result'] = 1  # 正确
# df['result'][df['col'] > 0] = 1    # 错误
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

### 文件结构
```
project/
├── data_source/          # 数据源接口
│   ├── config.py        # 配置
│   └── fund_data_source.py
├── backtest/            # 回测逻辑
│   ├── dca_backtest.py
│   └── visualization.py
├── tests/               # 单元测试（如果有）
├── main.py             # 命令行入口
├── app.py              # Streamlit Web UI
└── AGENTS.md           # 本文件
```

### Git 工作流
- 提交信息：使用conventional格式（feat:、fix:、refactor:等）
- 保持提交原子性和专注性
- 完成功能后推送到远程

### 常见模式

#### 数据源降级
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

#### 类定义
```python
from dataclasses import dataclass
from typing import Optional

@dataclass
class BacktestResult:
    """回测结果"""
    total_invested: float      # 总投入
    final_value: float         # 最终价值
    total_return: float        # 总收益
    return_rate: float         # 收益率
    annual_return: float       # 年化收益
    max_drawdown: float        # 最大回撤
    investment_count: int      # 投资次数
    nav_data: pd.DataFrame    # 净值数据
    trades: pd.DataFrame      # 交易记录
```

### 运行单个测试
```bash
# 使用 pytest
pytest tests/test_backtest.py::test_dca_calculation -v

# 使用 unittest
python -m unittest tests.test_backtest.TestDCABacktest.test_dca_calculation
```

### VS Code / IDE 推荐设置
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
