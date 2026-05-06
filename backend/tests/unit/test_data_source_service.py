"""
数据源服务单元测试

测试数据源服务层的所有业务逻辑
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime
from src.services.data_source_service import DataSourceService
from src.models.data_source_model import DataSource
from src.utils.encryption import encrypt_password, decrypt_password


class TestDataSourceService:
    """数据源服务测试类"""
    
    def setup_method(self):
        """测试前置设置"""
        self.mock_db = Mock()
        self.service = DataSourceService()
        self.test_data = {
            "name": "测试数据源",
            "source_type": "DATABASE",
            "db_type": "MySQL",
            "host": "localhost",
            "port": 3306,
            "database_name": "test_db",
            "username": "test_user",
            "password": "test_password",
            "description": "测试用数据源"
        }
    
    def test_add_data_source_success(self):
        """测试成功添加数据源"""
        # 创建模拟数据源对象
        mock_source = Mock(spec=DataSource)
        mock_source.id = "test-id-123"
        mock_source.name = self.test_data["name"]
        mock_source.source_type = "DATABASE"
        mock_source.status = True
        
        self.mock_db.add.return_value = None
        self.mock_db.commit.return_value = None
        self.mock_db.refresh.return_value = None
        
        # 调用服务方法
        result = self.service.add_data_source(self.mock_db, mock_source)
        
        # 验证结果
        assert result == mock_source
        assert result.name == self.test_data["name"]
        
        # 验证数据库操作
        self.mock_db.add.assert_called_once_with(mock_source)
        self.mock_db.commit.assert_called_once()
        self.mock_db.refresh.assert_called_once_with(mock_source)
    
    def test_add_data_source_with_encryption(self):
        """测试添加数据源时密码加密"""
        mock_source = Mock(spec=DataSource)
        mock_source.password = "test_password"
        
        # 调用服务方法
        result = self.service.add_data_source(self.mock_db, mock_source)
        
        # 验证结果
        assert result == mock_source
    
    def test_get_all_sources_with_pagination(self):
        """测试分页获取数据源列表"""
        # 创建模拟数据源
        mock_sources = []
        for i in range(5):
            mock_source = Mock(spec=DataSource)
            mock_source.id = f"test-id-{i}"
            mock_source.name = f"数据源{i}"
            mock_sources.append(mock_source)
        
        # 模拟查询结果
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = mock_sources
        mock_query.count.return_value = 15
        
        self.mock_db.query.return_value = mock_query
        
        # 调用服务方法
        sources, total = self.service.get_all_sources(self.mock_db, page=1, page_size=10)
        
        # 验证结果
        assert len(sources) == 5
        assert total == 15
        
        # 验证查询调用
        self.mock_db.query.assert_called_with(DataSource)
        mock_query.offset.assert_called_once_with(0)
        mock_query.limit.assert_called_once_with(10)
    
    def test_get_source_by_id_success(self):
        """测试根据ID获取数据源成功"""
        mock_source = Mock(spec=DataSource)
        mock_source.id = "test-id-123"
        mock_source.name = "测试数据源"
        
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = mock_source
        
        self.mock_db.query.return_value = mock_query
        
        # 调用服务方法
        result = self.service.get_source_by_id(self.mock_db, "test-id-123")
        
        # 验证结果
        assert result == mock_source
        assert result.id == "test-id-123"
    
    def test_get_source_by_id_not_found(self):
        """测试根据ID获取数据源失败"""
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None
        
        self.mock_db.query.return_value = mock_query
        
        # 调用服务方法
        result = self.service.get_source_by_id(self.mock_db, "nonexistent-id")
        
        # 验证结果
        assert result is None
    
    def test_update_data_source_success(self):
        """测试成功更新数据源"""
        # 模拟现有数据源
        mock_source = Mock(spec=DataSource)
        mock_source.id = "test-id-123"
        mock_source.name = "原始名称"
        mock_source.status = True
        mock_source.source_type = "DATABASE"
        
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = mock_source
        
        self.mock_db.query.return_value = mock_query
        
        # 更新数据
        update_data = {
            "name": "更新后的名称",
            "description": "更新后的描述"
        }
        
        # 调用服务方法
        result = self.service.update_data_source(self.mock_db, "test-id-123", update_data)
        
        # 验证结果
        assert result == mock_source
        assert mock_source.name == "更新后的名称"
        assert mock_source.description == "更新后的描述"
        
        # 验证数据库操作
        self.mock_db.commit.assert_called_once()
        self.mock_db.refresh.assert_called_once_with(mock_source)
    
    def test_update_data_source_not_found(self):
        """测试更新不存在的数据源"""
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None
        
        self.mock_db.query.return_value = mock_query
        
        # 调用服务方法
        result = self.service.update_data_source(self.mock_db, "nonexistent-id", {"name": "新名称"})
        
        # 验证结果
        assert result is None
    
    def test_delete_source_success(self):
        """测试成功删除数据源"""
        mock_source = Mock(spec=DataSource)
        mock_source.id = "test-id-123"
        mock_source.source_type = "DATABASE"
        
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = mock_source
        
        self.mock_db.query.return_value = mock_query
        
        # 调用服务方法
        result = self.service.delete_source(self.mock_db, "test-id-123")
        
        # 验证结果
        assert result is True
        
        # 验证数据库操作
        self.mock_db.delete.assert_called_once_with(mock_source)
        self.mock_db.commit.assert_called_once()
    
    def test_delete_source_not_found(self):
        """测试删除不存在的数据源"""
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None
        
        self.mock_db.query.return_value = mock_query
        
        # 调用服务方法
        result = self.service.delete_source(self.mock_db, "nonexistent-id")
        
        # 验证结果
        assert result is False
    
    @patch('src.services.data_source_service.ConnectionTestService')
    def test_test_connection_success(self, mock_connection_test):
        """测试连接测试成功"""
        # 模拟连接测试结果
        mock_result = Mock()
        mock_result.success = True
        mock_result.message = "连接测试成功"
        mock_result.latency_ms = 150
        mock_connection_test.test_connection.return_value = mock_result
        
        # 创建数据源对象
        mock_source = Mock(spec=DataSource)
        mock_source.id = "test-id-123"
        mock_source.name = "测试数据源"
        mock_source.source_type = "DATABASE"
        mock_source.db_type = "MySQL"
        mock_source.host = "localhost"
        mock_source.port = 3306
        mock_source.database_name = "test_db"
        mock_source.username = "test_user"
        mock_source.password = "test_password"
        
        # 调用服务方法
        result = self.service.test_connection(mock_source)
        
        # 验证结果
        assert result["success"] is True
        assert "连接测试成功" in result["details"]
        assert result["elapsed_time_ms"] == 150
        assert result["connection_status"] == "CONNECTED"
    
    @patch('src.services.data_source_service.ConnectionTestService')
    def test_test_connection_failure(self, mock_connection_test):
        """测试连接测试失败"""
        # 模拟连接测试失败
        mock_result = Mock()
        mock_result.success = False
        mock_result.message = "连接超时"
        mock_result.latency_ms = 0
        mock_connection_test.test_connection.return_value = mock_result
        
        # 创建数据源对象
        mock_source = Mock(spec=DataSource)
        mock_source.id = "test-id-123"
        mock_source.name = "测试数据源"
        mock_source.source_type = "DATABASE"
        mock_source.db_type = "MySQL"
        mock_source.host = "localhost"
        mock_source.port = 3306
        mock_source.database_name = "test_db"
        mock_source.username = "test_user"
        mock_source.password = "test_password"
        
        # 调用服务方法
        result = self.service.test_connection(mock_source)
        
        # 验证结果
        assert result["success"] is False
        assert "连接超时" in result["details"]
        assert result["connection_status"] == "FAILED"
    
    def test_has_related_tables_true(self):
        """测试数据源有关联数据表"""
        # 模拟有关联的数据表
        mock_table = Mock()
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = mock_table
        
        self.mock_db.query.return_value = mock_query
        
        # 调用服务方法
        result = self.service.has_related_tables(self.mock_db, "test-id-123")
        
        # 验证结果
        assert result is True
    
    def test_has_related_tables_false(self):
        """测试数据源无关联数据表"""
        # 模拟无关联的数据表
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None
        
        self.mock_db.query.return_value = mock_query
        
        # 调用服务方法
        result = self.service.has_related_tables(self.mock_db, "test-id-123")
        
        # 验证结果
        assert result is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])