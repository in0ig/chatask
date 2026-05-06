import unittest
import logging
from unittest.mock import patch, MagicMock, mock_open
import sys
import os

# 导入模拟的mysql包
from tests.unit.mock_mysql import mock_mysql

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

# 验证src模块是否可导入
try:
    from src.services.table_discovery import TableDiscoveryService, TableDiscoveryResult, TableInfo
    from src.schemas.data_source_schema import DatabaseType
except ImportError as e:
    raise ImportError(f"无法导入src模块，请确保在backend目录下运行测试。项目根目录: {project_root}\n错误: {e}")

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TestTableDiscoveryService(unittest.TestCase):
    """表发现服务单元测试"""
    
    def setUp(self):
        """测试前设置"""
        self.test_mysql_config = {
            "name": "test_mysql",
            "source_type": "DATABASE",
            "db_type": "MYSQL",
            "host": "localhost",
            "port": 3306,
            "database_name": "test_db",
            "username": "test_user",
            "password": "test_password",
            "domain": None
        }
        
        self.test_sql_server_config = {
            "name": "test_sql_server",
            "source_type": "DATABASE",
            "db_type": "SQL_SERVER",
            "host": "localhost",
            "port": 1433,
            "database_name": "test_db",
            "username": "test_user",
            "password": "test_password",
            "domain": None
        }
        
        self.test_postgresql_config = {
            "name": "test_postgresql",
            "source_type": "DATABASE",
            "db_type": "POSTGRESQL",
            "host": "localhost",
            "port": 5432,
            "database_name": "test_db",
            "username": "test_user",
            "password": "test_password",
            "domain": None
        }
        
        self.test_clickhouse_config = {
            "name": "test_clickhouse",
            "source_type": "DATABASE",
            "db_type": "CLICKHOUSE",
            "host": "localhost",
            "port": 8123,
            "database_name": "test_db",
            "username": "default",
            "password": "",
            "domain": None
        }
        
        # 测试数据
        self.test_tables = [
            TableInfo(name="users", type="TABLE", comment="用户表"),
            TableInfo(name="orders", type="TABLE", comment="订单表"),
            TableInfo(name="products", type="VIEW", comment="产品视图")
        ]
    
    def test_discover_mysql_tables_success(self):
        """测试MySQL表列表查询成功"""
        # 使用导入的mock_mysql模拟包
        mock_connector = mock_mysql.connector
        mock_connection = MagicMock()
        mock_cursor = MagicMock()
        
        # 设置模拟的connect函数
        mock_connector.connect = MagicMock(return_value=mock_connection)
        mock_connection.is_connected.return_value = True
        
        # 模拟查询结果，使用生产代码中可能返回的类型
        mock_cursor.fetchall.return_value = [
            ("users", "BASE TABLE", "用户表"),
            ("orders", "BASE TABLE", "订单表"),
            ("products", "VIEW", "产品视图")
        ]
        
        # 模拟游标
        mock_connection.cursor.return_value = mock_cursor
        
        # 执行测试
        result = TableDiscoveryService.discover_mysql_tables(
            "localhost", 3306, "test_db", "test_user", "test_password"
        )
        
        # 验证结果
        self.assertTrue(result.success)
        self.assertEqual(len(result.tables), 3)
        self.assertEqual(result.tables[0].name, "users")
        self.assertEqual(result.tables[0].type, "BASE TABLE")
        self.assertEqual(result.tables[0].comment, "用户表")
        self.assertEqual(result.tables[2].name, "products")
        self.assertEqual(result.tables[2].type, "VIEW")
        self.assertEqual(result.tables[2].comment, "产品视图")
        self.assertIsNone(result.error_message)
        
                # 验证连接和查询被正确调用
        mock_connector.connect.assert_called_once_with(
            host="localhost", port=3306, database="test_db", 
            user="test_user", password="test_password", 
            connection_timeout=10, autocommit=True
        )
        mock_connection.cursor.assert_called_once()
        mock_cursor.execute.assert_called_once_with(
            "\n                SELECT \n                    TABLE_NAME as table_name,\n                    TABLE_TYPE as table_type,\n                    TABLE_COMMENT as table_comment\n                FROM information_schema.TABLES \n                WHERE TABLE_SCHEMA = %s\n                ORDER BY TABLE_NAME\n            ", ("test_db",)
        )
        mock_cursor.close.assert_called_once()
        mock_connection.close.assert_called_once()
    
    def test_discover_mysql_tables_connection_failed(self):
        """测试MySQL连接失败"""
        # 使用导入的mock_mysql模拟包
        mock_connector = mock_mysql.connector
        
        # 创建真实的mysql.connector.Error异常类型
        mock_connector.Error = type('Error', (Exception,), {})
        mock_connector.connect.side_effect = mock_connector.Error("Can't connect to MySQL server")
        
        # 执行测试
        result = TableDiscoveryService.discover_mysql_tables(
            "localhost", 3306, "test_db", "test_user", "test_password"
        )
        
        # 验证结果
        self.assertFalse(result.success)
        self.assertEqual(len(result.tables), 0)
        self.assertEqual(result.error_message, "MySQL连接失败：主机不可达或端口错误")
    
    def test_discover_mysql_tables_authentication_failed(self):
        """测试MySQL认证失败"""
        # 使用导入的mock_mysql模拟包
        mock_connector = mock_mysql.connector
        
        # 创建真实的mysql.connector.Error异常类型
        mock_connector.Error = type('Error', (Exception,), {})
        mock_connector.connect.side_effect = mock_connector.Error("Access denied for user")
        
        # 执行测试
        result = TableDiscoveryService.discover_mysql_tables(
            "localhost", 3306, "test_db", "test_user", "test_password"
        )
        
        # 验证结果
        self.assertFalse(result.success)
        self.assertEqual(len(result.tables), 0)
        self.assertEqual(result.error_message, "MySQL认证失败：用户名或密码错误")
    
    def test_discover_mysql_tables_database_not_exist(self):
        """测试MySQL数据库不存在"""
        # 使用导入的mock_mysql模拟包
        mock_connector = mock_mysql.connector
        
        # 创建真实的mysql.connector.Error异常类型
        mock_connector.Error = type('Error', (Exception,), {})
        mock_connector.connect.side_effect = mock_connector.Error("Unknown database")
        
        # 执行测试
        result = TableDiscoveryService.discover_mysql_tables(
            "localhost", 3306, "test_db", "test_user", "test_password"
        )
        
        # 验证结果
        self.assertFalse(result.success)
        self.assertEqual(len(result.tables), 0)
        self.assertEqual(result.error_message, "MySQL连接失败：数据库不存在")
    
    def test_discover_sql_server_tables_success(self):
        """测试SQL Server表列表查询成功"""
        # 创建模拟的pyodbc模块
        mock_pyodbc = MagicMock()
        mock_connection = MagicMock()
        mock_cursor = MagicMock()
        
        # 设置模拟的connect函数
        mock_pyodbc.connect = MagicMock(return_value=mock_connection)
        
        # 模拟查询结果
        mock_cursor.fetchall.return_value = [
            ("users", "TABLE", "用户表"),
            ("orders", "TABLE", "订单表"),
            ("products", "VIEW", "产品视图")
        ]
        
        # 模拟游标
        mock_connection.cursor.return_value = mock_cursor
        
        # 将模拟的模块添加到sys.modules中
        import sys
        sys.modules['pyodbc'] = mock_pyodbc
        
        # 执行测试
        result = TableDiscoveryService.discover_sql_server_tables(
            "localhost", 1433, "test_db", "test_user", "test_password"
        )
        
        # 验证结果
        self.assertTrue(result.success)
        self.assertEqual(len(result.tables), 3)
        self.assertEqual(result.tables[0].name, "users")
        self.assertEqual(result.tables[0].type, "TABLE")
        self.assertEqual(result.tables[0].comment, "用户表")
        self.assertEqual(result.tables[2].name, "products")
        self.assertEqual(result.tables[2].type, "VIEW")
        self.assertEqual(result.tables[2].comment, "产品视图")
        self.assertIsNone(result.error_message)
        
        # 验证连接和查询被正确调用
        mock_pyodbc.connect.assert_called_once_with(
            "DRIVER={ODBC Driver 17 for SQL Server};SERVER=localhost,1433;DATABASE=test_db;UID=test_user;PWD=test_password;", timeout=10
        )
        mock_connection.cursor.assert_called_once()
        mock_cursor.execute.assert_called_once_with(
            "\n                SELECT \n                    t.name as table_name,\n                    CASE t.type \n                        WHEN 'U' THEN 'TABLE'\n                        WHEN 'V' THEN 'VIEW'\n                        ELSE t.type\n                    END as table_type,\n                    ep.value as table_comment\n                FROM sys.tables t\n                LEFT JOIN sys.extended_properties ep ON t.object_id = ep.major_id \n                    AND ep.minor_id = 0 \n                    AND ep.name = 'MS_Description'\n                ORDER BY t.name\n            "
        )
        mock_cursor.close.assert_called_once()
        mock_connection.close.assert_called_once()
    
    def test_discover_sql_server_tables_connection_failed(self):
        """测试SQL Server连接失败"""
        # 创建模拟的pyodbc模块
        mock_pyodbc = MagicMock()
        
        # 创建真实的pyodbc.Error异常类型
        mock_pyodbc.Error = type('Error', (Exception,), {})
        mock_pyodbc.connect.side_effect = mock_pyodbc.Error("Could not open a connection to SQL Server")
        
        # 将模拟的模块添加到sys.modules中
        import sys
        sys.modules['pyodbc'] = mock_pyodbc
        
        # 执行测试
        result = TableDiscoveryService.discover_sql_server_tables(
            "localhost", 1433, "test_db", "test_user", "test_password"
        )
        
        # 验证结果
        self.assertFalse(result.success)
        self.assertEqual(len(result.tables), 0)
        self.assertEqual(result.error_message, "SQL Server连接失败：主机不可达或端口错误")
    
    def test_discover_sql_server_tables_authentication_failed(self):
        """测试SQL Server认证失败"""
        # 创建模拟的pyodbc模块
        mock_pyodbc = MagicMock()
        
        # 创建真实的pyodbc.Error异常类型
        mock_pyodbc.Error = type('Error', (Exception,), {})
        mock_pyodbc.connect.side_effect = mock_pyodbc.Error("Login failed for user")
        
        # 将模拟的模块添加到sys.modules中
        import sys
        sys.modules['pyodbc'] = mock_pyodbc
        
        # 执行测试
        result = TableDiscoveryService.discover_sql_server_tables(
            "localhost", 1433, "test_db", "test_user", "test_password"
        )
        
        # 验证结果
        self.assertFalse(result.success)
        self.assertEqual(len(result.tables), 0)
        self.assertEqual(result.error_message, "SQL Server认证失败：用户名或密码错误")
    
    def test_discover_sql_server_tables_database_not_exist(self):
        """测试SQL Server数据库不存在"""
        # 创建模拟的pyodbc模块
        mock_pyodbc = MagicMock()
        
        # 创建真实的pyodbc.Error异常类型
        mock_pyodbc.Error = type('Error', (Exception,), {})
        mock_pyodbc.connect.side_effect = mock_pyodbc.Error("Database does not exist")
        
        # 将模拟的模块添加到sys.modules中
        import sys
        sys.modules['pyodbc'] = mock_pyodbc
        
        # 执行测试
        result = TableDiscoveryService.discover_sql_server_tables(
            "localhost", 1433, "test_db", "test_user", "test_password"
        )
        
        # 验证结果
        self.assertFalse(result.success)
        self.assertEqual(len(result.tables), 0)
        self.assertEqual(result.error_message, "SQL Server连接失败：数据库不存在")
    
    def test_discover_postgresql_tables_success(self):
        """测试PostgreSQL表列表查询成功"""
        # 创建模拟的psycopg2模块
        mock_psycopg2 = MagicMock()
        mock_connection = MagicMock()
        mock_cursor = MagicMock()
        
        # 设置模拟的connect函数
        mock_psycopg2.connect = MagicMock(return_value=mock_connection)
        
        # 模拟查询结果，将table_type映射为TABLE/VIEW
        mock_cursor.fetchall.return_value = [
            ("users", "BASE TABLE", "用户表"),
            ("orders", "BASE TABLE", "订单表"),
            ("products", "VIEW", "产品视图")
        ]
        
        # 模拟游标
        mock_connection.cursor.return_value = mock_cursor
        
        # 将模拟的模块添加到sys.modules中
        import sys
        sys.modules['psycopg2'] = mock_psycopg2
        
        # 执行测试
        result = TableDiscoveryService.discover_postgresql_tables(
            "localhost", 5432, "test_db", "test_user", "test_password"
        )
        
        # 验证结果
        self.assertTrue(result.success)
        self.assertEqual(len(result.tables), 3)
        self.assertEqual(result.tables[0].name, "users")
        self.assertEqual(result.tables[0].type, "TABLE")
        self.assertEqual(result.tables[0].comment, "用户表")
        self.assertEqual(result.tables[2].name, "products")
        self.assertEqual(result.tables[2].type, "VIEW")
        self.assertEqual(result.tables[2].comment, "产品视图")
        self.assertIsNone(result.error_message)
        
        # 验证连接和查询被正确调用
        mock_psycopg2.connect.assert_called_once_with(
            host="localhost", port=5432, database="test_db", 
            user="test_user", password="test_password", connect_timeout=10
        )
        mock_connection.cursor.assert_called_once()
        mock_cursor.execute.assert_called_once_with(
            "\n                SELECT \n                    t.table_name as table_name,\n                    t.table_type as table_type,\n                    pgd.description as table_comment\n                FROM information_schema.tables t\n                LEFT JOIN pg_catalog.pg_statio_user_tables st ON t.table_name = st.relname\n                LEFT JOIN pg_catalog.pg_description pgd ON st.relid = pgd.objoid AND pgd.objsubid = 0\n                WHERE t.table_schema = 'public'\n                ORDER BY t.table_name\n            "
        )
        mock_cursor.close.assert_called_once()
        mock_connection.close.assert_called_once()
    
    def test_discover_postgresql_tables_connection_failed(self):
        """测试PostgreSQL连接失败"""
        # 创建模拟的psycopg2模块
        mock_psycopg2 = MagicMock()
        
        # 创建真实的psycopg2.OperationalError异常类型
        mock_psycopg2.OperationalError = type('OperationalError', (Exception,), {})
        mock_psycopg2.connect.side_effect = mock_psycopg2.OperationalError("could not translate host name")
        
        # 将模拟的模块添加到sys.modules中
        import sys
        sys.modules['psycopg2'] = mock_psycopg2
        
        # 执行测试
        result = TableDiscoveryService.discover_postgresql_tables(
            "localhost", 5432, "test_db", "test_user", "test_password"
        )
        
        # 验证结果
        self.assertFalse(result.success)
        self.assertEqual(len(result.tables), 0)
        self.assertEqual(result.error_message, "PostgreSQL连接失败：主机不可达或端口错误")
    
    def test_discover_postgresql_tables_authentication_failed(self):
        """测试PostgreSQL认证失败"""
        # 创建模拟的psycopg2模块
        mock_psycopg2 = MagicMock()
        
        # 创建真实的psycopg2.OperationalError异常类型
        mock_psycopg2.OperationalError = type('OperationalError', (Exception,), {})
        mock_psycopg2.connect.side_effect = mock_psycopg2.OperationalError("password authentication failed")
        
        # 将模拟的模块添加到sys.modules中
        import sys
        sys.modules['psycopg2'] = mock_psycopg2
        
        # 执行测试
        result = TableDiscoveryService.discover_postgresql_tables(
            "localhost", 5432, "test_db", "test_user", "test_password"
        )
        
        # 验证结果
        self.assertFalse(result.success)
        self.assertEqual(len(result.tables), 0)
        self.assertEqual(result.error_message, "PostgreSQL认证失败：用户名或密码错误")
    
    def test_discover_postgresql_tables_database_not_exist(self):
        """测试PostgreSQL数据库不存在"""
        # 创建模拟的psycopg2模块
        mock_psycopg2 = MagicMock()
        
        # 创建真实的psycopg2.OperationalError异常类型
        mock_psycopg2.OperationalError = type('OperationalError', (Exception,), {})
        mock_psycopg2.connect.side_effect = mock_psycopg2.OperationalError("database \"test_db\" does not exist")
        
        # 将模拟的模块添加到sys.modules中
        import sys
        sys.modules['psycopg2'] = mock_psycopg2
        
        # 执行测试
        result = TableDiscoveryService.discover_postgresql_tables(
            "localhost", 5432, "test_db", "test_user", "test_password"
        )
        
        # 验证结果
        self.assertFalse(result.success)
        self.assertEqual(len(result.tables), 0)
        self.assertEqual(result.error_message, "PostgreSQL连接失败：数据库不存在")
    
    def test_discover_clickhouse_tables_success(self):
        """测试ClickHouse表列表查询成功"""
        # 创建模拟的clickhouse_driver模块
        mock_clickhouse_driver = MagicMock()
        mock_client = MagicMock()
        
        # 设置模拟的Client类
        mock_clickhouse_driver.Client = MagicMock(return_value=mock_client)
        
        # 模拟查询结果，将engine类型映射为TABLE/VIEW
        mock_client.execute.return_value = [
            ("users", "MergeTree", "用户表"),
            ("orders", "MergeTree", "订单表"),
            ("products", "View", "产品视图")
        ]
        
        # 将模拟的模块添加到sys.modules中
        import sys
        sys.modules['clickhouse_driver'] = mock_clickhouse_driver
        
        # 执行测试
        result = TableDiscoveryService.discover_clickhouse_tables(
            "localhost", 8123, "test_db", "default", ""
        )
        
        # 验证结果
        self.assertTrue(result.success)
        self.assertEqual(len(result.tables), 3)
        self.assertEqual(result.tables[0].name, "users")
        self.assertEqual(result.tables[0].type, "TABLE")
        self.assertEqual(result.tables[0].comment, "用户表")
        self.assertEqual(result.tables[2].name, "products")
        self.assertEqual(result.tables[2].type, "VIEW")
        self.assertIsNone(result.error_message)
        
        # 验证连接和查询被正确调用
        mock_clickhouse_driver.Client.assert_called_once_with(
            host="localhost", port=8123, database="test_db", 
            user="default", password="", connect_timeout=10, send_receive_timeout=10
        )
        mock_client.execute.assert_called_once_with(
            "\n                SELECT \n                    name as table_name,\n                    engine as table_type,\n                    comment as table_comment\n                FROM system.tables \n                WHERE database = %s\n                ORDER BY name\n            ",
            ("test_db",)
        )
        mock_client.disconnect.assert_called_once()
    
    def test_discover_clickhouse_tables_connection_failed(self):
        """测试ClickHouse连接失败"""
        # 创建模拟的clickhouse_driver模块
        mock_clickhouse_driver = MagicMock()
        
        # 创建模拟的Client类，使用Exception作为基类
        mock_client_class = MagicMock()
        mock_client_class.side_effect = Exception("Connection refused")
        mock_clickhouse_driver.Client = mock_client_class
        
        # 将模拟的模块添加到sys.modules中
        import sys
        sys.modules['clickhouse_driver'] = mock_clickhouse_driver
        
        # 执行测试
        result = TableDiscoveryService.discover_clickhouse_tables(
            "localhost", 8123, "test_db", "default", ""
        )
        
        # 验证结果
        self.assertFalse(result.success)
        self.assertEqual(len(result.tables), 0)
        self.assertEqual(result.error_message, "ClickHouse连接失败：主机不可达或端口错误")
    
    def test_discover_clickhouse_tables_authentication_failed(self):
        """测试ClickHouse认证失败"""
        # 创建模拟的clickhouse_driver模块
        mock_clickhouse_driver = MagicMock()
        
        # 创建模拟的Client类，使用Exception作为基类
        mock_client_class = MagicMock()
        mock_client_class.side_effect = Exception("Authentication failed")
        mock_clickhouse_driver.Client = mock_client_class
        
        # 将模拟的模块添加到sys.modules中
        import sys
        sys.modules['clickhouse_driver'] = mock_clickhouse_driver
        
        # 执行测试
        result = TableDiscoveryService.discover_clickhouse_tables(
            "localhost", 8123, "test_db", "default", ""
        )
        
        # 验证结果
        self.assertFalse(result.success)
        self.assertEqual(len(result.tables), 0)
        self.assertEqual(result.error_message, "ClickHouse认证失败：用户名或密码错误")
    
    def test_discover_clickhouse_tables_database_not_exist(self):
        """测试ClickHouse数据库不存在"""
        # 创建模拟的clickhouse_driver模块
        mock_clickhouse_driver = MagicMock()
        
        # 创建模拟的Client类，使用Exception作为基类
        mock_client_class = MagicMock()
        mock_client_class.side_effect = Exception("Database does not exist")
        mock_clickhouse_driver.Client = mock_client_class
        
        # 将模拟的模块添加到sys.modules中
        import sys
        sys.modules['clickhouse_driver'] = mock_clickhouse_driver
        
        # 执行测试
        result = TableDiscoveryService.discover_clickhouse_tables(
            "localhost", 8123, "test_db", "default", ""
        )
        
        # 验证结果
        self.assertFalse(result.success)
        self.assertEqual(len(result.tables), 0)
        self.assertEqual(result.error_message, "ClickHouse连接失败：数据库不存在")
    
    def test_discover_tables_by_data_source_missing_host(self):
        """测试缺少主机地址的情况"""
        config = self.test_mysql_config.copy()
        config["host"] = None
        
        result = TableDiscoveryService.discover_tables_by_data_source(config)
        
        self.assertFalse(result.success)
        self.assertEqual(result.error_message, "主机地址不能为空")
        self.assertEqual(len(result.tables), 0)
    
    def test_discover_tables_by_data_source_missing_port(self):
        """测试缺少端口号的情况"""
        config = self.test_mysql_config.copy()
        config["port"] = None
        
        result = TableDiscoveryService.discover_tables_by_data_source(config)
        
        self.assertFalse(result.success)
        self.assertEqual(result.error_message, "端口号不能为空")
        self.assertEqual(len(result.tables), 0)
    
    def test_discover_tables_by_data_source_missing_database_name(self):
        """测试缺少数据库名称的情况"""
        config = self.test_mysql_config.copy()
        config["database_name"] = None
        
        result = TableDiscoveryService.discover_tables_by_data_source(config)
        
        self.assertFalse(result.success)
        self.assertEqual(result.error_message, "数据库名称不能为空")
        self.assertEqual(len(result.tables), 0)
    
    def test_discover_tables_by_data_source_missing_username(self):
        """测试缺少用户名的情况（非SQL Server Windows认证）"""
        config = self.test_mysql_config.copy()
        config["username"] = None
        
        result = TableDiscoveryService.discover_tables_by_data_source(config)
        
        self.assertFalse(result.success)
        self.assertEqual(result.error_message, "用户名不能为空")
        self.assertEqual(len(result.tables), 0)
    
    def test_discover_tables_by_data_source_missing_password(self):
        """测试缺少密码的情况（非Windows认证且非ClickHouse默认连接）"""
        config = self.test_mysql_config.copy()
        config["password"] = None
        
        result = TableDiscoveryService.discover_tables_by_data_source(config)
        
        self.assertFalse(result.success)
        self.assertEqual(result.error_message, "密码不能为空")
        self.assertEqual(len(result.tables), 0)
    
    def test_discover_tables_by_data_source_sql_server_windows_auth(self):
        """测试SQL Server Windows认证（用户名为空）"""
        config = self.test_sql_server_config.copy()
        config["username"] = None
        config["domain"] = "DOMAIN"
        
        # 模拟查询成功
        with patch.object(TableDiscoveryService, 'discover_sql_server_tables') as mock_discover:
            mock_discover.return_value = TableDiscoveryResult(
                tables=self.test_tables,
                success=True,
                error_message=None
            )
            
            result = TableDiscoveryService.discover_tables_by_data_source(config)
            
            self.assertTrue(result.success)
            self.assertEqual(len(result.tables), 3)
            self.assertIsNone(result.error_message)
            mock_discover.assert_called_once()
    
    def test_discover_tables_by_data_source_clickhouse_default_connection(self):
        """测试ClickHouse默认连接（密码为空）"""
        config = self.test_clickhouse_config.copy()
        config["password"] = ""
        
        # 模拟查询成功
        with patch.object(TableDiscoveryService, 'discover_clickhouse_tables') as mock_discover:
            mock_discover.return_value = TableDiscoveryResult(
                tables=self.test_tables,
                success=True,
                error_message=None
            )
            
            result = TableDiscoveryService.discover_tables_by_data_source(config)
            
            self.assertTrue(result.success)
            self.assertEqual(len(result.tables), 3)
            self.assertIsNone(result.error_message)
            mock_discover.assert_called_once_with(
                "localhost", 8123, "test_db", "default", ""
            )
    
    def test_discover_tables_by_data_source_unsupported_db_type(self):
        """测试不支持的数据库类型"""
        config = self.test_mysql_config.copy()
        config["db_type"] = "ORACLE"
        
        result = TableDiscoveryService.discover_tables_by_data_source(config)
        
        self.assertFalse(result.success)
        self.assertEqual(result.error_message, "不支持的数据库类型")
        self.assertEqual(len(result.tables), 0)
    
    def test_discover_tables_by_data_source_mysql_success(self):
        """测试MySQL数据库表发现成功"""
        # 模拟查询成功
        with patch.object(TableDiscoveryService, 'discover_mysql_tables') as mock_discover:
            mock_discover.return_value = TableDiscoveryResult(
                tables=self.test_tables,
                success=True,
                error_message=None
            )
            
            result = TableDiscoveryService.discover_tables_by_data_source(self.test_mysql_config)
            
            self.assertTrue(result.success)
            self.assertEqual(len(result.tables), 3)
            self.assertIsNone(result.error_message)
            mock_discover.assert_called_once_with(
                "localhost", 3306, "test_db", "test_user", "test_password"
            )

    def test_discover_tables_by_data_source_sql_server_success(self):
        """测试SQL Server数据库表发现成功"""
        # 模拟查询成功
        with patch.object(TableDiscoveryService, 'discover_sql_server_tables') as mock_discover:
            mock_discover.return_value = TableDiscoveryResult(
                tables=self.test_tables,
                success=True,
                error_message=None
            )
            
            result = TableDiscoveryService.discover_tables_by_data_source(self.test_sql_server_config)
            
            self.assertTrue(result.success)
            self.assertEqual(len(result.tables), 3)
            self.assertIsNone(result.error_message)
            mock_discover.assert_called_once_with(
                "localhost", 1433, "test_db", "test_user", "test_password", None
            )

if __name__ == '__main__':
    unittest.main()