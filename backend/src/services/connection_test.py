import time
import logging
from typing import Dict, Optional
from pydantic import BaseModel
from enum import Enum

# 导入数据库类型枚举
from src.schemas.data_source_schema import DatabaseType
from src.utils.sql_server_odbc import build_sql_server_connection_string

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ConnectionResult(BaseModel):
    """连接测试结果模型"""
    success: bool
    message: str
    latency_ms: Optional[int] = None


class ConnectionTestService:
    """数据源连接测试服务"""
    
    @staticmethod
    def test_mysql_connection(host: str, port: int, database_name: str, username: str, password: str) -> ConnectionResult:
        """测试MySQL连接"""
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
                connection_timeout=10,  # 10秒超时
                autocommit=True
            )
            
            # 验证连接
            if connection.is_connected():
                latency_ms = int((time.time() - start_time) * 1000)
                connection.close()
                return ConnectionResult(
                    success=True,
                    message="MySQL连接成功",
                    latency_ms=latency_ms
                )
            else:
                return ConnectionResult(
                    success=False,
                    message="MySQL连接失败：无法建立连接"
                )
                
        except mysql.connector.Error as e:
            error_msg = str(e)
            if "Access denied" in error_msg or "Unknown user" in error_msg:
                return ConnectionResult(
                    success=False,
                    message="MySQL认证失败：用户名或密码错误"
                )
            elif "Can't connect to MySQL server" in error_msg:
                return ConnectionResult(
                    success=False,
                    message="MySQL连接失败：主机不可达或端口错误"
                )
            elif "Unknown database" in error_msg:
                return ConnectionResult(
                    success=False,
                    message="MySQL连接失败：数据库不存在"
                )
            elif "Timeout" in error_msg or "Lost connection" in error_msg:
                return ConnectionResult(
                    success=False,
                    message="MySQL连接超时：请检查网络连接或增加超时时间"
                )
            else:
                return ConnectionResult(
                    success=False,
                    message=f"MySQL连接失败：{error_msg}"
                )
        except Exception as e:
            logger.error(f"MySQL连接测试异常: {str(e)}")
            # 捕获所有其他异常，返回具体的错误信息
            error_msg = str(e)
            if "Unknown MySQL server host" in error_msg:
                return ConnectionResult(
                    success=False,
                    message="MySQL连接失败：主机不可达或端口错误"
                )
            elif "Unknown database" in error_msg:
                return ConnectionResult(
                    success=False,
                    message="MySQL连接失败：数据库不存在"
                )
            elif "Access denied" in error_msg:
                return ConnectionResult(
                    success=False,
                    message="MySQL认证失败：用户名或密码错误"
                )
            elif "Timeout" in error_msg:
                return ConnectionResult(
                    success=False,
                    message="MySQL连接超时：请检查网络连接或增加超时时间"
                )
            else:
                return ConnectionResult(
                    success=False,
                    message=f"MySQL连接失败：{error_msg}"
                )
    
    @staticmethod
    def test_sql_server_connection(host: str, port: int, database_name: str, username: str, password: str, domain: str = None) -> ConnectionResult:
        """测试SQL Server连接"""
        try:
            import pyodbc  # type: ignore
        except ModuleNotFoundError:
            return ConnectionResult(
                success=False,
                message="SQL Server连接失败：缺少 pyodbc 依赖，请先安装 pyodbc 与 SQL Server ODBC 驱动"
            )

        try:
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
            
            # 验证连接
            if connection:
                latency_ms = int((time.time() - start_time) * 1000)
                connection.close()
                return ConnectionResult(
                    success=True,
                    message="SQL Server连接成功",
                    latency_ms=latency_ms
                )
            else:
                return ConnectionResult(
                    success=False,
                    message="SQL Server连接失败：无法建立连接"
                )
                
        except pyodbc.Error as e:
            error_msg = str(e)
            error_msg_lower = error_msg.lower()
            if "Login failed" in error_msg or "Invalid user" in error_msg:
                return ConnectionResult(
                    success=False,
                    message="SQL Server认证失败：用户名或密码错误"
                )
            elif "SSL Provider" in error_msg or "certificate verify failed" in error_msg or "self signed certificate" in error_msg:
                return ConnectionResult(
                    success=False,
                    message="SQL Server SSL 握手失败：请检查证书链，或按需设置 ODBC_TRUST_SERVER_CERTIFICATE=yes"
                )
            elif "hostname" in error_msg.lower() and "certificate" in error_msg.lower():
                return ConnectionResult(
                    success=False,
                    message="SQL Server SSL 主机名校验失败：请检查服务器证书 CN/SAN，或设置 ODBC_HOSTNAME_IN_CERTIFICATE"
                )
            elif (
                "can't open lib" in error_msg_lower
                or "data source name not found" in error_msg_lower
                or "file not found" in error_msg_lower
                or "driver manager" in error_msg_lower
            ):
                return ConnectionResult(
                    success=False,
                    message="SQL Server连接失败：未安装可用的 SQL Server ODBC 驱动（如 ODBC Driver 17/18）"
                )
            elif "Could not open a connection to SQL Server" in error_msg:
                return ConnectionResult(
                    success=False,
                    message="SQL Server连接失败：主机不可达或端口错误"
                )
            elif "Database does not exist" in error_msg:
                return ConnectionResult(
                    success=False,
                    message="SQL Server连接失败：数据库不存在"
                )
            elif "Timeout" in error_msg or "Connection timeout" in error_msg:
                return ConnectionResult(
                    success=False,
                    message="SQL Server连接超时：请检查网络连接或增加超时时间"
                )
            else:
                return ConnectionResult(
                    success=False,
                    message=f"SQL Server连接失败：{error_msg}"
                )
        except Exception as e:
            logger.error(f"SQL Server连接测试异常: {str(e)}")
            # 捕获所有其他异常，返回具体的错误信息
            error_msg = str(e)
            if "Login failed" in error_msg or "Invalid user" in error_msg:
                return ConnectionResult(
                    success=False,
                    message="SQL Server认证失败：用户名或密码错误"
                )
            elif "Could not open a connection to SQL Server" in error_msg:
                return ConnectionResult(
                    success=False,
                    message="SQL Server连接失败：主机不可达或端口错误"
                )
            elif "Database does not exist" in error_msg:
                return ConnectionResult(
                    success=False,
                    message="SQL Server连接失败：数据库不存在"
                )
            elif "Timeout" in error_msg or "Connection timeout" in error_msg:
                return ConnectionResult(
                    success=False,
                    message="SQL Server连接超时：请检查网络连接或增加超时时间"
                )
            else:
                return ConnectionResult(
                    success=False,
                    message=f"SQL Server连接失败：{error_msg}"
                )
    
    @staticmethod
    def test_postgresql_connection(host: str, port: int, database_name: str, username: str, password: str) -> ConnectionResult:
        """测试PostgreSQL连接"""
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
                connect_timeout=10  # 10秒超时
            )
            
            # 验证连接
            if connection:
                latency_ms = int((time.time() - start_time) * 1000)
                connection.close()
                return ConnectionResult(
                    success=True,
                    message="PostgreSQL连接成功",
                    latency_ms=latency_ms
                )
            else:
                return ConnectionResult(
                    success=False,
                    message="PostgreSQL连接失败：无法建立连接"
                )
                
        except psycopg2.OperationalError as e:
            error_msg = str(e)
            if "password authentication failed" in error_msg.lower() or "invalid username" in error_msg.lower():
                return ConnectionResult(
                    success=False,
                    message="PostgreSQL认证失败：用户名或密码错误"
                )
            elif "could not translate host name" in error_msg.lower() or "connection refused" in error_msg.lower():
                return ConnectionResult(
                    success=False,
                    message="PostgreSQL连接失败：主机不可达或端口错误"
                )
            elif "database \"" in error_msg.lower() and "does not exist" in error_msg.lower():
                return ConnectionResult(
                    success=False,
                    message="PostgreSQL连接失败：数据库不存在"
                )
            elif "timeout" in error_msg.lower():
                return ConnectionResult(
                    success=False,
                    message="PostgreSQL连接超时：请检查网络连接或增加超时时间"
                )
            else:
                return ConnectionResult(
                    success=False,
                    message=f"PostgreSQL连接失败：{error_msg}"
                )
        except Exception as e:
            logger.error(f"PostgreSQL连接测试异常: {str(e)}")
            # 捕获所有其他异常，返回具体的错误信息
            error_msg = str(e)
            if "password authentication failed" in error_msg.lower() or "invalid username" in error_msg.lower():
                return ConnectionResult(
                    success=False,
                    message="PostgreSQL认证失败：用户名或密码错误"
                )
            elif "could not translate host name" in error_msg.lower() or "connection refused" in error_msg.lower():
                return ConnectionResult(
                    success=False,
                    message="PostgreSQL连接失败：主机不可达或端口错误"
                )
            elif "database \"" in error_msg.lower() and "does not exist" in error_msg.lower():
                return ConnectionResult(
                    success=False,
                    message="PostgreSQL连接失败：数据库不存在"
                )
            elif "timeout" in error_msg.lower():
                return ConnectionResult(
                    success=False,
                    message="PostgreSQL连接超时：请检查网络连接或增加超时时间"
                )
            else:
                return ConnectionResult(
                    success=False,
                    message=f"PostgreSQL连接失败：{error_msg}"
                )
    
    @staticmethod
    def test_clickhouse_connection(host: str, port: int, database_name: str, username: str, password: str) -> ConnectionResult:
        """测试ClickHouse连接"""
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
                connect_timeout=10,  # 10秒超时
                send_receive_timeout=10  # 10秒发送/接收超时
            )
            
            # 执行简单查询验证连接
            result = client.execute("SELECT 1")
            
            if result and result[0][0] == 1:
                latency_ms = int((time.time() - start_time) * 1000)
                client.disconnect()
                return ConnectionResult(
                    success=True,
                    message="ClickHouse连接成功",
                    latency_ms=latency_ms
                )
            else:
                return ConnectionResult(
                    success=False,
                    message="ClickHouse连接失败：无法执行测试查询"
                )
                
        except Exception as e:
            error_msg = str(e)
            if "Authentication failed" in error_msg or "User not found" in error_msg:
                return ConnectionResult(
                    success=False,
                    message="ClickHouse认证失败：用户名或密码错误"
                )
            elif "Connection refused" in error_msg or "Host not found" in error_msg:
                return ConnectionResult(
                    success=False,
                    message="ClickHouse连接失败：主机不可达或端口错误"
                )
            elif "Database does not exist" in error_msg:
                return ConnectionResult(
                    success=False,
                    message="ClickHouse连接失败：数据库不存在"
                )
            elif "Timeout" in error_msg or "Connection timeout" in error_msg:
                return ConnectionResult(
                    success=False,
                    message="ClickHouse连接超时：请检查网络连接或增加超时时间"
                )
            else:
                return ConnectionResult(
                    success=False,
                    message=f"ClickHouse连接失败：{error_msg}"
                )
        except Exception as e:
            logger.error(f"ClickHouse连接测试异常: {str(e)}")
            # 捕获所有其他异常，返回具体的错误信息
            error_msg = str(e)
            if "Authentication failed" in error_msg or "User not found" in error_msg:
                return ConnectionResult(
                    success=False,
                    message="ClickHouse认证失败：用户名或密码错误"
                )
            elif "Connection refused" in error_msg or "Host not found" in error_msg:
                return ConnectionResult(
                    success=False,
                    message="ClickHouse连接失败：主机不可达或端口错误"
                )
            elif "Database does not exist" in error_msg:
                return ConnectionResult(
                    success=False,
                    message="ClickHouse连接失败：数据库不存在"
                )
            elif "Timeout" in error_msg or "Connection timeout" in error_msg:
                return ConnectionResult(
                    success=False,
                    message="ClickHouse连接超时：请检查网络连接或增加超时时间"
                )
            else:
                return ConnectionResult(
                    success=False,
                    message=f"ClickHouse连接失败：{error_msg}"
                )
    
    @staticmethod
    def test_connection(data_source: dict) -> ConnectionResult:
        """根据数据源类型测试连接 - ChatBI只支持MySQL和SQL Server"""
        data_source = dict(data_source)
        db_type = data_source.get('db_type')
        if db_type == DatabaseType.MYSQL:
            from src.utils.mysql_datasource_docker_remap import remap_mysql_datasource_host

            data_source = remap_mysql_datasource_host(data_source)
        host = data_source.get('host')
        port = data_source.get('port')
        database_name = data_source.get('database_name')
        username = data_source.get('username')
        password = data_source.get('password')
        domain = data_source.get('domain')
        
        # 验证必要参数
        if not host:
            return ConnectionResult(success=False, message="主机地址不能为空")
        if not port:
            return ConnectionResult(success=False, message="端口号不能为空")
        if not database_name:
            return ConnectionResult(success=False, message="数据库名称不能为空")
        
        # 对于SQL Server Windows认证，username可以为空（使用当前Windows用户）
        # 对于其他情况，username必须提供
        if not username and not (db_type == DatabaseType.SQL_SERVER and domain):
            return ConnectionResult(success=False, message="用户名不能为空")
        
        # 对于Windows认证，密码可以为空
        if not password and not (db_type == DatabaseType.SQL_SERVER and domain):
            return ConnectionResult(success=False, message="密码不能为空")
        
        # 根据数据库类型调用相应测试方法 - ChatBI只支持MySQL和SQL Server
        if db_type == DatabaseType.MYSQL:
            return ConnectionTestService.test_mysql_connection(host, port, database_name, username, password)
        elif db_type == DatabaseType.SQL_SERVER:
            return ConnectionTestService.test_sql_server_connection(host, port, database_name, username, password, domain)
        else:
            return ConnectionResult(success=False, message="ChatBI只支持MySQL和SQL Server数据库")

# 为测试准备的辅助函数
# 这些函数在生产环境中不会被使用，仅用于测试

def create_test_data_source(db_type: str, host: str, port: int, database_name: str, username: str, password: str, domain: str = None) -> dict:
    """创建测试用的数据源配置"""
    return {
        "name": "test_connection",
        "source_type": "DATABASE",
        "db_type": db_type,
        "host": host,
        "port": port,
        "database_name": database_name,
        "username": username,
        "password": password,
        "domain": domain
    }
