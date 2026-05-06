"""
五模块语义增强系统 - 基于Gemini架构建议
实现数据源、表结构、表关联、数据字典、知识库的语义注入
"""

import json
import logging
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, asdict
from enum import Enum
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class DatabaseType(Enum):
    """数据库类型枚举"""
    MYSQL = "mysql"
    SQL_SERVER = "sqlserver"
    POSTGRESQL = "postgresql"
    ORACLE = "oracle"


@dataclass
class DataSourceSemanticInfo:
    """数据源语义信息"""
    source_id: str
    source_name: str
    database_type: DatabaseType
    sql_dialect: Dict[str, Any]
    connection_config: Dict[str, Any]
    performance_characteristics: Dict[str, Any]
    business_rules: List[Dict[str, Any]]
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "source_id": self.source_id,
            "source_name": self.source_name,
            "database_type": self.database_type.value,
            "sql_dialect": self.sql_dialect,
            "connection_config": self.connection_config,
            "performance_characteristics": self.performance_characteristics,
            "business_rules": self.business_rules
        }


@dataclass
class TableSemanticInfo:
    """表结构语义信息"""
    table_id: str
    table_name: str
    schema_name: Optional[str]
    table_comment: Optional[str]
    fields: List[Dict[str, Any]]
    primary_keys: List[str]
    foreign_keys: List[Dict[str, Any]]
    indexes: List[Dict[str, Any]]
    business_meaning: Optional[str]
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "table_id": self.table_id,
            "table_name": self.table_name,
            "schema_name": self.schema_name,
            "table_comment": self.table_comment,
            "fields": self.fields,
            "primary_keys": self.primary_keys,
            "foreign_keys": self.foreign_keys,
            "indexes": self.indexes,
            "business_meaning": self.business_meaning
        }


@dataclass
class TableRelationSemanticInfo:
    """表关联语义信息"""
    relation_id: str
    source_table: str
    target_table: str
    join_type: str
    join_conditions: List[Dict[str, Any]]
    relation_description: Optional[str]
    business_logic: Optional[str]
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "relation_id": self.relation_id,
            "source_table": self.source_table,
            "target_table": self.target_table,
            "join_type": self.join_type,
            "join_conditions": self.join_conditions,
            "relation_description": self.relation_description,
            "business_logic": self.business_logic
        }


@dataclass
class DictionarySemanticInfo:
    """数据字典语义信息"""
    field_id: str
    field_name: str
    table_name: str
    business_name: str
    business_meaning: str
    value_range: Optional[str]
    enum_values: Optional[List[Dict[str, Any]]]
    business_rules: Optional[List[str]]
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "field_id": self.field_id,
            "field_name": self.field_name,
            "table_name": self.table_name,
            "business_name": self.business_name,
            "business_meaning": self.business_meaning,
            "value_range": self.value_range,
            "enum_values": self.enum_values,
            "business_rules": self.business_rules
        }


@dataclass
class KnowledgeSemanticInfo:
    """知识库语义信息"""
    knowledge_id: str
    knowledge_type: str  # TERM, LOGIC, EVENT
    title: str
    content: str
    scope: str  # global, table_specific
    related_tables: List[str]
    related_fields: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "knowledge_id": self.knowledge_id,
            "knowledge_type": self.knowledge_type,
            "title": self.title,
            "content": self.content,
            "scope": self.scope,
            "related_tables": self.related_tables,
            "related_fields": self.related_fields
        }


class BaseSemanticModule(ABC):
    """语义模块基类"""
    
    @abstractmethod
    async def inject_semantic_info(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """注入语义信息"""
        pass
    
    @abstractmethod
    def get_module_name(self) -> str:
        """获取模块名称"""
        pass


class DataSourceSemanticModule(BaseSemanticModule):
    """数据源语义注入模块 - Task 4.2.1"""
    
    def __init__(self):
        # SQL方言差异配置
        self.sql_dialects = {
            DatabaseType.MYSQL: {
                "limit_syntax": "LIMIT {limit}",
                "offset_syntax": "LIMIT {offset}, {limit}",
                "string_concat": "CONCAT({args})",
                "date_format": "DATE_FORMAT({date}, '{format}')",
                "case_sensitive": False,
                "quote_identifier": "`{identifier}`",
                "auto_increment": "AUTO_INCREMENT",
                "engine_support": ["InnoDB", "MyISAM"],
                "max_connections": 151,
                "default_charset": "utf8mb4"
            },
            DatabaseType.SQL_SERVER: {
                "limit_syntax": "TOP {limit}",
                "offset_syntax": "OFFSET {offset} ROWS FETCH NEXT {limit} ROWS ONLY",
                "string_concat": "CONCAT({args})",
                "date_format": "FORMAT({date}, '{format}')",
                "case_sensitive": False,
                "quote_identifier": "[{identifier}]",
                "auto_increment": "IDENTITY(1,1)",
                "engine_support": ["SQL Server"],
                "max_connections": 32767,
                "default_charset": "SQL_Latin1_General_CP1_CI_AS"
            },
            DatabaseType.POSTGRESQL: {
                "limit_syntax": "LIMIT {limit}",
                "offset_syntax": "LIMIT {limit} OFFSET {offset}",
                "string_concat": "CONCAT({args})",
                "date_format": "TO_CHAR({date}, '{format}')",
                "case_sensitive": True,
                "quote_identifier": '"{identifier}"',
                "auto_increment": "SERIAL",
                "engine_support": ["PostgreSQL"],
                "max_connections": 100,
                "default_charset": "UTF8"
            }
        }
        
        # 性能特征配置
        self.performance_characteristics = {
            DatabaseType.MYSQL: {
                "optimal_batch_size": 1000,
                "max_query_timeout": 30,
                "index_hint_support": True,
                "partition_support": True,
                "full_text_search": True,
                "json_support": True,
                "recommended_page_size": 50
            },
            DatabaseType.SQL_SERVER: {
                "optimal_batch_size": 1000,
                "max_query_timeout": 30,
                "index_hint_support": True,
                "partition_support": True,
                "full_text_search": True,
                "json_support": True,
                "recommended_page_size": 50
            },
            DatabaseType.POSTGRESQL: {
                "optimal_batch_size": 1000,
                "max_query_timeout": 30,
                "index_hint_support": False,
                "partition_support": True,
                "full_text_search": True,
                "json_support": True,
                "recommended_page_size": 50
            }
        }
    
    async def inject_semantic_info(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """注入数据源语义信息"""
        data_sources = context.get('data_sources', [])
        
        enhanced_context = context.copy()
        enhanced_context['data_source_semantics'] = []
        
        if not data_sources:
            logger.warning("No data sources found in context")
            return enhanced_context
        
        for ds in data_sources:
            try:
                semantic_info = await self._create_data_source_semantic_info(ds)
                enhanced_context['data_source_semantics'].append(semantic_info.to_dict())
                logger.debug(f"Injected semantic info for data source: {ds.get('name', 'unknown')}")
            except Exception as e:
                logger.error(f"Failed to inject semantic info for data source {ds.get('id', 'unknown')}: {str(e)}")
        
        return enhanced_context
    
    async def _create_data_source_semantic_info(self, data_source: Dict[str, Any]) -> DataSourceSemanticInfo:
        """创建数据源语义信息"""
        # 识别数据库类型
        db_type = self._identify_database_type(data_source)
        
        # 获取SQL方言信息
        sql_dialect = self.sql_dialects.get(db_type, {})
        
        # 获取连接配置信息
        connection_config = self._extract_connection_config(data_source)
        
        # 获取性能特征
        performance_chars = self.performance_characteristics.get(db_type, {})
        
        # 获取业务规则
        business_rules = self._extract_business_rules(data_source)
        
        return DataSourceSemanticInfo(
            source_id=data_source.get('id', ''),
            source_name=data_source.get('name', ''),
            database_type=db_type,
            sql_dialect=sql_dialect,
            connection_config=connection_config,
            performance_characteristics=performance_chars,
            business_rules=business_rules
        )
    
    def _identify_database_type(self, data_source: Dict[str, Any]) -> DatabaseType:
        """识别数据库类型"""
        db_type_str = data_source.get('type', '').lower()
        
        if db_type_str in ['mysql', 'mariadb']:
            return DatabaseType.MYSQL
        elif db_type_str in ['sqlserver', 'mssql', 'sql_server']:
            return DatabaseType.SQL_SERVER
        elif db_type_str in ['postgresql', 'postgres']:
            return DatabaseType.POSTGRESQL
        elif db_type_str in ['oracle']:
            return DatabaseType.ORACLE
        else:
            logger.warning(f"Unknown database type: {db_type_str}, defaulting to MySQL")
            return DatabaseType.MYSQL
    
    def _extract_connection_config(self, data_source: Dict[str, Any]) -> Dict[str, Any]:
        """提取连接配置信息（不包含敏感信息）"""
        config = data_source.get('config', {})
        
        return {
            "host": config.get('host', ''),
            "port": config.get('port', 0),
            "database": config.get('database', ''),
            "charset": config.get('charset', ''),
            "connection_pool": {
                "min_connections": config.get('connection_pool', {}).get('min', 1),
                "max_connections": config.get('connection_pool', {}).get('max', 10),
                "timeout": config.get('connection_pool', {}).get('timeout', 30)
            }
        }
    
    def _extract_business_rules(self, data_source: Dict[str, Any]) -> List[Dict[str, Any]]:
        """提取数据源级别的业务规则"""
        # 从数据源配置中提取业务规则
        business_rules = []
        
        # 默认业务规则
        db_type = self._identify_database_type(data_source)
        
        if db_type == DatabaseType.MYSQL:
            business_rules.extend([
                {
                    "rule_type": "query_optimization",
                    "description": "MySQL查询优化：使用LIMIT限制结果集大小",
                    "sql_pattern": "SELECT ... LIMIT {limit}"
                },
                {
                    "rule_type": "date_handling",
                    "description": "MySQL日期处理：使用DATE_FORMAT格式化日期",
                    "sql_pattern": "DATE_FORMAT(date_column, '%Y-%m-%d')"
                }
            ])
        elif db_type == DatabaseType.SQL_SERVER:
            business_rules.extend([
                {
                    "rule_type": "query_optimization",
                    "description": "SQL Server查询优化：使用TOP限制结果集大小",
                    "sql_pattern": "SELECT TOP {limit} ..."
                },
                {
                    "rule_type": "date_handling",
                    "description": "SQL Server日期处理：使用FORMAT格式化日期",
                    "sql_pattern": "FORMAT(date_column, 'yyyy-MM-dd')"
                }
            ])
        
        # 从数据源配置中获取自定义业务规则
        custom_rules = data_source.get('business_rules', [])
        business_rules.extend(custom_rules)
        
        return business_rules
    
    def get_sql_dialect_info(self, database_type: DatabaseType) -> Dict[str, Any]:
        """获取SQL方言信息"""
        return self.sql_dialects.get(database_type, {})
    
    def get_performance_characteristics(self, database_type: DatabaseType) -> Dict[str, Any]:
        """获取性能特征"""
        return self.performance_characteristics.get(database_type, {})
    
    def adapt_sql_for_database(self, sql: str, database_type: DatabaseType) -> str:
        """根据数据库类型适配SQL语法"""
        dialect = self.sql_dialects.get(database_type, {})
        
        # 适配LIMIT语法
        if database_type == DatabaseType.SQL_SERVER:
            # 将MySQL的LIMIT转换为SQL Server的TOP
            import re
            # 匹配 LIMIT n 模式
            limit_pattern = r'\bLIMIT\s+(\d+)\b'
            match = re.search(limit_pattern, sql, re.IGNORECASE)
            if match:
                limit_value = match.group(1)
                # 将LIMIT移到SELECT后面作为TOP
                sql = re.sub(r'\bSELECT\b', f'SELECT TOP {limit_value}', sql, flags=re.IGNORECASE)
                sql = re.sub(limit_pattern, '', sql, flags=re.IGNORECASE)
                sql = re.sub(r'\s+', ' ', sql).strip()  # 清理多余空格
        
        return sql
    
    def get_module_name(self) -> str:
        """获取模块名称"""
        return "DataSourceSemanticModule"


class TableStructureSemanticModule(BaseSemanticModule):
    """表结构语义注入模块 - Task 4.2.2"""
    
    def __init__(self):
        # 数据类型语义映射
        self.data_type_semantics = {
            # 数值类型
            "int": {"category": "数值", "description": "整数类型", "business_meaning": "计数、ID、状态码"},
            "bigint": {"category": "数值", "description": "大整数类型", "business_meaning": "大数值ID、时间戳"},
            "decimal": {"category": "数值", "description": "精确小数类型", "business_meaning": "金额、价格、比率"},
            "float": {"category": "数值", "description": "浮点数类型", "business_meaning": "测量值、百分比"},
            "double": {"category": "数值", "description": "双精度浮点数", "business_meaning": "高精度数值"},
            
            # 字符串类型
            "varchar": {"category": "文本", "description": "可变长度字符串", "business_meaning": "名称、描述、代码"},
            "char": {"category": "文本", "description": "固定长度字符串", "business_meaning": "编码、标识符"},
            "text": {"category": "文本", "description": "长文本类型", "business_meaning": "详细描述、内容、备注"},
            "longtext": {"category": "文本", "description": "超长文本类型", "business_meaning": "文章内容、详细信息"},
            
            # 时间类型
            "datetime": {"category": "时间", "description": "日期时间类型", "business_meaning": "创建时间、更新时间、事件时间"},
            "date": {"category": "时间", "description": "日期类型", "business_meaning": "生日、截止日期、开始日期"},
            "timestamp": {"category": "时间", "description": "时间戳类型", "business_meaning": "记录时间、版本时间"},
            "time": {"category": "时间", "description": "时间类型", "business_meaning": "营业时间、持续时间"},
            
            # 布尔类型
            "boolean": {"category": "逻辑", "description": "布尔类型", "business_meaning": "状态标识、开关、是否标记"},
            "tinyint": {"category": "逻辑", "description": "小整数（常用作布尔）", "business_meaning": "状态、标志位"},
            
            # JSON类型
            "json": {"category": "结构化", "description": "JSON数据类型", "business_meaning": "配置信息、扩展属性、复杂数据"}
        }
        
        # 字段名模式识别
        self.field_name_patterns = {
            # ID类字段
            r".*_?id$": {"type": "identifier", "meaning": "标识符", "description": "用于唯一标识记录"},
            r"^id$": {"type": "primary_key", "meaning": "主键", "description": "表的主键标识符"},
            
            # 时间类字段
            r".*created.*": {"type": "timestamp", "meaning": "创建时间", "description": "记录创建的时间"},
            r".*updated.*": {"type": "timestamp", "meaning": "更新时间", "description": "记录最后更新的时间"},
            r".*deleted.*": {"type": "timestamp", "meaning": "删除时间", "description": "记录删除的时间（软删除）"},
            r".*time$": {"type": "timestamp", "meaning": "时间字段", "description": "时间相关信息"},
            r".*date$": {"type": "date", "meaning": "日期字段", "description": "日期相关信息"},
            
            # 状态类字段
            r".*status$": {"type": "status", "meaning": "状态", "description": "记录的状态信息"},
            r".*state$": {"type": "status", "meaning": "状态", "description": "记录的状态信息"},
            r".*flag$": {"type": "flag", "meaning": "标志", "description": "布尔标志位"},
            r"is_.*": {"type": "boolean", "meaning": "是否标记", "description": "布尔判断字段"},
            
            # 名称类字段
            r".*name$": {"type": "name", "meaning": "名称", "description": "名称信息"},
            r".*title$": {"type": "title", "meaning": "标题", "description": "标题信息"},
            r".*desc.*": {"type": "description", "meaning": "描述", "description": "描述性信息"},
            
            # 数量类字段
            r".*count$": {"type": "count", "meaning": "计数", "description": "数量统计"},
            r".*amount$": {"type": "amount", "meaning": "金额", "description": "金额数值"},
            r".*price$": {"type": "price", "meaning": "价格", "description": "价格信息"},
            r".*total$": {"type": "total", "meaning": "总计", "description": "总计数值"}
        }
        
        # 表名业务含义映射
        self.table_business_meanings = {
            "user": "用户信息管理",
            "customer": "客户信息管理", 
            "order": "订单业务处理",
            "product": "产品信息管理",
            "category": "分类信息管理",
            "payment": "支付业务处理",
            "address": "地址信息管理",
            "log": "日志记录存储",
            "config": "配置信息管理",
            "role": "角色权限管理",
            "permission": "权限控制管理",
            "department": "部门组织管理",
            "employee": "员工信息管理",
            "inventory": "库存管理",
            "supplier": "供应商管理",
            "invoice": "发票管理",
            "report": "报表数据存储"
        }
    
    async def inject_semantic_info(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """注入表结构语义信息"""
        tables = context.get('tables', [])
        
        enhanced_context = context.copy()
        enhanced_context['table_structure_semantics'] = []
        
        if not tables:
            logger.warning("No tables found in context")
            return enhanced_context
        
        for table in tables:
            try:
                semantic_info = await self._create_table_semantic_info(table)
                enhanced_context['table_structure_semantics'].append(semantic_info.to_dict())
                logger.debug(f"Injected semantic info for table: {table.get('name', 'unknown')}")
            except Exception as e:
                logger.error(f"Failed to inject semantic info for table {table.get('name', 'unknown')}: {str(e)}")
        
        return enhanced_context
    
    async def _create_table_semantic_info(self, table: Dict[str, Any]) -> TableSemanticInfo:
        """创建表结构语义信息"""
        table_name = table.get('name', '')
        table_id = table.get('id', table_name)
        schema_name = table.get('schema', table.get('schema_name'))
        table_comment = table.get('comment', table.get('table_comment'))
        
        # 处理字段信息
        fields = table.get('fields', [])
        enhanced_fields = []
        primary_keys = []
        
        for field in fields:
            enhanced_field = await self._enhance_field_info(field, table_name)
            enhanced_fields.append(enhanced_field)
            
            # 收集主键信息
            if enhanced_field.get('is_primary_key') or enhanced_field.get('primary_key'):
                primary_keys.append(enhanced_field['name'])
        
        # 处理外键信息
        foreign_keys = self._process_foreign_keys(table.get('foreign_keys', []))
        
        # 处理索引信息
        indexes = self._process_indexes(table.get('indexes', []))
        
        # 推断业务含义
        business_meaning = self._infer_table_business_meaning(table_name, enhanced_fields, table_comment)
        
        return TableSemanticInfo(
            table_id=table_id,
            table_name=table_name,
            schema_name=schema_name,
            table_comment=table_comment,
            fields=enhanced_fields,
            primary_keys=primary_keys,
            foreign_keys=foreign_keys,
            indexes=indexes,
            business_meaning=business_meaning
        )
    
    async def _enhance_field_info(self, field: Dict[str, Any], table_name: str) -> Dict[str, Any]:
        """增强字段信息"""
        field_name = field.get('name', '')
        field_type = field.get('type', '').lower()
        field_comment = field.get('comment', '')
        
        # 基础字段信息
        enhanced_field = {
            'name': field_name,
            'type': field_type,
            'comment': field_comment,
            'is_nullable': field.get('is_nullable', field.get('nullable', True)),
            'is_primary_key': field.get('is_primary_key', field.get('primary_key', False)),
            'default_value': field.get('default_value', field.get('default')),
            'max_length': field.get('max_length', field.get('length')),
            'precision': field.get('precision'),
            'scale': field.get('scale')
        }
        
        # 数据类型语义化
        type_semantic = self._get_data_type_semantic(field_type)
        enhanced_field['type_semantic'] = type_semantic
        
        # 字段名模式识别
        field_pattern = self._recognize_field_pattern(field_name)
        enhanced_field['field_pattern'] = field_pattern
        
        # 业务含义推断
        business_meaning = self._infer_field_business_meaning(
            field_name, field_type, field_comment, table_name
        )
        enhanced_field['business_meaning'] = business_meaning
        
        # 约束信息语义化
        constraints = self._analyze_field_constraints(enhanced_field)
        enhanced_field['constraints_semantic'] = constraints
        
        return enhanced_field
    
    def _get_data_type_semantic(self, field_type: str) -> Dict[str, Any]:
        """获取数据类型语义信息"""
        # 提取基础类型（去除长度等修饰符）
        base_type = field_type.split('(')[0].lower()
        
        # 查找匹配的语义信息 - 优先精确匹配，然后前缀匹配
        # 先尝试精确匹配
        if base_type in self.data_type_semantics:
            return self.data_type_semantics[base_type].copy()
        
        # 再尝试前缀匹配（按长度降序，避免短类型名匹配长类型名）
        sorted_types = sorted(self.data_type_semantics.keys(), key=len, reverse=True)
        for type_key in sorted_types:
            if base_type.startswith(type_key):
                return self.data_type_semantics[type_key].copy()
        
        # 默认语义信息
        return {
            "category": "其他",
            "description": f"数据类型: {field_type}",
            "business_meaning": "通用数据字段"
        }
    
    def _recognize_field_pattern(self, field_name: str) -> Dict[str, Any]:
        """识别字段名模式"""
        import re
        
        field_name_lower = field_name.lower()
        
        for pattern, meaning in self.field_name_patterns.items():
            if re.match(pattern, field_name_lower):
                return meaning.copy()
        
        # 默认模式
        return {
            "type": "general",
            "meaning": "通用字段",
            "description": "通用业务字段"
        }
    
    def _infer_field_business_meaning(self, field_name: str, field_type: str, 
                                    field_comment: str, table_name: str) -> str:
        """推断字段业务含义"""
        meanings = []
        
        # 基于注释的含义
        if field_comment:
            meanings.append(f"注释说明: {field_comment}")
        
        # 基于字段名模式的含义
        pattern = self._recognize_field_pattern(field_name)
        if pattern['type'] != 'general':
            meanings.append(f"字段模式: {pattern['meaning']} - {pattern['description']}")
        
        # 基于数据类型的含义
        type_semantic = self._get_data_type_semantic(field_type)
        meanings.append(f"数据类型: {type_semantic['business_meaning']}")
        
        # 基于表名上下文的含义
        table_base = self._get_table_base_name(table_name)
        if table_base in self.table_business_meanings:
            table_meaning = self.table_business_meanings[table_base]
            meanings.append(f"表上下文: {table_meaning}中的{field_name}字段")
        
        return "; ".join(meanings)
    
    def _get_table_base_name(self, table_name: str) -> str:
        """获取表名基础形式"""
        base_name = table_name.lower()
        
        # 移除复数形式
        if base_name.endswith('s') and len(base_name) > 3:
            base_name = base_name[:-1]
        
        # 移除常见前缀
        prefixes = ['tbl_', 't_', 'tb_']
        for prefix in prefixes:
            if base_name.startswith(prefix):
                base_name = base_name[len(prefix):]
                break
        
        return base_name
    
    def _analyze_field_constraints(self, field: Dict[str, Any]) -> List[Dict[str, Any]]:
        """分析字段约束信息"""
        constraints = []
        
        # 主键约束
        if field.get('is_primary_key'):
            constraints.append({
                "type": "PRIMARY_KEY",
                "description": "主键约束，确保字段值唯一且非空",
                "business_impact": "作为记录的唯一标识符"
            })
        
        # 非空约束
        if not field.get('is_nullable', True):
            constraints.append({
                "type": "NOT_NULL",
                "description": "非空约束，字段值不能为空",
                "business_impact": "该字段为必填项"
            })
        
        # 长度约束
        if field.get('max_length'):
            constraints.append({
                "type": "LENGTH",
                "description": f"长度约束，最大长度为{field['max_length']}",
                "business_impact": f"输入内容不能超过{field['max_length']}个字符"
            })
        
        # 默认值约束
        if field.get('default_value') is not None:
            constraints.append({
                "type": "DEFAULT",
                "description": f"默认值约束，默认值为{field['default_value']}",
                "business_impact": "未指定值时使用默认值"
            })
        
        return constraints
    
    def _process_foreign_keys(self, foreign_keys: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """处理外键信息"""
        processed_fks = []
        
        for fk in foreign_keys:
            processed_fk = {
                "name": fk.get('name', ''),
                "column": fk.get('column', ''),
                "referenced_table": fk.get('referenced_table', ''),
                "referenced_column": fk.get('referenced_column', ''),
                "semantic_description": f"外键关联到{fk.get('referenced_table', '')}表的{fk.get('referenced_column', '')}字段",
                "business_meaning": f"建立与{fk.get('referenced_table', '')}表的关联关系，确保数据一致性"
            }
            processed_fks.append(processed_fk)
        
        return processed_fks
    
    def _process_indexes(self, indexes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """处理索引信息"""
        processed_indexes = []
        
        for index in indexes:
            index_type = index.get('type', 'BTREE').upper()
            columns = index.get('columns', [])
            
            processed_index = {
                "name": index.get('name', ''),
                "type": index_type,
                "columns": columns,
                "is_unique": index.get('is_unique', False),
                "semantic_description": self._get_index_semantic_description(index_type, columns, index.get('is_unique', False)),
                "performance_impact": self._get_index_performance_impact(index_type, len(columns))
            }
            processed_indexes.append(processed_index)
        
        return processed_indexes
    
    def _get_index_semantic_description(self, index_type: str, columns: List[str], is_unique: bool) -> str:
        """获取索引语义描述"""
        column_str = ", ".join(columns) if columns else "未知字段"
        
        if is_unique:
            return f"唯一{index_type}索引，确保{column_str}字段组合的唯一性"
        else:
            return f"{index_type}索引，加速基于{column_str}字段的查询"
    
    def _get_index_performance_impact(self, index_type: str, column_count: int) -> str:
        """获取索引性能影响描述"""
        if index_type == "BTREE":
            if column_count == 1:
                return "单字段B树索引，提供高效的等值和范围查询"
            else:
                return f"复合B树索引（{column_count}个字段），支持左前缀匹配查询"
        elif index_type == "HASH":
            return "哈希索引，提供高效的等值查询，不支持范围查询"
        elif index_type == "FULLTEXT":
            return "全文索引，支持文本内容的全文搜索"
        else:
            return f"{index_type}索引，提供特定的查询优化"
    
    def _infer_table_business_meaning(self, table_name: str, fields: List[Dict[str, Any]], 
                                    table_comment: str) -> str:
        """推断表的业务含义"""
        meanings = []
        
        # 基于表注释的含义
        if table_comment:
            meanings.append(f"表说明: {table_comment}")
        
        # 基于表名的含义
        table_base = self._get_table_base_name(table_name)
        if table_base in self.table_business_meanings:
            meanings.append(f"业务领域: {self.table_business_meanings[table_base]}")
        
        # 基于字段分析的含义
        field_analysis = self._analyze_table_fields(fields)
        if field_analysis:
            meanings.append(f"字段分析: {field_analysis}")
        
        # 基于表结构特征的含义
        structure_analysis = self._analyze_table_structure(fields)
        if structure_analysis:
            meanings.append(f"结构特征: {structure_analysis}")
        
        return "; ".join(meanings) if meanings else f"数据表{table_name}的业务信息存储"
    
    def _analyze_table_fields(self, fields: List[Dict[str, Any]]) -> str:
        """分析表字段特征"""
        field_types = {}
        
        for field in fields:
            pattern_type = field.get('field_pattern', {}).get('type', 'general')
            field_types[pattern_type] = field_types.get(pattern_type, 0) + 1
        
        analysis_parts = []
        
        if field_types.get('identifier', 0) > 1:
            analysis_parts.append("包含多个标识符字段")
        
        if field_types.get('timestamp', 0) >= 2:
            analysis_parts.append("具有完整的时间戳管理")
        
        if field_types.get('status', 0) > 0:
            analysis_parts.append("包含状态管理字段")
        
        if field_types.get('amount', 0) > 0 or field_types.get('price', 0) > 0:
            analysis_parts.append("涉及金额或价格信息")
        
        return ", ".join(analysis_parts)
    
    def _analyze_table_structure(self, fields: List[Dict[str, Any]]) -> str:
        """分析表结构特征"""
        total_fields = len(fields)
        nullable_fields = sum(1 for f in fields if f.get('is_nullable', True))
        pk_fields = sum(1 for f in fields if f.get('is_primary_key', False))
        
        analysis_parts = []
        
        if total_fields > 20:
            analysis_parts.append("大型表结构")
        elif total_fields < 5:
            analysis_parts.append("简单表结构")
        else:
            analysis_parts.append("中等规模表结构")
        
        if pk_fields == 0:
            analysis_parts.append("缺少主键定义")
        elif pk_fields > 1:
            analysis_parts.append("复合主键结构")
        
        nullable_ratio = nullable_fields / total_fields if total_fields > 0 else 0
        if nullable_ratio > 0.8:
            analysis_parts.append("大部分字段可为空")
        elif nullable_ratio < 0.3:
            analysis_parts.append("严格的非空约束")
        
        return ", ".join(analysis_parts)
    
    def get_table_structure_summary(self, tables: List[TableSemanticInfo]) -> str:
        """获取表结构摘要"""
        if not tables:
            return "无表结构信息"
        
        summary_parts = []
        
        total_tables = len(tables)
        total_fields = sum(len(table.fields) for table in tables)
        
        summary_parts.append(f"共{total_tables}个表，{total_fields}个字段")
        
        # 统计字段类型分布
        type_categories = {}
        for table in tables:
            for field in table.fields:
                category = field.get('type_semantic', {}).get('category', '其他')
                type_categories[category] = type_categories.get(category, 0) + 1
        
        if type_categories:
            category_desc = ", ".join([f"{cat}: {count}个" for cat, count in type_categories.items()])
            summary_parts.append(f"字段类型分布: {category_desc}")
        
        return "; ".join(summary_parts)
    
    def get_module_name(self) -> str:
        """获取模块名称"""
        return "TableStructureSemanticModule"


class TableRelationSemanticModule(BaseSemanticModule):
    """表关联语义注入模块 - Task 4.2.3"""
    
    def __init__(self):
        # JOIN类型语义描述
        self.join_type_semantics = {
            "INNER": {
                "description": "内连接",
                "business_meaning": "只返回两表中都存在匹配记录的数据",
                "use_case": "查询必须在两表中都有对应记录的数据",
                "performance": "通常性能最好，结果集最小"
            },
            "LEFT": {
                "description": "左外连接",
                "business_meaning": "返回左表所有记录，右表匹配记录，无匹配时右表字段为NULL",
                "use_case": "查询主表所有记录及其可能的关联信息",
                "performance": "性能中等，结果集包含左表所有记录"
            },
            "RIGHT": {
                "description": "右外连接",
                "business_meaning": "返回右表所有记录，左表匹配记录，无匹配时左表字段为NULL",
                "use_case": "查询从表所有记录及其可能的关联信息",
                "performance": "性能中等，结果集包含右表所有记录"
            },
            "FULL": {
                "description": "全外连接",
                "business_meaning": "返回两表所有记录，无匹配时对应字段为NULL",
                "use_case": "查询两表的完整数据集合",
                "performance": "性能较差，结果集最大"
            }
        }
        
        # 关联关系类型
        self.relation_types = {
            "ONE_TO_ONE": {
                "description": "一对一关系",
                "business_meaning": "每条记录在两表中都有唯一对应",
                "recommended_join": "INNER",
                "examples": ["用户-用户详情", "订单-订单详情"]
            },
            "ONE_TO_MANY": {
                "description": "一对多关系",
                "business_meaning": "主表一条记录对应从表多条记录",
                "recommended_join": "LEFT",
                "examples": ["用户-订单", "分类-产品", "部门-员工"]
            },
            "MANY_TO_ONE": {
                "description": "多对一关系",
                "business_meaning": "从表多条记录对应主表一条记录",
                "recommended_join": "INNER",
                "examples": ["订单-用户", "产品-分类", "员工-部门"]
            },
            "MANY_TO_MANY": {
                "description": "多对多关系",
                "business_meaning": "两表记录可以有多重对应关系",
                "recommended_join": "INNER",
                "examples": ["用户-角色", "产品-标签", "学生-课程"]
            }
        }
        
        # 常见表关联模式
        self.common_relation_patterns = {
            # 用户相关
            "user": {
                "order": {"type": "ONE_TO_MANY", "join_field": "user_id", "business": "用户的订单记录"},
                "profile": {"type": "ONE_TO_ONE", "join_field": "user_id", "business": "用户详细信息"},
                "addresse": {"type": "ONE_TO_MANY", "join_field": "user_id", "business": "用户地址信息"},  # addresses -> addresse
                "payment": {"type": "ONE_TO_MANY", "join_field": "user_id", "business": "用户支付记录"}
            },
            # 订单相关
            "order": {
                "user": {"type": "MANY_TO_ONE", "join_field": "user_id", "business": "订单所属用户"},
                "order_item": {"type": "ONE_TO_MANY", "join_field": "order_id", "business": "订单商品明细"},
                "payment": {"type": "ONE_TO_MANY", "join_field": "order_id", "business": "订单支付记录"},
                "shipment": {"type": "ONE_TO_ONE", "join_field": "order_id", "business": "订单物流信息"}
            },
            # 产品相关
            "product": {
                "categorie": {"type": "MANY_TO_ONE", "join_field": "category_id", "business": "产品分类"},  # categories -> categorie
                "order_item": {"type": "ONE_TO_MANY", "join_field": "product_id", "business": "产品销售记录"},
                "review": {"type": "ONE_TO_MANY", "join_field": "product_id", "business": "产品评价"},
                "inventor": {"type": "ONE_TO_ONE", "join_field": "product_id", "business": "产品库存"}  # inventory -> inventor
            }
        }
    
    async def inject_semantic_info(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """注入表关联语义信息"""
        tables = context.get('tables', [])
        
        enhanced_context = context.copy()
        enhanced_context['table_relation_semantics'] = []
        
        if len(tables) < 2:
            logger.warning("Need at least 2 tables to analyze relations")
            return enhanced_context
        
        try:
            # 发现表间关联关系
            relations = await self._discover_table_relations(tables)
            
            # 为每个关联关系创建语义信息
            for relation in relations:
                semantic_info = await self._create_relation_semantic_info(relation, tables)
                enhanced_context['table_relation_semantics'].append(semantic_info.to_dict())
            
            # 生成最优关联路径
            if len(relations) > 1:
                optimal_paths = self._generate_optimal_join_paths(relations, tables)
                enhanced_context['optimal_join_paths'] = optimal_paths
            
            logger.debug(f"Injected {len(relations)} table relation semantic info")
            
        except Exception as e:
            logger.error(f"Failed to inject table relation semantic info: {str(e)}")
        
        return enhanced_context
    
    async def _discover_table_relations(self, tables: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """发现表间关联关系"""
        relations = []
        
        # 基于外键发现关联关系
        fk_relations = self._discover_foreign_key_relations(tables)
        relations.extend(fk_relations)
        
        # 基于字段名模式发现潜在关联
        pattern_relations = self._discover_pattern_based_relations(tables)
        relations.extend(pattern_relations)
        
        # 基于业务模式发现关联
        business_relations = self._discover_business_pattern_relations(tables)
        relations.extend(business_relations)
        
        # 去重和优化
        relations = self._deduplicate_relations(relations)
        
        return relations
    
    def _discover_foreign_key_relations(self, tables: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """基于外键发现关联关系"""
        relations = []
        
        for table in tables:
            table_name = table.get('name', '')
            foreign_keys = table.get('foreign_keys', [])
            
            for fk in foreign_keys:
                relation = {
                    "source_table": table_name,
                    "target_table": fk.get('referenced_table', ''),
                    "source_field": fk.get('column', ''),
                    "target_field": fk.get('referenced_column', ''),
                    "relation_type": "FOREIGN_KEY",
                    "confidence": 1.0,  # 外键关系置信度最高
                    "discovery_method": "foreign_key"
                }
                relations.append(relation)
        
        return relations
    
    def _discover_pattern_based_relations(self, tables: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """基于字段名模式发现潜在关联"""
        relations = []
        table_fields = {}
        
        # 收集所有表的字段信息
        for table in tables:
            table_name = table.get('name', '')
            fields = table.get('fields', [])
            table_fields[table_name] = {field.get('name', ''): field for field in fields}
        
        # 查找潜在的关联字段
        for source_table, source_fields in table_fields.items():
            for target_table, target_fields in table_fields.items():
                if source_table == target_table:
                    continue
                
                # 查找 table_id 模式
                target_id_field = f"{target_table.rstrip('s')}_id"  # users -> user_id
                if target_id_field in source_fields and 'id' in target_fields:
                    relation = {
                        "source_table": source_table,
                        "target_table": target_table,
                        "source_field": target_id_field,
                        "target_field": "id",
                        "relation_type": "PATTERN_MATCH",
                        "confidence": 0.8,
                        "discovery_method": "field_pattern"
                    }
                    relations.append(relation)
                
                # 查找相同字段名
                for source_field_name, source_field in source_fields.items():
                    if source_field_name in target_fields:
                        # 排除常见的非关联字段
                        if source_field_name not in ['id', 'created_at', 'updated_at', 'status', 'name']:
                            relation = {
                                "source_table": source_table,
                                "target_table": target_table,
                                "source_field": source_field_name,
                                "target_field": source_field_name,
                                "relation_type": "SAME_FIELD",
                                "confidence": 0.6,
                                "discovery_method": "same_field_name"
                            }
                            relations.append(relation)
        
        return relations
    
    def _discover_business_pattern_relations(self, tables: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """基于业务模式发现关联"""
        relations = []
        
        for table in tables:
            table_name = table.get('name', '').lower()
            
            # 查找表名的基础形式
            base_name = self._get_table_base_name(table_name)
            
            if base_name in self.common_relation_patterns:
                patterns = self.common_relation_patterns[base_name]
                
                for other_table in tables:
                    if table == other_table:  # 跳过自己
                        continue
                        
                    other_table_name = other_table.get('name', '').lower()
                    other_base_name = self._get_table_base_name(other_table_name)
                    
                    if other_base_name in patterns:
                        pattern = patterns[other_base_name]
                        
                        # 验证关联字段是否存在
                        join_field = pattern['join_field']
                        source_field = join_field
                        target_field = "id"
                        
                        # 检查字段是否存在
                        if (self._field_exists_in_table(table, source_field) or 
                            self._field_exists_in_table(other_table, source_field)):
                            
                            relation = {
                                "source_table": table.get('name', ''),
                                "target_table": other_table.get('name', ''),
                                "source_field": source_field,
                                "target_field": target_field,
                                "relation_type": pattern['type'],
                                "confidence": 0.7,
                                "discovery_method": "business_pattern",
                                "business_meaning": pattern['business']
                            }
                            relations.append(relation)
        
        return relations
    
    def _get_table_base_name(self, table_name: str) -> str:
        """获取表名的基础形式"""
        # 移除常见前缀和后缀
        base_name = table_name.lower()
        
        # 移除复数形式
        if base_name.endswith('s') and len(base_name) > 3:
            base_name = base_name[:-1]
        
        # 移除常见前缀
        prefixes = ['tbl_', 't_', 'tb_']
        for prefix in prefixes:
            if base_name.startswith(prefix):
                base_name = base_name[len(prefix):]
                break
        
        return base_name
    
    def _field_exists_in_table(self, table: Dict[str, Any], field_name: str) -> bool:
        """检查字段是否存在于表中"""
        fields = table.get('fields', [])
        field_names = [field.get('name', '').lower() for field in fields]
        return field_name.lower() in field_names
    
    def _deduplicate_relations(self, relations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """去重和优化关联关系"""
        unique_relations = {}
        
        for relation in relations:
            # 创建关联关系的唯一键
            key = f"{relation['source_table']}-{relation['target_table']}-{relation['source_field']}-{relation['target_field']}"
            
            # 保留置信度最高的关联关系
            if key not in unique_relations or relation['confidence'] > unique_relations[key]['confidence']:
                unique_relations[key] = relation
        
        return list(unique_relations.values())
    
    async def _create_relation_semantic_info(self, relation: Dict[str, Any], tables: List[Dict[str, Any]]) -> TableRelationSemanticInfo:
        """创建关联关系语义信息"""
        # 生成关联ID
        relation_id = f"rel_{relation['source_table']}_{relation['target_table']}_{relation['source_field']}"
        
        # 推荐JOIN类型
        recommended_join = self._recommend_join_type(relation, tables)
        
        # 创建JOIN条件
        join_conditions = [{
            "source_field": relation['source_field'],
            "target_field": relation['target_field'],
            "operator": "=",
            "condition_type": "EQUALITY"
        }]
        
        # 生成关联描述
        relation_description = self._generate_relation_description(relation, recommended_join)
        
        # 生成业务逻辑说明
        business_logic = self._generate_business_logic(relation, tables)
        
        return TableRelationSemanticInfo(
            relation_id=relation_id,
            source_table=relation['source_table'],
            target_table=relation['target_table'],
            join_type=recommended_join,
            join_conditions=join_conditions,
            relation_description=relation_description,
            business_logic=business_logic
        )
    
    def _recommend_join_type(self, relation: Dict[str, Any], tables: List[Dict[str, Any]]) -> str:
        """推荐JOIN类型"""
        relation_type = relation.get('relation_type', '')
        confidence = relation.get('confidence', 0.5)
        
        # 基于关联类型推荐
        if relation_type in self.relation_types:
            return self.relation_types[relation_type]['recommended_join']
        
        # 基于外键关系推荐
        if relation.get('discovery_method') == 'foreign_key':
            return "INNER"  # 外键关系通常使用内连接
        
        # 基于字段名模式推荐
        source_field = relation.get('source_field', '').lower()
        if source_field.endswith('_id'):
            return "LEFT"  # ID字段通常使用左连接保留主表数据
        
        # 默认推荐
        return "INNER"
    
    def _generate_relation_description(self, relation: Dict[str, Any], join_type: str) -> str:
        """生成关联关系描述"""
        source_table = relation['source_table']
        target_table = relation['target_table']
        source_field = relation['source_field']
        target_field = relation['target_field']
        discovery_method = relation.get('discovery_method', 'unknown')
        
        join_desc = self.join_type_semantics.get(join_type, {}).get('description', join_type)
        
        if discovery_method == 'foreign_key':
            return f"通过外键{source_field}将{source_table}表与{target_table}表进行{join_desc}，关联条件：{source_table}.{source_field} = {target_table}.{target_field}"
        elif discovery_method == 'field_pattern':
            return f"基于字段名模式将{source_table}表与{target_table}表进行{join_desc}，关联条件：{source_table}.{source_field} = {target_table}.{target_field}"
        elif discovery_method == 'business_pattern':
            return f"基于业务模式将{source_table}表与{target_table}表进行{join_desc}，关联条件：{source_table}.{source_field} = {target_table}.{target_field}"
        else:
            return f"将{source_table}表与{target_table}表进行{join_desc}，关联条件：{source_table}.{source_field} = {target_table}.{target_field}"
    
    def _generate_business_logic(self, relation: Dict[str, Any], tables: List[Dict[str, Any]]) -> str:
        """生成业务逻辑说明"""
        source_table = relation['source_table']
        target_table = relation['target_table']
        
        # 如果有预定义的业务含义，直接使用
        if 'business_meaning' in relation:
            return relation['business_meaning']
        
        # 基于表名推断业务逻辑
        source_base = self._get_table_base_name(source_table)
        target_base = self._get_table_base_name(target_table)
        
        # 常见业务逻辑模式
        business_patterns = {
            ("user", "order"): "用户可以有多个订单，每个订单属于一个用户",
            ("order", "order_item"): "订单包含多个商品明细，每个明细属于一个订单",
            ("product", "category"): "产品属于某个分类，每个分类包含多个产品",
            ("user", "profile"): "用户有唯一的详细信息，一对一关系",
            ("department", "employee"): "部门包含多个员工，每个员工属于一个部门",
            ("customer", "address"): "客户可以有多个地址，每个地址属于一个客户"
        }
        
        pattern_key = (source_base, target_base)
        reverse_key = (target_base, source_base)
        
        if pattern_key in business_patterns:
            return business_patterns[pattern_key]
        elif reverse_key in business_patterns:
            return business_patterns[reverse_key]
        else:
            return f"{source_table}表与{target_table}表存在业务关联关系"
    
    def _generate_optimal_join_paths(self, relations: List[Dict[str, Any]], tables: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """生成最优关联路径"""
        paths = []
        
        # 构建关联图
        relation_graph = self._build_relation_graph(relations)
        
        # 为每对表找到最优路径
        table_names = [table.get('name', '') for table in tables]
        
        for i, source_table in enumerate(table_names):
            for j, target_table in enumerate(table_names):
                if i >= j:  # 避免重复和自连接
                    continue
                
                # 查找最短路径
                path = self._find_shortest_path(relation_graph, source_table, target_table)
                
                if path:
                    path_info = {
                        "source_table": source_table,
                        "target_table": target_table,
                        "path_length": len(path) - 1,
                        "join_sequence": self._generate_join_sequence(path, relations),
                        "estimated_performance": self._estimate_path_performance(path, relations),
                        "business_description": self._describe_join_path(path, relations)
                    }
                    paths.append(path_info)
        
        # 按性能排序
        paths.sort(key=lambda x: (x['path_length'], -x['estimated_performance']))
        
        return paths
    
    def _build_relation_graph(self, relations: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        """构建关联关系图"""
        graph = {}
        
        for relation in relations:
            source = relation['source_table']
            target = relation['target_table']
            
            if source not in graph:
                graph[source] = []
            if target not in graph:
                graph[target] = []
            
            # 双向关联
            graph[source].append(target)
            graph[target].append(source)
        
        return graph
    
    def _find_shortest_path(self, graph: Dict[str, List[str]], start: str, end: str) -> List[str]:
        """查找最短路径（BFS）"""
        if start == end:
            return [start]
        
        if start not in graph or end not in graph:
            return []
        
        queue = [(start, [start])]
        visited = {start}
        
        while queue:
            current, path = queue.pop(0)
            
            for neighbor in graph[current]:
                if neighbor == end:
                    return path + [neighbor]
                
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, path + [neighbor]))
        
        return []  # 无路径
    
    def _generate_join_sequence(self, path: List[str], relations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """生成JOIN序列"""
        join_sequence = []
        
        for i in range(len(path) - 1):
            source_table = path[i]
            target_table = path[i + 1]
            
            # 查找对应的关联关系
            relation = self._find_relation(relations, source_table, target_table)
            
            if relation:
                join_info = {
                    "step": i + 1,
                    "source_table": source_table,
                    "target_table": target_table,
                    "join_type": self._recommend_join_type(relation, []),
                    "join_condition": f"{source_table}.{relation['source_field']} = {target_table}.{relation['target_field']}",
                    "confidence": relation.get('confidence', 0.5)
                }
                join_sequence.append(join_info)
        
        return join_sequence
    
    def _find_relation(self, relations: List[Dict[str, Any]], table1: str, table2: str) -> Optional[Dict[str, Any]]:
        """查找两表间的关联关系"""
        for relation in relations:
            if ((relation['source_table'] == table1 and relation['target_table'] == table2) or
                (relation['source_table'] == table2 and relation['target_table'] == table1)):
                return relation
        return None
    
    def _estimate_path_performance(self, path: List[str], relations: List[Dict[str, Any]]) -> float:
        """估算路径性能"""
        if len(path) <= 1:
            return 1.0
        
        # 基础性能分数（路径越短越好）
        base_score = 1.0 / len(path)
        
        # 关联质量分数
        quality_score = 0.0
        relation_count = 0
        
        for i in range(len(path) - 1):
            relation = self._find_relation(relations, path[i], path[i + 1])
            if relation:
                quality_score += relation.get('confidence', 0.5)
                relation_count += 1
        
        if relation_count > 0:
            quality_score /= relation_count
        
        return (base_score + quality_score) / 2
    
    def _describe_join_path(self, path: List[str], relations: List[Dict[str, Any]]) -> str:
        """描述JOIN路径"""
        if len(path) <= 1:
            return "单表查询"
        
        descriptions = []
        
        for i in range(len(path) - 1):
            source_table = path[i]
            target_table = path[i + 1]
            relation = self._find_relation(relations, source_table, target_table)
            
            if relation:
                business_meaning = relation.get('business_meaning', f"{source_table}与{target_table}的关联")
                descriptions.append(business_meaning)
        
        return " → ".join(descriptions)
    
    def get_relation_summary(self, relations: List[TableRelationSemanticInfo]) -> str:
        """获取关联关系摘要"""
        if not relations:
            return "无表关联关系"
        
        summary_parts = []
        
        # 统计JOIN类型
        join_types = {}
        for relation in relations:
            join_type = relation.join_type
            join_types[join_type] = join_types.get(join_type, 0) + 1
        
        summary_parts.append(f"发现{len(relations)}个表关联关系")
        
        for join_type, count in join_types.items():
            join_desc = self.join_type_semantics.get(join_type, {}).get('description', join_type)
            summary_parts.append(f"{join_desc}: {count}个")
        
        return "; ".join(summary_parts)
    
    def get_module_name(self) -> str:
        """获取模块名称"""
        return "TableRelationSemanticModule"


class DictionarySemanticModule(BaseSemanticModule):
    """数据字典语义注入模块 - Task 4.2.4"""
    
    async def inject_semantic_info(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """注入数据字典语义信息"""
        # TODO: 实现数据字典语义注入
        return context
    
    def get_module_name(self) -> str:
        """获取模块名称"""
        return "DictionarySemanticModule"


class KnowledgeSemanticModule(BaseSemanticModule):
    """知识库语义注入模块 - Task 4.2.5"""
    
    async def inject_semantic_info(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """注入知识库语义信息"""
        # TODO: 实现知识库语义注入
        return context
    
    def get_module_name(self) -> str:
        """获取模块名称"""
        return "KnowledgeSemanticModule"


class SemanticContextAggregator:
    """语义上下文聚合引擎 - Task 4.2.6"""
    
    def __init__(self, max_tokens: int = 4000):
        self.max_tokens = max_tokens
        self.modules: List[BaseSemanticModule] = [
            DataSourceSemanticModule(),
            TableStructureSemanticModule(),
            TableRelationSemanticModule(),
            DictionarySemanticModule(),
            KnowledgeSemanticModule()
        ]
    
    async def aggregate_semantic_context(self, base_context: Dict[str, Any], 
                                       enabled_modules: List[str] = None) -> Dict[str, Any]:
        """聚合语义上下文"""
        if enabled_modules is None:
            enabled_modules = [module.get_module_name() for module in self.modules]
        
        enhanced_context = base_context.copy()
        
        for module in self.modules:
            if module.get_module_name() in enabled_modules:
                try:
                    enhanced_context = await module.inject_semantic_info(enhanced_context)
                    logger.debug(f"Applied semantic module: {module.get_module_name()}")
                except Exception as e:
                    logger.error(f"Failed to apply semantic module {module.get_module_name()}: {str(e)}")
        
        # Token管理和上下文优化
        optimized_context = self._optimize_context_for_tokens(enhanced_context)
        
        return optimized_context
    
    def _optimize_context_for_tokens(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """优化上下文以控制Token使用量"""
        # 估算当前Token数量
        context_str = json.dumps(context, ensure_ascii=False)
        estimated_tokens = len(context_str) // 4  # 简单估算
        
        if estimated_tokens <= self.max_tokens:
            return context
        
        # 需要优化：按重要性保留信息
        optimized = context.copy()
        
        # 优先级：数据源语义 > 表结构语义 > 数据字典语义 > 表关联语义 > 知识库语义
        priority_keys = [
            'data_source_semantics',
            'table_structure_semantics', 
            'dictionary_semantics',
            'table_relation_semantics',
            'knowledge_semantics'
        ]
        
        # 逐步移除低优先级信息直到Token数量合适
        for key in reversed(priority_keys):
            if key in optimized:
                # 先尝试压缩该部分信息
                if isinstance(optimized[key], list) and len(optimized[key]) > 3:
                    optimized[key] = optimized[key][:3]  # 只保留前3个
                
                # 重新估算Token数量
                context_str = json.dumps(optimized, ensure_ascii=False)
                estimated_tokens = len(context_str) // 4
                
                if estimated_tokens <= self.max_tokens:
                    break
                
                # 如果还是太多，完全移除该部分
                del optimized[key]
                context_str = json.dumps(optimized, ensure_ascii=False)
                estimated_tokens = len(context_str) // 4
                
                if estimated_tokens <= self.max_tokens:
                    break
        
        logger.info(f"Context optimized: {len(context_str)} chars -> {len(json.dumps(optimized, ensure_ascii=False))} chars")
        return optimized
    
    def get_enabled_modules(self) -> List[str]:
        """获取已启用的模块列表"""
        return [module.get_module_name() for module in self.modules]


# 全局语义聚合器实例
_semantic_aggregator: Optional[SemanticContextAggregator] = None


def get_semantic_aggregator() -> SemanticContextAggregator:
    """获取语义聚合器实例"""
    global _semantic_aggregator
    if _semantic_aggregator is None:
        _semantic_aggregator = SemanticContextAggregator()
    return _semantic_aggregator


def init_semantic_aggregator(max_tokens: int = 4000) -> SemanticContextAggregator:
    """初始化语义聚合器"""
    global _semantic_aggregator
    _semantic_aggregator = SemanticContextAggregator(max_tokens)
    return _semantic_aggregator