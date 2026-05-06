"""
数据安全和隐私保护集成测试

专注于验证数据安全边界和隐私保护机制
验收标准：
- 云端模型零业务数据接触率 = 100%
- 本地数据处理覆盖率 = 100%
- 数据传输加密率 = 100%
- 敏感数据泄露事件 = 0
"""

import pytest
import pytest_asyncio
import asyncio
import re
from datetime import datetime
from typing import Dict, Any, List

from src.services.context_manager import ContextManager, DataSanitizer
from src.services.chat_orchestrator import ChatOrchestrator
from src.services.dialogue_manager import DialogueManager
from src.database import get_db


class TestDataPrivacySecurity:
    """数据安全和隐私保护集成测试"""
    
    @pytest_asyncio.fixture
    async def setup_privacy_test(self):
        """设置隐私测试环境"""
        db = next(get_db())
        context_manager = ContextManager()
        dialogue_manager = DialogueManager(db)
        
        return {
            "context_manager": context_manager,
            "dialogue_manager": dialogue_manager,
            "sanitizer": DataSanitizer(),
            "db": db
        }
    
    @pytest.mark.asyncio
    async def test_cloud_model_zero_data_exposure(self, setup_privacy_test):
        """
        测试1: 云端模型零业务数据暴露
        
        验收标准：
        - 云端历史记录不包含任何实际数据值
        - 仅包含SQL语句和状态描述
        - 敏感信息完全过滤
        """
        services = setup_privacy_test
        context_manager = services["context_manager"]
        
        session_id = f"test_zero_exposure_{datetime.now().timestamp()}"
        
        # 模拟包含敏感数据的查询结果
        sensitive_data = {
            "columns": ["customer_name", "email", "phone", "order_amount"],
            "rows": [
                ["张三", "zhangsan@example.com", "13800138000", 1500.00],
                ["李四", "lisi@example.com", "13900139000", 2300.50],
                ["王五", "wangwu@example.com", "13700137000", 980.00]
            ]
        }
        
        # 添加到本地历史
        context_manager.add_local_message(
            session_id=session_id,
            role="assistant",
            content="查询完成",
            query_result=sensitive_data
        )
        
        # 获取云端历史
        cloud_history = context_manager.get_cloud_history(session_id)
        
        # 验证云端历史不包含敏感数据
        for message in cloud_history:
            content = str(message.get("content", ""))
            
            # 不应包含邮箱
            assert not re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', content), \
                "云端历史不应包含邮箱地址"
            
            # 不应包含电话号码
            assert not re.search(r'1[3-9]\d{9}', content), \
                "云端历史不应包含电话号码"
            
            # 不应包含具体姓名
            assert "张三" not in content and "李四" not in content and "王五" not in content, \
                "云端历史不应包含具体姓名"
            
            # 不应包含具体金额
            assert "1500" not in content and "2300" not in content and "980" not in content, \
                "云端历史不应包含具体金额"
        
        print(f"✅ 云端模型零业务数据暴露测试通过")
        print(f"   - 验证了邮箱、电话、姓名、金额等敏感信息均未泄露")
    
    @pytest.mark.asyncio
    async def test_data_sanitizer_effectiveness(self, setup_privacy_test):
        """
        测试2: 数据消毒器有效性
        
        验收标准：
        - 所有敏感数据类型都能被识别
        - 消毒后的数据保持结构但不含敏感值
        - 消毒过程可逆（用于本地分析）
        """
        services = setup_privacy_test
        sanitizer = services["sanitizer"]
        
        # 测试各种敏感数据类型
        test_cases = [
            {
                "name": "邮箱地址",
                "data": "用户邮箱是 user@example.com",
                "should_not_contain": ["user@example.com", "@example.com"]
            },
            {
                "name": "电话号码",
                "data": "联系电话：13800138000",
                "should_not_contain": ["13800138000"]
            },
            {
                "name": "日期时间",
                "data": "订单时间：2024-01-15 14:30:00",
                "should_not_contain": ["2024-01-15", "14:30:00"]
            },
            {
                "name": "数字金额",
                "data": "订单金额：1234.56元",
                "should_not_contain": ["1234.56"]
            },
            {
                "name": "身份证号",
                "data": "身份证：110101199001011234",
                "should_not_contain": ["110101199001011234"]
            }
        ]
        
        for test_case in test_cases:
            sanitized = sanitizer.sanitize_text(test_case["data"])
            
            # 验证敏感信息被移除
            for sensitive_value in test_case["should_not_contain"]:
                assert sensitive_value not in sanitized, \
                    f"{test_case['name']}应该被消毒: {sensitive_value}"
            
            # 验证消毒后仍保持可读性
            assert len(sanitized) > 0, "消毒后的文本不应为空"
            assert "[REDACTED" in sanitized or "***" in sanitized, \
                "消毒后应该有明显的标记"
            
            print(f"   ✓ {test_case['name']}消毒测试通过")
        
        print(f"✅ 数据消毒器有效性测试通过")
    
    @pytest.mark.asyncio
    async def test_local_history_completeness(self, setup_privacy_test):
        """
        测试3: 本地历史记录完整性
        
        验收标准：
        - 本地历史包含完整的查询结果
        - 包含所有数据值和元数据
        - 支持数据追问和分析
        """
        services = setup_privacy_test
        context_manager = services["context_manager"]
        
        session_id = f"test_local_complete_{datetime.now().timestamp()}"
        
        # 添加完整的查询结果到本地历史
        complete_result = {
            "columns": ["product_id", "product_name", "sales", "revenue"],
            "rows": [
                [1, "产品A", 100, 15000.00],
                [2, "产品B", 85, 12750.00],
                [3, "产品C", 120, 18000.00]
            ],
            "metadata": {
                "total_rows": 3,
                "execution_time": 0.5,
                "data_source": "MySQL"
            }
        }
        
        context_manager.add_local_message(
            session_id=session_id,
            role="assistant",
            content="查询完成",
            query_result=complete_result
        )
        
        # 获取本地历史
        local_history = context_manager.get_local_history(session_id)
        
        # 验证完整性
        assert len(local_history) > 0, "本地历史应该有记录"
        
        result_message = None
        for msg in local_history:
            if "query_result" in msg:
                result_message = msg
                break
        
        assert result_message is not None, "本地历史应该包含查询结果"
        
        query_result = result_message["query_result"]
        
        # 验证数据完整性
        assert "columns" in query_result, "应该包含列信息"
        assert "rows" in query_result, "应该包含行数据"
        assert len(query_result["rows"]) == 3, "应该包含所有数据行"
        
        # 验证数据值完整
        assert query_result["rows"][0][0] == 1, "应该包含完整的数据值"
        assert query_result["rows"][0][1] == "产品A", "应该包含完整的文本数据"
        assert query_result["rows"][0][3] == 15000.00, "应该包含完整的数值数据"
        
        # 验证元数据
        if "metadata" in query_result:
            assert "total_rows" in query_result["metadata"], "应该包含元数据"
        
        print(f"✅ 本地历史记录完整性测试通过")
        print(f"   - 验证了列信息、行数据、数据值、元数据的完整性")
    
    @pytest.mark.asyncio
    async def test_context_compression_safety(self, setup_privacy_test):
        """
        测试4: 上下文压缩安全性
        
        验收标准：
        - 压缩过程不泄露敏感数据
        - 压缩后的上下文仍然有用
        - Token管理有效
        """
        services = setup_privacy_test
        context_manager = services["context_manager"]
        
        session_id = f"test_compression_{datetime.now().timestamp()}"
        
        # 添加多条消息模拟长对话
        for i in range(10):
            context_manager.add_local_message(
                session_id=session_id,
                role="user",
                content=f"查询第{i+1}个问题，包含敏感数据：user{i}@example.com"
            )
            
            context_manager.add_local_message(
                session_id=session_id,
                role="assistant",
                content=f"回答第{i+1}个问题",
                query_result={
                    "columns": ["id", "value"],
                    "rows": [[i, f"data_{i}"]]
                }
            )
        
        # 获取压缩后的云端历史
        cloud_history = context_manager.get_cloud_history(session_id)
        
        # 验证压缩效果
        assert len(cloud_history) < 20, "云端历史应该被压缩"
        
        # 验证压缩后不包含敏感数据
        for message in cloud_history:
            content = str(message.get("content", ""))
            
            # 不应包含邮箱
            assert not re.search(r'user\d+@example\.com', content), \
                "压缩后的云端历史不应包含邮箱"
            
            # 不应包含具体数据值
            assert not re.search(r'data_\d+', content), \
                "压缩后的云端历史不应包含具体数据值"
        
        print(f"✅ 上下文压缩安全性测试通过")
        print(f"   - 原始消息数: 20, 压缩后: {len(cloud_history)}")
    
    @pytest.mark.asyncio
    async def test_sql_only_cloud_transmission(self, setup_privacy_test):
        """
        测试5: 仅SQL传输到云端
        
        验收标准：
        - 云端只接收SQL语句
        - 不接收查询结果
        - 不接收数据值
        """
        services = setup_privacy_test
        context_manager = services["context_manager"]
        
        session_id = f"test_sql_only_{datetime.now().timestamp()}"
        
        # 模拟SQL生成和执行
        generated_sql = "SELECT product_name, SUM(sales) FROM products GROUP BY product_name"
        
        # 添加SQL到云端历史
        context_manager.add_cloud_message(
            session_id=session_id,
            role="assistant",
            content=f"```sql\n{generated_sql}\n```"
        )
        
        # 添加查询结果到本地历史（不应出现在云端）
        query_result = {
            "columns": ["product_name", "total_sales"],
            "rows": [
                ["产品A", 1000],
                ["产品B", 1500],
                ["产品C", 800]
            ]
        }
        
        context_manager.add_local_message(
            session_id=session_id,
            role="system",
            content="查询执行成功",
            query_result=query_result
        )
        
        # 获取云端历史
        cloud_history = context_manager.get_cloud_history(session_id)
        
        # 验证云端历史
        sql_found = False
        for message in cloud_history:
            content = str(message.get("content", ""))
            
            # 应该包含SQL
            if "SELECT" in content.upper():
                sql_found = True
                assert generated_sql in content, "云端历史应该包含完整SQL"
            
            # 不应包含查询结果
            assert "产品A" not in content, "云端历史不应包含查询结果"
            assert "1000" not in content, "云端历史不应包含数据值"
            assert "1500" not in content, "云端历史不应包含数据值"
        
        assert sql_found, "云端历史应该包含SQL语句"
        
        print(f"✅ 仅SQL传输到云端测试通过")
    
    @pytest.mark.asyncio
    async def test_session_isolation(self, setup_privacy_test):
        """
        测试6: 会话隔离
        
        验收标准：
        - 不同会话的数据完全隔离
        - 会话A的数据不会泄露到会话B
        - 会话管理安全可靠
        """
        services = setup_privacy_test
        context_manager = services["context_manager"]
        
        # 创建两个独立会话
        session_a = f"test_session_a_{datetime.now().timestamp()}"
        session_b = f"test_session_b_{datetime.now().timestamp()}"
        
        # 会话A的敏感数据
        context_manager.add_local_message(
            session_id=session_a,
            role="user",
            content="查询客户A的订单：customer_a@example.com"
        )
        
        # 会话B的敏感数据
        context_manager.add_local_message(
            session_id=session_b,
            role="user",
            content="查询客户B的订单：customer_b@example.com"
        )
        
        # 获取各自的历史
        history_a = context_manager.get_local_history(session_a)
        history_b = context_manager.get_local_history(session_b)
        
        # 验证隔离性
        # 会话A的历史不应包含会话B的数据
        for msg in history_a:
            content = str(msg.get("content", ""))
            assert "customer_b@example.com" not in content, \
                "会话A不应包含会话B的数据"
        
        # 会话B的历史不应包含会话A的数据
        for msg in history_b:
            content = str(msg.get("content", ""))
            assert "customer_a@example.com" not in content, \
                "会话B不应包含会话A的数据"
        
        print(f"✅ 会话隔离测试通过")
        print(f"   - 会话A消息数: {len(history_a)}")
        print(f"   - 会话B消息数: {len(history_b)}")
    
    @pytest.mark.asyncio
    async def test_metadata_only_cloud_context(self, setup_privacy_test):
        """
        测试7: 云端仅接收元数据
        
        验收标准：
        - 云端接收表结构元数据
        - 云端接收列名但不接收数据值
        - 元数据足够支持SQL生成
        """
        services = setup_privacy_test
        context_manager = services["context_manager"]
        
        session_id = f"test_metadata_only_{datetime.now().timestamp()}"
        
        # 模拟表结构元数据（可以发送到云端）
        table_metadata = {
            "table_name": "orders",
            "columns": [
                {"name": "order_id", "type": "INT", "comment": "订单ID"},
                {"name": "customer_name", "type": "VARCHAR", "comment": "客户姓名"},
                {"name": "order_amount", "type": "DECIMAL", "comment": "订单金额"}
            ]
        }
        
        # 添加元数据到云端上下文
        context_manager.add_cloud_message(
            session_id=session_id,
            role="system",
            content=f"表结构: {table_metadata['table_name']}, 列: {[c['name'] for c in table_metadata['columns']]}"
        )
        
        # 模拟实际数据（不应发送到云端）
        actual_data = {
            "rows": [
                [1, "张三", 1500.00],
                [2, "李四", 2300.50]
            ]
        }
        
        # 添加实际数据到本地历史
        context_manager.add_local_message(
            session_id=session_id,
            role="system",
            content="查询结果",
            query_result=actual_data
        )
        
        # 获取云端历史
        cloud_history = context_manager.get_cloud_history(session_id)
        
        # 验证云端历史
        metadata_found = False
        for message in cloud_history:
            content = str(message.get("content", ""))
            
            # 应该包含表名和列名
            if "orders" in content:
                metadata_found = True
                assert "order_id" in content or "customer_name" in content, \
                    "云端历史应该包含列名"
            
            # 不应包含实际数据值
            assert "张三" not in content, "云端历史不应包含实际姓名"
            assert "李四" not in content, "云端历史不应包含实际姓名"
            assert "1500" not in content, "云端历史不应包含实际金额"
        
        assert metadata_found, "云端历史应该包含元数据"
        
        print(f"✅ 云端仅接收元数据测试通过")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
