"""
意图澄清结果处理和意图更新测试

测试Task 5.3.2的功能：
- 用户澄清反馈的结构化处理
- 澄清结果对原始意图的动态更新
- 澄清历史的记录和回溯机制
- 澄清效果的评估和优化策略
"""

import pytest
from datetime import datetime
from src.services.intent_clarification_service import (
    IntentClarificationService,
    ClarificationResult,
    ClarificationQuestion,
    ClarificationStatus,
    IntentUpdateType
)


@pytest.fixture
def service():
    """创建意图澄清服务实例"""
    return IntentClarificationService()


@pytest.fixture
def sample_session(service):
    """创建示例会话"""
    session_id = "test_session_001"
    original_question = "查询销售数据"
    table_selection = {
        "selected_tables": [
            {"table_name": "sales", "relevance_score": 0.9},
            {"table_name": "products", "relevance_score": 0.7}
        ]
    }
    
    clarification_result = ClarificationResult(
        clarification_needed=True,
        questions=[
            ClarificationQuestion(
                question="请确认时间范围",
                options=["今天", "本周", "本月"],
                question_type="single_choice",
                reasoning="需要明确查询的时间范围",
                importance=0.8
            ),
            ClarificationQuestion(
                question="请选择要查询的表",
                options=["sales", "products"],
                question_type="multiple_choice",
                reasoning="有多个相关表",
                importance=0.9
            )
        ],
        summary="理解您想查询销售数据",
        confidence=0.8,
        reasoning="需要澄清时间范围和表选择"
    )
    
    session = service.create_session(
        session_id=session_id,
        original_question=original_question,
        table_selection=table_selection,
        clarification_result=clarification_result
    )
    
    return session


class TestClarificationFeedbackProcessing:
    """测试澄清反馈处理"""
    
    def test_process_single_feedback(self, service, sample_session):
        """测试处理单个反馈"""
        user_feedbacks = [
            {
                "response": "本月",
                "type": "single_choice",
                "confidence": 1.0
            }
        ]
        
        feedbacks, intent_updates = service.process_clarification_feedback(
            session_id=sample_session.session_id,
            user_feedbacks=user_feedbacks
        )
        
        assert len(feedbacks) == 1
        assert feedbacks[0].user_response == "本月"
        assert feedbacks[0].response_type == "single_choice"
        assert feedbacks[0].confidence == 1.0
        
        assert len(intent_updates) >= 1
        assert intent_updates[0].update_type == IntentUpdateType.TIME_RANGE
        assert intent_updates[0].updated_value == "本月"
    
    def test_process_multiple_feedbacks(self, service, sample_session):
        """测试处理多个反馈"""
        user_feedbacks = [
            {
                "response": "本月",
                "type": "single_choice",
                "confidence": 1.0
            },
            {
                "response": ["sales", "products"],
                "type": "multiple_choice",
                "confidence": 0.9
            }
        ]
        
        feedbacks, intent_updates = service.process_clarification_feedback(
            session_id=sample_session.session_id,
            user_feedbacks=user_feedbacks
        )
        
        assert len(feedbacks) == 2
        assert len(intent_updates) >= 2
        
        # 验证时间范围更新
        time_updates = [u for u in intent_updates if u.update_type == IntentUpdateType.TIME_RANGE]
        assert len(time_updates) > 0
        assert time_updates[0].updated_value == "本月"
        
        # 验证表选择更新
        table_updates = [u for u in intent_updates if u.update_type == IntentUpdateType.TABLE_SELECTION]
        assert len(table_updates) > 0
        assert table_updates[0].updated_value == ["sales", "products"]
    
    def test_process_feedback_with_session_not_found(self, service):
        """测试处理不存在会话的反馈"""
        with pytest.raises(ValueError, match="Session not found"):
            service.process_clarification_feedback(
                session_id="nonexistent_session",
                user_feedbacks=[]
            )
    
    def test_infer_update_type_from_question(self, service, sample_session):
        """测试从问题推断更新类型"""
        # 时间相关问题
        update_type = service._infer_update_type("请确认时间范围", "本月")
        assert update_type == IntentUpdateType.TIME_RANGE
        
        # 表选择相关问题
        update_type = service._infer_update_type("请选择要查询的表", ["sales"])
        assert update_type == IntentUpdateType.TABLE_SELECTION
        
        # 聚合相关问题
        update_type = service._infer_update_type("请确认统计方式", "求和")
        assert update_type == IntentUpdateType.AGGREGATION
        
        # 字段相关问题
        update_type = service._infer_update_type("请选择字段", ["name", "price"])
        assert update_type == IntentUpdateType.FIELD_SELECTION


class TestIntentUpdate:
    """测试意图更新"""
    
    def test_update_intent_with_time_range(self, service, sample_session):
        """测试更新时间范围意图"""
        user_feedbacks = [
            {
                "response": "本月",
                "type": "single_choice",
                "confidence": 1.0
            }
        ]
        
        _, intent_updates = service.process_clarification_feedback(
            session_id=sample_session.session_id,
            user_feedbacks=user_feedbacks
        )
        
        updated_intent = service.update_intent(
            session_id=sample_session.session_id,
            intent_updates=intent_updates
        )
        
        assert "time_range" in updated_intent
        assert updated_intent["time_range"] == "本月"
    
    def test_update_intent_with_table_selection(self, service, sample_session):
        """测试更新表选择意图"""
        user_feedbacks = [
            {
                "response": ["sales"],
                "type": "multiple_choice",
                "confidence": 1.0
            }
        ]
        
        _, intent_updates = service.process_clarification_feedback(
            session_id=sample_session.session_id,
            user_feedbacks=user_feedbacks
        )
        
        # 手动设置更新类型为表选择
        for update in intent_updates:
            update.update_type = IntentUpdateType.TABLE_SELECTION
        
        updated_intent = service.update_intent(
            session_id=sample_session.session_id,
            intent_updates=intent_updates
        )
        
        assert "selected_tables" in updated_intent
        assert updated_intent["selected_tables"] == ["sales"]
    
    def test_update_intent_with_multiple_updates(self, service, sample_session):
        """测试多个意图更新"""
        user_feedbacks = [
            {
                "response": "本月",
                "type": "single_choice",
                "confidence": 1.0
            },
            {
                "response": ["sales"],
                "type": "multiple_choice",
                "confidence": 0.9
            }
        ]
        
        _, intent_updates = service.process_clarification_feedback(
            session_id=sample_session.session_id,
            user_feedbacks=user_feedbacks
        )
        
        updated_intent = service.update_intent(
            session_id=sample_session.session_id,
            intent_updates=intent_updates
        )
        
        # 验证多个更新都被应用
        assert len(sample_session.intent_updates) >= 2
    
    def test_update_intent_increments_statistics(self, service, sample_session):
        """测试意图更新增加统计计数"""
        initial_count = service.stats["total_intent_updates"]
        
        user_feedbacks = [
            {
                "response": "本月",
                "type": "single_choice",
                "confidence": 1.0
            }
        ]
        
        _, intent_updates = service.process_clarification_feedback(
            session_id=sample_session.session_id,
            user_feedbacks=user_feedbacks
        )
        
        service.update_intent(
            session_id=sample_session.session_id,
            intent_updates=intent_updates
        )
        
        assert service.stats["total_intent_updates"] == initial_count + len(intent_updates)


class TestClarificationHistory:
    """测试澄清历史记录"""
    
    def test_confirm_creates_history_record(self, service, sample_session):
        """测试确认创建历史记录"""
        user_responses = [
            {
                "response": "本月",
                "type": "single_choice",
                "confidence": 1.0
            }
        ]
        
        result = service.confirm_clarification(
            session_id=sample_session.session_id,
            user_responses=user_responses
        )
        
        assert len(sample_session.clarification_history) == 1
        history = sample_session.clarification_history[0]
        
        assert history.session_id == sample_session.session_id
        assert history.round_number == 1
        assert len(history.user_feedbacks) > 0
        assert len(history.intent_updates) > 0
        assert 0.0 <= history.effectiveness_score <= 1.0
    
    def test_get_clarification_history(self, service, sample_session):
        """测试获取澄清历史"""
        # 先确认一次澄清
        user_responses = [
            {
                "response": "本月",
                "type": "single_choice",
                "confidence": 1.0
            }
        ]
        
        service.confirm_clarification(
            session_id=sample_session.session_id,
            user_responses=user_responses
        )
        
        # 获取历史
        history = service.get_clarification_history(sample_session.session_id)
        
        assert len(history) == 1
        assert history[0]["round_number"] == 1
        assert "clarification_result" in history[0]
        assert "user_feedbacks" in history[0]
        assert "intent_updates" in history[0]
        assert "effectiveness_score" in history[0]
    
    def test_multi_round_clarification_history(self, service, sample_session):
        """测试多轮澄清历史"""
        # 第一轮澄清
        user_responses_1 = [
            {
                "response": "本月",
                "type": "single_choice",
                "confidence": 1.0
            }
        ]
        
        service.confirm_clarification(
            session_id=sample_session.session_id,
            user_responses=user_responses_1
        )
        
        # 修改并进入第二轮
        service.modify_clarification(
            session_id=sample_session.session_id,
            modifications={"additional_info": "需要更详细的数据"}
        )
        
        # 第二轮澄清（需要重新生成澄清问题，这里简化处理）
        sample_session.current_round = 2
        
        # 获取历史
        history = service.get_clarification_history(sample_session.session_id)
        
        assert len(history) >= 1
        assert sample_session.current_round == 2


class TestClarificationRollback:
    """测试澄清回溯"""
    
    def test_rollback_to_previous_round(self, service, sample_session):
        """测试回溯到上一轮"""
        # 创建两轮澄清历史
        user_responses_1 = [
            {
                "response": "本月",
                "type": "single_choice",
                "confidence": 1.0
            }
        ]
        
        service.confirm_clarification(
            session_id=sample_session.session_id,
            user_responses=user_responses_1
        )
        
        # 修改进入第二轮
        service.modify_clarification(
            session_id=sample_session.session_id,
            modifications={"change": "需要修改"}
        )
        
        # 回溯到第一轮
        result = service.rollback_to_round(
            session_id=sample_session.session_id,
            round_number=1
        )
        
        assert result["round_number"] == 1
        assert sample_session.current_round == 1
        assert len(sample_session.clarification_history) == 1
    
    def test_rollback_with_invalid_round_number(self, service, sample_session):
        """测试无效轮次的回溯"""
        with pytest.raises(ValueError, match="Invalid round number"):
            service.rollback_to_round(
                session_id=sample_session.session_id,
                round_number=99
            )
    
    def test_rollback_with_nonexistent_session(self, service):
        """测试不存在会话的回溯"""
        with pytest.raises(ValueError, match="Session not found"):
            service.rollback_to_round(
                session_id="nonexistent_session",
                round_number=1
            )


class TestClarificationEffectivenessEvaluation:
    """测试澄清效果评估"""
    
    def test_evaluate_high_effectiveness(self, service, sample_session):
        """测试高效果评分"""
        user_responses = [
            {
                "response": "本月",
                "type": "single_choice",
                "confidence": 1.0
            },
            {
                "response": ["sales"],
                "type": "multiple_choice",
                "confidence": 0.9
            }
        ]
        
        result = service.confirm_clarification(
            session_id=sample_session.session_id,
            user_responses=user_responses
        )
        
        effectiveness = result["effectiveness_score"]
        assert 0.7 <= effectiveness <= 1.0  # 高效果
    
    def test_evaluate_low_effectiveness(self, service, sample_session):
        """测试低效果评分"""
        user_responses = [
            {
                "response": "不确定",
                "type": "single_choice",
                "confidence": 0.3
            }
        ]
        
        result = service.confirm_clarification(
            session_id=sample_session.session_id,
            user_responses=user_responses
        )
        
        effectiveness = result["effectiveness_score"]
        assert 0.0 <= effectiveness < 0.7  # 低效果
    
    def test_effectiveness_updates_statistics(self, service, sample_session):
        """测试效果评分更新统计"""
        user_responses = [
            {
                "response": "本月",
                "type": "single_choice",
                "confidence": 1.0
            }
        ]
        
        service.confirm_clarification(
            session_id=sample_session.session_id,
            user_responses=user_responses
        )
        
        stats = service.get_statistics()
        assert "avg_effectiveness_score" in stats
        assert 0.0 <= stats["avg_effectiveness_score"] <= 1.0


class TestClarificationOptimization:
    """测试澄清策略优化"""
    
    def test_optimize_with_low_effectiveness(self, service, sample_session):
        """测试低效果的优化建议"""
        # 创建低效果的澄清历史
        user_responses = [
            {
                "response": "不确定",
                "type": "single_choice",
                "confidence": 0.3
            }
        ]
        
        service.confirm_clarification(
            session_id=sample_session.session_id,
            user_responses=user_responses
        )
        
        result = service.optimize_clarification_strategy(sample_session.session_id)
        
        assert "recommendations" in result
        assert len(result["recommendations"]) > 0
        
        # 应该有低效果的建议
        low_eff_recs = [r for r in result["recommendations"] if r["type"] == "low_effectiveness"]
        assert len(low_eff_recs) > 0
    
    def test_optimize_with_too_many_rounds(self, service, sample_session):
        """测试多轮澄清的优化建议"""
        # 创建多轮澄清
        for i in range(3):
            user_responses = [
                {
                    "response": f"回答{i}",
                    "type": "single_choice",
                    "confidence": 0.8
                }
            ]
            
            service.confirm_clarification(
                session_id=sample_session.session_id,
                user_responses=user_responses
            )
            
            if i < 2:
                service.modify_clarification(
                    session_id=sample_session.session_id,
                    modifications={"round": i + 1}
                )
        
        result = service.optimize_clarification_strategy(sample_session.session_id)
        
        # 应该有多轮澄清的建议
        multi_round_recs = [r for r in result["recommendations"] if r["type"] == "too_many_rounds"]
        assert len(multi_round_recs) > 0
    
    def test_optimize_with_no_history(self, service, sample_session):
        """测试无历史数据的优化"""
        result = service.optimize_clarification_strategy(sample_session.session_id)
        
        assert "recommendations" in result
        assert len(result["recommendations"]) == 0
        assert "暂无历史数据" in result["message"]


class TestConfirmClarificationEnhanced:
    """测试增强的确认澄清功能"""
    
    def test_confirm_returns_intent_updates(self, service, sample_session):
        """测试确认返回意图更新"""
        user_responses = [
            {
                "response": "本月",
                "type": "single_choice",
                "confidence": 1.0
            }
        ]
        
        result = service.confirm_clarification(
            session_id=sample_session.session_id,
            user_responses=user_responses
        )
        
        assert "intent_updates" in result
        assert len(result["intent_updates"]) > 0
        assert "updated_intent" in result
        assert "effectiveness_score" in result
    
    def test_confirm_updates_session_status(self, service, sample_session):
        """测试确认更新会话状态"""
        user_responses = [
            {
                "response": "本月",
                "type": "single_choice",
                "confidence": 1.0
            }
        ]
        
        service.confirm_clarification(
            session_id=sample_session.session_id,
            user_responses=user_responses
        )
        
        assert sample_session.status == ClarificationStatus.CONFIRMED
        assert len(sample_session.intent_updates) > 0


class TestModifyClarificationEnhanced:
    """测试增强的修改澄清功能"""
    
    def test_modify_increments_round_number(self, service, sample_session):
        """测试修改增加轮次编号"""
        initial_round = sample_session.current_round
        
        service.modify_clarification(
            session_id=sample_session.session_id,
            modifications={"change": "需要修改"}
        )
        
        assert sample_session.current_round == initial_round + 1
    
    def test_modify_updates_statistics(self, service, sample_session):
        """测试修改更新统计"""
        initial_count = service.stats["user_modified_count"]
        initial_multi_round = service.stats["multi_round_clarifications"]
        
        service.modify_clarification(
            session_id=sample_session.session_id,
            modifications={"change": "需要修改"}
        )
        
        assert service.stats["user_modified_count"] == initial_count + 1
        assert service.stats["multi_round_clarifications"] == initial_multi_round + 1


class TestStatisticsEnhanced:
    """测试增强的统计功能"""
    
    def test_statistics_include_new_metrics(self, service):
        """测试统计包含新指标"""
        stats = service.get_statistics()
        
        assert "total_intent_updates" in stats
        assert "avg_effectiveness_score" in stats
        assert "multi_round_clarifications" in stats
        assert "modification_rate" in stats
        assert "multi_round_rate" in stats
    
    def test_modification_rate_calculation(self, service, sample_session):
        """测试修改率计算"""
        # 增加澄清计数
        service.stats["clarification_needed_count"] = 10
        service.stats["user_modified_count"] = 3
        
        stats = service.get_statistics()
        
        assert stats["modification_rate"] == 0.3
    
    def test_multi_round_rate_calculation(self, service):
        """测试多轮率计算"""
        service.stats["total_clarifications"] = 10
        service.stats["multi_round_clarifications"] = 2
        
        stats = service.get_statistics()
        
        assert stats["multi_round_rate"] == 0.2
