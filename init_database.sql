-- 三分钟热情项目管理系统 - 数据库初始化脚本
-- 创建时间: 2025-11-13

-- 创建数据库（如果不存在）
CREATE DATABASE IF NOT EXISTS `threemins` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE `threemins`;

-- 1. 兴趣孵化池表
CREATE TABLE IF NOT EXISTS `incubator` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `idea` TEXT NOT NULL COMMENT '想法内容',
    `notes` TEXT COMMENT '备注',
    `created_at` DATETIME NOT NULL COMMENT '创建时间',
    `status` VARCHAR(20) NOT NULL DEFAULT 'pending' COMMENT '状态：pending-待处理',
    INDEX `idx_status` (`status`),
    INDEX `idx_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='兴趣孵化池';

-- 2. 进行中实验表
CREATE TABLE IF NOT EXISTS `active_experiments` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `idea` TEXT NOT NULL COMMENT '想法内容',
    `goal` TEXT NOT NULL COMMENT '目标',
    `budget` DECIMAL(10, 2) DEFAULT 0.00 COMMENT '预算',
    `start_date` DATE NOT NULL COMMENT '开始日期',
    `end_date` DATE NOT NULL COMMENT '结束日期',
    `duration_days` INT NOT NULL DEFAULT 21 COMMENT '持续天数',
    `status` VARCHAR(20) NOT NULL DEFAULT 'active' COMMENT '状态：active-进行中',
    `created_at` DATETIME NOT NULL COMMENT '创建时间',
    INDEX `idx_status` (`status`),
    INDEX `idx_end_date` (`end_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='进行中的实验';

-- 3. 实验进度记录表
CREATE TABLE IF NOT EXISTS `progress_notes` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `experiment_id` INT NOT NULL COMMENT '实验ID',
    `note` TEXT NOT NULL COMMENT '进度记录内容',
    `created_at` DATETIME NOT NULL COMMENT '记录时间',
    FOREIGN KEY (`experiment_id`) REFERENCES `active_experiments`(`id`) ON DELETE CASCADE,
    INDEX `idx_experiment_id` (`experiment_id`),
    INDEX `idx_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='实验进度记录';

-- 4. 项目档案馆表
CREATE TABLE IF NOT EXISTS `archive` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `idea` TEXT NOT NULL COMMENT '想法内容',
    `goal` TEXT NOT NULL COMMENT '目标',
    `start_date` DATE NOT NULL COMMENT '开始日期',
    `end_date` DATE NOT NULL COMMENT '结束日期',
    `completed_at` DATETIME NOT NULL COMMENT '完成时间',
    `skill_learned` TEXT COMMENT '学到的技能',
    `experience` TEXT COMMENT '过程体验',
    `connection` TEXT COMMENT '连接可能性',
    INDEX `idx_completed_at` (`completed_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='项目档案馆';

-- 5. 归档项目进度记录表（从实验进度记录复制）
CREATE TABLE IF NOT EXISTS `archive_progress_notes` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `archive_id` INT NOT NULL COMMENT '归档项目ID',
    `note` TEXT NOT NULL COMMENT '进度记录内容',
    `created_at` DATETIME NOT NULL COMMENT '记录时间',
    FOREIGN KEY (`archive_id`) REFERENCES `archive`(`id`) ON DELETE CASCADE,
    INDEX `idx_archive_id` (`archive_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='归档项目进度记录';

