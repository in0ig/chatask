"""
数据表API单元测试 - 修复版本
"""
import pytest
from fastapi.testclient import TestClient
from datetime import datetime
import uuid
import os
import logging

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

def test_get_data_tables_list(setup_database):
    """测试获取数据表列表"""
    response = client.get("/api/data-tables")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "page_size" in data

def test_create_data_table_success(setup_database):
    """测试创建数据表（成功场景）"""
    source = setup_database.query(DataSource).first()
    
    # 使用时间戳确保表名唯一
    import time
    unique_name = f"customers_{int(time.time())}"
    
    table_data = {
        "source_id": source.id,
        "table_name": unique_name,
        "description": "客户信息表",
        "row_count": 800,
        "column_count": 7,
        "status": True
    }
    
    response = client.post("/api/data-tables", json=table_data)
    assert response.status_code == 201
    data = response.json()
    
    assert data["table_name"] == unique_name
    assert data["data_source_id"] == source.id  # 使用正确的字段名
    assert data["description"] == "客户信息表"

def test_get_data_table_by_id_success(setup_database):
    """测试获取数据表详情（存在）"""
    table = setup_database.query(DataTable).first()
    
    response = client.get(f"/api/data-tables/{table.id}")
    assert response.status_code == 200
    data = response.json()
    
    assert data["id"] == table.id
    assert data["table_name"] == table.table_name
    assert data["data_source_id"] == table.data_source_id

def test_get_data_table_by_id_not_found(setup_database):
    """测试获取数据表详情（不存在）"""
    response = client.get("/api/data-tables/invalid-id")
    assert response.status_code == 404
    data = response.json()
    assert data["detail"] == "数据表不存在"