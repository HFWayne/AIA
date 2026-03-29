# 变更记录

所有版本变更和 TODO 需求记录。

---

## TODO 待开发功能

### 高优先级

**Phase 1: 自选股管理** ✅ 已完成
- [x] **自选股数据模型** - 定义 Watchlist、StockInfo 数据结构
- [x] **自选股存储** - 保存到 `reports/watchlists.json`
- [x] **自选股 UI** - 列表管理（创建/删除/重命名）
- [x] **股票管理 UI** - 添加/删除/编辑股票，支持搜索
- [x] **预设自选股** - 内置 ETF 列表（宽基/行业/红利）

**Phase 2: 策略管理** ✅ 已完成
- [x] **策略模板数据模型** - 定义 StrategyTemplate 数据结构
- [x] **策略存储** - 保存到 `reports/strategies.json`
- [x] **策略管理 UI** - 创建/编辑/删除策略模板
- [x] **策略分组** - 支持按分组筛选（保守型/激进型/增强型/我的策略）
- [x] **预设策略** - 内置 6 个策略模板

**Phase 3: 任务管理** ✅ 已完成
- [x] **任务数据模型** - 定义 AutoTask、StockItem、StrategyConfig 数据结构
- [x] **多策略选择** - 支持任务中多选策略
- [x] **异步执行引擎** - 后台执行，不阻塞 UI
- [x] **进度展示** - 进度条、当前股票、日志
- [x] **任务状态持久化** - 保存到 `reports/auto/TASKS.json`

### 数据库开发 ✅ 新增

**Phase 1: MySQL 存储层**
- [x] MySQL 数据库配置
- [x] SQLAlchemy 数据模型（stocks, daily_kline, income, fina_indicator, sync_log）
- [x] 数据库连接池封装
- [x] 初始化 SQL 脚本

**Phase 2: Redis 缓存层**
- [x] Redis 配置
- [x] 缓存客户端封装（get/set/批量/模式清除）
- [x] 缓存 Key 命名空间

**Phase 3: 数据同步服务**
- [x] tushare 数据拉取服务
- [x] 股票列表同步
- [x] 日线行情同步（支持后复权）
- [x] 财务数据同步（利润表、财务指标）
- [x] 命令行同步工具

**Phase 4: 集成与优化**
- [x] FundDataSource 集成缓存（Redis -> MySQL -> API 优先级）
- [x] 缓存命中率统计
- [ ] 数据更新监控页面

### 中优先级

**国际化 (i18n)** ✅ 已完成
- [x] **翻译框架** - `i18n/` 模块，字典式翻译系统
- [x] **中英文支持** - zh_CN / en_US 语言包
- [x] **语言切换器** - Streamlit 侧边栏语言选择组件
- [x] **完整翻译** - 侧边栏、回测页面、对比页面、报告管理页面全部翻译

- [ ] **股票搜索自动补全** - 集成数据源，模糊搜索
- [ ] **任务模板** - 保存任务配置为模板复用
- [ ] **批量标签管理** - 给报告批量添加/移除标签
- [ ] **执行日志导出** - 导出回测执行日志
- [ ] **补仓份额单独跟踪** - 记录补仓成本和收益
- [ ] **移动端适配** - 响应式布局优化，适合手机访问

### 低优先级（后续扩展）

- [ ] **沪深港通持股数据同步** - 跟踪外资动向
- [ ] **融资融券数据同步** - 杠杆分析数据
- [ ] **股东户数数据同步** - 人心变化数据
- [ ] **指数成分数据同步** - 指数跟踪数据
- [ ] **定时任务** - 支持每日/每周定时执行（需后台服务）
- [ ] **邮件/推送通知** - 回测完成通知
- [ ] **策略参数优化** - 网格搜索最优参数
- [ ] **报告对比 PDF 导出** - 生成对比报告 PDF
- [ ] **Excel 数据导出** - 导出回测数据到 Excel
- [ ] **自选股同步** - 支持导入/导出 CSV
- [ ] **股票详情页** - 显示基本信息、历史表现
- [ ] **探索 backtrader 集成** - 研究 backtrader 库高级功能

---

## v1.6.0 - 2026-03-29

### 新增功能

**国际化 (i18n)**
- `i18n/` 模块，字典式翻译框架
- zh_CN / en_US 语言包，包含 200+ 翻译 key
- `t()` 翻译函数，支持字符串插值
- `render_language_selector()` 语言切换组件
- Streamlit 会话状态持久化语言选择

---

## v1.5.0 - 2026-03-29

### 新增功能

**回测结果分析 (backtest/analysis.py)**
- 夏普比率计算
- 卡玛比率计算
- 索提诺比率计算
- 最大回撤及持续时间
- 胜率和盈亏比
- 多策略对比分析

**报告导出 (backtest/report_exporter.py)**
- Excel 多 sheet 导出（汇总、交易记录、策略参数）
- CSV 导出
- 多报告对比导出

**进度追踪 (backtest/progress.py)**
- 实时进度回调
- 多任务并发追踪
- Streamlit 进度条支持

**分级缓存 (data_source/cache/tiered_cache.py)**
- L1 内存 LRU 缓存
- L2 Redis 缓存
- 缓存预热服务

**增量数据同步 (data_source/sync/free_sync.py)**
- 自动检测最新日期
- 进度回调支持
- 自选股批量同步

**自动化测试**
- 63+ 单元测试
- 回测分析测试
- 报告导出测试
- 进度追踪测试
- 分级缓存测试

### Bug修复

- 修复 `use_container_width` 弃用警告（改为 `width='stretch'`）
- 修复 Report 类名与 SQLAlchemy 模型冲突

---

## v1.4.0 - 2026-03-27

### 新增功能

**数据库存储层 (MySQL)**
- SQLAlchemy ORM 模型：stocks、daily_kline、income、fina_indicator、sync_log
- 数据库连接池（PyMySQL + QueuePool）
- 初始化 SQL 脚本 (`data_source/db/migrations/init.sql`)

**缓存层 (Redis)**
- Redis 客户端封装，支持 get/set/批量/模式清除
- 缓存 Key 命名空间规范
- 缓存过期时间配置

**数据同步服务**
- TushareSync：股票列表、日线行情、财务数据同步
- 命令行工具：`python -m data_source.db.migrations`
- 支持全量同步和增量同步

### 优化改进

- FundDataSource 改造：Redis缓存 -> MySQL数据库 -> tushare API 优先级获取
- 缓存命中率统计功能
- 数据自动持久化到本地数据库

### 使用方法

```bash
# 1. 确保 MySQL 和 Redis 已启动
# 2. 配置环境变量（或修改 config.py）
export MYSQL_HOST=localhost
export MYSQL_PASSWORD=your_password
export REDIS_HOST=localhost

# 3. 初始化数据库
python -m data_source.db.migrations --init

# 4. 同步股票列表
python -m data_source.db.migrations --sync-stocks

# 5. 同步单只股票历史数据
python -m data_source.db.migrations --code 510300

# 6. 全量同步（首次运行，需要较长时间）
python -m data_source.db.migrations --full

# 7. 每日增量同步
python -m data_source.db.migrations --incremental
```

---

## v1.3.0 - 2026-03-27

### 新增功能

**自选股管理**
- 自选股数据模型和存储（`reports/watchlists.json`）
- UI 支持创建/删除/重命名自选股列表
- 股票管理：添加/删除/编辑股票
- 预设自选股：宽基ETF、行业ETF、红利基金

**策略管理**
- 策略模板数据模型和存储（`reports/strategies.json`）
- UI 支持创建/编辑/删除策略模板
- 策略分组：保守型、激进型、增强型、我的策略
- 6 个预设策略模板

### 优化改进

- 自选股页面优化：使用表格展示，更紧凑、信息更丰富
- 添加股票支持只输入代码或名称之一
- 列表设置支持修改名称和描述
- 新建列表时可选择预设股票
- **添加股票时自动从 tushare 获取信息**：股票名称、市场、类型、行业
- **添加股票时验证代码有效性**：自动检查股票代码是否合法

---

## v1.2.1 - 2026-03-26

### Bug修复

- 修复类型注解问题：List -> List[datetime]，添加 Optional 类型注解
- 修复 Streamlit `use_container_width` 弃用警告
- 移除 `plt.show()` 调用，避免 FigureCanvasAgg 警告
- **数据源改为后复权**：tushare 添加 `adj='hfq'`，baostock `adjustflag="2"`
  - 保证回测收益率计算准确（包含分红再投资收益）

### 优化改进

- 清理未使用的 imports
- 代码风格统一

---

## v1.2.0 - 2026-03-25

### 新增功能

- **补仓策略**
  - 单日大跌补仓：支持3档固定设置（-3%、-5%、-7%），每档可设置不同补仓金额
  - 累计收益率增额定投：收益率低于阈值时增加定投额度，回升到恢复阈值时还原
  - 两策略可同时启用
- **月/周定投日期设置**
  - 月定投可选每月1-28日
  - 周定投可选周一至周五
  - 支持顺延：指定日期无交易数据时自动顺延到最近交易日

### Bug修复

- 修复月定投频率计算问题：`>=` 改为 `==`，避免所有 day>=1 的交易日都定投
- 修复 `buy_dip` 份额（shares）和投入金额（invest_amount）为0的问题

### 优化改进

- 交易记录新增 `invest_amount` 字段，记录每次操作的实际投入金额
- 回测结果新增统计字段：`dip_buy_count`、`dip_buy_amount`、`boost_count`、`boost_amount`
- 报告管理页面优化：删除后自动刷新

---

## v1.1.0 - 2026-03-24

### 新增功能

- **报告管理功能**
  - 保存回测报告到本地 JSON 文件
  - 查看已保存的报告列表
  - 查看报告详情（指标、图表、交易记录）
  - 对比多个报告的收益表现
  - 支持按股票代码筛选和关键词搜索
- **止损止盈策略**
  - 止损：收益率低于阈值时按比例卖出
  - 止盈（最大回撤法）：达到目标收益率后追踪高点，从高点回撤超过阈值时卖出

### 优化改进

- 移除 CLI 版本（main.py），保留 Web UI
- 更新 README.md 文档

---

## v1.0.0 - 2026-03-23

### 新增功能

- **数据源接口**
  - 支持 tushare、akshare、baostock 三个数据源
  - 自动降级：主数据源失败时自动切换到备用数据源
  - 接口保护：添加 REQUEST_DELAY 防止 API 频率限制
- **Streamlit Web UI**
  - 单股票回测：输入股票代码、时间范围、定投参数，查看回测结果
  - 多股票对比：输入多个股票代码，对比收益表现
  - 可视化图表：净值走势、投入收益曲线、收益对比等
- **单元测试**
  - DCA 回测核心逻辑测试
  - 止损止盈策略测试
  - 报告管理器测试

### 初始项目结构

```
├── app.py                    # Streamlit Web UI
├── data_source/
│   ├── config.py            # 配置
│   └── fund_data_source.py # 数据源接口
├── backtest/
│   ├── dca_backtest.py     # 回测核心逻辑
│   ├── visualization.py      # 可视化
│   └── report_manager.py     # 报告管理
├── tests/                   # 单元测试
└── README.md               # 文档
```
