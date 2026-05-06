"""
对话管理服务测试
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from sqlalchemy.orm import Session

from src.services.dialogue_manager import DialogueManager
from src.services.context_manager import ContextManager
from src.models.dialogue_session_model import DialogueSession, SessionStatus


@pytest.fixture
def mock_db():
    """Mock 数据库会话"""
    db = Mock(spec=Session)
    db.query = Mock()
    db.add = Mock()
    db.commit = Mock()
    db.refresh = Mock()
    db.rollback = Mock()
    db.delete = Mock()
    return db


@pytest.fixture
def mock_context_manager():
    """Mock 上下文管理器"""
    manager = Mock(spec=ContextManager)
    manager.sessions = {}
    manager.create_session = Mock()
    manager.get_session = Mock()
    manager.get_session_stats = Mock(return_value={
        "session_id": "test-session",
        "cloud_message_count": 5,
        "local_message_count": 5,
        "total_tokens": 1000
    })
    return manager


@pytest.fixture
def dialogue_manager(mock_db, mock_context_manager):
    """对话管理器实例"""
    manager = DialogueManager(mock_db, mock_context_manager)
    return manager


class TestCreateSession:
    """测试创建会话"""
    
    def test_create_session_success(self, dialogue_manager, mock_db, mock_context_manager):
        """测试成功创建会话"""
        # 准备
        mock_context_manager.create_session.return_value = Mock()
        
        # 执行
        result = dialogue_manager.create_session(
            user_id="user123",
            title="测试会话",
            description="这是一个测试会话"
        )
        
        # 验证
        assert result["success"] is True
        assert "session_id" in result
        assert mock_db.add.called
        assert mock_db.commit.called
        assert mock_context_manager.create_session.called
    
    def test_create_session_with_defaults(self, dialogue_manager, mock_db, mock_context_manager):
        """测试使用默认参数创建会话"""
        # 准备
        mock_context_manager.create_session.return_value = Mock()
        
        # 执行
        result = dialogue_manager.create_session()
        
        # 验证
        assert result["success"] is True
        assert mock_db.add.called
    
    def test_create_session_database_error(self, dialogue_manager, mock_db, mock_context_manager):
        """测试数据库错误"""
        # 准备
        mock_db.commit.side_effect = Exception("数据库错误")
        
        # 执行
        result = dialogue_manager.create_session()
        
        # 验证
        assert result["success"] is False
        assert "error" in result
        assert mock_db.rollback.called


class TestGetSession:
    """测试获取会话"""
    
    def test_get_session_success(self, dialogue_manager, mock_db):
        """测试成功获取会话"""
        # 准备
        mock_session = Mock(spec=DialogueSession)
        mock_session.session_id = "test-session"
        mock_session.to_dict.return_value = {"session_id": "test-session"}
        
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = mock_session
        mock_db.query.return_value = mock_query
        
        # 执行
        result = dialogue_manager.get_session("test-session")
        
        # 验证
        assert result is not None
        assert result["session_id"] == "test-session"
        assert mock_db.commit.called
    
    def test_get_session_not_found(self, dialogue_manager, mock_db):
        """测试会话不存在"""
        # 准备
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = None
        mock_db.query.return_value = mock_query
        
        # 执行
        result = dialogue_manager.get_session("nonexistent")
        
        # 验证
        assert result is None


class TestUpdateSessionStatus:
    """测试更新会话状态"""
    
    def test_update_status_success(self, dialogue_manager, mock_db):
        """测试成功更新状态"""
        # 准备
        mock_session = Mock(spec=DialogueSession)
        mock_session.session_id = "test-session"
        mock_session.status = SessionStatus.ACTIVE
        mock_session.context_data = {}
        
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = mock_session
        mock_db.query.return_value = mock_query
        
        # 执行
        result = dialogue_manager.update_session_status(
            "test-session",
            SessionStatus.PAUSED,
            "用户暂停"
        )
        
        # 验证
        assert result["success"] is True
        assert mock_session.status == SessionStatus.PAUSED
        assert mock_db.commit.called
    
    def test_update_status_not_found(self, dialogue_manager, mock_db):
        """测试会话不存在"""
        # 准备
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = None
        mock_db.query.return_value = mock_query
        
        # 执行
        result = dialogue_manager.update_session_status(
            "nonexistent",
            SessionStatus.CLOSED
        )
        
        # 验证
        assert result["success"] is False
        assert "error" in result


class TestPauseResumeSession:
    """测试暂停和恢复会话"""
    
    def test_pause_session(self, dialogue_manager, mock_db):
        """测试暂停会话"""
        # 准备
        mock_session = Mock(spec=DialogueSession)
        mock_session.status = SessionStatus.ACTIVE
        mock_session.context_data = {}
        
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = mock_session
        mock_db.query.return_value = mock_query
        
        # 执行
        result = dialogue_manager.pause_session("test-session", "测试暂停")
        
        # 验证
        assert result["success"] is True
        assert mock_session.status == SessionStatus.PAUSED
    
    def test_resume_session_success(self, dialogue_manager, mock_db):
        """测试恢复会话"""
        # 准备
        mock_session = Mock(spec=DialogueSession)
        mock_session.session_id = "test-session"
        mock_session.status = SessionStatus.PAUSED
        mock_session.context_data = {}
        mock_session.cloud_messages = []
        mock_session.local_messages = []
        
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = mock_session
        mock_db.query.return_value = mock_query
        
        # 执行
        result = dialogue_manager.resume_session("test-session")
        
        # 验证
        assert result["success"] is True
    
    def test_resume_session_wrong_status(self, dialogue_manager, mock_db):
        """测试恢复非暂停状态的会话"""
        # 准备
        mock_session = Mock(spec=DialogueSession)
        mock_session.status = SessionStatus.ACTIVE
        
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = mock_session
        mock_db.query.return_value = mock_query
        
        # 执行
        result = dialogue_manager.resume_session("test-session")
        
        # 验证
        assert result["success"] is False
        assert "只能恢复暂停的会话" in result["error"]


class TestCloseSession:
    """测试关闭会话"""
    
    def test_close_session_success(self, dialogue_manager, mock_db, mock_context_manager):
        """测试成功关闭会话"""
        # 准备
        mock_session = Mock(spec=DialogueSession)
        mock_session.session_id = "test-session"
        mock_session.status = SessionStatus.ACTIVE
        mock_session.context_data = {}
        
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = mock_session
        mock_db.query.return_value = mock_query
        
        mock_context = Mock()
        mock_context.cloud_messages = []
        mock_context.local_messages = []
        mock_context.total_tokens = 0
        mock_context.compressed_context = None
        mock_context.created_at = datetime.now()
        mock_context.last_activity = datetime.now()
        
        mock_context_manager.get_session.return_value = mock_context
        mock_context_manager.sessions = {"test-session": mock_context}
        
        # 执行
        result = dialogue_manager.close_session("test-session", "测试关闭")
        
        # 验证
        assert result["success"] is True
        assert mock_session.status == SessionStatus.CLOSED


class TestPersistSessionContext:
    """测试持久化会话上下文"""
    
    def test_persist_context_success(self, dialogue_manager, mock_db, mock_context_manager):
        """测试成功持久化上下文"""
        # 准备
        mock_session = Mock(spec=DialogueSession)
        mock_session.session_id = "test-session"
        
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = mock_session
        mock_db.query.return_value = mock_query
        
        mock_context = Mock()
        mock_context.cloud_messages = []
        mock_context.local_messages = []
        mock_context.total_tokens = 1000
        mock_context.compressed_context = "compressed"
        mock_context.created_at = datetime.now()
        mock_context.last_activity = datetime.now()
        
        mock_context_manager.get_session.return_value = mock_context
        
        # 执行
        result = dialogue_manager.persist_session_context("test-session")
        
        # 验证
        assert result["success"] is True
        assert mock_db.commit.called
    
    def test_persist_context_no_context(self, dialogue_manager, mock_context_manager):
        """测试上下文不存在"""
        # 准备
        mock_context_manager.get_session.return_value = None
        
        # 执行
        result = dialogue_manager.persist_session_context("test-session")
        
        # 验证
        assert result["success"] is False
        assert "上下文不存在" in result["error"]


class TestListSessions:
    """测试列出会话"""
    
    def test_list_sessions_all(self, dialogue_manager, mock_db):
        """测试列出所有会话"""
        # 准备
        mock_sessions = [
            Mock(spec=DialogueSession, to_dict=Mock(return_value={"id": 1})),
            Mock(spec=DialogueSession, to_dict=Mock(return_value={"id": 2}))
        ]
        
        mock_query = Mock()
        mock_query.order_by.return_value = mock_query
        mock_query.count.return_value = 2
        mock_query.limit.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.all.return_value = mock_sessions
        mock_db.query.return_value = mock_query
        
        # 执行
        result = dialogue_manager.list_sessions()
        
        # 验证
        assert result["success"] is True
        assert result["total"] == 2
        assert len(result["sessions"]) == 2
    
    def test_list_sessions_with_filters(self, dialogue_manager, mock_db):
        """测试带过滤条件列出会话"""
        # 准备
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.count.return_value = 1
        mock_query.limit.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.all.return_value = []
        mock_db.query.return_value = mock_query
        
        # 执行
        result = dialogue_manager.list_sessions(
            user_id="user123",
            status=SessionStatus.ACTIVE
        )
        
        # 验证
        assert result["success"] is True


class TestArchiveAndCleanup:
    """测试归档和清理"""
    
    def test_archive_old_sessions(self, dialogue_manager, mock_db, mock_context_manager):
        """测试归档旧会话"""
        # 准备
        old_date = datetime.now() - timedelta(days=40)
        mock_session = Mock(spec=DialogueSession)
        mock_session.session_id = "old-session"
        mock_session.status = SessionStatus.CLOSED
        mock_session.auto_archive = True
        mock_session.archive_after_days = 30
        mock_session.closed_at = old_date
        
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = [mock_session]
        mock_db.query.return_value = mock_query
        
        mock_context_manager.sessions = {}
        
        # 执行
        result = dialogue_manager.archive_old_sessions()
        
        # 验证
        assert result["success"] is True
        assert result["archived_count"] == 1
        assert mock_session.status == SessionStatus.ARCHIVED
    
    def test_cleanup_archived_sessions(self, dialogue_manager, mock_db):
        """测试清理归档会话"""
        # 准备
        old_date = datetime.now() - timedelta(days=100)
        mock_session = Mock(spec=DialogueSession)
        mock_session.status = SessionStatus.ARCHIVED
        mock_session.archived_at = old_date
        
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = [mock_session]
        mock_db.query.return_value = mock_query
        
        # 执行
        result = dialogue_manager.cleanup_archived_sessions(days=90)
        
        # 验证
        assert result["success"] is True
        assert result["deleted_count"] == 1
        assert mock_db.delete.called


class TestSessionStatistics:
    """测试会话统计"""
    
    def test_get_session_statistics(self, dialogue_manager, mock_db, mock_context_manager):
        """测试获取会话统计"""
        # 准备
        mock_session = Mock(spec=DialogueSession)
        mock_session.session_id = "test-session"
        mock_session.status = SessionStatus.ACTIVE
        mock_session.message_count = 10
        mock_session.total_tokens = 2000
        mock_session.error_count = 0
        mock_session.created_at = datetime.now() - timedelta(hours=2)
        mock_session.last_activity_at = datetime.now()
        
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = mock_session
        mock_db.query.return_value = mock_query
        
        # 执行
        result = dialogue_manager.get_session_statistics("test-session")
        
        # 验证
        assert result["success"] is True
        assert "statistics" in result
        assert result["statistics"]["message_count"] == 10


class TestMigrateSession:
    """测试会话迁移"""
    
    def test_migrate_session_success(self, dialogue_manager, mock_db):
        """测试成功迁移会话"""
        # 准备
        mock_session = Mock(spec=DialogueSession)
        mock_session.session_id = "test-session"
        mock_session.user_id = "user1"
        mock_session.context_data = {}
        
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = mock_session
        mock_db.query.return_value = mock_query
        
        # 执行
        result = dialogue_manager.migrate_session(
            "test-session",
            "user2",
            "测试迁移"
        )
        
        # 验证
        assert result["success"] is True
        assert mock_session.user_id == "user2"
        assert mock_db.commit.called
    
    def test_migrate_session_not_found(self, dialogue_manager, mock_db):
        """测试迁移不存在的会话"""
        # 准备
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = None
        mock_db.query.return_value = mock_query
        
        # 执行
        result = dialogue_manager.migrate_session("nonexistent", "user2")
        
        # 验证
        assert result["success"] is False
        assert "会话不存在" in result["error"]
