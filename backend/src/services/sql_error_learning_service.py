"""
SQL错误反馈学习循环服务

实现从SQL执行错误中学习的机制，包括：
1. 错误模式识别和预防
2. 错误反馈到AI模型的学习循环
3. 持续改进SQL生成准确率
4. 错误知识库的构建和维护
"""

import json
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import asyncio
import re
from enum import Enum

from .sql_error_classifier import (
    SQLErrorRecoveryService, 
    SQLError, 
    SQLErrorType, 
    ErrorFeedback
)

logger = logging.getLogger(__name__)


class LearningType(Enum):
    """学习类型枚举"""
    PATTERN_RECOGNITION = "pattern_recognition"
    FREQUENCY_ANALYSIS = "frequency_analysis"
    CONTEXT_CORRELATION = "context_correlation"
    SUCCESS_PATTERN = "success_pattern"


@dataclass
class ErrorPattern:
    """错误模式数据类"""
    pattern_id: str
    error_type: SQLErrorType
    pattern_regex: str
    frequency: int
    confidence: float
    context_keywords: List[str]
    common_fixes: List[str]
    created_at: datetime
    last_seen: datetime
    success_rate_after_fix: float = 0.0


@dataclass
class LearningSession:
    """学习会话数据类"""
    session_id: str
    original_question: str
    error_sequence: List[SQLError]
    successful_sql: Optional[str] = None
    learning_insights: List[str] = None
    created_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.learning_insights is None:
            self.learning_insights = []


@dataclass
class AIFeedbackMessage:
    """AI反馈消息数据类"""
    message_id: str
    session_id: str
    feedback_type: str
    original_question: str
    failed_sql: str
    error_analysis: str
    suggested_improvements: List[str]
    context_enhancement: Dict[str, Any]
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


class ErrorPatternLearner:
    """错误模式学习器"""
    
    def __init__(self):
        self.error_patterns: Dict[str, ErrorPattern] = {}
        self.pattern_counter = 0
        self.min_frequency_threshold = 3  # 最小频率阈值
        self.confidence_threshold = 0.7   # 置信度阈值
    
    def learn_from_error(self, sql_error: SQLError, context: Dict[str, Any]) -> Optional[ErrorPattern]:
        """
        从错误中学习模式
        
        Args:
            sql_error: SQL错误信息
            context: 上下文信息
            
        Returns:
            Optional[ErrorPattern]: 学习到的模式（如果有）
        """
        try:
            # 提取错误特征
            error_features = self._extract_error_features(sql_error, context)
            
            # 查找现有模式
            existing_pattern = self._find_matching_pattern(error_features)
            
            if existing_pattern:
                # 更新现有模式
                existing_pattern.frequency += 1
                existing_pattern.last_seen = datetime.now()
                existing_pattern.confidence = min(1.0, existing_pattern.confidence + 0.1)
                
                # 更新上下文关键词
                new_keywords = error_features.get("context_keywords", [])
                for keyword in new_keywords:
                    if keyword not in existing_pattern.context_keywords:
                        existing_pattern.context_keywords.append(keyword)
                
                logger.info(f"Updated existing error pattern: {existing_pattern.pattern_id}")
                return existing_pattern
            
            else:
                # 创建新模式
                new_pattern = self._create_new_pattern(error_features, sql_error)
                if new_pattern:
                    self.error_patterns[new_pattern.pattern_id] = new_pattern
                    logger.info(f"Created new error pattern: {new_pattern.pattern_id}")
                    return new_pattern
            
            return None
            
        except Exception as e:
            logger.error(f"Error in pattern learning: {e}")
            return None
    
    def _extract_error_features(self, sql_error: SQLError, context: Dict[str, Any]) -> Dict[str, Any]:
        """提取错误特征"""
        features = {
            "error_type": sql_error.error_type,
            "error_message_pattern": self._generalize_error_message(sql_error.original_error),
            "sql_pattern": self._extract_sql_pattern(sql_error.sql_statement),
            "context_keywords": self._extract_context_keywords(context),
            "table_names": context.get("table_names", []),
            "field_names": context.get("field_names", [])
        }
        return features
    
    def _generalize_error_message(self, error_message: str) -> str:
        """泛化错误消息，提取模式"""
        # 替换具体的表名、字段名为占位符
        generalized = error_message
        
        # 替换引号中的内容为占位符
        generalized = re.sub(r"'[^']*'", "'<IDENTIFIER>'", generalized)
        generalized = re.sub(r"`[^`]*`", "`<IDENTIFIER>`", generalized)
        
        # 替换数字为占位符
        generalized = re.sub(r'\b\d+\b', '<NUMBER>', generalized)
        
        return generalized
    
    def _extract_sql_pattern(self, sql_statement: str) -> str:
        """提取SQL模式"""
        # 简化SQL语句，提取结构模式
        sql_upper = sql_statement.upper()
        
        # 提取主要SQL关键词
        keywords = []
        sql_keywords = ['SELECT', 'FROM', 'WHERE', 'JOIN', 'GROUP BY', 'ORDER BY', 'HAVING']
        
        for keyword in sql_keywords:
            if keyword in sql_upper:
                keywords.append(keyword)
        
        return " ".join(keywords)
    
    def _extract_context_keywords(self, context: Dict[str, Any]) -> List[str]:
        """提取上下文关键词"""
        keywords = []
        
        # 从原始问题中提取关键词
        original_question = context.get("original_question", "")
        if original_question:
            # 简单的关键词提取（实际应用中可以使用更复杂的NLP技术）
            words = re.findall(r'\b\w+\b', original_question.lower())
            keywords.extend([word for word in words if len(word) > 3])
        
        # 从表名和字段名中提取
        keywords.extend(context.get("table_names", []))
        keywords.extend(context.get("field_names", []))
        
        return list(set(keywords))
    
    def _find_matching_pattern(self, error_features: Dict[str, Any]) -> Optional[ErrorPattern]:
        """查找匹配的现有模式"""
        for pattern in self.error_patterns.values():
            if (pattern.error_type == error_features["error_type"] and
                pattern.pattern_regex == error_features["error_message_pattern"]):
                return pattern
        return None
    
    def _create_new_pattern(self, error_features: Dict[str, Any], sql_error: SQLError) -> Optional[ErrorPattern]:
        """创建新的错误模式"""
        self.pattern_counter += 1
        pattern_id = f"pattern_{self.pattern_counter}_{sql_error.error_type.value}"
        
        return ErrorPattern(
            pattern_id=pattern_id,
            error_type=error_features["error_type"],
            pattern_regex=error_features["error_message_pattern"],
            frequency=1,
            confidence=0.5,  # 初始置信度
            context_keywords=error_features["context_keywords"],
            common_fixes=[],
            created_at=datetime.now(),
            last_seen=datetime.now()
        )
    
    def get_frequent_patterns(self, min_frequency: int = None) -> List[ErrorPattern]:
        """获取高频错误模式"""
        threshold = min_frequency or self.min_frequency_threshold
        return [
            pattern for pattern in self.error_patterns.values()
            if pattern.frequency >= threshold
        ]
    
    def predict_error_likelihood(self, context: Dict[str, Any]) -> Dict[SQLErrorType, float]:
        """预测错误可能性"""
        predictions = defaultdict(float)
        
        context_keywords = self._extract_context_keywords(context)
        
        for pattern in self.error_patterns.values():
            # 计算上下文匹配度
            keyword_overlap = len(set(context_keywords) & set(pattern.context_keywords))
            if keyword_overlap > 0:
                match_score = keyword_overlap / len(pattern.context_keywords)
                predictions[pattern.error_type] += match_score * pattern.confidence
        
        return dict(predictions)


class AIFeedbackGenerator:
    """AI反馈生成器"""
    
    def __init__(self, pattern_learner: ErrorPatternLearner):
        self.pattern_learner = pattern_learner
        self.feedback_history: List[AIFeedbackMessage] = []
    
    def generate_learning_feedback(
        self, 
        learning_session: LearningSession,
        context: Dict[str, Any]
    ) -> AIFeedbackMessage:
        """
        生成学习反馈消息
        
        Args:
            learning_session: 学习会话
            context: 上下文信息
            
        Returns:
            AIFeedbackMessage: AI反馈消息
        """
        try:
            # 分析错误序列
            error_analysis = self._analyze_error_sequence(learning_session.error_sequence)
            
            # 生成改进建议
            improvements = self._generate_improvement_suggestions(
                learning_session, error_analysis, context
            )
            
            # 增强上下文信息
            enhanced_context = self._enhance_context_for_ai(
                learning_session, context
            )
            
            # 创建反馈消息
            feedback_message = AIFeedbackMessage(
                message_id=f"feedback_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{learning_session.session_id}",
                session_id=learning_session.session_id,
                feedback_type="error_learning",
                original_question=learning_session.original_question,
                failed_sql=learning_session.error_sequence[-1].sql_statement if learning_session.error_sequence else "",
                error_analysis=error_analysis,
                suggested_improvements=improvements,
                context_enhancement=enhanced_context
            )
            
            self.feedback_history.append(feedback_message)
            logger.info(f"Generated AI feedback: {feedback_message.message_id}")
            
            return feedback_message
            
        except Exception as e:
            logger.error(f"Error generating AI feedback: {e}")
            raise
    
    def _analyze_error_sequence(self, error_sequence: List[SQLError]) -> str:
        """分析错误序列"""
        if not error_sequence:
            return "无错误序列"
        
        analysis_parts = []
        
        # 错误类型分布
        error_types = [error.error_type for error in error_sequence]
        error_counts = Counter(error_types)
        
        analysis_parts.append(f"错误序列包含 {len(error_sequence)} 个错误")
        analysis_parts.append(f"错误类型分布: {dict(error_counts)}")
        
        # 最常见的错误
        most_common_error = error_counts.most_common(1)[0]
        analysis_parts.append(f"最常见错误: {most_common_error[0].value} (出现 {most_common_error[1]} 次)")
        
        # 错误趋势
        if len(error_sequence) > 1:
            if error_sequence[-1].error_type == error_sequence[0].error_type:
                analysis_parts.append("错误类型未改变，可能需要不同的解决策略")
            else:
                analysis_parts.append("错误类型发生变化，显示了问题解决的进展")
        
        return "; ".join(analysis_parts)
    
    def _generate_improvement_suggestions(
        self, 
        learning_session: LearningSession,
        error_analysis: str,
        context: Dict[str, Any]
    ) -> List[str]:
        """生成改进建议"""
        suggestions = []
        
        if not learning_session.error_sequence:
            return suggestions
        
        # 基于错误类型的建议
        error_types = set(error.error_type for error in learning_session.error_sequence)
        
        if SQLErrorType.FIELD_NOT_EXISTS in error_types:
            suggestions.append("建议：在生成SQL前，验证所有字段名是否存在于目标表中")
            suggestions.append("建议：使用表结构信息进行字段名校验")
        
        if SQLErrorType.TABLE_NOT_EXISTS in error_types:
            suggestions.append("建议：在生成SQL前，确认所有表名都在可用表列表中")
            suggestions.append("建议：提供更准确的表选择逻辑")
        
        if SQLErrorType.SYNTAX_ERROR in error_types:
            suggestions.append("建议：加强SQL语法验证，特别是数据库方言差异")
            suggestions.append("建议：使用SQL解析器进行语法检查")
        
        if SQLErrorType.TYPE_MISMATCH in error_types:
            suggestions.append("建议：在生成WHERE条件时，考虑字段的数据类型")
            suggestions.append("建议：为不同数据类型提供适当的比较操作符")
        
        # 基于频繁模式的建议
        frequent_patterns = self.pattern_learner.get_frequent_patterns()
        for pattern in frequent_patterns:
            if any(error.error_type == pattern.error_type for error in learning_session.error_sequence):
                suggestions.extend(pattern.common_fixes)
        
        # 基于上下文的建议
        if context.get("table_count", 0) > 1:
            suggestions.append("建议：多表查询时，明确指定表别名和JOIN条件")
        
        if context.get("complex_conditions", False):
            suggestions.append("建议：复杂条件查询时，分步构建WHERE子句")
        
        return list(set(suggestions))  # 去重
    
    def _enhance_context_for_ai(
        self, 
        learning_session: LearningSession,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """为AI增强上下文信息"""
        enhanced_context = context.copy()
        
        # 添加错误历史信息
        enhanced_context["error_history"] = [
            {
                "error_type": error.error_type.value,
                "error_message": error.error_message,
                "confidence": error.confidence
            }
            for error in learning_session.error_sequence
        ]
        
        # 添加学习洞察
        enhanced_context["learning_insights"] = learning_session.learning_insights
        
        # 添加成功SQL（如果有）
        if learning_session.successful_sql:
            enhanced_context["successful_sql_example"] = learning_session.successful_sql
        
        # 添加预测的错误可能性
        error_predictions = self.pattern_learner.predict_error_likelihood(context)
        enhanced_context["predicted_error_risks"] = {
            error_type.value: probability 
            for error_type, probability in error_predictions.items()
        }
        
        return enhanced_context
    
    def format_feedback_for_ai_model(self, feedback: AIFeedbackMessage) -> str:
        """格式化反馈信息供AI模型使用"""
        feedback_text = f"""
错误学习反馈 - 会话 {feedback.session_id}

原始问题: {feedback.original_question}

失败的SQL: {feedback.failed_sql}

错误分析: {feedback.error_analysis}

改进建议:
{chr(10).join(f"- {suggestion}" for suggestion in feedback.suggested_improvements)}

增强上下文信息:
- 错误历史: {len(feedback.context_enhancement.get('error_history', []))} 个错误
- 预测风险: {feedback.context_enhancement.get('predicted_error_risks', {})}
- 学习洞察: {feedback.context_enhancement.get('learning_insights', [])}

请基于以上反馈信息，在后续的SQL生成中避免类似错误，并采用建议的改进策略。
"""
        return feedback_text.strip()


class SQLErrorLearningService:
    """SQL错误学习服务"""
    
    def __init__(self, error_recovery_service: SQLErrorRecoveryService):
        self.error_recovery_service = error_recovery_service
        self.pattern_learner = ErrorPatternLearner()
        self.feedback_generator = AIFeedbackGenerator(self.pattern_learner)
        self.learning_sessions: Dict[str, LearningSession] = {}
        self.learning_enabled = True
    
    async def start_learning_session(self, session_id: str, original_question: str) -> LearningSession:
        """
        开始学习会话
        
        Args:
            session_id: 会话ID
            original_question: 原始问题
            
        Returns:
            LearningSession: 学习会话
        """
        learning_session = LearningSession(
            session_id=session_id,
            original_question=original_question,
            error_sequence=[]
        )
        
        self.learning_sessions[session_id] = learning_session
        logger.info(f"Started learning session: {session_id}")
        
        return learning_session
    
    async def record_error(
        self, 
        session_id: str, 
        sql_error: SQLError, 
        context: Dict[str, Any]
    ) -> Optional[ErrorPattern]:
        """
        记录错误并学习
        
        Args:
            session_id: 会话ID
            sql_error: SQL错误
            context: 上下文信息
            
        Returns:
            Optional[ErrorPattern]: 学习到的模式
        """
        if not self.learning_enabled:
            return None
        
        try:
            # 获取或创建学习会话
            if session_id not in self.learning_sessions:
                await self.start_learning_session(session_id, context.get("original_question", ""))
            
            learning_session = self.learning_sessions[session_id]
            learning_session.error_sequence.append(sql_error)
            
            # 从错误中学习模式
            learned_pattern = self.pattern_learner.learn_from_error(sql_error, context)
            
            # 记录学习洞察
            if learned_pattern:
                insight = f"学习到新的错误模式: {learned_pattern.pattern_id}"
                learning_session.learning_insights.append(insight)
                logger.info(f"Learned new pattern: {learned_pattern.pattern_id}")
            
            return learned_pattern
            
        except Exception as e:
            logger.error(f"Error recording error for learning: {e}")
            return None
    
    async def record_success(self, session_id: str, successful_sql: str):
        """
        记录成功的SQL
        
        Args:
            session_id: 会话ID
            successful_sql: 成功的SQL
        """
        if session_id in self.learning_sessions:
            learning_session = self.learning_sessions[session_id]
            learning_session.successful_sql = successful_sql
            
            # 更新相关错误模式的成功率
            await self._update_pattern_success_rates(learning_session)
            
            logger.info(f"Recorded successful SQL for session: {session_id}")
    
    async def generate_feedback_for_ai(
        self, 
        session_id: str, 
        context: Dict[str, Any]
    ) -> Optional[AIFeedbackMessage]:
        """
        为AI模型生成反馈
        
        Args:
            session_id: 会话ID
            context: 上下文信息
            
        Returns:
            Optional[AIFeedbackMessage]: AI反馈消息
        """
        if session_id not in self.learning_sessions:
            return None
        
        try:
            learning_session = self.learning_sessions[session_id]
            
            # 只有在有错误时才生成反馈
            if not learning_session.error_sequence:
                return None
            
            feedback = self.feedback_generator.generate_learning_feedback(
                learning_session, context
            )
            
            return feedback
            
        except Exception as e:
            logger.error(f"Error generating AI feedback: {e}")
            return None
    
    async def _update_pattern_success_rates(self, learning_session: LearningSession):
        """更新错误模式的成功率"""
        if not learning_session.successful_sql or not learning_session.error_sequence:
            return
        
        # 为每个错误类型更新成功率
        error_types = set(error.error_type for error in learning_session.error_sequence)
        
        for pattern in self.pattern_learner.error_patterns.values():
            if pattern.error_type in error_types:
                # 简单的成功率更新逻辑
                pattern.success_rate_after_fix = min(1.0, pattern.success_rate_after_fix + 0.1)
    
    def get_learning_statistics(self) -> Dict[str, Any]:
        """获取学习统计信息"""
        total_sessions = len(self.learning_sessions)
        total_errors = sum(len(session.error_sequence) for session in self.learning_sessions.values())
        successful_sessions = len([
            session for session in self.learning_sessions.values() 
            if session.successful_sql
        ])
        
        pattern_stats = {
            "total_patterns": len(self.pattern_learner.error_patterns),
            "frequent_patterns": len(self.pattern_learner.get_frequent_patterns()),
            "high_confidence_patterns": len([
                p for p in self.pattern_learner.error_patterns.values() 
                if p.confidence >= self.pattern_learner.confidence_threshold
            ])
        }
        
        return {
            "learning_enabled": self.learning_enabled,
            "total_learning_sessions": total_sessions,
            "total_errors_recorded": total_errors,
            "successful_sessions": successful_sessions,
            "success_rate": successful_sessions / total_sessions if total_sessions > 0 else 0,
            "pattern_statistics": pattern_stats,
            "feedback_messages_generated": len(self.feedback_generator.feedback_history)
        }
    
    def get_error_predictions(self, context: Dict[str, Any]) -> Dict[str, float]:
        """获取错误预测"""
        predictions = self.pattern_learner.predict_error_likelihood(context)
        return {error_type.value: probability for error_type, probability in predictions.items()}
    
    def get_improvement_suggestions(self, session_id: str) -> List[str]:
        """获取改进建议"""
        if session_id not in self.learning_sessions:
            return []
        
        learning_session = self.learning_sessions[session_id]
        if not learning_session.error_sequence:
            return []
        
        # 基于错误序列生成建议
        suggestions = []
        error_types = set(error.error_type for error in learning_session.error_sequence)
        
        for error_type in error_types:
            patterns = [
                p for p in self.pattern_learner.error_patterns.values()
                if p.error_type == error_type and p.common_fixes
            ]
            for pattern in patterns:
                suggestions.extend(pattern.common_fixes)
        
        return list(set(suggestions))
    
    def cleanup_old_sessions(self, max_age_hours: int = 24):
        """清理旧的学习会话"""
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        
        old_sessions = [
            session_id for session_id, session in self.learning_sessions.items()
            if session.created_at < cutoff_time
        ]
        
        for session_id in old_sessions:
            del self.learning_sessions[session_id]
        
        logger.info(f"Cleaned up {len(old_sessions)} old learning sessions")
    
    def export_learning_data(self) -> Dict[str, Any]:
        """导出学习数据"""
        return {
            "error_patterns": {
                pattern_id: asdict(pattern) 
                for pattern_id, pattern in self.pattern_learner.error_patterns.items()
            },
            "learning_sessions": {
                session_id: {
                    "session_id": session.session_id,
                    "original_question": session.original_question,
                    "error_count": len(session.error_sequence),
                    "successful_sql": session.successful_sql,
                    "learning_insights": session.learning_insights,
                    "created_at": session.created_at.isoformat()
                }
                for session_id, session in self.learning_sessions.items()
            },
            "feedback_history": [
                asdict(feedback) for feedback in self.feedback_generator.feedback_history
            ]
        }