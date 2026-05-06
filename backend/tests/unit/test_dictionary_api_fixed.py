"""
字典API修复版单元测试
修复Mock对象设置和响应验证问题
"""
import pytest
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient
from datetime import datetime
from typing import List, Dict, Any, Optional
import os

from src.main import app
from src.models.data_preparation_model import Dictionary, DictionaryItem

# 创建测试客户端
client = TestClient(app)


class TestDictionaryAPIFixed:
    """字典API修复版测试类"""

    @pytest.fixture
    def mock_db_session(self):
        """模拟数据库会话"""
        with patch('src.api.dictionary.get_db') as mock_get_db:
            mock_session = Mock()
            mock_get_db.return_value = mock_session
            yield mock_session

    @pytest.fixture
    def sample_dictionary_data(self):
        """示例字典数据"""
        return {
            "code": "TEST_DICT_001",
            "name": "测试字典001",
            "description": "用于测试的字典",
            "parent_id": None,
            "dict_type": "static",  # 添加缺失的 dict_type 字段
            "status": True,
            "sort_order": 1,
            "created_by": "test_user"
        }

    @pytest.fixture
    def sample_dictionary_model(self):
        """示例字典模型"""
        model = Mock(spec=Dictionary)
        model.id = "dict-123"
        model.code = "TEST_DICT_001"
        model.name = "测试字典001"
        model.description = "用于测试的字典"
        model.parent_id = None
        model.dict_type = "static"  # 添加缺失的 dict_type 字段
        model.status = True
        model.sort_order = 1
        model.created_by = "test_user"
        model.created_at = datetime(2026, 2, 4, 10, 58, 19, 477289)
        model.updated_at = datetime(2026, 2, 4, 10, 58, 19, 477295)
        
        # Mock to_dict method
        model.to_dict.return_value = {
            "id": "dict-123",
            "code": "TEST_DICT_001",
            "name": "测试字典001",
            "description": "用于测试的字典",
            "parent_id": None,
            "dict_type": "static",  # 添加缺失的 dict_type 字段
            "status": True,
            "sort_order": 1,
            "created_by": "test_user",
            "created_at": "2026-02-04T10:58:19.477289",
            "updated_at": "2026-02-04T10:58:19.477295"
        }
        return model

    @pytest.fixture
    def sample_item_model(self):
        """示例字典项模型"""
        model = Mock(spec=DictionaryItem)
        model.id = "item-123"
        model.dictionary_id = "dict-123"
        model.item_key = "KEY_001"
        model.item_value = "值001"
        model.description = "测试项描述"
        model.sort_order = 1
        model.status = True
        model.extra_data = None  # 添加缺失的 extra_data 字段
        model.created_by = "test_user"
        model.created_at = datetime(2026, 2, 4, 10, 58, 19, 477289)
        model.updated_at = datetime(2026, 2, 4, 10, 58, 19, 477295)
        
        # Mock to_dict method
        model.to_dict.return_value = {
            "id": "item-123",
            "dictionary_id": "dict-123",
            "item_key": "KEY_001",
            "item_value": "值001",
            "description": "测试项描述",
            "sort_order": 1,
            "status": True,
            "extra_data": None,  # 添加缺失的 extra_data 字段
            "created_by": "test_user",
            "created_at": "2026-02-04T10:58:19.477289",
            "updated_at": "2026-02-04T10:58:19.477295"
        }
        return model

    # ====================
    # 字典CRUD测试
    # ====================

    def test_create_dictionary_success(self, mock_db_session, sample_dictionary_data, sample_dictionary_model):
        """测试创建字典 - 成功"""
        with patch('src.api.dictionary.dictionary_service') as mock_service:
            mock_service.get_dictionary_by_code.return_value = None
            mock_service.create_dictionary.return_value = sample_dictionary_model

            response = client.post("/api/dictionaries/", json=sample_dictionary_data)

            assert response.status_code == 201
            data = response.json()
            assert data["code"] == "TEST_DICT_001"
            assert data["name"] == "测试字典001"
            mock_service.create_dictionary.assert_called_once()

    def test_get_dictionaries_list(self, mock_db_session, sample_dictionary_model):
        """测试获取字典列表"""
        with patch('src.api.dictionary.dictionary_service') as mock_service:
            mock_service.get_all_dictionaries.return_value = {
                "items": [sample_dictionary_model],
                "total": 1,
                "page": 1,
                "page_size": 10
            }

            response = client.get("/api/dictionaries/?page=1&page_size=10")

            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            assert data[0]["code"] == "TEST_DICT_001"

    def test_get_dictionary_by_id(self, mock_db_session, sample_dictionary_model):
        """测试获取指定字典详情"""
        with patch('src.api.dictionary.dictionary_service') as mock_service:
            mock_service.get_dictionary_by_id.return_value = sample_dictionary_model

            response = client.get("/api/dictionaries/dict-123")

            assert response.status_code == 200
            data = response.json()
            assert data["code"] == "TEST_DICT_001"
            assert data["name"] == "测试字典001"

    def test_get_dictionary_by_id_not_found(self, mock_db_session):
        """测试获取指定字典详情 - 字典不存在"""
        with patch('src.api.dictionary.dictionary_service') as mock_service:
            mock_service.get_dictionary_by_id.return_value = None

            response = client.get("/api/dictionaries/non-existent-id")

            assert response.status_code == 404
            assert "字典不存在" in response.json()["detail"]

    def test_update_dictionary_success(self, mock_db_session, sample_dictionary_model):
        """测试更新字典 - 成功"""
        update_data = {
            "name": "更新后的字典",
            "description": "更新后的描述",
            "status": False,
            "sort_order": 2
        }

        with patch('src.api.dictionary.dictionary_service') as mock_service:
            mock_service.get_dictionary_by_id.return_value = sample_dictionary_model
            mock_service.update_dictionary.return_value = sample_dictionary_model

            response = client.put("/api/dictionaries/dict-123", json=update_data)

            assert response.status_code == 200
            mock_service.update_dictionary.assert_called_once()

    def test_delete_dictionary_success(self, mock_db_session):
        """测试删除字典 - 成功"""
        with patch('src.api.dictionary.dictionary_service') as mock_service:
            mock_service.get_dictionary_by_id.return_value = Mock()
            mock_service.has_children.return_value = False
            mock_service.has_field_references.return_value = False
            mock_service.has_dynamic_configs.return_value = False
            mock_service.delete_dictionary.return_value = True

            response = client.delete("/api/dictionaries/dict-123")

            assert response.status_code == 204

    # ====================
    # 字典项管理测试
    # ====================

    def test_get_dictionary_items(self, mock_db_session, sample_item_model):
        """测试获取字典项列表"""
        with patch('src.api.dictionary.dictionary_service') as mock_service:
            mock_service.get_dictionary_by_id.return_value = Mock()
            mock_service.get_dictionary_items.return_value = Mock(
                items=[sample_item_model],
                total=1,
                page=1,
                page_size=10
            )

            response = client.get("/api/dictionaries/dict-123/items?page=1&page_size=10")

            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            assert data[0]["item_key"] == "KEY_001"

    def test_create_dictionary_item_success(self, mock_db_session, sample_item_model):
        """测试创建字典项 - 成功"""
        item_data = {
            "dictionary_id": "dict-123",  # 添加缺失的 dictionary_id 字段
            "item_key": "KEY_001",
            "item_value": "值001",
            "description": "测试项描述",
            "sort_order": 1,
            "status": True
        }

        with patch('src.api.dictionary.dictionary_service') as mock_service:
            mock_service.get_dictionary_by_id.return_value = Mock()
            mock_service.get_dictionary_item_by_key.return_value = None
            mock_service.create_dictionary_item.return_value = sample_item_model

            response = client.post("/api/dictionaries/dict-123/items", json=item_data)

            assert response.status_code == 201
            data = response.json()
            assert data["item_key"] == "KEY_001"
            assert data["item_value"] == "值001"

    def test_update_dictionary_item_success(self, mock_db_session, sample_item_model):
        """测试更新字典项 - 成功"""
        update_data = {
            "item_value": "更新后的值",
            "description": "更新后的描述",
            "sort_order": 2,
            "status": False
        }

        with patch('src.api.dictionary.dictionary_service') as mock_service:
            mock_service.get_dictionary_by_id.return_value = Mock()
            mock_service.get_dictionary_item_by_id.return_value = sample_item_model
            mock_service.update_dictionary_item.return_value = sample_item_model

            response = client.put("/api/dictionaries/dict-123/items/item-123", json=update_data)

            assert response.status_code == 200
            mock_service.update_dictionary_item.assert_called_once()

    def test_delete_dictionary_item_success(self, mock_db_session):
        """测试删除字典项 - 成功"""
        with patch('src.api.dictionary.dictionary_service') as mock_service:
            mock_service.get_dictionary_by_id.return_value = Mock()
            mock_service.get_dictionary_item_by_id.return_value = Mock()
            mock_service.delete_dictionary_item.return_value = True

            response = client.delete("/api/dictionaries/dict-123/items/item-123")

            assert response.status_code == 204

    # ====================
    # 搜索和筛选功能测试
    # ====================

    def test_search_dictionaries(self, mock_db_session, sample_dictionary_model):
        """测试搜索字典"""
        with patch('src.api.dictionary.dictionary_service') as mock_service:
            mock_service.get_all_dictionaries.return_value = {
                "items": [sample_dictionary_model],
                "total": 1,
                "page": 1,
                "page_size": 10
            }

            response = client.get("/api/dictionaries/?search=测试")

            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            assert data[0]["name"] == "测试字典001"

    def test_filter_dictionaries_by_status(self, mock_db_session, sample_dictionary_model):
        """测试按状态筛选字典"""
        with patch('src.api.dictionary.dictionary_service') as mock_service:
            mock_service.get_all_dictionaries.return_value = {
                "items": [sample_dictionary_model],
                "total": 1,
                "page": 1,
                "page_size": 10
            }

            response = client.get("/api/dictionaries/?status=true")

            assert response.status_code == 200
            mock_service.get_all_dictionaries.assert_called_once()

    # ====================
    # 错误处理测试
    # ====================

    def test_create_dictionary_missing_required_fields(self, mock_db_session):
        """测试创建字典 - 缺少必填字段"""
        invalid_data = {
            "description": "测试描述"
        }

        response = client.post("/api/dictionaries/", json=invalid_data)
        assert response.status_code == 422

    def test_get_dictionaries_invalid_page(self, mock_db_session):
        """测试获取字典列表 - 无效页码"""
        response = client.get("/api/dictionaries/?page=0&page_size=10")
        assert response.status_code == 422

        response = client.get("/api/dictionaries/?page=-1&page_size=10")
        assert response.status_code == 422

    def test_get_dictionaries_invalid_page_size(self, mock_db_session):
        """测试获取字典列表 - 无效页大小"""
        response = client.get("/api/dictionaries/?page=1&page_size=0")
        assert response.status_code == 422

        response = client.get("/api/dictionaries/?page=1&page_size=101")
        assert response.status_code == 422