import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch
from sqlalchemy.orm import Session

from src.main import app
from src.services.semantic_injection_service import semantic_injection_service

client = TestClient(app)

class TestSemanticInjectionAPI:
    """语义注入API测试"""
    
    def setup_method(self):
        """测试前置设置"""
        self.mock_db = Mock(spec=Session)
    
    @patch('src.api.semantic_injection_api.get_db')
    @patch.object(semantic_injection_service, 'get_field_semantic_mapping')
    def test_get_field_semantic_mapping_success(self, mock_get_mapping, mock_get_db):
        """测试成功获取字段语义映射"""
        mock_get_db.return_value = self.mock_db
        mock_get_mapping.return_value = {
            'dictionary_id': 'dict_1',
            'dictionary_name': '用户状态字典',
            'dictionary_code': 'USER_STATUS',
            'field_mapping_id': 'mapping_1',
            'mapping_type': 'direct',
            'value_mappings': {
                '1': {'label': '激活', 'description': '用户已激活'},
                '0': {'label': '禁用', 'description': '用户已禁用'}
            },
            'metadata': {'description': '用户状态枚举'}
        }
        
        response = client.get("/api/semantic-injection/field-mapping/users/status")
        
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert data['message'] == "获取字段语义映射成功"
        assert data['data']['dictionary_name'] == '用户状态字典'
        assert data['data']['dictionary_code'] == 'USER_STATUS'
        assert '1' in data['data']['value_mappings']
        assert '0' in data['data']['value_mappings']
    
    @patch('src.api.semantic_injection_api.get_db')
    @patch.object(semantic_injection_service, 'get_field_semantic_mapping')
    def test_get_field_semantic_mapping_not_found(self, mock_get_mapping, mock_get_db):
        """测试获取不存在的字段语义映射"""
        mock_get_db.return_value = self.mock_db
        mock_get_mapping.return_value = None
        
        response = client.get("/api/semantic-injection/field-mapping/users/status")
        
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is False
        assert "未找到字段 users.status 的语义映射" in data['message']
        assert data['data'] is None
    
    @patch('src.api.semantic_injection_api.get_db')
    @patch.object(semantic_injection_service, 'inject_semantic_values')
    def test_inject_semantic_values_success(self, mock_inject, mock_get_db):
        """测试成功注入语义值"""
        mock_get_db.return_value = self.mock_db
        mock_inject.return_value = [
            {
                'id': 1,
                'status': 1,
                'name': 'test',
                '_semantic': {
                    'status_semantic': {
                        'original_value': 1,
                        'semantic_label': '激活',
                        'description': '用户已激活',
                        'dictionary_name': '用户状态字典'
                    }
                }
            }
        ]
        
        request_data = {
            "table_name": "users",
            "data": [{"id": 1, "status": 1, "name": "test"}]
        }
        
        response = client.post("/api/semantic-injection/inject", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert data['message'] == "语义值注入成功"
        assert len(data['data']) == 1
        assert '_semantic' in data['data'][0]
        assert 'status_semantic' in data['data'][0]['_semantic']
    
    @patch('src.api.semantic_injection_api.get_db')
    @patch.object(semantic_injection_service, 'get_table_semantic_schema')
    def test_get_table_semantic_schema_success(self, mock_get_schema, mock_get_db):
        """测试成功获取表语义模式"""
        mock_get_db.return_value = self.mock_db
        mock_get_schema.return_value = {
            'table_name': 'users',
            'semantic_fields': {
                'status': {
                    'dictionary_name': '用户状态字典',
                    'dictionary_code': 'USER_STATUS',
                    'mapping_type': 'direct',
                    'available_values': ['1', '0']
                }
            },
            'metadata': {
                'total_mapped_fields': 1,
                'generated_at': '2024-01-01T00:00:00'
            }
        }
        
        response = client.get("/api/semantic-injection/schema/users")
        
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert data['message'] == "获取表语义模式成功"
        assert data['data']['table_name'] == 'users'
        assert 'status' in data['data']['semantic_fields']
        assert data['data']['metadata']['total_mapped_fields'] == 1
    
    @patch.object(semantic_injection_service, 'clear_cache')
    def test_clear_semantic_cache_success(self, mock_clear_cache):
        """测试成功清空语义注入缓存"""
        mock_clear_cache.return_value = None
        
        response = client.post("/api/semantic-injection/cache/clear")
        
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert data['message'] == "语义注入缓存已清空"
        assert data['data']['status'] == "cleared"
        mock_clear_cache.assert_called_once()
    
    @patch.object(semantic_injection_service, 'get_cache_stats')
    def test_get_cache_stats_success(self, mock_get_stats):
        """测试成功获取缓存统计信息"""
        mock_get_stats.return_value = {
            'cache_size': 5,
            'last_clear': '2024-01-01T00:00:00',
            'ttl_minutes': 30
        }
        
        response = client.get("/api/semantic-injection/cache/stats")
        
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert data['message'] == "获取缓存统计信息成功"
        assert data['data']['cache_size'] == 5
        assert data['data']['ttl_minutes'] == 30
        mock_get_stats.assert_called_once()
    
    def test_health_check(self):
        """测试健康检查"""
        response = client.get("/api/semantic-injection/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert data['message'] == "语义注入服务运行正常"
        assert data['data']['status'] == "healthy"