"""
意图识别上下文管理服务 - 任务 5.1.2
基于对话历史的意图推断、动态调整和澄清机制
"""

import json
import logging
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum

from .intent_recognition_service import IntentRecognitionService, IntentResult, IntentType
from .context_manager import ContextManager, get_context_manager
from .ai_model_service import get_ai_service, ModelType

logger = logging.getLogger(__name__)


class ConfidenceLevel(Enum):
    """置信度级别"""
    HIGH = "high"      # >= 0.8
    MEDIUM = "medium"  # 0.5 - 0.8
    LOW = "low"        # < 0.5


class ClarificationReason(Enum):
    """澄清原因"""
    LOW_CONFIDENCE = "low_confidence"
    AMBIGUOUS_INTENT = "ambiguous_intent"
    CONTEXT_CONFLICT = "context_conflict"
    MISSING_INFORMATION = "missing_information"


@dataclass
class IntentAdjustment:
    """意图调整记录"""
    original_intent: IntentType
    adjusted_intent: IntentType
    reason: str
    confidence_change: float
    timestamp: datetime
    user_confirmed: bool = False


@dataclass
class ClarificationRequest:
    """澄清请求"""
    session_id: str
    original_question: str
    detected_intent: IntentType
    confidence: float
    reason: ClarificationReason
    clarification_questions: List[str]
    suggested_intents: List[Tuple[IntentType, float]]
    timestamp: datetime


@dataclass
class ContextualIntentResult:
    """上下文意图识别结果"""
    intent_result: IntentResult
    confidence_level: ConfidenceLevel
    context_influence: Dict[str, Any]
    adjustment_history: List[IntentAdjustment]
    clarification_needed: bool
    clarification_request: Optional[ClarificationRequest] = None


class IntentContextManager:
    """意图识别上下文管理器"""
    
    def __init__(self):
        self.intent_service = IntentRecognitionService()
        self.context_manager = get_context_manager()
        self.ai_service = get_ai_service()
        
        # 配置参数
        self.confidence_thresholds = {
            ConfidenceLevel.HIGH: 0.8,
            ConfidenceLevel.MEDIUM: 0.5,
            ConfidenceLevel.LOW: 0.0
        }
        
        self.context_weight = 0.3  # 上下文对意图识别的影响权重
        self.history_window = 5    # 考虑的历史消息数量
        
        # 会话状态存储
        self.session_states: Dict[str, Dict[str, Any]] = {}
    
    async def identify_intent_with_context(
        self, 
        session_id: str, 
        user_question: str,
        force_clarification: bool = False
    ) -> ContextualIntentResult:
        """
        基于上下文识别意图
        
        Args:
            session_id: 会话ID
            user_question: 用户问题
            force_clarification: 是否强制澄清
            
        Returns:
            ContextualIntentResult: 上下文意图识别结果
        """
        try:
            # 获取会话上下文
            context = self._build_session_context(session_id)
            
            # 基础意图识别
            base_intent = await self.intent_service.identify_intent(user_question, context)
            
            # 上下文影响分析
            context_influence = self._analyze_context_influence(session_id, user_question, base_intent)
            
            # 调整意图（如果需要）
            adjusted_intent, adjustment = self._adjust_intent_with_context(
                base_intent, context_influence
            )
            
            # 确定置信度级别
            confidence_level = self._determine_confidence_level(adjusted_intent.confidence)
            
            # 获取调整历史
            adjustment_history = self._get_adjustment_history(session_id)
            if adjustment:
                adjustment_history.append(adjustment)
                self._save_adjustment_history(session_id, adjustment_history)
            
            # 判断是否需要澄清
            clarification_needed = (
                force_clarification or
                confidence_level == ConfidenceLevel.LOW or
                self._should_clarify_based_on_context(adjusted_intent, context_influence)
            )
            
            # 生成澄清请求（如果需要）
            clarification_request = None
            if clarification_needed:
                clarification_request = await self._generate_clarification_request(
                    session_id, user_question, adjusted_intent, context_influence
                )
            
            # 更新会话状态
            self._update_session_state(session_id, adjusted_intent, context_influence)
            
            result = ContextualIntentResult(
                intent_result=adjusted_intent,
                confidence_level=confidence_level,
                context_influence=context_influence,
                adjustment_history=adjustment_history,
                clarification_needed=clarification_needed,
                clarification_request=clarification_request
            )
            
            logger.info(f"Contextual intent identified for session {session_id}: "
                       f"{adjusted_intent.intent.value} (confidence: {adjusted_intent.confidence:.2f}, "
                       f"level: {confidence_level.value}, clarification: {clarification_needed})")
            
            return result
            
        except Exception as e:
            logger.error(f"Contextual intent identification failed for session {session_id}: {str(e)}")
            raise
    
    def _build_session_context(self, session_id: str) -> Dict[str, Any]:
        """构建会话上下文"""
        context = {}
        
        # 获取对话历史
        cloud_history = self.context_manager.get_cloud_history(session_id, self.history_window)
        if cloud_history:
            context['conversation_history'] = cloud_history
            context['conversation_length'] = len(cloud_history)
        
        # 获取会话状态
        session_state = self.session_states.get(session_id, {})
        if session_state:
            context['session_state'] = session_state
        
        # 获取最近的意图模式
        recent_intents = self._get_recent_intents(session_id)
        if recent_intents:
            context['recent_intents'] = recent_intents
            context['dominant_intent'] = self._get_dominant_intent(recent_intents)
        
        return context
    
    def _analyze_context_influence(
        self, 
        session_id: str, 
        user_question: str, 
        base_intent: IntentResult
    ) -> Dict[str, Any]:
        """分析上下文对意图识别的影响"""
        influence = {
            'historical_pattern': None,
            'conversation_flow': None,
            'question_similarity': None,
            'context_score': 0.0
        }
        
        # 分析历史模式
        recent_intents = self._get_recent_intents(session_id)
        if recent_intents:
            dominant_intent = self._get_dominant_intent(recent_intents)
            if dominant_intent == base_intent.intent:
                influence['historical_pattern'] = 'consistent'
                influence['context_score'] += 0.2
            else:
                influence['historical_pattern'] = 'divergent'
                influence['context_score'] -= 0.1
        
        # 分析对话流程
        conversation_flow = self._analyze_conversation_flow(session_id)
        influence['conversation_flow'] = conversation_flow
        if conversation_flow == 'natural_progression':
            influence['context_score'] += 0.1
        elif conversation_flow == 'topic_switch':
            influence['context_score'] -= 0.05
        
        # 分析问题相似性
        similarity_score = self._calculate_question_similarity(session_id, user_question)
        influence['question_similarity'] = similarity_score
        influence['context_score'] += similarity_score * 0.1
        
        return influence
    
    def _adjust_intent_with_context(
        self, 
        base_intent: IntentResult, 
        context_influence: Dict[str, Any]
    ) -> Tuple[IntentResult, Optional[IntentAdjustment]]:
        """基于上下文调整意图"""
        context_score = context_influence.get('context_score', 0.0)
        
        # 如果上下文影响很小，不调整
        if abs(context_score) < 0.1:
            return base_intent, None
        
        # 计算调整后的置信度
        adjusted_confidence = base_intent.confidence + (context_score * self.context_weight)
        adjusted_confidence = max(0.0, min(1.0, adjusted_confidence))  # 限制在[0,1]范围
        
        # 如果置信度变化显著，可能需要调整意图类型
        original_intent = base_intent.intent
        adjusted_intent_type = original_intent
        
        # 基于上下文决定是否切换意图类型
        if context_score > 0.3 and base_intent.confidence < 0.6:
            # 强正向上下文且原始置信度不高，可能需要切换
            dominant_intent = context_influence.get('dominant_intent')
            if dominant_intent and dominant_intent != original_intent:
                adjusted_intent_type = dominant_intent
        
        # 创建调整后的意图结果
        adjusted_intent = IntentResult(
            intent=adjusted_intent_type,
            confidence=adjusted_confidence,
            reasoning=f"{base_intent.reasoning} (上下文调整: {context_score:+.2f})",
            original_question=base_intent.original_question,
            metadata={
                **base_intent.metadata,
                'context_adjusted': True,
                'original_confidence': base_intent.confidence,
                'context_score': context_score
            }
        )
        
        # 创建调整记录
        adjustment = None
        if adjusted_intent_type != original_intent or abs(adjusted_confidence - base_intent.confidence) > 0.1:
            adjustment = IntentAdjustment(
                original_intent=original_intent,
                adjusted_intent=adjusted_intent_type,
                reason=f"上下文影响: {context_score:+.2f}",
                confidence_change=adjusted_confidence - base_intent.confidence,
                timestamp=datetime.now()
            )
        
        return adjusted_intent, adjustment
    
    def _determine_confidence_level(self, confidence: float) -> ConfidenceLevel:
        """确定置信度级别"""
        if confidence >= self.confidence_thresholds[ConfidenceLevel.HIGH]:
            return ConfidenceLevel.HIGH
        elif confidence >= self.confidence_thresholds[ConfidenceLevel.MEDIUM]:
            return ConfidenceLevel.MEDIUM
        else:
            return ConfidenceLevel.LOW
    
    def _should_clarify_based_on_context(
        self, 
        intent: IntentResult, 
        context_influence: Dict[str, Any]
    ) -> bool:
        """基于上下文判断是否需要澄清"""
        # 低置信度需要澄清
        if intent.confidence < self.confidence_thresholds[ConfidenceLevel.MEDIUM]:
            return True
        
        # 上下文冲突需要澄清
        if context_influence.get('historical_pattern') == 'divergent':
            return True
        
        # 话题切换可能需要澄清
        if context_influence.get('conversation_flow') == 'topic_switch':
            return True
        
        return False
    
    async def _generate_clarification_request(
        self,
        session_id: str,
        user_question: str,
        intent: IntentResult,
        context_influence: Dict[str, Any]
    ) -> ClarificationRequest:
        """生成澄清请求"""
        # 确定澄清原因
        reason = ClarificationReason.LOW_CONFIDENCE
        if intent.confidence < 0.3:
            reason = ClarificationReason.LOW_CONFIDENCE
        elif context_influence.get('historical_pattern') == 'divergent':
            reason = ClarificationReason.CONTEXT_CONFLICT
        elif intent.intent == IntentType.UNKNOWN:
            reason = ClarificationReason.AMBIGUOUS_INTENT
        
        # 生成澄清问题
        clarification_questions = await self._generate_clarification_questions(
            user_question, intent, reason
        )
        
        # 生成建议意图
        suggested_intents = self._generate_suggested_intents(intent, context_influence)
        
        return ClarificationRequest(
            session_id=session_id,
            original_question=user_question,
            detected_intent=intent.intent,
            confidence=intent.confidence,
            reason=reason,
            clarification_questions=clarification_questions,
            suggested_intents=suggested_intents,
            timestamp=datetime.now()
        )
    
    async def _generate_clarification_questions(
        self,
        user_question: str,
        intent: IntentResult,
        reason: ClarificationReason
    ) -> List[str]:
        """生成澄清问题"""
        questions = []
        
        if reason == ClarificationReason.LOW_CONFIDENCE:
            questions.extend([
                "您是想要查询具体的数据结果，还是需要生成一份分析报告？",
                "请问您希望看到具体的数值统计，还是需要综合性的分析总结？"
            ])
        elif reason == ClarificationReason.AMBIGUOUS_INTENT:
            questions.extend([
                "您的问题可能有多种理解方式，请问您具体想要：",
                "为了更好地帮助您，请明确您的具体需求："
            ])
        elif reason == ClarificationReason.CONTEXT_CONFLICT:
            questions.extend([
                "根据您之前的问题，我注意到可能有不同的需求，请确认：",
                "您当前的问题与之前的对话内容似乎有所不同，请澄清："
            ])
        
        return questions[:2]  # 最多返回2个问题
    
    def _generate_suggested_intents(
        self,
        intent: IntentResult,
        context_influence: Dict[str, Any]
    ) -> List[Tuple[IntentType, float]]:
        """生成建议意图"""
        suggestions = []
        
        # 当前检测到的意图
        suggestions.append((intent.intent, intent.confidence))
        
        # 基于历史模式的建议
        dominant_intent = context_influence.get('dominant_intent')
        if dominant_intent and dominant_intent != intent.intent:
            # 估算基于历史的置信度
            historical_confidence = min(0.8, intent.confidence + 0.2)
            suggestions.append((dominant_intent, historical_confidence))
        
        # 添加其他可能的意图
        for intent_type in IntentType:
            if intent_type not in [s[0] for s in suggestions] and intent_type != IntentType.UNKNOWN:
                suggestions.append((intent_type, 0.3))
        
        # 按置信度排序
        suggestions.sort(key=lambda x: x[1], reverse=True)
        return suggestions[:3]  # 最多返回3个建议
    
    async def confirm_intent_adjustment(
        self,
        session_id: str,
        confirmed_intent: IntentType,
        user_feedback: str = None
    ) -> bool:
        """确认意图调整"""
        try:
            # 获取调整历史
            adjustment_history = self._get_adjustment_history(session_id)
            
            # 标记最近的调整为已确认
            if adjustment_history:
                latest_adjustment = adjustment_history[-1]
                latest_adjustment.user_confirmed = True
                latest_adjustment.adjusted_intent = confirmed_intent
                
                # 保存调整历史
                self._save_adjustment_history(session_id, adjustment_history)
            
            # 更新会话状态
            session_state = self.session_states.get(session_id, {})
            session_state['last_confirmed_intent'] = confirmed_intent
            session_state['last_confirmation_time'] = datetime.now()
            if user_feedback:
                session_state['user_feedback'] = user_feedback
            
            self.session_states[session_id] = session_state
            
            logger.info(f"Intent adjustment confirmed for session {session_id}: {confirmed_intent.value}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to confirm intent adjustment for session {session_id}: {str(e)}")
            return False
    
    def _get_recent_intents(self, session_id: str, count: int = 5) -> List[IntentType]:
        """获取最近的意图"""
        # 从会话状态中获取
        session_state = self.session_states.get(session_id, {})
        return session_state.get('recent_intents', [])
    
    def _get_dominant_intent(self, recent_intents: List[IntentType]) -> Optional[IntentType]:
        """获取主导意图"""
        if not recent_intents:
            return None
        
        # 统计各意图出现次数
        intent_counts = {}
        for intent in recent_intents:
            intent_counts[intent] = intent_counts.get(intent, 0) + 1
        
        # 返回出现次数最多的意图
        return max(intent_counts.items(), key=lambda x: x[1])[0]
    
    def _analyze_conversation_flow(self, session_id: str) -> str:
        """分析对话流程"""
        recent_intents = self._get_recent_intents(session_id)
        
        if len(recent_intents) < 2:
            return 'insufficient_data'
        
        # 检查意图一致性
        unique_intents = set(recent_intents[-3:])  # 最近3个意图
        
        if len(unique_intents) == 1:
            return 'natural_progression'
        elif len(unique_intents) == 2:
            return 'minor_variation'
        else:
            return 'topic_switch'
    
    def _calculate_question_similarity(self, session_id: str, current_question: str) -> float:
        """计算问题相似性"""
        # 获取历史问题
        cloud_history = self.context_manager.get_cloud_history(session_id, 3)
        
        if not cloud_history:
            return 0.0
        
        # 简单的相似性计算（基于关键词重叠）
        current_words = set(current_question.lower().split())
        
        similarities = []
        for msg in cloud_history:
            if msg.get('role') == 'user':
                historical_words = set(msg.get('content', '').lower().split())
                if historical_words:
                    overlap = len(current_words & historical_words)
                    total = len(current_words | historical_words)
                    similarity = overlap / total if total > 0 else 0.0
                    similarities.append(similarity)
        
        return max(similarities) if similarities else 0.0
    
    def _update_session_state(
        self,
        session_id: str,
        intent: IntentResult,
        context_influence: Dict[str, Any]
    ):
        """更新会话状态"""
        session_state = self.session_states.get(session_id, {})
        
        # 更新最近意图列表
        recent_intents = session_state.get('recent_intents', [])
        recent_intents.append(intent.intent)
        
        # 保持最近5个意图
        if len(recent_intents) > 5:
            recent_intents = recent_intents[-5:]
        
        session_state.update({
            'recent_intents': recent_intents,
            'last_intent': intent.intent,
            'last_confidence': intent.confidence,
            'last_update': datetime.now(),
            'context_influence': context_influence
        })
        
        self.session_states[session_id] = session_state
    
    def _get_adjustment_history(self, session_id: str) -> List[IntentAdjustment]:
        """获取调整历史"""
        session_state = self.session_states.get(session_id, {})
        history_data = session_state.get('adjustment_history', [])
        
        # 转换为IntentAdjustment对象
        history = []
        for item in history_data:
            if isinstance(item, dict):
                history.append(IntentAdjustment(
                    original_intent=IntentType(item['original_intent']),
                    adjusted_intent=IntentType(item['adjusted_intent']),
                    reason=item['reason'],
                    confidence_change=item['confidence_change'],
                    timestamp=datetime.fromisoformat(item['timestamp']),
                    user_confirmed=item.get('user_confirmed', False)
                ))
            else:
                history.append(item)
        
        return history
    
    def _save_adjustment_history(self, session_id: str, history: List[IntentAdjustment]):
        """保存调整历史"""
        session_state = self.session_states.get(session_id, {})
        
        # 转换为可序列化的格式
        history_data = []
        for adjustment in history:
            history_data.append({
                'original_intent': adjustment.original_intent.value,
                'adjusted_intent': adjustment.adjusted_intent.value,
                'reason': adjustment.reason,
                'confidence_change': adjustment.confidence_change,
                'timestamp': adjustment.timestamp.isoformat(),
                'user_confirmed': adjustment.user_confirmed
            })
        
        session_state['adjustment_history'] = history_data
        self.session_states[session_id] = session_state
    
    def get_session_intent_stats(self, session_id: str) -> Dict[str, Any]:
        """获取会话意图统计"""
        session_state = self.session_states.get(session_id, {})
        recent_intents = session_state.get('recent_intents', [])
        
        stats = {
            'session_id': session_id,
            'total_intents': len(recent_intents),
            'intent_distribution': {},
            'last_intent': session_state.get('last_intent'),
            'last_confidence': session_state.get('last_confidence'),
            'last_update': session_state.get('last_update'),
            'adjustment_count': len(session_state.get('adjustment_history', []))
        }
        
        # 计算意图分布
        if recent_intents:
            for intent in IntentType:
                count = recent_intents.count(intent)
                stats['intent_distribution'][intent.value] = count / len(recent_intents)
        
        return stats


# 全局意图上下文管理器实例
_intent_context_manager: Optional[IntentContextManager] = None


def get_intent_context_manager() -> IntentContextManager:
    """获取意图上下文管理器实例"""
    global _intent_context_manager
    if _intent_context_manager is None:
        _intent_context_manager = IntentContextManager()
    return _intent_context_manager


def init_intent_context_manager() -> IntentContextManager:
    """初始化意图上下文管理器"""
    global _intent_context_manager
    _intent_context_manager = IntentContextManager()
    return _intent_context_manager