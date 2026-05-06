-- ChatBI 数据库初始化脚本（包含示例数据）
-- 创建时间: 2026-02-07
-- 说明: 此脚本包含完整的表结构和示例数据

-- 创建数据库
CREATE DATABASE IF NOT EXISTS chatbi CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE chatbi;

-- ============================================
-- 1. 数据源表 (data_sources)
-- ============================================
DROP TABLE IF EXISTS `data_sources`;
CREATE TABLE `data_sources` (
  `id` varchar(36) NOT NULL COMMENT '数据源ID（UUID）',
  `name` varchar(100) NOT NULL COMMENT '数据源名称',
  `source_type` enum('DATABASE','FILE') NOT NULL COMMENT '数据源类型：DATABASE或FILE',
  `db_type` varchar(50) DEFAULT NULL COMMENT '数据库类型：MySQL、PostgreSQL等',
  `host` varchar(255) DEFAULT NULL COMMENT '数据库主机',
  `port` int DEFAULT NULL COMMENT '数据库端口',
  `database_name` varchar(100) DEFAULT NULL COMMENT '数据库名称',
  `auth_type` enum('SQL_AUTH','WINDOWS_AUTH') DEFAULT NULL COMMENT '认证方式',
  `username` varchar(100) DEFAULT NULL COMMENT '用户名',
  `password` varchar(255) DEFAULT NULL COMMENT '加密后的密码',
  `domain` varchar(100) DEFAULT NULL COMMENT '域',
  `file_path` varchar(500) DEFAULT NULL COMMENT '文件路径',
  `connection_status` enum('CONNECTED','DISCONNECTED','TESTING','FAILED') DEFAULT NULL COMMENT '连接状态',
  `last_test_time` datetime DEFAULT NULL COMMENT '最后测试时间',
  `description` text COMMENT '描述',
  `status` tinyint(1) DEFAULT '1' COMMENT '状态：1-启用，0-禁用',
  `created_by` varchar(50) DEFAULT 'system' COMMENT '创建人',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  KEY `idx_name` (`name`),
  KEY `idx_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='数据源配置表';

-- 插入示例数据源
INSERT INTO `data_sources` (`id`, `name`, `source_type`, `db_type`, `host`, `port`, `database_name`, `auth_type`, `username`, `password`, `status`, `created_by`, `created_at`, `updated_at`) VALUES
('9f1e3b14-f248-4950-8070-860e8276d873', 'mock data', 'DATABASE', 'MySQL', '127.0.0.1', 3306, 'mock_data', 'SQL_AUTH', 'root', 'Z0FBQUFBQnBnZjJ3U3hfd1hRSlMzMTBBVXFRVjlVWU11dkNseE9RZXJiS1h2MF9nVnkxeHRmc29zY25RamE4LTNDbDcyVG5vdHBEYk1tVnpsNG1VcFpPQTNfU1l5b3Iyc1E9PQ==', 1, 'system', '2026-02-03 21:52:48', '2026-02-03 21:52:48'),
('0ef69205-1c8a-4632-8597-48c91e1e6245', 'mysql_test_source', 'DATABASE', 'MySQL', '127.0.0.1', 3306, 'Mock_data', 'SQL_AUTH', 'root', 'Z0FBQUFBQnBnV2JidmJDUzc0NTVhTUlQTk1RaGEySmhHaThuWWN4SGhpRUFOTHM3SUVjeDBXckthLVpTREd2OTVtZUpZMVFNZDRrdl9IMDhoUVI3cU5MZXA1R0wyWUNTRkE9PQ==', 1, 'test_user', '2026-02-03 11:09:16', '2026-02-03 11:09:16');

-- ============================================
-- 2. 数据表表 (data_tables)
-- ============================================
DROP TABLE IF EXISTS `data_tables`;
CREATE TABLE `data_tables` (
  `id` varchar(36) NOT NULL COMMENT '数据表ID（UUID）',
  `data_source_id` varchar(36) NOT NULL COMMENT '所属数据源ID',
  `table_name` varchar(100) NOT NULL COMMENT '表名',
  `display_name` varchar(100) DEFAULT NULL COMMENT '显示名称',
  `description` text COMMENT '表描述',
  `data_mode` enum('DIRECT_QUERY','IMPORT','CACHE') DEFAULT 'DIRECT_QUERY' COMMENT '数据模式',
  `status` tinyint(1) DEFAULT '1' COMMENT '状态：1-启用，0-禁用',
  `field_count` int DEFAULT '0' COMMENT '字段数量',
  `row_count` bigint DEFAULT '0' COMMENT '行数',
  `import_status` enum('PENDING','IMPORTING','COMPLETED','FAILED') DEFAULT NULL COMMENT '导入状态',
  `last_sync_time` datetime DEFAULT NULL COMMENT '最后同步时间',
  `created_by` varchar(50) DEFAULT 'system' COMMENT '创建人',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `folder_id` varchar(36) DEFAULT NULL COMMENT '所属文件夹ID',
  PRIMARY KEY (`id`),
  KEY `idx_data_source` (`data_source_id`),
  KEY `idx_table_name` (`table_name`),
  KEY `idx_folder` (`folder_id`),
  CONSTRAINT `fk_data_tables_source` FOREIGN KEY (`data_source_id`) REFERENCES `data_sources` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='数据表配置表';

-- 插入示例数据表
INSERT INTO `data_tables` (`id`, `data_source_id`, `table_name`, `display_name`, `description`, `data_mode`, `status`, `field_count`, `row_count`, `last_sync_time`, `created_by`, `created_at`, `updated_at`) VALUES
('097ff2e5-9bb7-4b9f-b84a-56bd6a161ef3', '0ef69205-1c8a-4632-8597-48c91e1e6245', 'users', 'users', '用户表', 'DIRECT_QUERY', 1, 5, 3, '2026-02-03 11:18:33', 'system', '2026-02-03 11:10:49', '2026-02-03 11:18:33'),
('f1b8e9aa-5b9a-495a-9e5e-33caa16d7bb8', '0ef69205-1c8a-4632-8597-48c91e1e6245', 'orders', 'orders', '订单表', 'DIRECT_QUERY', 1, 6, 4, '2026-02-03 11:10:59', 'system', '2026-02-03 11:10:59', '2026-02-03 11:10:59'),
('b8d9c30c-85c5-467d-9884-d862d82664b0', '9f1e3b14-f248-4950-8070-860e8276d873', 'orders', 'orders', '订单表', 'DIRECT_QUERY', 1, 6, 4, '2026-02-03 22:34:44', 'system', '2026-02-03 22:34:44', '2026-02-03 22:34:44');

-- ============================================
-- 3. 表字段表 (table_fields)
-- ============================================
DROP TABLE IF EXISTS `table_fields`;
CREATE TABLE `table_fields` (
  `id` varchar(36) NOT NULL COMMENT '字段ID（UUID）',
  `table_id` varchar(36) NOT NULL COMMENT '所属表ID',
  `field_name` varchar(100) NOT NULL COMMENT '字段名',
  `display_name` varchar(100) DEFAULT NULL COMMENT '显示名称',
  `data_type` varchar(50) NOT NULL COMMENT '数据类型',
  `is_primary_key` tinyint(1) DEFAULT '0' COMMENT '是否主键',
  `is_foreign_key` tinyint(1) DEFAULT '0' COMMENT '是否外键',
  `is_nullable` tinyint(1) DEFAULT '1' COMMENT '是否可空',
  `default_value` varchar(255) DEFAULT NULL COMMENT '默认值',
  `description` text COMMENT '字段描述',
  `field_order` int DEFAULT '0' COMMENT '字段顺序',
  `is_visible` tinyint(1) DEFAULT '1' COMMENT '是否可见',
  `aggregation_type` enum('SUM','AVG','COUNT','MAX','MIN','NONE') DEFAULT 'NONE' COMMENT '聚合类型',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  KEY `idx_table_id` (`table_id`),
  KEY `idx_field_name` (`field_name`),
  CONSTRAINT `fk_table_fields_table` FOREIGN KEY (`table_id`) REFERENCES `data_tables` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='表字段配置表';

-- 插入示例字段（users表）
INSERT INTO `table_fields` (`id`, `table_id`, `field_name`, `display_name`, `data_type`, `is_primary_key`, `is_nullable`, `description`, `field_order`) VALUES
('bbc6daa3-4b32-436c-9196-fbbe1ad0e6d7', '097ff2e5-9bb7-4b9f-b84a-56bd6a161ef3', 'id', 'id', 'int', 1, 0, '用户ID', 1),
('c1d2e3f4-5678-9abc-def0-123456789abc', '097ff2e5-9bb7-4b9f-b84a-56bd6a161ef3', 'name', 'name', 'varchar', 0, 0, '用户名', 2),
('d2e3f4g5-6789-abcd-ef01-23456789abcd', '097ff2e5-9bb7-4b9f-b84a-56bd6a161ef3', 'email', 'email', 'varchar', 0, 1, '邮箱', 3),
('e3f4g5h6-789a-bcde-f012-3456789abcde', '097ff2e5-9bb7-4b9f-b84a-56bd6a161ef3', 'age', 'age', 'int', 0, 1, '年龄', 4),
('f4g5h6i7-89ab-cdef-0123-456789abcdef', '097ff2e5-9bb7-4b9f-b84a-56bd6a161ef3', 'created_at', 'created_at', 'datetime', 0, 0, '创建时间', 5);

-- 插入示例字段（orders表）
INSERT INTO `table_fields` (`id`, `table_id`, `field_name`, `display_name`, `data_type`, `is_primary_key`, `is_nullable`, `description`, `field_order`) VALUES
('4e99c32e-c70c-48fd-9048-eef2e4366d4e', 'b8d9c30c-85c5-467d-9884-d862d82664b0', 'user_id', 'user_id', 'int', 0, 0, '用户ID', 2),
('5f0a4d3f-d81d-4fe0-9159-ff3ef5477e5f', 'b8d9c30c-85c5-467d-9884-d862d82664b0', 'id', 'id', 'int', 1, 0, '订单ID', 1),
('6g1b5e4g-e92e-5gf1-a26a-gg4fg6588f6g', 'b8d9c30c-85c5-467d-9884-d862d82664b0', 'product_name', 'product_name', 'varchar', 0, 0, '产品名称', 3),
('7h2c6f5h-fa3f-6hg2-b37b-hh5gh7699g7h', 'b8d9c30c-85c5-467d-9884-d862d82664b0', 'amount', 'amount', 'decimal', 0, 0, '金额', 4),
('8i3d7g6i-gb4g-7ih3-c48c-ii6hi8700h8i', 'b8d9c30c-85c5-467d-9884-d862d82664b0', 'order_date', 'order_date', 'date', 0, 0, '订单日期', 5),
('9j4e8h7j-hc5h-8ji4-d59d-jj7ij9811i9j', 'b8d9c30c-85c5-467d-9884-d862d82664b0', 'status', 'status', 'varchar', 0, 0, '订单状态', 6);

-- ============================================
-- 4. 表关联表 (table_relations)
-- ============================================
DROP TABLE IF EXISTS `table_relations`;
CREATE TABLE `table_relations` (
  `id` varchar(36) NOT NULL COMMENT '关联ID（UUID）',
  `relation_name` varchar(100) NOT NULL COMMENT '关联名称',
  `primary_table_id` varchar(36) NOT NULL COMMENT '主表ID',
  `primary_field_id` varchar(36) NOT NULL COMMENT '主表字段ID',
  `foreign_table_id` varchar(36) NOT NULL COMMENT '外表ID',
  `foreign_field_id` varchar(36) NOT NULL COMMENT '外表字段ID',
  `join_type` enum('INNER','LEFT','RIGHT','FULL') DEFAULT 'LEFT' COMMENT '连接类型',
  `description` text COMMENT '关联描述',
  `status` tinyint(1) DEFAULT '1' COMMENT '状态：1-启用，0-禁用',
  `created_by` varchar(50) DEFAULT 'system' COMMENT '创建人',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  KEY `idx_primary_table` (`primary_table_id`),
  KEY `idx_foreign_table` (`foreign_table_id`),
  CONSTRAINT `fk_relations_primary_table` FOREIGN KEY (`primary_table_id`) REFERENCES `data_tables` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_relations_foreign_table` FOREIGN KEY (`foreign_table_id`) REFERENCES `data_tables` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='表关联配置表';

-- 插入示例表关联
INSERT INTO `table_relations` (`id`, `relation_name`, `primary_table_id`, `primary_field_id`, `foreign_table_id`, `foreign_field_id`, `join_type`, `description`, `status`, `created_by`, `created_at`, `updated_at`) VALUES
('7da27458-46d3-4c88-8726-1cba33d69643', '订单-用户关联', 'b8d9c30c-85c5-467d-9884-d862d82664b0', '4e99c32e-c70c-48fd-9048-eef2e4366d4e', '097ff2e5-9bb7-4b9f-b84a-56bd6a161ef3', 'bbc6daa3-4b32-436c-9196-fbbe1ad0e6d7', 'LEFT', '订单 表通过 user_id 关联到用户表的 id', 1, 'system', '2026-02-06 16:16:37', '2026-02-06 16:16:37');

-- ============================================
-- 5. 字典表 (dictionaries)
-- ============================================
DROP TABLE IF EXISTS `dictionaries`;
CREATE TABLE `dictionaries` (
  `id` varchar(36) NOT NULL COMMENT '字典ID（UUID）',
  `name` varchar(100) NOT NULL COMMENT '字典名称',
  `code` varchar(50) NOT NULL COMMENT '字典编码',
  `description` text COMMENT '字典描述',
  `dict_type` enum('SYSTEM','CUSTOM') DEFAULT 'CUSTOM' COMMENT '字典类型',
  `status` tinyint(1) DEFAULT '1' COMMENT '状态：1-启用，0-禁用',
  `created_by` varchar(50) DEFAULT 'system' COMMENT '创建人',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_code` (`code`),
  KEY `idx_name` (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='字典表';

-- ============================================
-- 6. 字典项表 (dictionary_items)
-- ============================================
DROP TABLE IF EXISTS `dictionary_items`;
CREATE TABLE `dictionary_items` (
  `id` varchar(36) NOT NULL COMMENT '字典项ID（UUID）',
  `dictionary_id` varchar(36) NOT NULL COMMENT '所属字典ID',
  `item_key` varchar(100) NOT NULL COMMENT '字典项键',
  `item_value` varchar(255) NOT NULL COMMENT '字典项值',
  `item_order` int DEFAULT '0' COMMENT '排序',
  `description` text COMMENT '描述',
  `status` tinyint(1) DEFAULT '1' COMMENT '状态：1-启用，0-禁用',
  `created_by` varchar(50) DEFAULT 'system' COMMENT '创建人',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  KEY `idx_dictionary` (`dictionary_id`),
  KEY `idx_key` (`item_key`),
  CONSTRAINT `fk_dict_items_dict` FOREIGN KEY (`dictionary_id`) REFERENCES `dictionaries` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='字典项表';

-- ============================================
-- 7. 查询会话表 (query_sessions)
-- ============================================
DROP TABLE IF EXISTS `query_sessions`;
CREATE TABLE `query_sessions` (
  `session_id` varchar(100) NOT NULL COMMENT '会话ID',
  `user_id` varchar(50) DEFAULT NULL COMMENT '用户ID',
  `data_source_ids` text COMMENT '数据源ID列表（JSON）',
  `session_name` varchar(200) DEFAULT NULL COMMENT '会话名称',
  `status` enum('ACTIVE','COMPLETED','FAILED') DEFAULT 'ACTIVE' COMMENT '会话状态',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`session_id`),
  KEY `idx_user` (`user_id`),
  KEY `idx_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='查询会话表';

-- ============================================
-- 8. 对话会话表 (dialogue_sessions)
-- ============================================
DROP TABLE IF EXISTS `dialogue_sessions`;
CREATE TABLE `dialogue_sessions` (
  `id` varchar(36) NOT NULL COMMENT '会话ID（UUID）',
  `user_id` varchar(50) DEFAULT NULL COMMENT '用户ID',
  `session_name` varchar(200) DEFAULT NULL COMMENT '会话名称',
  `data_source_ids` text COMMENT '关联的数据源ID列表（JSON）',
  `status` enum('ACTIVE','COMPLETED','ARCHIVED') DEFAULT 'ACTIVE' COMMENT '会话状态',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  KEY `idx_user` (`user_id`),
  KEY `idx_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='对话会话表';

-- ============================================
-- 9. 知识库表 (knowledge_bases)
-- ============================================
DROP TABLE IF EXISTS `knowledge_bases`;
CREATE TABLE `knowledge_bases` (
  `id` varchar(36) NOT NULL COMMENT '知识库ID（UUID）',
  `name` varchar(100) NOT NULL COMMENT '知识库名称',
  `description` text COMMENT '知识库描述',
  `kb_type` enum('GENERAL','DOMAIN_SPECIFIC') DEFAULT 'GENERAL' COMMENT '知识库类型',
  `status` tinyint(1) DEFAULT '1' COMMENT '状态：1-启用，0-禁用',
  `created_by` varchar(50) DEFAULT 'system' COMMENT '创建人',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  KEY `idx_name` (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='知识库表';

-- ============================================
-- 10. 知识项表 (knowledge_items)
-- ============================================
DROP TABLE IF EXISTS `knowledge_items`;
CREATE TABLE `knowledge_items` (
  `id` varchar(36) NOT NULL COMMENT '知识项ID（UUID）',
  `knowledge_base_id` varchar(36) NOT NULL COMMENT '所属知识库ID',
  `title` varchar(200) NOT NULL COMMENT '知识项标题',
  `content` text NOT NULL COMMENT '知识项内容',
  `item_type` enum('FAQ','RULE','EXAMPLE') DEFAULT 'FAQ' COMMENT '知识项类型',
  `tags` text COMMENT '标签（JSON数组）',
  `priority` int DEFAULT '0' COMMENT '优先级',
  `status` tinyint(1) DEFAULT '1' COMMENT '状态：1-启用，0-禁用',
  `created_by` varchar(50) DEFAULT 'system' COMMENT '创建人',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  KEY `idx_kb` (`knowledge_base_id`),
  KEY `idx_type` (`item_type`),
  CONSTRAINT `fk_knowledge_items_kb` FOREIGN KEY (`knowledge_base_id`) REFERENCES `knowledge_bases` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='知识项表';

-- ============================================
-- 11. Alembic版本表
-- ============================================
DROP TABLE IF EXISTS `alembic_version`;
CREATE TABLE `alembic_version` (
  `version_num` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL,
  PRIMARY KEY (`version_num`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT INTO `alembic_version` VALUES ('56aa2d976da9');

-- ============================================
-- 完成
-- ============================================
-- 数据库初始化完成
-- 包含的表：
-- 1. data_sources - 数据源配置（2条示例数据）
-- 2. data_tables - 数据表配置（3条示例数据）
-- 3. table_fields - 表字段配置（11条示例数据）
-- 4. table_relations - 表关联配置（1条示例数据）
-- 5. dictionaries - 字典表
-- 6. dictionary_items - 字典项表
-- 7. query_sessions - 查询会话表
-- 8. dialogue_sessions - 对话会话表
-- 9. knowledge_bases - 知识库表
-- 10. knowledge_items - 知识项表
-- 11. alembic_version - 数据库版本管理

-- 使用说明：
-- 1. 执行此脚本将创建 chatbi 数据库及所有表
-- 2. 包含示例数据源、数据表、字段和关联关系
-- 3. 密码已加密，需要使用应用程序的解密功能
-- 4. 可以根据需要修改示例数据

SELECT 'ChatBI 数据库初始化完成！' AS message;
