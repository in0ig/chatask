"""
测试历史对话持久化功能
验证 Task 16: 实现历史对话持久化
"""

import pytest
import asyncio
from datetime import datetime
from sqlalchemy.orm import Session

from src.services.context_manager import ContextManager, MessageType
from src.services.session_service import SessionService
from src.models.dialogue_session_model import DialogueSession, SessionStatus


class TestHistoryPersistence:
    """测试历史对话持久化"""
    
    @pytest.fixture
    def context_manager(self):
        """创建 ContextManager 实例"""
        return ContextManager()
    
    @pytest.fixture
    def session_service(self):
        """创建 SessionService 实例"""
        return SessionService()
    
    @pytest.fixture
    def test_session_id(self):
        """测试会话ID"""
        return f"test_session_{datetime.now().timestamp()}"
    
    @pytest.mark.asyncio
    async def test_persist_context_manager_history(
        self, 
        context_manager: ContextManager,
        session_service: SessionService,
        test_session_id: str,
        db: Session
    ):
        """
        测试持久化 ContextManager 历史对话到数据库
        
        验收标准:
        - 能够将 ContextManager 的云端消息持久化到数据库
        - 能够将 ContextManager 的本地消息持久化到数据库
        - 持久化后能够正确保存 Token 统计信息
        """
        # 1. 创建会话并添加消息
        context_manager.create_session(test_session_id)
        
        # 添加用户消息
        context_manager.add_user_message(test_session_id, "查询2024年销售数据")
        
        # 添加 SQL 响应
        sql_content = "SELECT * FROM sales WHERE year = 2024"
        query_result = {
            "columns": ["id", "product", "amount"],
            "data": [
                {"id": 1, "product": "产品A", "amount": 1000},
                {"id": 2, "product": "产品B", "amount": 2000}
            ],
            "total_rows": 2
        }
        context_manager.add_sql_response(test_session_id, sql_content, query_result)
        
        # 添加分析响应
        analysis_content = "根据查询结果，2024年共有2条销售记录"
        analysis_data = {"summary": "销售数据分析"}
        context_manager.add_analysis_response(test_session_id, analysis_content, analysis_data)
        
        # 2. 设置数据库会话并持久化
        context_manager.set_db_session(db)
        success = await context_manager.persist_session_to_db(test_session_id)
        
        assert success, "持久化应该成功"
        
        # 3. 验证数据库中的数据
        session = db.query(DialogueSession).filter(
            DialogueSession.session_id == test_session_id
        ).first()
        
        assert session is not None, "会话应该存在于数据库中"
        assert session.cloud_messages is not None, "云端消息应该被保存"
        assert session.local_messages is not None, "本地消息应该被保存"
        assert len(session.cloud_messages) == 3, "应该有3条云端消息（用户+SQL+分析）"
        assert len(session.local_messages) == 3, "应该有3条本地消息"
        assert session.total_tokens > 0, "Token 统计应该大于0"
        
        # 4. 清理测试数据
        db.delete(session)
        db.commit()
    
    @pytest.mark.asyncio
    async def test_load_context_manager_history(
        self,
        context_manager: ContextManager,
        session_service: SessionService,
        test_session_id: str,
        db: Session
    ):
        """
        测试从数据库加载历史对话到 ContextManager
        
        验收标准:
        - 能够从数据库加载云端消息
        - 能够从数据库加载本地消息
        - 加载后的消息内容正确
        - 加载后的 Token 统计正确
        """
        # 1. 先创建并持久化一个会话
        context_manager.create_session(test_session_id)
        context_manager.add_user_message(test_session_id, "测试消息")
        context_manager.add_sql_response(test_session_id, "SELECT 1", {"data": []})
        
        context_manager.set_db_session(db)
        await context_manager.persist_session_to_db(test_session_id)
        
        # 2. 清空内存中的会话
        context_manager.sessions.clear()
        
        # 3. 从数据库加载会话
        loaded_session = await context_manager.load_session_from_db(test_session_id)
        
        assert loaded_session is not None, "应该能够加载会话"
        assert loaded_session.session_id == test_session_id, "会话ID应该匹配"
        assert len(loaded_session.cloud_messages) == 2, "应该有2条云端消息"
        assert len(loaded_session.local_messages) == 2, "应该有2条本地消息"
        
        # 验证消息内容
        user_msg = loaded_session.cloud_messages[0]
        assert user_msg.message_type == MessageType.USER_QUESTION, "第一条应该是用户消息"
        assert user_msg.content == "测试消息", "消息内容应该匹配"
        
        sql_msg = loaded_session.cloud_messages[1]
        assert sql_msg.message_type == MessageType.ASSISTANT_SQL, "第二条应该是SQL消息"
        assert "SELECT 1" in sql_msg.content, "SQL内容应该匹配"
        
        # 4. 清理测试数据
        session = db.query(DialogueSession).filter(
            DialogueSession.session_id == test_session_id
        ).first()
        if session:
            db.delete(session)
            db.commit()
    
    @pytest.mark.asyncio
    async def test_session_service_persist_and_load(
        self,
        session_service: SessionService,
        test_session_id: str,
        db: Session
    ):
        """
        测试 SessionService 的持久化和加载方法
        
        验收标准:
        - persist_context_manager_history 能够正确保存消息
        - load_context_manager_history 能够正确加载消息
        - 加载的数据格式正确
        """
        # 1. 准备测试数据
        cloud_messages = [
            {
                "message_id": "msg1",
                "session_id": test_session_id,
                "timestamp": datetime.now().isoformat(),
                "message_type": "user_question",
                "content": "测试问题",
                "metadata": {},
                "token_count": 10
            },
            {
                "message_id": "msg2",
                "session_id": test_session_id,
                "timestamp": datetime.now().isoformat(),
                "message_type": "assistant_sql",
                "content": "SELECT * FROM test",
                "metadata": {"row_count": 5},
                "token_count": 15
            }
        ]
        
        local_messages = [
            {
                "message_id": "msg1",
                "session_id": test_session_id,
                "timestamp": datetime.now().isoformat(),
                "message_type": "user_question",
                "content": "测试问题",
                "metadata": {},
                "query_result": None,
                "analysis_data": None,
                "token_count": 10
            },
            {
                "message_id": "msg2",
                "session_id": test_session_id,
                "timestamp": datetime.now().isoformat(),
                "message_type": "assistant_sql",
                "content": "SELECT * FROM test",
                "metadata": {"row_count": 5},
                "query_result": {"data": [{"id": 1}]},
                "analysis_data": None,
                "token_count": 15
            }
        ]
        
        total_tokens = 25
        
        # 2. 持久化
        success = await session_service.persist_context_manager_history(
            db, test_session_id, cloud_messages, local_messages, total_tokens
        )
        
        assert success, "持久化应该成功"
        
        # 3. 加载
        history_data = await session_service.load_context_manager_history(db, test_session_id)
        
        assert history_data is not None, "应该能够加载历史数据"
        assert history_data["session_id"] == test_session_id, "会话ID应该匹配"
        assert len(history_data["cloud_messages"]) == 2, "应该有2条云端消息"
        assert len(history_data["local_messages"]) == 2, "应该有2条本地消息"
        assert history_data["total_tokens"] == total_tokens, "Token统计应该匹配"
        
        # 4. 清理测试数据
        session = db.query(DialogueSession).filter(
            DialogueSession.session_id == test_session_id
        ).first()
        if session:
            db.delete(session)
            db.commit()
    
    @pytest.mark.asyncio
    async def test_get_session_history_for_display(
        self,
        session_service: SessionService,
        test_session_id: str,
        db: Session
    ):
        """
        测试获取会话历史用于前端展示
        
        验收标准:
        - 能够获取云端消息列表
        - 能够获取本地消息列表
        - 返回的消息格式正确
        """
        # 1. 先创建并持久化一个会话
        cloud_messages = [
            {
                "message_id": "msg1",
                "session_id": test_session_id,
                "timestamp": datetime.now().isoformat(),
                "message_type": "user_question",
                "content": "展示测试",
                "metadata": {},
                "token_count": 5
            }
        ]
        
        local_messages = [
            {
                "message_id": "msg1",
                "session_id": test_session_id,
                "timestamp": datetime.now().isoformat(),
                "message_type": "user_question",
                "content": "展示测试",
                "metadata": {},
                "query_result": None,
                "analysis_data": None,
                "token_count": 5
            }
        ]
        
        await session_service.persist_context_manager_history(
            db, test_session_id, cloud_messages, local_messages, 5
        )
        
        # 2. 获取云端消息
        cloud_history = await session_service.get_session_history_for_display(
            db, test_session_id, "cloud"
        )
        
        assert len(cloud_history) == 1, "应该有1条云端消息"
        assert cloud_history[0]["content"] == "展示测试", "消息内容应该匹配"
        
        # 3. 获取本地消息
        local_history = await session_service.get_session_history_for_display(
            db, test_session_id, "local"
        )
        
        assert len(local_history) == 1, "应该有1条本地消息"
        assert local_history[0]["content"] == "展示测试", "消息内容应该匹配"
        
        # 4. 清理测试数据
        session = db.query(DialogueSession).filter(
            DialogueSession.session_id == test_session_id
        ).first()
        if session:
            db.delete(session)
            db.commit()
    
    @pytest.mark.asyncio
    async def test_persistence_with_large_history(
        self,
        context_manager: ContextManager,
        test_session_id: str,
        db: Session
    ):
        """
        测试大量历史消息的持久化
        
        验收标准:
        - 能够持久化大量消息（100条）
        - 持久化后能够正确加载
        - 性能可接受（< 5秒）
        """
        import time
        
        # 1. 创建会话并添加大量消息
        context_manager.create_session(test_session_id)
        
        start_time = time.time()
        
        for i in range(50):
            context_manager.add_user_message(test_session_id, f"问题 {i}")
            context_manager.add_sql_response(
                test_session_id, 
                f"SELECT * FROM table_{i}",
                {"data": [{"id": i}]}
            )
        
        # 2. 持久化
        context_manager.set_db_session(db)
        success = await context_manager.persist_session_to_db(test_session_id)
        
        persist_time = time.time() - start_time
        
        assert success, "持久化应该成功"
        assert persist_time < 5.0, f"持久化时间应该小于5秒，实际: {persist_time:.2f}秒"
        
        # 3. 验证数据
        session = db.query(DialogueSession).filter(
            DialogueSession.session_id == test_session_id
        ).first()
        
        assert session is not None, "会话应该存在"
        assert len(session.cloud_messages) == 100, "应该有100条云端消息"
        assert len(session.local_messages) == 100, "应该有100条本地消息"
        
        # 4. 测试加载性能
        context_manager.sessions.clear()
        
        load_start = time.time()
        loaded_session = await context_manager.load_session_from_db(test_session_id)
        load_time = time.time() - load_start
        
        assert loaded_session is not None, "应该能够加载会话"
        assert load_time < 3.0, f"加载时间应该小于3秒，实际: {load_time:.2f}秒"
        assert len(loaded_session.cloud_messages) == 100, "加载的消息数量应该正确"
        
        # 5. 清理测试数据
        db.delete(session)
        db.commit()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
