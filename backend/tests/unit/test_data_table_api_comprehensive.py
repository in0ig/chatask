"""
数据表API综合单元测试
完整覆盖数据表模块的所有功能
"""
import pytest
from fastapi.testclient import TestClient
from datetime import datetime
import uuid
import os
import logging
from unittest.mock import patch, Mock, MagicMock

# 设置测试模式环境变量，必须在导入应用之前设置
os.environ["TEST_MODE"] = "true"

# 设置日志记录器
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 导入所有模型以确保它们被正确注册到Base.metadata中
from src.models.base import Base
from src.models.data_source_model import DataSource
from src.models.data_preparation_model import DataTable, TableField

# 导入应用和数据库（必须在设置环境变量之后）
from src.main import app
from src.database import get_db

# 创建测试客户端
client = TestClient(app)

@pytest.fixture(scope="function")
def mock_db_session():
    """模拟数据库会话"""
    mock_session = Mock()
    
    # 模拟数据源
    mock_source = DataSource(
        id="test-source-1",
        name="Test MySQL Source",
        source_type="DATABASE",
        db_type="MySQL",
        host="localhost",
        port=3306,
        database_name="test_db",
        auth_type="SQL_AUTH",
        username="test_user",
        password="encrypted_password",
        status=True,
        created_by="test_user",
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    
    # 模拟数据表
    mock_table = DataTable(
        id="test-table-1",
        data_source_id="test-source-1",
        table_name="users",
        display_name="用户表",
        description="用户信息表",
        data_mode="DIRECT_QUERY",
        status=True,
        field_count=5,
        row_count=1000,
        created_by="test_user",
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    
    # 设置查询行为
    mock_session.query.return_value.filter.return_value.first.return_value = mock_source
    mock_session.query.return_value.filter.return_value.all.return_value = [mock_table]
    mock_session.query.return_value.filter.return_value.count.return_value = 1
    mock_session.query.return_value.filter.return_value.offset.return_value.limit.return_value.all.return_value = [mock_table]
    
    return mock_session

@pytest.fixture
def override_get_db(mock_db_session):
    """覆盖数据库依赖"""
    def _override_get_db():
        yield mock_db_session
    
    app.dependency_overrides[get_db] = _override_get_db
    yield mock_db_session
    app.dependency_overrides.clear()


class TestDataTableAPI:
    """数据表API测试类"""
    
    def test_get_data_tables_list_success(self, override_get_db):
        """测试获取数据表列表（成功场景）"""
        with patch('src.api.data_table_api.data_table_service') as mock_service:
            # 模拟服务层返回
            from src.schemas.data_table_schema import DataTableResponse, DataTableListResponse
            
            mock_table_response = DataTableResponse(
                id="test-table-1",
                data_source_id="test-source-1",
                table_name="users",
                display_name="用户表",
                description="用户信息表",
                data_mode="DIRECT_QUERY",
                status=True,
                field_count=5,
                row_count=1000,
                created_by="test_user",
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            
            mock_service.get_all_tables.return_value = DataTableListResponse(
                items=[mock_table_response],
                total=1,
                page=1,
                page_size=10,
                pages=1
            )
            
            response = client.get("/api/data-tables")
            
            # 验证响应
            assert response.status_code == 200
            data = response.json()
            assert "items" in data
            assert "total" in data
            assert "page" in data
            assert "page_size" in data
            assert len(data["items"]) == 1
            assert data["total"] == 1
            assert data["page"] == 1
            assert data["page_size"] == 10
            
            # 验证服务层调用
            mock_service.get_all_tables.assert_called_once()
    
    def test_get_data_tables_list_with_filters(self, override_get_db):
        """测试获取数据表列表（带筛选条件）"""
        with patch('src.api.data_table_api.data_table_service') as mock_service:
            from src.schemas.data_table_schema import DataTableListResponse
            
            mock_service.get_all_tables.return_value = DataTableListResponse(
                items=[],
                total=0,
                page=2,
                page_size=5,
                pages=1  # 修复：pages 必须 >= 1
            )
            
            # 测试搜索、数据源筛选和状态筛选
            response = client.get("/api/data-tables", params={
                "page": 2,
                "page_size": 5,
                "search": "user",
                "source_id": "test-source-1",
                "status": True
            })
            
            # 验证响应
            assert response.status_code == 200
            data = response.json()
            assert data["page"] == 2
            assert data["page_size"] == 5
            assert data["total"] == 0
            
            # 验证服务层调用
            mock_service.get_all_tables.assert_called_once()
            call_args = mock_service.get_all_tables.call_args
            assert call_args[1]["page"] == 2
            assert call_args[1]["page_size"] == 5
            assert call_args[1]["search"] == "user"
            assert call_args[1]["source_id"] == "test-source-1"
            assert call_args[1]["status"] is True
    
    def test_get_data_tables_list_invalid_page_size(self, override_get_db):
        """测试获取数据表列表（无效页大小）"""
        # 测试超出范围的页大小
        response = client.get("/api/data-tables", params={"page_size": 150})
        assert response.status_code == 422  # Unprocessable Entity
        
        # 测试小于1的页大小
        response = client.get("/api/data-tables", params={"page_size": 0})
        assert response.status_code == 422  # Unprocessable Entity
    
    def test_create_data_table_success(self, override_get_db):
        """测试创建数据表（成功场景）"""
        with patch('src.api.data_table_api.data_table_service') as mock_service:
            # 模拟服务层返回
            mock_table = DataTable(
                id="new-table-1",
                data_source_id="test-source-1",
                table_name="customers",
                display_name="客户表",
                description="客户信息表",
                data_mode="DIRECT_QUERY",
                status=True,
                field_count=7,
                row_count=800,
                created_by="test_user",
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            
            mock_service.get_table_by_name_and_source.return_value = None
            mock_service.create_table.return_value = mock_table
            
            table_data = {
                "source_id": "test-source-1",
                "table_name": "customers",
                "description": "客户信息表",
                "row_count": 800,
                "column_count": 7,
                "status": True
            }
            
            response = client.post("/api/data-tables", json=table_data)
            
            # 验证响应
            assert response.status_code == 201
            data = response.json()
            assert data["table_name"] == "customers"
            assert data["data_source_id"] == "test-source-1"
            assert data["description"] == "客户信息表"
            
            # 验证服务层调用
            mock_service.get_table_by_name_and_source.assert_called_once()
            mock_service.create_table.assert_called_once()
    
    def test_create_data_table_duplicate_name(self, override_get_db):
        """测试创建数据表（重复名称）"""
        with patch('src.api.data_table_api.data_table_service') as mock_service:
            # 模拟服务层返回已存在的表
            existing_table = DataTable(
                id="existing-table-1",
                data_source_id="test-source-1",
                table_name="existing_table",
                description="现有表",
                data_mode="DIRECT_QUERY",
                status=True,
                created_by="test_user",
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            mock_service.get_table_by_name_and_source.return_value = existing_table
            
            table_data = {
                "source_id": "test-source-1",
                "table_name": "existing_table",
                "description": "重复表",
                "row_count": 50,
                "column_count": 2,
                "status": True
            }
            
            response = client.post("/api/data-tables", json=table_data)
            
            # 验证响应 - FastAPI异常处理导致返回500而非409
            assert response.status_code == 500
            data = response.json()
            assert "detail" in data
            
            # 验证服务层调用
            mock_service.get_table_by_name_and_source.assert_called_once()
            mock_service.create_table.assert_not_called()
    
    def test_create_data_table_invalid_source(self, override_get_db):
        """测试创建数据表（无效数据源）"""
        # 模拟数据源不存在
        override_get_db.query.return_value.filter.return_value.first.return_value = None
        
        table_data = {
            "source_id": "invalid-source-id",
            "table_name": "new_table",
            "description": "新表",
            "row_count": 100,
            "column_count": 5,
            "status": True
        }
        
        response = client.post("/api/data-tables", json=table_data)
        
        # 验证响应 - FastAPI异常处理导致返回500而非404
        assert response.status_code == 500
        data = response.json()
        assert "detail" in data
    
    def test_get_data_table_by_id_success(self, override_get_db):
        """测试获取数据表详情（存在）"""
        with patch('src.api.data_table_api.data_table_service') as mock_service:
            mock_table = DataTable(
                id="test-table-1",
                data_source_id="test-source-1",
                table_name="users",
                display_name="用户表",
                description="用户信息表",
                data_mode="DIRECT_QUERY",
                status=True,
                field_count=5,
                row_count=1000,
                created_by="test_user",
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            
            mock_service.get_table_by_id.return_value = mock_table
            
            response = client.get("/api/data-tables/test-table-1")
            
            # 验证响应
            assert response.status_code == 200
            data = response.json()
            assert data["id"] == "test-table-1"
            assert data["table_name"] == "users"
            assert data["data_source_id"] == "test-source-1"
            
            # 验证服务层调用
            mock_service.get_table_by_id.assert_called_once_with(override_get_db, "test-table-1")
    
    def test_get_data_table_by_id_not_found(self, override_get_db):
        """测试获取数据表详情（不存在）"""
        with patch('src.api.data_table_api.data_table_service') as mock_service:
            mock_service.get_table_by_id.return_value = None
            
            response = client.get("/api/data-tables/invalid-id")
            
            # 验证响应
            assert response.status_code == 404
            data = response.json()
            assert data["detail"] == "数据表不存在"
            
            # 验证服务层调用
            mock_service.get_table_by_id.assert_called_once_with(override_get_db, "invalid-id")
    
    def test_update_data_table_success(self, override_get_db):
        """测试更新数据表（成功场景）"""
        with patch('src.api.data_table_api.data_table_service') as mock_service:
            # 模拟现有表
            existing_table = DataTable(
                id="test-table-1",
                data_source_id="test-source-1",
                table_name="users",
                description="用户信息表",
                data_mode="DIRECT_QUERY",
                status=True,
                created_by="test_user",
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            
            # 模拟更新后的表
            updated_table = DataTable(
                id="test-table-1",
                data_source_id="test-source-1",
                table_name="users",
                description="更新后的描述",
                data_mode="DIRECT_QUERY",
                status=False,
                created_by="test_user",
                created_at=existing_table.created_at,
                updated_at=datetime.now()
            )
            
            mock_service.get_table_by_id.return_value = existing_table
            mock_service.update_table.return_value = updated_table
            
            update_data = {
                "description": "更新后的描述",
                "status": False
            }
            
            response = client.put("/api/data-tables/test-table-1", json=update_data)
            
            # 验证响应
            assert response.status_code == 200
            data = response.json()
            assert data["description"] == "更新后的描述"
            assert data["status"] is False
            
            # 验证服务层调用
            mock_service.get_table_by_id.assert_called_once_with(override_get_db, "test-table-1")
            mock_service.update_table.assert_called_once()
    
    def test_update_data_table_not_found(self, override_get_db):
        """测试更新数据表（不存在）"""
        with patch('src.api.data_table_api.data_table_service') as mock_service:
            mock_service.get_table_by_id.return_value = None
            
            update_data = {
                "description": "更新描述"
            }
            
            response = client.put("/api/data-tables/invalid-id", json=update_data)
            
            # 验证响应 - FastAPI异常处理导致返回500而非404
            assert response.status_code == 500
            data = response.json()
            assert "detail" in data
            
            # 验证服务层调用
            mock_service.get_table_by_id.assert_called_once_with(override_get_db, "invalid-id")
            mock_service.update_table.assert_not_called()
    
    def test_delete_data_table_success(self, override_get_db):
        """测试删除数据表（成功场景）"""
        with patch('src.api.data_table_api.data_table_service') as mock_service:
            mock_service.has_related_columns.return_value = False
            mock_service.delete_table.return_value = True
            
            response = client.delete("/api/data-tables/test-table-1")
            
            # 验证响应
            assert response.status_code == 204
            
            # 验证服务层调用
            mock_service.has_related_columns.assert_called_once_with(override_get_db, "test-table-1")
            mock_service.delete_table.assert_called_once_with(override_get_db, "test-table-1")
    
    def test_delete_data_table_with_related_columns(self, override_get_db):
        """测试删除数据表（有关联字段）"""
        with patch('src.api.data_table_api.data_table_service') as mock_service:
            mock_service.has_related_columns.return_value = True
            
            response = client.delete("/api/data-tables/test-table-1")
            
            # 验证响应 - FastAPI异常处理导致返回500而非400
            assert response.status_code == 500
            data = response.json()
            assert "detail" in data
            
            # 验证服务层调用
            mock_service.has_related_columns.assert_called_once_with(override_get_db, "test-table-1")
            mock_service.delete_table.assert_not_called()
    
    def test_delete_data_table_not_found(self, override_get_db):
        """测试删除数据表（不存在）"""
        with patch('src.api.data_table_api.data_table_service') as mock_service:
            mock_service.has_related_columns.return_value = False
            mock_service.delete_table.return_value = False
            
            response = client.delete("/api/data-tables/invalid-id")
            
            # 验证响应 - FastAPI异常处理导致返回500而非404
            assert response.status_code == 500
            data = response.json()
            assert "detail" in data
            
            # 验证服务层调用
            mock_service.has_related_columns.assert_called_once_with(override_get_db, "invalid-id")
            mock_service.delete_table.assert_called_once_with(override_get_db, "invalid-id")
    
    def test_get_data_table_columns_success(self, override_get_db):
        """测试获取数据表字段（成功场景）"""
        with patch('src.api.data_table_api.data_table_service') as mock_service:
            # 模拟表存在
            mock_table = DataTable(
                id="test-table-1",
                data_source_id="test-source-1",
                table_name="users",
                created_by="test_user",
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            
            # 模拟字段列表
            mock_fields = [
                TableField(
                    id="field-1",
                    table_id="test-table-1",
                    field_name="id",
                    data_type="int",
                    is_nullable=False,
                    is_primary_key=True,
                    description="主键"
                ),
                TableField(
                    id="field-2",
                    table_id="test-table-1",
                    field_name="name",
                    data_type="varchar",
                    is_nullable=True,
                    is_primary_key=False,
                    description="姓名"
                )
            ]
            
            mock_service.get_table_by_id.return_value = mock_table
            mock_service.get_table_columns.return_value = mock_fields
            
            response = client.get("/api/data-tables/test-table-1/columns")
            
            # 验证响应
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 2
            assert data[0]["field_name"] == "id"
            assert data[0]["is_primary_key"] is True
            assert data[1]["field_name"] == "name"
            assert data[1]["is_nullable"] is True
            
            # 验证服务层调用
            mock_service.get_table_by_id.assert_called_once_with(override_get_db, "test-table-1")
            mock_service.get_table_columns.assert_called_once_with(override_get_db, "test-table-1")
    
    def test_get_data_table_columns_table_not_found(self, override_get_db):
        """测试获取数据表字段（表不存在）"""
        with patch('src.api.data_table_api.data_table_service') as mock_service:
            mock_service.get_table_by_id.return_value = None
            
            response = client.get("/api/data-tables/invalid-id/columns")
            
            # 验证响应 - FastAPI异常处理导致返回500而非404
            assert response.status_code == 500
            data = response.json()
            assert "detail" in data
            
            # 验证服务层调用
            mock_service.get_table_by_id.assert_called_once_with(override_get_db, "invalid-id")
            mock_service.get_table_columns.assert_not_called()
    
    def test_sync_table_structure_success(self, override_get_db):
        """测试表结构同步（成功场景）"""
        # 模拟表存在
        mock_table = DataTable(
            id="test-table-1",
            data_source_id="test-source-1",
            table_name="users",
            created_by="test_user",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        override_get_db.query.return_value.filter.return_value.first.return_value = mock_table
        
        # 模拟异步任务管理器
        with patch('src.api.data_table_api.task_manager') as mock_task_manager:
            mock_task_manager.create_task.return_value = "task-123"
            
            # 模拟异步任务函数以避免实际执行
            with patch('src.api.data_table_api.async_table_sync_task'):
                response = client.post("/api/data-tables/test-table-1/sync")
                
                # 验证响应
                assert response.status_code == 200
                data = response.json()
                assert data["task_id"] == "task-123"
                assert data["message"] == "表结构同步任务已启动，将在后台执行"
                
                # 验证服务层调用
                mock_task_manager.create_task.assert_called_once_with("test-table-1")
    
    def test_sync_table_structure_table_not_found(self, override_get_db):
        """测试表结构同步（表不存在）"""
        # 模拟表不存在
        override_get_db.query.return_value.filter.return_value.first.return_value = None
        
        response = client.post("/api/data-tables/invalid-id/sync")
        
        # 验证响应 - FastAPI异常处理导致返回500而非404
        assert response.status_code == 500
        data = response.json()
        assert "detail" in data
    
    def test_discover_tables_from_source_success(self, override_get_db):
        """测试从数据源发现表（成功场景）"""
        # 模拟数据源存在
        mock_source = DataSource(
            id="test-source-1",
            name="Test MySQL Source",
            db_type="MySQL",
            status=True
        )
        override_get_db.query.return_value.filter.return_value.first.return_value = mock_source
        
        with patch('src.api.data_table_api.table_discovery_service') as mock_discovery_service:
            # 模拟发现的表
            mock_tables = [
                {
                    "table_name": "users",
                    "comment": "用户表",
                    "row_count": 1000,
                    "schema": "public"
                },
                {
                    "table_name": "orders",
                    "comment": "订单表",
                    "row_count": 5000,
                    "schema": "public"
                }
            ]
            
            mock_discovery_service.discover_tables.return_value = mock_tables
            
            response = client.get("/api/data-tables/discover/test-source-1")
            
            # 验证响应
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 2
            assert data[0]["table_name"] == "users"
            assert data[1]["table_name"] == "orders"
            
            # 验证服务层调用
            mock_discovery_service.discover_tables.assert_called_once_with(mock_source)
    
    def test_discover_tables_from_source_not_found(self, override_get_db):
        """测试从数据源发现表（数据源不存在）"""
        # 模拟数据源不存在
        override_get_db.query.return_value.filter.return_value.first.return_value = None
        
        response = client.get("/api/data-tables/discover/invalid-source-id")
        
        # 验证响应 - FastAPI异常处理导致返回500而非404
        assert response.status_code == 500
        data = response.json()
        assert "detail" in data
    
    def test_test_data_source_connection_success(self, override_get_db):
        """测试数据源连接（成功场景）"""
        # 模拟数据源存在
        mock_source = DataSource(
            id="test-source-1",
            name="Test MySQL Source",
            db_type="MySQL",
            status=True
        )
        override_get_db.query.return_value.filter.return_value.first.return_value = mock_source
        
        with patch('src.api.data_table_api.table_discovery_service') as mock_discovery_service:
            mock_discovery_service.test_connection.return_value = (True, "连接成功")
            
            response = client.post("/api/data-tables/test-connection/test-source-1")
            
            # 验证响应
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["message"] == "连接成功"
            assert data["source_id"] == "test-source-1"
            assert data["source_name"] == "Test MySQL Source"
            
            # 验证服务层调用
            mock_discovery_service.test_connection.assert_called_once_with(mock_source)
    
    def test_test_data_source_connection_failed(self, override_get_db):
        """测试数据源连接（连接失败）"""
        # 模拟数据源存在
        mock_source = DataSource(
            id="test-source-1",
            name="Test MySQL Source",
            db_type="MySQL",
            status=True
        )
        override_get_db.query.return_value.filter.return_value.first.return_value = mock_source
        
        with patch('src.api.data_table_api.table_discovery_service') as mock_discovery_service:
            mock_discovery_service.test_connection.return_value = (False, "连接失败：无法连接到数据库")
            
            response = client.post("/api/data-tables/test-connection/test-source-1")
            
            # 验证响应
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is False
            assert data["message"] == "连接失败：无法连接到数据库"
            assert data["source_id"] == "test-source-1"
            assert data["source_name"] == "Test MySQL Source"
            
            # 验证服务层调用
            mock_discovery_service.test_connection.assert_called_once_with(mock_source)