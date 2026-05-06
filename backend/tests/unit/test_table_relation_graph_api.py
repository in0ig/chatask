"""
表关联图 API 测试
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from unittest.mock import patch
from datetime import datetime

from src.main import app
from src.database import get_db
from src.models.data_preparation_model import DataTable, TableField, TableRelation
from src.models.data_source_model import DataSource
from src.database import engine, Base

# 创建测试客户端
client = TestClient(app)

# 测试数据库会话
@pytest.fixture
def db_session():
    """创建测试数据库会话"""
    # 创建测试表
    Base.metadata.create_all(bind=engine)
    
    # 创建测试数据
    session = Session(bind=engine)
    
    # 获取当前时间用于所有时间戳
    now = datetime.now()
    
    # 创建数据源
    data_source = DataSource(
        id="data_source_1",
        name="用户数据源",
        source_type="DATABASE",
        db_type="MySQL",
        host="localhost",
        port=3306,
        database_name="test_db",
        auth_type="SQL_AUTH",
        username="test_user",
        password="test_password",
        status=True,
        created_by="admin",
        created_at=now,
        updated_at=now
    )
    session.add(data_source)
    
    data_source2 = DataSource(
        id="data_source_2",
        name="订单数据源",
        source_type="DATABASE",
        db_type="MySQL",
        host="localhost",
        port=3306,
        database_name="test_db",
        auth_type="SQL_AUTH",
        username="test_user",
        password="test_password",
        status=True,
        created_by="admin",
        created_at=now,
        updated_at=now
    )
    session.add(data_source2)
    
    # 创建数据表，关联到数据源
    table1 = DataTable(
        id="table_1",
        data_source_id="data_source_1",
        table_name="users",
        display_name="用户表",
        data_mode="DIRECT_QUERY",
        status=True,
        created_by="admin",
        created_at=now,
        updated_at=now
    )
    session.add(table1)
    
    table2 = DataTable(
        id="table_2",
        data_source_id="data_source_2",
        table_name="orders",
        display_name="订单表",
        data_mode="DIRECT_QUERY",
        status=True,
        created_by="admin",
        created_at=now,
        updated_at=now
    )
    session.add(table2)
    
    # 创建字段
    field1 = TableField(
        id="field_1",
        table_id="table_1",
        field_name="id",
        display_name="ID",
        data_type="int",
        is_primary_key=True,
        created_at=now,
        updated_at=now
    )
    session.add(field1)
    
    field2 = TableField(
        id="field_2",
        table_id="table_1",
        field_name="name",
        display_name="姓名",
        data_type="varchar",
        created_at=now,
        updated_at=now
    )
    session.add(field2)
    
    field3 = TableField(
        id="field_3",
        table_id="table_2",
        field_name="id",
        display_name="ID",
        data_type="int",
        is_primary_key=True,
        created_at=now,
        updated_at=now
    )
    session.add(field3)
    
    field4 = TableField(
        id="field_4",
        table_id="table_2",
        field_name="user_id",
        display_name="用户ID",
        data_type="int",
        created_at=now,
        updated_at=now
    )
    session.add(field4)
    
    # 创建关联
    relation1 = TableRelation(
        id="relation_1",
        relation_name="用户-订单关联",
        primary_table_id="table_1",
        primary_field_id="field_1",
        foreign_table_id="table_2",
        foreign_field_id="field_4",
        join_type="INNER",
        created_by="admin",
        created_at=now,
        updated_at=now
    )
    session.add(relation1)
    
    relation2 = TableRelation(
        id="relation_2",
        relation_name="用户-订单关联2",
        primary_table_id="table_1",
        primary_field_id="field_1",
        foreign_table_id="table_2",
        foreign_field_id="field_3",
        join_type="LEFT",
        created_by="admin",
        created_at=now,
        updated_at=now
    )
    session.add(relation2)
    
    session.commit()
    
    yield session
    
    # 清理
    session.close()
    Base.metadata.drop_all(bind=engine)

# 测试用例

def test_get_all_table_relations_graph(db_session):
    """测试获取所有表的关联图数据"""
    response = client.get("/api/table-relations/graph")
    
    assert response.status_code == 200
    data = response.json()
    
    # 验证返回结构
    assert "nodes" in data
    assert "edges" in data
    
    # 验证节点数量（2个表）
    assert len(data["nodes"]) == 2
    
    # 验证边数量（2个关联）
    assert len(data["edges"]) == 2
    
    # 验证节点数据
    nodes = data["nodes"]
    node_ids = [node["id"] for node in nodes]
    assert "data_source_1" in node_ids
    assert "data_source_2" in node_ids
    
    # 验证节点属性
    for node in nodes:
        assert "id" in node
        assert "name" in node
        assert "x" in node
        assert "y" in node
        assert "data_source_id" in node
        assert "table_name" in node
        
    # 验证边数据
    edges = data["edges"]
    edge_ids = [edge["id"] for edge in edges]
    assert "relation_1" in edge_ids
    assert "relation_2" in edge_ids
    
    # 验证边属性
    for edge in edges:
        assert "id" in edge
        assert "source" in edge
        assert "target" in edge
        assert "relation_name" in edge
        assert "join_type" in edge


def test_get_table_relations_graph_by_data_source(db_session):
    """测试按数据源筛选关联图数据"""
    # 按第一个数据源筛选
    response = client.get("/api/table-relations/graph?data_source_id=data_source_1")
    
    assert response.status_code == 200
    data = response.json()
    
    # 验证返回结构
    assert "nodes" in data
    assert "edges" in data
    
    # 验证节点数量（2个表，因为两个表都关联到data_source_1）
    assert len(data["nodes"]) == 2
    
    # 验证边数量（2个关联）
    assert len(data["edges"]) == 2
    
    # 验证返回的节点包含指定数据源的节点和关联的其他数据源节点
    node_data_source_ids = {node["data_source_id"] for node in data["nodes"]}
    assert "data_source_1" in node_data_source_ids
    assert "data_source_2" in node_data_source_ids
    
    # 按第二个数据源筛选
    response = client.get("/api/table-relations/graph?data_source_id=data_source_2")
    
    assert response.status_code == 200
    data = response.json()
    
    # 验证返回结构
    assert "nodes" in data
    assert "edges" in data
    
    # 验证节点数量（2个表）
    assert len(data["nodes"]) == 2
    
    # 验证边数量（2个关联）
    assert len(data["edges"]) == 2
    
    # 验证返回的节点包含指定数据源的节点和关联的其他数据源节点
    node_data_source_ids = {node["data_source_id"] for node in data["nodes"]}
    assert "data_source_1" in node_data_source_ids
    assert "data_source_2" in node_data_source_ids


def test_get_table_relations_graph_empty_data(db_session):
    """测试空数据情况"""
    # 删除所有关联
    db_session.query(TableRelation).delete()
    db_session.commit()
    
    response = client.get("/api/table-relations/graph")
    
    assert response.status_code == 200
    data = response.json()
    
    # 验证返回结构
    assert "nodes" in data
    assert "edges" in data
    
    # 验证节点数量（2个表，因为表仍然存在）
    assert len(data["nodes"]) == 2
    
    # 验证边数量（0）
    assert len(data["edges"]) == 0


def test_coordinate_calculation_logic(db_session):
    """测试坐标计算逻辑"""
    response = client.get("/api/table-relations/graph")
    
    assert response.status_code == 200
    data = response.json()
    
    nodes = data["nodes"]
    
    # 验证所有节点都有有效的坐标
    for node in nodes:
        assert isinstance(node["x"], (int, float))
        assert isinstance(node["y"], (int, float))
        
        # 验证坐标不是 NaN
        assert not (node["x"] != node["x"])  # NaN 检查
        assert not (node["y"] != node["y"])  # NaN 检查
    
    # 验证圆形布局：节点应该大致均匀分布在圆周上
    # 对于2个节点，它们应该在相对的两侧
    if len(nodes) >= 2:
        # 计算节点之间的角度差
        # 由于是圆形布局，节点应该围绕中心点均匀分布
        center_x = sum(node["x"] for node in nodes) / len(nodes)
        center_y = sum(node["y"] for node in nodes) / len(nodes)
        
        # 验证所有节点都在合理的范围内
        for node in nodes:
            # 验证坐标在合理范围内（-100 到 100）
            assert -100 <= node["x"] <= 100
            assert -100 <= node["y"] <= 100
            
            # 验证节点与中心点的距离
            distance = ((node["x"] - center_x) ** 2 + (node["y"] - center_y) ** 2) ** 0.5
            assert 10 <= distance <= 50  # 合理的半径范围


def test_node_and_edge_data_structure(db_session):
    """测试节点和边数据结构"""
    response = client.get("/api/table-relations/graph")
    
    assert response.status_code == 200
    data = response.json()
    
    # 测试节点结构
    for node in data["nodes"]:
        assert isinstance(node["id"], str)
        assert isinstance(node["name"], str)
        assert isinstance(node["x"], (int, float))
        assert isinstance(node["y"], (int, float))
        assert isinstance(node["data_source_id"], str)
        assert isinstance(node["table_name"], str)
        
    # 测试边结构
    for edge in data["edges"]:
        assert isinstance(edge["id"], str)
        assert isinstance(edge["source"], str)
        assert isinstance(edge["target"], str)
        assert isinstance(edge["relation_name"], str)
        assert isinstance(edge["join_type"], str)
        assert edge["join_type"] in ["INNER", "LEFT", "RIGHT", "FULL"]


# 额外测试：测试没有表的情况

def test_get_table_relations_graph_no_tables(db_session):
    """测试没有表的情况"""
    # 删除所有表和关联
    db_session.query(TableRelation).delete()
    db_session.query(TableField).delete()
    db_session.query(DataTable).delete()
    db_session.commit()
    
    response = client.get("/api/table-relations/graph")
    
    assert response.status_code == 200
    data = response.json()
    
    # 验证返回结构
    assert "nodes" in data
    assert "edges" in data
    
    # 验证节点数量（0）
    assert len(data["nodes"]) == 0
    
    # 验证边数量（0）
    assert len(data["edges"]) == 0
