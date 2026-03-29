-- ============================================
-- 股票定投回测系统 - 数据库表结构
-- 目标数据库: stock_data
-- ============================================

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ----------------------------
-- 表 1: 自选股列表
-- ----------------------------
DROP TABLE IF EXISTS `watchlists`;
CREATE TABLE `watchlists` (
  `id` VARCHAR(8) NOT NULL COMMENT '列表ID',
  `name` VARCHAR(100) NOT NULL COMMENT '列表名称',
  `description` VARCHAR(500) NULL DEFAULT NULL COMMENT '描述',
  `created_at` DATETIME NOT NULL COMMENT '创建时间',
  `updated_at` DATETIME NOT NULL COMMENT '更新时间',
  PRIMARY KEY (`id`),
  INDEX `idx_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='自选股列表';

-- ----------------------------
-- 表 2: 自选股列表中的股票
-- ----------------------------
DROP TABLE IF EXISTS `watchlist_stocks`;
CREATE TABLE `watchlist_stocks` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT 'ID',
  `watchlist_id` VARCHAR(8) NOT NULL COMMENT '列表ID',
  `code` VARCHAR(10) NOT NULL COMMENT '股票代码',
  `name` VARCHAR(100) NULL DEFAULT NULL COMMENT '股票名称',
  `market` VARCHAR(20) NULL DEFAULT 'A股' COMMENT '市场',
  `type` VARCHAR(20) NULL DEFAULT 'ETF' COMMENT '类型',
  `notes` VARCHAR(500) NULL DEFAULT NULL COMMENT '备注',
  `tags` TEXT NULL DEFAULT NULL COMMENT '标签JSON',
  PRIMARY KEY (`id`),
  UNIQUE INDEX `uk_watchlist_code` (`watchlist_id`, `code`),
  INDEX `idx_watchlist_id` (`watchlist_id`),
  FOREIGN KEY (`watchlist_id`) REFERENCES `watchlists`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='自选股列表中的股票';

-- ----------------------------
-- 表 3: 回测报告
-- ----------------------------
DROP TABLE IF EXISTS `reports`;
CREATE TABLE `reports` (
  `id` VARCHAR(8) NOT NULL COMMENT '报告ID',
  `name` VARCHAR(200) NOT NULL COMMENT '报告名称',
  `created_at` DATETIME NOT NULL COMMENT '创建时间',
  `fund_code` VARCHAR(10) NOT NULL COMMENT '基金代码',
  `fund_name` VARCHAR(100) NULL DEFAULT NULL COMMENT '基金名称',
  `start_date` DATE NOT NULL COMMENT '开始日期',
  `end_date` DATE NOT NULL COMMENT '结束日期',
  `investment_amount` DECIMAL(12,2) NULL DEFAULT NULL COMMENT '每次投入金额',
  `frequency` VARCHAR(20) NULL DEFAULT NULL COMMENT '频率',
  `strategy_params` TEXT NULL DEFAULT NULL COMMENT '策略参数JSON',
  `result` TEXT NULL DEFAULT NULL COMMENT '回测结果JSON',
  `trades` TEXT NULL DEFAULT NULL COMMENT '交易记录JSON',
  PRIMARY KEY (`id`),
  INDEX `idx_fund_code` (`fund_code`),
  INDEX `idx_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='回测报告';

-- ----------------------------
-- 表 4: 策略模板
-- ----------------------------
DROP TABLE IF EXISTS `strategy_templates`;
CREATE TABLE `strategy_templates` (
  `id` VARCHAR(8) NOT NULL COMMENT '策略ID',
  `name` VARCHAR(100) NOT NULL COMMENT '策略名称',
  `group_name` VARCHAR(50) NOT NULL COMMENT '分组',
  `description` VARCHAR(500) NULL DEFAULT NULL COMMENT '描述',
  `params` TEXT NULL DEFAULT NULL COMMENT '策略参数JSON',
  `color` VARCHAR(20) NULL DEFAULT '#1f77b4' COMMENT '颜色',
  `is_default` TINYINT(1) NULL DEFAULT 0 COMMENT '是否默认',
  `created_at` DATETIME NOT NULL COMMENT '创建时间',
  `updated_at` DATETIME NOT NULL COMMENT '更新时间',
  PRIMARY KEY (`id`),
  INDEX `idx_group_name` (`group_name`),
  INDEX `idx_is_default` (`is_default`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='策略模板';

SET FOREIGN_KEY_CHECKS = 1;

-- ============================================
-- 验证表是否创建成功
-- ============================================
SHOW TABLES;
