"""
表字段配置API单元测试
测试表字段的查询和配置功能
"""
import pytest
from unittest.mock import Mock, MagicMock
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from datetime import datetime
from src.models.data_preparation_model import DataTable, TableField
from src.api.table_field import router
from src.database import get_db

# 创建测试应用
app = FastAPI()
app.include_router(router)

# 创建测试客户端
client = TestClient(app)


class TestTableFieldAPI:
    """表字段配置API测试类"""
    
    def setup_method(self):
        """设置测试环境"""
        # 创建数据库会话的模拟对象
        self.db_session = Mock(spec=Session)
        
        # 创建数据表模拟对象
        self.mock_table = DataTable(
            id="table-1",
            data_source_id="source-1",
            table_name="test_table",
            display_name="Test Table",
            data_mode="DIRECT_QUERY",
            status=True
        )
        
        # 创建字段模拟对象
        self.mock_fields = [
            TableField(
                id="field-1",
                table_id="table-1",
                field_name="id",
                display_name="ID",
                data_type="INT",
                description="主键ID",
                is_primary_key=True,
                is_nullable=False,
                default_value=None,
                dictionary_id=None,
                is_queryable=True,
                is_aggregatable=True,
                sort_order=0,
                created_at=datetime.now(),
                updated_at=datetime.now()
            ),
            TableField(
                id="field-2",
                table_id="table-1",
                field_name="name",
                display_name="姓名",
                data_type="VARCHAR(50)",
                description="姓名",
                is_primary_key=False,
                is_nullable=True,
                default_value=None,
                dictionary_id="dict-1",
                is_queryable=True,
                is_aggregatable=False,
                sort_order=1,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
        ]
        
        # 设置依赖注入覆盖
        app.dependency_overrides[get_db] = lambda: self.db_session
    
    def teardown_method(self):
        """清理测试环境"""
        app.dependency_overrides.clear()

    def test_get_table_fields_success(self):
        """测试成功获取表字段列表"""
        # 设置数据库会话的查询行为
        def mock_query(model):
            if model == DataTable:
                mock_table_query = MagicMock()
                mock_table_filter = MagicMock()
                mock_table_filter.first.return_value = self.mock_table
                mock_table_query.filter.return_value = mock_table_filter
                return mock_table_query
            elif model == TableField:
                mock_field_query = MagicMock()
                mock_field_filter = MagicMock()
                mock_field_order = MagicMock()
                mock_field_order.all.return_value = self.mock_fields
                mock_field_filter.order_by.return_value = mock_field_order
                mock_field_query.filter.return_value = mock_field_filter
                return mock_field_query
            return MagicMock()
        
        self.db_session.query.side_effect = mock_query
        
        # 执行API调用
        response = client.get("/api/data-tables/table-1/fields")
        
        # 验证响应
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        
        # 验证第一个字段
        assert data[0]["id"] == "field-1"
        assert data[0]["field_name"] == "id"
        assert data[0]["display_name"] == "ID"
        assert data[0]["data_type"] == "INT"
        assert data[0]["is_primary_key"] == True
        assert data[0]["is_nullable"] == False

    def test_get_table_fields_table_not_found(self):
        """测试表不存在时返回404"""
        # 设置数据库会话的查询行为 - 表不存在
        mock_table_query = MagicMock()
        mock_table_filter = MagicMock()
        mock_table_filter.first.return_value = None
        mock_table_query.filter.return_value = mock_table_filter
        self.db_session.query.return_value = mock_table_query
        
        # 执行API调用
        response = client.get("/api/data-tables/table-999/fields")
        
        # 验证响应
        assert response.status_code == 404
        assert response.json()["detail"] == "数据表不存在: table-999"

    def test_update_table_field_success(self):
        """测试成功更新字段配置"""
        # 设置数据库会话的查询行为
        mock_field_query = MagicMock()
        mock_field_filter = MagicMock()
        mock_field_filter.first.return_value = self.mock_fields[0]
        mock_field_query.filter.return_value = mock_field_filter
        self.db_session.query.return_value = mock_field_query
        self.db_session.commit = MagicMock()
        self.db_session.refresh = MagicMock()
        
        # 更新数据
        update_data = {
            "display_name": "用户ID",
            "description": "用户唯一标识"
        }
        
        # 执行API调用
        response = client.put("/api/table-fields/field-1", json=update_data)
        
        # 验证响应
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "field-1"
        
        # 验证数据库操作
        self.db_session.commit.assert_called_once()
        self.db_session.refresh.assert_called_once()

    def test_update_table_field_not_found(self):
        """测试字段不存在时返回404"""
        # 设置数据库会话的查询行为 - 字段不存在
        mock_field_query = MagicMock()
        mock_field_filter = MagicMock()
        mock_field_filter.first.return_value = None
        mock_field_query.filter.return_value = mock_field_filter
        self.db_session.query.return_value = mock_field_query
        
        # 更新数据
        update_data = {
            "display_name": "用户ID"
        }
        
        # 执行API调用
        response = client.put("/api/table-fields/field-999", json=update_data)
        
        # 验证响应
        assert response.status_code == 404
        assert response.json()["detail"] == "字段不存在: field-999"

    def test_update_table_field_partial_update(self):
        """测试部分字段更新"""
        # 设置数据库会话的查询行为
        mock_field_query = MagicMock()
        mock_field_filter = MagicMock()
        mock_field_filter.first.return_value = self.mock_fields[1]
        mock_field_query.filter.return_value = mock_field_filter
        self.db_session.query.return_value = mock_field_query
        self.db_session.commit = MagicMock()
        self.db_session.refresh = MagicMock()
        
        # 只更新部分字段
        update_data = {
            "is_queryable": False
        }
        
        # 执行API调用
        response = client.put("/api/table-fields/field-2", json=update_data)
        
        # 验证响应
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "field-2"
        
        # 验证数据库操作
        self.db_session.commit.assert_called_once()
        self.db_session.refresh.assert_called_once()

    def test_update_table_field_database_error(self):
        """测试数据库错误处理"""
        # 设置数据库会话的查询行为
        mock_field_query = MagicMock()
        mock_field_filter = MagicMock()
        mock_field_filter.first.return_value = self.mock_fields[0]
        mock_field_query.filter.return_value = mock_field_filter
        self.db_session.query.return_value = mock_field_query
        self.db_session.commit.side_effect = Exception("Database error")
        self.db_session.rollback = MagicMock()
        
        # 更新数据
        update_data = {
            "display_name": "用户ID"
        }
        
        # 执行API调用
        response = client.put("/api/table-fields/field-1", json=update_data)
        
        # 验证响应
        assert response.status_code == 500
        assert response.json()["detail"] == "更新字段配置失败"
        
        # 验证数据库操作
        self.db_session.rollback.assert_called_once()