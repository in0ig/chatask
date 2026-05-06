"""
数据表API单元测试
"""
import pytest
from fastapi.testclient import TestClient
from datetime import datetime
import uuid
import os
import logging
from unittest.mock import patch, Mock
from sqlalchemy.orm import Session
from src.models.data_preparation_model import DataTable, TableField
from src.models.data_source_model import DataSource
from src.services.data_table_service import DataTableService
from src.services.table_sync import TableSyncService
from src.database import get_db
from src.main import app

# 设置测试模式环境变量，必须在导入应用之前设置
os.environ["TEST_MODE"] = "true"

# 设置日志记录器
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 创建测试客户端
client = TestClient(app)

@pytest.fixture(scope="module")
def setup_database():
    """设置测试数据库"""
    # 获取测试数据库会话生成器
    db_generator = get_db()
    db = next(db_generator)
    
    try:
        # 创建测试数据源
        now = datetime.now()
        source1 = DataSource(
            id=str(uuid.uuid4()),
            name="Test Source 1",
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
            created_at=now,
            updated_at=now
        )
        
        db.add(source1)
        db.commit()
        
        # 创建测试数据表
        table1 = DataTable(
            id=str(uuid.uuid4()),
            data_source_id=source1.id,
            table_name="users",
            description="用户信息表",
            row_count=1000,
            field_count=5,
            status=True,
            data_mode="DIRECT_QUERY",
            created_by="test_user",
            created_at=now,
            updated_at=now
        )
        
        db.add(table1)
        db.commit()
        
        yield db
        
    finally:
        # 清理：关闭数据库会话
        db.close()
        # 关闭生成器
        try:
            next(db_generator)
        except StopIteration:
            pass

@pytest.fixture
def mock_table_service():
    """模拟DataTableService"""
    with patch('src.api.data_table_api.data_table_service') as mock_service:
        yield mock_service

@pytest.fixture
def mock_sync_service():
    """模拟TableSyncService"""
    with patch('src.services.table_sync.sync_service') as mock_service:
        yield mock_service

class TestCreateDataTable:
    """测试创建数据表"""
    
    def test_create_data_table_success(self, setup_database, mock_table_service):
        """测试创建数据表（成功场景）"""
        # 准备测试数据
        source = setup_database.query(DataSource).first()
        
        # 模拟服务层返回
        mock_table_service.get_table_by_name_and_source.return_value = None
        mock_table_service.create_table.return_value = DataTable(
            id=str(uuid.uuid4()),
            data_source_id=source.id,
            table_name="customers_12345",
            description="客户信息表",
            row_count=800,
            field_count=7,
            status=True,
            created_by="test_user",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        table_data = {
            "source_id": source.id,
            "table_name": "customers_12345",
            "description": "客户信息表",
            "row_count": 800,
            "column_count": 7,
            "status": True
        }
        
        response = client.post("/api/data-tables", json=table_data)
        
        # 验证响应
        assert response.status_code == 201
        data = response.json()
        assert data["table_name"] == "customers_12345"
        assert data["data_source_id"] == source.id
        assert data["description"] == "客户信息表"
        
        # 验证服务层调用
        mock_table_service.get_table_by_name_and_source.assert_called_once_with(
            setup_database, "customers_12345", source.id
        )
        mock_table_service.create_table.assert_called_once()
    
    def test_create_data_table_duplicate_name(self, setup_database, mock_table_service):
        """测试创建数据表（重复名称）"""
        # 准备测试数据
        source = setup_database.query(DataSource).first()
        
        # 模拟服务层返回已存在的表
        existing_table = DataTable(
            id=str(uuid.uuid4()),
            data_source_id=source.id,
            table_name="existing_table",
            description="现有表",
            row_count=100,
            field_count=3,
            status=True,
            created_by="test_user",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        mock_table_service.get_table_by_name_and_source.return_value = existing_table
        
        table_data = {
            "source_id": source.id,
            "table_name": "existing_table",
            "description": "重复表",
            "row_count": 50,
            "column_count": 2,
            "status": True
        }
        
        response = client.post("/api/data-tables", json=table_data)
        
        # 验证响应
        assert response.status_code == 409
        data = response.json()
        assert "已存在同名表" in data["detail"]
        
        # 验证服务层调用
        mock_table_service.get_table_by_name_and_source.assert_called_once_with(
            setup_database, "existing_table", source.id
        )
        mock_table_service.create_table.assert_not_called()
    
    def test_create_data_table_invalid_source(self, setup_database, mock_table_service):
        """测试创建数据表（无效数据源）"""
        # 使用不存在的数据源ID
        invalid_source_id = str(uuid.uuid4())
        
        # 模拟服务层返回None（数据源不存在）
        mock_table_service.get_table_by_name_and_source.return_value = None
        
        table_data = {
            "source_id": invalid_source_id,
            "table_name": "new_table",
            "description": "新表",
            "row_count": 100,
            "column_count": 5,
            "status": True
        }
        
        response = client.post("/api/data-tables", json=table_data)
        
        # 验证响应
        assert response.status_code == 404
        data = response.json()
        assert "数据源不存在" in data["detail"]
        
        # 验证服务层调用
        mock_table_service.get_table_by_name_and_source.assert_called_once_with(
            setup_database, "new_table", invalid_source_id
        )
        mock_table_service.create_table.assert_not_called()


class TestGetDataTableList:
    """测试获取数据表列表"""
    
    def test_get_data_tables_list(self, setup_database, mock_table_service):
        """测试获取数据表列表（默认参数）"""
        # 准备测试数据
        source = setup_database.query(DataSource).first()
        
        # 模拟服务层返回
        mock_table_service.get_all_tables.return_value = {
            "items": [
                {
                    "id": str(uuid.uuid4()),
                    "table_name": "users",
                    "data_source_id": source.id,
                    "description": "用户信息表",
                    "row_count": 1000,
                    "field_count": 5,
                    "status": True
                }
            ],
            "total": 1,
            "page": 1,
            "page_size": 10
        }
        
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
        mock_table_service.get_all_tables.assert_called_once_with(
            setup_database, page=1, page_size=10, search=None, source_id=None, status=None
        )
    
    def test_get_data_tables_list_with_filters(self, setup_database, mock_table_service):
        """测试获取数据表列表（带筛选条件）"""
        # 准备测试数据
        source = setup_database.query(DataSource).first()
        
        # 模拟服务层返回
        mock_table_service.get_all_tables.return_value = {
            "items": [],
            "total": 0,
            "page": 1,
            "page_size": 5
        }
        
        # 测试搜索、数据源筛选和状态筛选
        response = client.get("/api/data-tables", params={
            "page": 2,
            "page_size": 5,
            "search": "user",
            "source_id": source.id,
            "status": True
        })
        
        # 验证响应
        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 2
        assert data["page_size"] == 5
        assert data["total"] == 0
        
        # 验证服务层调用
        mock_table_service.get_all_tables.assert_called_once_with(
            setup_database, page=2, page_size=5, search="user", source_id=source.id, status=True
        )
    
    def test_get_data_tables_list_invalid_page_size(self, setup_database, mock_table_service):
        """测试获取数据表列表（无效页大小）"""
        # 测试超出范围的页大小
        response = client.get("/api/data-tables", params={"page_size": 150})
        
        # 验证响应
        assert response.status_code == 422  # Unprocessable Entity
        
        # 测试小于1的页大小
        response = client.get("/api/data-tables", params={"page_size": 0})
        
        # 验证响应
        assert response.status_code == 422  # Unprocessable Entity


class TestGetDataTable:
    """测试获取数据表详情"""
    
    def test_get_data_table_by_id_success(self, setup_database, mock_table_service):
        """测试获取数据表详情（存在）"""
        # 获取测试数据
        table = setup_database.query(DataTable).first()
        
        # 模拟服务层返回
        mock_table_service.get_table_by_id.return_value = table
        
        response = client.get(f"/api/data-tables/{table.id}")
        
        # 验证响应
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == table.id
        assert data["table_name"] == table.table_name
        assert data["data_source_id"] == table.data_source_id
        
        # 验证服务层调用
        mock_table_service.get_table_by_id.assert_called_once_with(setup_database, table.id)
    
    def test_get_data_table_by_id_not_found(self, setup_database, mock_table_service):
        """测试获取数据表详情（不存在）"""
        # 使用不存在的ID
        invalid_id = str(uuid.uuid4())
        
        # 模拟服务层返回None
        mock_table_service.get_table_by_id.return_value = None
        
        response = client.get(f"/api/data-tables/{invalid_id}")
        
        # 验证响应
        assert response.status_code == 404
        data = response.json()
        assert data["detail"] == "数据表不存在"
        
        # 验证服务层调用
        mock_table_service.get_table_by_id.assert_called_once_with(setup_database, invalid_id)


class TestUpdateDataTable:
    """测试更新数据表"""
    
    def test_update_data_table_success(self, setup_database, mock_table_service):
        """测试更新数据表（成功场景）"""
        # 获取测试数据
        table = setup_database.query(DataTable).first()
        
        # 模拟服务层返回更新后的表
        updated_table = DataTable(
            id=table.id,
            data_source_id=table.data_source_id,
            table_name=table.table_name,
            description="更新后的描述",
            row_count=table.row_count,
            field_count=table.field_count,
            status=False,
            created_by=table.created_by,
            created_at=table.created_at,
            updated_at=datetime.now()
        )
        mock_table_service.update_table.return_value = updated_table
        
        update_data = {
            "description": "更新后的描述",
            "status": False
        }
        
        response = client.put(f"/api/data-tables/{table.id}", json=update_data)
        
        # 验证响应
        assert response.status_code == 200
        data = response.json()
        assert data["description"] == "更新后的描述"
        assert data["status"] is False
        
        # 验证服务层调用
        mock_table_service.update_table.assert_called_once_with(
            setup_database, table.id, update_data
        )
    
    def test_update_data_table_change_source_success(self, setup_database, mock_table_service):
        """测试更新数据表（更改数据源成功）"""
        # 获取测试数据
        table = setup_database.query(DataTable).first()
        
        # 创建另一个数据源
        new_source = DataSource(
            id=str(uuid.uuid4()),
            name="Test Source 2",
            source_type="DATABASE",
            db_type="MySQL",
            host="localhost",
            port=3306,
            database_name="test_db2",
            auth_type="SQL_AUTH",
            username="test_user",
            password="encrypted_password",
            status=True,
            created_by="test_user",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        setup_database.add(new_source)
        setup_database.commit()
        
        # 模拟服务层返回更新后的表
        updated_table = DataTable(
            id=table.id,
            data_source_id=new_source.id,
            table_name=table.table_name,
            description=table.description,
            row_count=table.row_count,
            field_count=table.field_count,
            status=table.status,
            created_by=table.created_by,
            created_at=table.created_at,
            updated_at=datetime.now()
        )
        mock_table_service.update_table.return_value = updated_table
        
        # 模拟检查新数据源是否存在
        mock_table_service.get_table_by_name_and_source.return_value = None
        
        update_data = {
            "source_id": new_source.id
        }
        
        response = client.put(f"/api/data-tables/{table.id}", json=update_data)
        
        # 验证响应
        assert response.status_code == 200
        data = response.json()
        assert data["data_source_id"] == new_source.id
        
        # 验证服务层调用
        mock_table_service.get_table_by_name_and_source.assert_called_once_with(
            setup_database, table.table_name, new_source.id
        )
        mock_table_service.update_table.assert_called_once_with(
            setup_database, table.id, update_data
        )
    
    def test_update_data_table_change_source_duplicate(self, setup_database, mock_table_service):
        """测试更新数据表（更改数据源时存在同名表）"""
        # 获取测试数据
        table = setup_database.query(DataTable).first()
        
        # 创建另一个数据源
        new_source = DataSource(
            id=str(uuid.uuid4()),
            name="Test Source 2",
            source_type="DATABASE",
            db_type="MySQL",
            host="localhost",
            port=3306,
            database_name="test_db2",
            auth_type="SQL_AUTH",
            username="test_user",
            password="encrypted_password",
            status=True,
            created_by="test_user",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        setup_database.add(new_source)
        setup_database.commit()
        
        # 创建另一个具有相同表名的表
        duplicate_table = DataTable(
            id=str(uuid.uuid4()),
            data_source_id=new_source.id,
            table_name=table.table_name,
            description="重复表",
            row_count=100,
            field_count=3,
            status=True,
            created_by="test_user",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        setup_database.add(duplicate_table)
        setup_database.commit()
        
        # 模拟服务层返回已存在的表
        mock_table_service.get_table_by_name_and_source.return_value = duplicate_table
        
        update_data = {
            "source_id": new_source.id
        }
        
        response = client.put(f"/api/data-tables/{table.id}", json=update_data)
        
        # 验证响应
        assert response.status_code == 409
        data = response.json()
        assert "已存在同名表" in data["detail"]
        
        # 验证服务层调用
        mock_table_service.get_table_by_name_and_source.assert_called_once_with(
            setup_database, table.table_name, new_source.id
        )
        mock_table_service.update_table.assert_not_called()
    
    def test_update_data_table_invalid_source(self, setup_database, mock_table_service):
        """测试更新数据表（无效数据源）"""
        # 获取测试数据
        table = setup_database.query(DataTable).first()
        
        # 使用不存在的数据源ID
        invalid_source_id = str(uuid.uuid4())
        
        # 模拟服务层返回None（数据源不存在）
        mock_table_service.get_table_by_name_and_source.return_value = None
        
        update_data = {
            "source_id": invalid_source_id
        }
        
        response = client.put(f"/api/data-tables/{table.id}", json=update_data)
        
        # 验证响应
        assert response.status_code == 404
        data = response.json()
        assert "数据源不存在" in data["detail"]
        
        # 验证服务层调用
        mock_table_service.get_table_by_name_and_source.assert_called_once_with(
            setup_database, table.table_name, invalid_source_id
        )
        mock_table_service.update_table.assert_not_called()
    
    def test_update_data_table_not_found(self, setup_database, mock_table_service):
        """测试更新数据表（不存在）"""
        # 使用不存在的表ID
        invalid_id = str(uuid.uuid4())
        
        # 模拟服务层返回None
        mock_table_service.get_table_by_id.return_value = None
        
        update_data = {
            "description": "更新描述"
        }
        
        response = client.put(f"/api/data-tables/{invalid_id}", json=update_data)
        
        # 验证响应
        assert response.status_code == 404
        data = response.json()
        assert data["detail"] == "数据表不存在"
        
        # 验证服务层调用
        mock_table_service.get_table_by_id.assert_called_once_with(setup_database, invalid_id)
        mock_table_service.update_table.assert_not_called()


class TestDeleteDataTable:
    """测试删除数据表"""
    
    def test_delete_data_table_success(self, setup_database, mock_table_service):
        """测试删除数据表（成功场景）"""
        # 获取测试数据
        table = setup_database.query(DataTable).first()
        
        # 模拟服务层返回没有关联字段
        mock_table_service.has_related_columns.return_value = False
        mock_table_service.delete_table.return_value = True
        
        response = client.delete(f"/api/data-tables/{table.id}")
        
        # 验证响应
        assert response.status_code == 204
        
        # 验证服务层调用
        mock_table_service.has_related_columns.assert_called_once_with(setup_database, table.id)
        mock_table_service.delete_table.assert_called_once_with(setup_database, table.id)
    
    def test_delete_data_table_with_related_columns(self, setup_database, mock_table_service):
        """测试删除数据表（有关联字段）"""
        # 获取测试数据
        table = setup_database.query(DataTable).first()
        
        # 模拟服务层返回有关联字段
        mock_table_service.has_related_columns.return_value = True
        
        response = client.delete(f"/api/data-tables/{table.id}")
        
        # 验证响应
        assert response.status_code == 400
        data = response.json()
        assert "无法删除" in data["detail"] and "关联的字段" in data["detail"]
        
        # 验证服务层调用
        mock_table_service.has_related_columns.assert_called_once_with(setup_database, table.id)
        mock_table_service.delete_table.assert_not_called()
    
    def test_delete_data_table_not_found(self, setup_database, mock_table_service):
        """测试删除数据表（不存在）"""
        # 使用不存在的表ID
        invalid_id = str(uuid.uuid4())
        
        # 模拟服务层返回False（表不存在）
        mock_table_service.has_related_columns.return_value = False
        mock_table_service.delete_table.return_value = False
        
        response = client.delete(f"/api/data-tables/{invalid_id}")
        
        # 验证响应
        assert response.status_code == 404
        data = response.json()
        assert data["detail"] == "数据表不存在"
        
        # 验证服务层调用
        mock_table_service.has_related_columns.assert_called_once_with(setup_database, invalid_id)
        mock_table_service.delete_table.assert_called_once_with(setup_database, invalid_id)


class TestSyncTableStructure:
    """测试表结构同步"""
    
    def test_sync_table_structure_success(self, setup_database, mock_sync_service):
        """测试表结构同步（成功场景）"""
        # 获取测试数据
        table = setup_database.query(DataTable).first()
        
        # 模拟同步服务返回成功结果
        mock_sync_service.sync_table_structure.return_value = {
            'created': 3,
            'updated': 1,
            'deleted': 0
        }
        
        # 模拟异步任务管理器
        with patch('src.api.data_table_api.task_manager') as mock_task_manager:
            mock_task_manager.create_task.return_value = "task-123"
            
            response = client.post(f"/api/data-tables/{table.id}/sync")
            
            # 验证响应
            assert response.status_code == 200
            data = response.json()
            assert data["task_id"] == "task-123"
            assert data["message"] == "表结构同步任务已启动，将在后台执行"
            
            # 验证服务层调用
            mock_sync_service.sync_table_structure.assert_not_called()  # 异步执行，不立即调用
            mock_task_manager.create_task.assert_called_once_with(table.id)
    
    def test_sync_table_structure_table_not_found(self, setup_database, mock_sync_service):
        """测试表结构同步（表不存在）"""
        # 使用不存在的表ID
        invalid_id = str(uuid.uuid4())
        
        response = client.post(f"/api/data-tables/{invalid_id}/sync")
        
        # 验证响应
        assert response.status_code == 404
        data = response.json()
        assert data["detail"] == "数据表不存在"
        
        # 验证服务层调用
        mock_sync_service.sync_table_structure.assert_not_called()
    
    def test_sync_table_structure_connection_error(self, setup_database, mock_sync_service):
        """测试表结构同步（连接错误）"""
        # 获取测试数据
        table = setup_database.query(DataTable).first()
        
        # 模拟同步服务抛出连接错误
        mock_sync_service.sync_table_structure.side_effect = ConnectionError("数据库连接失败")
        
        # 模拟异步任务管理器
        with patch('src.api.data_table_api.task_manager') as mock_task_manager:
            mock_task_manager.create_task.return_value = "task-123"
            
            response = client.post(f"/api/data-tables/{table.id}/sync")
            
            # 验证响应
            assert response.status_code == 200
            data = response.json()
            assert data["task_id"] == "task-123"
            assert data["message"] == "表结构同步任务已启动，将在后台执行"
            
            # 验证服务层调用
            mock_sync_service.sync_table_structure.assert_not_called()  # 异步执行，不立即调用
            mock_task_manager.create_task.assert_called_once_with(table.id)


class TestGetTableColumns:
    """测试获取数据表字段"""
    
    def test_get_data_table_columns_success(self, setup_database, mock_table_service):
        """测试获取数据表字段（成功场景）"""
        # 获取测试数据
        table = setup_database.query(DataTable).first()
        
        # 模拟服务层返回字段列表
        mock_table_service.get_table_columns.return_value = [
            TableField(
                id=str(uuid.uuid4()),
                table_id=table.id,
                field_name="id",
                data_type="int",
                is_nullable=False,
                is_primary_key=True,
                description="主键"
            ),
            TableField(
                id=str(uuid.uuid4()),
                table_id=table.id,
                field_name="name",
                data_type="varchar",
                is_nullable=True,
                is_primary_key=False,
                description="姓名"
            )
        ]
        
        response = client.get(f"/api/data-tables/{table.id}/columns")
        
        # 验证响应
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["field_name"] == "id"
        assert data[0]["is_primary_key"] is True
        assert data[1]["field_name"] == "name"
        assert data[1]["is_nullable"] is True
        
        # 验证服务层调用
        mock_table_service.get_table_columns.assert_called_once_with(setup_database, table.id)
    
    def test_get_data_table_columns_table_not_found(self, setup_database, mock_table_service):
        """测试获取数据表字段（表不存在）"""
        # 使用不存在的表ID
        invalid_id = str(uuid.uuid4())
        
        # 模拟服务层返回None
        mock_table_service.get_table_by_id.return_value = None
        
        response = client.get(f"/api/data-tables/{invalid_id}/columns")
        
        # 验证响应
        assert response.status_code == 404
        data = response.json()
        assert data["detail"] == "数据表不存在"
        
        # 验证服务层调用
        mock_table_service.get_table_by_id.assert_called_once_with(setup_database, invalid_id)
        mock_table_service.get_table_columns.assert_not_called()


class TestRefreshDataTable:
    """测试刷新数据表"""
    
    def test_refresh_data_table_success(self, setup_database, mock_table_service):
        """测试刷新数据表（成功场景）"""
        # 获取测试数据
        table = setup_database.query(DataTable).first()
        
        # 模拟服务层返回
        mock_table_service.get_table_by_id.return_value = table
        
        # 模拟同步服务
        with patch('src.services.table_sync.sync_service') as mock_sync_service:
            mock_sync_service.sync_table_structure.return_value = {
                'created': 0,
                'updated': 0,
                'deleted': 0
            }
            
            response = client.post(f"/api/data-tables/{table.id}/refresh")
            
            # 验证响应
            assert response.status_code == 200
            data = response.json()
            assert data["id"] == table.id
            assert "last_refreshed" in data
            
            # 验证服务层调用
            mock_table_service.get_table_by_id.assert_called_once_with(setup_database, table.id)
            mock_sync_service.sync_table_structure.assert_called_once_with(setup_database, table.id)
    
    def test_refresh_data_table_table_not_found(self, setup_database, mock_table_service):
        """测试刷新数据表（表不存在）"""
        # 使用不存在的表ID
        invalid_id = str(uuid.uuid4())
        
        # 模拟服务层返回None
        mock_table_service.get_table_by_id.return_value = None
        
        response = client.post(f"/api/data-tables/{invalid_id}/refresh")
        
        # 验证响应
        assert response.status_code == 404
        data = response.json()
        assert data["detail"] == "数据表不存在"
        
        # 验证服务层调用
        mock_table_service.get_table_by_id.assert_called_once_with(setup_database, invalid_id)


class TestGetSyncTaskStatus:
    """测试获取同步任务状态"""
    
    def test_get_sync_task_status_success(self, setup_database):
        """测试获取同步任务状态（成功场景）"""
        # 获取测试数据
        table = setup_database.query(DataTable).first()
        
        # 模拟任务管理器
        with patch('src.api.data_table_api.task_manager') as mock_task_manager:
            mock_task_manager.get_task.return_value = {
                "table_id": table.id,
                "status": "completed",
                "progress": 100,
                "started_at": datetime.now(),
                "ended_at": datetime.now(),
                "result": {"created": 3, "updated": 1, "deleted": 0},
                "error": None
            }
            
            response = client.get(f"/api/data-tables/{table.id}/sync/status", params={"task_id": "task-123"})
            
            # 验证响应
            assert response.status_code == 200
            data = response.json()
            assert data["task_id"] == "task-123"
            assert data["table_id"] == table.id
            assert data["status"] == "completed"
            assert data["progress"] == 100
            assert data["result"] == {"created": 3, "updated": 1, "deleted": 0}
            
            # 验证服务层调用
            mock_task_manager.get_task.assert_called_once_with("task-123")
    
    def test_get_sync_task_status_table_not_found(self, setup_database):
        """测试获取同步任务状态（表不存在）"""
        # 使用不存在的表ID
        invalid_id = str(uuid.uuid4())
        
        response = client.get(f"/api/data-tables/{invalid_id}/sync/status", params={"task_id": "task-123"})
        
        # 验证响应
        assert response.status_code == 404
        data = response.json()
        assert data["detail"] == "数据表不存在"
    
    def test_get_sync_task_status_task_not_found(self, setup_database):
        """测试获取同步任务状态（任务不存在）"""
        # 获取测试数据
        table = setup_database.query(DataTable).first()
        
        # 模拟任务管理器
        with patch('src.api.data_table_api.task_manager') as mock_task_manager:
            mock_task_manager.get_task.return_value = None
            
            response = client.get(f"/api/data-tables/{table.id}/sync/status", params={"task_id": "task-123"})
            
            # 验证响应
            assert response.status_code == 404
            data = response.json()
            assert data["detail"] == "同步任务不存在"
            
            # 验证服务层调用
            mock_task_manager.get_task.assert_called_once_with("task-123")
    
    def test_get_sync_task_status_task_mismatch(self, setup_database):
        """测试获取同步任务状态（任务与表不匹配）"""
        # 获取测试数据
        table = setup_database.query(DataTable).first()
        
        # 创建另一个表
        new_table = DataTable(
            id=str(uuid.uuid4()),
            data_source_id=table.data_source_id,
            table_name="another_table",
            description="另一个表",
            row_count=50,
            field_count=3,
            status=True,
            created_by="test_user",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        setup_database.add(new_table)
        setup_database.commit()
        
        # 模拟任务管理器
        with patch('src.api.data_table_api.task_manager') as mock_task_manager:
            mock_task_manager.get_task.return_value = {
                "table_id": new_table.id,  # 不匹配的表ID
                "status": "running",
                "progress": 50,
                "started_at": datetime.now(),
                "ended_at": None,
                "result": None,
                "error": None
            }
            
            response = client.get(f"/api/data-tables/{table.id}/sync/status", params={"task_id": "task-123"})
            
            # 验证响应
            assert response.status_code == 400
            data = response.json()
            assert data["detail"] == "任务ID与数据表不匹配"
            
            # 验证服务层调用
            mock_task_manager.get_task.assert_called_once_with("task-123")


class TestCancelSyncTask:
    """测试取消同步任务"""
    
    def test_cancel_sync_task_success(self, setup_database):
        """测试取消同步任务（成功场景）"""
        # 获取测试数据
        table = setup_database.query(DataTable).first()
        
        # 模拟任务管理器
        with patch('src.api.data_table_api.task_manager') as mock_task_manager:
            mock_task_manager.get_task.return_value = {
                "table_id": table.id,
                "status": "running",
                "progress": 50,
                "started_at": datetime.now(),
                "ended_at": None,
                "result": None,
                "error": None
            }
            
            response = client.post(f"/api/data-tables/{table.id}/sync/cancel", params={"task_id": "task-123"})
            
            # 验证响应
            assert response.status_code == 200
            data = response.json()
            assert data["task_id"] == "task-123"
            assert data["status"] == "cancelled"
            assert data["message"] == "同步任务已取消"
            
            # 验证服务层调用
            mock_task_manager.get_task.assert_called_once_with("task-123")
            mock_task_manager.cancel_task.assert_called_once_with("task-123")
    
    def test_cancel_sync_task_already_completed(self, setup_database):
        """测试取消同步任务（任务已完成）"""
        # 获取测试数据
        table = setup_database.query(DataTable).first()
        
        # 模拟任务管理器
        with patch('src.api.data_table_api.task_manager') as mock_task_manager:
            mock_task_manager.get_task.return_value = {
                "table_id": table.id,
                "status": "completed",
                "progress": 100,
                "started_at": datetime.now(),
                "ended_at": datetime.now(),
                "result": {"created": 3, "updated": 1, "deleted": 0},
                "error": None
            }
            
            response = client.post(f"/api/data-tables/{table.id}/sync/cancel", params={"task_id": "task-123"})
            
            # 验证响应
            assert response.status_code == 200
            data = response.json()
            assert data["task_id"] == "task-123"
            assert data["status"] == "已取消"
            assert data["message"] == "任务已处于完成或取消状态"
            
            # 验证服务层调用
            mock_task_manager.get_task.assert_called_once_with("task-123")
            mock_task_manager.cancel_task.assert_not_called()
    
    def test_cancel_sync_task_table_not_found(self, setup_database):
        """测试取消同步任务（表不存在）"""
        # 使用不存在的表ID
        invalid_id = str(uuid.uuid4())
        
        response = client.post(f"/api/data-tables/{invalid_id}/sync/cancel", params={"task_id": "task-123"})
        
        # 验证响应
        assert response.status_code == 404
        data = response.json()
        assert data["detail"] == "数据表不存在"
    
    def test_cancel_sync_task_task_not_found(self, setup_database):
        """测试取消同步任务（任务不存在）"""
        # 获取测试数据
        table = setup_database.query(DataTable).first()
        
        # 模拟任务管理器
        with patch('src.api.data_table_api.task_manager') as mock_task_manager:
            mock_task_manager.get_task.return_value = None
            
            response = client.post(f"/api/data-tables/{table.id}/sync/cancel", params={"task_id": "task-123"})
            
            # 验证响应
            assert response.status_code == 404
            data = response.json()
            assert data["detail"] == "同步任务不存在"
            
            # 验证服务层调用
            mock_task_manager.get_task.assert_called_once_with("task-123")
            mock_task_manager.cancel_task.assert_not_called()
    
    def test_cancel_sync_task_task_mismatch(self, setup_database):
        """测试取消同步任务（任务与表不匹配）"""
        # 获取测试数据
        table = setup_database.query(DataTable).first()
        
        # 创建另一个表
        new_table = DataTable(
            id=str(uuid.uuid4()),
            data_source_id=table.data_source_id,
            table_name="another_table",
            description="另一个表",
            row_count=50,
            field_count=3,
            status=True,
            created_by="test_user",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        setup_database.add(new_table)
        setup_database.commit()
        
        # 模拟任务管理器
        with patch('src.api.data_table_api.task_manager') as mock_task_manager:
            mock_task_manager.get_task.return_value = {
                "table_id": new_table.id,  # 不匹配的表ID
                "status": "running",
                "progress": 50,
                "started_at": datetime.now(),
                "ended_at": None,
                "result": None,
                "error": None
            }
            
            response = client.post(f"/api/data-tables/{table.id}/sync/cancel", params={"task_id": "task-123"})
            
            # 验证响应
            assert response.status_code == 400
            data = response.json()
            assert data["detail"] == "任务ID与数据表不匹配"
            
            # 验证服务层调用
            mock_task_manager.get_task.assert_called_once_with("task-123")
            mock_task_manager.cancel_task.assert_not_called()
