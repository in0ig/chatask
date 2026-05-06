-- ChatBI 数据库初始化脚本
-- 创建数据库和基础表结构
-- 适用于 MySQL 8.0+

-- 创建数据库（如果不存在）
CREATE DATABASE IF NOT EXISTS chatbi CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- 使用数据库
USE chatbi;

-- 创建用户表（用于认证和授权）
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(100) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    is_admin BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_username (username),
    INDEX idx_email (email),
    INDEX idx_is_active (is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 创建数据源配置表
CREATE TABLE IF NOT EXISTS data_sources (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    type ENUM('mysql', 'excel', 'api') NOT NULL,
    connection_string TEXT,
    file_path VARCHAR(255),
    is_active BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    description TEXT,
    metadata JSON,
    INDEX idx_name (name),
    INDEX idx_type (type),
    INDEX idx_is_active (is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 创建查询历史表
CREATE TABLE IF NOT EXISTS query_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,
    query_text TEXT NOT NULL,
    generated_sql TEXT,
    chart_type VARCHAR(50),
    result_data JSON,
    execution_time DECIMAL(10,4),
    status ENUM('success', 'failed', 'pending') DEFAULT 'pending',
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
    INDEX idx_user_id (user_id),
    INDEX idx_created_at (created_at),
    INDEX idx_status (status),
    INDEX idx_query_text (query_text(255))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 创建查询会话表（用于多轮对话上下文）
CREATE TABLE IF NOT EXISTS query_sessions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,
    session_id VARCHAR(100) NOT NULL UNIQUE,
    conversation JSON DEFAULT '{}',
    last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_user_id (user_id),
    INDEX idx_session_id (session_id),
    INDEX idx_last_active (last_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 创建数据字典表（用于数据标准化）
CREATE TABLE IF NOT EXISTS data_dictionary (
    id INT AUTO_INCREMENT PRIMARY KEY,
    source_id INT,
    column_name VARCHAR(100) NOT NULL,
    alias_name VARCHAR(100),
    data_type VARCHAR(50),
    unit VARCHAR(50),
    category VARCHAR(100),
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (source_id) REFERENCES data_sources(id) ON DELETE CASCADE,
    INDEX idx_source_id (source_id),
    INDEX idx_column_name (column_name),
    INDEX idx_alias_name (alias_name),
    INDEX idx_is_active (is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 创建字典表（用于数据标准化）
CREATE TABLE IF NOT EXISTS dictionary_table (
    id INT AUTO_INCREMENT PRIMARY KEY,
    table_name VARCHAR(100) NOT NULL,
    field_name VARCHAR(100) NOT NULL,
    value VARCHAR(100) NOT NULL,
    label VARCHAR(100) NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    sort_order INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY unique_entry (table_name, field_name, value),
    INDEX idx_table_field (table_name, field_name),
    INDEX idx_is_active (is_active),
    INDEX idx_sort_order (sort_order)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 创建知识库表
CREATE TABLE IF NOT EXISTS knowledge_base (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    content TEXT,
    category VARCHAR(100),
    tags JSON,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    created_by INT,
    FOREIGN KEY (created_by) REFERENCES users(id),
    INDEX idx_title (title),
    INDEX idx_category (category),
    INDEX idx_is_active (is_active),
    FULLTEXT idx_content (content)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 创建知识项表
CREATE TABLE IF NOT EXISTS knowledge_items (
    id INT AUTO_INCREMENT PRIMARY KEY,
    knowledge_base_id INT,
    title VARCHAR(255) NOT NULL,
    content TEXT,
    category VARCHAR(100),
    tags JSON,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    created_by INT,
    FOREIGN KEY (knowledge_base_id) REFERENCES knowledge_base(id) ON DELETE CASCADE,
    FOREIGN KEY (created_by) REFERENCES users(id),
    INDEX idx_knowledge_base_id (knowledge_base_id),
    INDEX idx_title (title),
    INDEX idx_category (category),
    INDEX idx_is_active (is_active),
    FULLTEXT idx_content (content)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 创建数据表元数据表
CREATE TABLE IF NOT EXISTS data_tables (
    id INT AUTO_INCREMENT PRIMARY KEY,
    source_id INT,
    table_name VARCHAR(100) NOT NULL,
    table_type ENUM('base', 'derived', 'view') DEFAULT 'base',
    row_count INT DEFAULT 0,
    column_count INT DEFAULT 0,
    schema_info JSON,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (source_id) REFERENCES data_sources(id) ON DELETE CASCADE,
    UNIQUE KEY unique_source_table (source_id, table_name),
    INDEX idx_source_id (source_id),
    INDEX idx_table_name (table_name),
    INDEX idx_is_active (is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 创建表字段元数据表
CREATE TABLE IF NOT EXISTS table_fields (
    id INT AUTO_INCREMENT PRIMARY KEY,
    table_id INT,
    field_name VARCHAR(100) NOT NULL,
    data_type VARCHAR(50),
    is_primary_key BOOLEAN DEFAULT FALSE,
    is_foreign_key BOOLEAN DEFAULT FALSE,
    is_nullable BOOLEAN DEFAULT TRUE,
    default_value VARCHAR(255),
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (table_id) REFERENCES data_tables(id) ON DELETE CASCADE,
    UNIQUE KEY unique_table_field (table_id, field_name),
    INDEX idx_table_id (table_id),
    INDEX idx_field_name (field_name),
    INDEX idx_is_active (is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 创建表关系表
CREATE TABLE IF NOT EXISTS table_relations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    from_table_id INT,
    to_table_id INT,
    relation_type ENUM('one_to_one', 'one_to_many', 'many_to_one', 'many_to_many') NOT NULL,
    from_field_name VARCHAR(100),
    to_field_name VARCHAR(100),
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (from_table_id) REFERENCES data_tables(id) ON DELETE CASCADE,
    FOREIGN KEY (to_table_id) REFERENCES data_tables(id) ON DELETE CASCADE,
    UNIQUE KEY unique_relation (from_table_id, to_table_id, from_field_name, to_field_name),
    INDEX idx_from_table (from_table_id),
    INDEX idx_to_table (to_table_id),
    INDEX idx_relation_type (relation_type),
    INDEX idx_is_active (is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 创建Excel上传记录表
CREATE TABLE IF NOT EXISTS excel_uploads (
    id INT AUTO_INCREMENT PRIMARY KEY,
    file_name VARCHAR(255) NOT NULL,
    original_name VARCHAR(255),
    file_path VARCHAR(255) NOT NULL,
    file_size INT,
    sheet_count INT,
    row_count INT,
    status ENUM('pending', 'processing', 'completed', 'failed') DEFAULT 'pending',
    error_message TEXT,
    created_by INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (created_by) REFERENCES users(id),
    INDEX idx_file_name (file_name),
    INDEX idx_status (status),
    INDEX idx_created_by (created_by),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 创建Excel解析记录表
CREATE TABLE IF NOT EXISTS excel_parsers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    upload_id INT,
    sheet_name VARCHAR(100),
    header_row INT,
    data_start_row INT,
    column_mapping JSON,
    parsing_status ENUM('pending', 'processing', 'completed', 'failed') DEFAULT 'pending',
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (upload_id) REFERENCES excel_uploads(id) ON DELETE CASCADE,
    INDEX idx_upload_id (upload_id),
    INDEX idx_sheet_name (sheet_name),
    INDEX idx_parsing_status (parsing_status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 创建数据准备配置表
CREATE TABLE IF NOT EXISTS data_preparation_config (
    id INT AUTO_INCREMENT PRIMARY KEY,
    config_name VARCHAR(100) NOT NULL UNIQUE,
    config_type ENUM('excel_import', 'data_mapping', 'data_cleaning') NOT NULL,
    config_data JSON NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_by INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (created_by) REFERENCES users(id),
    INDEX idx_config_name (config_name),
    INDEX idx_config_type (config_type),
    INDEX idx_is_active (is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 创建系统设置表
CREATE TABLE IF NOT EXISTS system_settings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    setting_key VARCHAR(100) NOT NULL UNIQUE,
    setting_value TEXT,
    setting_type ENUM('string', 'integer', 'boolean', 'json') DEFAULT 'string',
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_setting_key (setting_key),
    INDEX idx_is_active (is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 创建会话上下文表
CREATE TABLE IF NOT EXISTS session_context (
    id INT AUTO_INCREMENT PRIMARY KEY,
    session_id VARCHAR(100) NOT NULL,
    context_key VARCHAR(100) NOT NULL,
    context_value TEXT,
    context_type ENUM('string', 'json', 'number') DEFAULT 'string',
    expires_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY unique_session_key (session_id, context_key),
    INDEX idx_session_id (session_id),
    INDEX idx_expires_at (expires_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 创建API访问日志表
CREATE TABLE IF NOT EXISTS api_access_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,
    endpoint VARCHAR(255),
    method VARCHAR(10),
    status_code INT,
    response_time DECIMAL(10,4),
    request_size INT,
    response_size INT,
    ip_address VARCHAR(45),
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    INDEX idx_user_id (user_id),
    INDEX idx_endpoint (endpoint),
    INDEX idx_method (method),
    INDEX idx_status_code (status_code),
    INDEX idx_created_at (created_at),
    INDEX idx_ip_address (ip_address)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 插入默认系统设置
INSERT INTO system_settings (setting_key, setting_value, setting_type, description, is_active) VALUES
('app.name', 'ChatBI', 'string', '应用程序名称', TRUE),
('app.version', '1.0.0', 'string', '应用程序版本', TRUE),
('app.timezone', 'Asia/Shanghai', 'string', '应用时区', TRUE),
('feature.nlu.enabled', 'true', 'boolean', '自然语言理解功能是否启用', TRUE),
('feature.data_prep.enabled', 'true', 'boolean', '数据准备功能是否启用', TRUE),
('feature.knowledge_base.enabled', 'true', 'boolean', '知识库功能是否启用', TRUE),
('feature.multi_turn.enabled', 'true', 'boolean', '多轮对话功能是否启用', TRUE),
('feature.auth.enabled', 'true', 'boolean', '认证功能是否启用', TRUE),
('feature.api_docs.enabled', 'true', 'boolean', 'API文档功能是否启用', TRUE),
('cache.dictionary.ttl', '3600', 'integer', '字典缓存过期时间（秒）', TRUE),
('cache.session.ttl', '7200', 'integer', '会话缓存过期时间（秒）', TRUE),
('upload.max_size', '52428800', 'integer', '文件上传最大大小（字节）', TRUE),
('upload.allowed_types', '[".xlsx", ".xls"]', 'json', '允许的文件类型', TRUE),
('log.level', 'INFO', 'string', '日志级别', TRUE),
('debug.enabled', 'false', 'boolean', '调试模式是否启用', FALSE);

-- 插入示例数据源
INSERT INTO data_sources (name, type, is_active, description) VALUES
('示例MySQL数据库', 'mysql', TRUE, '用于演示的MySQL数据库连接'),
('示例Excel文件', 'excel', TRUE, '用于演示的Excel文件上传');

-- 插入示例用户（管理员）
-- 注意：在生产环境中，密码应使用哈希存储
-- 这里使用明文密码只是为了演示目的
-- 实际部署时应使用安全的密码哈希算法
INSERT INTO users (username, email, password_hash, is_active, is_admin) VALUES
('admin', 'admin@chatbi.com', 'pbkdf2:sha256:260000$Z5z9x1Y8t2v3w4x5$7a8b9c0d1e2f3g4h5i6j7k8l9m0n1o2p', TRUE, TRUE);

-- 插入示例知识库
INSERT INTO knowledge_base (title, content, category, is_active, created_by) VALUES
('ChatBI 使用指南', '这是一个关于ChatBI系统使用方法的完整指南，包含功能介绍、操作步骤和最佳实践。', 'documentation', TRUE, 1);

-- 插入示例字典数据
INSERT INTO dictionary_table (table_name, field_name, value, label, description, is_active, sort_order) VALUES
('data_sources', 'type', 'mysql', 'MySQL数据库', 'MySQL数据库连接', TRUE, 1),
('data_sources', 'type', 'excel', 'Excel文件', 'Excel文件上传', TRUE, 2),
('data_sources', 'type', 'api', 'API接口', '外部API数据源', TRUE, 3),
('query_history', 'status', 'success', '成功', '查询执行成功', TRUE, 1),
('query_history', 'status', 'failed', '失败', '查询执行失败', TRUE, 2),
('query_history', 'status', 'pending', '待处理', '查询正在处理中', TRUE, 3),
('excel_uploads', 'status', 'pending', '待处理', '文件上传待处理', TRUE, 1),
('excel_uploads', 'status', 'processing', '处理中', '文件正在解析中', TRUE, 2),
('excel_uploads', 'status', 'completed', '完成', '文件解析完成', TRUE, 3),
('excel_uploads', 'status', 'failed', '失败', '文件解析失败', TRUE, 4);

-- 创建触发器：自动更新更新时间
DELIMITER $$

CREATE TRIGGER update_data_sources_updated_at 
BEFORE UPDATE ON data_sources 
FOR EACH ROW 
BEGIN
    IF NEW.name != OLD.name OR NEW.type != OLD.type OR NEW.connection_string != OLD.connection_string OR NEW.file_path != OLD.file_path OR NEW.is_active != OLD.is_active THEN
        SET NEW.updated_at = NOW();
    END IF;
END$$

CREATE TRIGGER update_data_dictionary_updated_at 
BEFORE UPDATE ON data_dictionary 
FOR EACH ROW 
BEGIN
    IF NEW.source_id != OLD.source_id OR NEW.column_name != OLD.column_name OR NEW.alias_name != OLD.alias_name OR NEW.data_type != OLD.data_type OR NEW.unit != OLD.unit OR NEW.category != OLD.category OR NEW.description != OLD.description OR NEW.is_active != OLD.is_active THEN
        SET NEW.updated_at = NOW();
    END IF;
END$$

CREATE TRIGGER update_dictionary_table_updated_at 
BEFORE UPDATE ON dictionary_table 
FOR EACH ROW 
BEGIN
    IF NEW.table_name != OLD.table_name OR NEW.field_name != OLD.field_name OR NEW.value != OLD.value OR NEW.label != OLD.label OR NEW.description != OLD.description OR NEW.is_active != OLD.is_active OR NEW.sort_order != OLD.sort_order THEN
        SET NEW.updated_at = NOW();
    END IF;
END$$

CREATE TRIGGER update_knowledge_base_updated_at 
BEFORE UPDATE ON knowledge_base 
FOR EACH ROW 
BEGIN
    IF NEW.title != OLD.title OR NEW.content != OLD.content OR NEW.category != OLD.category OR NEW.tags != OLD.tags OR NEW.is_active != OLD.is_active THEN
        SET NEW.updated_at = NOW();
    END IF;
END$$

CREATE TRIGGER update_knowledge_items_updated_at 
BEFORE UPDATE ON knowledge_items 
FOR EACH ROW 
BEGIN
    IF NEW.knowledge_base_id != OLD.knowledge_base_id OR NEW.title != OLD.title OR NEW.content != OLD.content OR NEW.category != OLD.category OR NEW.tags != OLD.tags OR NEW.is_active != OLD.is_active THEN
        SET NEW.updated_at = NOW();
    END IF;
END$$

CREATE TRIGGER update_data_tables_updated_at 
BEFORE UPDATE ON data_tables 
FOR EACH ROW 
BEGIN
    IF NEW.source_id != OLD.source_id OR NEW.table_name != OLD.table_name OR NEW.table_type != OLD.table_type OR NEW.row_count != OLD.row_count OR NEW.column_count != OLD.column_count OR NEW.schema_info != OLD.schema_info OR NEW.is_active != OLD.is_active THEN
        SET NEW.updated_at = NOW();
    END IF;
END$$

CREATE TRIGGER update_table_fields_updated_at 
BEFORE UPDATE ON table_fields 
FOR EACH ROW 
BEGIN
    IF NEW.table_id != OLD.table_id OR NEW.field_name != OLD.field_name OR NEW.data_type != OLD.data_type OR NEW.is_primary_key != OLD.is_primary_key OR NEW.is_foreign_key != OLD.is_foreign_key OR NEW.is_nullable != OLD.is_nullable OR NEW.default_value != OLD.default_value OR NEW.description != OLD.description OR NEW.is_active != OLD.is_active THEN
        SET NEW.updated_at = NOW();
    END IF;
END$$

CREATE TRIGGER update_table_relations_updated_at 
BEFORE UPDATE ON table_relations 
FOR EACH ROW 
BEGIN
    IF NEW.from_table_id != OLD.from_table_id OR NEW.to_table_id != OLD.to_table_id OR NEW.relation_type != OLD.relation_type OR NEW.from_field_name != OLD.from_field_name OR NEW.to_field_name != OLD.to_field_name OR NEW.description != OLD.description OR NEW.is_active != OLD.is_active THEN
        SET NEW.updated_at = NOW();
    END IF;
END$$

CREATE TRIGGER update_excel_uploads_updated_at 
BEFORE UPDATE ON excel_uploads 
FOR EACH ROW 
BEGIN
    IF NEW.file_name != OLD.file_name OR NEW.original_name != OLD.original_name OR NEW.file_path != OLD.file_path OR NEW.file_size != OLD.file_size OR NEW.sheet_count != OLD.sheet_count OR NEW.row_count != OLD.row_count OR NEW.status != OLD.status OR NEW.error_message != OLD.error_message THEN
        SET NEW.updated_at = NOW();
    END IF;
END$$

CREATE TRIGGER update_data_preparation_config_updated_at 
BEFORE UPDATE ON data_preparation_config 
FOR EACH ROW 
BEGIN
    IF NEW.config_name != OLD.config_name OR NEW.config_type != OLD.config_type OR NEW.config_data != OLD.config_data OR NEW.description != OLD.description OR NEW.is_active != OLD.is_active THEN
        SET NEW.updated_at = NOW();
    END IF;
END$$

DELIMITER ;

-- 创建存储过程：获取数据源的完整信息
DELIMITER $$

CREATE PROCEDURE GetDataSourceFullInfo(IN source_id INT)
BEGIN
    SELECT 
        ds.*,
        COUNT(dt.id) as table_count,
        COUNT(dd.id) as dictionary_count,
        COUNT(tr.id) as relation_count
    FROM data_sources ds
    LEFT JOIN data_tables dt ON ds.id = dt.source_id
    LEFT JOIN data_dictionary dd ON ds.id = dd.source_id
    LEFT JOIN table_relations tr ON ds.id = tr.from_table_id OR ds.id = tr.to_table_id
    WHERE ds.id = source_id
    GROUP BY ds.id;
END$$

-- 创建存储过程：获取查询历史的统计信息
CREATE PROCEDURE GetQueryHistoryStats(IN start_date DATE, IN end_date DATE)
BEGIN
    SELECT 
        COUNT(*) as total_queries,
        SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as successful_queries,
        SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed_queries,
        AVG(execution_time) as avg_execution_time,
        MAX(execution_time) as max_execution_time,
        MIN(execution_time) as min_execution_time
    FROM query_history 
    WHERE created_at >= start_date AND created_at <= end_date;
END$$

DELIMITER ;

-- 创建索引优化查询性能
-- 查询历史表索引（已包含在创建表语句中）
-- CREATE INDEX idx_query_history_user_created ON query_history(user_id, created_at);
-- CREATE INDEX idx_query_history_status_created ON query_history(status, created_at);

-- 数据源表索引（已包含在创建表语句中）
-- CREATE INDEX idx_data_sources_active_name ON data_sources(is_active, name);

-- 数据字典表索引（已包含在创建表语句中）
-- CREATE INDEX idx_data_dictionary_source_column ON data_dictionary(source_id, column_name);

-- 字典表索引（已包含在创建表语句中）
-- CREATE INDEX idx_dictionary_table_table_field ON dictionary_table(table_name, field_name);

-- 知识库表索引（已包含在创建表语句中）
-- CREATE INDEX idx_knowledge_base_active_category ON knowledge_base(is_active, category);

-- 会话表索引（已包含在创建表语句中）
-- CREATE INDEX idx_query_sessions_active ON query_sessions(user_id, last_active);

-- Excel上传表索引（已包含在创建表语句中）
-- CREATE INDEX idx_excel_uploads_status_created ON excel_uploads(status, created_at);

-- 系统设置表索引（已包含在创建表语句中）
-- CREATE INDEX idx_system_settings_active ON system_settings(is_active);

-- API访问日志索引（已包含在创建表语句中）
-- CREATE INDEX idx_api_access_logs_user_created ON api_access_logs(user_id, created_at);

-- 创建视图：查询历史与用户信息关联视图
CREATE VIEW query_history_with_user AS
SELECT 
    qh.*,
    u.username,
    u.email
FROM query_history qh
LEFT JOIN users u ON qh.user_id = u.id;

-- 创建视图：数据源与数据表关联视图
CREATE VIEW data_sources_with_tables AS
SELECT 
    ds.*,
    COUNT(dt.id) as table_count,
    GROUP_CONCAT(dt.table_name SEPARATOR ', ') as table_names
FROM data_sources ds
LEFT JOIN data_tables dt ON ds.id = dt.source_id
GROUP BY ds.id;

-- 创建视图：字典表与数据源关联视图
CREATE VIEW dictionary_with_source AS
SELECT 
    dd.*,
    ds.name as source_name,
    ds.type as source_type
FROM data_dictionary dd
JOIN data_sources ds ON dd.source_id = ds.id;

-- 创建视图：Excel上传与解析关联视图
CREATE VIEW excel_uploads_with_parsers AS
SELECT 
    eu.*,
    COUNT(ep.id) as parser_count,
    GROUP_CONCAT(ep.sheet_name SEPARATOR ', ') as sheet_names
FROM excel_uploads eu
LEFT JOIN excel_parsers ep ON eu.id = ep.upload_id
GROUP BY eu.id;

-- 创建视图：数据准备配置与用户关联视图
CREATE VIEW data_preparation_config_with_user AS
SELECT 
    dpc.*,
    u.username as created_by_username
FROM data_preparation_config dpc
LEFT JOIN users u ON dpc.created_by = u.id;

-- 创建视图：系统设置与用户关联视图
CREATE VIEW system_settings_with_user AS
SELECT 
    ss.*,
    u.username as updated_by_username
FROM system_settings ss
LEFT JOIN users u ON ss.id = u.id;

-- 创建视图：表关系与表信息关联视图
CREATE VIEW table_relations_with_info AS
SELECT 
    tr.*,
    ft.table_name as from_table_name,
    tt.table_name as to_table_name,
    ftf.field_name as from_field_name_full,
    ttf.field_name as to_field_name_full
FROM table_relations tr
JOIN data_tables ft ON tr.from_table_id = ft.id
JOIN data_tables tt ON tr.to_table_id = tt.id
JOIN table_fields ftf ON tr.from_table_id = ftf.table_id AND tr.from_field_name = ftf.field_name
JOIN table_fields ttf ON tr.to_table_id = ttf.table_id AND tr.to_field_name = ttf.field_name;

-- 创建用户定义函数：获取数据源类型名称
DELIMITER $$

CREATE FUNCTION GetDataSourceTypeName(type ENUM('mysql', 'excel', 'api'))
RETURNS VARCHAR(20)
READS SQL DATA
DETERMINISTIC
BEGIN
    DECLARE result VARCHAR(20);
    CASE type
        WHEN 'mysql' THEN SET result = 'MySQL数据库';
        WHEN 'excel' THEN SET result = 'Excel文件';
        WHEN 'api' THEN SET result = 'API接口';
        ELSE SET result = '未知';
    END CASE;
    RETURN result;
END$$

-- 创建用户定义函数：获取查询状态名称
CREATE FUNCTION GetQueryStatusName(status ENUM('success', 'failed', 'pending'))
RETURNS VARCHAR(20)
READS SQL DATA
DETERMINISTIC
BEGIN
    DECLARE result VARCHAR(20);
    CASE status
        WHEN 'success' THEN SET result = '成功';
        WHEN 'failed' THEN SET result = '失败';
        WHEN 'pending' THEN SET result = '待处理';
        ELSE SET result = '未知';
    END CASE;
    RETURN result;
END$$

DELIMITER ;

-- 验证数据库结构
SELECT '数据库初始化完成' as status;
