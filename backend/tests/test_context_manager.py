import pytest
import json
import sys
import pathlib
from datetime import datetime
from unittest.mock import patch, MagicMock
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add src directory to Python path to ensure modules can be imported
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "src"))

from services.context_manager import ContextManager
from models.database_models import Base, SessionContext, ConversationMessage, TokenUsageStats, ContextType, ModelType, Role, ModelUsed
from utils import get_db_session as get_db

# 测试数据
TEST_SESSION_ID = "test-session-123"
TEST_MESSAGES = [
    {"role": "user", "content": "上个月的销售额是多少？"},
    {"role": "assistant", "content": "上个月的销售额是1,250,000元。"},
    {"role": "user", "content": "和上上个月相比呢？"},
    {"role": "assistant", "content": "与上上个月相比，销售额增长了15%。"}
]


# 创建SQLite内存数据库引擎用于测试
TEST_DATABASE_URL = "sqlite:///:memory:"
test_engine = create_engine(TEST_DATABASE_URL)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

# 创建所有表
Base.metadata.create_all(bind=test_engine)

def get_test_db():
    """为测试创建数据库会话"""
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()

class TestContextManager:
    """ContextManager类的单元测试"""
    
    def setup_method(self):
        """设置测试环境"""
        self.context_manager = ContextManager()
        # 为每个测试创建新的数据库会话
        self.test_db = next(get_test_db())
        
    @patch('services.context_manager.get_db')
    def test_get_session_context_existing(self, mock_get_db):
        """测试获取存在的会话上下文"""
        # 创建真实的SessionContext对象并添加到数据库
        context = SessionContext(
            session_id=TEST_SESSION_ID,
            context_type=ContextType.local_model,
            messages=TEST_MESSAGES,
            token_count=120,
            summary="上个月的销售额分析",
            last_summary_at=datetime.now()
        )
        self.test_db.add(context)
        self.test_db.commit()
        
        # Mock get_db_session返回测试数据库会话
        mock_get_db.side_effect = lambda: iter([self.test_db])
        
        # 调用方法
        result = self.context_manager.get_session_context(TEST_SESSION_ID, ContextType.local_model)
        
        # 验证结果
        assert result is not None
        assert result["messages"] == TEST_MESSAGES
        assert result["token_count"] == 120
        assert result["summary"] == "上个月的销售额分析"
        
    @patch('services.context_manager.get_db')
    def test_get_session_context_not_found(self, mock_get_db):
        """测试获取不存在的会话上下文"""
        # Mock get_db_session返回测试数据库会话
        mock_get_db.side_effect = lambda: iter([self.test_db])
        
        # 调用方法
        result = self.context_manager.get_session_context("non-existent-session", ContextType.local_model)
        
        # 验证结果
        assert result is None
        
    @patch('services.context_manager.get_db')
    def test_get_session_messages(self, mock_get_db):
        """测试获取会话消息"""
        # 创建真实的ConversationMessage对象并添加到数据库
        message1 = ConversationMessage(
            session_id=TEST_SESSION_ID,
            turn=1,
            role=Role.user,
            content="上个月的销售额是多少？",
            token_count=10,
            model_used=ModelUsed.local,
            created_at=datetime.now()
        )
        message2 = ConversationMessage(
            session_id=TEST_SESSION_ID,
            turn=2,
            role=Role.assistant,
            content="上个月的销售额是1,250,000元。",
            token_count=12,
            model_used=ModelUsed.local,
            created_at=datetime.now()
        )
        self.test_db.add(message1)
        self.test_db.add(message2)
        self.test_db.commit()
        
        # Mock get_db_session返回测试数据库会话
        mock_get_db.side_effect = lambda: iter([self.test_db])
        
        # 调用方法
        result = self.context_manager.get_session_messages(TEST_SESSION_ID, limit=10)
        
        # 验证结果
        assert len(result) == 2
        assert result[0]["role"] == "user"
        assert result[0]["content"] == "上个月的销售额是多少？"
        assert result[1]["role"] == "assistant"
        assert result[1]["content"] == "上个月的销售额是1,250,000元。"
        
    @patch('services.context_manager.get_db')
    def test_get_token_usage(self, mock_get_db):
        """测试获取token使用统计"""
        # 创建真实的TokenUsageStats对象并添加到数据库
        stat1 = TokenUsageStats(
            session_id=TEST_SESSION_ID,
            model_type=ModelType.local,
            turn=1,
            input_tokens=50,
            output_tokens=30,
            total_tokens=80,
            created_at=datetime.now()
        )
        stat2 = TokenUsageStats(
            session_id=TEST_SESSION_ID,
            model_type=ModelType.aliyun,
            turn=2,
            input_tokens=40,
            output_tokens=25,
            total_tokens=65,
            created_at=datetime.now()
        )
        self.test_db.add(stat1)
        self.test_db.add(stat2)
        self.test_db.commit()
        
        # Mock get_db_session返回测试数据库会话
        mock_get_db.side_effect = lambda: iter([self.test_db])
        
        # 调用方法
        result = self.context_manager.get_token_usage(TEST_SESSION_ID)
        
        # 验证结果
        assert result["session_id"] == TEST_SESSION_ID
        assert result["total_turns"] == 2
        assert result["total_input_tokens"] == 90
        assert result["total_output_tokens"] == 55
        assert result["total_tokens"] == 145
        assert result["model_usage"]["local"]["input_tokens"] == 50
        assert result["model_usage"]["aliyun"]["output_tokens"] == 25
        
    @patch('services.context_manager.get_db')
    def test_summarize_context(self, mock_get_db):
        """测试总结上下文"""
        # 创建真实的SessionContext对象并添加到数据库
        context = SessionContext(
            session_id=TEST_SESSION_ID,
            context_type=ContextType.local_model,
            messages=TEST_MESSAGES,
            token_count=120,
            summary="",
            last_summary_at=None
        )
        self.test_db.add(context)
        self.test_db.commit()
        
        # Mock get_db_session返回测试数据库会话
        mock_get_db.side_effect = lambda: iter([self.test_db])
        
        # 调用方法
        summary = self.context_manager.summarize_context(TEST_SESSION_ID, ContextType.local_model, TEST_MESSAGES)
        
        # 验证结果
        assert isinstance(summary, str)
        assert len(summary) > 0
        assert "会话包含2条用户查询和2条助手回复" in summary
        
        # 验证数据库更新
        updated_context = self.test_db.query(SessionContext).filter(
            SessionContext.session_id == TEST_SESSION_ID,
            SessionContext.context_type == ContextType.local_model
        ).first()
        assert updated_context.summary == summary
        assert updated_context.last_summary_at is not None
        
    def test_calculate_token_count_local(self):
        """测试本地模型token计数"""
        # 测试空字符串
        assert self.context_manager.calculate_token_count("", ModelType.local) == 0
        
        # 测试简单文本
        text = "你好，世界！"
        # 由于tiktoken被mock，使用估算值
        # 实际测试中应该mock tiktoken
        result = self.context_manager.calculate_token_count(text, ModelType.local)
        assert result > 0
        
    def test_calculate_token_count_aliyun(self):
        """测试阿里云模型token计数"""
        text = "这是一个测试文本"
        result = self.context_manager.calculate_token_count(text, ModelType.aliyun)
        assert result > 0
        
    @patch('services.context_manager.get_db')
    def test_update_token_usage(self, mock_get_db):
        """测试更新token使用统计"""
        # 这个测试主要验证方法不会抛出异常
        # 由于涉及数据库操作，我们只验证基本功能
        try:
            # Mock get_db_session返回测试数据库会话
            mock_get_db.side_effect = lambda: iter([self.test_db])
            
            self.context_manager.update_token_usage(TEST_SESSION_ID, ModelType.local, 1, 50, 30)
            # 验证数据是否被正确插入
            token_stat = self.test_db.query(TokenUsageStats).filter(
                TokenUsageStats.session_id == TEST_SESSION_ID,
                TokenUsageStats.model_type == ModelType.local,
                TokenUsageStats.turn == 1
            ).first()
            assert token_stat is not None
            assert token_stat.input_tokens == 50
            assert token_stat.output_tokens == 30
            assert token_stat.total_tokens == 80
            
            # 如果没有抛出异常，测试通过
            assert True
        except Exception as e:
            assert False, f"update_token_usage failed with error: {str(e)}"

