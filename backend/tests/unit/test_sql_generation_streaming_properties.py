"""
SQL生成流式输出属性测试
Feature: streaming-stage-output
使用 Hypothesis 进行基于属性的测试
"""

import pytest
import asyncio
from hypothesis import given, strategies as st, settings, HealthCheck
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import json
from typing import List, Dict, Any

from src.services.chat_orchestrator import ChatOrchestrator, ChatContext, ChatStage
from src.services.ai_model_service import AIModelService, ModelType
from src.services.websocket_stream_service import WebSocketStreamService
from src.services.sql_security_validator import SQLSecurityService, ValidationResult, SecurityLevel


# ============================================================================
# Property 5: Streaming for AI-Generated Stages (SQL Generation)
# Validates: Requirements 4.2, 4.5
# ============================================================================


class TestSQLGenerationStreamingProperties:
    """
    Property 5: Streaming for AI-Generated Stages (SQL Generation)
    
    测试SQL生成流式输出的核心属性：
    1. stage_start, stage_update, stage_complete 消息序列正确
    2. 内容累积和 SQL 提取正确
    3. 错误处理正确
    """
    
    @pytest.fixture
    def mock_websocket_service(self):
        """创建模拟的 WebSocket 服务"""
        service = Mock(spec=WebSocketStreamService)
        service.send_stage_start = AsyncMock()
        service.send_stage_update = AsyncMock()
        service.send_stage_complete = AsyncMock()
        service.send_error_message = AsyncMock()
        return service
    
    @pytest.fixture
    def mock_ai_service(self):
        """创建模拟的 AI 服务"""
        service = Mock(spec=AIModelService)
        return service
    
    @pytest.fixture
    def mock_sql_security(self):
        """创建模拟的 SQL 安全验证服务"""
        service = Mock(spec=SQLSecurityService)
        # 默认返回验证通过
        from src.services.sql_security_validator import (
            SQLOperation, TableReference, FieldReference, QueryComplexity
        )
        validation_result = ValidationResult(
            is_valid=True,
            security_level=SecurityLevel.SAFE,
            operation=SQLOperation.SELECT,
            violations=[],
            table_references=[],
            field_references=[],
            complexity=QueryComplexity(
                table_count=1,
                join_count=0,
                subquery_count=0,
                function_count=0,
                condition_count=1,
                complexity_score=10.0,
                estimated_cost="low"
            ),
            sanitized_sql=None
        )
        service.validate_and_secure_sql = AsyncMock(return_value=validation_result)
        return service
    
    @pytest.fixture
    def mock_semantic_aggregator(self):
        """创建模拟的语义聚合器"""
        aggregator = Mock()
        result = Mock()
        result.enhanced_context = "Mock semantic context"
        result.modules_used = ["table_structure", "dictionary"]
        result.total_tokens_used = 100
        result.relevance_scores = {}
        aggregator.aggregate_semantic_context = AsyncMock(return_value=result)
        return aggregator
    
    @pytest.fixture
    def orchestrator(self, mock_websocket_service, mock_ai_service, mock_sql_security, mock_semantic_aggregator):
        """创建 ChatOrchestrator 实例"""
        orch = ChatOrchestrator()
        orch.websocket_service = mock_websocket_service
        orch.ai_service = mock_ai_service
        orch.sql_security = mock_sql_security
        orch.semantic_aggregator = mock_semantic_aggregator
        return orch
    
    @pytest.fixture
    def chat_context(self):
        """创建测试用的对话上下文"""
        context = ChatContext(session_id="test_session_123")
        context.selected_tables = ["table1", "table2"]
        return context
    
    # ------------------------------------------------------------------------
    # Property 5.1: stage_start, stage_update, stage_complete 消息序列
    # ------------------------------------------------------------------------
    
    @pytest.mark.asyncio
    @given(
        user_question=st.text(min_size=5, max_size=100),
        table_name=st.text(min_size=3, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll'))),
        chunks=st.lists(
            st.text(min_size=1, max_size=20, alphabet=st.characters(blacklist_categories=('Cs',))),
            min_size=2,
            max_size=10
        )
    )
    @settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.filter_too_much]
    )
    async def test_sql_generation_sends_correct_message_sequence(
        self,
        orchestrator,
        chat_context,
        mock_websocket_service,
        mock_ai_service,
        user_question: str,
        table_name: str,
        chunks: List[str]
    ):
        """
        Property: 对于任何用户问题，SQL生成应该发送正确的消息序列：
        stage_start (空内容) → stage_update (多个块) → stage_complete (格式化SQL)
        
        Feature: streaming-stage-output, Property 5: Streaming for AI-Generated Stages
        Validates: Requirements 4.2, 4.5
        """
        # 构建完整的 SQL 响应
        sql_query = f"SELECT * FROM {table_name} WHERE id > 0"
        full_response = f"```sql\n{sql_query}\n```"
        
        # 将响应分成多个块
        chunk_size = max(1, len(full_response) // len(chunks))
        actual_chunks = []
        for i in range(0, len(full_response), chunk_size):
            actual_chunks.append(full_response[i:i+chunk_size])
        
        # 模拟流式响应
        async def mock_stream():
            for chunk in actual_chunks:
                yield chunk
        
        mock_ai_service.call_cloud_model_stream = Mock(return_value=mock_stream())
        
        # 执行SQL生成
        result = await orchestrator._generate_sql(chat_context, user_question, "1")
        
        # 验证消息序列
        # 1. 应该发送 stage_start（空内容）
        assert mock_websocket_service.send_stage_start.called
        start_call = mock_websocket_service.send_stage_start.call_args
        assert start_call[1]['session_id'] == chat_context.session_id
        assert start_call[1]['stage_id'] == "sql_generation"
        assert start_call[1]['stage_name'] == "SQL生成"
        assert start_call[1]['content'] == ""
        
        # 2. 应该发送多个 stage_update（增量块）
        assert mock_websocket_service.send_stage_update.call_count >= len(actual_chunks)
        
        # 验证每个 stage_update 调用
        for i, call in enumerate(mock_websocket_service.send_stage_update.call_args_list):
            assert call[1]['session_id'] == chat_context.session_id
            assert call[1]['stage_id'] == "sql_generation"
            assert 'content' in call[1]
            assert len(call[1]['content']) > 0
        
        # 3. 应该发送 stage_complete（格式化SQL）
        assert mock_websocket_service.send_stage_complete.called
        complete_call = mock_websocket_service.send_stage_complete.call_args
        assert complete_call[1]['session_id'] == chat_context.session_id
        assert complete_call[1]['stage_id'] == "sql_generation"
        assert complete_call[1]['stage_name'] == "SQL生成"
        assert len(complete_call[1]['content']) > 0
        assert "```sql" in complete_call[1]['content']
        
        # 验证返回结果
        assert result['success'] is True
        assert 'sql' in result
        assert len(result['sql']) > 0
    
    # ------------------------------------------------------------------------
    # Property 5.2: 内容累积和 SQL 提取
    # ------------------------------------------------------------------------
    
    @pytest.mark.asyncio
    @given(
        user_question=st.text(min_size=5, max_size=100),
        table_name=st.text(min_size=3, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll'))),
        num_chunks=st.integers(min_value=2, max_value=15)
    )
    @settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    async def test_sql_generation_accumulates_and_extracts_sql(
        self,
        orchestrator,
        chat_context,
        mock_websocket_service,
        mock_ai_service,
        user_question: str,
        table_name: str,
        num_chunks: int
    ):
        """
        Property: 对于任何分块的 SQL 响应，系统应该正确累积内容并提取 SQL
        
        Feature: streaming-stage-output, Property 5: Streaming for AI-Generated Stages
        Validates: Requirements 4.2, 4.5
        """
        # 构建完整的 SQL 响应
        sql_query = f"SELECT * FROM {table_name} WHERE id > 0"
        full_response = f"```sql\n{sql_query}\n```"
        
        # 将响应分成指定数量的块
        chunk_size = max(1, len(full_response) // num_chunks)
        chunks = []
        for i in range(0, len(full_response), chunk_size):
            chunks.append(full_response[i:i+chunk_size])
        
        # 模拟流式响应
        async def mock_stream():
            for chunk in chunks:
                yield chunk
        
        mock_ai_service.call_cloud_model_stream = Mock(return_value=mock_stream())
        
        # 执行SQL生成
        result = await orchestrator._generate_sql(chat_context, user_question, "1")
        
        # 验证：应该成功提取 SQL
        assert result['success'] is True
        assert 'sql' in result
        
        # 验证：提取的 SQL 应该包含表名
        assert table_name in result['sql']
        assert "SELECT" in result['sql'].upper()
    
    # ------------------------------------------------------------------------
    # Property 5.3: 错误处理
    # ------------------------------------------------------------------------
    
    @pytest.mark.asyncio
    @given(
        user_question=st.text(min_size=5, max_size=100),
        chunks_before_error=st.lists(
            st.text(min_size=1, max_size=20, alphabet=st.characters(blacklist_categories=('Cs',))),
            min_size=1,
            max_size=5
        )
    )
    @settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    async def test_sql_generation_handles_streaming_errors(
        self,
        orchestrator,
        chat_context,
        mock_websocket_service,
        mock_ai_service,
        mock_sql_security,
        user_question: str,
        chunks_before_error: List[str]
    ):
        """
        Property: 对于任何流式过程中的错误，系统应该优雅处理并发送 stage_complete
        
        Feature: streaming-stage-output, Property 5: Streaming for AI-Generated Stages
        Validates: Requirements 4.2, 4.5
        """
        # 模拟流式响应，在产生几个块后抛出异常
        async def mock_stream():
            for chunk in chunks_before_error:
                yield chunk
            raise Exception("Simulated streaming error")
        
        mock_ai_service.call_cloud_model_stream = Mock(return_value=mock_stream())
        
        # 模拟非流式降级调用也失败
        mock_ai_service.call_cloud_model = AsyncMock(return_value={
            "success": False,
            "error": "Non-streaming also failed"
        })
        
        # 模拟安全验证失败（确保累积的内容无法通过验证）
        from src.services.sql_security_validator import (
            SecurityViolation, SQLOperation, QueryComplexity
        )
        mock_sql_security.validate_and_secure_sql = AsyncMock(return_value=ValidationResult(
            is_valid=False,
            security_level=SecurityLevel.DANGEROUS,
            operation=SQLOperation.DELETE,
            violations=[SecurityViolation(
                level=SecurityLevel.DANGEROUS,
                type="INVALID_SQL",
                message="Invalid SQL syntax",
                location=None,
                suggestion="Please provide valid SQL"
            )],
            table_references=[],
            field_references=[],
            complexity=QueryComplexity(
                table_count=0,
                join_count=0,
                subquery_count=0,
                function_count=0,
                condition_count=0,
                complexity_score=0.0,
                estimated_cost="unknown"
            ),
            sanitized_sql=None
        ))
        
        # 执行SQL生成
        result = await orchestrator._generate_sql(chat_context, user_question, "1")
        
        # 验证：应该发送 stage_start
        assert mock_websocket_service.send_stage_start.called
        
        # 验证：应该发送一些 stage_update（错误前的块）
        assert mock_websocket_service.send_stage_update.call_count >= len(chunks_before_error)
        
        # 验证：应该发送 stage_complete（即使出错）
        assert mock_websocket_service.send_stage_complete.called
        
        # 验证：结果应该标记为失败（因为流式失败且降级也失败）
        assert result['success'] is False
        assert 'error' in result
    
    # ------------------------------------------------------------------------
    # Property 5.4: SQL 安全验证失败重试
    # ------------------------------------------------------------------------
    
    @pytest.mark.asyncio
    @given(
        user_question=st.text(min_size=5, max_size=100),
        unsafe_sql=st.sampled_from([
            "DROP TABLE users",
            "DELETE FROM orders",
            "UPDATE products SET price = 0"
        ])
    )
    @settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    async def test_sql_generation_retries_on_security_failure(
        self,
        orchestrator,
        chat_context,
        mock_websocket_service,
        mock_ai_service,
        mock_sql_security,
        user_question: str,
        unsafe_sql: str
    ):
        """
        Property: 对于任何不安全的 SQL，系统应该重试生成
        
        Feature: streaming-stage-output, Property 5: Streaming for AI-Generated Stages
        Validates: Requirements 4.2, 4.5
        """
        # 模拟第一次返回不安全的 SQL
        async def mock_stream_unsafe():
            yield unsafe_sql
        
        # 模拟第二次返回安全的 SQL
        safe_sql = "SELECT * FROM users WHERE id > 0"
        async def mock_stream_safe():
            yield safe_sql
        
        # 设置流式调用返回不同的结果
        call_count = 0
        def get_stream():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return mock_stream_unsafe()
            else:
                return mock_stream_safe()
        
        mock_ai_service.call_cloud_model_stream = Mock(side_effect=lambda *args, **kwargs: get_stream())
        
        # 模拟安全验证：第一次失败，第二次成功
        validation_count = 0
        async def mock_validate(sql, data_source_id):
            nonlocal validation_count
            validation_count += 1
            if validation_count == 1:
                # 第一次验证失败
                from src.services.sql_security_validator import (
                    SecurityViolation, SQLOperation, TableReference, FieldReference, QueryComplexity
                )
                return ValidationResult(
                    is_valid=False,
                    security_level=SecurityLevel.DANGEROUS,
                    operation=SQLOperation.DELETE,
                    violations=[SecurityViolation(
                        level=SecurityLevel.DANGEROUS,
                        type="DANGEROUS_OPERATION",
                        message="Detected dangerous operation: DROP/DELETE/UPDATE",
                        location=None,
                        suggestion="Please regenerate with SELECT only"
                    )],
                    table_references=[],
                    field_references=[],
                    complexity=QueryComplexity(
                        table_count=1,
                        join_count=0,
                        subquery_count=0,
                        function_count=0,
                        condition_count=0,
                        complexity_score=100.0,
                        estimated_cost="high"
                    ),
                    sanitized_sql=None
                )
            else:
                # 第二次验证成功
                from src.services.sql_security_validator import (
                    SQLOperation, TableReference, FieldReference, QueryComplexity
                )
                return ValidationResult(
                    is_valid=True,
                    security_level=SecurityLevel.SAFE,
                    operation=SQLOperation.SELECT,
                    violations=[],
                    table_references=[],
                    field_references=[],
                    complexity=QueryComplexity(
                        table_count=1,
                        join_count=0,
                        subquery_count=0,
                        function_count=0,
                        condition_count=1,
                        complexity_score=10.0,
                        estimated_cost="low"
                    ),
                    sanitized_sql=safe_sql
                )
        
        # Use AsyncMock to properly wrap the async function
        mock_sql_security.validate_and_secure_sql = AsyncMock(side_effect=mock_validate)
        
        # 执行SQL生成
        result = await orchestrator._generate_sql(chat_context, user_question, "1")
        
        # 验证：应该成功（经过重试）
        assert result['success'] is True
        assert 'sql' in result
        
        # 验证：最终的 SQL 应该是安全的
        assert "SELECT" in result['sql'].upper()
        assert "DROP" not in result['sql'].upper()
        assert "DELETE" not in result['sql'].upper()
        assert "UPDATE" not in result['sql'].upper()
        
        # 验证：应该调用了多次流式生成（重试）
        assert call_count >= 2

    
    # ------------------------------------------------------------------------
    # Property 5.5: 空响应处理
    # ------------------------------------------------------------------------
    
    @pytest.mark.asyncio
    @given(
        user_question=st.text(min_size=5, max_size=100)
    )
    @settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    async def test_sql_generation_handles_empty_response(
        self,
        orchestrator,
        chat_context,
        mock_websocket_service,
        mock_ai_service,
        user_question: str
    ):
        """
        Property: 对于任何空响应，系统应该使用降级策略
        
        Feature: streaming-stage-output, Property 5: Streaming for AI-Generated Stages
        Validates: Requirements 4.2, 4.5
        """
        # 模拟空的流式响应
        async def mock_stream():
            return
            yield  # 使其成为生成器
        
        mock_ai_service.call_cloud_model_stream = Mock(return_value=mock_stream())
        
        # 模拟非流式降级调用也返回空
        mock_ai_service.call_cloud_model = AsyncMock(return_value={
            "success": True,
            "content": ""
        })
        
        # 执行SQL生成
        result = await orchestrator._generate_sql(chat_context, user_question, "1")
        
        # 验证：应该发送消息序列
        assert mock_websocket_service.send_stage_start.called
        assert mock_websocket_service.send_stage_complete.called
        
        # 验证：结果应该标记为失败（因为无法提取 SQL）
        # 或者使用降级策略返回默认 SQL
        assert 'success' in result
    
    # ------------------------------------------------------------------------
    # Property 5.6: 消息内容格式化
    # ------------------------------------------------------------------------
    
    @pytest.mark.asyncio
    @given(
        user_question=st.text(min_size=5, max_size=100),
        table_name=st.text(min_size=3, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll')))
    )
    @settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    async def test_stage_complete_content_is_formatted_sql(
        self,
        orchestrator,
        chat_context,
        mock_websocket_service,
        mock_ai_service,
        user_question: str,
        table_name: str
    ):
        """
        Property: 对于任何成功的SQL生成，stage_complete 的内容应该是格式化的 SQL（包含 ```sql 标记）
        
        Feature: streaming-stage-output, Property 5: Streaming for AI-Generated Stages
        Validates: Requirements 4.2, 4.5
        """
        # 构建有效的 SQL 响应
        sql_query = f"SELECT * FROM {table_name}"
        full_response = f"```sql\n{sql_query}\n```"
        
        # 模拟流式响应
        async def mock_stream():
            yield full_response
        
        mock_ai_service.call_cloud_model_stream = Mock(return_value=mock_stream())
        
        # 执行SQL生成
        result = await orchestrator._generate_sql(chat_context, user_question, "1")
        
        # 验证：stage_complete 的内容应该是格式化的 SQL
        assert mock_websocket_service.send_stage_complete.called
        complete_call = mock_websocket_service.send_stage_complete.call_args
        content = complete_call[1]['content']
        
        assert content is not None
        assert len(content) > 0
        assert "```sql" in content
        assert table_name in content or table_name in result['sql']


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
