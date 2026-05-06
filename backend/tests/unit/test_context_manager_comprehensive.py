"""
双层历史记录管理系统单元测试
测试基于Gemini语义影子模式的上下文管理器
"""

import pytest
import json
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
import sys
import pathlib

# Add src directory to Python path
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent.parent / "src"))

from services.context_manager import (
    ContextManager, DataSanitizer, ContextCompressor,
    CloudHistoryMessage, LocalHistoryMessage, SessionContext,
    MessageType, HistoryLevel, get_context_manager, init_context_manager
)


class TestDataSanitizer:
    """数据消毒器测试"""
    
    def setup_method(self):
        """设置测试环境"""
        self.sanitizer = DataSanitizer()
    
    def test_sanitize_for_cloud_basic(self):
        """测试基本数据消毒"""
        content = "用户ID是12345，销售额是1250.50元，日期是2024-01-15"
        result = self.sanitizer.sanitize_for_cloud(content)
        
        # 验证敏感数据被替换
        assert "12345" not in result
        assert "1250.50" not in result
        assert "2024-01-15" not in result
        assert "[COUNT]" in result or "[NUMBER]" in result or "[DATE]" in result
    
    def test_sanitize_for_cloud_email(self):
        """测试邮箱数据消毒"""
        content = "联系邮箱是user@example.com"
        result = self.sanitizer.sanitize_for_cloud(content)
        
        assert "user@example.com" not in result
        assert "[EMAIL]" in result
    
    def test_sanitize_for_cloud_strings(self):
        """测试字符串值消毒"""
        content = "产品名称是'iPhone 15'，描述是\"高端智能手机\""
        result = self.sanitizer.sanitize_for_cloud(content)
        
        assert "'iPhone 15'" not in result
        assert '"高端智能手机"' not in result
        assert "[VALUE]" in result
    
    def test_extract_sql_metadata(self):
        """测试SQL元数据提取"""
        query_result = {
            "columns": ["id", "name", "amount"],
            "data": [
                [1, "Product A", 100.50],
                [2, "Product B", 200.75]
            ],
            "status": "success",
            "execution_time": 0.15
        }
        
        metadata = self.sanitizer.extract_sql_metadata(query_result)
        
        assert metadata["columns"] == ["id", "name", "amount"]
        assert metadata["column_count"] == 3
        assert metadata["row_count"] == 2
        assert metadata["has_data"] is True
        assert metadata["query_status"] == "success"
        assert metadata["execution_time"] == 0.15
    
    def test_extract_sql_metadata_empty(self):
        """测试空查询结果的元数据提取"""
        metadata = self.sanitizer.extract_sql_metadata(None)
        assert metadata == {}
        
        empty_result = {"columns": [], "data": []}
        metadata = self.sanitizer.extract_sql_metadata(empty_result)
        assert metadata["column_count"] == 0
        assert metadata["row_count"] == 0
        assert metadata["has_data"] is False
    
    def test_create_cloud_summary_sql(self):
        """测试SQL消息的云端摘要创建"""
        sql_message = LocalHistoryMessage(
            message_id="test-1",
            session_id="session-1",
            timestamp=datetime.now(),
            message_type=MessageType.ASSISTANT_SQL,
            content="SELECT * FROM products WHERE price > 100",
            metadata={}
        )
        
        summary = self.sanitizer.create_cloud_summary(sql_message)
        assert summary == "SELECT * FROM products WHERE price > 100"
    
    def test_create_cloud_summary_analysis(self):
        """测试分析消息的云端摘要创建"""
        analysis_message = LocalHistoryMessage(
            message_id="test-2",
            session_id="session-1",
            timestamp=datetime.now(),
            message_type=MessageType.ASSISTANT_ANALYSIS,
            content="根据查询结果，产品A的销量是150件，产品B的销量是200件，总销量增长了25%",
            metadata={}
        )
        
        summary = self.sanitizer.create_cloud_summary(analysis_message)
        
        # 验证具体数值被替换
        assert "150" not in summary
        assert "200" not in summary
        assert "25%" not in summary
        assert "[COUNT]" in summary or "[NUMBER]" in summary
        assert "Analysis completed:" in summary


class TestContextCompressor:
    """上下文压缩器测试"""
    
    def setup_method(self):
        """设置测试环境"""
        self.compressor = ContextCompressor(max_tokens=1000)
    
    def test_estimate_tokens(self):
        """测试Token估算"""
        text = "这是一个测试文本"
        tokens = self.compressor.estimate_tokens(text)
        assert tokens > 0
        assert tokens == len(text) // 4
    
    def test_compress_context_under_limit(self):
        """测试Token数量在限制内的压缩"""
        messages = [
            CloudHistoryMessage(
                message_id="1",
                session_id="session-1",
                timestamp=datetime.now(),
                message_type=MessageType.USER_QUESTION,
                content="简短问题",
                metadata={},
                token_count=10
            )
        ]
        
        result = self.compressor.compress_context(messages)
        assert "简短问题" in result
        assert "[Compressed context" not in result
    
    def test_compress_context_over_limit(self):
        """测试Token数量超过限制的压缩"""
        # 创建大量消息超过Token限制
        messages = []
        for i in range(20):
            msg = CloudHistoryMessage(
                message_id=f"msg-{i}",
                session_id="session-1",
                timestamp=datetime.now() + timedelta(minutes=i),
                message_type=MessageType.USER_QUESTION,
                content=f"这是第{i}个问题，内容比较长，用来测试Token压缩功能" * 10,
                metadata={},
                token_count=200  # 每个消息200 tokens
            )
            messages.append(msg)
        
        result = self.compressor.compress_context(messages)
        assert "[Compressed context" in result
    
    def test_select_important_messages(self):
        """测试重要消息选择"""
        messages = [
            CloudHistoryMessage(
                message_id="1",
                session_id="session-1",
                timestamp=datetime.now() - timedelta(minutes=10),
                message_type=MessageType.USER_QUESTION,
                content="旧问题",
                metadata={},
                token_count=50
            ),
            CloudHistoryMessage(
                message_id="2",
                session_id="session-1",
                timestamp=datetime.now() - timedelta(minutes=5),
                message_type=MessageType.ASSISTANT_SQL,
                content="SELECT * FROM table",
                metadata={},
                token_count=30
            ),
            CloudHistoryMessage(
                message_id="3",
                session_id="session-1",
                timestamp=datetime.now(),
                message_type=MessageType.ERROR,
                content="错误信息",
                metadata={},
                token_count=20
            )
        ]
        
        selected = self.compressor._select_important_messages(messages, 80)
        
        # 应该选择SQL消息和错误消息（更重要）
        assert len(selected) >= 2
        message_types = [msg.message_type for msg in selected]
        assert MessageType.ASSISTANT_SQL in message_types
        assert MessageType.ERROR in message_types


class TestCloudHistoryMessage:
    """云端历史消息测试"""
    
    def test_to_dict(self):
        """测试转换为字典"""
        now = datetime.now()
        message = CloudHistoryMessage(
            message_id="test-1",
            session_id="session-1",
            timestamp=now,
            message_type=MessageType.USER_QUESTION,
            content="测试问题",
            metadata={"key": "value"},
            token_count=10
        )
        
        result = message.to_dict()
        
        assert result["message_id"] == "test-1"
        assert result["session_id"] == "session-1"
        assert result["timestamp"] == now.isoformat()
        assert result["message_type"] == "user_question"
        assert result["content"] == "测试问题"
        assert result["metadata"] == {"key": "value"}
        assert result["token_count"] == 10


class TestLocalHistoryMessage:
    """本地历史消息测试"""
    
    def test_to_dict_with_query_result(self):
        """测试包含查询结果的转换"""
        now = datetime.now()
        query_result = {
            "columns": ["id", "name"],
            "data": [[1, "test"]]
        }
        
        message = LocalHistoryMessage(
            message_id="test-1",
            session_id="session-1",
            timestamp=now,
            message_type=MessageType.ASSISTANT_SQL,
            content="SELECT * FROM test",
            metadata={},
            query_result=query_result,
            token_count=15
        )
        
        result = message.to_dict()
        
        assert result["query_result"] == query_result
        assert result["analysis_data"] is None


class TestContextManager:
    """上下文管理器测试"""
    
    def setup_method(self):
        """设置测试环境"""
        self.manager = ContextManager(max_sessions=10, session_timeout_hours=1)
    
    def test_create_session(self):
        """测试创建会话"""
        session_id = "test-session-1"
        session = self.manager.create_session(session_id)
        
        assert session.session_id == session_id
        assert len(session.cloud_messages) == 0
        assert len(session.local_messages) == 0
        assert session.total_tokens == 0
        assert session_id in self.manager.sessions
    
    def test_get_session_existing(self):
        """测试获取存在的会话"""
        session_id = "test-session-2"
        created_session = self.manager.create_session(session_id)
        
        retrieved_session = self.manager.get_session(session_id)
        
        assert retrieved_session is not None
        assert retrieved_session.session_id == session_id
        # 验证last_activity被更新
        assert retrieved_session.last_activity >= created_session.last_activity
    
    def test_get_session_nonexistent(self):
        """测试获取不存在的会话"""
        result = self.manager.get_session("nonexistent-session")
        assert result is None
    
    def test_add_user_message(self):
        """测试添加用户消息"""
        session_id = "test-session-3"
        content = "用户问题测试"
        
        message_id = self.manager.add_user_message(session_id, content)
        
        assert message_id is not None
        session = self.manager.get_session(session_id)
        assert len(session.cloud_messages) == 1
        assert len(session.local_messages) == 1
        
        # 验证云端和本地消息内容相同
        cloud_msg = session.cloud_messages[0]
        local_msg = session.local_messages[0]
        
        assert cloud_msg.content == content
        assert local_msg.content == content
        assert cloud_msg.message_type == MessageType.USER_QUESTION
        assert local_msg.message_type == MessageType.USER_QUESTION
    
    def test_add_sql_response(self):
        """测试添加SQL响应"""
        session_id = "test-session-4"
        sql_content = "SELECT * FROM products WHERE price > 100"
        query_result = {
            "columns": ["id", "name", "price"],
            "data": [[1, "Product A", 150.0], [2, "Product B", 200.0]],
            "status": "success"
        }
        
        message_id = self.manager.add_sql_response(session_id, sql_content, query_result)
        
        assert message_id is not None
        session = self.manager.get_session(session_id)
        assert len(session.cloud_messages) == 1
        assert len(session.local_messages) == 1
        
        cloud_msg = session.cloud_messages[0]
        local_msg = session.local_messages[0]
        
        # 验证云端消息被消毒（数字被替换）
        assert "100" not in cloud_msg.content  # 数字应该被替换
        assert "SELECT * FROM products WHERE price >" in cloud_msg.content
        assert "columns" in cloud_msg.metadata
        assert "row_count" in cloud_msg.metadata
        
        # 验证本地消息包含完整查询结果
        assert local_msg.content == sql_content
        assert local_msg.query_result == query_result
    
    def test_add_analysis_response(self):
        """测试添加分析响应"""
        session_id = "test-session-5"
        analysis_content = "根据查询结果，产品A的价格是150元，产品B的价格是200元"
        analysis_data = {"insights": ["价格差异", "产品对比"]}
        
        message_id = self.manager.add_analysis_response(session_id, analysis_content, analysis_data)
        
        assert message_id is not None
        session = self.manager.get_session(session_id)
        
        cloud_msg = session.cloud_messages[0]
        local_msg = session.local_messages[0]
        
        # 验证云端消息是消毒后的摘要
        assert "150" not in cloud_msg.content
        assert "200" not in cloud_msg.content
        assert "Analysis completed:" in cloud_msg.content
        
        # 验证本地消息包含完整分析数据
        assert local_msg.content == analysis_content
        assert local_msg.analysis_data == analysis_data
    
    def test_get_cloud_history(self):
        """测试获取云端历史记录"""
        session_id = "test-session-6"
        
        # 添加一些消息
        self.manager.add_user_message(session_id, "用户问题1")
        self.manager.add_sql_response(session_id, "SELECT * FROM table1")
        self.manager.add_user_message(session_id, "用户问题2")
        
        history = self.manager.get_cloud_history(session_id)
        
        assert len(history) == 3
        assert history[0]["role"] == "user"
        assert history[0]["content"] == "用户问题1"
        assert history[1]["role"] == "assistant"
        assert history[1]["content"] == "SELECT * FROM table1"
        assert history[2]["role"] == "user"
        assert history[2]["content"] == "用户问题2"
    
    def test_get_local_history(self):
        """测试获取本地历史记录"""
        session_id = "test-session-7"
        
        # 添加消息
        self.manager.add_user_message(session_id, "用户问题")
        query_result = {"columns": ["id"], "data": [[1]]}
        self.manager.add_sql_response(session_id, "SELECT id FROM table", query_result)
        
        history = self.manager.get_local_history(session_id)
        
        assert len(history) == 2
        # 验证本地历史包含完整信息
        sql_message = next(msg for msg in history if msg["message_type"] == "assistant_sql")
        assert sql_message["query_result"] == query_result
    
    def test_get_previous_query_results(self):
        """测试获取历史查询结果"""
        session_id = "test-session-8"
        
        # 添加多个SQL响应
        result1 = {"columns": ["count"], "data": [[10]]}
        result2 = {"columns": ["sum"], "data": [[100]]}
        result3 = {"columns": ["avg"], "data": [[50]]}
        
        self.manager.add_sql_response(session_id, "SELECT COUNT(*) FROM table", result1)
        self.manager.add_sql_response(session_id, "SELECT SUM(amount) FROM table", result2)
        self.manager.add_sql_response(session_id, "SELECT AVG(amount) FROM table", result3)
        
        previous_results = self.manager.get_previous_query_results(session_id, count=2)
        
        assert len(previous_results) == 2
        # 应该返回最近的2个结果（按时间倒序）
        assert previous_results[0] == result2  # 倒数第二个
        assert previous_results[1] == result3  # 最后一个
    
    def test_compress_session_context(self):
        """测试会话上下文压缩"""
        session_id = "test-session-9"
        
        # 创建会话并添加消息
        self.manager.create_session(session_id)
        self.manager.add_user_message(session_id, "测试问题")
        
        result = self.manager.compress_session_context(session_id)
        
        assert result is True
        session = self.manager.get_session(session_id)
        assert session.compressed_context is not None
    
    def test_session_cleanup(self):
        """测试会话清理"""
        # 创建超过最大数量的会话
        manager = ContextManager(max_sessions=2, session_timeout_hours=1)
        
        manager.create_session("session-1")
        manager.create_session("session-2")
        manager.create_session("session-3")  # 这应该触发清理
        
        # 验证只保留了最大数量的会话
        assert len(manager.sessions) <= 2
    
    def test_get_session_stats(self):
        """测试获取会话统计信息"""
        session_id = "test-session-10"
        
        self.manager.add_user_message(session_id, "测试问题")
        self.manager.add_sql_response(session_id, "SELECT * FROM test")
        
        stats = self.manager.get_session_stats(session_id)
        
        assert stats["session_id"] == session_id
        assert stats["cloud_message_count"] == 2
        assert stats["local_message_count"] == 2
        assert stats["total_tokens"] > 0
        assert "created_at" in stats
        assert "last_activity" in stats
    
    def test_get_all_sessions_stats(self):
        """测试获取所有会话统计信息"""
        self.manager.create_session("session-a")
        self.manager.create_session("session-b")
        
        stats = self.manager.get_all_sessions_stats()
        
        assert stats["total_sessions"] == 2
        assert stats["max_sessions"] == 10
        assert stats["session_timeout_hours"] == 1
        assert len(stats["sessions"]) == 2
    
    def test_generate_message_id(self):
        """测试消息ID生成"""
        session_id = "test-session"
        content = "测试内容"
        
        id1 = self.manager._generate_message_id(session_id, content)
        # 添加微小延迟确保时间戳不同
        import time
        time.sleep(0.001)
        id2 = self.manager._generate_message_id(session_id, content)
        
        # 由于包含微秒级时间戳，两次生成的ID应该不同
        assert id1 != id2
        assert session_id in id1
        assert session_id in id2


class TestGlobalFunctions:
    """测试全局函数"""
    
    def test_get_context_manager(self):
        """测试获取上下文管理器实例"""
        manager1 = get_context_manager()
        manager2 = get_context_manager()
        
        # 应该返回同一个实例
        assert manager1 is manager2
    
    def test_init_context_manager(self):
        """测试初始化上下文管理器"""
        manager = init_context_manager(max_sessions=500, session_timeout_hours=12)
        
        assert manager.max_sessions == 500
        assert manager.session_timeout.total_seconds() == 12 * 3600
        
        # 验证全局实例被更新
        global_manager = get_context_manager()
        assert global_manager is manager


class TestDataSecurityAndPrivacy:
    """数据安全和隐私保护测试"""
    
    def setup_method(self):
        """设置测试环境"""
        self.manager = ContextManager()
        self.sanitizer = DataSanitizer()
    
    def test_cloud_history_no_business_data(self):
        """测试云端历史记录不包含业务数据"""
        session_id = "security-test-1"
        
        # 添加包含敏感数据的SQL响应
        sql_content = "SELECT customer_name, phone, email FROM customers WHERE id = 12345"
        query_result = {
            "columns": ["customer_name", "phone", "email"],
            "data": [["张三", "13800138000", "zhangsan@example.com"]],
            "status": "success"
        }
        
        self.manager.add_sql_response(session_id, sql_content, query_result)
        
        # 获取云端历史记录
        cloud_history = self.manager.get_cloud_history(session_id)
        
        # 验证云端历史不包含查询结果数据
        assert len(cloud_history) == 1
        cloud_message = cloud_history[0]
        
        # SQL语句本身应该保留（因为它是逻辑，不是数据）
        assert "SELECT customer_name, phone, email FROM customers" in cloud_message["content"]
        
        # 但是不应该包含实际的查询结果数据
        cloud_message_str = str(cloud_message)
        assert "张三" not in cloud_message_str
        assert "13800138000" not in cloud_message_str
        assert "zhangsan@example.com" not in cloud_message_str
    
    def test_local_history_contains_full_data(self):
        """测试本地历史记录包含完整数据"""
        session_id = "security-test-2"
        
        query_result = {
            "columns": ["product_name", "sales"],
            "data": [["iPhone 15", 1500], ["MacBook Pro", 800]]
        }
        
        self.manager.add_sql_response(session_id, "SELECT * FROM products", query_result)
        
        # 获取本地历史记录
        local_history = self.manager.get_local_history(session_id)
        
        # 验证本地历史包含完整数据
        assert len(local_history) == 1
        local_message = local_history[0]
        
        assert local_message["query_result"] == query_result
        assert "iPhone 15" in str(local_message["query_result"])
        assert 1500 in local_message["query_result"]["data"][0]
    
    def test_analysis_data_sanitization(self):
        """测试分析数据的消毒处理"""
        session_id = "security-test-3"
        
        # 添加包含具体数值的分析
        analysis_content = "根据分析，Q1销售额为2,500,000元，比去年同期增长15.5%，主要客户包括'腾讯'和'阿里巴巴'"
        analysis_data = {
            "q1_sales": 2500000,
            "growth_rate": 0.155,
            "top_customers": ["腾讯", "阿里巴巴"]
        }
        
        self.manager.add_analysis_response(session_id, analysis_content, analysis_data)
        
        # 获取云端历史
        cloud_history = self.manager.get_cloud_history(session_id)
        cloud_content = cloud_history[0]["content"]
        
        # 验证敏感数据被消毒
        assert "2,500,000" not in cloud_content
        assert "15.5%" not in cloud_content
        assert "'腾讯'" not in cloud_content
        assert "'阿里巴巴'" not in cloud_content
        
        # 获取本地历史
        local_history = self.manager.get_local_history(session_id)
        local_message = local_history[0]
        
        # 验证本地历史包含完整数据
        assert local_message["content"] == analysis_content
        assert local_message["analysis_data"] == analysis_data
    
    def test_previous_data_injection_security(self):
        """测试历史数据注入的安全性"""
        session_id = "security-test-4"
        
        # 添加多个查询结果
        result1 = {"columns": ["revenue"], "data": [[1000000]]}
        result2 = {"columns": ["profit"], "data": [[200000]]}
        
        self.manager.add_sql_response(session_id, "SELECT revenue FROM sales", result1)
        self.manager.add_sql_response(session_id, "SELECT profit FROM sales", result2)
        
        # 获取历史查询结果用于本地分析
        previous_results = self.manager.get_previous_query_results(session_id)
        
        # 验证历史数据只用于本地分析，不会发送到云端
        assert len(previous_results) == 2
        assert previous_results[0] == result1
        assert previous_results[1] == result2
        
        # 验证云端历史不包含这些数据值
        cloud_history = self.manager.get_cloud_history(session_id)
        cloud_history_str = str(cloud_history)
        assert "1000000" not in cloud_history_str
        assert "200000" not in cloud_history_str


if __name__ == "__main__":
    pytest.main([__file__, "-v"])