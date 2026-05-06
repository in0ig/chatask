"""
表关联 API 测试用例
测试表关联的 CRUD 操作和验证逻辑
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.database import Base, get_db
from src.main import app
from src.models.data_preparation_model import DataTable, TableField, TableRelation
from src.models.data_source_model import DataSource
import uuid
from datetime import datetime

# 使用内存数据库进行测试
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 覆盖依赖项
@pytest.fixture
def db_session():
    """创建测试数据库会话"""
    # 确保所有模型都被导入并注册到Base的元数据中
    # 重新导入所有相关模型以确保Base.metadata包含所有表
    from src.models.data_preparation_model import DataTable, TableField, TableRelation
    from src.models.data_source_model import DataSource
    
    # 手动创建所有表
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)

@pytest.fixture
def client(db_session):
    """创建测试客户端"""
    def override_get_db():
        try:
            yield db_session
        finally:
            db_session.close()
    
    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)

@pytest.fixture
def setup_test_data(db_session):
    """设置测试数据：数据源、数据表和字段"""
    # 创建数据源
    now = datetime.now()
    data_source = DataSource(
        id=str(uuid.uuid4()),
        name="测试数据源",
        source_type="DATABASE",
        db_type="MySQL",
        host="localhost",
        port=3306,
        database_name="test_db",
        auth_type="SQL_AUTH",
        username="test_user",
        password="test_password",
        status=True,
        created_by="test_user",
        created_at=now,
        updated_at=now
    )
    db_session.add(data_source)
    db_session.commit()
    
    # 创建数据表
    data_source_id = data_source.id
    data_source_table = DataTable(
        id=str(uuid.uuid4()),
        data_source_id=data_source_id,
        table_name="orders",
        display_name="订单表",
        data_mode="DIRECT_QUERY",
        status=True,
        created_by="test_user",
        created_at=now,
        updated_at=now
    )
    db_session.add(data_source_table)
    
    # 创建另一个数据源
    data_source2 = DataSource(
        id=str(uuid.uuid4()),
        name="测试数据源2",
        source_type="DATABASE",
        db_type="MySQL",
        host="localhost",
        port=3306,
        database_name="test_db2",
        auth_type="SQL_AUTH",
        username="test_user",
        password="test_password",
        status=True,
        created_by="test_user",
        created_at=now,
        updated_at=now
    )
    db_session.add(data_source2)
    db_session.commit()
    
    # 创建数据表
    data_source2_id = data_source2.id
    data_source2_table = DataTable(
        id=str(uuid.uuid4()),
        data_source_id=data_source2_id,
        table_name="users",
        display_name="用户表",
        data_mode="DIRECT_QUERY",
        status=True,
        created_by="test_user",
        created_at=now,
        updated_at=now
    )
    db_session.add(data_source2_table)
    db_session.commit()
    
    # 创建订单表字段
    now = datetime.now()
    order_id_field = TableField(
        id=str(uuid.uuid4()),
        table_id=data_source_table.id,
        field_name="order_id",
        display_name="订单ID",
        data_type="INT",
        is_primary_key=True,
        is_nullable=False,
        created_at=now,
        updated_at=now
    )
    db_session.add(order_id_field)
    
    customer_id_field = TableField(
        id=str(uuid.uuid4()),
        table_id=data_source_table.id,
        field_name="customer_id",
        display_name="客户ID",
        data_type="INT",
        is_primary_key=False,
        is_nullable=False,
        created_at=now,
        updated_at=now
    )
    db_session.add(customer_id_field)
    
    # 创建用户表字段
    user_id_field = TableField(
        id=str(uuid.uuid4()),
        table_id=data_source2_table.id,
        field_name="id",
        display_name="用户ID",
        data_type="INT",
        is_primary_key=True,
        is_nullable=False,
        created_at=now,
        updated_at=now
    )
    db_session.add(user_id_field)
    
    username_field = TableField(
        id=str(uuid.uuid4()),
        table_id=data_source2_table.id,
        field_name="username",
        display_name="用户名",
        data_type="VARCHAR",
        is_primary_key=False,
        is_nullable=False,
        created_at=now,
        updated_at=now
    )
    db_session.add(username_field)
    
    # 创建一个类型不匹配的字段
    email_field = TableField(
        id=str(uuid.uuid4()),
        table_id=data_source2_table.id,
        field_name="email",
        display_name="邮箱",
        data_type="VARCHAR",
        is_primary_key=False,
        is_nullable=False,
        created_at=now,
        updated_at=now
    )
    db_session.add(email_field)
    
    db_session.commit()
    
    return {
        "orders_table_id": data_source_table.id,
        "users_table_id": data_source2_table.id,
        "order_id_field_id": order_id_field.id,
        "customer_id_field_id": customer_id_field.id,
        "user_id_field_id": user_id_field.id,
        "username_field_id": username_field.id,
        "email_field_id": email_field.id,
        "data_source_id": data_source_id,
        "data_source2_id": data_source2_id
    }


def test_create_table_relation_success(client, setup_test_data):
    """测试创建表关联成功"""
    # 使用订单表的 order_id 字段和用户表的 id 字段创建关联
    response = client.post("/api/table-relations", json={
        "relation_name": "订单-用户关联",
        "primary_table_id": setup_test_data["orders_table_id"],
        "primary_field_id": setup_test_data["order_id_field_id"],
        "foreign_table_id": setup_test_data["users_table_id"],
        "foreign_field_id": setup_test_data["user_id_field_id"],
        "join_type": "INNER",
        "description": "订单表与用户表的关联",
        "created_by": "test_user"
    })
    
    assert response.status_code == 201
    data = response.json()
    
    # 验证返回数据
    assert data["relation_name"] == "订单-用户关联"
    assert data["primary_table_id"] == setup_test_data["orders_table_id"]
    assert data["primary_field_id"] == setup_test_data["order_id_field_id"]
    assert data["foreign_table_id"] == setup_test_data["users_table_id"]
    assert data["foreign_field_id"] == setup_test_data["user_id_field_id"]
    assert data["join_type"] == "INNER"
    assert data["description"] == "订单表与用户表的关联"
    assert data["status"] == True
    assert data["primary_table_name"] == "orders"
    assert data["primary_field_name"] == "order_id"
    assert data["primary_field_type"] == "INT"
    assert data["foreign_table_name"] == "users"
    assert data["foreign_field_name"] == "id"
    assert data["foreign_field_type"] == "INT"


def test_get_table_relations_list(client, setup_test_data):
    """测试获取关联列表（分页、筛选）"""
    # 创建两个关联
    relation1 = client.post("/api/table-relations", json={
        "relation_name": "订单-用户关联",
        "primary_table_id": setup_test_data["orders_table_id"],
        "primary_field_id": setup_test_data["order_id_field_id"],
        "foreign_table_id": setup_test_data["users_table_id"],
        "foreign_field_id": setup_test_data["user_id_field_id"],
        "join_type": "INNER",
        "description": "订单表与用户表的关联",
        "created_by": "test_user"
    }).json()
    
    relation2 = client.post("/api/table-relations", json={
        "relation_name": "订单-客户关联",
        "primary_table_id": setup_test_data["orders_table_id"],
        "primary_field_id": setup_test_data["order_id_field_id"],
        "foreign_table_id": setup_test_data["users_table_id"],
        "foreign_field_id": setup_test_data["user_id_field_id"],
        "join_type": "LEFT",
        "description": "订单表与客户表的关联",
        "created_by": "test_user"
    }).json()
    
    # 获取所有关联
    response = client.get("/api/table-relations")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 2
    
    # 按主表ID筛选
    response = client.get(f"/api/table-relations?primary_table_id={setup_test_data['orders_table_id']}")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 2
    
    # 按从表ID筛选
    response = client.get(f"/api/table-relations?foreign_table_id={setup_test_data['users_table_id']}")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 2
    
    # 按状态筛选
    response = client.get(f"/api/table-relations?status=true")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 2
    
    # 分页测试
    response = client.get(f"/api/table-relations?skip=0&limit=1")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1


def test_get_table_relation_detail(client, setup_test_data):
    """测试获取关联详情"""
    # 创建关联
    response = client.post("/api/table-relations", json={
        "relation_name": "订单-用户关联",
        "primary_table_id": setup_test_data["orders_table_id"],
        "primary_field_id": setup_test_data["order_id_field_id"],
        "foreign_table_id": setup_test_data["users_table_id"],
        "foreign_field_id": setup_test_data["user_id_field_id"],
        "join_type": "INNER",
        "description": "订单表与用户表的关联",
        "created_by": "test_user"
    })
    created_relation = response.json()
    relation_id = created_relation["id"]
    
    # 获取详情
    response = client.get(f"/api/table-relations/{relation_id}")
    assert response.status_code == 200
    data = response.json()
    
    # 验证详情
    assert data["id"] == relation_id
    assert data["relation_name"] == "订单-用户关联"
    assert data["primary_table_id"] == setup_test_data["orders_table_id"]
    assert data["primary_field_id"] == setup_test_data["order_id_field_id"]
    assert data["foreign_table_id"] == setup_test_data["users_table_id"]
    assert data["foreign_field_id"] == setup_test_data["user_id_field_id"]
    assert data["join_type"] == "INNER"
    assert data["description"] == "订单表与用户表的关联"
    assert data["status"] == True
    assert data["primary_table_name"] == "orders"
    assert data["primary_field_name"] == "order_id"
    assert data["primary_field_type"] == "INT"
    assert data["foreign_table_name"] == "users"
    assert data["foreign_field_name"] == "id"
    assert data["foreign_field_type"] == "INT"


def test_update_table_relation(client, setup_test_data):
    """测试更新关联"""
    # 创建关联
    response = client.post("/api/table-relations", json={
        "relation_name": "订单-用户关联",
        "primary_table_id": setup_test_data["orders_table_id"],
        "primary_field_id": setup_test_data["order_id_field_id"],
        "foreign_table_id": setup_test_data["users_table_id"],
        "foreign_field_id": setup_test_data["user_id_field_id"],
        "join_type": "INNER",
        "description": "订单表与用户表的关联",
        "created_by": "test_user"
    })
    created_relation = response.json()
    relation_id = created_relation["id"]
    
    # 更新关联
    response = client.put(f"/api/table-relations/{relation_id}", json={
        "relation_name": "更新后的关联名称",
        "join_type": "LEFT",
        "status": False
    })
    
    assert response.status_code == 200
    data = response.json()
    
    # 验证更新结果
    assert data["relation_name"] == "更新后的关联名称"
    assert data["join_type"] == "LEFT"
    assert data["status"] == False
    
    # 验证其他字段未被修改
    assert data["primary_table_id"] == setup_test_data["orders_table_id"]
    assert data["primary_field_id"] == setup_test_data["order_id_field_id"]
    assert data["foreign_table_id"] == setup_test_data["users_table_id"]
    assert data["foreign_field_id"] == setup_test_data["user_id_field_id"]


def test_delete_table_relation(client, setup_test_data):
    """测试删除关联"""
    # 创建关联
    response = client.post("/api/table-relations", json={
        "relation_name": "订单-用户关联",
        "primary_table_id": setup_test_data["orders_table_id"],
        "primary_field_id": setup_test_data["order_id_field_id"],
        "foreign_table_id": setup_test_data["users_table_id"],
        "foreign_field_id": setup_test_data["user_id_field_id"],
        "join_type": "INNER",
        "description": "订单表与用户表的关联",
        "created_by": "test_user"
    })
    created_relation = response.json()
    relation_id = created_relation["id"]
    
    # 删除关联
    response = client.delete(f"/api/table-relations/{relation_id}")
    assert response.status_code == 204
    
    # 验证关联已被删除
    response = client.get(f"/api/table-relations/{relation_id}")
    assert response.status_code == 404


def test_field_type_validation(client, setup_test_data):
    """测试字段类型验证"""
    # 尝试创建一个类型不匹配的关联（INT 和 VARCHAR）
    response = client.post("/api/table-relations", json={
        "relation_name": "订单-用户邮箱关联",
        "primary_table_id": setup_test_data["orders_table_id"],
        "primary_field_id": setup_test_data["order_id_field_id"],  # INT 类型
        "foreign_table_id": setup_test_data["users_table_id"],
        "foreign_field_id": setup_test_data["email_field_id"],    # VARCHAR 类型
        "join_type": "INNER",
        "created_by": "test_user"
    })
    
    assert response.status_code == 400
    error_detail = response.json()["detail"]
    assert "数据类型不匹配" in error_detail
    
    # 验证相同类型可以创建
    response = client.post("/api/table-relations", json={
        "relation_name": "订单-用户关联",
        "primary_table_id": setup_test_data["orders_table_id"],
        "primary_field_id": setup_test_data["order_id_field_id"],  # INT 类型
        "foreign_table_id": setup_test_data["users_table_id"],
        "foreign_field_id": setup_test_data["user_id_field_id"],   # INT 类型
        "join_type": "INNER",
        "created_by": "test_user"
    })
    
    assert response.status_code == 201


def test_error_handling_table_not_exist(client, setup_test_data):
    """测试错误处理（表不存在）"""
    # 使用不存在的主表ID
    response = client.post("/api/table-relations", json={
        "relation_name": "无效关联",
        "primary_table_id": "nonexistent_table_id",
        "primary_field_id": setup_test_data["order_id_field_id"],
        "foreign_table_id": setup_test_data["users_table_id"],
        "foreign_field_id": setup_test_data["user_id_field_id"],
        "join_type": "INNER",
        "created_by": "test_user"
    })
    
    assert response.status_code == 404
    assert "数据表不存在" in response.json()["detail"]


def test_error_handling_field_not_exist(client, setup_test_data):
    """测试错误处理（字段不存在）"""
    # 使用不存在的主表字段ID
    response = client.post("/api/table-relations", json={
        "relation_name": "无效关联",
        "primary_table_id": setup_test_data["orders_table_id"],
        "primary_field_id": "nonexistent_field_id",
        "foreign_table_id": setup_test_data["users_table_id"],
        "foreign_field_id": setup_test_data["user_id_field_id"],
        "join_type": "INNER",
        "created_by": "test_user"
    })
    
    assert response.status_code == 404
    assert "字段不存在" in response.json()["detail"]


def test_invalid_join_type(client, setup_test_data):
    """测试无效的连接类型"""
    response = client.post("/api/table-relations", json={
        "relation_name": "无效关联",
        "primary_table_id": setup_test_data["orders_table_id"],
        "primary_field_id": setup_test_data["order_id_field_id"],
        "foreign_table_id": setup_test_data["users_table_id"],
        "foreign_field_id": setup_test_data["user_id_field_id"],
        "join_type": "INVALID_TYPE",
        "created_by": "test_user"
    })
    
    assert response.status_code == 422  # Pydantic 验证错误
    
    # 验证错误信息包含有效的类型
    error_detail = response.json()["detail"]
    for type_str in ["INNER", "LEFT", "RIGHT", "FULL"]:
        assert type_str in str(error_detail)


def test_update_field_type_validation(client, setup_test_data):
    """测试更新时字段类型验证"""
    # 创建一个有效的关联
    response = client.post("/api/table-relations", json={
        "relation_name": "订单-用户关联",
        "primary_table_id": setup_test_data["orders_table_id"],
        "primary_field_id": setup_test_data["order_id_field_id"],  # INT
        "foreign_table_id": setup_test_data["users_table_id"],
        "foreign_field_id": setup_test_data["user_id_field_id"],   # INT
        "join_type": "INNER",
        "created_by": "test_user"
    })
    created_relation = response.json()
    relation_id = created_relation["id"]
    
    # 尝试更新为类型不匹配的字段
    response = client.put(f"/api/table-relations/{relation_id}", json={
        "foreign_field_id": setup_test_data["email_field_id"]  # 改为 VARCHAR
    })
    
    assert response.status_code == 400
    assert "数据类型不匹配" in response.json()["detail"]


def test_duplicate_relation(client, setup_test_data):
    """测试重复关联"""
    # 创建第一个关联
    response = client.post("/api/table-relations", json={
        "relation_name": "订单-用户关联",
        "primary_table_id": setup_test_data["orders_table_id"],
        "primary_field_id": setup_test_data["order_id_field_id"],
        "foreign_table_id": setup_test_data["users_table_id"],
        "foreign_field_id": setup_test_data["user_id_field_id"],
        "join_type": "INNER",
        "created_by": "test_user"
    })
    assert response.status_code == 201
    
    # 尝试创建相同的关联
    response = client.post("/api/table-relations", json={
        "relation_name": "订单-用户关联2",
        "primary_table_id": setup_test_data["orders_table_id"],
        "primary_field_id": setup_test_data["order_id_field_id"],
        "foreign_table_id": setup_test_data["users_table_id"],
        "foreign_field_id": setup_test_data["user_id_field_id"],
        "join_type": "INNER",
        "created_by": "test_user"
    })
    
    assert response.status_code == 409
    assert "该关联关系已存在" in response.json()["detail"]