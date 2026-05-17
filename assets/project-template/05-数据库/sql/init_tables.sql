-- ===================================================
-- 数据库初始化SQL
-- 项目：[项目名称]
-- 创建日期：2025-10-27
-- 说明：创建所有核心表
-- ===================================================

-- 设置字符集
SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ===================================================
-- 用户表（示例）
-- ===================================================
CREATE TABLE IF NOT EXISTS `users` (
  `id` BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY COMMENT '用户ID',
  `username` VARCHAR(64) NOT NULL UNIQUE COMMENT '用户名',
  `email` VARCHAR(255) DEFAULT NULL COMMENT '邮箱',
  `phone` VARCHAR(20) DEFAULT NULL COMMENT '手机号',
  `password_hash` VARCHAR(255) NOT NULL COMMENT '密码hash',
  `status` TINYINT DEFAULT 1 COMMENT '状态：0-禁用，1-正常',
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `deleted_at` DATETIME DEFAULT NULL COMMENT '删除时间（软删除）',
  INDEX `idx_username` (`username`),
  INDEX `idx_email` (`email`),
  INDEX `idx_phone` (`phone`),
  INDEX `idx_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户表';

-- ===================================================
-- 其他表（根据实际需求添加）
-- ===================================================

-- 示例：订单表
-- CREATE TABLE IF NOT EXISTS `orders` (
--   `id` BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY COMMENT '订单ID',
--   `user_id` BIGINT UNSIGNED NOT NULL COMMENT '用户ID',
--   `order_no` VARCHAR(32) NOT NULL UNIQUE COMMENT '订单号',
--   `amount` DECIMAL(10,2) NOT NULL COMMENT '订单金额',
--   `status` TINYINT DEFAULT 1 COMMENT '状态：1-待支付，2-已支付',
--   `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
--   `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
--   INDEX `idx_user_id` (`user_id`),
--   INDEX `idx_order_no` (`order_no`),
--   INDEX `idx_status` (`status`),
--   FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE CASCADE
-- ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='订单表';

-- ===================================================
-- 初始化数据（可选）
-- ===================================================

-- 示例：插入默认管理员账号
-- INSERT INTO `users` (`username`, `email`, `password_hash`, `status`) VALUES
-- ('admin', 'admin@example.com', '$2b$12$...', 1);

-- ===================================================
-- 完成
-- ===================================================
SET FOREIGN_KEY_CHECKS = 1;

-- 查看已创建的表
SHOW TABLES;

