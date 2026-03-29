-- -*- coding: utf-8 -*-
-- MySQL 数据库初始化脚本
-- 运行前请确保 MySQL 服务已启动

-- 创建数据库
CREATE DATABASE IF NOT EXISTS stock_data CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE stock_data;

-- 股票基本信息表
CREATE TABLE IF NOT EXISTS stocks (
    code VARCHAR(10) PRIMARY KEY COMMENT '股票代码',
    name VARCHAR(100) NOT NULL COMMENT '股票名称',
    market VARCHAR(10) NOT NULL COMMENT '市场: SH/SZ',
    industry VARCHAR(50) COMMENT '所属行业',
    list_date DATE COMMENT '上市日期',
    delist_date DATE COMMENT '退市日期',
    stock_type VARCHAR(20) COMMENT '类型: ETF/股票/基金',
    full_code VARCHAR(20) COMMENT '完整代码如 600036.SH',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='股票基本信息';

-- 日线行情表
CREATE TABLE IF NOT EXISTS daily_kline (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    code VARCHAR(10) NOT NULL COMMENT '股票代码',
    trade_date DATE NOT NULL COMMENT '交易日期',
    open DECIMAL(10,3) COMMENT '开盘价',
    high DECIMAL(10,3) COMMENT '最高价',
    low DECIMAL(10,3) COMMENT '最低价',
    close DECIMAL(10,3) COMMENT '收盘价',
    volume DECIMAL(20,2) COMMENT '成交量',
    amount DECIMAL(20,2) COMMENT '成交额',
    adj_close DECIMAL(10,3) COMMENT '后复权收盘价',
    turn DECIMAL(10,4) COMMENT '换手率',
    pct_chg DECIMAL(10,4) COMMENT '涨跌幅',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_code_date (code, trade_date),
    INDEX idx_trade_date (trade_date),
    INDEX idx_code (code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='日线行情';

-- 利润表
CREATE TABLE IF NOT EXISTS income (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    code VARCHAR(10) NOT NULL COMMENT '股票代码',
    ann_date DATE COMMENT '公告日期',
    end_date DATE NOT NULL COMMENT '报告期',
    report_type INT COMMENT '报告类型: 1-年报 2-季报 3-半年报 4-三季报',
    total_revenue DECIMAL(20,2) COMMENT '营业总收入',
    oper_profit DECIMAL(20,2) COMMENT '营业利润',
    net_profit DECIMAL(20,2) COMMENT '净利润',
    total_revenue_yoy DECIMAL(10,4) COMMENT '营收同比',
    net_profit_yoy DECIMAL(10,4) COMMENT '净利润同比',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_code_end_report (code, end_date, report_type),
    INDEX idx_end_date (end_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='利润表';

-- 主要财务指标表
CREATE TABLE IF NOT EXISTS fina_indicator (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    code VARCHAR(10) NOT NULL COMMENT '股票代码',
    ann_date DATE COMMENT '公告日期',
    end_date DATE NOT NULL COMMENT '报告期',
    roe DECIMAL(10,4) COMMENT '净资产收益率',
    net_profit_margin DECIMAL(10,4) COMMENT '净利率',
    gross_profit_margin DECIMAL(10,4) COMMENT '毛利率',
    debt_to_assets DECIMAL(10,4) COMMENT '资产负债率',
    current_ratio DECIMAL(10,4) COMMENT '流动比率',
    quick_ratio DECIMAL(10,4) COMMENT '速动比率',
    pe_ttm DECIMAL(12,4) COMMENT '市盈率TTM',
    pb DECIMAL(10,4) COMMENT '市净率',
    ps_ttm DECIMAL(10,4) COMMENT '市销率TTM',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_code_end_fina (code, end_date),
    INDEX idx_ann_date (ann_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='主要财务指标';

-- 数据同步记录表
CREATE TABLE IF NOT EXISTS sync_log (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    table_name VARCHAR(50) NOT NULL COMMENT '表名',
    code VARCHAR(10) COMMENT '股票代码',
    start_date DATE COMMENT '开始日期',
    end_date DATE COMMENT '结束日期',
    status VARCHAR(20) DEFAULT 'running' COMMENT '状态: running/success/failed',
    records INT DEFAULT 0 COMMENT '同步记录数',
    error_msg TEXT COMMENT '错误信息',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_status (status),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='数据同步记录';

-- ==================== 回测相关表 ====================

-- 回测报告表
CREATE TABLE IF NOT EXISTS reports (
    id VARCHAR(8) PRIMARY KEY COMMENT '报告ID',
    name VARCHAR(200) NOT NULL COMMENT '报告名称',
    created_at DATETIME NOT NULL COMMENT '创建时间',
    fund_code VARCHAR(10) NOT NULL COMMENT '基金代码',
    fund_name VARCHAR(100) COMMENT '基金名称',
    start_date DATE NOT NULL COMMENT '开始日期',
    end_date DATE NOT NULL COMMENT '结束日期',
    investment_amount DECIMAL(12,2) COMMENT '每次投入金额',
    frequency VARCHAR(20) COMMENT '频率',
    strategy_params TEXT COMMENT '策略参数JSON',
    result TEXT COMMENT '回测结果JSON',
    trades TEXT COMMENT '交易记录JSON',
    INDEX idx_fund_code (fund_code),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='回测报告';

-- 自选股列表表
CREATE TABLE IF NOT EXISTS watchlists (
    id VARCHAR(8) PRIMARY KEY COMMENT '列表ID',
    name VARCHAR(100) NOT NULL COMMENT '列表名称',
    description VARCHAR(500) COMMENT '描述',
    created_at DATETIME NOT NULL COMMENT '创建时间',
    updated_at DATETIME NOT NULL COMMENT '更新时间',
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='自选股列表';

-- 自选股列表中的股票
CREATE TABLE IF NOT EXISTS watchlist_stocks (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    watchlist_id VARCHAR(8) NOT NULL COMMENT '列表ID',
    code VARCHAR(10) NOT NULL COMMENT '股票代码',
    name VARCHAR(100) COMMENT '股票名称',
    market VARCHAR(20) DEFAULT 'A股' COMMENT '市场',
    type VARCHAR(20) DEFAULT 'ETF' COMMENT '类型',
    notes VARCHAR(500) COMMENT '备注',
    tags TEXT COMMENT '标签JSON',
    UNIQUE KEY uk_watchlist_code (watchlist_id, code),
    INDEX idx_watchlist_id (watchlist_id),
    FOREIGN KEY (watchlist_id) REFERENCES watchlists(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='自选股列表中的股票';

-- 策略模板表
CREATE TABLE IF NOT EXISTS strategy_templates (
    id VARCHAR(8) PRIMARY KEY COMMENT '策略ID',
    name VARCHAR(100) NOT NULL COMMENT '策略名称',
    group_name VARCHAR(50) NOT NULL COMMENT '分组',
    description VARCHAR(500) COMMENT '描述',
    params TEXT COMMENT '策略参数JSON',
    color VARCHAR(20) DEFAULT '#1f77b4' COMMENT '颜色',
    is_default BOOLEAN DEFAULT FALSE COMMENT '是否默认',
    created_at DATETIME NOT NULL COMMENT '创建时间',
    updated_at DATETIME NOT NULL COMMENT '更新时间',
    INDEX idx_group_name (group_name),
    INDEX idx_is_default (is_default)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='策略模板';

-- 创建存储过程：清理旧数据（保留最近N年）
DELIMITER //
CREATE PROCEDURE IF NOT EXISTS cleanup_old_data(IN years_to_keep INT)
BEGIN
    DECLARE cutoff_date DATE;
    SET cutoff_date = DATE_SUB(CURDATE(), INTERVAL years_to_keep YEAR);
    
    DELETE FROM daily_kline WHERE trade_date < cutoff_date;
    DELETE FROM income WHERE end_date < cutoff_date;
    DELETE FROM fina_indicator WHERE end_date < cutoff_date;
    
    SELECT CONCAT('已清理 ', years_to_keep, ' 年前的数据') AS result;
END //
DELIMITER ;

-- 示例：保留最近5年数据
-- CALL cleanup_old_data(5);
