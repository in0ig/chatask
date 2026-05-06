-- ChatBI 数据库初始化脚本
-- 幂等性设计：使用 IF NOT EXISTS 避免重复创建

-- 1. 创建 chatbi 数据库（如果不存在）
CREATE DATABASE IF NOT EXISTS chatbi;
USE chatbi;

-- 2. 创建 users 表
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(100) NOT NULL UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. 创建 data_sources 表
CREATE TABLE IF NOT EXISTS data_sources (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    type ENUM('mysql', 'excel', 'api') NOT NULL,
    connection_string TEXT,
    file_path VARCHAR(255),
    is_active BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- 4. 创建 query_history 表
CREATE TABLE IF NOT EXISTS query_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    query_text TEXT NOT NULL,
    generated_sql TEXT,
    chart_type VARCHAR(50),
    result_data JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- 5. 创建 query_sessions 表
CREATE TABLE IF NOT EXISTS query_sessions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    session_id VARCHAR(100) NOT NULL,
    conversation JSON,
    last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- 6. 创建 data_dictionary 表
CREATE TABLE IF NOT EXISTS data_dictionary (
    id INT AUTO_INCREMENT PRIMARY KEY,
    source_id INT NOT NULL,
    column_name VARCHAR(100) NOT NULL,
    alias_name VARCHAR(100),
    data_type VARCHAR(50),
    unit VARCHAR(50),
    category VARCHAR(100),
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (source_id) REFERENCES data_sources(id) ON DELETE CASCADE
);

-- 7. 创建 dictionary_table 表
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
    UNIQUE KEY unique_entry (table_name, field_name, value)
);

-- 8. 插入默认用户数据
INSERT IGNORE INTO users (username, email) VALUES 
('admin', 'admin@chatbi.local'),
('user1', 'user1@chatbi.local'),
('user2', 'user2@chatbi.local');

-- 9. 创建索引以提高查询性能
-- 检查并创建 idx_query_history_user_id
SET @exist := (SELECT COUNT(*) FROM information_schema.statistics WHERE table_schema = 'chatbi' AND table_name = 'query_history' AND index_name = 'idx_query_history_user_id');
SET @sql := IF(@exist = 0, 'CREATE INDEX idx_query_history_user_id ON query_history(user_id)', 'SELECT "Index idx_query_history_user_id already exists" AS message');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- 检查并创建 idx_query_history_created_at
SET @exist := (SELECT COUNT(*) FROM information_schema.statistics WHERE table_schema = 'chatbi' AND table_name = 'query_history' AND index_name = 'idx_query_history_created_at');
SET @sql := IF(@exist = 0, 'CREATE INDEX idx_query_history_created_at ON query_history(created_at)', 'SELECT "Index idx_query_history_created_at already exists" AS message');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- 检查并创建 idx_query_sessions_user_id
SET @exist := (SELECT COUNT(*) FROM information_schema.statistics WHERE table_schema = 'chatbi' AND table_name = 'query_sessions' AND index_name = 'idx_query_sessions_user_id');
SET @sql := IF(@exist = 0, 'CREATE INDEX idx_query_sessions_user_id ON query_sessions(user_id)', 'SELECT "Index idx_query_sessions_user_id already exists" AS message');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- 检查并创建 idx_query_sessions_session_id
SET @exist := (SELECT COUNT(*) FROM information_schema.statistics WHERE table_schema = 'chatbi' AND table_name = 'query_sessions' AND index_name = 'idx_query_sessions_session_id');
SET @sql := IF(@exist = 0, 'CREATE INDEX idx_query_sessions_session_id ON query_sessions(session_id)', 'SELECT "Index idx_query_sessions_session_id already exists" AS message');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- 检查并创建 idx_data_dictionary_source_id
SET @exist := (SELECT COUNT(*) FROM information_schema.statistics WHERE table_schema = 'chatbi' AND table_name = 'data_dictionary' AND index_name = 'idx_data_dictionary_source_id');
SET @sql := IF(@exist = 0, 'CREATE INDEX idx_data_dictionary_source_id ON data_dictionary(source_id)', 'SELECT "Index idx_data_dictionary_source_id already exists" AS message');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- 检查并创建 idx_dictionary_table_unique
SET @exist := (SELECT COUNT(*) FROM information_schema.statistics WHERE table_schema = 'chatbi' AND table_name = 'dictionary_table' AND index_name = 'idx_dictionary_table_unique');
SET @sql := IF(@exist = 0, 'CREATE INDEX idx_dictionary_table_unique ON dictionary_table(table_name, field_name, value)', 'SELECT "Index idx_dictionary_table_unique already exists" AS message');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- 10. 设置字符集和排序规则（确保中文支持）
ALTER DATABASE chatbi CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci;

-- 脚本执行完成
SELECT 'Database initialization completed successfully!' AS status;