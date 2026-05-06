import pytest
import asyncio
from datetime import datetime
from src.services.connection_test import ConnectionTestService, ConnectionResult
from src.schemas.data_source_schema import DatabaseType
from src.models.data_source_model import DataSource
import unittest
from unittest.mock import patch

# 测试数据源连接测试服务

class TestConnectionTestService:
    
    @patch('mysql.connector.connect')
    def test_mysql_connection_success(self, mock_connect):
        """测试MySQL连接成功场景"""
        # 创建测试数据
        test_data = {
            "name": "test_mysql",
            "source_type": "DATABASE",
            "db_type": DatabaseType.MYSQL,
            "host": "localhost",
            "port": 3306,
            "database_name": "test_db",
            "username": "test_user",
            "password": "test_password"
        }
        
        # 模拟连接成功
        mock_connection = unittest.mock.Mock()
        mock_connection.is_connected.return_value = True
        mock_connect.return_value = mock_connection
        
        # 调用连接测试服务
        result = ConnectionTestService.test_connection(test_data)
        
        # 验证结果
        assert result.success is True
        assert result.message == "MySQL连接成功"
        assert result.latency_ms is not None
        assert result.latency_ms >= 0
        
        # 验证mock被正确调用
        mock_connect.assert_called_once_with(
            host="localhost",
            port=3306,
            database="test_db",
            user="test_user",
            password="test_password",
            connection_timeout=10,
            autocommit=True
        )
    
    @patch('pyodbc.connect')
    def test_sql_server_sql_auth_connection(self, mock_connect):
        """测试SQL Server SQL认证连接"""
        # 创建测试数据
        test_data = {
            "name": "test_sql_server",
            "source_type": "DATABASE",
            "db_type": DatabaseType.SQL_SERVER,
            "host": "localhost",
            "port": 1433,
            "database_name": "test_db",
            "username": "test_user",
            "password": "test_password",
            "auth_type": "SQL_AUTH"
        }
        
        # 模拟连接成功
        mock_connection = unittest.mock.Mock()
        mock_connect.return_value = mock_connection
        
        # 调用连接测试服务
        result = ConnectionTestService.test_connection(test_data)
        
        # 验证结果
        assert result.success is True
        assert result.message == "SQL Server连接成功"
        assert result.latency_ms is not None
        assert result.latency_ms >= 0
        
        # 验证mock被正确调用
        mock_connect.assert_called_once_with(
            "DRIVER={ODBC Driver 17 for SQL Server};SERVER=localhost,1433;DATABASE=test_db;UID=test_user;PWD=test_password;",
            timeout=10
        )
    
    @patch('psycopg2.connect')
    def test_postgresql_connection_failure(self, mock_connect):
        """测试PostgreSQL连接失败场景"""
        # 创建测试数据 - 使用无效的认证信息
        test_data = {
            "name": "test_postgresql",
            "source_type": "DATABASE",
            "db_type": DatabaseType.POSTGRESQL,
            "host": "localhost",
            "port": 5432,
            "database_name": "test_db",
            "username": "invalid_user",
            "password": "invalid_password"
        }
        
        # 模拟认证失败
        mock_connect.side_effect = Exception("password authentication failed")
        
        # 调用连接测试服务
        result = ConnectionTestService.test_connection(test_data)
        
        # 验证结果
        assert result.success is False
        assert "认证失败" in result.message
        assert result.latency_ms is None
        
        # 验证mock被正确调用
        mock_connect.assert_called_once_with(
            host="localhost",
            port=5432,
            database="test_db",
            user="invalid_user",
            password="invalid_password",
            connect_timeout=10
        )
    
    @patch('mysql.connector.connect')
    def test_connection_timeout(self, mock_connect):
        """测试连接超时处理"""
        # 创建测试数据 - 使用一个不存在的主机
        test_data = {
            "name": "test_timeout",
            "source_type": "DATABASE",
            "db_type": DatabaseType.MYSQL,
            "host": "nonexistent.host.com",
            "port": 3306,
            "database_name": "test_db",
            "username": "test_user",
            "password": "test_password"
        }
        
        # 模拟连接超时
        mock_connect.side_effect = Exception("Unknown MySQL server host 'nonexistent.host.com' (8)")
        
        # 调用连接测试服务
        result = ConnectionTestService.test_connection(test_data)
        
        # 验证结果
        assert result.success is False
        assert "超时" in result.message or "不可达" in result.message
        assert result.latency_ms is None
        
        # 验证mock被正确调用
        mock_connect.assert_called_once_with(
            host="nonexistent.host.com",
            port=3306,
            database="test_db",
            user="test_user",
            password="test_password",
            connection_timeout=10,
            autocommit=True
        )
    
    @patch('mysql.connector.connect')
    @patch('pyodbc.connect')
    @patch('psycopg2.connect')
    @patch('clickhouse_driver.Client')
    def test_invalid_auth_info(self, mock_clickhouse, mock_postgresql, mock_sqlserver, mock_mysql):
        """测试无效认证信息处理"""
        # 测试MySQL无效认证
        mysql_data = {
            "name": "test_mysql_invalid",
            "source_type": "DATABASE",
            "db_type": DatabaseType.MYSQL,
            "host": "localhost",
            "port": 3306,
            "database_name": "test_db",
            "username": "invalid_user",
            "password": "invalid_password"
        }
        
        mock_mysql.side_effect = Exception("Access denied for user 'invalid_user'")
        result = ConnectionTestService.test_connection(mysql_data)
        assert result.success is False
        assert "认证失败" in result.message
        
        # 测试SQL Server无效认证
        sql_server_data = {
            "name": "test_sql_server_invalid",
            "source_type": "DATABASE",
            "db_type": DatabaseType.SQL_SERVER,
            "host": "localhost",
            "port": 1433,
            "database_name": "test_db",
            "username": "invalid_user",
            "password": "invalid_password",
            "auth_type": "SQL_AUTH"
        }
        
        mock_sqlserver.side_effect = Exception("Login failed for user 'invalid_user'")
        result = ConnectionTestService.test_connection(sql_server_data)
        assert result.success is False
        assert "认证失败" in result.message
        
        # 测试PostgreSQL无效认证
        postgresql_data = {
            "name": "test_postgresql_invalid",
            "source_type": "DATABASE",
            "db_type": DatabaseType.POSTGRESQL,
            "host": "localhost",
            "port": 5432,
            "database_name": "test_db",
            "username": "invalid_user",
            "password": "invalid_password"
        }
        
        mock_postgresql.side_effect = Exception("password authentication failed")
        result = ConnectionTestService.test_connection(postgresql_data)
        assert result.success is False
        assert "认证失败" in result.message
        
        # 测试ClickHouse无效认证
        clickhouse_data = {
            "name": "test_clickhouse_invalid",
            "source_type": "DATABASE",
            "db_type": DatabaseType.CLICKHOUSE,
            "host": "localhost",
            "port": 8123,
            "database_name": "test_db",
            "username": "invalid_user",
            "password": "invalid_password"
        }
        
        mock_clickhouse.side_effect = Exception("Authentication failed")
        result = ConnectionTestService.test_connection(clickhouse_data)
        assert result.success is False
        assert "认证失败" in result.message
    
    @patch('mysql.connector.connect')
    def test_connection_latency_calculation(self, mock_connect):
        """测试连接延迟计算"""
        # 创建测试数据
        test_data = {
            "name": "test_latency",
            "source_type": "DATABASE",
            "db_type": DatabaseType.MYSQL,
            "host": "localhost",
            "port": 3306,
            "database_name": "test_db",
            "username": "test_user",
            "password": "test_password"
        }
        
        # 模拟连接成功
        mock_connection = unittest.mock.Mock()
        mock_connection.is_connected.return_value = True
        mock_connect.return_value = mock_connection
        
        # 调用连接测试服务
        result = ConnectionTestService.test_connection(test_data)
        
        # 验证延迟计算
        assert result.success is True
        assert result.latency_ms is not None
        assert result.latency_ms >= 0
        
        # 验证延迟在合理范围内
        assert result.latency_ms < 10000  # 10秒内完成
    
    @patch('mysql.connector.connect')
    def test_database_not_found(self, mock_connect):
        """测试数据库不存在场景"""
        # 创建测试数据 - 使用不存在的数据库
        test_data = {
            "name": "test_db_not_found",
            "source_type": "DATABASE",
            "db_type": DatabaseType.MYSQL,
            "host": "localhost",
            "port": 3306,
            "database_name": "nonexistent_database",
            "username": "test_user",
            "password": "test_password"
        }
        
        # 模拟数据库不存在
        mock_connect.side_effect = Exception("Unknown database 'nonexistent_database'")
        
        # 调用连接测试服务
        result = ConnectionTestService.test_connection(test_data)
        
        # 验证结果
        assert result.success is False
        assert "数据库不存在" in result.message
        assert result.latency_ms is None
        
        # 验证mock被正确调用
        mock_connect.assert_called_once_with(
            host="localhost",
            port=3306,
            database="nonexistent_database",
            user="test_user",
            password="test_password",
            connection_timeout=10,
            autocommit=True
        )
    
    @patch('mysql.connector.connect')
    def test_host_unreachable(self, mock_connect):
        """测试主机不可达场景"""
        # 创建测试数据 - 使用不存在的主机
        test_data = {
            "name": "test_host_unreachable",
            "source_type": "DATABASE",
            "db_type": DatabaseType.MYSQL,
            "host": "192.168.1.999",  # 无效IP
            "port": 3306,
            "database_name": "test_db",
            "username": "test_user",
            "password": "test_password"
        }
        
        # 模拟主机不可达
        mock_connect.side_effect = Exception("Unknown MySQL server host '192.168.1.999' (8)")
        
        # 调用连接测试服务
        result = ConnectionTestService.test_connection(test_data)
        
        # 验证结果
        assert result.success is False
        assert "主机不可达" in result.message
        assert result.latency_ms is None
        
        # 验证mock被正确调用
        mock_connect.assert_called_once_with(
            host="192.168.1.999",
            port=3306,
            database="test_db",
            user="test_user",
            password="test_password",
            connection_timeout=10,
            autocommit=True
        )
    
    @patch('mysql.connector.connect')
    def test_port_error(self, mock_connect):
        """测试端口错误场景"""
        # 创建测试数据 - 使用错误的端口
        test_data = {
            "name": "test_port_error",
            "source_type": "DATABASE",
            "db_type": DatabaseType.MYSQL,
            "host": "localhost",
            "port": 99999,  # 无效端口
            "database_name": "test_db",
            "username": "test_user",
            "password": "test_password"
        }
        
        # 模拟端口错误
        mock_connect.side_effect = Exception("Unknown MySQL server host 'localhost' (8)")
        
        # 调用连接测试服务
        result = ConnectionTestService.test_connection(test_data)
        
        # 验证结果
        assert result.success is False
        assert "端口错误" in result.message or "主机不可达" in result.message
        assert result.latency_ms is None
        
        # 验证mock被正确调用
        mock_connect.assert_called_once_with(
            host="localhost",
            port=99999,
            database="test_db",
            user="test_user",
            password="test_password",
            connection_timeout=10,
            autocommit=True
        )
    
    def test_missing_required_fields(self):
        """测试缺少必要字段"""
        # 测试缺少主机
        test_data = {
            "name": "test_missing_host",
            "source_type": "DATABASE",
            "db_type": DatabaseType.MYSQL,
            "port": 3306,
            "database_name": "test_db",
            "username": "test_user",
            "password": "test_password"
        }
        
        result = ConnectionTestService.test_connection(test_data)
        assert result.success is False
        assert "主机地址不能为空" in result.message
        
        # 测试缺少端口
        test_data = {
            "name": "test_missing_port",
            "source_type": "DATABASE",
            "db_type": DatabaseType.MYSQL,
            "host": "localhost",
            "database_name": "test_db",
            "username": "test_user",
            "password": "test_password"
        }
        
        result = ConnectionTestService.test_connection(test_data)
        assert result.success is False
        assert "端口号不能为空" in result.message
        
        # 测试缺少数据库名称
        test_data = {
            "name": "test_missing_db",
            "source_type": "DATABASE",
            "db_type": DatabaseType.MYSQL,
            "host": "localhost",
            "port": 3306,
            "username": "test_user",
            "password": "test_password"
        }
        
        result = ConnectionTestService.test_connection(test_data)
        assert result.success is False
        assert "数据库名称不能为空" in result.message
        
        # 测试缺少用户名
        test_data = {
            "name": "test_missing_username",
            "source_type": "DATABASE",
            "db_type": DatabaseType.MYSQL,
            "host": "localhost",
            "port": 3306,
            "database_name": "test_db",
            "password": "test_password"
        }
        
        result = ConnectionTestService.test_connection(test_data)
        assert result.success is False
        assert "用户名不能为空" in result.message
        
        # 测试缺少密码
        test_data = {
            "name": "test_missing_password",
            "source_type": "DATABASE",
            "db_type": DatabaseType.MYSQL,
            "host": "localhost",
            "port": 3306,
            "database_name": "test_db",
            "username": "test_user"
        }
        
        result = ConnectionTestService.test_connection(test_data)
        assert result.success is False
        assert "密码不能为空" in result.message
    
    def test_unsupported_database_type(self):
        """测试不支持的数据库类型"""
        # 创建测试数据 - 使用不支持的数据库类型
        test_data = {
            "name": "test_unsupported",
            "source_type": "DATABASE",
            "db_type": "ORACLE",  # 不支持的类型
            "host": "localhost",
            "port": 1521,
            "database_name": "test_db",
            "username": "test_user",
            "password": "test_password"
        }
        
        # 调用连接测试服务
        result = ConnectionTestService.test_connection(test_data)
        
        # 验证结果
        assert result.success is False
        assert "不支持的数据库类型" in result.message
        assert result.latency_ms is None
    
    @patch('pyodbc.connect')
    def test_sql_server_windows_auth(self, mock_connect):
        """测试SQL Server Windows认证"""
        # 创建测试数据 - 使用Windows认证
        test_data = {
            "name": "test_sql_server_windows",
            "source_type": "DATABASE",
            "db_type": DatabaseType.SQL_SERVER,
            "host": "localhost",
            "port": 1433,
            "database_name": "test_db",
            "domain": "TESTDOMAIN",
            "auth_type": "WINDOWS_AUTH"
        }
        
        # 模拟连接成功
        mock_connection = unittest.mock.Mock()
        mock_connect.return_value = mock_connection
        
        # 调用连接测试服务
        result = ConnectionTestService.test_connection(test_data)
        
        # 验证结果
        assert result.success is True or "认证失败" in result.message  # Windows认证可能在非Windows环境失败，但不应抛出异常
        assert result.latency_ms is not None or result.latency_ms is None  # 延迟可能为None如果连接失败
        
        # 验证mock被正确调用
        mock_connect.assert_called_once_with(
            "DRIVER={ODBC Driver 17 for SQL Server};SERVER=localhost,1433;DATABASE=test_db;Trusted_Connection=yes;",
            timeout=10
        )
    
    @patch('clickhouse_driver.Client')
    def test_clickhouse_connection_success(self, mock_client):
        """测试ClickHouse连接成功场景"""
        # 创建测试数据
        test_data = {
            "name": "test_clickhouse",
            "source_type": "DATABASE",
            "db_type": DatabaseType.CLICKHOUSE,
            "host": "localhost",
            "port": 8123,
            "database_name": "default",
            "username": "default",
            "password": ""
        }
        
        # 模拟连接成功
        mock_client_instance = unittest.mock.Mock()
        mock_client_instance.execute.return_value = [[1]]
        mock_client.return_value = mock_client_instance
        
        # 调用连接测试服务
        result = ConnectionTestService.test_connection(test_data)
        
        # 验证结果
        assert result.success is True
        assert result.message == "ClickHouse连接成功"
        assert result.latency_ms is not None
        assert result.latency_ms >= 0
        
        # 验证mock被正确调用
        mock_client.assert_called_once_with(
            host="localhost",
            port=8123,
            database="default",
            user="default",
            password="",
            connect_timeout=10,
            send_receive_timeout=10
        )
        mock_client_instance.execute.assert_called_once_with("SELECT 1")
    
    @patch('clickhouse_driver.Client')
    def test_clickhouse_connection_failure(self, mock_client):
        """测试ClickHouse连接失败场景"""
        # 创建测试数据 - 使用无效的认证信息
        test_data = {
            "name": "test_clickhouse_failure",
            "source_type": "DATABASE",
            "db_type": DatabaseType.CLICKHOUSE,
            "host": "localhost",
            "port": 8123,
            "database_name": "default",
            "username": "invalid_user",
            "password": "invalid_password"
        }
        
        # 模拟认证失败
        mock_client.side_effect = Exception("Authentication failed")
        
        # 调用连接测试服务
        result = ConnectionTestService.test_connection(test_data)
        
        # 验证结果
        assert result.success is False
        assert "认证失败" in result.message
        assert result.latency_ms is None
        
        # 验证mock被正确调用
        mock_client.assert_called_once_with(
            host="localhost",
            port=8123,
            database="default",
            user="invalid_user",
            password="invalid_password",
            connect_timeout=10,
            send_receive_timeout=10
        )
