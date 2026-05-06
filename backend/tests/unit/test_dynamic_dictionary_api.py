"""
动态字典配置 API 测试
"""
import pytest
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient
from datetime import datetime

from src.main import app
from src.models.data_preparation_model import DynamicDictionaryConfig, Dictionary
from src.models.data_source_model import DataSource
from src.schemas.dynamic_dictionary_schema import (
    DynamicDictionaryConfigCreate,
    QueryTestRequest,
    RefreshResult
)

client = TestClient(app)


class TestDynamicDictionaryAPI:
    """动态字典配置 API 测试类"""

    @pytest.fixture
    def mock_db_session(self):
        """模拟数据库会话"""
        with patch('src.api.dynamic_dictionary.get_db') as mock_get_db:
            mock_session = Mock()
            mock_get_db.return_value = mock_session
            yield mock_session

    @pytest.fixture
    def sample_config_data(self):
        """示例配置数据"""
        return {
            "dictionary_id": "dict-123",
            "data_source_id": "ds-456",
            "sql_query": "SELECT id, name FROM users",
            "key_field": "id",
            "value_field": "name",
            "refresh_interval": 3600
        }

    @pytest.fixture
    def sample_config_model(self):
        """示例配置模型"""
        return DynamicDictionaryConfig(
            id="config-123",
            dictionary_id="dict-123",
            data_source_id="ds-456",
            sql_query="SELECT id, name FROM users",
            key_field="id",
            value_field="name",
            refresh_interval=3600,
            last_refresh_time=datetime.utcnow(),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )

    def test_create_dynamic_dictionary_config_success(self, mock_db_session, sample_config_data, sample_config_model):
        """测试创建动态字典配置 - 成功"""
        # 模拟服务层
        with patch('src.api.dynamic_dictionary.DynamicDictionaryService') as mock_service_class:
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            mock_service.create_config.return_value = sample_config_model

            # 发送请求
            response = client.post("/api/dynamic-dictionaries/", json=sample_config_data)

            # 验证响应
            assert response.status_code == 200
            data = response.json()
            assert data["dictionary_id"] == "dict-123"
            assert data["data_source_id"] == "ds-456"
            assert data["sql_query"] == "SELECT id, name FROM users"
            assert data["key_field"] == "id"
            assert data["value_field"] == "name"
            assert data["refresh_interval"] == 3600

            # 验证服务调用
            mock_service.create_config.assert_called_once()

    def test_create_dynamic_dictionary_config_validation_error(self, mock_db_session):
        """测试创建动态字典配置 - 验证错误"""
        # 无效数据（缺少必填字段）
        invalid_data = {
            "dictionary_id": "dict-123",
            # 缺少其他必填字段
        }

        response = client.post("/api/dynamic-dictionaries/", json=invalid_data)
        assert response.status_code == 422  # 验证错误

    def test_create_dynamic_dictionary_config_business_error(self, mock_db_session, sample_config_data):
        """测试创建动态字典配置 - 业务错误"""
        with patch('src.api.dynamic_dictionary.DynamicDictionaryService') as mock_service_class:
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            mock_service.create_config.side_effect = ValueError("字典不存在")

            response = client.post("/api/dynamic-dictionaries/", json=sample_config_data)
            assert response.status_code == 400
            assert "字典不存在" in response.json()["detail"]

    def test_get_dynamic_dictionary_config_success(self, mock_db_session, sample_config_model):
        """测试获取动态字典配置 - 成功"""
        with patch('src.api.dynamic_dictionary.DynamicDictionaryService') as mock_service_class:
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            mock_service.get_config.return_value = sample_config_model

            response = client.get("/api/dynamic-dictionaries/dict-123")
            
            assert response.status_code == 200
            data = response.json()
            assert data["dictionary_id"] == "dict-123"

    def test_get_dynamic_dictionary_config_not_found(self, mock_db_session):
        """测试获取动态字典配置 - 不存在"""
        with patch('src.api.dynamic_dictionary.DynamicDictionaryService') as mock_service_class:
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            mock_service.get_config.return_value = None

            response = client.get("/api/dynamic-dictionaries/dict-123")
            assert response.status_code == 404

    def test_update_dynamic_dictionary_config_success(self, mock_db_session, sample_config_model):
        """测试更新动态字典配置 - 成功"""
        update_data = {
            "refresh_interval": 7200,
            "sql_query": "SELECT id, name FROM updated_users"
        }

        with patch('src.api.dynamic_dictionary.DynamicDictionaryService') as mock_service_class:
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            mock_service.update_config.return_value = sample_config_model

            response = client.put("/api/dynamic-dictionaries/dict-123", json=update_data)
            
            assert response.status_code == 200
            mock_service.update_config.assert_called_once()

    def test_delete_dynamic_dictionary_config_success(self, mock_db_session):
        """测试删除动态字典配置 - 成功"""
        with patch('src.api.dynamic_dictionary.DynamicDictionaryService') as mock_service_class:
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            mock_service.delete_config.return_value = True

            response = client.delete("/api/dynamic-dictionaries/dict-123")
            
            assert response.status_code == 200
            assert response.json()["message"] == "删除成功"

    def test_test_sql_query_success(self, mock_db_session):
        """测试SQL查询 - 成功"""
        test_data = {
            "data_source_id": "ds-456",
            "sql_query": "SELECT id, name FROM users",
            "key_field": "id",
            "value_field": "name"
        }

        mock_result = {
            "success": True,
            "message": "查询执行成功",
            "sample_data": [{"id": "1", "name": "用户1"}],
            "total_count": 100,
            "execution_time_ms": 50
        }

        with patch('src.api.dynamic_dictionary.DynamicDictionaryService') as mock_service_class:
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            mock_service.test_query.return_value = Mock(**mock_result)

            response = client.post("/api/dynamic-dictionaries/test-query", json=test_data)
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["total_count"] == 100

    def test_test_sql_query_with_dangerous_keywords(self, mock_db_session):
        """测试SQL查询 - 包含危险关键字"""
        test_data = {
            "data_source_id": "ds-456",
            "sql_query": "DROP TABLE users",  # 危险操作
            "key_field": "id",
            "value_field": "name"
        }

        response = client.post("/api/dynamic-dictionaries/test-query", json=test_data)
        assert response.status_code == 422  # 验证错误

    def test_refresh_dynamic_dictionary_success(self, mock_db_session):
        """测试手动刷新动态字典 - 成功"""
        mock_result = RefreshResult(
            success=True,
            message="字典刷新成功",
            items_added=5,
            items_updated=3,
            items_removed=1,
            total_items=50,
            refresh_time=datetime.utcnow(),
            execution_time_ms=200
        )

        with patch('src.api.dynamic_dictionary.DynamicDictionaryService') as mock_service_class:
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            mock_service.refresh_dictionary.return_value = mock_result

            response = client.post("/api/dynamic-dictionaries/dict-123/refresh")
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["items_added"] == 5
            assert data["items_updated"] == 3
            assert data["items_removed"] == 1

    def test_refresh_dynamic_dictionary_failure(self, mock_db_session):
        """测试手动刷新动态字典 - 失败"""
        mock_result = RefreshResult(
            success=False,
            message="刷新失败: 数据源连接失败",
            refresh_time=datetime.utcnow(),
            execution_time_ms=100
        )

        with patch('src.api.dynamic_dictionary.DynamicDictionaryService') as mock_service_class:
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            mock_service.refresh_dictionary.return_value = mock_result

            response = client.post("/api/dynamic-dictionaries/dict-123/refresh")
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is False
            assert "数据源连接失败" in data["message"]

    def test_get_dynamic_dictionary_configs_list(self, mock_db_session, sample_config_model):
        """测试获取动态字典配置列表"""
        with patch('src.api.dynamic_dictionary.DynamicDictionaryService') as mock_service_class:
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            mock_service.get_configs_list.return_value = ([sample_config_model], 1)

            response = client.get("/api/dynamic-dictionaries/?page=1&page_size=20")
            
            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 1
            assert data["page"] == 1
            assert data["page_size"] == 20
            assert len(data["items"]) == 1

    def test_check_refresh_status(self, mock_db_session, sample_config_model):
        """测试检查刷新状态"""
        with patch('src.api.dynamic_dictionary.DynamicDictionaryService') as mock_service_class:
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            mock_service.check_refresh_needed.return_value = True
            mock_service.get_config.return_value = sample_config_model

            response = client.get("/api/dynamic-dictionaries/dict-123/refresh-status")
            
            assert response.status_code == 200
            data = response.json()
            assert data["needs_refresh"] is True
            assert data["refresh_interval"] == 3600

    def test_sql_injection_prevention(self, mock_db_session):
        """测试SQL注入防护"""
        dangerous_queries = [
            "DROP TABLE users",  # 不是SELECT开头
            "INSERT INTO users VALUES (1, 'hacker')",  # 不是SELECT开头
            "UPDATE users SET password = 'hacked'",  # 不是SELECT开头
            "DELETE FROM users WHERE id = 1",  # 不是SELECT开头
            "SELECT * FROM users; DROP TABLE users;",  # 包含DROP关键字
        ]

        for query in dangerous_queries:
            test_data = {
                "data_source_id": "ds-456",
                "sql_query": query,
                "key_field": "id",
                "value_field": "name"
            }

            # 不使用mock，让验证器正常工作
            response = client.post("/api/dynamic-dictionaries/test-query", json=test_data)
            # 应该被验证器拦截
            assert response.status_code == 422, f"Query '{query}' should be rejected but got {response.status_code}"

    def test_error_handling_coverage(self, mock_db_session):
        """测试错误处理覆盖"""
        # 测试服务层异常
        with patch('src.api.dynamic_dictionary.DynamicDictionaryService') as mock_service_class:
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            mock_service.get_config.side_effect = Exception("数据库连接失败")

            response = client.get("/api/dynamic-dictionaries/dict-123")
            assert response.status_code == 500