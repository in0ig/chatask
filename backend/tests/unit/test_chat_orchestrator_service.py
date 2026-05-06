"""
对话流程编排引擎服务单元测试
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from types import SimpleNamespace

from src.services.chat_orchestrator import (
    ChatOrchestrator,
    ChatContext,
    ChatStage,
    ChatIntent,
    get_chat_orchestrator
)


@pytest.fixture
def chat_orchestrator():
    """创建对话编排器实例"""
    return ChatOrchestrator()


@pytest.fixture
def mock_context():
    """创建模拟对话上下文"""
    context = ChatContext("test_session_1")
    context.intent = ChatIntent.SMART_QUERY
    context.selected_tables = ["products", "sales"]
    context.generated_sql = "SELECT * FROM products"
    context.query_result = {
        "columns": ["id", "name", "price"],
        "rows": [[1, "Product A", 100], [2, "Product B", 200]],
        "total_rows": 2,
        "execution_time": 0.05
    }
    return context


class TestChatContext:
    """对话上下文测试"""
    
    def test_chat_context_creation(self):
        """测试创建对话上下文"""
        session_id = "test_session"
        context = ChatContext(session_id)
        
        assert context.session_id == session_id
        assert context.current_stage == ChatStage.INTENT_RECOGNITION
        assert context.intent == ChatIntent.UNKNOWN
        assert context.selected_tables == []
        assert context.generated_sql is None
        assert context.query_result is None
        assert context.previous_data == []
        assert context.error_count == 0
        assert context.retry_count == 0
        assert isinstance(context.metadata, dict)
        assert context.created_at is not None
        assert context.updated_at is not None
    
    def test_update_stage(self):
        """测试更新对话阶段"""
        context = ChatContext("test_session")
        original_time = context.updated_at
        
        context.update_stage(ChatStage.TABLE_SELECTION)
        
        assert context.current_stage == ChatStage.TABLE_SELECTION
        assert context.updated_at > original_time
    
    def test_add_error(self):
        """测试添加错误记录"""
        context = ChatContext("test_session")
        
        context.add_error("测试错误")
        
        assert context.error_count == 1
        assert "errors" in context.metadata
        assert len(context.metadata["errors"]) == 1
        
        error = context.metadata["errors"][0]
        assert error["error"] == "测试错误"
        assert error["stage"] == ChatStage.INTENT_RECOGNITION.value
        assert "timestamp" in error
    
    def test_add_previous_data(self):
        """测试添加历史数据"""
        context = ChatContext("test_session")
        context.generated_sql = "SELECT * FROM test"
        
        test_data = {"columns": ["id"], "rows": [[1]], "total_rows": 1}
        context.add_previous_data(test_data)
        
        assert len(context.previous_data) == 1
        assert context.previous_data[0]["data"] == test_data
        assert context.previous_data[0]["sql"] == "SELECT * FROM test"
        assert "timestamp" in context.previous_data[0]
    
    def test_add_previous_data_limit(self):
        """测试历史数据数量限制"""
        context = ChatContext("test_session")
        
        # 添加6条历史数据
        for i in range(6):
            context.add_previous_data({"test": i})
        
        # 应该只保留最近5条
        assert len(context.previous_data) == 5
        assert context.previous_data[0]["data"]["test"] == 1  # 最早的被删除
        assert context.previous_data[-1]["data"]["test"] == 5  # 最新的保留


class TestJoinConstraintRelaxation:
    def test_relax_required_tables_when_time_is_resolved(self, chat_orchestrator):
        context = ChatContext("test_session")
        context.metadata["resolved_time_context"] = SimpleNamespace(
            date_ranges=[SimpleNamespace(start_date="2025-01-26", end_date="2025-02-01")]
        )
        join_constraints = {
            "mode": "strict",
            "required_table_ids": ["t1", "t2", "t3"],
            "required_table_names": [
                "survey_attendance_mock",
                "fiscal_calendar_holidays",
                "park_seasonal_campaign",
            ],
            "allowed_edges": [],
            "inferred_candidates": [],
        }

        relaxed = chat_orchestrator._relax_required_tables_for_resolved_time(
            context, join_constraints
        )

        assert "park_seasonal_campaign" not in relaxed["required_table_names"]
        assert relaxed["required_table_names"] == [
            "survey_attendance_mock",
            "fiscal_calendar_holidays",
        ]
        assert relaxed["required_table_ids"] == ["t1", "t2"]
        assert relaxed["required_table_relax_reason"] == "resolved_time_context_date_ranges"

    def test_keep_required_tables_when_time_not_resolved(self, chat_orchestrator):
        context = ChatContext("test_session")
        context.metadata["resolved_time_context"] = SimpleNamespace(date_ranges=[])
        join_constraints = {
            "mode": "strict",
            "required_table_ids": ["t1", "t2", "t3"],
            "required_table_names": [
                "survey_attendance_mock",
                "fiscal_calendar_holidays",
                "park_seasonal_campaign",
            ],
            "allowed_edges": [],
            "inferred_candidates": [],
        }

        kept = chat_orchestrator._relax_required_tables_for_resolved_time(
            context, join_constraints
        )

        assert kept == join_constraints


class TestFiscalTimeQueryGuard:
    def test_uncertain_fiscal_query_should_be_skipped(self, chat_orchestrator):
        query = {
            "type": "month_range",
            "year": 2025,
            "month": 1,
            "description": "2025年1月（假设生日月在1月，需先查活动表确认）",
        }
        assert chat_orchestrator._is_uncertain_fiscal_query(query) is True

    def test_certain_fiscal_query_should_not_be_skipped(self, chat_orchestrator):
        query = {
            "type": "month_range",
            "year": 2025,
            "month": 1,
            "description": "2025年1月自然月范围",
        }
        assert chat_orchestrator._is_uncertain_fiscal_query(query) is False


class TestEnumFlagSemanticGuard:
    def test_rejects_non_null_check_for_binary_flag_field(self, chat_orchestrator):
        semantic_context_result = SimpleNamespace(
            aggregated_content={
                "table_structure": {
                    "tables": [
                        {
                            "field_value_samples": {
                                "is_holiday": ["Y", "N"],
                                "is_weekday": ["Y", "N"],
                            }
                        }
                    ]
                }
            }
        )
        sql = "SELECT * FROM fiscal_calendar_holidays f WHERE f.is_holiday IS NOT NULL"
        error = chat_orchestrator._validate_sql_enum_flag_predicates(sql, semantic_context_result)
        assert error is not None
        assert "is_holiday" in error

    def test_allows_explicit_equality_for_binary_flag_field(self, chat_orchestrator):
        semantic_context_result = SimpleNamespace(
            aggregated_content={
                "table_structure": {
                    "tables": [
                        {
                            "field_value_samples": {
                                "is_holiday": ["Y", "N"],
                            }
                        }
                    ]
                }
            }
        )
        sql = "SELECT * FROM fiscal_calendar_holidays WHERE is_holiday = 'Y'"
        error = chat_orchestrator._validate_sql_enum_flag_predicates(sql, semantic_context_result)
        assert error is None


class TestTextExactMatchRiskGuard:
    def test_detects_partial_name_exact_match_risk(self, chat_orchestrator):
        semantic_context_result = SimpleNamespace(
            aggregated_content={
                "table_structure": {
                    "tables": [
                        {
                            "field_value_samples": {
                                "campaign_name": [
                                    "奇妙春日・奇奇蒂蒂生日月",
                                    "奇幻冬日季・圣诞跨年预热",
                                ]
                            }
                        }
                    ]
                }
            }
        )
        sql = "SELECT * FROM park_seasonal_campaign WHERE campaign_name = '奇奇蒂蒂生日月'"
        err = chat_orchestrator._validate_sql_text_exact_match_risk(sql, semantic_context_result)
        assert err is not None
        assert "campaign_name" in err

    def test_allows_exact_match_if_sample_contains_same_value(self, chat_orchestrator):
        semantic_context_result = SimpleNamespace(
            aggregated_content={
                "table_structure": {
                    "tables": [
                        {
                            "field_value_samples": {
                                "campaign_name": ["奇奇蒂蒂生日月"]
                            }
                        }
                    ]
                }
            }
        )
        sql = "SELECT * FROM park_seasonal_campaign WHERE campaign_name = '奇奇蒂蒂生日月'"
        err = chat_orchestrator._validate_sql_text_exact_match_risk(sql, semantic_context_result)
        assert err is None


class TestWorkdayHolidaySplitGuard:
    def test_detects_overlapping_workday_holiday_split(self, chat_orchestrator):
        sql = """
        WITH week_stats AS (
          SELECT
            SUM(CASE WHEN hc.is_weekday = 'Y' THEN 1 ELSE 0 END) AS workday_days,
            SUM(CASE WHEN hc.is_holiday = 'Y' THEN 1 ELSE 0 END) AS holiday_days
          FROM fiscal_calendar_holidays hc
        )
        SELECT * FROM week_stats
        """
        err = chat_orchestrator._validate_workday_holiday_split_consistency(
            sql=sql,
            user_question="2025年活动期间，工作日与节假日Attendance差异是多少？",
        )
        assert err is not None
        assert "重叠" in err

    def test_allows_complementary_split(self, chat_orchestrator):
        sql = """
        WITH week_stats AS (
          SELECT
            SUM(CASE WHEN hc.is_weekday = 'Y' AND (hc.is_holiday IS NULL OR hc.is_holiday = '') THEN 1 ELSE 0 END) AS workday_days,
            SUM(CASE WHEN NOT (hc.is_weekday = 'Y' AND (hc.is_holiday IS NULL OR hc.is_holiday = '')) THEN 1 ELSE 0 END) AS holiday_days
          FROM fiscal_calendar_holidays hc
        )
        SELECT * FROM week_stats
        """
        err = chat_orchestrator._validate_workday_holiday_split_consistency(
            sql=sql,
            user_question="2025年活动期间，工作日与节假日Attendance差异是多少？",
        )
        assert err is None


class TestSqlPeerReview:
    @pytest.mark.asyncio
    async def test_peer_review_returns_structured_result(self, chat_orchestrator):
        context = ChatContext("test_session")
        context.thinking_result = "test thinking"
        semantic_context_result = SimpleNamespace(enhanced_context="test semantic context")

        chat_orchestrator.prompt_manager.render_prompt = MagicMock(return_value="review prompt")
        chat_orchestrator.ai_service.call_model = AsyncMock(
            return_value={
                "success": True,
                "content": """
                {
                  "is_valid": false,
                  "confidence": 0.91,
                  "violations": [{"code":"ENUM_FLAG_NON_NULL_MISUSE","message":"bad predicate","evidence":"is_holiday IS NOT NULL"}],
                  "review_summary": "枚举字段分类条件错误",
                  "corrected_sql": "SELECT * FROM t WHERE is_holiday='Y'"
                }
                """,
            }
        )

        result = await chat_orchestrator._peer_review_sql(
            context=context,
            user_question="q",
            generated_sql="SELECT * FROM t",
            semantic_context_result=semantic_context_result,
            join_constraints={},
            prompt_db_type="MySQL",
            retry_index=1,
        )

        assert result["success"] is True
        assert result["is_valid"] is False
        assert "corrected_sql" in result
        assert result["corrected_sql"] == "SELECT * FROM t WHERE is_holiday='Y'"

class TestChatOrchestrator:
    """对话编排器测试"""
    
    @pytest.mark.asyncio
    async def test_get_or_create_context(self, chat_orchestrator):
        """测试获取或创建对话上下文"""
        session_id = "test_session"
        
        # 第一次调用，创建新上下文
        context1 = chat_orchestrator.get_or_create_context(session_id)
        assert context1.session_id == session_id
        assert session_id in chat_orchestrator.active_contexts
        
        # 第二次调用，返回已存在的上下文
        context2 = chat_orchestrator.get_or_create_context(session_id)
        assert context1 is context2
    
    @pytest.mark.asyncio
    @patch('src.services.chat_orchestrator.get_websocket_stream_service')
    @patch.object(ChatOrchestrator, '_execute_chat_pipeline')
    async def test_start_chat_success(self, mock_pipeline, mock_websocket, chat_orchestrator):
        """测试成功开始对话"""
        # 模拟依赖
        mock_websocket_service = AsyncMock()
        mock_websocket_service.send_status_message = AsyncMock(return_value=True)
        mock_websocket.return_value = mock_websocket_service
        
        # 替换实例中的websocket服务
        chat_orchestrator.websocket_service = mock_websocket_service
        
        mock_pipeline.return_value = {
            "success": True,
            "session_id": "test_session",
            "intent": "smart_query",
            "tables": ["products"],
            "sql": "SELECT * FROM products",
            "result": {"columns": ["id"], "rows": [[1]]},
            "analysis": "分析结果",
            "stage": "completed"
        }
        
        # 执行测试
        result = await chat_orchestrator.start_chat("test_session", "查询产品信息")
        
        # 验证结果
        assert result["success"] is True
        assert result["session_id"] == "test_session"
        assert result["intent"] == "smart_query"
        
        # 验证WebSocket调用
        mock_websocket_service.send_status_message.assert_called_once()
        
        # 验证流水线调用
        mock_pipeline.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('src.services.chat_orchestrator.get_websocket_stream_service')
    async def test_start_chat_failure(self, mock_websocket, chat_orchestrator):
        """测试开始对话失败"""
        # 模拟WebSocket服务
        mock_websocket_service = AsyncMock()
        mock_websocket_service.send_status_message = AsyncMock(return_value=True)
        mock_websocket_service.send_error_message = AsyncMock(return_value=True)
        mock_websocket.return_value = mock_websocket_service
        
        # 替换实例中的websocket服务
        chat_orchestrator.websocket_service = mock_websocket_service
        
        # 模拟流水线执行失败
        with patch.object(chat_orchestrator, '_execute_chat_pipeline', side_effect=Exception("测试错误")):
            result = await chat_orchestrator.start_chat("test_session", "查询产品信息")
        
        # 验证结果
        assert result["success"] is False
        assert "测试错误" in result["error"]
        assert result["session_id"] == "test_session"
        
        # 验证错误消息发送
        mock_websocket_service.send_error_message.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_continue_chat_no_session(self, chat_orchestrator):
        """测试继续不存在的对话"""
        result = await chat_orchestrator.continue_chat("nonexistent_session", "用户回复")
        
        assert result["success"] is False
        assert "会话不存在或已过期" in result["error"]
        assert result["session_id"] == "nonexistent_session"
    
    @pytest.mark.asyncio
    @patch.object(ChatOrchestrator, '_handle_clarification_response')
    async def test_continue_chat_clarification(self, mock_handle, chat_orchestrator):
        """测试继续对话 - 澄清阶段"""
        # 创建处于澄清阶段的上下文
        context = chat_orchestrator.get_or_create_context("test_session")
        context.update_stage(ChatStage.INTENT_CLARIFICATION)
        
        mock_handle.return_value = {"success": True, "result": "澄清处理结果"}
        
        result = await chat_orchestrator.continue_chat("test_session", "是的，请继续")
        
        assert result["success"] is True
        mock_handle.assert_called_once_with(context, "是的，请继续")
    
    @pytest.mark.asyncio
    @patch.object(ChatOrchestrator, '_handle_error_recovery')
    async def test_continue_chat_error_handling(self, mock_handle, chat_orchestrator):
        """测试继续对话 - 错误处理阶段"""
        # 创建处于错误处理阶段的上下文
        context = chat_orchestrator.get_or_create_context("test_session")
        context.update_stage(ChatStage.ERROR_HANDLING)
        
        mock_handle.return_value = {"success": True, "result": "错误恢复结果"}
        
        result = await chat_orchestrator.continue_chat("test_session", "重试")
        
        assert result["success"] is True
        mock_handle.assert_called_once_with(context, "重试")
    
    @pytest.mark.asyncio
    @patch.object(ChatOrchestrator, '_handle_followup_question')
    async def test_continue_chat_followup(self, mock_handle, chat_orchestrator):
        """测试继续对话 - 追问"""
        # 创建已完成的上下文
        context = chat_orchestrator.get_or_create_context("test_session")
        context.update_stage(ChatStage.COMPLETED)
        
        mock_handle.return_value = {"success": True, "answer": "追问答案"}
        
        result = await chat_orchestrator.continue_chat("test_session", "为什么是这个结果？")
        
        assert result["success"] is True
        mock_handle.assert_called_once_with(context, "为什么是这个结果？")
    
    @pytest.mark.asyncio
    @patch.object(ChatOrchestrator, '_recognize_intent')
    @patch('src.services.chat_orchestrator.get_websocket_stream_service')
    async def test_execute_chat_pipeline_intent_failure(self, mock_websocket, mock_intent, chat_orchestrator):
        """测试执行对话流水线 - 意图识别失败"""
        # 模拟依赖
        mock_websocket_service = AsyncMock()
        mock_websocket_service.send_thinking_message = AsyncMock(return_value=True)
        mock_websocket_service.send_error_message = AsyncMock(return_value=True)
        mock_websocket.return_value = mock_websocket_service
        
        # 替换实例中的websocket服务
        chat_orchestrator.websocket_service = mock_websocket_service
        
        mock_intent.return_value = {"success": False, "error": "意图识别失败"}
        
        context = chat_orchestrator.get_or_create_context("test_session")
        
        # 执行测试
        result = await chat_orchestrator._execute_chat_pipeline(context, "测试问题", None)
        
        # 验证结果
        assert result["success"] is False
        assert "意图识别失败" in result["error"]
        
        # 验证错误处理
        mock_websocket_service.send_error_message.assert_called()
    
    @pytest.mark.asyncio
    @patch.object(ChatOrchestrator, '_recognize_intent')
    @patch.object(ChatOrchestrator, '_select_tables')
    @patch('src.services.chat_orchestrator.get_websocket_stream_service')
    async def test_execute_chat_pipeline_table_selection_failure(self, mock_websocket, mock_tables, mock_intent, chat_orchestrator):
        """测试执行对话流水线 - 选表失败"""
        # 模拟依赖
        mock_websocket_service = AsyncMock()
        mock_websocket.return_value = mock_websocket_service
        
        mock_intent.return_value = {"success": True, "intent": "smart_query"}
        mock_tables.return_value = {"success": False, "error": "选表失败"}
        
        context = chat_orchestrator.get_or_create_context("test_session")
        
        # 执行测试
        result = await chat_orchestrator._execute_chat_pipeline(context, "测试问题", None)
        
        # 验证结果
        assert result["success"] is False
        assert "选表失败" in result["error"]
    
    @pytest.mark.asyncio
    @patch.object(ChatOrchestrator, '_recognize_intent')
    @patch.object(ChatOrchestrator, '_select_tables')
    @patch.object(ChatOrchestrator, '_request_clarification')
    @patch('src.services.chat_orchestrator.get_websocket_stream_service')
    async def test_execute_chat_pipeline_needs_clarification(self, mock_websocket, mock_clarify, mock_tables, mock_intent, chat_orchestrator):
        """测试执行对话流水线 - 需要澄清"""
        # 模拟依赖
        mock_websocket_service = AsyncMock()
        mock_websocket.return_value = mock_websocket_service
        
        mock_intent.return_value = {"success": True, "intent": "smart_query"}
        mock_tables.return_value = {
            "success": True,
            "tables": ["products"],
            "needs_clarification": True,
            "clarification_question": "请确认查询范围"
        }
        mock_clarify.return_value = {"success": True, "needs_clarification": True}
        
        context = chat_orchestrator.get_or_create_context("test_session")
        
        # 执行测试
        result = await chat_orchestrator._execute_chat_pipeline(context, "测试问题", None)
        
        # 验证结果
        assert result["success"] is True
        assert result["needs_clarification"] is True
        
        # 验证澄清请求
        mock_clarify.assert_called_once()
    
    def test_fallback_intent_recognition(self, chat_orchestrator):
        """测试意图识别降级策略"""
        # 测试查询意图
        result = chat_orchestrator._fallback_intent_recognition("查询销售数量")
        assert result["success"] is True
        assert result["intent"] == "smart_query"
        
        # 测试报告意图
        result = chat_orchestrator._fallback_intent_recognition("生成销售报告")
        assert result["success"] is True
        assert result["intent"] == "report_generation"
        
        # 测试追问意图
        result = chat_orchestrator._fallback_intent_recognition("为什么会这样？")
        assert result["success"] is True
        assert result["intent"] == "data_followup"
        
        # 测试未知意图
        result = chat_orchestrator._fallback_intent_recognition("随机文本")
        assert result["success"] is True
        assert result["intent"] == "smart_query"  # 默认为查询
        assert result["confidence"] == 0.5
    
    def test_extract_sql_from_response(self, chat_orchestrator):
        """测试从AI响应中提取SQL"""
        # 测试标准SQL代码块
        response1 = "```sql\nSELECT * FROM products\n```"
        sql1 = chat_orchestrator._extract_sql_from_response(response1)
        assert sql1 == "SELECT * FROM products"
        
        # 测试普通代码块
        response2 = "```\nSELECT * FROM users\n```"
        sql2 = chat_orchestrator._extract_sql_from_response(response2)
        assert sql2 == "SELECT * FROM users"
        
        # 测试无代码块
        response3 = "SELECT * FROM orders"
        sql3 = chat_orchestrator._extract_sql_from_response(response3)
        assert sql3 == "SELECT * FROM orders"
    
    def test_should_generate_chart(self, chat_orchestrator):
        """测试是否应该生成图表"""
        # 测试适合生成图表的数据
        good_result = {
            "columns": ["name", "value"],
            "rows": [["A", 10], ["B", 20], ["C", 30]],
            "total_rows": 3
        }
        assert chat_orchestrator._should_generate_chart(good_result) is True
        
        # 测试数据过少
        small_result = {
            "columns": ["name", "value"],
            "rows": [["A", 10]],
            "total_rows": 1
        }
        assert chat_orchestrator._should_generate_chart(small_result) is False
        
        # 测试数据过多
        large_result = {
            "columns": ["name", "value"],
            "rows": [["A", 10]] * 101,
            "total_rows": 101
        }
        assert chat_orchestrator._should_generate_chart(large_result) is False
        
        # 测试列数不足
        few_columns = {
            "columns": ["name"],
            "rows": [["A"], ["B"], ["C"]],
            "total_rows": 3
        }
        assert chat_orchestrator._should_generate_chart(few_columns) is False
    
    def test_generate_chart_data(self, chat_orchestrator):
        """测试生成图表数据"""
        query_result = {
            "columns": ["product", "sales"],
            "rows": [["A", 100], ["B", 200], ["C", 150]],
            "total_rows": 3
        }
        
        chart_data = chat_orchestrator._generate_chart_data(query_result)
        
        assert chart_data["type"] == "bar"
        assert chart_data["xAxis"] == "product"
        assert chart_data["yAxis"] == "sales"
        assert len(chart_data["data"]) == 3
        assert chart_data["data"][0] == {"x": "A", "y": 100.0}
        assert chart_data["data"][1] == {"x": "B", "y": 200.0}
        assert chart_data["data"][2] == {"x": "C", "y": 150.0}
    
    def test_format_previous_data(self, chat_orchestrator):
        """测试格式化历史数据"""
        # 测试无历史数据
        result1 = chat_orchestrator._format_previous_data([])
        assert result1 == "无历史数据"
        
        # 测试有历史数据
        previous_data = [
            {
                "timestamp": "2024-01-01T10:00:00.000Z",
                "data": {"total_rows": 10}
            },
            {
                "timestamp": "2024-01-01T11:00:00.000Z",
                "data": {"total_rows": 20}
            }
        ]
        
        result2 = chat_orchestrator._format_previous_data(previous_data)
        assert "历史查询1: 2024-01-01T10:00:00 - 行数: 10" in result2
        assert "历史查询2: 2024-01-01T11:00:00 - 行数: 20" in result2
    
    def test_get_session_status(self, chat_orchestrator):
        """测试获取会话状态"""
        # 测试不存在的会话
        status1 = chat_orchestrator.get_session_status("nonexistent")
        assert status1["session_id"] == "nonexistent"
        assert status1["exists"] is False
        
        # 测试存在的会话
        context = chat_orchestrator.get_or_create_context("test_session")
        context.intent = ChatIntent.SMART_QUERY
        context.selected_tables = ["products"]
        context.query_result = {"test": "data"}
        context.add_previous_data({"test": "previous"})
        
        status2 = chat_orchestrator.get_session_status("test_session")
        assert status2["session_id"] == "test_session"
        assert status2["exists"] is True
        assert status2["current_stage"] == ChatStage.INTENT_RECOGNITION.value
        assert status2["intent"] == ChatIntent.SMART_QUERY.value
        assert status2["selected_tables"] == ["products"]
        assert status2["has_result"] is True
        assert status2["previous_data_count"] == 1
    
    def test_cleanup_session(self, chat_orchestrator):
        """测试清理会话"""
        # 创建会话
        chat_orchestrator.get_or_create_context("test_session")
        assert "test_session" in chat_orchestrator.active_contexts
        
        # 清理会话
        result = chat_orchestrator.cleanup_session("test_session")
        assert result is True
        assert "test_session" not in chat_orchestrator.active_contexts
        
        # 清理不存在的会话
        result2 = chat_orchestrator.cleanup_session("nonexistent")
        assert result2 is False
    
    def test_get_all_sessions_status(self, chat_orchestrator):
        """测试获取所有会话状态"""
        # 创建几个会话
        chat_orchestrator.get_or_create_context("session1")
        chat_orchestrator.get_or_create_context("session2")
        
        status = chat_orchestrator.get_all_sessions_status()
        
        assert status["total_sessions"] == 2
        assert "sessions" in status
        assert "session1" in status["sessions"]
        assert "session2" in status["sessions"]
        
        # 验证会话详情
        session1_info = status["sessions"]["session1"]
        assert session1_info["current_stage"] == ChatStage.INTENT_RECOGNITION.value
        assert session1_info["intent"] == ChatIntent.UNKNOWN.value
        assert session1_info["error_count"] == 0


class TestChatOrchestratorSingleton:
    """对话编排器单例测试"""
    
    def test_get_chat_orchestrator_singleton(self):
        """测试获取对话编排器单例"""
        orchestrator1 = get_chat_orchestrator()
        orchestrator2 = get_chat_orchestrator()
        
        assert orchestrator1 is orchestrator2
        assert isinstance(orchestrator1, ChatOrchestrator)


class TestTokenCounting:
    """Token 计算功能测试"""
    
    def test_count_tokens_empty_text(self, chat_orchestrator):
        """测试空文本的 Token 计数"""
        assert chat_orchestrator._count_tokens("") == 0
        assert chat_orchestrator._count_tokens(None) == 0
    
    def test_count_tokens_chinese_only(self, chat_orchestrator):
        """测试纯中文文本的 Token 计数"""
        # 中文字符约 1.5 tokens
        text = "你好世界"  # 4个中文字符
        tokens = chat_orchestrator._count_tokens(text)
        # 4 * 1.5 = 6 tokens (允许一定误差)
        assert 5 <= tokens <= 8
    
    def test_count_tokens_english_only(self, chat_orchestrator):
        """测试纯英文文本的 Token 计数"""
        # 英文单词约 1 token
        text = "hello world test"  # 3个英文单词
        tokens = chat_orchestrator._count_tokens(text)
        # 3 * 1.0 = 3 tokens
        assert tokens == 3
    
    def test_count_tokens_mixed_text(self, chat_orchestrator):
        """测试中英文混合文本的 Token 计数"""
        # 混合文本：中文 + 英文 + 标点
        text = "查询 sales 数据，统计 2024 年的销售额"
        # 中文字符: 查询数据统计年的销售额 (10个) = 10 * 1.5 = 15
        # 英文单词: sales, 2024 (2个) = 2 * 1.0 = 2
        # 标点符号: ，(1个) = 1 * 0.5 = 0.5
        # 总计: 15 + 2 + 0.5 = 17.5 ≈ 17 (允许一定误差)
        tokens = chat_orchestrator._count_tokens(text)
        assert 15 <= tokens <= 25  # 允许一定误差范围
    
    def test_count_tokens_with_punctuation(self, chat_orchestrator):
        """测试包含标点符号的文本 Token 计数"""
        text = "Hello, world! How are you?"
        # 英文单词: Hello, world, How, are, you (5个) = 5 * 1.0 = 5
        # 标点符号: , ! ? (3个) = 3 * 0.5 = 1.5
        # 总计: 5 + 1.5 = 6.5 ≈ 6
        tokens = chat_orchestrator._count_tokens(text)
        assert 5 <= tokens <= 8  # 允许一定误差范围
    
    def test_count_tokens_sql_query(self, chat_orchestrator):
        """测试 SQL 查询的 Token 计数"""
        sql = "SELECT * FROM products WHERE price > 100"
        # 英文单词: SELECT, FROM, products, WHERE, price (5个) = 5 * 1.0 = 5
        # 标点符号: *, >, 100 等
        tokens = chat_orchestrator._count_tokens(sql)
        assert tokens > 0
        assert tokens < 50  # SQL 语句不应该太长
    
    def test_count_tokens_long_text(self, chat_orchestrator):
        """测试长文本的 Token 计数"""
        # 构造一个较长的文本
        text = "这是一个测试文本。" * 100  # 重复100次
        tokens = chat_orchestrator._count_tokens(text)
        # 每次重复约 9 个字符（7个中文 + 1个标点 + 1个空格）
        # 7 * 1.5 + 1 * 0.5 = 11 tokens per repeat
        # 100 * 11 = 1100 tokens
        assert 900 <= tokens <= 1300  # 允许一定误差范围
    
    def test_calculate_history_tokens_empty(self, chat_orchestrator):
        """测试空历史消息的 Token 计数"""
        history_messages = []
        total_tokens = chat_orchestrator._calculate_history_tokens(history_messages)
        assert total_tokens == 0
    
    def test_calculate_history_tokens_single_message(self, chat_orchestrator):
        """测试单条历史消息的 Token 计数"""
        history_messages = [
            {"role": "user", "content": "查询产品信息"}
        ]
        total_tokens = chat_orchestrator._calculate_history_tokens(history_messages)
        # "查询产品信息" = 6个中文字符 = 6 * 1.5 = 9 tokens (允许一定误差)
        assert 8 <= total_tokens <= 12
    
    def test_calculate_history_tokens_multiple_messages(self, chat_orchestrator):
        """测试多条历史消息的 Token 计数"""
        history_messages = [
            {"role": "user", "content": "查询产品信息"},  # 9 tokens
            {"role": "assistant", "content": "好的，我来帮您查询"},  # 11 * 1.5 = 16.5 ≈ 16 tokens
            {"role": "user", "content": "显示前10条"}  # 6 * 1.5 = 9 tokens
        ]
        total_tokens = chat_orchestrator._calculate_history_tokens(history_messages)
        # 总计: 9 + 16 + 9 = 34 tokens
        assert 30 <= total_tokens <= 40  # 允许一定误差范围
    
    def test_calculate_history_tokens_mixed_content(self, chat_orchestrator):
        """测试包含中英文混合内容的历史消息 Token 计数"""
        history_messages = [
            {"role": "user", "content": "查询 sales 数据"},
            {"role": "assistant", "content": "SELECT * FROM sales"},
            {"role": "user", "content": "统计 2024 年的销售额"}
        ]
        total_tokens = chat_orchestrator._calculate_history_tokens(history_messages)
        assert total_tokens > 0
        assert total_tokens < 200  # 合理的范围
    
    def test_calculate_history_tokens_with_empty_content(self, chat_orchestrator):
        """测试包含空内容的历史消息 Token 计数"""
        history_messages = [
            {"role": "user", "content": "查询产品"},
            {"role": "assistant", "content": ""},  # 空内容
            {"role": "user", "content": "显示结果"}
        ]
        total_tokens = chat_orchestrator._calculate_history_tokens(history_messages)
        # 只计算非空消息的 tokens
        assert total_tokens > 0
    
    def test_calculate_history_tokens_large_history(self, chat_orchestrator):
        """测试大量历史消息的 Token 计数"""
        # 模拟 20 轮对话（40 条消息）
        history_messages = []
        for i in range(20):
            history_messages.append({
                "role": "user",
                "content": f"这是第 {i+1} 轮对话的用户问题"
            })
            history_messages.append({
                "role": "assistant",
                "content": f"这是第 {i+1} 轮对话的 AI 回复"
            })
        
        total_tokens = chat_orchestrator._calculate_history_tokens(history_messages)
        # 每条消息约 15-20 tokens，40 条消息约 600-800 tokens
        assert 500 <= total_tokens <= 1000
    
    def test_token_threshold_logic(self, chat_orchestrator):
        """测试 Token 阈值判断逻辑"""
        TOKEN_THRESHOLD = 2000
        
        # 测试未超过阈值的情况
        small_history = [
            {"role": "user", "content": "简单问题"}
        ]
        small_tokens = chat_orchestrator._calculate_history_tokens(small_history)
        assert small_tokens < TOKEN_THRESHOLD
        
        # 测试超过阈值的情况（模拟大量历史消息）
        large_history = []
        for i in range(100):
            large_history.append({
                "role": "user",
                "content": "这是一个比较长的用户问题，包含了很多详细的描述和要求" * 5
            })
            large_history.append({
                "role": "assistant",
                "content": "这是一个详细的 AI 回复，包含了完整的分析和建议" * 5
            })
        
        large_tokens = chat_orchestrator._calculate_history_tokens(large_history)
        assert large_tokens > TOKEN_THRESHOLD


class TestChatOrchestratorIntegration:
    """对话编排器集成测试"""
    
    @pytest.mark.asyncio
    @patch('src.services.chat_orchestrator.get_websocket_stream_service')
    @patch.object(ChatOrchestrator, '_recognize_intent')
    @patch.object(ChatOrchestrator, '_select_tables')
    @patch.object(ChatOrchestrator, '_generate_sql')
    @patch.object(ChatOrchestrator, '_execute_sql')
    @patch.object(ChatOrchestrator, '_analyze_data')
    @patch.object(ChatOrchestrator, '_present_results')
    async def test_complete_chat_pipeline(self, mock_present, mock_analyze, mock_execute, 
                                        mock_generate, mock_select, mock_intent, 
                                        mock_websocket, chat_orchestrator):
        """测试完整对话流水线"""
        # 模拟所有依赖
        mock_websocket_service = AsyncMock()
        mock_websocket_service.send_status_message = AsyncMock(return_value=True)
        mock_websocket_service.send_thinking_message = AsyncMock(return_value=True)
        mock_websocket.return_value = mock_websocket_service
        
        # 替换实例中的websocket服务
        chat_orchestrator.websocket_service = mock_websocket_service
        
        mock_intent.return_value = {"success": True, "intent": "smart_query"}
        mock_select.return_value = {"success": True, "tables": ["products"], "needs_clarification": False}
        mock_generate.return_value = {"success": True, "sql": "SELECT * FROM products"}
        mock_execute.return_value = {"success": True, "result": {"columns": ["id"], "rows": [[1]]}}
        mock_analyze.return_value = {"success": True, "analysis": "分析结果"}
        mock_present.return_value = None
        
        # 执行完整流水线
        result = await chat_orchestrator.start_chat("test_session", "查询产品信息")
        
        # 验证结果
        assert result["success"] is True
        assert result["intent"] == "smart_query"
        assert result["tables"] == ["products"]
        assert result["sql"] == "SELECT * FROM products"
        assert result["analysis"] == "分析结果"
        assert result["stage"] == "completed"
        
        # 验证所有步骤都被调用
        mock_intent.assert_called_once()
        mock_select.assert_called_once()
        mock_generate.assert_called_once()
        mock_execute.assert_called_once()
        mock_analyze.assert_called_once()
        mock_present.assert_called_once()
        
        # 验证WebSocket消息发送
        assert mock_websocket_service.send_thinking_message.call_count >= 4  # 至少4个思考阶段
        mock_websocket_service.send_status_message.assert_called()
    
    @pytest.mark.asyncio
    @patch('src.services.chat_orchestrator.get_websocket_stream_service')
    async def test_error_handling_max_errors(self, mock_websocket, chat_orchestrator):
        """测试错误处理 - 达到最大错误次数"""
        mock_websocket_service = AsyncMock()
        mock_websocket_service.send_error_message = AsyncMock(return_value=True)
        mock_websocket.return_value = mock_websocket_service
        
        # 替换实例中的websocket服务
        chat_orchestrator.websocket_service = mock_websocket_service
        
        context = chat_orchestrator.get_or_create_context("test_session")
        
        # 模拟达到最大错误次数
        for i in range(chat_orchestrator.max_error_count):
            context.add_error(f"错误 {i+1}")
        
        result = await chat_orchestrator._handle_pipeline_error(context, "测试阶段", "测试错误")
        
        assert result["success"] is False
        assert result["terminated"] is True
        assert "错误次数过多" in result["error"]
        
        # 验证发送了终止消息
        assert mock_websocket_service.send_error_message.call_count == 2  # 阶段错误 + 终止错误


class TestHistoryContextManagement:
    """历史对话上下文管理测试"""
    
    @pytest.mark.asyncio
    async def test_get_history_context_no_history(self, chat_orchestrator):
        """测试无历史对话的情况"""
        context = ChatContext("test_session")
        # 不设置 history_messages
        
        history_context = await chat_orchestrator._get_history_context(context, "当前问题")
        
        assert history_context == ""
    
    @pytest.mark.asyncio
    async def test_get_history_context_below_threshold(self, chat_orchestrator):
        """测试历史对话未超过阈值的情况"""
        context = ChatContext("test_session")
        
        # 使用 ContextManager 添加历史消息
        chat_orchestrator.context_manager.add_user_message("test_session", "查询产品信息")
        chat_orchestrator.context_manager.add_sql_response("test_session", "SELECT * FROM products")
        chat_orchestrator.context_manager.add_user_message("test_session", "显示前10条")
        
        history_context = await chat_orchestrator._get_history_context(context, "当前问题")
        
        # 验证返回完整历史对话
        assert "历史对话上下文（完整对话" in history_context
        assert "用户: 查询产品信息" in history_context
        assert "AI助手: SELECT * FROM products" in history_context
        assert "用户: 显示前10条" in history_context
    
    @pytest.mark.asyncio
    @patch.object(ChatOrchestrator, '_summarize_history_context')
    async def test_get_history_context_above_threshold(self, mock_summarize, chat_orchestrator):
        """测试历史对话超过阈值的情况"""
        context = ChatContext("test_session")
        
        # 使用 ContextManager 创建大量历史消息以超过阈值
        for i in range(100):
            chat_orchestrator.context_manager.add_user_message(
                "test_session",
                "这是一个比较长的用户问题，包含了很多详细的描述和要求" * 5
            )
            chat_orchestrator.context_manager.add_analysis_response(
                "test_session",
                "这是一个详细的 AI 回复，包含了完整的分析和建议" * 5
            )
        
        # 模拟摘要结果
        mock_summarize.return_value = "\n\n历史对话上下文：\n【早期对话摘要】\n摘要内容\n【最近对话】\n最近对话内容"
        
        history_context = await chat_orchestrator._get_history_context(context, "当前问题")
        
        # 验证调用了摘要方法
        mock_summarize.assert_called_once()
        
        # 验证返回摘要结果
        assert "早期对话摘要" in history_context
        assert "最近对话" in history_context
    
    @pytest.mark.asyncio
    async def test_format_full_history(self, chat_orchestrator):
        """测试格式化完整历史对话"""
        history_messages = [
            {"role": "user", "content": "第一个问题"},
            {"role": "assistant", "content": "第一个回答"},
            {"role": "user", "content": "第二个问题"}
        ]
        
        formatted = chat_orchestrator._format_full_history(history_messages)
        
        assert "历史对话上下文（完整对话" in formatted
        assert "用户: 第一个问题" in formatted
        assert "AI助手: 第一个回答" in formatted
        assert "用户: 第二个问题" in formatted
    
    @pytest.mark.asyncio
    async def test_format_full_history_empty(self, chat_orchestrator):
        """测试格式化空历史对话"""
        formatted = chat_orchestrator._format_full_history([])
        assert formatted == ""
    
    @pytest.mark.asyncio
    async def test_format_messages_for_summary(self, chat_orchestrator):
        """测试格式化消息用于摘要"""
        messages = [
            {"role": "user", "content": "短消息"},
            {"role": "assistant", "content": "这是一个非常长的消息" + "x" * 600}  # 超过500字符
        ]
        
        formatted = chat_orchestrator._format_messages_for_summary(messages)
        
        assert "用户: 短消息" in formatted
        assert "AI助手:" in formatted
        # 验证长消息被截断
        assert "..." in formatted
        assert len(formatted) < len(messages[1]["content"])
    
    @pytest.mark.asyncio
    async def test_summarize_history_context_short_history(self, chat_orchestrator):
        """测试摘要短历史对话（不需要摘要）"""
        # 少于6条消息，不需要摘要
        history_messages = [
            {"role": "user", "content": "问题1"},
            {"role": "assistant", "content": "回答1"},
            {"role": "user", "content": "问题2"},
            {"role": "assistant", "content": "回答2"}
        ]
        
        result = await chat_orchestrator._summarize_history_context(history_messages, "当前问题")
        
        # 验证返回完整对话（不调用AI摘要）
        assert "历史对话上下文（完整对话）" in result
        assert "用户: 问题1" in result
        assert "AI助手: 回答1" in result
    
    @pytest.mark.asyncio
    async def test_summarize_history_context_long_history(self, chat_orchestrator):
        """测试摘要长历史对话"""
        # 创建10轮对话（20条消息）
        history_messages = []
        for i in range(10):
            history_messages.append({"role": "user", "content": f"用户问题 {i+1}"})
            history_messages.append({"role": "assistant", "content": f"AI回答 {i+1}"})
        
        # Mock AI service
        mock_ai_service = AsyncMock()
        mock_ai_service.call_local_model = AsyncMock(return_value={
            "success": True,
            "content": "这是早期对话的摘要内容"
        })
        chat_orchestrator.ai_service = mock_ai_service
        
        result = await chat_orchestrator._summarize_history_context(history_messages, "当前问题")
        
        # 验证包含摘要和最近对话
        assert "早期对话摘要" in result
        assert "最近对话" in result
        assert "这是早期对话的摘要内容" in result
        
        # 验证最近3轮对话（6条消息）被完整保留
        assert "用户问题 8" in result  # 第8轮
        assert "用户问题 9" in result  # 第9轮
        assert "用户问题 10" in result  # 第10轮
        
        # 验证早期对话不在完整对话中
        assert "用户问题 1" not in result or "早期对话摘要" in result
    
    @pytest.mark.asyncio
    async def test_summarize_history_context_ai_failure(self, chat_orchestrator):
        """测试AI摘要失败的降级处理"""
        # 创建10轮对话
        history_messages = []
        for i in range(10):
            history_messages.append({"role": "user", "content": f"用户问题 {i+1}"})
            history_messages.append({"role": "assistant", "content": f"AI回答 {i+1}"})
        
        # Mock AI service 返回失败
        mock_ai_service = AsyncMock()
        mock_ai_service.call_local_model = AsyncMock(return_value={
            "success": False,
            "error": "AI服务不可用"
        })
        chat_orchestrator.ai_service = mock_ai_service
        
        result = await chat_orchestrator._summarize_history_context(history_messages, "当前问题")
        
        # 验证降级处理：使用简化的早期对话
        assert "早期对话摘要" in result
        assert "最近对话" in result
        
        # 验证最近对话仍然完整保留
        assert "用户问题 10" in result
    
    @pytest.mark.asyncio
    async def test_token_threshold_boundary(self, chat_orchestrator):
        """测试Token阈值边界情况"""
        context = ChatContext("test_session")
        
        # 使用 ContextManager 创建恰好接近阈值的历史消息
        # 假设每条消息约20 tokens，需要约100条消息达到2000 tokens
        for i in range(95):  # 略低于阈值
            chat_orchestrator.context_manager.add_user_message(
                "test_session",
                f"问题 {i+1}"
            )
            chat_orchestrator.context_manager.add_analysis_response(
                "test_session",
                f"回答 {i+1}"
            )
        
        # 获取历史消息用于计算Token
        cloud_history = chat_orchestrator.context_manager.get_cloud_history("test_session", max_messages=200)
        history_messages = [
            {"role": msg["role"], "content": msg["content"]}
            for msg in cloud_history
        ]
        
        # 计算实际Token数
        total_tokens = chat_orchestrator._calculate_history_tokens(history_messages)
        
        # 验证Token计算
        assert total_tokens > 0
        
        # 如果低于阈值，应该返回完整历史
        if total_tokens < 2000:
            history_context = await chat_orchestrator._get_history_context(context, "当前问题")
            assert "历史对话上下文（完整对话" in history_context