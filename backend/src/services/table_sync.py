"""
表结构同步服务
负责从数据源数据库同步表结构到系统数据库
支持MySQL和PostgreSQL数据库
"""
import logging
from typing import Dict, List, Optional, Tuple
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError, OperationalError, DatabaseError
from src.models.data_preparation_model import DataTable, TableField
from src.models.data_source_model import DataSource
from src.database import get_db
from datetime import datetime
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

class TableSyncService:
    """
    表结构同步服务
    负责从数据源数据库同步表结构到系统数据库
    """
    
    def __init__(self):
        # 移除了对DatabaseService的依赖，因为该模块不存在
        # 直接使用传入的db会话进行数据库操作
        pass
    
    def _build_connection_string(self, source: DataSource) -> str:
        """
        根据数据源信息构建数据库连接字符串
        
        Args:
            source: 数据源对象
            
        Returns:
            str: 数据库连接字符串
        """
        if source.db_type == "MySQL":
            return f"mysql+mysqlconnector://{source.username}:{source.password}@{source.host}:{source.port}/{source.database_name}"
        elif source.db_type == "PostgreSQL":
            return f"postgresql://{source.username}:{source.password}@{source.host}:{source.port}/{source.database_name}"
        else:
            raise ValueError(f"不支持的数据库类型: {source.db_type}")
    
    def _get_table_structure(self, connection, db_type: str, table_name: str) -> List[Dict[str, str]]:
        """
        从数据库中获取表结构信息
        
        Args:
            connection: 数据库连接
            db_type: 数据库类型 (MySQL 或 PostgreSQL)
            table_name: 表名
            
        Returns:
            List[Dict[str, str]]: 字段信息列表，每个元素包含 field_name, data_type, is_nullable, is_primary_key, description
        """
        if db_type == "MySQL":
            query = text("""
                SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, COLUMN_KEY, COLUMN_COMMENT
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_SCHEMA = :database_name AND TABLE_NAME = :table_name
            """)
            result = connection.execute(query, {
                "database_name": connection.engine.url.database,
                "table_name": table_name
            })
            
            fields = []
            for row in result:
                field_name, data_type, is_nullable, column_key, description = row
                is_primary_key = column_key == "PRI"
                
                fields.append({
                    "field_name": field_name,
                    "data_type": data_type,
                    "is_nullable": is_nullable == "YES",
                    "is_primary_key": is_primary_key,
                    "description": description if description else ""
                })
            return fields
        
        elif db_type == "PostgreSQL":
            query = text("""
                SELECT 
                    a.attname AS column_name,
                    pg_catalog.format_type(a.atttypid, a.atttypmod) AS data_type,
                    a.attnotnull AS is_nullable,
                    CASE 
                        WHEN pk.column_name IS NOT NULL THEN 'PRI'
                        ELSE ''
                    END AS column_key,
                    col_description(a.attrelid, a.attnum) AS description
                FROM pg_attribute a
                JOIN pg_class c ON a.attrelid = c.oid
                JOIN pg_namespace n ON c.relnamespace = n.oid
                LEFT JOIN (
                    SELECT kcu.column_name
                    FROM information_schema.table_constraints tc
                    JOIN information_schema.key_column_usage kcu 
                        ON tc.constraint_name = kcu.constraint_name
                        AND tc.table_schema = kcu.table_schema
                    WHERE tc.constraint_type = 'PRIMARY KEY'
                        AND tc.table_name = :table_name
                ) pk ON a.attname = pk.column_name
                WHERE c.relname = :table_name
                    AND n.nspname = 'public'
                    AND a.attnum > 0
                    AND NOT a.attisdropped
                ORDER BY a.attnum
            """)
            
            result = connection.execute(query, {
                "table_name": table_name
            })
            
            fields = []
            for row in result:
                field_name, data_type, is_nullable, column_key, description = row
                is_primary_key = column_key == "PRI"
                
                fields.append({
                    "field_name": field_name,
                    "data_type": data_type,
                    "is_nullable": is_nullable,
                    "is_primary_key": is_primary_key,
                    "description": description if description else ""
                })
            return fields
        
        else:
            raise ValueError(f"不支持的数据库类型: {db_type}")
    
    def _field_has_changed(self, existing_field: TableField, field_info: Dict[str, str]) -> bool:
        """
        检查字段信息是否已更改
        
        Args:
            existing_field: 现有字段对象
            field_info: 数据库中获取的字段信息
            
        Returns:
            bool: 如果字段信息有变化返回True，否则返回False
        """
        # 检查数据类型是否变化
        if existing_field.data_type != field_info['data_type']:
            return True
        
        # 检查是否允许为空是否变化
        if existing_field.is_nullable != field_info['is_nullable']:
            return True
        
        # 检查是否为主键是否变化
        if existing_field.is_primary_key != field_info['is_primary_key']:
            return True
        
        # 检查描述是否变化
        if existing_field.description != field_info['description']:
            return True
        
        return False
    
    def _create_field(self, db: Session, table_id: str, field_info: Dict[str, str]) -> None:
        """
        创建新字段
        
        Args:
            db: 数据库会话
            table_id: 表ID
            field_info: 字段信息字典
        """
        field = TableField(
            table_id=table_id,
            field_name=field_info['field_name'],
            data_type=field_info['data_type'],
            is_nullable=field_info['is_nullable'],
            is_primary_key=field_info['is_primary_key'],
            description=field_info['description']
        )
        db.add(field)
    
    def _update_field(self, db: Session, field: TableField, field_info: Dict[str, str]) -> None:
        """
        更新现有字段
        
        Args:
            db: 数据库会话
            field: 现有字段对象
            field_info: 数据库中获取的字段信息
        """
        field.data_type = field_info['data_type']
        field.is_nullable = field_info['is_nullable']
        field.is_primary_key = field_info['is_primary_key']
        field.description = field_info['description']
        
    def sync_table_structure(self, db: Session, table_id: str) -> Dict[str, int]:
        """
        同步指定数据表的结构
        
        Args:
            db: 数据库会话
            table_id: 数据表ID
            
        Returns:
            Dict[str, int]: 同步结果统计 {created: int, updated: int, deleted: int}
            
        Raises:
            ValueError: 数据表或数据源不存在
            ConnectionError: 数据库连接失败
            PermissionError: 数据库权限不足
        """
        # 获取数据表信息
        table = db.query(DataTable).filter(DataTable.id == table_id).first()
        if not table:
            logger.error(f"Data table with ID {table_id} not found")
            raise ValueError(f"数据表不存在: {table_id}")
        
        # 获取数据源信息
        source = db.query(DataSource).filter(DataSource.id == table.data_source_id).first()
        if not source:
            logger.error(f"Data source with ID {table.data_source_id} not found")
            raise ValueError(f"数据源不存在: {table.data_source_id}")
        
        # 检查数据源是否启用
        if not source.status:
            logger.error(f"Data source {source.name} is disabled")
            raise ValueError(f"数据源 {source.name} 已禁用")
        
        # 根据数据库类型构建连接字符串
        connection_string = self._build_connection_string(source)
        
        try:
            # 创建数据库引擎
            engine = create_engine(connection_string)
            
            # 连接数据库并获取表结构
            with engine.connect() as connection:
                # 获取表结构信息
                table_structure = self._get_table_structure(connection, source.db_type, table.table_name)
                
                # 获取当前系统中的字段
                existing_fields = db.query(TableField).filter(TableField.table_id == table_id).all()
                existing_fields_map = {field.field_name: field for field in existing_fields}
                
                # 同步字段
                created_count = 0
                updated_count = 0
                deleted_count = 0
                
                # 处理新字段和更新字段
                for field_info in table_structure:
                    field_name = field_info['field_name']
                    
                    if field_name in existing_fields_map:
                        # 更新现有字段
                        field = existing_fields_map[field_name]
                        if self._field_has_changed(field, field_info):
                            self._update_field(db, field, field_info)
                            updated_count += 1
                        # 从映射中移除，以便后续删除未使用的字段
                        del existing_fields_map[field_name]
                    else:
                        # 创建新字段
                        self._create_field(db, table_id, field_info)
                        created_count += 1
                
                # 删除不再存在的字段
                for field_name, field in existing_fields_map.items():
                    db.delete(field)
                    deleted_count += 1
                
                # 更新表的最后同步时间
                table.last_sync_time = datetime.now()
                db.commit()
                
                logger.info(f"Table structure sync completed for {table.table_name}: created={created_count}, updated={updated_count}, deleted={deleted_count}")
                return {
                    'created': created_count,
                    'updated': updated_count,
                    'deleted': deleted_count
                }
                
        except OperationalError as e:
            logger.error(f"Database connection failed for table {table.table_name}: {str(e)}")
            raise ConnectionError(f"数据库连接失败: {str(e)}")
        except DatabaseError as e:
            logger.error(f"Database error for table {table.table_name}: {str(e)}")
            raise PermissionError(f"数据库权限不足: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error during table sync for {table.table_name}: {str(e)}")
            raise
    
# 导出实例供其他模块使用
sync_service = TableSyncService()