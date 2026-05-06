"""
意图澄清服务单元测试
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from src.services.intent_clarification_service import (
    IntentClarificationService,
    ClarificationQuestion,
    ClarificationResult,
    ClarificationSession
)


@pytest.fixture
def mock_ai_service():
    """Mock AI模型服务"""
    service = Mock()
    service.generate = AsyncMock()
    return service


@pytest.fixture
def mock_prompt_manager():
    """Mock Prompt管理器"""
    manager = Mock()
    manager.get_prompt = Mock(return_value="test prompt")
    return manager


@pytest.fixture
def clarification_service(mock_ai_service, mock_prompt_manager):
    """创建意图澄清服务实例"""
    return IntentClarificationService(
        ai_model_service=mock_ai_service,
        prompt_manager=mock_prompt_manager
    )


@pytest.fixture
def sample_table_selection():
    """示例表选择结果"""
    return {
        "selected_tables": [
            {
                "table_id": "table1",
                "table_name": "sales",
                "relevance_score": 0.9,
                "reasoning": "包含销售相关字段",
                "relevant_fields": ["amount", "date", "product"]
            }
        ],
        "overall_reasoning": "选择了销售表"
    }


class TestClarificationGeneration:
    """测试澄清问题生成"""
    
    @pytest.mark.asyncio
    async def test_generate_clarification_with_ai_model(
        self, clarification_service, mock_ai_service, sample_table_selection
    ):
        """测试使用AI模型生成澄清问题"""
        # 准备AI响应
        ai_response = """
        {
            "clarification_needed": true,
            "questions": [
                {
                    "question": "请确认时间范围",
                    "options": ["今天", "本周", "本月"],
                    "question_type": "single_choice",
                    "reasoning": "问题中未明确时间范围",
                    "importance": 0.8
                }
            ],
            "summary": "理解您想查询销售数据",
            "confidence": 0.85,
            "reasoning": "需要确认时间范围"
        }
        """
        mock_ai_service.generate.return_value = ai_response
        
        # 执行
        result = await clarification_service.generate_clarification(
            original_question="查询销售数据",
            table_selection=sample_table_selection
        )
        
        # 验证
        assert isinstance(result, ClarificationResult)
        assert result.clarification_needed is True
        assert len(result.questions) == 1
        assert result.questions[0].question == "请确认时间范围"
        assert result.questions[0].question_type == "single_choice"
        assert result.confidence == 0.85
        
        # 验证AI服务被调用
        mock_ai_service.generate.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_generate_clarification_without_ai_model(self, sample_table_selection):
        """测试无AI模型时使用规则生成澄清问题"""
        service = IntentClarificationService(ai_model_service=None)
        
        result = await service.generate_clarification(
            original_question="查询最近的销售数据",
            table_selection=sample_table_selection
        )
        
        assert isinstance(result, ClarificationResult)
        assert result.clarification_needed is True
        assert len(result.questions) > 0
        assert result.reasoning == "基于规则生成的澄清问题"
    
    @pytest.mark.asyncio
    async def test_generate_clarification_no_clarification_needed(
        self, clarification_service, mock_ai_service, sample_table_selection
    ):
        """测试不需要澄清的情况"""
        ai_response = """
        {
            "clarification_needed": false,
            "questions": [],
            "summary": "理解您想查询销售数据",
            "confidence": 0.95,
            "reasoning": "问题明确，无需澄清"
        }
        """
        mock_ai_service.generate.return_value = ai_response
        
        result = await clarification_service.generate_clarification(
            original_question="查询2024年1月的销售总额",
            table_selection=sample_table_selection
        )
        
        assert result.clarification_needed is False
        assert len(result.questions) == 0
        assert result.confidence == 0.95
    
    @pytest.mark.asyncio
    async def test_generate_clarification_with_context(
        self, clarification_service, mock_ai_service, sample_table_selection
    ):
        """测试带额外上下文的澄清生成"""
        ai_response = '{"clarification_needed": false, "questions": [], "summary": "test", "confidence": 0.9, "reasoning": "test"}'
        mock_ai_service.generate.return_value = ai_response
        
        context = {"user_preference": "monthly_report"}
        
        result = await clarification_service.generate_clarification(
            original_question="查询销售数据",
            table_selection=sample_table_selection,
            context=context
        )
        
        assert isinstance(result, ClarificationResult)
    
    @pytest.mark.asyncio
    async def test_generate_clarification_ai_error_handling(
        self, clarification_service, mock_ai_service, sample_table_selection
    ):
        """测试AI服务错误处理"""
        mock_ai_service.generate.side_effect = Exception("AI service error")
        
        result = await clarification_service.generate_clarification(
            original_question="查询销售数据",
            table_selection=sample_table_selection
        )
        
        # 应该返回默认结果而不是抛出异常
        assert isinstance(result, ClarificationResult)
        assert result.clarification_needed is False
        assert "生成澄清问题时出错" in result.reasoning


class TestRuleBasedClarification:
    """测试基于规则的澄清生成"""
    
    @pytest.mark.asyncio
    async def test_rule_based_multiple_tables(self, sample_table_selection):
        """测试多表情况的规则生成"""
        service = IntentClarificationService(ai_model_service=None)
        
        # 添加多个表
        sample_table_selection["selected_tables"].append({
            "table_name": "orders",
            "relevance_score": 0.8,
            "reasoning": "包含订单相关字段"
        })
        
        result = await service.generate_clarification(
            original_question="查询数据",
            table_selection=sample_table_selection
        )
        
        assert result.clarification_needed is True
        # 应该有关于表选择的问题
        table_questions = [q for q in result.questions if "表" in q.question]
        assert len(table_questions) > 0
    
    @pytest.mark.asyncio
    async def test_rule_based_time_keywords(self, sample_table_selection):
        """测试时间关键词的规则生成"""
        service = IntentClarificationService(ai_model_service=None)
        
        result = await service.generate_clarification(
            original_question="查询最近的销售数据",
            table_selection=sample_table_selection
        )
        
        assert result.clarification_needed is True
        # 应该有关于时间范围的问题
        time_questions = [q for q in result.questions if "时间" in q.question]
        assert len(time_questions) > 0
    
    @pytest.mark.asyncio
    async def test_rule_based_aggregation_keywords(self, sample_table_selection):
        """测试聚合关键词的规则生成"""
        service = IntentClarificationService(ai_model_service=None)
        
        result = await service.generate_clarification(
            original_question="查询销售总额",
            table_selection=sample_table_selection
        )
        
        assert result.clarification_needed is True
        # 应该有关于统计方式的问题
        agg_questions = [q for q in result.questions if "统计" in q.question]
        assert len(agg_questions) > 0


class TestSessionManagement:
    """测试会话管理"""
    
    def test_create_session(self, clarification_service, sample_table_selection):
        """测试创建澄清会话"""
        clarification_result = ClarificationResult(
            clarification_needed=True,
            questions=[],
            summary="test",
            confidence=0.8,
            reasoning="test"
        )
        
        session = clarification_service.create_session(
            session_id="test_session",
            original_question="查询销售数据",
            table_selection=sample_table_selection,
            clarification_result=clarification_result
        )
        
        assert isinstance(session, ClarificationSession)
        assert session.session_id == "test_session"
        assert session.original_question == "查询销售数据"
        assert session.status == "pending"
        assert session.clarification_result == clarification_result
    
    def test_confirm_clarification(self, clarification_service, sample_table_selection):
        """测试确认澄清"""
        # 先创建会话
        clarification_result = ClarificationResult(
            clarification_needed=True,
            questions=[],
            summary="test",
            confidence=0.8,
            reasoning="test"
        )
        
        clarification_service.create_session(
            session_id="test_session",
            original_question="查询销售数据",
            table_selection=sample_table_selection,
            clarification_result=clarification_result
        )
        
        # 确认澄清
        user_responses = [{"question_index": 0, "answer": "本月"}]
        result = clarification_service.confirm_clarification(
            session_id="test_session",
            user_responses=user_responses
        )
        
        assert result["session_id"] == "test_session"
        assert result["status"] == "confirmed"
        assert result["responses"] == user_responses
        
        # 验证会话状态更新
        session = clarification_service.get_session("test_session")
        assert session.status == "confirmed"
        assert session.user_responses == user_responses
    
    def test_confirm_clarification_session_not_found(self, clarification_service):
        """测试确认不存在的会话"""
        with pytest.raises(ValueError, match="Session not found"):
            clarification_service.confirm_clarification(
                session_id="nonexistent",
                user_responses=[]
            )
    
    def test_modify_clarification(self, clarification_service, sample_table_selection):
        """测试修改澄清"""
        # 先创建会话
        clarification_result = ClarificationResult(
            clarification_needed=True,
            questions=[],
            summary="test",
            confidence=0.8,
            reasoning="test"
        )
        
        clarification_service.create_session(
            session_id="test_session",
            original_question="查询销售数据",
            table_selection=sample_table_selection,
            clarification_result=clarification_result
        )
        
        # 修改澄清
        modifications = {"time_range": "本季度"}
        result = clarification_service.modify_clarification(
            session_id="test_session",
            modifications=modifications
        )
        
        assert result["session_id"] == "test_session"
        assert result["status"] == "modified"
        assert result["modifications"] == modifications
        
        # 验证会话状态更新
        session = clarification_service.get_session("test_session")
        assert session.status == "modified"
        assert len(session.user_responses) > 0
    
    def test_modify_clarification_session_not_found(self, clarification_service):
        """测试修改不存在的会话"""
        with pytest.raises(ValueError, match="Session not found"):
            clarification_service.modify_clarification(
                session_id="nonexistent",
                modifications={}
            )
    
    def test_get_session(self, clarification_service, sample_table_selection):
        """测试获取会话"""
        clarification_result = ClarificationResult(
            clarification_needed=True,
            questions=[],
            summary="test",
            confidence=0.8,
            reasoning="test"
        )
        
        clarification_service.create_session(
            session_id="test_session",
            original_question="查询销售数据",
            table_selection=sample_table_selection,
            clarification_result=clarification_result
        )
        
        session = clarification_service.get_session("test_session")
        
        assert session is not None
        assert session.session_id == "test_session"
    
    def test_get_session_not_found(self, clarification_service):
        """测试获取不存在的会话"""
        session = clarification_service.get_session("nonexistent")
        assert session is None
    
    def test_get_session_history(self, clarification_service, sample_table_selection):
        """测试获取会话历史"""
        clarification_result = ClarificationResult(
            clarification_needed=True,
            questions=[
                ClarificationQuestion(
                    question="测试问题",
                    options=["选项1", "选项2"],
                    question_type="single_choice"
                )
            ],
            summary="test",
            confidence=0.8,
            reasoning="test"
        )
        
        clarification_service.create_session(
            session_id="test_session",
            original_question="查询销售数据",
            table_selection=sample_table_selection,
            clarification_result=clarification_result
        )
        
        history = clarification_service.get_session_history("test_session")
        
        assert len(history) == 1
        assert history[0]["original_question"] == "查询销售数据"
        assert history[0]["status"] == "pending"
        assert len(history[0]["clarification_result"]["questions"]) == 1
    
    def test_get_session_history_not_found(self, clarification_service):
        """测试获取不存在会话的历史"""
        history = clarification_service.get_session_history("nonexistent")
        assert history == []


class TestStatistics:
    """测试统计功能"""
    
    @pytest.mark.asyncio
    async def test_statistics_update(
        self, clarification_service, mock_ai_service, sample_table_selection
    ):
        """测试统计信息更新"""
        ai_response = '{"clarification_needed": true, "questions": [{"question": "test", "options": [], "question_type": "text_input", "reasoning": "", "importance": 0.5}], "summary": "test", "confidence": 0.8, "reasoning": "test"}'
        mock_ai_service.generate.return_value = ai_response
        
        # 生成澄清
        await clarification_service.generate_clarification(
            original_question="查询销售数据",
            table_selection=sample_table_selection
        )
        
        stats = clarification_service.get_statistics()
        
        assert stats["total_clarifications"] == 1
        assert stats["clarification_needed_count"] == 1
        assert stats["avg_questions_per_clarification"] == 1.0
        assert stats["avg_response_time_ms"] > 0
    
    def test_get_statistics_initial(self, clarification_service):
        """测试初始统计信息"""
        stats = clarification_service.get_statistics()
        
        assert stats["total_clarifications"] == 0
        assert stats["clarification_needed_count"] == 0
        assert stats["user_confirmed_count"] == 0
        assert stats["user_modified_count"] == 0
        assert stats["active_sessions"] == 0
        assert stats["clarification_rate"] == 0.0
        assert stats["confirmation_rate"] == 0.0
    
    def test_statistics_rates_calculation(
        self, clarification_service, sample_table_selection
    ):
        """测试统计率计算"""
        # 创建并确认会话
        clarification_result = ClarificationResult(
            clarification_needed=True,
            questions=[],
            summary="test",
            confidence=0.8,
            reasoning="test"
        )
        
        clarification_service.create_session(
            session_id="test_session",
            original_question="查询销售数据",
            table_selection=sample_table_selection,
            clarification_result=clarification_result
        )
        
        clarification_service.confirm_clarification(
            session_id="test_session",
            user_responses=[]
        )
        
        # 手动更新统计
        clarification_service.stats["total_clarifications"] = 1
        clarification_service.stats["clarification_needed_count"] = 1
        
        stats = clarification_service.get_statistics()
        
        assert stats["clarification_rate"] == 1.0
        assert stats["confirmation_rate"] == 1.0


class TestPromptBuilding:
    """测试Prompt构建"""
    
    def test_build_clarification_prompt_with_prompt_manager(
        self, clarification_service, mock_prompt_manager, sample_table_selection
    ):
        """测试使用Prompt管理器构建prompt"""
        prompt = clarification_service._build_clarification_prompt(
            original_question="查询销售数据",
            table_selection=sample_table_selection,
            context={}
        )
        
        # 验证prompt管理器被调用
        mock_prompt_manager.get_prompt.assert_called_once()
        assert prompt == "test prompt"
    
    def test_build_clarification_prompt_without_prompt_manager(
        self, sample_table_selection
    ):
        """测试无Prompt管理器时构建prompt"""
        service = IntentClarificationService(
            ai_model_service=None,
            prompt_manager=None
        )
        
        prompt = service._build_clarification_prompt(
            original_question="查询销售数据",
            table_selection=sample_table_selection,
            context={}
        )
        
        # 验证prompt包含关键信息
        assert "查询销售数据" in prompt
        assert "sales" in prompt
        assert "JSON" in prompt
    
    def test_format_selected_tables(self, clarification_service, sample_table_selection):
        """测试格式化选中的表信息"""
        formatted = clarification_service._format_selected_tables(sample_table_selection)
        
        assert "sales" in formatted
        assert "amount" in formatted
        assert "包含销售相关字段" in formatted
    
    def test_format_selected_tables_empty(self, clarification_service):
        """测试格式化空表选择"""
        formatted = clarification_service._format_selected_tables({})
        assert formatted == "无选中的表"


class TestResponseParsing:
    """测试响应解析"""
    
    def test_parse_clarification_response_valid_json(self, clarification_service):
        """测试解析有效的JSON响应"""
        response = """
        {
            "clarification_needed": true,
            "questions": [
                {
                    "question": "测试问题",
                    "options": ["选项1", "选项2"],
                    "question_type": "single_choice",
                    "reasoning": "测试理由",
                    "importance": 0.8
                }
            ],
            "summary": "测试总结",
            "confidence": 0.9,
            "reasoning": "测试推理"
        }
        """
        
        result = clarification_service._parse_clarification_response(response)
        
        assert result.clarification_needed is True
        assert len(result.questions) == 1
        assert result.questions[0].question == "测试问题"
        assert result.questions[0].importance == 0.8
        assert result.confidence == 0.9
    
    def test_parse_clarification_response_with_extra_text(self, clarification_service):
        """测试解析带额外文本的响应"""
        response = """
        这是一些额外的文本
        {
            "clarification_needed": false,
            "questions": [],
            "summary": "测试",
            "confidence": 0.8,
            "reasoning": "测试"
        }
        还有一些文本
        """
        
        result = clarification_service._parse_clarification_response(response)
        
        assert result.clarification_needed is False
        assert len(result.questions) == 0
    
    def test_parse_clarification_response_invalid_json(self, clarification_service):
        """测试解析无效JSON"""
        response = "这不是有效的JSON"
        
        result = clarification_service._parse_clarification_response(response)
        
        # 应该返回默认结果
        assert result.clarification_needed is False
        assert len(result.questions) == 0
        assert result.confidence == 0.0
        assert "解析错误" in result.reasoning
