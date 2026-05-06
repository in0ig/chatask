"""
Pytest配置文件

用于设置测试环境，避免循环导入问题。
"""
import os
import sys
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import tempfile

# 在导入任何其他模块之前设置测试模式环境变量
os.environ["TEST_MODE"] = "true"

# 确保src模块在Python路径中
src_path = os.path.join(os.path.dirname(__file__), "..", "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)
print(f"Added {src_path} to Python path")

# 导入所有模型以确保Base.metadata包含所有表
from src.models import Base
from src.models.data_preparation_model import (
    DataTable, TableField, Dictionary, DictionaryItem, DynamicDictionaryConfig, 
    TableRelation, FieldMapping, DictionaryVersion, DictionaryVersionItem,
    TableFolder, DataTableSyncHistory, TableFieldHistory
)
from src.models.data_source_model import DataSource
from src.models.knowledge_base_model import KnowledgeBase
from src.models.knowledge_item_model import KnowledgeItem
from src.models.database_models import PromptConfig, SessionContext, ConversationMessage, TokenUsageStats

# 验证所有模型都已正确注册到Base.metadata中
expected_tables = [
    'data_sources', 'data_tables', 'table_fields', 'dictionaries', 
    'dictionary_items', 'dynamic_dictionary_configs', 'table_relations',
    'field_mappings', 'dictionary_versions', 'dictionary_version_items',
    'table_folders', 'data_table_sync_history', 'table_field_history',
    'knowledge_bases', 'knowledge_items', 'prompt_config', 
    'session_context', 'conversation_messages', 'token_usage_stats'
]

# 检查是否所有期望的表都已注册
registered_tables = list(Base.metadata.tables.keys())
missing_tables = [table for table in expected_tables if table not in registered_tables]

if missing_tables:
    raise RuntimeError(f"以下表未注册到Base.metadata: {missing_tables}. 已注册的表: {registered_tables}")

print("Base.metadata.tables keys:", registered_tables)

# 创建SQLite文件数据库引擎，与src/database.py保持一致
TEST_DB_PATH = os.path.join(tempfile.gettempdir(), "test_data_table.db")
SQLALCHEMY_DATABASE_URL = f"sqlite:///{TEST_DB_PATH}"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    connect_args={"check_same_thread": False}
)

# 创建所有表 - 使用src.models.base.Base确保一致性
Base.metadata.create_all(bind=engine)

# 验证表是否已创建
created_tables = list(Base.metadata.tables.keys())
print("Created tables:", created_tables)

# 确保所有期望的表都已创建
created_table_names = set(created_tables)
expected_table_names = set(expected_tables)
if not expected_table_names.issubset(created_table_names):
    missing_tables = expected_table_names - created_table_names
    raise RuntimeError(f"以下表未创建: {missing_tables}")

# 创建会话工厂
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 在pytest中创建一个fixture来提供数据库连接
@pytest.fixture(scope="session")
def db_engine():
    return engine

@pytest.fixture(scope="session")
def db_session_factory():
    return TestingSessionLocal

@pytest.fixture(scope="function")
def db_session():
    """为每个测试函数提供独立的数据库会话"""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

# 为测试客户端提供一个fixture
@pytest.fixture(scope="session")
def client():
    from fastapi.testclient import TestClient
    
    # 导入src.database中的get_db
    from src.database import get_db
    
    # 在导入app之前设置依赖注入覆盖
    def override_get_db():
        # 使用我们创建的TestingSessionLocal
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()
    
    # 导入app并设置依赖注入覆盖
    from src.main import app
    app.dependency_overrides[get_db] = override_get_db
    
    return TestClient(app)

# 为测试数据提供一个fixture
@pytest.fixture(scope="session")
def setup_database(db_session_factory):
    # 创建测试数据源
    db = db_session_factory()
    
    # 创建两个数据源用于测试
    from datetime import datetime
    import uuid
    
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
    
    source2 = DataSource(
        id=str(uuid.uuid4()),
        name="Test Source 2",
        source_type="DATABASE",
        db_type="PostgreSQL",
        host="localhost",
        port=5432,
        database_name="test_db2",
        auth_type="SQL_AUTH",
        username="test_user2",
        password="encrypted_password2",
        status=True,
        created_by="test_user2",
        created_at=now,
        updated_at=now
    )
    
    db.add(source1)
    db.add(source2)
    db.commit()
    
    # 创建测试数据表
    now = datetime.now()
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
    
    table2 = DataTable(
        id=str(uuid.uuid4()),
        data_source_id=source1.id,
        table_name="orders",
        description="订单表",
        row_count=500,
        field_count=8,
        status=True,
        data_mode="DIRECT_QUERY",
        created_by="test_user",
        created_at=now,
        updated_at=now
    )
    
    table3 = DataTable(
        id=str(uuid.uuid4()),
        data_source_id=source2.id,
        table_name="products",
        description="产品表",
        row_count=200,
        field_count=6,
        status=False,
        data_mode="DIRECT_QUERY",
        created_by="test_user2",
        created_at=now,
        updated_at=now
    )
    
    db.add(table1)
    db.add(table2)
    db.add(table3)
    db.commit()
    
    # 创建测试字段
    now = datetime.now()
    column1 = TableField(
        id=str(uuid.uuid4()),
        table_id=table1.id,
        field_name="id",
        data_type="INT",
        is_primary_key=True,
        is_nullable=False,
        description="主键",
        created_at=now,
        updated_at=now
    )
    
    column2 = TableField(
        id=str(uuid.uuid4()),
        table_id=table1.id,
        field_name="name",
        data_type="VARCHAR(100)",
        is_primary_key=False,
        is_nullable=False,
        description="用户名",
        created_at=now,
        updated_at=now
    )
    
    column3 = TableField(
        id=str(uuid.uuid4()),
        table_id=table2.id,
        field_name="order_id",
        data_type="INT",
        is_primary_key=True,
        is_nullable=False,
        description="订单ID",
        created_at=now,
        updated_at=now
    )
    
    db.add(column1)
    db.add(column2)
    db.add(column3)
    db.commit()
    
    # 创建测试字典
    dictionary = Dictionary(
        id=str(uuid.uuid4()),
        code=f"test_dict_{uuid.uuid4().hex[:8]}",
        name="测试字典",
        description="用于测试的字典",
        status=True,
        created_by="test_user",
        created_at=now,
        updated_at=now
    )
    
    db.add(dictionary)
    db.commit()    
    # 返回测试数据的ID
    yield {
        "table_id": table1.id,
        "field_id": column1.id,
        "dictionary_id": dictionary.id
    }
    
    # 清理 - 由于我们使用的是文件数据库，不需要显式删除表
    # 数据库连接会在会话结束时自动关闭
    db.close()