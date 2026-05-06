"""
数据表服务层综合单元测试
完整覆盖DataTableService类的所有功能
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import uuid
from sqlalchemy.orm import Session
from sqlalchemy import and_

from src.models.data_preparation_model import DataTable, TableField
from src.models.data_source_model import DataSource
from src.services.data_table_service import DataTableService
from src.schemas.data_table_schema import DataTableCreate, DataTableUpdate, DataTableResponse, DataTableListResponse


class TestDataTableService:
    """数据表服务测试类"""
    
    def setup_method(self):
        """设置测试环境"""
        self.service = DataTableService()
        self.mock_db = Mock(spec=Session)
        
    @pytest.fixture
    def mock_data_source(self):
        """创建数据源模拟对象"""
        return DataSource(
            id="source-1",
            name="Test MySQL Source",
            source_type="DATABASE",
            db_type="MySQL",
            host="localhost",
            port=3306,
            database_name="test_db",
            username="test_user",
            password="test_pass",
            status=True,
            created_by="test_user",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
    
    @pytest.fixture
    def mock_data_table(self):
        """创建数据表模拟对象"""
        return DataTable(
            id="table-1",
            data_source_id="source-1",
            table_name="test_table",
            display_name="Test Table",
            description="测试表",
            data_mode="DIRECT_QUERY",
            status=True,
            field_count=5,
            row_count=1000,
            created_by="test_user",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
    
    @pytest.fixture
    def mock_table_fields(self):
        """创建表字段模拟列表"""
        return [
            TableField(
                id="field-1",
                table_id="table-1",
                field_name="id",
                data_type="INT",
                is_nullable=False,
                is_primary_key=True,
                description="主键ID"
            ),
            TableField(
                id="field-2",
                table_id="table-1",
                field_name="name",
                data_type="VARCHAR(50)",
                is_nullable=True,
                is_primary_key=False,
                description="姓名"
            )
        ]
    
    def test_get_all_tables_success(self, mock_data_table):
        """测试获取所有数据表（成功场景）"""
        # 设置模拟查询行为
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.count.return_value = 1
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = [mock_data_table]
        
        self.mock_db.query.return_value = mock_query
        
        # 执行测试
        result = self.service.get_all_tables(
            db=self.mock_db,
            page=1,
            page_size=10,
            search=None,
            source_id=None,
            status=None
        )
        
        # 验证结果
        assert isinstance(result, DataTableListResponse)
        assert len(result.items) == 1
        assert result.total == 1
        assert result.page == 1
        assert result.page_size == 10
        assert result.pages == 1
        
        # 验证数据库查询调用
        self.mock_db.query.assert_called_once_with(DataTable)
        mock_query.order_by.assert_called_once()
        mock_query.count.assert_called_once()
        mock_query.offset.assert_called_once_with(0)
        mock_query.limit.assert_called_once_with(10)
        mock_query.all.assert_called_once()
    
    def test_get_all_tables_with_filters(self, mock_data_table):
        """测试获取数据表列表（带筛选条件）"""
        # 设置模拟查询行为
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.count.return_value = 0
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = []
        
        self.mock_db.query.return_value = mock_query
        
        # 执行测试（带筛选条件）
        result = self.service.get_all_tables(
            db=self.mock_db,
            page=2,
            page_size=5,
            search="user",
            source_id="source-1",
            status=True
        )
        
        # 验证结果
        assert isinstance(result, DataTableListResponse)
        assert len(result.items) == 0
        assert result.total == 0
        assert result.page == 2
        assert result.page_size == 5
        assert result.pages == 1  # 修复：pages 最小值为 1
        
        # 验证筛选条件被应用
        assert mock_query.filter.call_count >= 3  # source_id, status, search
        mock_query.offset.assert_called_once_with(5)  # (page-1) * page_size
        mock_query.limit.assert_called_once_with(5)
    
    def test_get_table_by_id_success(self, mock_data_table):
        """测试根据ID获取数据表（成功场景）"""
        # 设置模拟查询行为
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = mock_data_table
        
        self.mock_db.query.return_value = mock_query
        
        # 执行测试
        result = self.service.get_table_by_id(self.mock_db, "table-1")
        
        # 验证结果
        assert result == mock_data_table
        
        # 验证数据库查询调用
        self.mock_db.query.assert_called_once_with(DataTable)
        mock_query.filter.assert_called_once()
        mock_query.first.assert_called_once()
    
    def test_get_table_by_id_not_found(self):
        """测试根据ID获取数据表（不存在）"""
        # 设置模拟查询行为
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None
        
        self.mock_db.query.return_value = mock_query
        
        # 执行测试
        result = self.service.get_table_by_id(self.mock_db, "invalid-id")
        
        # 验证结果
        assert result is None
        
        # 验证数据库查询调用
        self.mock_db.query.assert_called_once_with(DataTable)
        mock_query.filter.assert_called_once()
        mock_query.first.assert_called_once()
    
    def test_create_table_success(self, mock_data_source):
        """测试创建数据表（成功场景）"""
        # 设置模拟查询行为
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = mock_data_source
        
        self.mock_db.query.return_value = mock_query
        
        # 创建测试数据
        table_data = DataTableCreate(
            source_id="source-1",
            table_name="new_table",
            description="新建表",
            row_count=500,
            column_count=3,
            status=True
        )
        
        # 执行测试
        with patch('src.services.data_table_service.datetime') as mock_datetime:
            mock_now = datetime(2024, 1, 1, 12, 0, 0)
            mock_datetime.now.return_value = mock_now
            
            result = self.service.create_table(self.mock_db, table_data)
        
        # 验证结果
        assert isinstance(result, DataTable)
        assert result.table_name == "new_table"
        assert result.description == "新建表"
        assert result.data_source_id == "source-1"
        assert result.row_count == 500
        assert result.field_count == 3
        assert result.status is True
        
        # 验证数据库操作
        self.mock_db.add.assert_called_once()
        self.mock_db.commit.assert_called_once()
        self.mock_db.refresh.assert_called_once()
    
    def test_create_table_invalid_source(self):
        """测试创建数据表（无效数据源）"""
        # 设置模拟查询行为（数据源不存在）
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None
        
        self.mock_db.query.return_value = mock_query
        
        # 创建测试数据
        table_data = DataTableCreate(
            source_id="invalid-source",
            table_name="new_table",
            description="新建表",
            row_count=500,
            column_count=3,
            status=True
        )
        
        # 执行测试并验证异常
        with pytest.raises(ValueError) as exc_info:
            self.service.create_table(self.mock_db, table_data)
        
        assert "数据源不存在" in str(exc_info.value)
        
        # 验证没有进行数据库写操作
        self.mock_db.add.assert_not_called()
        self.mock_db.commit.assert_not_called()
    
    def test_update_table_success(self, mock_data_table):
        """测试更新数据表（成功场景）"""
        # 设置模拟查询行为
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = mock_data_table
        
        self.mock_db.query.return_value = mock_query
        
        # 创建更新数据
        update_data = DataTableUpdate(
            description="更新后的描述",
            status=False
        )
        
        # 执行测试
        result = self.service.update_table(self.mock_db, "table-1", update_data)
        
        # 验证结果
        assert result == mock_data_table
        assert result.description == "更新后的描述"
        assert result.status is False
        
        # 验证数据库操作
        self.mock_db.commit.assert_called_once()
        self.mock_db.refresh.assert_called_once_with(mock_data_table)
    
    def test_update_table_not_found(self):
        """测试更新数据表（不存在）"""
        # 设置模拟查询行为（表不存在）
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None
        
        self.mock_db.query.return_value = mock_query
        
        # 创建更新数据
        update_data = DataTableUpdate(description="更新描述")
        
        # 执行测试并验证异常
        with pytest.raises(ValueError) as exc_info:
            self.service.update_table(self.mock_db, "invalid-id", update_data)
        
        assert "数据表不存在" in str(exc_info.value)
        
        # 验证没有进行数据库写操作
        self.mock_db.commit.assert_not_called()
    
    def test_delete_table_success(self, mock_data_table):
        """测试删除数据表（成功场景）"""
        # 设置模拟查询行为
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = mock_data_table
        
        self.mock_db.query.return_value = mock_query
        
        # 执行测试
        result = self.service.delete_table(self.mock_db, "table-1")
        
        # 验证结果
        assert result is True
        
        # 验证数据库操作
        self.mock_db.delete.assert_called_once_with(mock_data_table)
        self.mock_db.commit.assert_called_once()
    
    def test_delete_table_not_found(self):
        """测试删除数据表（不存在）"""
        # 设置模拟查询行为（表不存在）
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None
        
        self.mock_db.query.return_value = mock_query
        
        # 执行测试
        result = self.service.delete_table(self.mock_db, "invalid-id")
        
        # 验证结果
        assert result is False
        
        # 验证没有进行数据库写操作
        self.mock_db.delete.assert_not_called()
        self.mock_db.commit.assert_not_called()
    
    def test_has_related_columns_true(self):
        """测试检查关联字段（有关联）"""
        # 设置模拟查询行为
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.count.return_value = 3
        
        self.mock_db.query.return_value = mock_query
        
        # 执行测试
        result = self.service.has_related_columns(self.mock_db, "table-1")
        
        # 验证结果
        assert result is True
        
        # 验证数据库查询调用
        self.mock_db.query.assert_called_once_with(TableField)
        mock_query.filter.assert_called_once()
        mock_query.count.assert_called_once()
    
    def test_has_related_columns_false(self):
        """测试检查关联字段（无关联）"""
        # 设置模拟查询行为
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.count.return_value = 0
        
        self.mock_db.query.return_value = mock_query
        
        # 执行测试
        result = self.service.has_related_columns(self.mock_db, "table-1")
        
        # 验证结果
        assert result is False
        
        # 验证数据库查询调用
        self.mock_db.query.assert_called_once_with(TableField)
        mock_query.filter.assert_called_once()
        mock_query.count.assert_called_once()
    
    def test_get_table_columns_success(self, mock_table_fields):
        """测试获取数据表字段（成功场景）"""
        # 设置模拟查询行为
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = mock_table_fields
        
        self.mock_db.query.return_value = mock_query
        
        # 执行测试
        result = self.service.get_table_columns(self.mock_db, "table-1")
        
        # 验证结果
        assert result == mock_table_fields
        assert len(result) == 2
        assert result[0].field_name == "id"
        assert result[1].field_name == "name"
        
        # 验证数据库查询调用
        self.mock_db.query.assert_called_once_with(TableField)
        mock_query.filter.assert_called_once()
        mock_query.all.assert_called_once()
    
    def test_create_table_columns_success(self):
        """测试创建数据表字段（成功场景）"""
        # 创建测试数据
        columns_data = [
            {
                'name': 'id',
                'data_type': 'INT',
                'is_primary_key': True,
                'is_nullable': False,
                'description': '主键',
                'sort_order': 1,
                'is_queryable': True,
                'is_aggregatable': False
            },
            {
                'name': 'name',
                'data_type': 'VARCHAR(50)',
                'is_primary_key': False,
                'is_nullable': True,
                'description': '姓名',
                'sort_order': 2,
                'is_queryable': True,
                'is_aggregatable': True
            }
        ]
        
        # 执行测试
        result = self.service.create_table_columns(self.mock_db, "table-1", columns_data)
        
        # 验证结果
        assert len(result) == 2
        assert all(isinstance(field, TableField) for field in result)
        
        # 验证数据库操作
        assert self.mock_db.add.call_count == 2
        self.mock_db.commit.assert_called_once()
    
    def test_update_table_columns_success(self):
        """测试更新数据表字段（成功场景）"""
        # 设置模拟查询行为（删除现有字段）
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.delete.return_value = None
        
        self.mock_db.query.return_value = mock_query
        
        # 创建测试数据
        columns_data = [
            {
                'name': 'updated_field',
                'data_type': 'TEXT',
                'is_primary_key': False,
                'is_nullable': True,
                'description': '更新字段'
            }
        ]
        
        # 执行测试
        result = self.service.update_table_columns(self.mock_db, "table-1", columns_data)
        
        # 验证结果
        assert len(result) == 1
        assert result[0].field_name == 'updated_field'
        
        # 验证数据库操作
        mock_query.delete.assert_called_once()  # 删除现有字段
        self.mock_db.add.assert_called_once()   # 添加新字段
        self.mock_db.commit.assert_called_once()
    
    def test_get_tables_by_source_success(self, mock_data_table):
        """测试根据数据源ID获取数据表（成功场景）"""
        # 设置模拟查询行为
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = [mock_data_table]
        
        self.mock_db.query.return_value = mock_query
        
        # 执行测试
        result = self.service.get_tables_by_source(self.mock_db, "source-1")
        
        # 验证结果
        assert result == [mock_data_table]
        assert len(result) == 1
        assert result[0].data_source_id == "source-1"
        
        # 验证数据库查询调用
        self.mock_db.query.assert_called_once_with(DataTable)
        mock_query.filter.assert_called_once()
        mock_query.all.assert_called_once()
    
    def test_get_table_by_name_and_source_success(self, mock_data_table):
        """测试根据表名和数据源ID获取数据表（成功场景）"""
        # 设置模拟查询行为
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = mock_data_table
        
        self.mock_db.query.return_value = mock_query
        
        # 执行测试
        result = self.service.get_table_by_name_and_source(self.mock_db, "test_table", "source-1")
        
        # 验证结果
        assert result == mock_data_table
        
        # 验证数据库查询调用
        self.mock_db.query.assert_called_once_with(DataTable)
        mock_query.filter.assert_called_once()
        mock_query.first.assert_called_once()
    
    def test_get_table_by_name_and_source_not_found(self):
        """测试根据表名和数据源ID获取数据表（不存在）"""
        # 设置模拟查询行为
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None
        
        self.mock_db.query.return_value = mock_query
        
        # 执行测试
        result = self.service.get_table_by_name_and_source(self.mock_db, "nonexistent_table", "source-1")
        
        # 验证结果
        assert result is None
        
        # 验证数据库查询调用
        self.mock_db.query.assert_called_once_with(DataTable)
        mock_query.filter.assert_called_once()
        mock_query.first.assert_called_once()