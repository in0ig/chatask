"""
ChatBI数据源模块单元测试

专门针对ChatBI需求的数据源测试：
- 只支持MySQL和SQL Server
- 测试CRUD操作
- 测试连接功能
- 测试密码加密
- 测试错误处理
"""

import pytest
import uuid
from unittest.mock import Mock, patch, MagicMock
from sqlalchemy.orm import Session
from src.models.data_source_model import DataSource
from src.schemas.data_source_schema import (
    DataSourceCreate, 
    DataSourceUpdate, 
    DatabaseType, 
    AuthType,
    DataSourceTestConnection
)
from src.services.data_source_service import DataSourceService
from src.services.connection_test import ConnectionTestService, ConnectionResult


class TestDataSourceChatBI:
    """ChatBI数据源模块测试类"""
    
    def setup_method(self):
        """测试前准备"""
        self.service = DataSourceService()
        self.mock_db = Mock(spec=Session)
    
    def test_create_mysql_data_source_success(self):
        """测试创建MySQL数据源成功"""
        # 准备测试数据
        create_data = DataSourceCreate(
            name="ChatBI MySQL数据源",
            source_type="DATABASE",
            db_type=DatabaseType.MYSQL,
            host="localhost",
            port=3306,
            database_name="chatbi_db",
            auth_type=AuthType.SQL_AUTH,
            username="chatbi_user",
            password="ChatBI123!",
            description="ChatBI MySQL测试数据源",
            status=True,
            created_by="test_user"
        )
        
        # 模拟数据库操作
        mock_source = DataSource(
            id=str(uuid.uuid4()),
            name=create_data.name,
            source_type=create_data.source_type,
            db_type=create_data.db_type,
            host=create_data.host,
            port=create_data.port,
            database_name=create_data.database_name,
            auth_type=create_data.auth_type,
            username=create_data.username,
            password="encrypted_password",
            description=create_data.description,
            status=create_data.status,
            created_by=create_data.created_by
        )
        
        self.mock_db.add.return_value = None
        self.mock_db.commit.return_value = None
        self.mock_db.refresh.return_value = None
        
        # 执行测试
        result = self.service.add_data_source(self.mock_db, mock_source)
        
        # 验证结果
        assert result is not None
        assert result.name == create_data.name
        assert result.db_type == create_data.db_type
        assert result.host == create_data.host
        assert result.port == create_data.port
        assert result.database_name == create_data.database_name
        assert result.username == create_data.username
        
        # 验证数据库操作被调用
        self.mock_db.add.assert_called_once()
        self.mock_db.commit.assert_called_once()
        self.mock_db.refresh.assert_called_once()
    
    def test_create_sql_server_data_source_success(self):
        """测试创建SQL Server数据源成功"""
        # 准备测试数据
        create_data = DataSourceCreate(
            name="ChatBI SQL Server数据源",
            source_type="DATABASE",
            db_type=DatabaseType.SQL_SERVER,
            host="localhost",
            port=1433,
            database_name="ChatBI_DB",
            auth_type=AuthType.SQL_AUTH,
            username="chatbi_user",
            password="ChatBI123!",
            description="ChatBI SQL Server测试数据源",
            status=True,
            created_by="test_user"
        )
        
        # 模拟数据库操作
        mock_source = DataSource(
            id=str(uuid.uuid4()),
            name=create_data.name,
            source_type=create_data.source_type,
            db_type=create_data.db_type,
            host=create_data.host,
            port=create_data.port,
            database_name=create_data.database_name,
            auth_type=create_data.auth_type,
            username=create_data.username,
            password="encrypted_password",
            description=create_data.description,
            status=create_data.status,
            created_by=create_data.created_by
        )
        
        self.mock_db.add.return_value = None
        self.mock_db.commit.return_value = None
        self.mock_db.refresh.return_value = None
        
        # 执行测试
        result = self.service.add_data_source(self.mock_db, mock_source)
        
        # 验证结果
        assert result is not None
        assert result.name == create_data.name
        assert result.db_type == create_data.db_type
        assert result.host == create_data.host
        assert result.port == create_data.port
        assert result.database_name == create_data.database_name
        assert result.username == create_data.username
        
        # 验证数据库操作被调用
        self.mock_db.add.assert_called_once()
        self.mock_db.commit.assert_called_once()
        self.mock_db.refresh.assert_called_once()
    
    def test_get_data_source_by_id_success(self):
        """测试根据ID获取数据源成功"""
        # 准备测试数据
        source_id = str(uuid.uuid4())
        mock_source = DataSource(
            id=source_id,
            name="测试数据源",
            source_type="DATABASE",
            db_type=DatabaseType.MYSQL,
            host="localhost",
            port=3306,
            database_name="test_db",
            username="test_user",
            status=True,
            created_by="test_user"
        )
        
        # 模拟数据库查询
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = mock_source
        self.mock_db.query.return_value = mock_query
        
        # 执行测试
        result = self.service.get_source_by_id(self.mock_db, source_id)
        
        # 验证结果
        assert result is not None
        assert result.id == source_id
        assert result.name == "测试数据源"
        assert result.db_type == DatabaseType.MYSQL
        
        # 验证数据库查询被调用
        self.mock_db.query.assert_called_once_with(DataSource)
        mock_query.filter.assert_called_once()
        mock_query.filter.return_value.first.assert_called_once()
    
    def test_get_data_source_by_id_not_found(self):
        """测试根据ID获取数据源不存在"""
        # 准备测试数据
        source_id = str(uuid.uuid4())
        
        # 模拟数据库查询返回None
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = None
        self.mock_db.query.return_value = mock_query
        
        # 执行测试
        result = self.service.get_source_by_id(self.mock_db, source_id)
        
        # 验证结果
        assert result is None
        
        # 验证数据库查询被调用
        self.mock_db.query.assert_called_once_with(DataSource)
        mock_query.filter.assert_called_once()
        mock_query.filter.return_value.first.assert_called_once()
    
    def test_update_data_source_success(self):
        """测试更新数据源成功"""
        # 准备测试数据
        source_id = str(uuid.uuid4())
        mock_source = DataSource(
            id=source_id,
            name="原始数据源",
            description="原始描述",
            status=True,
            created_by="test_user"
        )
        
        update_data = {
            "name": "更新后的数据源",
            "description": "更新后的描述",
            "status": False
        }
        
        # 模拟数据库查询
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = mock_source
        self.mock_db.query.return_value = mock_query
        self.mock_db.commit.return_value = None
        self.mock_db.refresh.return_value = None
        
        # 执行测试
        result = self.service.update_data_source(self.mock_db, source_id, update_data)
        
        # 验证结果
        assert result is not None
        assert result.name == "更新后的数据源"
        assert result.description == "更新后的描述"
        assert result.status == False
        
        # 验证数据库操作被调用
        self.mock_db.commit.assert_called_once()
        self.mock_db.refresh.assert_called_once()
    
    def test_delete_data_source_success(self):
        """测试删除数据源成功"""
        # 准备测试数据
        source_id = str(uuid.uuid4())
        mock_source = DataSource(
            id=source_id,
            name="待删除数据源",
            created_by="test_user"
        )
        
        # 模拟数据库查询
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = mock_source
        self.mock_db.query.return_value = mock_query
        self.mock_db.delete.return_value = None
        self.mock_db.commit.return_value = None
        
        # 执行测试
        result = self.service.delete_source(self.mock_db, source_id)
        
        # 验证结果
        assert result == True
        
        # 验证数据库操作被调用
        self.mock_db.delete.assert_called_once_with(mock_source)
        self.mock_db.commit.assert_called_once()
    
    def test_delete_data_source_not_found(self):
        """测试删除不存在的数据源"""
        # 准备测试数据
        source_id = str(uuid.uuid4())
        
        # 模拟数据库查询返回None
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = None
        self.mock_db.query.return_value = mock_query
        
        # 执行测试
        result = self.service.delete_source(self.mock_db, source_id)
        
        # 验证结果
        assert result == False
        
        # 验证删除操作未被调用
        self.mock_db.delete.assert_not_called()
        self.mock_db.commit.assert_not_called()
    
    def test_get_all_sources_with_pagination(self):
        """测试分页获取数据源列表"""
        # 准备测试数据
        mock_sources = [
            DataSource(
                id=str(uuid.uuid4()),
                name=f"数据源{i}",
                source_type="DATABASE",
                db_type=DatabaseType.MYSQL,
                status=True,
                created_by="test_user"
            ) for i in range(5)
        ]
        
        # 模拟数据库查询
        mock_query = Mock()
        mock_query.offset.return_value.limit.return_value.all.return_value = mock_sources[:3]
        self.mock_db.query.return_value = mock_query
        
        # 执行测试
        result = self.service.get_all_sources(
            self.mock_db, 
            page=1, 
            page_size=3
        )
        
        # 验证结果
        assert len(result) == 3
        assert all(source.name.startswith("数据源") for source in result)
        
        # 验证分页参数
        mock_query.offset.assert_called_once_with(0)  # (page-1) * page_size = 0
        mock_query.offset.return_value.limit.assert_called_once_with(3)
    
    def test_get_all_sources_with_search(self):
        """测试搜索数据源"""
        # 准备测试数据
        mock_sources = [
            DataSource(
                id=str(uuid.uuid4()),
                name="ChatBI数据源",
                description="ChatBI专用数据源",
                source_type="DATABASE",
                db_type=DatabaseType.MYSQL,
                status=True,
                created_by="test_user"
            )
        ]
        
        # 模拟数据库查询
        mock_query = Mock()
        mock_query.filter.return_value.offset.return_value.limit.return_value.all.return_value = mock_sources
        self.mock_db.query.return_value = mock_query
        
        # 执行测试
        result = self.service.get_all_sources(
            self.mock_db, 
            search="ChatBI"
        )
        
        # 验证结果
        assert len(result) == 1
        assert result[0].name == "ChatBI数据源"
        
        # 验证搜索过滤被调用
        mock_query.filter.assert_called_once()
    
    def test_mysql_connection_test_success(self):
        """测试MySQL连接测试成功"""
        # 准备测试数据
        test_data = {
            "db_type": DatabaseType.MYSQL,
            "host": "localhost",
            "port": 3306,
            "database_name": "chatbi_db",
            "username": "chatbi_user",
            "password": "ChatBI123!"
        }
        
        # 模拟MySQL连接成功
        with patch('mysql.connector.connect') as mock_connect:
            mock_connection = Mock()
            mock_connection.is_connected.return_value = True
            mock_connect.return_value = mock_connection
            
            # 执行测试
            result = ConnectionTestService.test_connection(test_data)
            
            # 验证结果
            assert result.success == True
            assert "MySQL连接成功" in result.message
            assert result.latency_ms is not None
            assert result.latency_ms >= 0
            
            # 验证连接被调用
            mock_connect.assert_called_once()
            mock_connection.close.assert_called_once()
    
    def test_mysql_connection_test_auth_failure(self):
        """测试MySQL连接测试认证失败"""
        # 准备测试数据
        test_data = {
            "db_type": DatabaseType.MYSQL,
            "host": "localhost",
            "port": 3306,
            "database_name": "chatbi_db",
            "username": "invalid_user",
            "password": "invalid_password"
        }
        
        # 模拟MySQL认证失败
        with patch('mysql.connector.connect') as mock_connect:
            import mysql.connector
            mock_connect.side_effect = mysql.connector.Error("Access denied for user")
            
            # 执行测试
            result = ConnectionTestService.test_connection(test_data)
            
            # 验证结果
            assert result.success == False
            assert "认证失败" in result.message
            assert result.latency_ms is None
    
    def test_sql_server_connection_test_success(self):
        """测试SQL Server连接测试成功"""
        # 准备测试数据
        test_data = {
            "db_type": DatabaseType.SQL_SERVER,
            "host": "localhost",
            "port": 1433,
            "database_name": "ChatBI_DB",
            "username": "chatbi_user",
            "password": "ChatBI123!",
            "domain": None
        }
        
        # 模拟SQL Server连接成功
        with patch('src.services.connection_test.ConnectionTestService.test_sql_server_connection') as mock_test:
            mock_result = ConnectionResult(
                success=True,
                message="SQL Server连接成功",
                latency_ms=100
            )
            mock_test.return_value = mock_result
            
            # 执行测试
            result = ConnectionTestService.test_connection(test_data)
            
            # 验证结果
            assert result.success == True
            assert "SQL Server连接成功" in result.message
            assert result.latency_ms is not None
            assert result.latency_ms >= 0
    
    def test_sql_server_windows_auth_success(self):
        """测试SQL Server Windows认证成功"""
        # 准备测试数据
        test_data = {
            "db_type": DatabaseType.SQL_SERVER,
            "host": "localhost",
            "port": 1433,
            "database_name": "ChatBI_DB",
            "username": "",
            "password": "",
            "domain": "DOMAIN"
        }
        
        # 模拟SQL Server Windows认证成功
        with patch('src.services.connection_test.ConnectionTestService.test_sql_server_connection') as mock_test:
            mock_result = ConnectionResult(
                success=True,
                message="SQL Server连接成功",
                latency_ms=100
            )
            mock_test.return_value = mock_result
            
            # 执行测试
            result = ConnectionTestService.test_connection(test_data)
            
            # 验证结果
            assert result.success == True
            assert "SQL Server连接成功" in result.message
            assert result.latency_ms is not None
            assert result.latency_ms >= 0
    
    def test_unsupported_database_type(self):
        """测试不支持的数据库类型"""
        # 准备测试数据
        test_data = {
            "db_type": "POSTGRESQL",  # ChatBI不支持PostgreSQL
            "host": "localhost",
            "port": 5432,
            "database_name": "test_db",
            "username": "test_user",
            "password": "test_password"
        }
        
        # 执行测试
        result = ConnectionTestService.test_connection(test_data)
        
        # 验证结果
        assert result.success == False
        assert "ChatBI只支持MySQL和SQL Server数据库" in result.message
    
    def test_connection_test_missing_host(self):
        """测试连接测试缺少主机地址"""
        # 准备测试数据
        test_data = {
            "db_type": DatabaseType.MYSQL,
            "host": "",  # 空主机地址
            "port": 3306,
            "database_name": "test_db",
            "username": "test_user",
            "password": "test_password"
        }
        
        # 执行测试
        result = ConnectionTestService.test_connection(test_data)
        
        # 验证结果
        assert result.success == False
        assert "主机地址不能为空" in result.message
    
    def test_connection_test_missing_database_name(self):
        """测试连接测试缺少数据库名称"""
        # 准备测试数据
        test_data = {
            "db_type": DatabaseType.MYSQL,
            "host": "localhost",
            "port": 3306,
            "database_name": "",  # 空数据库名称
            "username": "test_user",
            "password": "test_password"
        }
        
        # 执行测试
        result = ConnectionTestService.test_connection(test_data)
        
        # 验证结果
        assert result.success == False
        assert "数据库名称不能为空" in result.message
    
    def test_connection_test_missing_username(self):
        """测试连接测试缺少用户名"""
        # 准备测试数据
        test_data = {
            "db_type": DatabaseType.MYSQL,
            "host": "localhost",
            "port": 3306,
            "database_name": "test_db",
            "username": "",  # 空用户名
            "password": "test_password"
        }
        
        # 执行测试
        result = ConnectionTestService.test_connection(test_data)
        
        # 验证结果
        assert result.success == False
        assert "用户名不能为空" in result.message
    
    def test_connection_test_missing_password(self):
        """测试连接测试缺少密码"""
        # 准备测试数据
        test_data = {
            "db_type": DatabaseType.MYSQL,
            "host": "localhost",
            "port": 3306,
            "database_name": "test_db",
            "username": "test_user",
            "password": ""  # 空密码
        }
        
        # 执行测试
        result = ConnectionTestService.test_connection(test_data)
        
        # 验证结果
        assert result.success == False
        assert "密码不能为空" in result.message
    
    def test_has_related_tables_true(self):
        """测试数据源有关联数据表"""
        # 准备测试数据
        source_id = str(uuid.uuid4())
        
        # 模拟查询返回关联数据表
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = Mock()  # 返回非None表示有关联
        self.mock_db.query.return_value = mock_query
        
        # 执行测试
        result = self.service.has_related_tables(self.mock_db, source_id)
        
        # 验证结果
        assert result == True
    
    def test_has_related_tables_false(self):
        """测试数据源无关联数据表"""
        # 准备测试数据
        source_id = str(uuid.uuid4())
        
        # 模拟查询返回None
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = None
        self.mock_db.query.return_value = mock_query
        
        # 执行测试
        result = self.service.has_related_tables(self.mock_db, source_id)
        
        # 验证结果
        assert result == False
    
    def test_activate_data_source(self):
        """测试激活数据源"""
        # 准备测试数据
        source_id = str(uuid.uuid4())
        mock_source = DataSource(
            id=source_id,
            name="测试数据源",
            status=False,  # 初始状态为禁用
            created_by="test_user"
        )
        
        # 模拟数据库查询
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = mock_source
        self.mock_db.query.return_value = mock_query
        self.mock_db.commit.return_value = None
        self.mock_db.refresh.return_value = None
        
        # 执行测试
        result = self.service.activate_source(self.mock_db, source_id)
        
        # 验证结果
        assert result == True
        assert mock_source.status == True
        
        # 验证数据库操作被调用
        self.mock_db.commit.assert_called_once()
        self.mock_db.refresh.assert_called_once()
    
    def test_deactivate_data_source(self):
        """测试禁用数据源"""
        # 准备测试数据
        source_id = str(uuid.uuid4())
        mock_source = DataSource(
            id=source_id,
            name="测试数据源",
            status=True,  # 初始状态为启用
            created_by="test_user"
        )
        
        # 模拟数据库查询
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = mock_source
        self.mock_db.query.return_value = mock_query
        self.mock_db.commit.return_value = None
        self.mock_db.refresh.return_value = None
        
        # 执行测试
        result = self.service.deactivate_source(self.mock_db, source_id)
        
        # 验证结果
        assert result == True
        assert mock_source.status == False
        
        # 验证数据库操作被调用
        self.mock_db.commit.assert_called_once()
        self.mock_db.refresh.assert_called_once()


class TestDataSourceValidation:
    """数据源验证测试类"""
    
    def test_sql_server_auth_type_validation(self):
        """测试SQL Server认证方式验证"""
        # 测试SQL Server必须提供认证方式
        try:
            DataSourceCreate(
                name="SQL Server数据源",
                source_type="DATABASE",
                db_type=DatabaseType.SQL_SERVER,
                host="localhost",
                port=1433,
                database_name="test_db",
                username="test_user",
                password="TestPassword123!",
                created_by="test_user"
                # 缺少auth_type
            )
            # 如果没有抛出异常，测试失败
            assert False, "Expected ValueError was not raised"
        except ValueError as e:
            assert "当数据库类型为SQL Server时，认证方式为必填项" in str(e)
    
    def test_password_length_validation(self):
        """测试密码长度验证"""
        # 测试密码长度不足
        with pytest.raises(ValueError, match="密码长度不能少于8位"):
            DataSourceCreate(
                name="测试数据源",
                source_type="DATABASE",
                db_type=DatabaseType.MYSQL,
                host="localhost",
                port=3306,
                database_name="test_db",
                auth_type=AuthType.SQL_AUTH,
                username="test_user",
                password="short",  # 密码长度不足
                created_by="test_user"
            )
    
    def test_valid_mysql_data_source(self):
        """测试有效的MySQL数据源创建"""
        # 创建有效的MySQL数据源
        source = DataSourceCreate(
            name="有效的MySQL数据源",
            source_type="DATABASE",
            db_type=DatabaseType.MYSQL,
            host="localhost",
            port=3306,
            database_name="chatbi_db",
            auth_type=AuthType.SQL_AUTH,
            username="chatbi_user",
            password="ChatBI123!",
            description="有效的ChatBI MySQL数据源",
            status=True,
            created_by="test_user"
        )
        
        # 验证创建成功
        assert source.name == "有效的MySQL数据源"
        assert source.db_type == DatabaseType.MYSQL
        assert source.host == "localhost"
        assert source.port == 3306
        assert source.database_name == "chatbi_db"
        assert source.username == "chatbi_user"
        assert source.password == "ChatBI123!"
    
    def test_valid_sql_server_data_source(self):
        """测试有效的SQL Server数据源创建"""
        # 创建有效的SQL Server数据源
        source = DataSourceCreate(
            name="有效的SQL Server数据源",
            source_type="DATABASE",
            db_type=DatabaseType.SQL_SERVER,
            host="localhost",
            port=1433,
            database_name="ChatBI_DB",
            auth_type=AuthType.SQL_AUTH,
            username="chatbi_user",
            password="ChatBI123!",
            description="有效的ChatBI SQL Server数据源",
            status=True,
            created_by="test_user"
        )
        
        # 验证创建成功
        assert source.name == "有效的SQL Server数据源"
        assert source.db_type == DatabaseType.SQL_SERVER
        assert source.host == "localhost"
        assert source.port == 1433
        assert source.database_name == "ChatBI_DB"
        assert source.auth_type == AuthType.SQL_AUTH
        assert source.username == "chatbi_user"
        assert source.password == "ChatBI123!"