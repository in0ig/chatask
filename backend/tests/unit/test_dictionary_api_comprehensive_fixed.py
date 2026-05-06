"""
字典API综合修复版单元测试
修复Mock对象设置和响应验证问题，使用务实主义方法
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


class TestDictionaryAPIComprehensiveFixed:
    """字典API综合修复版测试类"""

    @pytest.fixture
    def mock_db_session(self):
        """模拟数据库会话"""
        with patch('src.api.dictionary.get_db') as mock_get_db:
            mock_session = Mock()
            mock_get_db.return_value = mock_session
            yield mock_session

    @pytest.fixture
    def sample_dictionary_dict(self):
        """示例字典字典数据（直接返回字典而非Mock对象）"""
        return {
            "id": "dict-123",
            "code": "TEST_DICT_001",
            "name": "测试字典001",
            "description": "用于测试的字典",
            "parent_id": None,
            "dict_type": "static",
            "status": True,
            "sort_order": 1,
            "created_by": "test_user",
            "created_at": "2026-02-04T10:58:19.477289",
            "updated_at": "2026-02-04T10:58:19.477295"
        }

    @pytest.fixture
    def sample_item_dict(self):
        """示例字典项字典数据（直接返回字典而非Mock对象）"""
        return {
            "id": "item-123",
            "dictionary_id": "dict-123",
            "item_key": "KEY_001",
            "item_value": "值001",
            "description": "测试项描述",
            "sort_order": 1,
            "status": True,
            "extra_data": None,
            "created_by": "test_user",
            "created_at": "2026-02-04T10:58:19.477289",
            "updated_at": "2026-02-04T10:58:19.477295"
        }

    @pytest.fixture
    def sample_dictionary_data(self):
        """示例字典创建数据"""
        return {
            "code": "TEST_DICT_001",
            "name": "测试字典001",
            "description": "用于测试的字典",
            "parent_id": None,
            "dict_type": "static",
            "status": True,
            "sort_order": 1,
            "created_by": "test_user"
        }

    # ====================
    # 字典CRUD测试
    # ====================

    def test_create_dictionary_success(self, mock_db_session, sample_dictionary_data, sample_dictionary_dict):
        """测试创建字典 - 成功"""
        with patch('src.api.dictionary.dictionary_service') as mock_service:
            # Mock service methods
            mock_service.get_dictionary_by_code.return_value = None
            
            # Create a mock model that returns the dictionary data
            mock_model = Mock()
            mock_model.to_dict.return_value = sample_dictionary_dict
            mock_service.create_dictionary.return_value = mock_model

            response = client.post("/api/dictionaries/", json=sample_dictionary_data)

            assert response.status_code == 201
            data = response.json()
            assert data["code"] == "TEST_DICT_001"
            assert data["name"] == "测试字典001"
            assert data["dict_type"] == "static"
            mock_service.create_dictionary.assert_called_once()

    def test_get_dictionaries_list(self, mock_db_session, sample_dictionary_dict):
        """测试获取字典列表"""
        with patch('src.api.dictionary.dictionary_service') as mock_service:
            # Mock service to return dictionary data directly
            mock_model = Mock()
            mock_model.to_dict.return_value = sample_dictionary_dict
            
            mock_service.get_all_dictionaries.return_value = {
                "items": [mock_model],
                "total": 1,
                "page": 1,
                "page_size": 10
            }

            response = client.get("/api/dictionaries/?page=1&page_size=10")

            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            assert data[0]["code"] == "TEST_DICT_001"
            assert data[0]["dict_type"] == "static"

    def test_get_dictionary_by_id(self, mock_db_session, sample_dictionary_dict):
        """测试获取指定字典详情"""
        with patch('src.api.dictionary.dictionary_service') as mock_service:
            mock_model = Mock()
            mock_model.to_dict.return_value = sample_dictionary_dict
            mock_service.get_dictionary_by_id.return_value = mock_model

            response = client.get("/api/dictionaries/dict-123")

            assert response.status_code == 200
            data = response.json()
            assert data["code"] == "TEST_DICT_001"
            assert data["name"] == "测试字典001"
            assert data["dict_type"] == "static"

    def test_get_dictionary_by_id_not_found(self, mock_db_session):
        """测试获取指定字典详情 - 字典不存在"""
        with patch('src.api.dictionary.dictionary_service') as mock_service:
            mock_service.get_dictionary_by_id.return_value = None

            response = client.get("/api/dictionaries/non-existent-id")

            assert response.status_code == 404
            assert "字典不存在" in response.json()["detail"]

    def test_update_dictionary_success(self, mock_db_session, sample_dictionary_dict):
        """测试更新字典 - 成功"""
        update_data = {
            "name": "更新后的字典",
            "description": "更新后的描述",
            "status": False,
            "sort_order": 2
        }

        with patch('src.api.dictionary.dictionary_service') as mock_service:
            mock_existing = Mock()
            mock_existing.code = "TEST_DICT_001"
            mock_service.get_dictionary_by_id.return_value = mock_existing
            
            mock_updated = Mock()
            updated_dict = sample_dictionary_dict.copy()
            updated_dict.update(update_data)
            mock_updated.to_dict.return_value = updated_dict
            mock_service.update_dictionary.return_value = mock_updated

            response = client.put("/api/dictionaries/dict-123", json=update_data)

            assert response.status_code == 200
            data = response.json()
            assert data["name"] == "更新后的字典"
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

    def test_get_dictionary_items(self, mock_db_session, sample_item_dict):
        """测试获取字典项列表"""
        with patch('src.api.dictionary.dictionary_service') as mock_service:
            mock_service.get_dictionary_by_id.return_value = Mock()
            
            # Create mock items result
            mock_item = Mock()
            mock_item.to_dict.return_value = sample_item_dict
            
            mock_result = Mock()
            mock_result.items = [mock_item]
            mock_result.total = 1
            mock_result.page = 1
            mock_result.page_size = 10
            
            mock_service.get_dictionary_items.return_value = mock_result

            response = client.get("/api/dictionaries/dict-123/items?page=1&page_size=10")

            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            assert data[0]["item_key"] == "KEY_001"
            assert data[0]["extra_data"] is None

    def test_create_dictionary_item_success(self, mock_db_session, sample_item_dict):
        """测试创建字典项 - 成功"""
        item_data = {
            "dictionary_id": "dict-123",
            "item_key": "KEY_001",
            "item_value": "值001",
            "description": "测试项描述",
            "sort_order": 1,
            "status": True
        }

        with patch('src.api.dictionary.dictionary_service') as mock_service:
            mock_service.get_dictionary_by_id.return_value = Mock()
            mock_service.get_dictionary_item_by_key.return_value = None
            
            mock_item = Mock()
            mock_item.to_dict.return_value = sample_item_dict
            mock_service.create_dictionary_item.return_value = mock_item

            response = client.post("/api/dictionaries/dict-123/items", json=item_data)

            assert response.status_code == 201
            data = response.json()
            assert data["item_key"] == "KEY_001"
            assert data["item_value"] == "值001"
            assert data["extra_data"] is None

    def test_update_dictionary_item_success(self, mock_db_session, sample_item_dict):
        """测试更新字典项 - 成功"""
        update_data = {
            "item_value": "更新后的值",
            "description": "更新后的描述",
            "sort_order": 2,
            "status": False
        }

        with patch('src.api.dictionary.dictionary_service') as mock_service:
            mock_service.get_dictionary_by_id.return_value = Mock()
            
            mock_existing = Mock()
            mock_existing.item_key = "KEY_001"
            mock_service.get_dictionary_item_by_id.return_value = mock_existing
            
            mock_updated = Mock()
            updated_item = sample_item_dict.copy()
            updated_item.update(update_data)
            mock_updated.to_dict.return_value = updated_item
            mock_service.update_dictionary_item.return_value = mock_updated

            response = client.put("/api/dictionaries/dict-123/items/item-123", json=update_data)

            assert response.status_code == 200
            data = response.json()
            assert data["item_value"] == "更新后的值"
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

    def test_search_dictionaries(self, mock_db_session, sample_dictionary_dict):
        """测试搜索字典"""
        with patch('src.api.dictionary.dictionary_service') as mock_service:
            mock_model = Mock()
            mock_model.to_dict.return_value = sample_dictionary_dict
            
            mock_service.get_all_dictionaries.return_value = {
                "items": [mock_model],
                "total": 1,
                "page": 1,
                "page_size": 10
            }

            response = client.get("/api/dictionaries/?search=测试")

            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            assert data[0]["name"] == "测试字典001"

    def test_filter_dictionaries_by_status(self, mock_db_session, sample_dictionary_dict):
        """测试按状态筛选字典"""
        with patch('src.api.dictionary.dictionary_service') as mock_service:
            mock_model = Mock()
            mock_model.to_dict.return_value = sample_dictionary_dict
            
            mock_service.get_all_dictionaries.return_value = {
                "items": [mock_model],
                "total": 1,
                "page": 1,
                "page_size": 10
            }

            response = client.get("/api/dictionaries/?status=true")

            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            assert data[0]["status"] == True
            mock_service.get_all_dictionaries.assert_called_once()

    # ====================
    # 错误处理测试
    # ====================

    def test_create_dictionary_missing_required_fields(self, mock_db_session):
        """测试创建字典 - 缺少必填字段"""
        invalid_data = {
            "description": "测试描述"
            # 缺少 code, name, created_by 等必填字段
        }

        response = client.post("/api/dictionaries/", json=invalid_data)
        assert response.status_code == 422

    def test_create_dictionary_duplicate_code(self, mock_db_session):
        """测试创建字典 - 编码重复"""
        sample_data = {
            "code": "DUPLICATE_CODE",
            "name": "重复编码字典",
            "created_by": "test_user"
        }

        with patch('src.api.dictionary.dictionary_service') as mock_service:
            # Mock existing dictionary with same code
            mock_service.get_dictionary_by_code.return_value = Mock()

            response = client.post("/api/dictionaries/", json=sample_data)
            assert response.status_code == 409
            assert "字典编码已存在" in response.json()["detail"]

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

    def test_create_dictionary_item_missing_dictionary_id(self, mock_db_session):
        """测试创建字典项 - 缺少dictionary_id字段"""
        item_data = {
            "item_key": "KEY_001",
            "item_value": "值001"
            # 缺少 dictionary_id 字段
        }

        response = client.post("/api/dictionaries/dict-123/items", json=item_data)
        assert response.status_code == 422

    def test_create_dictionary_item_duplicate_key(self, mock_db_session):
        """测试创建字典项 - 键值重复"""
        item_data = {
            "dictionary_id": "dict-123",
            "item_key": "DUPLICATE_KEY",
            "item_value": "重复键值"
        }

        with patch('src.api.dictionary.dictionary_service') as mock_service:
            mock_service.get_dictionary_by_id.return_value = Mock()
            # Mock existing item with same key
            mock_service.get_dictionary_item_by_key.return_value = Mock()

            response = client.post("/api/dictionaries/dict-123/items", json=item_data)
            assert response.status_code == 409
            assert "字典项键值已存在" in response.json()["detail"]

    # ====================
    # 批量操作测试
    # ====================

    def test_batch_create_dictionary_items_success(self, mock_db_session):
        """测试批量创建字典项 - 成功"""
        batch_data = {
            "items": [
                {
                    "dictionary_id": "dict-123",
                    "item_key": "KEY_001",
                    "item_value": "值001",
                    "description": "测试项1",
                    "sort_order": 1,
                    "status": True
                },
                {
                    "dictionary_id": "dict-123",
                    "item_key": "KEY_002",
                    "item_value": "值002",
                    "description": "测试项2",
                    "sort_order": 2,
                    "status": True
                }
            ]
        }

        with patch('src.api.dictionary.dictionary_service') as mock_service:
            mock_service.get_dictionary_by_id.return_value = Mock()
            mock_service.get_dictionary_item_by_key.return_value = None
            mock_service.create_dictionary_item.return_value = Mock()

            response = client.post("/api/dictionaries/dict-123/items/batch", json=batch_data)

            assert response.status_code == 201
            data = response.json()
            assert data["success_count"] == 2
            assert data["failed_count"] == 0
            assert data["total_processed"] == 2

    # ====================
    # 导入导出测试
    # ====================

    def test_export_dictionary_excel(self, mock_db_session):
        """测试导出字典到Excel"""
        with patch('src.api.dictionary.dictionary_service') as mock_service:
            mock_service.get_dictionary_by_id.return_value = Mock(name="测试字典")
            
            mock_result = Mock()
            mock_result.items = []
            mock_service.get_dictionary_items.return_value = mock_result

            with patch('src.services.dictionary_import_export.DictionaryImportExportService') as mock_export_service:
                mock_export_instance = Mock()
                mock_export_service.return_value = mock_export_instance
                mock_export_instance.export_dictionary_to_excel.return_value = "/tmp/test_dict.xlsx"

                response = client.get("/api/dictionaries/dict-123/export?format_type=excel")

                assert response.status_code == 200
                data = response.json()
                assert data["format"] == "excel"
                assert "导出成功" in data["message"]

    def test_export_dictionary_csv(self, mock_db_session):
        """测试导出字典到CSV"""
        with patch('src.api.dictionary.dictionary_service') as mock_service:
            mock_service.get_dictionary_by_id.return_value = Mock(name="测试字典")
            
            mock_result = Mock()
            mock_result.items = []
            mock_service.get_dictionary_items.return_value = mock_result

            with patch('src.services.dictionary_import_export.DictionaryImportExportService') as mock_export_service:
                mock_export_instance = Mock()
                mock_export_service.return_value = mock_export_instance
                mock_export_instance.export_dictionary_to_csv.return_value = "/tmp/test_dict.csv"

                response = client.get("/api/dictionaries/dict-123/export?format_type=csv")

                assert response.status_code == 200
                data = response.json()
                assert data["format"] == "csv"
                assert "导出成功" in data["message"]

    def test_export_dictionary_invalid_format(self, mock_db_session):
        """测试导出字典 - 无效格式"""
        with patch('src.api.dictionary.dictionary_service') as mock_service:
            mock_service.get_dictionary_by_id.return_value = Mock()

            response = client.get("/api/dictionaries/dict-123/export?format_type=invalid")

            assert response.status_code == 400
            assert "不支持的格式类型" in response.json()["detail"]

    def test_export_dictionary_not_found(self, mock_db_session):
        """测试导出字典 - 字典不存在"""
        with patch('src.api.dictionary.dictionary_service') as mock_service:
            mock_service.get_dictionary_by_id.return_value = None

            response = client.get("/api/dictionaries/non-existent/export?format_type=excel")

            assert response.status_code == 404
            assert "字典不存在" in response.json()["detail"]

    # ====================
    # 树形结构测试
    # ====================

    def test_get_dictionaries_tree(self, mock_db_session, sample_dictionary_dict):
        """测试获取字典树形结构"""
        with patch('src.api.dictionary.dictionary_service') as mock_service:
            mock_model = Mock()
            mock_model.to_dict.return_value = sample_dictionary_dict
            mock_service.get_dictionaries_tree.return_value = [mock_model]

            response = client.get("/api/dictionaries/tree")

            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            assert data[0]["code"] == "TEST_DICT_001"

    def test_get_dictionaries_tree_with_status_filter(self, mock_db_session, sample_dictionary_dict):
        """测试获取字典树形结构 - 按状态筛选"""
        with patch('src.api.dictionary.dictionary_service') as mock_service:
            mock_model = Mock()
            mock_model.to_dict.return_value = sample_dictionary_dict
            mock_service.get_dictionaries_tree.return_value = [mock_model]

            response = client.get("/api/dictionaries/tree?status=true")

            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            assert data[0]["status"] == True
            mock_service.get_dictionaries_tree.assert_called_once_with(mock_db_session, status=True)

    # ====================
    # 依赖检查测试
    # ====================

    def test_delete_dictionary_with_children(self, mock_db_session):
        """测试删除字典 - 有子字典"""
        with patch('src.api.dictionary.dictionary_service') as mock_service:
            mock_service.get_dictionary_by_id.return_value = Mock()
            mock_service.has_children.return_value = True

            response = client.delete("/api/dictionaries/dict-123")

            assert response.status_code == 400
            assert "该字典有子字典" in response.json()["detail"]

    def test_delete_dictionary_with_field_references(self, mock_db_session):
        """测试删除字典 - 有字段引用"""
        with patch('src.api.dictionary.dictionary_service') as mock_service:
            mock_service.get_dictionary_by_id.return_value = Mock()
            mock_service.has_children.return_value = False
            mock_service.has_field_references.return_value = True

            response = client.delete("/api/dictionaries/dict-123")

            assert response.status_code == 400
            assert "该字典被字段引用" in response.json()["detail"]

    def test_delete_dictionary_with_dynamic_configs(self, mock_db_session):
        """测试删除字典 - 有动态配置"""
        with patch('src.api.dictionary.dictionary_service') as mock_service:
            mock_service.get_dictionary_by_id.return_value = Mock()
            mock_service.has_children.return_value = False
            mock_service.has_field_references.return_value = False
            mock_service.has_dynamic_configs.return_value = True

            response = client.delete("/api/dictionaries/dict-123")

            assert response.status_code == 400
            assert "该字典有关联的动态字典配置" in response.json()["detail"]