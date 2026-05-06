import logging
import time
from typing import List, Dict, Optional
from pydantic import BaseModel

# 导入数据库类型枚举
from src.schemas.data_source_schema import DatabaseType
from src.utils.sql_server_odbc import build_sql_server_connection_string

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TableInfo(BaseModel):
    """表信息模型"""
    name: str
    type: str
    comment: Optional[str] = None

class TableDiscoveryResult(BaseModel):
    """表发现结果模型"""
    tables: List[TableInfo]
    success: bool
    error_message: Optional[str] = None

class TableDiscoveryService:
    """表发现服务，用于查询指定数据源的所有表列表"""
    
    @staticmethod
    def discover_mysql_tables(host: str, port: int, database_name: str, username: str, password: str) -> TableDiscoveryResult:
        """查询MySQL数据库的所有表"""
        try:
            import mysql.connector
            from mysql.connector import Error
            
            start_time = time.time()
            
            # 创建连接
            connection = mysql.connector.connect(
                host=host,
                port=port,
                database=database_name,
                user=username,
                password=password,
                connection_timeout=10,
                autocommit=True
            )
            
            if not connection.is_connected():
                return TableDiscoveryResult(
                    tables=[],
                    success=False,
                    error_message="MySQL连接失败：无法建立连接"
                )
            
            cursor = connection.cursor()
            
            # 查询所有表信息
            cursor.execute("""
                SELECT 
                    TABLE_NAME as table_name,
                    TABLE_TYPE as table_type,
                    TABLE_COMMENT as table_comment
                FROM information_schema.TABLES 
                WHERE TABLE_SCHEMA = %s
                ORDER BY TABLE_NAME
            """, (database_name,))
            
            tables = []
            for row in cursor.fetchall():
                table_name, table_type, table_comment = row
                tables.append(TableInfo(
                    name=table_name,
                    type=table_type if table_type else "TABLE",
                    comment=table_comment if table_comment else None
                ))
            
            cursor.close()
            connection.close()
            
            logger.info(f"Successfully discovered {len(tables)} tables from MySQL database {database_name}")
            return TableDiscoveryResult(
                tables=tables,
                success=True,
                error_message=None
            )
            
        except mysql.connector.Error as e:
            error_msg = str(e)
            if "Access denied" in error_msg or "Unknown user" in error_msg:
                error_message = "MySQL认证失败：用户名或密码错误"
            elif "Can't connect to MySQL server" in error_msg:
                error_message = "MySQL连接失败：主机不可达或端口错误"
            elif "Unknown database" in error_msg:
                error_message = "MySQL连接失败：数据库不存在"
            elif "Timeout" in error_msg or "Lost connection" in error_msg:
                error_message = "MySQL连接超时：请检查网络连接或增加超时时间"
            else:
                error_message = f"MySQL查询表列表失败：{error_msg}"
            
            logger.error(f"MySQL table discovery failed: {error_message}")
            return TableDiscoveryResult(
                tables=[],
                success=False,
                error_message=error_message
            )
        except Exception as e:
            error_msg = str(e)
            if "Unknown MySQL server host" in error_msg:
                error_message = "MySQL连接失败：主机不可达或端口错误"
            elif "Unknown database" in error_msg:
                error_message = "MySQL连接失败：数据库不存在"
            elif "Access denied" in error_msg:
                error_message = "MySQL认证失败：用户名或密码错误"
            elif "Timeout" in error_msg:
                error_message = "MySQL连接超时：请检查网络连接或增加超时时间"
            else:
                error_message = f"MySQL查询表列表失败：{error_msg}"
            
            logger.error(f"MySQL table discovery exception: {error_message}")
            return TableDiscoveryResult(
                tables=[],
                success=False,
                error_message=error_message
            )
    
    @staticmethod
    def discover_sql_server_tables(host: str, port: int, database_name: str, username: str, password: str, domain: str = None) -> TableDiscoveryResult:
        """查询SQL Server数据库的所有表"""
        try:
            import pyodbc
            
            start_time = time.time()
            
            # 构建连接字符串（支持可配置 SSL/TLS 参数）
            connection_string = build_sql_server_connection_string(
                host=host,
                port=port,
                database_name=database_name,
                username=username,
                password=password,
                domain=domain,
            )
            
            # 创建连接
            connection = pyodbc.connect(connection_string, timeout=10)
            
            cursor = connection.cursor()
            
            # 查询所有表信息
            cursor.execute("""
                SELECT 
                    t.name as table_name,
                    CASE t.type 
                        WHEN 'U' THEN 'TABLE'
                        WHEN 'V' THEN 'VIEW'
                        ELSE t.type
                    END as table_type,
                    ep.value as table_comment
                FROM sys.tables t
                LEFT JOIN sys.extended_properties ep ON t.object_id = ep.major_id 
                    AND ep.minor_id = 0 
                    AND ep.name = 'MS_Description'
                ORDER BY t.name
            """)
            
            tables = []
            for row in cursor.fetchall():
                table_name, table_type, table_comment = row
                tables.append(TableInfo(
                    name=table_name,
                    type=table_type if table_type else "TABLE",
                    comment=table_comment if table_comment else None
                ))
            
            cursor.close()
            connection.close()
            
            logger.info(f"Successfully discovered {len(tables)} tables from SQL Server database {database_name}")
            return TableDiscoveryResult(
                tables=tables,
                success=True,
                error_message=None
            )
            
        except pyodbc.Error as e:
            error_msg = str(e)
            if "Login failed" in error_msg or "Invalid user" in error_msg:
                error_message = "SQL Server认证失败：用户名或密码错误"
            elif "Could not open a connection to SQL Server" in error_msg:
                error_message = "SQL Server连接失败：主机不可达或端口错误"
            elif "Database does not exist" in error_msg:
                error_message = "SQL Server连接失败：数据库不存在"
            elif "Timeout" in error_msg or "Connection timeout" in error_msg:
                error_message = "SQL Server连接超时：请检查网络连接或增加超时时间"
            else:
                error_message = f"SQL Server查询表列表失败：{error_msg}"
            
            logger.error(f"SQL Server table discovery failed: {error_message}")
            return TableDiscoveryResult(
                tables=[],
                success=False,
                error_message=error_message
            )
        except Exception as e:
            error_msg = str(e)
            if "Login failed" in error_msg or "Invalid user" in error_msg:
                error_message = "SQL Server认证失败：用户名或密码错误"
            elif "Could not open a connection to SQL Server" in error_msg:
                error_message = "SQL Server连接失败：主机不可达或端口错误"
            elif "Database does not exist" in error_msg:
                error_message = "SQL Server连接失败：数据库不存在"
            elif "Timeout" in error_msg or "Connection timeout" in error_msg:
                error_message = "SQL Server连接超时：请检查网络连接或增加超时时间"
            else:
                error_message = f"SQL Server查询表列表失败：{error_msg}"
            
            logger.error(f"SQL Server table discovery exception: {error_message}")
            return TableDiscoveryResult(
                tables=[],
                success=False,
                error_message=error_message
            )
    
    @staticmethod
    def discover_postgresql_tables(host: str, port: int, database_name: str, username: str, password: str) -> TableDiscoveryResult:
        """查询PostgreSQL数据库的所有表"""
        try:
            import psycopg2
            
            start_time = time.time()
            
            # 创建连接
            connection = psycopg2.connect(
                host=host,
                port=port,
                database=database_name,
                user=username,
                password=password,
                connect_timeout=10
            )
            
            cursor = connection.cursor()
            
            # 查询所有表信息
            cursor.execute("""
                SELECT 
                    t.table_name as table_name,
                    t.table_type as table_type,
                    pgd.description as table_comment
                FROM information_schema.tables t
                LEFT JOIN pg_catalog.pg_statio_user_tables st ON t.table_name = st.relname
                LEFT JOIN pg_catalog.pg_description pgd ON st.relid = pgd.objoid AND pgd.objsubid = 0
                WHERE t.table_schema = 'public'
                ORDER BY t.table_name
            """)
            
            tables = []
            for row in cursor.fetchall():
                table_name, table_type, table_comment = row
                # 映射PostgreSQL表类型到标准类型
                if table_type in ["BASE TABLE", "FOREIGN TABLE"]:
                    table_type = "TABLE"
                elif table_type in ["VIEW", "MATERIALIZED VIEW"]:
                    table_type = "VIEW"
                tables.append(TableInfo(
                    name=table_name,
                    type=table_type if table_type else "TABLE",
                    comment=table_comment if table_comment else None
                ))
            
            cursor.close()
            connection.close()
            
            logger.info(f"Successfully discovered {len(tables)} tables from PostgreSQL database {database_name}")
            return TableDiscoveryResult(
                tables=tables,
                success=True,
                error_message=None
            )
            
        except psycopg2.OperationalError as e:
            error_msg = str(e)
            if "password authentication failed" in error_msg.lower() or "invalid username" in error_msg.lower():
                error_message = "PostgreSQL认证失败：用户名或密码错误"
            elif "could not translate host name" in error_msg.lower() or "connection refused" in error_msg.lower():
                error_message = "PostgreSQL连接失败：主机不可达或端口错误"
            elif "database \"" in error_msg.lower() and "does not exist" in error_msg.lower():
                error_message = "PostgreSQL连接失败：数据库不存在"
            elif "timeout" in error_msg.lower():
                error_message = "PostgreSQL连接超时：请检查网络连接或增加超时时间"
            else:
                error_message = f"PostgreSQL查询表列表失败：{error_msg}"
            
            logger.error(f"PostgreSQL table discovery failed: {error_message}")
            return TableDiscoveryResult(
                tables=[],
                success=False,
                error_message=error_message
            )
        except Exception as e:
            error_msg = str(e)
            if "password authentication failed" in error_msg.lower() or "invalid username" in error_msg.lower():
                error_message = "PostgreSQL认证失败：用户名或密码错误"
            elif "could not translate host name" in error_msg.lower() or "connection refused" in error_msg.lower():
                error_message = "PostgreSQL连接失败：主机不可达或端口错误"
            elif "database \"" in error_msg.lower() and "does not exist" in error_msg.lower():
                error_message = "PostgreSQL连接失败：数据库不存在"
            elif "timeout" in error_msg.lower():
                error_message = "PostgreSQL连接超时：请检查网络连接或增加超时时间"
            else:
                error_message = f"PostgreSQL查询表列表失败：{error_msg}"
            
            logger.error(f"PostgreSQL table discovery exception: {error_message}")
            return TableDiscoveryResult(
                tables=[],
                success=False,
                error_message=error_message
            )
    
    @staticmethod
    def discover_clickhouse_tables(host: str, port: int, database_name: str, username: str, password: str) -> TableDiscoveryResult:
        """查询ClickHouse数据库的所有表"""
        try:
            from clickhouse_driver import Client
            
            start_time = time.time()
            
            # 创建连接
            client = Client(
                host=host,
                port=port,
                database=database_name,
                user=username,
                password=password,
                connect_timeout=10,
                send_receive_timeout=10
            )
            
            # 查询所有表信息
            result = client.execute("""
                SELECT 
                    name as table_name,
                    engine as table_type,
                    comment as table_comment
                FROM system.tables 
                WHERE database = %s
                ORDER BY name
            """, (database_name,))
            
            tables = []
            for row in result:
                table_name, table_type, table_comment = row
                # 映射ClickHouse引擎类型到标准类型
                if table_type in ["MergeTree", "ReplacingMergeTree", "SummingMergeTree", "AggregatingMergeTree", "CollapsingMergeTree", "VersionedCollapsingMergeTree", "GraphiteMergeTree", "Log", "TinyLog", "StripeLog"]:
                    table_type = "TABLE"
                elif table_type in ["View", "MaterializedView", "LiveView"]:
                    table_type = "VIEW"
                tables.append(TableInfo(
                    name=table_name,
                    type=table_type if table_type else "TABLE",
                    comment=table_comment if table_comment else None
                ))
            
            client.disconnect()
            
            logger.info(f"Successfully discovered {len(tables)} tables from ClickHouse database {database_name}")
            return TableDiscoveryResult(
                tables=tables,
                success=True,
                error_message=None
            )
            
        except Exception as e:
            error_msg = str(e)
            if "Authentication failed" in error_msg or "User not found" in error_msg:
                error_message = "ClickHouse认证失败：用户名或密码错误"
            elif "Connection refused" in error_msg or "Host not found" in error_msg:
                error_message = "ClickHouse连接失败：主机不可达或端口错误"
            elif "Database does not exist" in error_msg:
                error_message = "ClickHouse连接失败：数据库不存在"
            elif "Timeout" in error_msg or "Connection timeout" in error_msg:
                error_message = "ClickHouse连接超时：请检查网络连接或增加超时时间"
            else:
                error_message = f"ClickHouse查询表列表失败：{error_msg}"
            
            logger.error(f"ClickHouse table discovery failed: {error_message}")
            return TableDiscoveryResult(
                tables=[],
                success=False,
                error_message=error_message
            )
        except Exception as e:
            error_msg = str(e)
            if "Authentication failed" in error_msg or "User not found" in error_msg:
                error_message = "ClickHouse认证失败：用户名或密码错误"
            elif "Connection refused" in error_msg or "Host not found" in error_msg:
                error_message = "ClickHouse连接失败：主机不可达或端口错误"
            elif "Database does not exist" in error_msg:
                error_message = "ClickHouse连接失败：数据库不存在"
            elif "Timeout" in error_msg or "Connection timeout" in error_msg:
                error_message = "ClickHouse连接超时：请检查网络连接或增加超时时间"
            else:
                error_message = f"ClickHouse查询表列表失败：{error_msg}"
            
            logger.error(f"ClickHouse table discovery exception: {error_message}")
            return TableDiscoveryResult(
                tables=[],
                success=False,
                error_message=error_message
            )
    
    @staticmethod
    def discover_tables_by_data_source(data_source: dict) -> TableDiscoveryResult:
        """根据数据源配置查询表列表"""
        db_type = data_source.get('db_type')
        host = data_source.get('host')
        port = data_source.get('port')
        database_name = data_source.get('database_name')
        username = data_source.get('username')
        password = data_source.get('password')
        domain = data_source.get('domain')
        
        # 验证必要参数
        if not host:
            return TableDiscoveryResult(
                tables=[],
                success=False,
                error_message="主机地址不能为空"
            )
        if not port:
            return TableDiscoveryResult(
                tables=[],
                success=False,
                error_message="端口号不能为空"
            )
        if not database_name:
            return TableDiscoveryResult(
                tables=[],
                success=False,
                error_message="数据库名称不能为空"
            )
        
        # 对于SQL Server Windows认证，username可以为空（使用当前Windows用户）
        # 对于其他情况，username必须提供
        if not username and not (db_type == 'SQL_SERVER' and domain):
            return TableDiscoveryResult(
                tables=[],
                success=False,
                error_message="用户名不能为空"
            )
        
        # 对于Windows认证，密码可以为空；对于ClickHouse默认连接，密码也可以为空
        # 只有在不是Windows认证且不是ClickHouse时才需要检查密码
        if not password and not (db_type == 'SQL_SERVER' and domain) and not (db_type == 'CLICKHOUSE' and username == "default" and password == ""):
            return TableDiscoveryResult(
                tables=[],
                success=False,
                error_message="密码不能为空"
            )
        
        # 根据数据库类型调用相应发现方法
        if db_type == 'MYSQL':
            return TableDiscoveryService.discover_mysql_tables(host, port, database_name, username, password)
        elif db_type == 'SQL_SERVER':
            return TableDiscoveryService.discover_sql_server_tables(host, port, database_name, username, password, domain)
        elif db_type == 'POSTGRESQL':
            return TableDiscoveryService.discover_postgresql_tables(host, port, database_name, username, password)
        elif db_type == 'CLICKHOUSE':
            return TableDiscoveryService.discover_clickhouse_tables(host, port, database_name, username, password)
        else:
            return TableDiscoveryResult(
                tables=[],
                success=False,
                error_message="不支持的数据库类型"
            )