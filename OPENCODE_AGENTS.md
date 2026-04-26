# OpenCode 全局配置

## 概述

本文件定义了 AI 开发助手 (OpenCode) 在本项目中的全局配置和行为规范。

---

## 语言要求

- **AI 必须使用中文回复**
- 所有代码注释、文档、提交信息使用中文（或英文，符合项目规范）
- 与用户交流时使用简体中文

---

## 代码审查原则

- 不更改现有功能逻辑，仅修复 bug 或添加新功能
- 修改代码前先阅读理解现有代码风格
- 保持代码简洁，避免过度工程化

---

## 响应规范

- 避免不必要的开场白和总结
- 直接回答用户问题
- 保持简洁，优先给出结论或方案

---

## 任务执行

### 执行流程
1. 执行前先理解需求，必要时询问用户确认
2. 完成后运行 lint/typecheck 确保代码正确
3. 不主动 commit，除非用户明确要求
4. 永远不要忘了更新文档和增加 UT 测试

### 测试命令
```bash
# 运行所有测试
pytest tests/ -v

# 运行单个测试
pytest tests/test_dca_backtest.py::TestDCABacktest::test_simple_dca_basic -v

# flake8 检查
flake8 .

# type check
python3 -m mypy .
```

---

## Python 项目规范

### 代码风格
- 使用类型注解
- 导入顺序：标准库 > 第三方库 > 本地模块
- 函数/类使用 snake_case / PascalCase

### 命名规范
- 变量/函数：snake_case
- 类名：PascalCase
- 常量：UPPER_SNAKE_CASE

### 异常处理
- 异常需要捕获并记录日志
- 使用适当的日志级别 (DEBUG/INFO/WARNING/ERROR/CRITICAL)

### DataFrame 操作
- 使用方法链
- 避免链式索引

---

## 项目技术栈

| 技术 | 说明 |
|------|------|
| Python 3.12+ | 运行环境 |
| Streamlit | Web UI 框架 |
| SQLAlchemy | ORM |
| MySQL | 数据库 |
| Redis | 缓存 |
| Tushare | 金融数据源 |
| Pandas | 数据处理 |

---

## 常用命令

```bash
# Web UI
streamlit run app.py

# 数据同步
python3 scripts/sync_fund_nav.py
nohup python3 scripts/sync_fund_nav.py > logs/sync_fund_nav.log 2>&1 &

# 数据库状态
python3 -c "
from data_source.db.connection import get_db_session
from data_source.db.models import FundNav
with get_db_session() as s:
    print(f'NAV: {s.query(FundNav).count()}')
"
```

---

## 分支策略

- 主分支：`main`
- 提交信息：使用conventional格式
  - `feat:` 新功能
  - `fix:` bug修复
  - `refactor:` 重构
  - `chore:` 构建/工具
  - `docs:` 文档

---

## Git 工作流

1. 所有更改在本地完成
2. 用户明确要求后 commit
3. 推送到远程

### 推送命令
```bash
GIT_SSH_COMMAND="ssh -o StrictHostKeyChecking=no" git push
```