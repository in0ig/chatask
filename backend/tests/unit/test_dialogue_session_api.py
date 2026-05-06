"""
对话会话管理 API 测试
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch
from datetime import datetime

from src.main import app
from src.models.dialogue_session_model import SessionStatus


client = TestClient(app)


@pytest.fixture
def mock_dialogue_manager():
    """Mock 对话管理器"""
    with patch('src.api.dialogue_session_api.get_dialogue_manager') as mock:
        manager = Mock()
        mock.return_value = manager
        yield manager


class TestCreateSession:
    """测试创建会话 API"""
    
    def test_create_session_success(self, mock_dialogue_manager):
        """测试成功创建会话"""
        # 准备
        mock_dialogue_manager.create_session.return_value = {
            "success": True,
            "session_id": "test-session-123",
            "session": {
                "session_id": "test-session-123",
                "status": "active"
            }
        }
        
        # 执行
        response = client.post("/api/dialogue/sessions", json={
            "user_id": "user123",
            "title": "测试会话"
        })
        
        # 验证
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data
    
    def test_create_session_with_defaults(self, mock_dialogue_manager):
        """测试使用默认参数创建会话"""
        # 准备
        mock_dialogue_manager.create_session.return_value = {
            "success": True,
            "session_id": "test-session"
        }
        
        # 执行
        response = client.post("/api/dialogue/sessions", json={})
        
        # 验证
        assert response.status_code == 200
    
    def test_create_session_error(self, mock_dialogue_manager):
        """测试创建会话失败"""
        # 准备
        mock_dialogue_manager.create_session.return_value = {
            "success": False,
            "error": "数据库错误"
        }
        
        # 执行
        response = client.post("/api/dialogue/sessions", json={})
        
        # 验证
        assert response.status_code == 500


class TestGetSession:
    """测试获取会话 API"""
    
    def test_get_session_success(self, mock_dialogue_manager):
        """测试成功获取会话"""
        # 准备
        mock_dialogue_manager.get_session.return_value = {
            "session_id": "test-session",
            "status": "active",
            "message_count": 5
        }
        
        # 执行
        response = client.get("/api/dialogue/sessions/test-session")
        
        # 验证
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["session"]["session_id"] == "test-session"
    
    def test_get_session_not_found(self, mock_dialogue_manager):
        """测试会话不存在"""
        # 准备
        mock_dialogue_manager.get_session.return_value = None
        
        # 执行
        response = client.get("/api/dialogue/sessions/nonexistent")
        
        # 验证
        assert response.status_code == 404


class TestUpdateSessionStatus:
    """测试更新会话状态 API"""
    
    def test_update_status_success(self, mock_dialogue_manager):
        """测试成功更新状态"""
        # 准备
        mock_dialogue_manager.update_session_status.return_value = {
            "success": True,
            "session_id": "test-session",
            "old_status": "active",
            "new_status": "paused"
        }
        
        # 执行
        response = client.put("/api/dialogue/sessions/test-session/status", json={
            "status": "paused",
            "reason": "用户暂停"
        })
        
        # 验证
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
    
    def test_update_status_error(self, mock_dialogue_manager):
        """测试更新状态失败"""
        # 准备
        mock_dialogue_manager.update_session_status.return_value = {
            "success": False,
            "error": "会话不存在"
        }
        
        # 执行
        response = client.put("/api/dialogue/sessions/test-session/status", json={
            "status": "closed"
        })
        
        # 验证
        assert response.status_code == 400


class TestPauseResumeSession:
    """测试暂停和恢复会话 API"""
    
    def test_pause_session(self, mock_dialogue_manager):
        """测试暂停会话"""
        # 准备
        mock_dialogue_manager.pause_session.return_value = {
            "success": True,
            "session_id": "test-session"
        }
        
        # 执行
        response = client.post("/api/dialogue/sessions/test-session/pause")
        
        # 验证
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
    
    def test_resume_session(self, mock_dialogue_manager):
        """测试恢复会话"""
        # 准备
        mock_dialogue_manager.resume_session.return_value = {
            "success": True,
            "session_id": "test-session"
        }
        
        # 执行
        response = client.post("/api/dialogue/sessions/test-session/resume")
        
        # 验证
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True


class TestCloseSession:
    """测试关闭会话 API"""
    
    def test_close_session(self, mock_dialogue_manager):
        """测试关闭会话"""
        # 准备
        mock_dialogue_manager.close_session.return_value = {
            "success": True,
            "session_id": "test-session"
        }
        
        # 执行
        response = client.post("/api/dialogue/sessions/test-session/close")
        
        # 验证
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True


class TestPersistSessionContext:
    """测试持久化会话上下文 API"""
    
    def test_persist_context(self, mock_dialogue_manager):
        """测试持久化上下文"""
        # 准备
        mock_dialogue_manager.persist_session_context.return_value = {
            "success": True,
            "session_id": "test-session",
            "message_count": 10
        }
        
        # 执行
        response = client.post("/api/dialogue/sessions/test-session/persist")
        
        # 验证
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True


class TestListSessions:
    """测试列出会话 API"""
    
    def test_list_sessions_all(self, mock_dialogue_manager):
        """测试列出所有会话"""
        # 准备
        mock_dialogue_manager.list_sessions.return_value = {
            "success": True,
            "total": 2,
            "limit": 50,
            "offset": 0,
            "sessions": [
                {"session_id": "session1"},
                {"session_id": "session2"}
            ]
        }
        
        # 执行
        response = client.get("/api/dialogue/sessions")
        
        # 验证
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["total"] == 2
    
    def test_list_sessions_with_filters(self, mock_dialogue_manager):
        """测试带过滤条件列出会话"""
        # 准备
        mock_dialogue_manager.list_sessions.return_value = {
            "success": True,
            "total": 1,
            "sessions": []
        }
        
        # 执行
        response = client.get(
            "/api/dialogue/sessions",
            params={"user_id": "user123", "status": "active"}
        )
        
        # 验证
        assert response.status_code == 200


class TestSessionStatistics:
    """测试会话统计 API"""
    
    def test_get_statistics(self, mock_dialogue_manager):
        """测试获取统计信息"""
        # 准备
        mock_dialogue_manager.get_session_statistics.return_value = {
            "success": True,
            "statistics": {
                "session_id": "test-session",
                "message_count": 10,
                "total_tokens": 2000
            }
        }
        
        # 执行
        response = client.get("/api/dialogue/sessions/test-session/statistics")
        
        # 验证
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["statistics"]["message_count"] == 10


class TestMigrateSession:
    """测试会话迁移 API"""
    
    def test_migrate_session(self, mock_dialogue_manager):
        """测试迁移会话"""
        # 准备
        mock_dialogue_manager.migrate_session.return_value = {
            "success": True,
            "session_id": "test-session",
            "old_user_id": "user1",
            "new_user_id": "user2"
        }
        
        # 执行
        response = client.post("/api/dialogue/sessions/test-session/migrate", json={
            "target_user_id": "user2",
            "reason": "测试迁移"
        })
        
        # 验证
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True


class TestMaintenance:
    """测试维护操作 API"""
    
    def test_archive_old_sessions(self, mock_dialogue_manager):
        """测试归档旧会话"""
        # 准备
        mock_dialogue_manager.archive_old_sessions.return_value = {
            "success": True,
            "archived_count": 5
        }
        
        # 执行
        response = client.post("/api/dialogue/maintenance/archive")
        
        # 验证
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "已归档 5 个会话" in data["message"]
    
    def test_cleanup_archived_sessions(self, mock_dialogue_manager):
        """测试清理归档会话"""
        # 准备
        mock_dialogue_manager.cleanup_archived_sessions.return_value = {
            "success": True,
            "deleted_count": 3
        }
        
        # 执行
        response = client.post("/api/dialogue/maintenance/cleanup?days=90")
        
        # 验证
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "已清理 3 个归档会话" in data["message"]


class TestHealthCheck:
    """测试健康检查 API"""
    
    def test_health_check(self):
        """测试健康检查"""
        # 执行
        response = client.get("/api/dialogue/health")
        
        # 验证
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
