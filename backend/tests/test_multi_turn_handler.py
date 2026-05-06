import pytest
import sys
import pathlib
from datetime import datetime
from unittest.mock import patch, MagicMock
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add src directory to Python path to ensure modules can be imported
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "src"))

from services.multi_turn_handler import MultiTurnHandler
from models.database_models import Base, ConversationMessage, SessionContext, Role
from utils import get_db_session as get_db

# 测试数据
TEST_SESSION_ID = "test-session-123"
TEST_USER_MESSAGE = "上个月的销售额是多少？"
TEST_ASSISTANT_RESPONSE = "上个月的销售额是1,250,000元。"

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

class TestMultiTurnHandler:
    """MultiTurnHandler类的单元测试"""
    
    def setup_method(self):
        """设置测试环境"""
        self.multi_turn_handler = MultiTurnHandler()
        # 为每个测试创建新的数据库会话
        self.test_db = next(get_test_db())
        
    def teardown_method(self):
        """清理测试环境"""
        # 清空测试数据库
        self.test_db.query(ConversationMessage).delete()
        self.test_db.commit()
        
    @patch('services.multi_turn_handler.get_db')
    def test_add_message(self, mock_get_db):
        """测试添加消息"""
        # Mock get_db_session返回测试数据库会话
        mock_get_db.side_effect = lambda: iter([self.test_db])
        
        # 添加第一条消息
        message_data = {
            "role": "user",
            "content": TEST_USER_MESSAGE,
            "parent_message_id": None
        }
        result = self.multi_turn_handler.add_message(TEST_SESSION_ID, message_data)
        
        # 验证结果
        assert result["role"] == "user"
        assert result["content"] == TEST_USER_MESSAGE
        assert result["parent_message_id"] is None
        assert result["turn"] == 1
        
        # 验证数据库中存在该消息
        message = self.test_db.query(ConversationMessage).filter(
            ConversationMessage.session_id == TEST_SESSION_ID,
            ConversationMessage.turn == 1
        ).first()
        assert message is not None
        assert message.role.value == "user"
        assert message.content == TEST_USER_MESSAGE
        assert message.parent_message_id is None
        
    @patch('services.multi_turn_handler.get_db')
    def test_add_message_with_parent(self, mock_get_db):
        """测试添加带有父消息的消息"""
        # Mock get_db_session返回测试数据库会话
        mock_get_db.side_effect = lambda: iter([self.test_db])
        
        # 添加第一条消息
        first_message_data = {
            "role": "user",
            "content": TEST_USER_MESSAGE,
            "parent_message_id": None
        }
        first_result = self.multi_turn_handler.add_message(TEST_SESSION_ID, first_message_data)
        
        # 添加第二条消息，作为第一条消息的子消息
        second_message_data = {
            "role": "assistant",
            "content": TEST_ASSISTANT_RESPONSE,
            "parent_message_id": first_result["id"]
        }
        second_result = self.multi_turn_handler.add_message(TEST_SESSION_ID, second_message_data)
        
        # 验证第二条消息的parent_message_id正确
        assert second_result["parent_message_id"] == first_result["id"]
        assert second_result["turn"] == 2
        
        # 验证数据库中第二条消息的parent_message_id正确
        second_message = self.test_db.query(ConversationMessage).filter(
            ConversationMessage.session_id == TEST_SESSION_ID,
            ConversationMessage.turn == 2
        ).first()
        assert second_message.parent_message_id == first_result["id"]
        
    @patch('services.multi_turn_handler.get_db')
    def test_get_conversation_history(self, mock_get_db):
        """测试获取对话历史"""
        # Mock get_db_session返回测试数据库会话
        mock_get_db.side_effect = lambda: iter([self.test_db])
        
        # 添加多条消息
        messages_data = [
            {"role": "user", "content": "上个月的销售额是多少？", "parent_message_id": None},
            {"role": "assistant", "content": "上个月的销售额是1,250,000元。", "parent_message_id": None},
            {"role": "user", "content": "和上上个月相比呢？", "parent_message_id": None},
            {"role": "assistant", "content": "与上上个月相比，销售额增长了15%。", "parent_message_id": None}
        ]
        
        for msg_data in messages_data:
            self.multi_turn_handler.add_message(TEST_SESSION_ID, msg_data)
        
        # 获取对话历史
        history = self.multi_turn_handler.get_conversation_history(TEST_SESSION_ID)
        
        # 验证结果
        assert len(history) == 4
        assert history[0]["role"] == "user"
        assert history[0]["content"] == "上个月的销售额是多少？"
        assert history[1]["role"] == "assistant"
        assert history[1]["content"] == "上个月的销售额是1,250,000元。"
        assert history[2]["role"] == "user"
        assert history[2]["content"] == "和上上个月相比呢？"
        assert history[3]["role"] == "assistant"
        assert history[3]["content"] == "与上上个月相比，销售额增长了15%。"
        
        # 验证turn顺序正确
        turns = [msg["turn"] for msg in history]
        assert turns == [1, 2, 3, 4]
        
    @patch('services.multi_turn_handler.get_db')
    def test_get_conversation_history_with_limit(self, mock_get_db):
        """测试获取对话历史时使用limit参数"""
        # 使用测试模式的 MultiTurnHandler
        test_handler = MultiTurnHandler(test_mode=True)
        
        # 添加5条消息
        for i in range(5):
            msg_data = {
                "role": "user" if i % 2 == 0 else "assistant",
                "content": f"消息 {i+1}",
                "parent_message_id": None
            }
            test_handler.add_message(TEST_SESSION_ID, msg_data)
        
        # 获取前3条消息
        history = test_handler.get_conversation_history(TEST_SESSION_ID, limit=3)
        
        # 验证只返回3条消息
        assert len(history) == 3
        # 确保按时间顺序返回（最早的消息在前）
        assert history[0]["content"] == "消息 1"
        assert history[1]["content"] == "消息 2"
        assert history[2]["content"] == "消息 3"
        
    @patch('services.multi_turn_handler.get_db')
    def test_handle_user_input(self, mock_get_db):
        """测试处理用户输入"""
        # Mock get_db_session返回测试数据库会话
        mock_get_db.side_effect = lambda: iter([self.test_db])
        
        # 处理用户输入
        result = self.multi_turn_handler.handle_user_input(TEST_SESSION_ID, TEST_USER_MESSAGE)
        
        # 验证结果
        assert "user_message" in result
        assert "assistant_message" in result
        assert "conversation_history" in result
        
        # 验证用户消息
        user_msg = result["user_message"]
        assert user_msg["role"] == "user"
        assert user_msg["content"] == TEST_USER_MESSAGE
        assert user_msg["parent_message_id"] is None
        
        # 验证助手消息
        assistant_msg = result["assistant_message"]
        assert assistant_msg["role"] == "assistant"
        assert assistant_msg["content"] == "我理解了您的查询，正在为您分析数据..."
        assert assistant_msg["parent_message_id"] == user_msg["id"]
        
        # 验证对话历史包含两条消息
        history = result["conversation_history"]
        assert len(history) == 2
        assert history[0]["role"] == "user"
        assert history[0]["content"] == TEST_USER_MESSAGE
        assert history[1]["role"] == "assistant"
        assert history[1]["content"] == "我理解了您的查询，正在为您分析数据..."
        
    @patch('services.multi_turn_handler.get_db')
    def test_get_last_message(self, mock_get_db):
        """测试获取最后一条消息"""
        # Mock get_db_session返回测试数据库会话
        mock_get_db.side_effect = lambda: iter([self.test_db])
        
        # 添加多条消息
        messages_data = [
            {"role": "user", "content": "第一条消息", "parent_message_id": None},
            {"role": "assistant", "content": "第二条消息", "parent_message_id": None},
            {"role": "user", "content": "第三条消息", "parent_message_id": None}
        ]
        
        for msg_data in messages_data:
            self.multi_turn_handler.add_message(TEST_SESSION_ID, msg_data)
        
        # 获取最后一条消息
        last_message = self.multi_turn_handler.get_last_message(TEST_SESSION_ID)
        
        # 验证最后一条消息是第三条消息
        assert last_message["role"] == "user"
        assert last_message["content"] == "第三条消息"
        assert last_message["turn"] == 3
        
    @patch('services.multi_turn_handler.get_db')
    def test_get_last_message_empty_session(self, mock_get_db):
        """测试在空会话中获取最后一条消息"""
        # Mock get_db_session返回测试数据库会话
        mock_get_db.return_value = iter([self.test_db])
        
        # 获取最后一条消息（会话为空）
        last_message = self.multi_turn_handler.get_last_message(TEST_SESSION_ID)
        
        # 验证返回None
        assert last_message is None
        
    @patch('services.multi_turn_handler.get_db')
    def test_get_messages_by_parent(self, mock_get_db):
        """测试获取指定父消息的子消息"""
        # Mock get_db_session返回测试数据库会话
        mock_get_db.side_effect = lambda: iter([self.test_db])
        
        # 添加父消息
        parent_msg_data = {
            "role": "user",
            "content": "父消息",
            "parent_message_id": None
        }
        parent_result = self.multi_turn_handler.add_message(TEST_SESSION_ID, parent_msg_data)
        
        # 添加子消息
        child_msg_data_1 = {
            "role": "assistant",
            "content": "子消息1",
            "parent_message_id": parent_result["id"]
        }
        child_msg_data_2 = {
            "role": "assistant",
            "content": "子消息2",
            "parent_message_id": parent_result["id"]
        }
        
        child1_result = self.multi_turn_handler.add_message(TEST_SESSION_ID, child_msg_data_1)
        child2_result = self.multi_turn_handler.add_message(TEST_SESSION_ID, child_msg_data_2)
        
        # 获取子消息
        child_messages = self.multi_turn_handler.get_messages_by_parent(TEST_SESSION_ID, parent_result["id"])
        
        # 验证返回两个子消息
        assert len(child_messages) == 2
        assert child_messages[0]["content"] == "子消息1"
        assert child_messages[1]["content"] == "子消息2"
        assert child_messages[0]["parent_message_id"] == parent_result["id"]
        assert child_messages[1]["parent_message_id"] == parent_result["id"]
        
    @patch('services.multi_turn_handler.get_db')
    def test_get_messages_by_parent_no_children(self, mock_get_db):
        """测试获取没有子消息的父消息"""
        # Mock get_db_session返回测试数据库会话
        mock_get_db.side_effect = lambda: iter([self.test_db])
        
        # 添加父消息
        parent_msg_data = {
            "role": "user",
            "content": "父消息",
            "parent_message_id": None
        }
        parent_result = self.multi_turn_handler.add_message(TEST_SESSION_ID, parent_msg_data)
        
        # 获取子消息（应该为空）
        child_messages = self.multi_turn_handler.get_messages_by_parent(TEST_SESSION_ID, parent_result["id"])
        
        # 验证返回空列表
        assert len(child_messages) == 0
        
    @patch('services.multi_turn_handler.get_db')
    def test_add_message_error_handling(self, mock_get_db):
        """测试添加消息时的错误处理"""
        # 使用一个无效的数据库会话来触发错误
        with patch('services.multi_turn_handler.get_db') as mock_get_db:
            mock_get_db.side_effect = Exception("Database connection error")
            
            # 尝试添加消息
            message_data = {
                "role": "user",
                "content": "测试消息",
                "parent_message_id": None
            }
            
            # 验证会抛出异常
            with pytest.raises(Exception):
                self.multi_turn_handler.add_message(TEST_SESSION_ID, message_data)
        
    @patch('services.multi_turn_handler.get_db')
    def test_get_conversation_history_error_handling(self, mock_get_db):
        """测试获取对话历史时的错误处理"""
        # 使用一个无效的数据库会话来触发错误
        with patch('services.multi_turn_handler.get_db') as mock_get_db:
            mock_get_db.side_effect = Exception("Database connection error")
            
            # 尝试获取对话历史
            with pytest.raises(Exception):
                self.multi_turn_handler.get_conversation_history(TEST_SESSION_ID)
        
    @patch('services.multi_turn_handler.get_db')
    def test_handle_user_input_error_handling(self, mock_get_db):
        """测试处理用户输入时的错误处理"""
        # 使用一个无效的数据库会话来触发错误
        with patch('services.multi_turn_handler.get_db') as mock_get_db:
            mock_get_db.side_effect = Exception("Database connection error")
            
            # 尝试处理用户输入
            with pytest.raises(Exception):
                self.multi_turn_handler.handle_user_input(TEST_SESSION_ID, "测试消息")