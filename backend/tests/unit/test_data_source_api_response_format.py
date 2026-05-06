"""
数据源 API 响应格式测试

验证 API 返回正确的 {data: [], total: 0} 格式
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch
from src.main import app
from src.schemas.data_source_schema import DataSourceListResponse


class TestDataSourceAPIResponseFormat:
    """数据源 API 响应格式测试类"""
    
    def setup_method(self):
        """测试前置设置"""
        self.client = TestClient(app)
    
    @patch('src.api.data_source_api.data_source_service')
    def test_get_data_sources_empty_list_format(self, mock_service):
        """测试空数据源列表的响应格式"""
        # 模拟服务返回空列表
        mock_service.get_all_sources.return_value = ([], 0)
        
        # 调用 API
        response = self.client.get("/api/datasources/")
        
        # 验证响应状态
        assert response.status_code == 200
        
        # 验证响应格式
        data = response.json()
        assert isinstance(data, dict), "响应应该是字典类型"
        assert "data" in data, "响应应该包含 data 字段"
        assert "total" in data, "响应应该包含 total 字段"
        assert isinstance(data["data"], list), "data 字段应该是数组类型"
        assert isinstance(data["total"], int), "total 字段应该是整数类型"
        assert data["data"] == [], "空列表时 data 应该是空数组"
        assert data["total"] == 0, "空列表时 total 应该是 0"
    
    @patch('src.api.data_source_api.data_source_service')
    def test_get_data_sources_with_data_format(self, mock_service):
        """测试有数据时的响应格式"""
        # 创建模拟数据源
        from datetime import datetime
        mock_source = Mock()
        mock_source.id = "test-id"
        mock_source.name = "测试数据源"
        mock_source.source_type = "DATABASE"
        mock_source.db_type = "MySQL"
        mock_source.host = "localhost"
        mock_source.port = 3306
        mock_source.database_name = "test_db"
        mock_source.auth_type = None
        mock_source.username = "test_user"
        mock_source.domain = None
        mock_source.file_path = None
        mock_source.connection_status = None
        mock_source.last_test_time = None
        mock_source.description = None
        mock_source.status = True
        mock_source.created_by = "test_user"
        mock_source.created_at = datetime.now()  # 修复：提供有效的 datetime 对象
        mock_source.updated_at = datetime.now()  # 修复：提供有效的 datetime 对象
        
        # 模拟服务返回数据
        mock_service.get_all_sources.return_value = ([mock_source], 1)
        
        # 调用 API
        response = self.client.get("/api/datasources/")
        
        # 验证响应状态
        assert response.status_code == 200
        
        # 验证响应格式
        data = response.json()
        assert isinstance(data, dict), "响应应该是字典类型"
        assert "data" in data, "响应应该包含 data 字段"
        assert "total" in data, "响应应该包含 total 字段"
        assert isinstance(data["data"], list), "data 字段应该是数组类型"
        assert isinstance(data["total"], int), "total 字段应该是整数类型"
        assert len(data["data"]) == 1, "应该返回 1 个数据源"
        assert data["total"] == 1, "total 应该是 1"
        
        # 验证数据源对象结构
        source_data = data["data"][0]
        assert isinstance(source_data, dict), "数据源对象应该是字典类型"
        assert "id" in source_data, "数据源应该包含 id 字段"
        assert "name" in source_data, "数据源应该包含 name 字段"
        assert source_data["name"] == "测试数据源", "数据源名称应该正确"
    
    def test_data_source_list_response_schema(self):
        """测试 DataSourceListResponse 模式定义"""
        # 测试空响应
        empty_response = DataSourceListResponse(data=[], total=0)
        assert empty_response.data == []
        assert empty_response.total == 0
        
        # 测试序列化
        serialized = empty_response.model_dump()
        assert serialized == {"data": [], "total": 0}
        
        # 验证字段类型
        assert isinstance(empty_response.data, list)
        assert isinstance(empty_response.total, int)
    
    @patch('src.api.data_source_api.data_source_service')
    def test_compatibility_api_response_format(self, mock_service):
        """测试兼容性 API 的响应格式"""
        # 模拟服务返回空列表
        mock_service.get_all_sources.return_value = ([], 0)
        
        # 调用兼容性 API
        response = self.client.get("/api/datasources/")
        
        # 验证响应状态
        assert response.status_code == 200
        
        # 验证响应格式与主 API 一致
        data = response.json()
        assert isinstance(data, dict), "兼容性 API 响应应该是字典类型"
        assert "data" in data, "兼容性 API 响应应该包含 data 字段"
        assert "total" in data, "兼容性 API 响应应该包含 total 字段"
        assert data["data"] == [], "兼容性 API 空列表时 data 应该是空数组"
        assert data["total"] == 0, "兼容性 API 空列表时 total 应该是 0"
    
    @patch('src.api.data_source_api.data_source_service')
    def test_main_api_response_format(self, mock_service):
        """测试主 API 的响应格式"""
        # 模拟服务返回空列表
        mock_service.get_all_sources.return_value = ([], 0)
        
        # 调用主 API
        response = self.client.get("/api/data-sources/")
        
        # 验证响应状态
        assert response.status_code == 200
        
        # 验证响应格式
        data = response.json()
        assert isinstance(data, dict), "主 API 响应应该是字典类型"
        assert "data" in data, "主 API 响应应该包含 data 字段"
        assert "total" in data, "主 API 响应应该包含 total 字段"
        assert data["data"] == [], "主 API 空列表时 data 应该是空数组"
        assert data["total"] == 0, "主 API 空列表时 total 应该是 0"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])