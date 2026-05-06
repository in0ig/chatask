import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch
from sqlalchemy.orm import Session

from src.main import app

client = TestClient(app)

class TestSemanticInjectionAPISimple:
    """语义注入API简单测试"""
    
    def test_health_check(self):
        """测试健康检查"""
        response = client.get("/api/semantic-injection/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert data['message'] == "语义注入服务运行正常"
        assert data['data']['status'] == "healthy"
    
    def test_get_field_semantic_mapping_not_found(self):
        """测试获取不存在的字段语义映射"""
        response = client.get("/api/semantic-injection/field-mapping/nonexistent_table/nonexistent_field")
        
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is False
        assert "未找到字段" in data['message']
        assert data['data'] is None
    
    def test_inject_semantic_values_empty_data(self):
        """测试注入语义值到空数据"""
        request_data = {
            "table_name": "users",
            "data": []
        }
        
        response = client.post("/api/semantic-injection/inject", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert data['message'] == "语义值注入成功"
        assert data['data'] == []
    
    def test_get_table_semantic_schema_empty(self):
        """测试获取无映射的表语义模式"""
        response = client.get("/api/semantic-injection/schema/nonexistent_table")
        
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert data['message'] == "获取表语义模式成功"
        assert data['data']['table_name'] == 'nonexistent_table'
        assert data['data']['semantic_fields'] == {}
    
    def test_batch_inject_semantic_values_empty(self):
        """测试批量注入语义值到空数据"""
        request_data = {
            "table_data_map": {
                "users": [],
                "orders": []
            }
        }
        
        response = client.post("/api/semantic-injection/batch-inject", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert data['message'] == "批量语义值注入成功"
        assert 'users' in data['data']
        assert 'orders' in data['data']
        assert data['data']['users'] == []
        assert data['data']['orders'] == []