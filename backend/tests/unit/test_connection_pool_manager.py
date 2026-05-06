"""
连接池管理器单元测试

测试连接池的创建、管理、监控和健康检查功能
"""

import pytest
import uuid
from unittest.mock import Mock, patch, MagicMock
from src.services.connection_pool_manager import (
    ConnectionPoolManager,
    ConnectionPoolConfig,
    ConnectionPoolStats,
    ConnectionPoolStatus
)


class TestConnectionPoolManager:
    """连接池管理器测试类"""
    
    def setup_method(self):
        """测试前准备"""
        self.manager = ConnectionPoolManager()
        self.mysql_config = ConnectionPoolConfig(
            pool_id=str(uuid.uuid4()),
            db_type="MySQL",
            host="localhost",
            port=3306,
            database_name="test_db",
            username="test_user",
            password="test_password",
            min_connections=5,
            max_connections=20
        )
        self.sql_server_config = ConnectionPoolConfig(
            pool_id=str(uuid.uuid4()),
            db_type="SQL Server",
            host="localhost",
            port=1433,
            database_name="TestDB",
            username="test_user",
            password="test_password",
            min_connections=5,
            max_connections=20
        )
    
    def test_create_mysql_pool_success(self):
        """测试创建MySQL连接池成功"""
        with patch('mysql.connector.pooling.MySQLConnectionPool') as mock_pool:
            mock_pool.return_value = Mock()
            
            # 执行测试
            result = self.manager.create_pool(self.mysql_config)
            
            # 验证结果
            assert result == True
            assert self.mysql_config.pool_id in self.manager._pools
            assert self.mysql_config.pool_id in self.manager._pool_configs
            assert self.mysql_config.pool_id in self.manager._pool_stats
            
            # 验证连接池创建被调用
            mock_pool.assert_called_once()
    
    def test_create_sql_server_pool_success(self):
        """测试创建SQL Server连接池成功"""
        # 执行测试
        result = self.manager.create_pool(self.sql_server_config)
        
        # 验证结果
        assert result == True
        assert self.sql_server_config.pool_id in self.manager._pools
        assert self.sql_server_config.pool_id in self.manager._pool_configs
        assert self.sql_server_config.pool_id in self.manager._pool_stats
    
    def test_create_pool_duplicate_id(self):
        """测试创建重复ID的连接池"""
        with patch('mysql.connector.pooling.MySQLConnectionPool') as mock_pool:
            mock_pool.return_value = Mock()
            
            # 先创建一个连接池
            result1 = self.manager.create_pool(self.mysql_config)
            assert result1 == True
            
            # 尝试创建相同ID的连接池
            result2 = self.manager.create_pool(self.mysql_config)
            assert result2 == False
    
    def test_create_pool_unsupported_db_type(self):
        """测试创建不支持的数据库类型连接池"""
        unsupported_config = ConnectionPoolConfig(
            pool_id=str(uuid.uuid4()),
            db_type="PostgreSQL",  # 不支持的类型
            host="localhost",
            port=5432,
            database_name="test_db",
            username="test_user",
            password="test_password"
        )
        
        # 执行测试
        result = self.manager.create_pool(unsupported_config)
        
        # 验证结果
        assert result == False
        assert unsupported_config.pool_id not in self.manager._pools
    
    def test_get_mysql_connection_success(self):
        """测试获取MySQL连接成功"""
        with patch('mysql.connector.pooling.MySQLConnectionPool') as mock_pool_class:
            mock_pool = Mock()
            mock_connection = Mock()
            mock_pool.get_connection.return_value = mock_connection
            mock_pool_class.return_value = mock_pool
            
            # 创建连接池
            self.manager.create_pool(self.mysql_config)
            
            # 获取连接
            with self.manager.get_connection(self.mysql_config.pool_id) as connection:
                assert connection == mock_connection
            
            # 验证连接获取和释放被调用
            mock_pool.get_connection.assert_called_once()
            mock_connection.close.assert_called_once()
    
    def test_get_sql_server_connection_success(self):
        """测试获取SQL Server连接成功"""
        # 创建连接池
        self.manager.create_pool(self.sql_server_config)
        
        # 模拟pyodbc.connect
        with patch.object(self.manager, '_get_sql_server_connection') as mock_get_conn:
            mock_connection = Mock()
            mock_get_conn.return_value = mock_connection
            
            # 获取连接
            with self.manager.get_connection(self.sql_server_config.pool_id) as connection:
                assert connection == mock_connection
            
            # 验证连接获取被调用
            mock_get_conn.assert_called_once()
    
    def test_get_connection_pool_not_found(self):
        """测试获取不存在连接池的连接"""
        non_existent_id = str(uuid.uuid4())
        
        # 执行测试并验证异常
        with pytest.raises(ValueError, match="Connection pool .* not found"):
            with self.manager.get_connection(non_existent_id):
                pass
    
    def test_check_mysql_pool_health_success(self):
        """测试MySQL连接池健康检查成功"""
        with patch('mysql.connector.pooling.MySQLConnectionPool') as mock_pool_class:
            mock_pool = Mock()
            mock_connection = Mock()
            mock_cursor = Mock()
            
            # 设置模拟对象
            mock_pool.get_connection.return_value = mock_connection
            mock_connection.cursor.return_value = mock_cursor
            mock_cursor.fetchone.return_value = (1,)
            mock_pool_class.return_value = mock_pool
            
            # 创建连接池
            self.manager.create_pool(self.mysql_config)
            
            # 执行健康检查
            result = self.manager.check_pool_health(self.mysql_config.pool_id)
            
            # 验证结果
            assert result == True
            
            # 验证统计信息更新
            stats = self.manager.get_pool_stats(self.mysql_config.pool_id)
            assert stats.status == ConnectionPoolStatus.HEALTHY
    
    def test_check_pool_health_failure(self):
        """测试连接池健康检查失败"""
        with patch('mysql.connector.pooling.MySQLConnectionPool') as mock_pool_class:
            mock_pool = Mock()
            mock_pool.get_connection.side_effect = Exception("Connection failed")
            mock_pool_class.return_value = mock_pool
            
            # 创建连接池
            self.manager.create_pool(self.mysql_config)
            
            # 执行健康检查
            result = self.manager.check_pool_health(self.mysql_config.pool_id)
            
            # 验证结果
            assert result == False
            
            # 验证统计信息更新
            stats = self.manager.get_pool_stats(self.mysql_config.pool_id)
            assert stats.status == ConnectionPoolStatus.FAILED
    
    def test_get_pool_stats_success(self):
        """测试获取连接池统计信息成功"""
        with patch('mysql.connector.pooling.MySQLConnectionPool') as mock_pool:
            mock_pool.return_value = Mock()
            
            # 创建连接池
            self.manager.create_pool(self.mysql_config)
            
            # 获取统计信息
            stats = self.manager.get_pool_stats(self.mysql_config.pool_id)
            
            # 验证结果
            assert stats is not None
            assert stats.pool_id == self.mysql_config.pool_id
            assert stats.db_type == self.mysql_config.db_type
            assert stats.status == ConnectionPoolStatus.INITIALIZING
    
    def test_get_pool_stats_not_found(self):
        """测试获取不存在连接池的统计信息"""
        non_existent_id = str(uuid.uuid4())
        
        # 执行测试
        stats = self.manager.get_pool_stats(non_existent_id)
        
        # 验证结果
        assert stats is None
    
    def test_get_all_pool_stats(self):
        """测试获取所有连接池统计信息"""
        with patch('mysql.connector.pooling.MySQLConnectionPool') as mock_pool:
            mock_pool.return_value = Mock()
            
            # 创建多个连接池
            self.manager.create_pool(self.mysql_config)
            
            sql_server_config2 = ConnectionPoolConfig(
                pool_id=str(uuid.uuid4()),
                db_type="SQL Server",
                host="localhost",
                port=1433,
                database_name="TestDB2",
                username="test_user",
                password="test_password"
            )
            self.manager.create_pool(sql_server_config2)
            
            # 获取所有统计信息
            all_stats = self.manager.get_all_pool_stats()
            
            # 验证结果
            assert len(all_stats) == 2
            assert self.mysql_config.pool_id in all_stats
            assert sql_server_config2.pool_id in all_stats
    
    def test_remove_pool_success(self):
        """测试移除连接池成功"""
        with patch('mysql.connector.pooling.MySQLConnectionPool') as mock_pool:
            mock_pool.return_value = Mock()
            
            # 创建连接池
            self.manager.create_pool(self.mysql_config)
            assert self.mysql_config.pool_id in self.manager._pools
            
            # 移除连接池
            result = self.manager.remove_pool(self.mysql_config.pool_id)
            
            # 验证结果
            assert result == True
            assert self.mysql_config.pool_id not in self.manager._pools
            assert self.mysql_config.pool_id not in self.manager._pool_configs
            assert self.mysql_config.pool_id not in self.manager._pool_stats
    
    def test_remove_pool_not_found(self):
        """测试移除不存在的连接池"""
        non_existent_id = str(uuid.uuid4())
        
        # 执行测试
        result = self.manager.remove_pool(non_existent_id)
        
        # 验证结果
        assert result == False
    
    def test_monitoring_control(self):
        """测试监控控制功能"""
        # 测试启动监控
        self.manager.start_monitoring()
        assert self.manager._monitoring_enabled == True
        
        # 测试停止监控
        self.manager.stop_monitoring()
        assert self.manager._monitoring_enabled == False


class TestConnectionPoolConfig:
    """连接池配置测试类"""
    
    def test_connection_pool_config_creation(self):
        """测试连接池配置创建"""
        config = ConnectionPoolConfig(
            pool_id="test-pool",
            db_type="MySQL",
            host="localhost",
            port=3306,
            database_name="test_db",
            username="test_user",
            password="test_password",
            min_connections=5,
            max_connections=20,
            connection_timeout=30,
            idle_timeout=300
        )
        
        # 验证配置
        assert config.pool_id == "test-pool"
        assert config.db_type == "MySQL"
        assert config.host == "localhost"
        assert config.port == 3306
        assert config.database_name == "test_db"
        assert config.username == "test_user"
        assert config.password == "test_password"
        assert config.min_connections == 5
        assert config.max_connections == 20
        assert config.connection_timeout == 30
        assert config.idle_timeout == 300


class TestConnectionPoolStats:
    """连接池统计信息测试类"""
    
    def test_connection_pool_stats_creation(self):
        """测试连接池统计信息创建"""
        stats = ConnectionPoolStats(
            pool_id="test-pool",
            db_type="MySQL",
            total_connections=10,
            active_connections=5,
            idle_connections=5,
            failed_connections=0,
            status=ConnectionPoolStatus.HEALTHY,
            last_check_time=1234567890.0,
            average_response_time=50.0,
            error_rate=0.01
        )
        
        # 验证统计信息
        assert stats.pool_id == "test-pool"
        assert stats.db_type == "MySQL"
        assert stats.total_connections == 10
        assert stats.active_connections == 5
        assert stats.idle_connections == 5
        assert stats.failed_connections == 0
        assert stats.status == ConnectionPoolStatus.HEALTHY
        assert stats.last_check_time == 1234567890.0
        assert stats.average_response_time == 50.0
        assert stats.error_rate == 0.01