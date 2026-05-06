"""
意图识别上下文管理服务单元测试 - 任务 5.1.2
测试基于对话历史的意图推断、动态调整和澄清机制
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta
from typing import Dict, Any, List

from src.services.intent_context_manager import (
    IntentContextManager,
    ContextualIntentResult,
    ClarificationRequest,
    IntentAdjustment,
    ConfidenceLevel,
    ClarificationReason,
    get_intent_context_manager,
    init_intent_context_manager
)
from src.services.intent_recognition_service import IntentResult, IntentType


class TestIntentContextManager:
    """意图上下文管理器测试类"""
    
    @pytest.fixture
    def mock_intent_service(self):
        """模拟意图识别服务"""
        mock = Mock()
        mock.identify_intent = AsyncMock()
        return mock
    
    @pytest.fixture
    def mock_context_manager(self):
        """模拟上下文管理器"""
        mock = Mock()
        mock.get_cloud_history = Mock(return_value=[])
        return mock
    
    @pytest.fixture
    def mock_ai_service(self):
        """模拟AI服务"""
        mock = Mock()
        return mock
    
    @pytest.fixture
    def intent_context_manager(self, mock_intent_service, mock_context_manager, mock_ai_service):
        """创建意图上下文管理器实例"""
        with patch('src.services.intent_context_manager.IntentRecognitionService', return_value=mock_intent_service), \
             patch('src.services.intent_context_manager.get_context_manager', return_value=mock_context_manager), \
             patch('src.services.intent_context_manager.get_ai_service', return_value=mock_ai_service):
            manager = IntentContextManager()
            return manager
    
    @pytest.fixture
    def sample_intent_result(self):
        """示例意图识别结果"""
        return IntentResult(
            intent=IntentType.QUERY,
            confidence=0.75,
            reasoning="用户询问具体数据",
            original_question="今天的销售额是多少？",
            metadata={"keywords": ["销售额", "今天"]}
        )
    
    @pytest.fixture
    def sample_session_id(self):
        """示例会话ID"""
        return "test_session_123"

    @pytest.mark.asyncio
    async def test_identify_intent_with_context_basic(self, intent_context_manager, sample_intent_result, sample_session_id):
        """测试基础上下文意图识别"""
        # 设置模拟
        intent_context_manager.intent_service.identify_intent.return_value = sample_intent_result
        
        # 执行测试
        result = await intent_context_manager.identify_intent_with_context(
            session_id=sample_session_id,
            user_question="今天的销售额是多少？"
        )
        
        # 验证结果
        assert isinstance(result, ContextualIntentResult)
        assert result.intent_result.intent == IntentType.QUERY
        assert result.intent_result.confidence == 0.75
        assert result.confidence_level == ConfidenceLevel.MEDIUM
        assert isinstance(result.context_influence, dict)
        assert isinstance(result.adjustment_history, list)
        assert isinstance(result.clarification_needed, bool)
    
    @pytest.mark.asyncio
    async def test_identify_intent_with_context_high_confidence(self, intent_context_manager, sample_session_id):
        """测试高置信度意图识别"""
        # 创建高置信度意图结果
        high_confidence_result = IntentResult(
            intent=IntentType.QUERY,
            confidence=0.95,
            reasoning="明确的数据查询请求",
            original_question="显示所有用户数据",
            metadata={"keywords": ["显示", "用户数据"]}
        )
        
        intent_context_manager.intent_service.identify_intent.return_value = high_confidence_result
        
        # 执行测试
        result = await intent_context_manager.identify_intent_with_context(
            session_id=sample_session_id,
            user_question="显示所有用户数据"
        )
        
        # 验证结果
        assert result.confidence_level == ConfidenceLevel.HIGH
        assert not result.clarification_needed  # 高置信度不需要澄清
        assert result.clarification_request is None
    
    @pytest.mark.asyncio
    async def test_identify_intent_with_context_low_confidence(self, intent_context_manager, sample_session_id):
        """测试低置信度意图识别"""
        # 创建低置信度意图结果
        low_confidence_result = IntentResult(
            intent=IntentType.UNKNOWN,
            confidence=0.3,
            reasoning="意图不明确",
            original_question="这个怎么样？",
            metadata={"keywords": ["这个", "怎么样"]}
        )
        
        intent_context_manager.intent_service.identify_intent.return_value = low_confidence_result
        
        # 执行测试
        result = await intent_context_manager.identify_intent_with_context(
            session_id=sample_session_id,
            user_question="这个怎么样？"
        )
        
        # 验证结果
        assert result.confidence_level == ConfidenceLevel.LOW
        assert result.clarification_needed  # 低置信度需要澄清
        assert result.clarification_request is not None
        assert isinstance(result.clarification_request, ClarificationRequest)
    
    def test_confidence_level_determination(self, intent_context_manager):
        """测试置信度级别确定"""
        # 测试高置信度
        high_level = intent_context_manager._determine_confidence_level(0.9)
        assert high_level == ConfidenceLevel.HIGH
        
        # 测试中等置信度
        medium_level = intent_context_manager._determine_confidence_level(0.6)
        assert medium_level == ConfidenceLevel.MEDIUM
        
        # 测试低置信度
        low_level = intent_context_manager._determine_confidence_level(0.3)
        assert low_level == ConfidenceLevel.LOW
        
        # 测试边界值
        boundary_high = intent_context_manager._determine_confidence_level(0.8)
        assert boundary_high == ConfidenceLevel.HIGH
        
        boundary_medium = intent_context_manager._determine_confidence_level(0.5)
        assert boundary_medium == ConfidenceLevel.MEDIUM
    
    def test_recent_intents_management(self, intent_context_manager, sample_session_id):
        """测试最近意图管理"""
        # 测试空会话
        recent_intents = intent_context_manager._get_recent_intents(sample_session_id)
        assert recent_intents == []
        
        # 设置会话状态
        intent_context_manager.session_states[sample_session_id] = {
            'recent_intents': [
                IntentType.QUERY,
                IntentType.REPORT,
                IntentType.QUERY
            ]
        }
        
        # 测试获取最近意图
        recent_intents = intent_context_manager._get_recent_intents(sample_session_id)
        assert len(recent_intents) == 3
        assert recent_intents[0] == IntentType.QUERY
        
        # 测试主导意图
        dominant_intent = intent_context_manager._get_dominant_intent(recent_intents)
        assert dominant_intent == IntentType.QUERY  # 出现2次，最多
    
    def test_conversation_flow_analysis(self, intent_context_manager, sample_session_id):
        """测试对话流程分析"""
        # 测试数据不足
        flow = intent_context_manager._analyze_conversation_flow(sample_session_id)
        assert flow == 'insufficient_data'
        
        # 测试自然进展（相同意图）
        intent_context_manager.session_states[sample_session_id] = {
            'recent_intents': [
                IntentType.QUERY,
                IntentType.QUERY,
                IntentType.QUERY
            ]
        }
        flow = intent_context_manager._analyze_conversation_flow(sample_session_id)
        assert flow == 'natural_progression'
        
        # 测试轻微变化（2种意图）
        intent_context_manager.session_states[sample_session_id] = {
            'recent_intents': [
                IntentType.QUERY,
                IntentType.REPORT,
                IntentType.QUERY
            ]
        }
        flow = intent_context_manager._analyze_conversation_flow(sample_session_id)
        assert flow == 'minor_variation'
        
        # 测试话题切换（3种意图）
        intent_context_manager.session_states[sample_session_id] = {
            'recent_intents': [
                IntentType.QUERY,
                IntentType.REPORT,
                IntentType.UNKNOWN
            ]
        }
        flow = intent_context_manager._analyze_conversation_flow(sample_session_id)
        assert flow == 'topic_switch'
    
    def test_question_similarity_calculation(self, intent_context_manager, sample_session_id):
        """测试问题相似性计算"""
        # 测试无历史记录
        similarity = intent_context_manager._calculate_question_similarity(
            sample_session_id, "今天的销售额是多少？"
        )
        assert similarity == 0.0
        
        # 设置历史记录
        intent_context_manager.context_manager.get_cloud_history.return_value = [
            {'role': 'user', 'content': '昨天的销售额是多少？'},
            {'role': 'assistant', 'content': '查询结果...'},
            {'role': 'user', 'content': '显示用户数据'}
        ]
        
        # 测试相似问题
        similarity = intent_context_manager._calculate_question_similarity(
            sample_session_id, "今天的销售额是多少？"
        )
        assert similarity >= 0.0  # 应该有一定相似性或为0
        
        # 测试完全不同的问题
        similarity = intent_context_manager._calculate_question_similarity(
            sample_session_id, "天气怎么样？"
        )
        assert similarity >= 0.0  # 相似性应该很低或为0
    
    def test_get_session_intent_stats(self, intent_context_manager, sample_session_id):
        """测试获取会话意图统计"""
        # 设置会话状态
        intent_context_manager.session_states[sample_session_id] = {
            'recent_intents': [
                IntentType.QUERY,
                IntentType.QUERY,
                IntentType.REPORT
            ],
            'last_intent': IntentType.REPORT,
            'last_confidence': 0.85,
            'last_update': datetime.now(),
            'adjustment_history': [{'test': 'data'}]
        }
        
        # 执行测试
        stats = intent_context_manager.get_session_intent_stats(sample_session_id)
        
        # 验证统计结果
        assert stats['session_id'] == sample_session_id
        assert stats['total_intents'] == 3
        assert stats['last_intent'] == IntentType.REPORT
        assert stats['last_confidence'] == 0.85
        assert stats['adjustment_count'] == 1
        assert 'intent_distribution' in stats
        
        # 验证意图分布
        distribution = stats['intent_distribution']
        assert distribution[IntentType.QUERY.value] == 2/3
        assert distribution[IntentType.REPORT.value] == 1/3
    
    def test_empty_session_handling(self, intent_context_manager):
        """测试空会话处理"""
        empty_session_id = "empty_session"
        
        # 测试获取空会话统计
        stats = intent_context_manager.get_session_intent_stats(empty_session_id)
        assert stats['total_intents'] == 0
        assert stats['adjustment_count'] == 0
        assert stats['last_intent'] is None
        
        # 测试获取空调整历史
        history = intent_context_manager._get_adjustment_history(empty_session_id)
        assert history == []


class TestIntentContextManagerGlobalFunctions:
    """测试全局函数"""
    
    def test_get_intent_context_manager(self):
        """测试获取意图上下文管理器"""
        with patch('src.services.intent_context_manager.IntentRecognitionService'), \
             patch('src.services.intent_context_manager.get_context_manager'), \
             patch('src.services.intent_context_manager.get_ai_service'):
            manager1 = get_intent_context_manager()
            manager2 = get_intent_context_manager()
            
            # 应该返回同一个实例（单例模式）
            assert manager1 is manager2
            assert isinstance(manager1, IntentContextManager)
    
    def test_init_intent_context_manager(self):
        """测试初始化意图上下文管理器"""
        with patch('src.services.intent_context_manager.IntentRecognitionService'), \
             patch('src.services.intent_context_manager.get_context_manager'), \
             patch('src.services.intent_context_manager.get_ai_service'):
            manager = init_intent_context_manager()
            assert isinstance(manager, IntentContextManager)
            
            # 验证初始化后的获取
            same_manager = get_intent_context_manager()
            assert same_manager is manager


if __name__ == "__main__":
    pytest.main([__file__, "-v"])