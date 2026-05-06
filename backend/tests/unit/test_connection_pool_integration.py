"""
连接池管理集成测试

测试连接池的创建、管理、监控和清理功能
"""
import pytest
from unittest.mock import Mock, patch
from src.services.connection_pool_manager import ConnectionPoolManager, ConnectionPoolConfig, ConnectionPoolStatus


class TestConnectionPoolIntegration:
    """连接池集成测试类"""
    
    def setup_method(self):
        """测试前置设置"""
        self.pool_manager = ConnectionPoolManager()
        self.data_source_id = "test-source-123"
    
    @patch('mysql.connector.pooling.MySQLConnectionPool')
    def test_create_pool_success(self, mock_mysql_pool):
        """测试成功创建连接池"""
        # 创建连接池配置
        config = ConnectionPoolConfig(
            pool_id=self.data_source_id,
            db_type="MySQL",
            host="localhost",
            port=3306,
            database_name="test_db",
            username="test_user",
            password="test_password"
        )
        
        mock_mysql_pool.return_value = Mock()
        
        # 创建连接池
        result = self.pool_manager.create_pool(config)
        
        # 验证结果
        assert result is True
        assert self.data_source_id in self.pool_manager._pools
    
    @patch('mysql.connector.pooling.MySQLConnectionPool')
    def test_create_pool_failure(self, mock_mysql_pool):
        """测试创建连接池失败"""
        # 创建连接池配置
        config = ConnectionPoolConfig(
            pool_id=self.data_source_id,
            db_type="MySQL",
            host="localhost",
            port=3306,
            database_name="test_db",
            username="test_user",
            password="test_password"
        )
        
        mock_mysql_pool.side_effect = Exception("数据库连接失败")
        
        # 创建连接池
        result = self.pool_manager.create_pool(config)
        
        # 验证结果
        assert result is False
        assert self.data_source_id not in self.pool_manager._pools
    
    @patch('mysql.connector.pooling.MySQLConnectionPool')
    def test_remove_pool_success(self, mock_mysql_pool):
        """测试成功移除连接池"""
        # 创建连接池配置
        config = ConnectionPoolConfig(
            pool_id=self.data_source_id,
            db_type="MySQL",
            host="localhost",
            port=3306,
            database_name="test_db",
            username="test_user",
            password="test_password"
        )
        
        mock_mysql_pool.return_value = Mock()
        
        # 先创建连接池
        self.pool_manager.create_pool(config)
        assert self.data_source_id in self.pool_manager._pools
        
        # 移除连接池
        result = self.pool_manager.remove_pool(self.data_source_id)
        
        # 验证结果
        assert result is True
        assert self.data_source_id not in self.pool_manager._pools
    
    def test_remove_pool_nonexistent(self):
        """测试移除不存在的连接池"""
        result = self.pool_manager.remove_pool("nonexistent-id")
        assert result is False
    
    def test_check_pool_health_nonexistent(self):
        """测试不存在连接池的健康检查"""
        result = self.pool_manager.check_pool_health("nonexistent-id")
        assert result is False
    
    @patch('mysql.connector.pooling.MySQLConnectionPool')
    def test_get_pool_stats_success(self, mock_mysql_pool):
        """测试获取连接池统计信息"""
        # 创建连接池配置
        config = ConnectionPoolConfig(
            pool_id=self.data_source_id,
            db_type="MySQL",
            host="localhost",
            port=3306,
            database_name="test_db",
            username="test_user",
            password="test_password"
        )
        
        mock_mysql_pool.return_value = Mock()
        
        # 创建连接池
        self.pool_manager.create_pool(config)
        
        # 获取统计信息
        stats = self.pool_manager.get_pool_stats(self.data_source_id)
        
        # 验证结果
        assert stats is not None
        assert stats.pool_id == self.data_source_id
        assert stats.db_type == "MySQL"
    
    def test_get_pool_stats_nonexistent(self):
        """测试获取不存在连接池的统计信息"""
        stats = self.pool_manager.get_pool_stats("nonexistent-id")
        assert stats is None
    
    @patch('mysql.connector.pooling.MySQLConnectionPool')
    def test_get_all_pool_stats(self, mock_mysql_pool):
        """测试获取所有连接池统计信息"""
        mock_mysql_pool.return_value = Mock()
        
        # 创建多个连接池
        for i in range(2):
            config = ConnectionPoolConfig(
                pool_id=f"source-{i}",
                db_type="MySQL",
                host="localhost",
                port=3306,
                database_name="test_db",
                username="test_user",
                password="test_password"
            )
            self.pool_manager.create_pool(config)
        
        # 获取所有统计信息
        all_stats = self.pool_manager.get_all_pool_stats()
        
        # 验证结果
        assert len(all_stats) == 2
        assert "source-0" in all_stats
        assert "source-1" in all_stats
    
    @patch('mysql.connector.pooling.MySQLConnectionPool')
    def test_connection_context_manager(self, mock_mysql_pool):
        """测试连接上下文管理器"""
        # 创建连接池配置
        config = ConnectionPoolConfig(
            pool_id=self.data_source_id,
            db_type="MySQL",
            host="localhost",
            port=3306,
            database_name="test_db",
            username="test_user",
            password="test_password"
        )
        
        # 模拟连接池和连接
        mock_connection = Mock()
        mock_pool = Mock()
        mock_pool.get_connection.return_value = mock_connection
        mock_mysql_pool.return_value = mock_pool
        
        # 创建连接池
        self.pool_manager.create_pool(config)
        
        # 使用连接上下文管理器
        with self.pool_manager.get_connection(self.data_source_id) as connection:
            assert connection == mock_connection
        
        # 验证连接被正确获取和释放
        mock_pool.get_connection.assert_called_once()
        mock_connection.close.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])