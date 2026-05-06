# ChatBI 数据库初始化说明

## 文件说明

### 1. init_chatbi_with_data.sql
完整的数据库初始化脚本，包含：
- 数据库创建
- 所有表结构定义
- 示例数据

### 2. chatbi_full_backup.sql
完整的数据库备份文件（由 mysqldump 生成）

## 使用方法

### 初始化新数据库

```bash
# 方法1：使用初始化脚本（推荐）
mysql -h 127.0.0.1 -u root -p12345678 < database/init_chatbi_with_data.sql

# 方法2：使用完整备份
mysql -h 127.0.0.1 -u root -p12345678 < database/chatbi_full_backup.sql
```

### 备份当前数据库

```bash
# 完整备份（包含数据）
mysqldump -h 127.0.0.1 -u root -p12345678 chatbi > database/chatbi_backup_$(date +%Y%m%d).sql

# 仅备份结构
mysqldump -h 127.0.0.1 -u root -p12345678 --no-data chatbi > database/chatbi_schema_only.sql
```

## 数据库结构

### 核心表

1. **data_sources** - 数据源配置表
2. **data_tables** - 数据表配置表
3. **table_fields** - 表字段配置表
4. **table_relations** - 表关联配置表
5. **dictionaries** - 字典表
6. **dictionary_items** - 字典项表
7. **query_sessions** - 查询会话表
8. **dialogue_sessions** - 对话会话表
9. **knowledge_bases** - 知识库表
10. **knowledge_items** - 知识项表

### 示例数据

初始化脚本包含以下示例数据：
- 2个数据源（mock data, mysql_test_source）
- 3个数据表（users, orders）
- 11个字段定义
- 1个表关联（订单-用户关联）

## 注意事项

1. 密码已加密存储，需要使用应用程序的解密功能
2. 执行初始化脚本会删除现有的 chatbi 数据库
3. 建议在执行前先备份现有数据
