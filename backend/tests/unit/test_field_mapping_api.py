"""
字段映射API测试
"""
import pytest
import uuid
from unittest.mock import Mock, patch
from datetime import datetime
from fastapi.testclient import TestClient

from src.main import app
from src.models.data_preparation_model import DataTable, TableField, Dictionary
from src.schemas.field_mapping_schema import (
    FieldMappingCreate, FieldMappingUpdate, FieldMappingResponse,
    BatchFieldMappingCreate, BatchFieldMappingUpdate
)

# 创建测试客户端
client = TestClient(app)

# 测试数据
TEST_TABLE_ID = str(uuid.uuid4())
TEST_FIELD_ID = str(uuid.uuid4())
TEST_DICTIONARY_ID = str(uuid.uuid4())
TEST_MAPPING_ID = str(uuid.uuid4())


class TestFieldMappingAPI:
    """字段映射API测试类"""

    @pytest.fixture
    def mock_db_session(self):
        """模拟数据库会话"""
        with patch('src.api.field_mapping.get_db') as mock_get_db:
            mock_session = Mock()
            mock_get_db.return_value = mock_session
            yield mock_session

    @pytest.fixture
    def sample_table_model(self):
        """示例数据表模型"""
        return DataTable(
            id=TEST_TABLE_ID,
            data_source_id=str(uuid.uuid4()),
            table_name="test_table",
            display_name="测试表",
            description="测试用数据表",
            data_mode="DIRECT_QUERY",
            status=True,
            created_by="test_user",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )

    @pytest.fixture
    def sample_field_model(self):
        """示例字段模型"""
        return TableField(
            id=TEST_FIELD_ID,
            table_id=TEST_TABLE_ID,
            field_name="user_id",
            display_name="用户ID",
            data_type="VARCHAR",
            description="用户唯一标识",
            is_primary_key=True,
            is_nullable=False,
            is_queryable=True,
            is_aggregatable=False,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )

    @pytest.fixture
    def sample_dictionary_model(self):
        """示例字典模型"""
        return Dictionary(
            id=TEST_DICTIONARY_ID,
            code="USER_STATUS",
            name="用户状态字典",
            description="用户账户状态字典",
            dict_type="static",
            status=True,
            created_by="test_user",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )

    @pytest.fixture
    def sample_mapping_data(self):
        """示例字段映射数据"""
        return {
            "table_id": TEST_TABLE_ID,
            "field_id": TEST_FIELD_ID,
            "dictionary_id": TEST_DICTIONARY_ID,
            "business_name": "用户标识",
            "business_meaning": "系统中用户的唯一标识符",
            "value_range": "正整数",
            "is_required": True,
            "default_value": None
        }

    @pytest.fixture
    def sample_mapping_response(self):
        """示例字段映射响应"""
        return FieldMappingResponse(
            id=TEST_MAPPING_ID,
            table_id=TEST_TABLE_ID,
            field_id=TEST_FIELD_ID,
            field_name="user_id",
            field_type="VARCHAR",
            dictionary_id=TEST_DICTIONARY_ID,
            dictionary_name="用户状态字典",
            business_name="用户标识",
            business_meaning="系统中用户的唯一标识符",
            value_range="正整数",
            is_required=True,
            default_value=None,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )

    # ====================
    # 字段映射CRUD测试
    # ====================

    def test_create_field_mapping_success(self, mock_db_session, sample_mapping_data, sample_mapping_response):
        """测试创建字段映射 - 成功"""
        # 模拟服务层
        with patch('src.api.field_mapping.FieldMappingService') as mock_service_class:
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            mock_service.create_mapping.return_value = sample_mapping_response

            # 发送请求
            response = client.post("/api/field-mappings/", json=sample_mapping_data)

            # 验证响应
            assert response.status_code == 201
            data = response.json()
            assert data["id"] == TEST_MAPPING_ID
            assert data["business_name"] == "用户标识"
            assert data["is_required"] == True

            # 验证服务层调用
            mock_service.create_mapping.assert_called_once()

    def test_create_field_mapping_validation_error(self, mock_db_session):
        """测试创建字段映射 - 验证错误"""
        # 无效数据（缺少必填字段）
        invalid_data = {
            "table_id": TEST_TABLE_ID,
            # 缺少 field_id 和 business_name
        }

        response = client.post("/api/field-mappings/", json=invalid_data)
        assert response.status_code == 422  # 验证错误

    def test_create_field_mapping_duplicate_field(self, mock_db_session, sample_mapping_data):
        """测试创建字段映射 - 字段已存在映射"""
        with patch('src.api.field_mapping.FieldMappingService') as mock_service_class:
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            mock_service.create_mapping.side_effect = ValueError("字段已存在映射")

            response = client.post("/api/field-mappings/", json=sample_mapping_data)
            assert response.status_code == 400
            assert "字段已存在映射" in response.json()["detail"]

    def test_get_field_mappings_by_table(self, mock_db_session, sample_mapping_response):
        """测试获取表的字段映射列表"""
        with patch('src.api.field_mapping.FieldMappingService') as mock_service_class:
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            mock_service.get_mappings_by_table.return_value = {
                "items": [sample_mapping_response],
                "total": 1,
                "page": 1,
                "page_size": 10
            }

            response = client.get(f"/api/field-mappings/table/{TEST_TABLE_ID}")

            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 1
            assert len(data["items"]) == 1
            assert data["items"][0]["business_name"] == "用户标识"

    def test_get_field_mapping_by_id(self, mock_db_session, sample_mapping_response):
        """测试获取指定字段映射详情"""
        with patch('src.api.field_mapping.FieldMappingService') as mock_service_class:
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            mock_service.get_mapping_by_id.return_value = sample_mapping_response

            response = client.get(f"/api/field-mappings/{TEST_MAPPING_ID}")

            assert response.status_code == 200
            data = response.json()
            assert data["id"] == TEST_MAPPING_ID
            assert data["business_name"] == "用户标识"

    def test_get_field_mapping_by_id_not_found(self, mock_db_session):
        """测试获取指定字段映射详情 - 映射不存在"""
        with patch('src.api.field_mapping.FieldMappingService') as mock_service_class:
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            mock_service.get_mapping_by_id.return_value = None

            response = client.get(f"/api/field-mappings/{TEST_MAPPING_ID}")

            assert response.status_code == 404
            assert "字段映射不存在" in response.json()["detail"]

    def test_update_field_mapping_success(self, mock_db_session, sample_mapping_response):
        """测试更新字段映射 - 成功"""
        update_data = {
            "business_name": "更新后的用户标识",
            "business_meaning": "更新后的业务含义",
            "is_required": False
        }

        with patch('src.api.field_mapping.FieldMappingService') as mock_service_class:
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            mock_service.update_mapping.return_value = sample_mapping_response

            response = client.put(f"/api/field-mappings/{TEST_MAPPING_ID}", json=update_data)

            assert response.status_code == 200
            mock_service.update_mapping.assert_called_once()

    def test_delete_field_mapping_success(self, mock_db_session):
        """测试删除字段映射 - 成功"""
        with patch('src.api.field_mapping.FieldMappingService') as mock_service_class:
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            mock_service.delete_mapping.return_value = True

            response = client.delete(f"/api/field-mappings/{TEST_MAPPING_ID}")

            assert response.status_code == 204
            mock_service.delete_mapping.assert_called_once()

    # ====================
    # 批量操作测试
    # ====================

    def test_batch_create_field_mappings_success(self, mock_db_session):
        """测试批量创建字段映射 - 成功"""
        batch_data = {
            "table_id": TEST_TABLE_ID,
            "mappings": [
                {
                    "field_id": TEST_FIELD_ID,
                    "business_name": "用户ID",
                    "business_meaning": "用户唯一标识",
                    "is_required": True
                },
                {
                    "field_id": str(uuid.uuid4()),
                    "business_name": "用户名",
                    "business_meaning": "用户登录名",
                    "is_required": True
                }
            ]
        }

        with patch('src.api.field_mapping.FieldMappingService') as mock_service_class:
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            mock_service.batch_create_mappings.return_value = {
                "success_count": 2,
                "error_count": 0,
                "errors": []
            }

            response = client.post("/api/field-mappings/batch", json=batch_data)

            assert response.status_code == 201
            data = response.json()
            assert data["success_count"] == 2
            assert data["error_count"] == 0

    def test_batch_update_field_mappings_success(self, mock_db_session):
        """测试批量更新字段映射 - 成功"""
        batch_data = {
            "mappings": [
                {
                    "id": TEST_MAPPING_ID,
                    "business_name": "更新后的用户ID",
                    "is_required": False
                }
            ]
        }

        with patch('src.api.field_mapping.FieldMappingService') as mock_service_class:
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            
            # The actual API behavior: batch_update_mappings returns the expected batch format
            mock_service.batch_update_mappings.return_value = {
                "success_count": 1,
                "error_count": 0,
                "errors": []
            }

            response = client.put("/api/field-mappings/batch", json=batch_data)

            assert response.status_code == 200
            data = response.json()
            
            # Verify the batch operation response format
            assert "success_count" in data
            assert "error_count" in data
            assert "errors" in data
            assert data["success_count"] == 1
            assert data["error_count"] == 0
            assert data["errors"] == []
            
            # Verify the service was called correctly
            mock_service.batch_update_mappings.assert_called_once()

    # ====================
    # 导入导出测试
    # ====================

    def test_export_field_mappings_excel(self, mock_db_session):
        """测试导出字段映射到Excel"""
        with patch('src.api.field_mapping.FieldMappingService') as mock_service_class:
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            mock_service.export_mappings.return_value = b"excel_content"

            response = client.get(f"/api/field-mappings/table/{TEST_TABLE_ID}/export?format=excel")

            assert response.status_code == 200
            assert response.headers["content-type"] == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

    def test_export_field_mappings_csv(self, mock_db_session):
        """测试导出字段映射到CSV"""
        with patch('src.api.field_mapping.FieldMappingService') as mock_service_class:
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            mock_service.export_mappings.return_value = b"csv_content"

            response = client.get(f"/api/field-mappings/table/{TEST_TABLE_ID}/export?format=csv")

            assert response.status_code == 200
            assert "text/csv" in response.headers["content-type"]

    def test_import_field_mappings_excel(self, mock_db_session):
        """测试从Excel导入字段映射"""
        import tempfile

        # 创建临时Excel文件
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp_file:
            tmp_file.write(b"dummy excel content")
            tmp_file_path = tmp_file.name

        try:
            with patch('src.api.field_mapping.FieldMappingService') as mock_service_class:
                mock_service = Mock()
                mock_service_class.return_value = mock_service
                mock_service.import_mappings.return_value = {
                    "success_count": 5,
                    "error_count": 0,
                    "errors": []
                }

                with open(tmp_file_path, 'rb') as f:
                    response = client.post(
                        f"/api/field-mappings/table/{TEST_TABLE_ID}/import",
                        files={"file": ("test.xlsx", f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
                    )

                assert response.status_code == 200
                data = response.json()
                assert data["success_count"] == 5

        finally:
            import os
            os.unlink(tmp_file_path)

    # ====================
    # 搜索和筛选测试
    # ====================

    def test_search_field_mappings(self, mock_db_session, sample_mapping_response):
        """测试搜索字段映射"""
        with patch('src.api.field_mapping.FieldMappingService') as mock_service_class:
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            mock_service.get_mappings_by_table.return_value = {
                "items": [sample_mapping_response],
                "total": 1,
                "page": 1,
                "page_size": 10
            }

            response = client.get(f"/api/field-mappings/table/{TEST_TABLE_ID}?q=用户")

            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 1
            assert len(data["items"]) == 1

    def test_filter_field_mappings_by_dictionary(self, mock_db_session, sample_mapping_response):
        """测试按字典筛选字段映射"""
        with patch('src.api.field_mapping.FieldMappingService') as mock_service_class:
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            mock_service.get_mappings_by_table.return_value = {
                "items": [sample_mapping_response],
                "total": 1,
                "page": 1,
                "page_size": 10
            }

            response = client.get(f"/api/field-mappings/table/{TEST_TABLE_ID}?dictionary_id={TEST_DICTIONARY_ID}")

            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 1

    def test_filter_field_mappings_by_required_status(self, mock_db_session, sample_mapping_response):
        """测试按必填状态筛选字段映射"""
        with patch('src.api.field_mapping.FieldMappingService') as mock_service_class:
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            mock_service.get_mappings_by_table.return_value = {
                "items": [sample_mapping_response],
                "total": 1,
                "page": 1,
                "page_size": 10
            }

            response = client.get(f"/api/field-mappings/table/{TEST_TABLE_ID}?is_required=true")

            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 1

    # ====================
    # 错误处理测试
    # ====================

    def test_api_error_handling_service_exception(self, mock_db_session):
        """测试API错误处理 - 服务层异常"""
        with patch('src.api.field_mapping.FieldMappingService') as mock_service_class:
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            mock_service.get_mappings_by_table.side_effect = Exception("数据库连接失败")

            response = client.get(f"/api/field-mappings/table/{TEST_TABLE_ID}")

            assert response.status_code == 500

    def test_api_error_handling_validation_error(self, mock_db_session):
        """测试API错误处理 - 数据验证失败"""
        invalid_data = {
            "table_id": "invalid-uuid",  # 无效的UUID格式
            "field_id": TEST_FIELD_ID,
            "business_name": ""  # 空的业务名称
        }

        with patch('src.api.field_mapping.FieldMappingService') as mock_service_class:
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            mock_service.create_mapping.side_effect = ValueError("数据验证失败")

            response = client.post("/api/field-mappings/", json=invalid_data)
            assert response.status_code == 400

    def test_api_error_handling_not_found(self, mock_db_session):
        """测试API错误处理 - 资源不存在"""
        with patch('src.api.field_mapping.FieldMappingService') as mock_service_class:
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            mock_service.get_mapping_by_id.return_value = None

            response = client.get(f"/api/field-mappings/non-existent-id")

            assert response.status_code == 404

    # ====================
    # 性能和边界测试
    # ====================

    def test_large_batch_operation(self, mock_db_session):
        """测试大批量操作"""
        # 创建100个字段映射
        mappings = []
        for i in range(100):
            mappings.append({
                "field_id": str(uuid.uuid4()),
                "business_name": f"字段{i}",
                "business_meaning": f"字段{i}的业务含义",
                "is_required": i % 2 == 0
            })

        batch_data = {
            "table_id": TEST_TABLE_ID,
            "mappings": mappings
        }

        with patch('src.api.field_mapping.FieldMappingService') as mock_service_class:
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            mock_service.batch_create_mappings.return_value = {
                "success_count": 100,
                "error_count": 0,
                "errors": []
            }

            response = client.post("/api/field-mappings/batch", json=batch_data)

            assert response.status_code == 201
            data = response.json()
            assert data["success_count"] == 100

    def test_pagination_large_dataset(self, mock_db_session):
        """测试大数据集分页"""
        with patch('src.api.field_mapping.FieldMappingService') as mock_service_class:
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            mock_service.get_mappings_by_table.return_value = {
                "items": [],
                "total": 1000,
                "page": 10,
                "page_size": 50
            }

            response = client.get(f"/api/field-mappings/table/{TEST_TABLE_ID}?page=10&page_size=50")

            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 1000
            assert data["page"] == 10
            assert data["page_size"] == 50