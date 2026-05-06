"""
表发现服务
实现从数据源数据库中发现表结构和同步表结构的功能
"""
import logging
from typing import List, Dict, Optional, Tuple
from urllib.parse import quote_plus
from sqlalchemy import create_engine, text, inspect, MetaData, Table
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from src.models.data_source_model import DataSource
from src.models.data_preparation_model import DataTable, TableField
from src.services.data_table_service import DataTableService
from src.utils.encryption import decrypt_password
from src.utils.sql_server_odbc import build_sql_server_connection_string
from datetime import datetime

# 创建日志记录器
logger = logging.getLogger(__name__)

class TableDiscoveryService:
    """
    表发现服务类
    提供从数据源数据库中发现表结构和同步表结构的功能
    """
    
    def __init__(self):
        self.data_table_service = DataTableService()

    @staticmethod
    def _normalize_db_type(db_type: str) -> str:
        """Normalize db_type text for tolerant matching."""
        return str(db_type or "").replace("_", "").replace(" ", "").upper()

    def _get_sql_server_table_row_counts(self, engine: Engine) -> Dict[Tuple[str, str], int]:
        """
        获取 SQL Server 各表的估算行数（一次查询）。
        使用 sys.partitions 避免逐表 COUNT(*) 带来的长耗时。
        """
        sql = text(
            """
            SELECT
                s.name AS schema_name,
                t.name AS table_name,
                COALESCE(SUM(CASE WHEN p.index_id IN (0,1) THEN p.rows ELSE 0 END), 0) AS row_count
            FROM sys.tables t
            JOIN sys.schemas s ON s.schema_id = t.schema_id
            LEFT JOIN sys.partitions p ON p.object_id = t.object_id
            GROUP BY s.name, t.name
            """
        )
        mapping: Dict[Tuple[str, str], int] = {}
        with engine.connect() as conn:
            rows = conn.execute(sql).fetchall()
            for row in rows:
                mapping[(row[0], row[1])] = int(row[2] or 0)
        return mapping
    
    def create_connection_string(self, data_source: DataSource) -> str:
        """
        根据数据源配置创建数据库连接字符串
        
        Args:
            data_source: 数据源对象
            
        Returns:
            str: 数据库连接字符串
        """
        logger.info(f"Creating connection string for {data_source.name}: host={data_source.host}, port={data_source.port}, db={data_source.database_name}, user={data_source.username}")
        
        # 解密密码
        password = decrypt_password(data_source.password) if data_source.password else ""
        
        db_type_normalized = self._normalize_db_type(data_source.db_type)

        if db_type_normalized == 'MYSQL':
            return f"mysql+pymysql://{data_source.username}:{password}@{data_source.host}:{data_source.port}/{data_source.database_name}"
        elif db_type_normalized == 'SQLSERVER':
            auth_type_text = str(data_source.auth_type or "").upper()
            domain = data_source.domain if auth_type_text == 'WINDOWS_AUTH' else None
            odbc_conn = build_sql_server_connection_string(
                host=data_source.host,
                port=data_source.port,
                database_name=data_source.database_name,
                username=data_source.username,
                password=password,
                domain=domain,
            )
            return f"mssql+pyodbc:///?odbc_connect={quote_plus(odbc_conn)}"
        elif db_type_normalized == 'POSTGRESQL':
            return f"postgresql://{data_source.username}:{password}@{data_source.host}:{data_source.port}/{data_source.database_name}"
        else:
            raise ValueError(f"不支持的数据库类型: {data_source.db_type}")
    
    def discover_tables(self, data_source: DataSource) -> List[Dict]:
        """
        从数据源中发现所有表
        
        Args:
            data_source: 数据源对象
            
        Returns:
            List[Dict]: 表信息列表，每个元素包含表名、注释等信息
        """
        logger.info(f"Discovering tables from data source: {data_source.name} ({data_source.db_type})")
        
        try:
            # 创建数据库连接
            connection_string = self.create_connection_string(data_source)
            engine = create_engine(connection_string)
            
            # 使用 SQLAlchemy inspect 获取表信息
            inspector = inspect(engine)
            db_type_normalized = self._normalize_db_type(data_source.db_type)

            # SQL Server: 支持多 schema；MySQL/PostgreSQL: 使用默认 schema 逻辑
            discovered: List[Tuple[str, str]] = []
            if db_type_normalized == 'SQLSERVER':
                schema_names = [
                    s for s in inspector.get_schema_names()
                    if s.lower() not in {'sys', 'information_schema'}
                ]
                for schema_name in schema_names:
                    for table_name in inspector.get_table_names(schema=schema_name):
                        discovered.append((schema_name, table_name))
            else:
                for table_name in inspector.get_table_names():
                    discovered.append((data_source.database_name, table_name))

            # SQL Server 使用一次性估算行数；其他库保持原有逐表查询
            sql_server_row_count_map: Dict[Tuple[str, str], int] = {}
            if db_type_normalized == 'SQLSERVER':
                try:
                    sql_server_row_count_map = self._get_sql_server_table_row_counts(engine)
                except Exception as e:
                    logger.warning(f"Failed to prefetch SQL Server row counts: {str(e)}")

            tables = []
            for schema_name, table_name in discovered:
                try:
                    # 获取表注释
                    table_comment = None
                    if db_type_normalized == 'MYSQL':
                        with engine.connect() as conn:
                            result = conn.execute(text(f"""
                                SELECT TABLE_COMMENT 
                                FROM INFORMATION_SCHEMA.TABLES 
                                WHERE TABLE_SCHEMA = '{data_source.database_name}' 
                                AND TABLE_NAME = '{table_name}'
                            """))
                            row = result.fetchone()
                            if row:
                                table_comment = row[0] if row[0] else None
                    
                    # 获取表行数（估算）
                    row_count = 0
                    try:
                        if db_type_normalized == 'SQLSERVER':
                            row_count = sql_server_row_count_map.get((schema_name, table_name), 0)
                        else:
                            with engine.connect() as conn:
                                result = conn.execute(text(f"SELECT COUNT(*) FROM `{table_name}`"))
                                row_count = result.scalar()
                    except Exception as e:
                        logger.warning(f"Failed to get row count for table {table_name}: {str(e)}")
                    
                    tables.append({
                        'table_name': table_name,
                        'comment': table_comment,
                        'row_count': row_count,
                        'schema': schema_name
                    })
                    
                except Exception as e:
                    logger.warning(f"Failed to get details for table {table_name}: {str(e)}")
                    # 仍然添加基本信息
                    tables.append({
                        'table_name': table_name,
                        'comment': None,
                        'row_count': 0,
                        'schema': schema_name
                    })
            
            logger.info(f"Discovered {len(tables)} tables from data source {data_source.name}")
            return tables
            
        except Exception as e:
            logger.error(f"Failed to discover tables from data source {data_source.name}: {str(e)}")
            raise
        finally:
            if 'engine' in locals():
                engine.dispose()
    
    def get_table_structure(self, data_source: DataSource, table_name: str) -> Dict:
        """
        获取指定表的结构信息
        
        Args:
            data_source: 数据源对象
            table_name: 表名
            
        Returns:
            Dict: 表结构信息，包含字段列表
        """
        logger.info(f"Getting table structure for {table_name} from data source {data_source.name}")
        
        try:
            # 创建数据库连接
            connection_string = self.create_connection_string(data_source)
            engine = create_engine(connection_string)
            
            # 使用SQLAlchemy的inspect功能获取表结构
            inspector = inspect(engine)
            columns = inspector.get_columns(table_name)
            primary_keys = inspector.get_pk_constraint(table_name)['constrained_columns']
            
            # 转换字段信息
            fields = []
            for i, column in enumerate(columns):
                field_info = {
                    'name': column['name'],
                    'data_type': str(column['type']),
                    'is_nullable': column['nullable'],
                    'is_primary_key': column['name'] in primary_keys,
                    'default_value': column.get('default'),
                    'comment': column.get('comment'),
                    'sort_order': i + 1
                }
                fields.append(field_info)
            
            # 获取表注释和行数
            table_comment = None
            row_count = 0
            
            if self._normalize_db_type(data_source.db_type) == 'MYSQL':
                with engine.connect() as conn:
                    # 获取表注释
                    result = conn.execute(text(f"""
                        SELECT TABLE_COMMENT 
                        FROM INFORMATION_SCHEMA.TABLES 
                        WHERE TABLE_SCHEMA = '{data_source.database_name}' 
                        AND TABLE_NAME = '{table_name}'
                    """))
                    row = result.fetchone()
                    if row:
                        table_comment = row[0] if row[0] else None
            
            # 获取行数
            try:
                with engine.connect() as conn:
                    if self._normalize_db_type(data_source.db_type) == 'SQLSERVER':
                        result = conn.execute(text(f"SELECT COUNT(*) FROM [{table_name}]"))
                    else:
                        result = conn.execute(text(f"SELECT COUNT(*) FROM `{table_name}`"))
                    row_count = result.scalar()
            except Exception as e:
                logger.warning(f"Failed to get row count for table {table_name}: {str(e)}")
            
            table_structure = {
                'table_name': table_name,
                'comment': table_comment,
                'row_count': row_count,
                'field_count': len(fields),
                'fields': fields
            }
            
            logger.info(f"Retrieved structure for table {table_name}: {len(fields)} fields, {row_count} rows")
            return table_structure
            
        except Exception as e:
            logger.error(f"Failed to get table structure for {table_name}: {str(e)}")
            raise
        finally:
            if 'engine' in locals():
                engine.dispose()
    
    def sync_table_structure(self, db: Session, data_source: DataSource, table_name: str) -> DataTable:
        """
        同步表结构到本地数据库
        
        Args:
            db: 数据库会话
            data_source: 数据源对象
            table_name: 表名
            
        Returns:
            DataTable: 同步后的数据表对象
        """
        logger.info(f"Syncing table structure for {table_name} from data source {data_source.name}")
        
        try:
            # 获取表结构
            table_structure = self.get_table_structure(data_source, table_name)
            
            # 检查表是否已存在
            existing_table = self.data_table_service.get_table_by_name_and_source(
                db, table_name, str(data_source.id)
            )
            
            if existing_table:
                # 更新现有表
                logger.info(f"Updating existing table {table_name}")
                
                # 更新表信息
                existing_table.description = table_structure['comment']
                existing_table.row_count = table_structure['row_count']
                existing_table.field_count = table_structure['field_count']
                existing_table.updated_at = datetime.now()
                existing_table.last_sync_time = datetime.now()
                
                # 更新字段信息
                self.data_table_service.update_table_columns(
                    db, str(existing_table.id), table_structure['fields']
                )
                
                db.commit()
                db.refresh(existing_table)
                
                logger.info(f"Table {table_name} updated successfully")
                return existing_table
            else:
                # 创建新表
                logger.info(f"Creating new table {table_name}")
                
                now = datetime.now()
                new_table = DataTable(
                    data_source_id=str(data_source.id),
                    table_name=table_name,
                    display_name=table_name,
                    description=table_structure['comment'],
                    data_mode='DIRECT_QUERY',
                    row_count=table_structure['row_count'],
                    field_count=table_structure['field_count'],
                    status=True,
                    created_by='system',
                    created_at=now,
                    updated_at=now,
                    last_sync_time=now
                )
                
                db.add(new_table)
                db.flush()  # 获取ID但不提交
                
                # 创建字段信息
                self.data_table_service.create_table_columns(
                    db, str(new_table.id), table_structure['fields']
                )
                
                db.commit()
                db.refresh(new_table)
                
                logger.info(f"Table {table_name} created successfully")
                return new_table
                
        except Exception as e:
            logger.error(f"Failed to sync table structure for {table_name}: {str(e)}")
            db.rollback()
            raise
    
    def batch_sync_tables(self, db: Session, data_source: DataSource, table_names: List[str]) -> List[DataTable]:
        """
        批量同步多个表的结构
        
        Args:
            db: 数据库会话
            data_source: 数据源对象
            table_names: 表名列表
            
        Returns:
            List[DataTable]: 同步后的数据表对象列表
        """
        logger.info(f"Batch syncing {len(table_names)} tables from data source {data_source.name}")
        
        synced_tables = []
        failed_tables = []
        
        for table_name in table_names:
            try:
                synced_table = self.sync_table_structure(db, data_source, table_name)
                synced_tables.append(synced_table)
                logger.info(f"Successfully synced table: {table_name}")
            except Exception as e:
                logger.error(f"Failed to sync table {table_name}: {str(e)}")
                failed_tables.append(table_name)
        
        logger.info(f"Batch sync completed: {len(synced_tables)} succeeded, {len(failed_tables)} failed")
        
        if failed_tables:
            logger.warning(f"Failed tables: {', '.join(failed_tables)}")
        
        return synced_tables
    
    def test_connection(self, data_source: DataSource) -> Tuple[bool, str]:
        """
        测试数据源连接
        
        Args:
            data_source: 数据源对象
            
        Returns:
            Tuple[bool, str]: (连接是否成功, 消息)
        """
        logger.info(f"Testing connection to data source: {data_source.name}")
        
        try:
            connection_string = self.create_connection_string(data_source)
            engine = create_engine(connection_string)
            
            # 尝试连接并执行简单查询
            with engine.connect() as conn:
                result = conn.execute(text("SELECT 1"))
                result.fetchone()
            
            logger.info(f"Connection test successful for data source: {data_source.name}")
            return True, "连接成功"
            
        except Exception as e:
            error_msg = f"连接失败: {str(e)}"
            logger.error(f"Connection test failed for data source {data_source.name}: {error_msg}")
            return False, error_msg
        finally:
            if 'engine' in locals():
                engine.dispose()