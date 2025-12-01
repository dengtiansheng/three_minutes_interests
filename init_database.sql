-- 三分钟热情项目管理系统 - 数据库初始化脚本（重构版）
-- 创建时间: 2025-11-13
-- 重构时间: 2025-12-13
-- 重构说明: 使用统一的projects表替代原来的incubator、active_experiments、archive三个表

-- 创建数据库（如果不存在）
CREATE DATABASE IF NOT EXISTS `threemins` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE `threemins`;

-- 统一的项目表（替代原来的incubator、active_experiments、archive三个表）
-- 通过status字段区分：'concept'（概念/孵化池）、'active'（进行中实验）、'archived'（已归档）
CREATE TABLE IF NOT EXISTS `projects` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `idea` TEXT NOT NULL COMMENT '想法内容',
    `notes` TEXT COMMENT '备注（概念阶段使用）',
    `goal` TEXT COMMENT '目标（实验和归档阶段使用）',
    `budget` DECIMAL(10, 2) DEFAULT 0.00 COMMENT '预算（实验阶段使用）',
    `start_date` DATE COMMENT '开始日期（实验和归档阶段使用）',
    `end_date` DATE COMMENT '结束日期（实验和归档阶段使用）',
    `duration_days` INT DEFAULT 21 COMMENT '持续天数（实验阶段使用）',
    `completed_at` DATETIME COMMENT '完成时间（归档阶段使用）',
    `skill_learned` TEXT COMMENT '学到的技能（归档阶段使用）',
    `experience` TEXT COMMENT '过程体验（归档阶段使用）',
    `connection` TEXT COMMENT '连接可能性（归档阶段使用）',
    `status` VARCHAR(20) NOT NULL DEFAULT 'concept' COMMENT '状态：concept-概念/孵化池, active-进行中实验, archived-已归档',
    `created_at` DATETIME NOT NULL COMMENT '创建时间',
    `updated_at` DATETIME NOT NULL COMMENT '更新时间',
    INDEX `idx_status` (`status`),
    INDEX `idx_created_at` (`created_at`),
    INDEX `idx_end_date` (`end_date`),
    INDEX `idx_completed_at` (`completed_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='统一项目表';

-- 进度记录表（统一引用projects表）
CREATE TABLE IF NOT EXISTS `progress_notes` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `project_id` INT NOT NULL COMMENT '项目ID（引用projects表）',
    `note` TEXT NOT NULL COMMENT '进度记录内容',
    `created_at` DATETIME NOT NULL COMMENT '记录时间',
    FOREIGN KEY (`project_id`) REFERENCES `projects`(`id`) ON DELETE CASCADE,
    INDEX `idx_project_id` (`project_id`),
    INDEX `idx_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='项目进度记录';
