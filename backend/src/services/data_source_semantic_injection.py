"""
数据源语义注入服务

实现数据源类型和SQL方言信息的智能注入，创建MySQL和SQL Server语法差异的自动适配，
添加连接配置和性能特征的上下文增强，支持数据源级别的业务规则注入。
"""

import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class DatabaseType(str, Enum):
    """数据库类型枚举"""
    MYSQL = "mysql"
    SQL_SERVER = "sqlserver"
    POSTGRESQL = "postgresql"
    ORACLE = "oracle"


@dataclass
class DataSourceSemanticInfo:
    """数据源语义信息"""
    database_type: DatabaseType
    sql_dialect: Dict[str, Any]
    performance_tips: List[str]
    business_rules: List[str]
    connection_config: Dict[str, Any]


class DataSourceSemanticInjectionService:
    """数据源语义注入服务"""
    
    def __init__(self, db_session=None):
        self.db = db_session
        
        # SQL方言差异配置
        self.sql_dialects = {
            DatabaseType.MYSQL: {
                "limit_syntax": "LIMIT {limit}",
                "top_syntax": None,
                "identifier_quote": "`",
                "string_quote": "'",
                "date_format": "%Y-%m-%d",
                "datetime_format": "%Y-%m-%d %H:%i:%s"
            },
            DatabaseType.SQL_SERVER: {
                "limit_syntax": None,
                "top_syntax": "TOP {limit}",
                "identifier_quote": "[",
                "string_quote": "'",
                "date_format": "yyyy-MM-dd",
                "datetime_format": "yyyy-MM-dd HH:mm:ss"
            }
        }
        
        # 性能优化建议
        self.performance_tips = {
            DatabaseType.MYSQL: [
                "使用索引优化查询性能",
                "避免SELECT *，明确指定需要的字段",
                "使用LIMIT限制返回结果数量",
                "合理使用JOIN，避免笛卡尔积"
            ],
            DatabaseType.SQL_SERVER: [
                "使用TOP限制返回结果数量",
                "利用索引提升查询效率",
                "避免在WHERE子句中使用函数",
                "合理使用存储过程"
            ]
        }
        
        # 业务规则配置
        self.business_rules = {
            DatabaseType.MYSQL: [
                "查询超时时间设置为30秒",
                "单次查询结果不超过10000行",
                "避免使用DELETE和UPDATE操作"
            ],
            DatabaseType.SQL_SERVER: [
                "查询超时时间设置为60秒",
                "使用WITH (NOLOCK)提升查询性能",
                "避免长时间锁表操作"
            ]
        }
    
    def inject_data_source_semantics(
        self,
        data_source_id: Optional[str] = None,
        database_type: Optional[DatabaseType] = None
    ) -> DataSourceSemanticInfo:
        """
        注入数据源语义信息
        
        Args:
            data_source_id: 数据源ID
            database_type: 数据库类型
            
        Returns:
            数据源语义信息
        """
        try:
            # 如果提供了数据源ID，从数据库获取类型
            if data_source_id and self.db:
                db_type = self._get_database_type_from_db(data_source_id)
            else:
                db_type = database_type or DatabaseType.MYSQL
            
            # 获取SQL方言信息
            sql_dialect = self.sql_dialects.get(db_type, self.sql_dialects[DatabaseType.MYSQL])
            
            # 获取性能建议
            performance_tips = self.performance_tips.get(db_type, self.performance_tips[DatabaseType.MYSQL])
            
            # 获取业务规则
            business_rules = self.business_rules.get(db_type, self.business_rules[DatabaseType.MYSQL])
            
            # 生成连接配置建议
            connection_config = self._generate_connection_config(db_type)
            
            return DataSourceSemanticInfo(
                database_type=db_type,
                sql_dialect=sql_dialect,
                performance_tips=performance_tips,
                business_rules=business_rules,
                connection_config=connection_config
            )
            
        except Exception as e:
            logger.error(f"数据源语义注入失败: {str(e)}", exc_info=True)
            # 返回默认MySQL配置
            return DataSourceSemanticInfo(
                database_type=DatabaseType.MYSQL,
                sql_dialect=self.sql_dialects[DatabaseType.MYSQL],
                performance_tips=self.performance_tips[DatabaseType.MYSQL],
                business_rules=self.business_rules[DatabaseType.MYSQL],
                connection_config=self._generate_connection_config(DatabaseType.MYSQL)
            )
    
    def _get_database_type_from_db(self, data_source_id: str) -> DatabaseType:
        """从数据库获取数据源类型"""
        try:
            # 这里应该查询数据库获取数据源类型
            # 暂时返回MySQL作为默认值
            return DatabaseType.MYSQL
        except Exception as e:
            logger.error(f"获取数据源类型失败: {str(e)}")
            return DatabaseType.MYSQL
    
    def _generate_connection_config(self, db_type: DatabaseType) -> Dict[str, Any]:
        """生成连接配置建议"""
        base_config = {
            "pool_size": 10,
            "max_overflow": 20,
            "pool_timeout": 30,
            "pool_recycle": 3600
        }
        
        if db_type == DatabaseType.MYSQL:
            base_config.update({
                "charset": "utf8mb4",
                "autocommit": True,
                "connect_timeout": 10
            })
        elif db_type == DatabaseType.SQL_SERVER:
            base_config.update({
                "driver": "ODBC Driver 18 for SQL Server",
                "timeout": 30,
                "autocommit": True
            })
        
        return base_config
    
    def get_sql_syntax_for_limit(self, db_type: DatabaseType, limit: int) -> str:
        """获取限制查询结果数量的SQL语法"""
        dialect = self.sql_dialects.get(db_type, self.sql_dialects[DatabaseType.MYSQL])
        
        if dialect.get("limit_syntax"):
            return dialect["limit_syntax"].format(limit=limit)
        elif dialect.get("top_syntax"):
            return dialect["top_syntax"].format(limit=limit)
        else:
            return f"LIMIT {limit}"  # 默认使用LIMIT语法
    
    def get_identifier_quote(self, db_type: DatabaseType) -> str:
        """获取标识符引用符号"""
        dialect = self.sql_dialects.get(db_type, self.sql_dialects[DatabaseType.MYSQL])
        return dialect.get("identifier_quote", "`")
    
    def generate_semantic_context(self, semantic_info: DataSourceSemanticInfo) -> str:
        """生成语义上下文字符串"""
        context_parts = [
            f"数据库类型: {semantic_info.database_type.value}",
            f"SQL方言: {semantic_info.sql_dialect}",
            f"性能建议: {'; '.join(semantic_info.performance_tips)}",
            f"业务规则: {'; '.join(semantic_info.business_rules)}"
        ]
        
        return "\n".join(context_parts)