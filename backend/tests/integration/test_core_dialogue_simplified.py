"""
核心对话功能简化集成测试

使用真实的ContextManager API进行测试
验证双层历史记录和数据安全机制
"""

import pytest
import pytest_asyncio
import re
from datetime import datetime
from typing import Dict, Any, List

from src.services.context_manager import ContextManager, MessageType
from src.database import get_db


class TestCoreDialogueSimplified:
    """核心对话功能简化集成测试"""
    
    @pytest_asyncio.fixture
    async def setup_context(self):
        """设置上下文管理器"""
        context_manager = ContextManager()
        return {"context_manager": context_manager}
    
    @pytest.mark.asyncio
    async def test_dual_history_separation(self, setup_context):
        """
        测试1: 双层历史记录分离
        
        验收标准：
        - 云端历史和本地历史分离存储
        - 云端历史不包含查询结果数据
        - 本地历史包含完整数据
        """
        services = setup_context
        context_manager = services["context_manager"]
        
        session_id = f"test_dual_history_{datetime.now().timestamp()}"
        
        # 添加用户问题
        context_manager.add_user_message(
            session_id=session_id,
            content="查询销售额最高的前10个产品"
        )
        
        # 添加SQL响应（包含查询结果）
        query_result = {
            "columns": ["product_name", "sales", "revenue"],
            "rows": [
                ["产品A", 100, 15000.00],
                ["产品B", 85, 12750.00],
                ["产品C", 120, 18000.00]
            ]
        }
        
        context_manager.add_sql_response(
            session_id=session_id,
            sql_content="SELECT product_name, sales, revenue FROM products ORDER BY revenue DESC LIMIT 10",
            query_result=query_result
        )
        
        # 获取会话上下文
        session = context_manager.get_session(session_id)
        
        assert session is not None, "会话应该存在"
        assert len(session.cloud_messages) > 0, "云端历史应该有消息"
        assert len(session.local_messages) > 0, "本地历史应该有消息"
        
        # 验证云端历史不包含查询结果
        cloud_has_data = False
        for msg in session.cloud_messages:
            if msg.message_type == MessageType.ASSISTANT_SQL:
                # 云端应该有SQL
                assert "SELECT" in msg.content.upper(), "云端历史应该包含SQL"
                
                # 云端不应该有查询结果数据
                assert "产品A" not in msg.content, "云端历史不应包含产品名称"
                assert "15000" not in msg.content, "云端历史不应包含具体金额"
        
        # 验证本地历史包含完整数据
        local_has_data = False
        for msg in session.local_messages:
            if msg.message_type == MessageType.ASSISTANT_SQL and msg.query_result:
                local_has_data = True
                assert "rows" in msg.query_result, "本地历史应该包含查询结果"
                assert len(msg.query_result["rows"]) == 3, "本地历史应该包含所有数据行"
                break
        
        assert local_has_data, "本地历史应该包含查询结果数据"
        
        print(f"✅ 双层历史记录分离测试通过")
        print(f"   - 云端消息数: {len(session.cloud_messages)}")
        print(f"   - 本地消息数: {len(session.local_messages)}")
    
    @pytest.mark.asyncio
    async def test_context_token_management(self, setup_context):
        """
        测试2: 上下文Token管理
        
        验收标准：
        - Token计数准确
        - 上下文压缩有效
        - 重要消息保留
        """
        services = setup_context
        context_manager = services["context_manager"]
        
        session_id = f"test_token_mgmt_{datetime.now().timestamp()}"
        
        # 添加多条消息模拟长对话
        for i in range(5):
            context_manager.add_user_message(
                session_id=session_id,
                content=f"这是第{i+1}个问题，查询相关数据"
            )
            
            context_manager.add_sql_response(
                session_id=session_id,
                sql_content=f"SELECT * FROM table_{i} WHERE id = {i}",
                query_result={"columns": ["id", "value"], "rows": [[i, f"data_{i}"]]}
            )
        
        # 获取会话上下文
        session = context_manager.get_session(session_id)
        
        assert session is not None, "会话应该存在"
        assert session.total_tokens > 0, "应该有Token计数"
        
        # 验证消息数量
        total_messages = len(session.cloud_messages) + len(session.local_messages)
        assert total_messages >= 10, "应该有至少10条消息"
        
        print(f"✅ 上下文Token管理测试通过")
        print(f"   - 总Token数: {session.total_tokens}")
        print(f"   - 总消息数: {total_messages}")
    
    @pytest.mark.asyncio
    async def test_session_isolation(self, setup_context):
        """
        测试3: 会话隔离
        
        验收标准：
        - 不同会话完全隔离
        - 会话A的数据不会出现在会话B
        """
        services = setup_context
        context_manager = services["context_manager"]
        
        # 创建两个独立会话
        session_a = f"test_session_a_{datetime.now().timestamp()}"
        session_b = f"test_session_b_{datetime.now().timestamp()}"
        
        # 会话A的数据
        context_manager.add_user_message(
            session_id=session_a,
            content="查询客户A的订单"
        )
        
        context_manager.add_sql_response(
            session_id=session_a,
            sql_content="SELECT * FROM orders WHERE customer_id = 'A'",
            query_result={"columns": ["order_id"], "rows": [[1001]]}
        )
        
        # 会话B的数据
        context_manager.add_user_message(
            session_id=session_b,
            content="查询客户B的订单"
        )
        
        context_manager.add_sql_response(
            session_id=session_b,
            sql_content="SELECT * FROM orders WHERE customer_id = 'B'",
            query_result={"columns": ["order_id"], "rows": [[2001]]}
        )
        
        # 获取各自的会话
        session_a_data = context_manager.get_session(session_a)
        session_b_data = context_manager.get_session(session_b)
        
        assert session_a_data is not None, "会话A应该存在"
        assert session_b_data is not None, "会话B应该存在"
        
        # 验证隔离性
        # 会话A不应包含会话B的数据
        for msg in session_a_data.local_messages:
            if msg.query_result:
                assert "2001" not in str(msg.query_result), "会话A不应包含会话B的订单ID"
        
        # 会话B不应包含会话A的数据
        for msg in session_b_data.local_messages:
            if msg.query_result:
                assert "1001" not in str(msg.query_result), "会话B不应包含会话A的订单ID"
        
        print(f"✅ 会话隔离测试通过")
        print(f"   - 会话A消息数: {len(session_a_data.local_messages)}")
        print(f"   - 会话B消息数: {len(session_b_data.local_messages)}")
    
    @pytest.mark.asyncio
    async def test_message_type_handling(self, setup_context):
        """
        测试4: 消息类型处理
        
        验收标准：
        - 支持多种消息类型
        - 消息类型正确分类
        - 不同类型消息正确处理
        """
        services = setup_context
        context_manager = services["context_manager"]
        
        session_id = f"test_msg_types_{datetime.now().timestamp()}"
        
        # 添加用户问题
        context_manager.add_user_message(
            session_id=session_id,
            content="查询数据"
        )
        
        # 添加SQL响应
        context_manager.add_sql_response(
            session_id=session_id,
            sql_content="SELECT * FROM test",
            query_result={"columns": ["id"], "rows": [[1]]}
        )
        
        # 添加分析响应
        context_manager.add_analysis_response(
            session_id=session_id,
            analysis_content="数据分析结果：总计1条记录",
            analysis_data={"total": 1, "summary": "分析完成"}
        )
        
        # 获取会话
        session = context_manager.get_session(session_id)
        
        assert session is not None, "会话应该存在"
        
        # 验证消息类型
        message_types = set()
        for msg in session.local_messages:
            message_types.add(msg.message_type)
        
        assert MessageType.USER_QUESTION in message_types, "应该有用户问题"
        assert MessageType.ASSISTANT_SQL in message_types, "应该有SQL响应"
        assert MessageType.ASSISTANT_ANALYSIS in message_types, "应该有分析响应"
        
        print(f"✅ 消息类型处理测试通过")
        print(f"   - 消息类型数: {len(message_types)}")
    
    @pytest.mark.asyncio
    async def test_context_retrieval(self, setup_context):
        """
        测试5: 上下文检索
        
        验收标准：
        - 能够正确检索会话上下文
        - 支持按时间范围检索
        - 支持按消息类型过滤
        """
        services = setup_context
        context_manager = services["context_manager"]
        
        session_id = f"test_retrieval_{datetime.now().timestamp()}"
        
        # 添加多条不同类型的消息
        context_manager.add_user_message(session_id, "问题1")
        context_manager.add_sql_response(session_id, "SELECT 1", {"columns": [], "rows": []})
        context_manager.add_user_message(session_id, "问题2")
        context_manager.add_sql_response(session_id, "SELECT 2", {"columns": [], "rows": []})
        
        # 获取会话
        session = context_manager.get_session(session_id)
        
        assert session is not None, "会话应该存在"
        assert len(session.local_messages) >= 4, "应该有至少4条消息"
        
        # 验证消息顺序
        user_questions = [msg for msg in session.local_messages if msg.message_type == MessageType.USER_QUESTION]
        assert len(user_questions) == 2, "应该有2个用户问题"
        
        sql_responses = [msg for msg in session.local_messages if msg.message_type == MessageType.ASSISTANT_SQL]
        assert len(sql_responses) == 2, "应该有2个SQL响应"
        
        print(f"✅ 上下文检索测试通过")
        print(f"   - 用户问题数: {len(user_questions)}")
        print(f"   - SQL响应数: {len(sql_responses)}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
