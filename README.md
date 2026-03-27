# 📈 股票定投回测工具

一个基于 Python 的股票/基金 DCA（定期定额投资）回测系统，支持 Streamlit Web 界面。

## 功能特性

- ✅ **本地数据库存储**：MySQL 存储历史数据，支持多年回测
- ✅ **Redis 缓存加速**：热点数据缓存，大幅减少 API 调用
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
- ✅ **可视化图表**：净值走势、投入收益曲线、K线图、收益对比等
- ✅ **报告管理**：保存、加载、对比历史回测报告
- ✅ **自动回测任务**：多股票多策略批量回测
- ✅ **自选股管理**：股票池管理，支持分组
- ✅ **策略模板**：预设多种策略，快速复用

## 快速开始

### 1. 安装依赖

```bash
pip install streamlit pandas matplotlib tushare akshare baostock sqlalchemy pymysql redis
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

系统支持将 tushare 数据同步到本地 MySQL 数据库，并使用 Redis 缓存热点数据：

```
请求 → Redis缓存（命中直接返回）
      ↓ 未命中
    MySQL数据库（命中返回并缓存）
      ↓ 未命中
    tushare API（获取后存入数据库和缓存）
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
# 注意：这是高效模式，按日期批量获取，效率高
python -m data_source.db.migrations --full

# 每日增量同步（建议每天定时执行）
python -m data_source.db.migrations --incremental

# 查看数据统计
python -m data_source.db.migrations --stats
```

### 补齐遗漏数据

如果某天忘记执行增量同步，可以使用以下命令自动检测并补齐：

```bash
# 检测并补齐缺失数据（默认检测最近30天）
python -m data_source.db.migrations --missing

# 指定检测天数范围
python -m data_source.db.migrations --missing 60

# 仅检查缺失情况（不补齐）
python -m data_source.db.migrations --check-missing
```

### 按日期范围同步

```bash
# 按指定日期同步所有股票
python -m data_source.db.migrations --date 20240325

# 按日期范围同步（YYYYMMDD YYYYMMDD）
python -m data_source.db.migrations --range 20200101 20240325
```

### 设置定时任务

#### Windows 任务计划程序

```batch
# 创建每日下午6点执行的任务
schtasks /create /tn "StockDataSync" /tr "python E:\code\AIA\data_source\db\migrations\__main__.py --incremental" /sc daily /st 18:00
```

#### Linux crontab

```bash
# 编辑 crontab
crontab -e

# 添加以下行：每天下午6点执行
0 18 * * * cd /path/to/AIA && python -m data_source.db.migrations --incremental >> logs/sync.log 2>&1
```

## 使用说明

### 自选股管理

1. 切换到"⭐ 自选股" Tab
2. 创建股票池（如：宽基ETF、行业ETF）
3. 添加股票：
   - 按代码添加（支持自动查询股票信息）
   - 按名称搜索（从tushare搜索）
   - 批量添加
   - 选择预设ETF

### 策略管理

1. 切换到"🎯 策略管理" Tab
2. 使用预设策略（基础定投、稳健定投、积极定投等）
3. 或创建自定义策略，设置：
   - 投资频率和金额
   - 止损止盈参数
   - 补仓策略
   - 收益增强策略

### 自动回测任务

1. 切换到"📋 自动回测" Tab
2. 选择自选股列表和策略
3. 设置日期范围
4. 点击"开始回测"
5. 查看进度和结果

### 单股票回测

1. 输入股票代码（如 600036）
2. 设置回测时间范围
3. 设置定投参数
4. 可选：启用止损/止盈策略
5. 点击"开始回测"
6. 可选：点击"保存报告"

### 多股票对比

1. 输入多个股票代码（逗号分隔）
2. 设置回测参数
3. 点击"开始对比"

## 止损止盈策略说明

### 止损策略

- **止损率**：当收益率低于此值时触发止损
- **卖出比例**：触发止损时卖出的持仓比例

### 止盈策略（最大回撤法）

1. **观察期**：当累计收益率达到目标收益率时，进入观察期
2. **追踪高点**：持续追踪持仓最高净值
3. **触发卖出**：当从高点回撤超过阈值时，按比例卖出

**示例**：
- 止盈收益率 = 20%
- 最大回撤阈值 = 10%
- 卖出比例 = 50%

```
收益达到20% → 进入观察期 → 记录高点22%
继续涨到25% → 更新高点25%
跌到23%（回撤8%）→ 不卖出
跌到22%（回撤12%）→ 触发卖出50%
```

## 项目结构

```
E:\code\AIA\
├── app.py                      # Streamlit Web 应用
├── data_source/
│   ├── config.py              # 配置文件（数据库、Redis、API配置）
│   ├── fund_data_source.py    # 数据源接口（缓存优先）
│   ├── cache/
│   │   └── redis_client.py    # Redis 缓存客户端
│   ├── db/
│   │   ├── models.py          # SQLAlchemy 数据模型
│   │   ├── connection.py      # 数据库连接池
│   │   └── migrations/
│   │       ├── init.sql      # MySQL 初始化脚本
│   │       └── __main__.py   # 命令行同步工具
│   └── sync/
│       ├── tushare_sync.py   # tushare 数据同步服务
│       └── scheduler.py       # 定时任务调度器
├── backtest/
│   ├── dca_backtest.py       # 回测核心逻辑
│   ├── visualization.py       # 可视化图表
│   ├── report_manager.py      # 报告管理器
│   ├── watchlist_manager.py   # 自选股管理器
│   ├── strategy_manager.py    # 策略管理器
│   ├── page_watchlist.py      # 自选股页面
│   ├── page_strategy.py       # 策略管理页面
│   └── page_task.py           # 自动回测任务页面
├── reports/                   # 保存的报告和数据
│   ├── watchlists.json       # 自选股列表
│   ├── strategies.json        # 策略模板
│   └── auto/                  # 自动回测报告
└── tests/                    # 单元测试
```

## 数据库表结构

| 表名 | 说明 |
|------|------|
| stocks | 股票/ETF 基础信息 |
| daily_kline | 日线行情数据 |
| income | 利润表数据 |
| fina_indicator | 主要财务指标 |
| sync_log | 数据同步记录 |

详细表结构请参考 `data_source/db/migrations/init.sql`

## 运行测试

```bash
pytest tests/ -v
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

1. tushare 免费版有接口调用频率限制，建议设置 `REQUEST_DELAY = 0.3`
2. 首次使用建议执行 `--full` 全量同步，可获取完整历史数据
3. 建议每天定时执行 `--incremental` 增量同步
4. 基金数据需要付费权限，股票数据使用 `daily` 接口
5. 回测结果仅供参考，不构成投资建议

## License

MIT
