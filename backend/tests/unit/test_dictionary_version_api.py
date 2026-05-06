"""
字典版本管理 API 单元测试
"""
import pytest
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import uuid

from src.main import app
from src.database import Base, get_db
from src.models.data_preparation_model import (
    Dictionary, DictionaryVersion, DictionaryVersionItem, DictionaryItem
)
from src.services.dictionary_version_service import DictionaryVersionService
from src.api.dictionary_version import router as dictionary_version_router

# 使用内存数据库进行测试
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 创建测试数据库
Base.metadata.create_all(bind=engine)

# 覆盖依赖项
def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

# 测试客户端
client = TestClient(app)

# 测试数据
TEST_DICTIONARY_ID = str(uuid.uuid4())
TEST_VERSION_ID_1 = str(uuid.uuid4())
TEST_VERSION_ID_2 = str(uuid.uuid4())
TEST_VERSION_ID_3 = str(uuid.uuid4())

@pytest.fixture(autouse=True)
def setup_database():
    """设置测试数据库"""
    # 清空数据库
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    
    # 创建测试字典
    test_dictionary = Dictionary(
        id=TEST_DICTIONARY_ID,
        code="test_dict",
        name="测试字典",
        created_by="test_user"
    )
    
    # 创建测试字典项
    test_items = [
        DictionaryItem(
            dictionary_id=TEST_DICTIONARY_ID,
            item_key="key1",
            item_value="value1",
            description="测试项1",
            created_by="test_user"
        ),
        DictionaryItem(
            dictionary_id=TEST_DICTIONARY_ID,
            item_key="key2",
            item_value="value2",
            description="测试项2",
            created_by="test_user"
        ),
        DictionaryItem(
            dictionary_id=TEST_DICTIONARY_ID,
            item_key="key3",
            item_value="value3",
            description="测试项3",
            created_by="test_user"
        )
    ]
    
    # 添加到数据库
    db = TestingSessionLocal()
    try:
        db.add(test_dictionary)
        for item in test_items:
            db.add(item)
        db.commit()
    finally:
        db.close()


def test_create_version_from_current():
    """测试从当前状态创建版本"""
    with patch('src.api.dictionary_version.DictionaryVersionService') as mock_service_class:
        mock_service = Mock()
        mock_service_class.return_value = mock_service
        
        # 模拟服务返回
        mock_version = DictionaryVersionResponse(
            id=TEST_VERSION_ID_1,
            dictionary_id=TEST_DICTIONARY_ID,
            version_number=1,
            version_name="v1.0",
            description="初始版本",
            change_type="created",
            change_summary="创建初始版本",
            items_count=10,
            created_at=datetime.now(),
            is_current=True
        )
        
        mock_service.create_version_from_current.return_value = mock_version
        
        request_data = {
            "dictionary_id": TEST_DICTIONARY_ID,
            "version_name": "v1.0",
            "description": "初始版本",
            "change_summary": "创建初始版本"
        }
        
        response = client.post("/api/dictionary-version/create-from-current", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == TEST_VERSION_ID_1
        assert data["dictionary_id"] == TEST_DICTIONARY_ID
        assert data["version_number"] == 1
        assert data["version_name"] == "v1.0"


def test_get_version_list():
    """测试获取版本列表"""
    with patch('src.api.dictionary_version.DictionaryVersionService') as mock_service_class:
        mock_service = Mock()
        mock_service_class.return_value = mock_service
        
        # 模拟版本列表
        mock_versions = []
        for i in range(2):
            mock_version = DictionaryVersionResponse(
                id=f"version-{i+1}",
                dictionary_id=TEST_DICTIONARY_ID,
                version_number=i + 1,
                version_name=f"v{i+1}.0",
                description=f"版本 {i+1}",
                change_type="created",
                items_count=10,
                created_at=datetime.now(),
                is_current=(i == 1)
            )
            mock_versions.append(mock_version)
        
        # 返回模拟数据，使用字典格式
        mock_service.get_version_list.return_value = {
            "items": mock_versions,
            "total": 2,
            "page": 1,
            "page_size": 10
        }
        
        response = client.get(f"/api/dictionary-version/{TEST_DICTIONARY_ID}/list?page=1&page_size=10")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert data["page"] == 1
        assert data["page_size"] == 10
        assert len(data["items"]) == 2


def test_get_version_detail():
    """测试获取版本详情"""
    with patch('src.api.dictionary_version.DictionaryVersionService') as mock_service_class:
        mock_service = Mock()
        mock_service_class.return_value = mock_service
        
        # 模拟版本详情
        mock_version_info = {
            "id": TEST_VERSION_ID_1,
            "dictionary_id": TEST_DICTIONARY_ID,
            "version_number": 1,
            "version_name": "v1.0",
            "description": None,
            "change_type": "created",
            "change_summary": None,
            "items_count": 0,
            "created_at": datetime.now(),
            "is_current": False
        }
        
        mock_detail = {
            "version_info": mock_version_info,
            "items": [
                {"item_key": "key1", "item_value": "value1", "item_order": 1, "status": True},
                {"item_key": "key2", "item_value": "value2", "item_order": 2, "status": True}
            ],
            "statistics": {
                "total_versions": 1,
                "current_version_number": 1,
                "latest_change_time": None,
                "change_frequency": {}
            }
        }
        
        mock_service.get_version_detail.return_value = mock_detail
        
        response = client.get(f"/api/dictionary-version/detail/{TEST_VERSION_ID_1}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["version_info"]["id"] == TEST_VERSION_ID_1
        assert len(data["items"]) == 2
        assert data["statistics"]["total_versions"] == 1


def test_compare_versions():
    """测试版本比较功能"""
    with patch('src.api.dictionary_version.DictionaryVersionService') as mock_service_class:
        mock_service = Mock()
        mock_service_class.return_value = mock_service
        
        # 模拟比较结果
        mock_source_version = DictionaryVersionResponse(
            id=TEST_VERSION_ID_1,
            dictionary_id=TEST_DICTIONARY_ID,
            version_number=1,
            version_name="v1.0",
            description=None,
            change_type="created",
            change_summary=None,
            items_count=0,
            created_at=datetime.now(),
            is_current=False
        )
        
        mock_target_version = DictionaryVersionResponse(
            id=TEST_VERSION_ID_2,
            dictionary_id=TEST_DICTIONARY_ID,
            version_number=2,
            version_name="v2.0",
            description=None,
            change_type="created",
            change_summary=None,
            items_count=0,
            created_at=datetime.now(),
            is_current=False
        )
        
        mock_comparison = VersionCompareResponse(
            dictionary_id=TEST_DICTIONARY_ID,
            source_version=mock_source_version,
            target_version=mock_target_version,
            changes=[
                {
                    "item_key": "key1",
                    "change_type": "added",
                    "old_value": None,
                    "new_value": "new_value"
                }
            ],
            summary={"added": 1, "updated": 0, "deleted": 0}
        )
        
        mock_service.compare_versions.return_value = mock_comparison
        
        compare_data = {
            "dictionary_id": TEST_DICTIONARY_ID,
            "source_version_id": TEST_VERSION_ID_1,
            "target_version_id": TEST_VERSION_ID_2
        }
        
        response = client.post("/api/dictionary-version/compare", json=compare_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["dictionary_id"] == TEST_DICTIONARY_ID
        assert len(data["changes"]) == 1
        assert data["summary"]["added"] == 1


def test_rollback_version():
    """测试版本回滚功能"""
    with patch('src.api.dictionary_version.DictionaryVersionService') as mock_service_class:
        mock_service = Mock()
        mock_service_class.return_value = mock_service
        
        # 模拟回滚结果
        mock_new_version = DictionaryVersionResponse(
            id="new-version-id",
            dictionary_id=TEST_DICTIONARY_ID,
            version_number=1,
            version_name="v1.0",
            description=None,
            change_type="created",
            change_summary=None,
            items_count=0,
            created_at=datetime.now(),
            is_current=False
        )
        
        mock_rollback_result = VersionRollbackResponse(
            success=True,
            message="成功回滚到版本 1",
            new_version=mock_new_version,
            changes_applied=10,
            rollback_time=datetime.now()
        )
        
        mock_service.rollback_version.return_value = mock_rollback_result
        
        rollback_data = {
            "dictionary_id": TEST_DICTIONARY_ID,
            "target_version_id": TEST_VERSION_ID_1,
            "description": "回滚到稳定版本"
        }
        
        response = client.post("/api/dictionary-version/rollback", json=rollback_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["changes_applied"] == 10
        assert "成功回滚" in data["message"]


def test_error_handling():
    """测试错误处理和边界情况"""
    with patch('src.api.dictionary_version.DictionaryVersionService') as mock_service_class:
        mock_service = Mock()
        mock_service_class.return_value = mock_service
        
        # 模拟字典不存在错误
        mock_service.create_version_from_current.side_effect = ValueError("字典不存在")
        
        response = client.post("/api/dictionary-version/create-from-current", json={
            "dictionary_id": "non-existent-id",
            "version_name": "v1.0"
        })
        assert response.status_code == 400
        assert "字典不存在" in response.json()["detail"]


def test_version_statistics():
    """测试版本统计信息"""
    with patch('src.api.dictionary_version.DictionaryVersionService') as mock_service_class:
        mock_service = Mock()
        mock_service_class.return_value = mock_service
        
        # 创建 VersionStatistics 模型实例作为模拟返回值
        mock_statistics = VersionStatistics(
            total_versions=3,
            current_version_number=3,
            latest_change_time=datetime.now(),
            change_frequency={
                "created": 1,
                "updated": 1,
                "deleted": 1
            }
        )
        
        # 模拟 get_version_statistics 方法返回统计信息，而不是 get_version_list
        mock_service.get_version_statistics.return_value = mock_statistics
        
        # 调用正确的统计信息API端点
        response = client.get(f"/api/dictionary-version/statistics/{TEST_DICTIONARY_ID}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_versions"] == 3
        assert data["current_version_number"] == 3
        assert data["change_frequency"]["created"] == 1
        assert data["change_frequency"]["updated"] == 1
        assert data["change_frequency"]["deleted"] == 1
        assert "latest_change_time" in data


def test_multiple_versions():
    """测试多个版本的创建和管理"""
    with patch('src.api.dictionary_version.DictionaryVersionService') as mock_service_class:
        mock_service = Mock()
        mock_service_class.return_value = mock_service
        
        # 模拟创建多个版本
        def mock_create_version(request):
            mock_version = DictionaryVersionResponse(
                id=str(uuid.uuid4()),
                dictionary_id=request.dictionary_id,
                version_number=1,
                version_name=request.version_name,
                description=request.description,
                change_type="created",
                change_summary=request.change_summary,
                items_count=10,
                created_at=datetime.now(),
                is_current=True
            )
            return mock_version
        
        mock_service.create_version_from_current.side_effect = mock_create_version
        
        # 创建5个版本
        for i in range(5):
            response = client.post("/api/dictionary-version/create-from-current", json={
                "dictionary_id": TEST_DICTIONARY_ID,
                "version_name": f"v{i+1}.0",
                "description": f"版本 {i+1}",
                "change_summary": f"创建版本 {i+1}"
            })
            assert response.status_code == 200
            data = response.json()
            assert data["version_name"] == f"v{i+1}.0"