"""
数据源模块集成测试

测试数据源连接、CRUD操作和错误处理的完整流程
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, AsyncMock
from src.main import app
from src.models.data_source_model import DataSource
from src.database import get_db
from sqlalchemy.orm import Session
from datetime import datetime


class TestDataSourceIntegration:
    """数据源集成测试类"""
    
    def setup_method(self):
        """测试前置设置"""
        self.client = TestClient(app)
        self.test_data_source = {
            "name": "集成测试数据源",
            "source_type": "DATABASE",
            "db_type": "MySQL",
            "host": "localhost",
            "port": 3306,
            "database_name": "test_db",
            "username": "test_user",
            "password": "test_password",
            "description": "用于集成测试的数据源"
        }
    
    @patch('src.services.data_source_service.data_source_service')
    def test_create_data_source_integration(self, mock_service):
        """测试创建数据源的完整流程"""
        # 模拟创建成功的数据源
        mock_created_source = Mock()
        mock_created_source.id = "test-id-123"
        mock_created_source.name = self.test_data_source["name"]
        mock_created_source.source_type = self.test_data_source["source_type"]
        mock_created_source.db_type = self.test_data_source["db_type"]
        mock_created_source.host = self.test_data_source["host"]
        mock_created_source.port = self.test_data_source["port"]
        mock_created_source.database_name = self.test_data_source["database_name"]
        mock_created_source.username = self.test_data_source["username"]
        mock_created_source.description = self.test_data_source["description"]
        mock_created_source.status = True
        mock_created_source.created_at = datetime.now()
        mock_created_source.updated_at = datetime.now()
        
        mock_service.create_data_source.return_value = mock_created_source
        
        # 发送创建请求
        response = self.client.post("/api/data-sources/", json=self.test_data_source)
        
        # 验证响应
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == self.test_data_source["name"]
        assert data["db_type"] == self.test_data_source["db_type"]
        assert data["host"] == self.test_data_source["host"]
        assert data["port"] == self.test_data_source["port"]
        
        # 验证服务调用
        mock_service.create_data_source.assert_called_once()
    
    @patch('src.services.data_source_service.data_source_service')
    def test_connection_test_integration(self, mock_service):
        """测试连接测试的完整流程"""
        # 模拟连接测试成功
        mock_service.test_connection.return_value = {
            "success": True,
            "message": "连接测试成功",
            "response_time": 0.5
        }
        
        # 发送连接测试请求
        response = self.client.post("/api/data-sources/test-connection", json=self.test_data_source)
        
        # 验证响应
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "连接测试成功" in data["message"]
        assert "response_time" in data
        
        # 验证服务调用
        mock_service.test_connection.assert_called_once()
    
    @patch('src.services.data_source_service.data_source_service')
    def test_connection_test_failure_integration(self, mock_service):
        """测试连接测试失败的完整流程"""
        # 模拟连接测试失败
        mock_service.test_connection.return_value = {
            "success": False,
            "message": "连接超时",
            "error_code": "CONNECTION_TIMEOUT"
        }
        
        # 发送连接测试请求
        response = self.client.post("/api/data-sources/test-connection", json=self.test_data_source)
        
        # 验证响应
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert "连接超时" in data["message"]
        assert data["error_code"] == "CONNECTION_TIMEOUT"
    
    @patch('src.services.data_source_service.data_source_service')
    def test_get_data_sources_with_pagination(self, mock_service):
        """测试分页获取数据源列表"""
        # 创建模拟数据源列表
        mock_sources = []
        for i in range(15):
            mock_source = Mock()
            mock_source.id = f"test-id-{i}"
            mock_source.name = f"测试数据源{i}"
            mock_source.source_type = "DATABASE"
            mock_source.db_type = "MySQL"
            mock_source.host = "localhost"
            mock_source.port = 3306
            mock_source.database_name = f"test_db_{i}"
            mock_source.username = "test_user"
            mock_source.status = True
            mock_source.created_at = datetime.now()
            mock_source.updated_at = datetime.now()
            mock_sources.append(mock_source)
        
        # 模拟分页返回
        mock_service.get_all_sources.return_value = (mock_sources[:10], 15)
        
        # 发送分页请求
        response = self.client.get("/api/data-sources/?page=1&size=10")
        
        # 验证响应
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 10
        assert data["total"] == 15
        
        # 验证第二页
        mock_service.get_all_sources.return_value = (mock_sources[10:], 15)
        response = self.client.get("/api/data-sources/?page=2&size=10")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 5
        assert data["total"] == 15
    
    @patch('src.services.data_source_service.data_source_service')
    def test_update_data_source_integration(self, mock_service):
        """测试更新数据源的完整流程"""
        # 模拟更新后的数据源
        updated_data = self.test_data_source.copy()
        updated_data["name"] = "更新后的数据源名称"
        updated_data["description"] = "更新后的描述"
        
        mock_updated_source = Mock()
        mock_updated_source.id = "test-id-123"
        mock_updated_source.name = updated_data["name"]
        mock_updated_source.description = updated_data["description"]
        mock_updated_source.source_type = updated_data["source_type"]
        mock_updated_source.db_type = updated_data["db_type"]
        mock_updated_source.host = updated_data["host"]
        mock_updated_source.port = updated_data["port"]
        mock_updated_source.database_name = updated_data["database_name"]
        mock_updated_source.username = updated_data["username"]
        mock_updated_source.status = True
        mock_updated_source.created_at = datetime.now()
        mock_updated_source.updated_at = datetime.now()
        
        mock_service.update_data_source.return_value = mock_updated_source
        
        # 发送更新请求
        response = self.client.put("/api/data-sources/test-id-123", json=updated_data)
        
        # 验证响应
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == updated_data["name"]
        assert data["description"] == updated_data["description"]
        
        # 验证服务调用
        mock_service.update_data_source.assert_called_once_with("test-id-123", updated_data)
    
    @patch('src.services.data_source_service.data_source_service')
    def test_delete_data_source_integration(self, mock_service):
        """测试删除数据源的完整流程"""
        # 模拟删除成功
        mock_service.delete_data_source.return_value = True
        
        # 发送删除请求
        response = self.client.delete("/api/data-sources/test-id-123")
        
        # 验证响应
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "数据源删除成功"
        
        # 验证服务调用
        mock_service.delete_data_source.assert_called_once_with("test-id-123")
    
    @patch('src.services.data_source_service.data_source_service')
    def test_delete_nonexistent_data_source(self, mock_service):
        """测试删除不存在的数据源"""
        # 模拟数据源不存在
        mock_service.delete_data_source.side_effect = ValueError("数据源不存在")
        
        # 发送删除请求
        response = self.client.delete("/api/data-sources/nonexistent-id")
        
        # 验证响应
        assert response.status_code == 404
        data = response.json()
        assert "数据源不存在" in data["detail"]
    
    @patch('src.services.data_source_service.data_source_service')
    def test_get_data_source_by_id_integration(self, mock_service):
        """测试根据ID获取数据源"""
        # 模拟数据源
        mock_source = Mock()
        mock_source.id = "test-id-123"
        mock_source.name = self.test_data_source["name"]
        mock_source.source_type = self.test_data_source["source_type"]
        mock_source.db_type = self.test_data_source["db_type"]
        mock_source.host = self.test_data_source["host"]
        mock_source.port = self.test_data_source["port"]
        mock_source.database_name = self.test_data_source["database_name"]
        mock_source.username = self.test_data_source["username"]
        mock_source.description = self.test_data_source["description"]
        mock_source.status = True
        mock_source.created_at = datetime.now()
        mock_source.updated_at = datetime.now()
        
        mock_service.get_data_source_by_id.return_value = mock_source
        
        # 发送获取请求
        response = self.client.get("/api/data-sources/test-id-123")
        
        # 验证响应
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "test-id-123"
        assert data["name"] == self.test_data_source["name"]
        assert data["db_type"] == self.test_data_source["db_type"]
    
    @patch('src.services.data_source_service.data_source_service')
    def test_error_handling_integration(self, mock_service):
        """测试错误处理集成"""
        # 模拟服务异常
        mock_service.create_data_source.side_effect = Exception("数据库连接失败")
        
        # 发送创建请求
        response = self.client.post("/api/data-sources/", json=self.test_data_source)
        
        # 验证错误响应
        assert response.status_code == 500
        data = response.json()
        assert "数据库连接失败" in data["detail"]
    
    @patch('src.services.connection_pool_manager.ConnectionPoolManager')
    def test_connection_pool_integration(self, mock_pool_manager):
        """测试连接池集成"""
        # 模拟连接池管理器
        mock_pool = Mock()
        mock_pool.get_pool_status.return_value = {
            "active_connections": 5,
            "idle_connections": 3,
            "total_connections": 8,
            "max_connections": 20
        }
        mock_pool_manager.return_value = mock_pool
        
        # 发送连接池状态请求
        response = self.client.get("/api/data-sources/test-id-123/pool-status")
        
        # 验证响应
        assert response.status_code == 200
        data = response.json()
        assert data["active_connections"] == 5
        assert data["idle_connections"] == 3
        assert data["total_connections"] == 8
        assert data["max_connections"] == 20


if __name__ == "__main__":
    pytest.main([__file__, "-v"])