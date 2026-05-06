"""
SQL错误分类和处理服务

实现SQL生成错误的自动分类、重试策略和结构化反馈机制。
支持错误模式的学习和预防。
"""

import re
import json
import logging
from enum import Enum
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import asyncio

logger = logging.getLogger(__name__)


class SQLErrorType(Enum):
    """SQL错误类型枚举"""
    SYNTAX_ERROR = "syntax_error"
    FIELD_NOT_EXISTS = "field_not_exists"
    TABLE_NOT_EXISTS = "table_not_exists"
    TYPE_MISMATCH = "type_mismatch"
    PERMISSION_ERROR = "permission_error"
    CONNECTION_ERROR = "connection_error"
    CONSTRAINT_VIOLATION = "constraint_violation"
    TIMEOUT_ERROR = "timeout_error"
    UNKNOWN_ERROR = "unknown_error"


class RetryStrategy(Enum):
    """重试策略枚举"""
    NO_RETRY = "no_retry"
    IMMEDIATE_RETRY = "immediate_retry"
    BACKOFF_RETRY = "backoff_retry"
    REGENERATE_SQL = "regenerate_sql"
    CLARIFY_INTENT = "clarify_intent"


@dataclass
class ErrorPattern:
    """错误模式数据类"""
    pattern: str
    error_type: SQLErrorType
    confidence: float
    description: str
    suggested_fix: str


@dataclass
class SQLError:
    """SQL错误信息数据类"""
    error_type: SQLErrorType
    original_error: str
    error_message: str
    sql_statement: str
    error_location: Optional[str] = None
    suggested_fields: List[str] = None
    suggested_tables: List[str] = None
    retry_strategy: RetryStrategy = RetryStrategy.NO_RETRY
    confidence: float = 0.0
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
        if self.suggested_fields is None:
            self.suggested_fields = []
        if self.suggested_tables is None:
            self.suggested_tables = []


@dataclass
class RetryConfig:
    """重试配置数据类"""
    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 30.0
    backoff_factor: float = 2.0
    jitter: bool = True


@dataclass
class ErrorFeedback:
    """错误反馈数据类"""
    session_id: str
    original_question: str
    generated_sql: str
    error_info: SQLError
    context: Dict[str, Any]
    feedback_for_ai: str
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


class SQLErrorClassifier:
    """SQL错误分类器"""
    
    def __init__(self):
        self.error_patterns = self._initialize_error_patterns()
        self.error_history: List[SQLError] = []
        self.pattern_learning_enabled = True
        
    def _initialize_error_patterns(self) -> List[ErrorPattern]:
        """初始化错误模式"""
        return [
            # MySQL语法错误模式
            ErrorPattern(
                pattern=r"You have an error in your SQL syntax",
                error_type=SQLErrorType.SYNTAX_ERROR,
                confidence=0.95,
                description="MySQL语法错误",
                suggested_fix="检查SQL语法，特别是关键字拼写和标点符号"
            ),
            ErrorPattern(
                pattern=r"Unknown column '([^']+)' in '([^']+)'",
                error_type=SQLErrorType.FIELD_NOT_EXISTS,
                confidence=0.98,
                description="字段不存在错误",
                suggested_fix="检查字段名是否正确，或者字段是否在指定的表中"
            ),
            ErrorPattern(
                pattern=r"Table '([^']+)' doesn't exist",
                error_type=SQLErrorType.TABLE_NOT_EXISTS,
                confidence=0.98,
                description="表不存在错误",
                suggested_fix="检查表名是否正确，或者表是否在当前数据库中"
            ),
            ErrorPattern(
                pattern=r"Incorrect.*?value.*?for column",
                error_type=SQLErrorType.TYPE_MISMATCH,
                confidence=0.90,
                description="数据类型不匹配错误",
                suggested_fix="检查数据类型是否匹配字段定义"
            ),
            
            # SQL Server错误模式
            ErrorPattern(
                pattern=r"Incorrect syntax near '([^']+)'",
                error_type=SQLErrorType.SYNTAX_ERROR,
                confidence=0.90,
                description="SQL Server语法错误",
                suggested_fix="检查SQL语法，特别是关键字和操作符"
            ),
            ErrorPattern(
                pattern=r"Invalid column name '([^']+)'",
                error_type=SQLErrorType.FIELD_NOT_EXISTS,
                confidence=0.95,
                description="SQL Server字段不存在错误",
                suggested_fix="检查字段名是否正确"
            ),
            ErrorPattern(
                pattern=r"Invalid object name '([^']+)'",
                error_type=SQLErrorType.TABLE_NOT_EXISTS,
                confidence=0.95,
                description="SQL Server表不存在错误",
                suggested_fix="检查表名是否正确"
            ),
            
            # 权限错误模式
            ErrorPattern(
                pattern=r"Access denied for user '([^']+)'",
                error_type=SQLErrorType.PERMISSION_ERROR,
                confidence=0.95,
                description="访问权限被拒绝",
                suggested_fix="检查用户权限设置"
            ),
            ErrorPattern(
                pattern=r"SELECT command denied to user '([^']+)'",
                error_type=SQLErrorType.PERMISSION_ERROR,
                confidence=0.98,
                description="SELECT权限被拒绝",
                suggested_fix="为用户授予SELECT权限"
            ),
            
            # 连接错误模式
            ErrorPattern(
                pattern=r"Can't connect to MySQL server",
                error_type=SQLErrorType.CONNECTION_ERROR,
                confidence=0.95,
                description="无法连接到MySQL服务器",
                suggested_fix="检查数据库服务器状态和网络连接"
            ),
            ErrorPattern(
                pattern=r"Connection timed out",
                error_type=SQLErrorType.TIMEOUT_ERROR,
                confidence=0.90,
                description="连接超时",
                suggested_fix="检查网络连接或增加超时时间"
            ),
            
            # 约束违反错误模式
            ErrorPattern(
                pattern=r"Duplicate entry '([^']+)' for key '([^']+)'",
                error_type=SQLErrorType.CONSTRAINT_VIOLATION,
                confidence=0.95,
                description="唯一约束违反",
                suggested_fix="检查是否存在重复数据"
            ),
        ]
    
    def classify_error(self, error_message: str, sql_statement: str) -> SQLError:
        """
        分类SQL错误
        
        Args:
            error_message: 错误消息
            sql_statement: SQL语句
            
        Returns:
            SQLError: 分类后的错误信息
        """
        try:
            # 尝试匹配已知错误模式
            for pattern in self.error_patterns:
                match = re.search(pattern.pattern, error_message, re.IGNORECASE)
                if match:
                    sql_error = self._create_sql_error_from_pattern(
                        pattern, error_message, sql_statement, match
                    )
                    self._add_to_history(sql_error)
                    return sql_error
            
            # 如果没有匹配到已知模式，尝试基于关键词分类
            sql_error = self._classify_by_keywords(error_message, sql_statement)
            self._add_to_history(sql_error)
            return sql_error
            
        except Exception as e:
            logger.error(f"Error classifying SQL error: {e}")
            return SQLError(
                error_type=SQLErrorType.UNKNOWN_ERROR,
                original_error=error_message,
                error_message="未知错误类型",
                sql_statement=sql_statement,
                confidence=0.0
            )
    
    def _create_sql_error_from_pattern(
        self, 
        pattern: ErrorPattern, 
        error_message: str, 
        sql_statement: str,
        match: re.Match
    ) -> SQLError:
        """从匹配的模式创建SQL错误对象"""
        sql_error = SQLError(
            error_type=pattern.error_type,
            original_error=error_message,
            error_message=pattern.description,
            sql_statement=sql_statement,
            confidence=pattern.confidence
        )
        
        # 根据错误类型提取额外信息
        if pattern.error_type == SQLErrorType.FIELD_NOT_EXISTS:
            if match.groups():
                sql_error.suggested_fields = [match.group(1)]
                if len(match.groups()) > 1:
                    sql_error.error_location = match.group(2)
        
        elif pattern.error_type == SQLErrorType.TABLE_NOT_EXISTS:
            if match.groups():
                sql_error.suggested_tables = [match.group(1)]
        
        # 设置重试策略
        sql_error.retry_strategy = self._determine_retry_strategy(pattern.error_type)
        
        return sql_error
    
    def _classify_by_keywords(self, error_message: str, sql_statement: str) -> SQLError:
        """基于关键词分类错误"""
        error_message_lower = error_message.lower()
        
        # 语法错误关键词
        syntax_keywords = ['syntax', 'parse', 'unexpected', 'invalid syntax']
        if any(keyword in error_message_lower for keyword in syntax_keywords):
            return SQLError(
                error_type=SQLErrorType.SYNTAX_ERROR,
                original_error=error_message,
                error_message="SQL语法错误",
                sql_statement=sql_statement,
                retry_strategy=RetryStrategy.REGENERATE_SQL,
                confidence=0.7
            )
        
        # 字段不存在关键词
        field_keywords = ['column', 'field', 'unknown column', 'invalid column']
        if any(keyword in error_message_lower for keyword in field_keywords):
            return SQLError(
                error_type=SQLErrorType.FIELD_NOT_EXISTS,
                original_error=error_message,
                error_message="字段不存在",
                sql_statement=sql_statement,
                retry_strategy=RetryStrategy.REGENERATE_SQL,
                confidence=0.6
            )
        
        # 表不存在关键词
        table_keywords = ['table', 'relation', "doesn't exist", 'not found']
        if any(keyword in error_message_lower for keyword in table_keywords):
            return SQLError(
                error_type=SQLErrorType.TABLE_NOT_EXISTS,
                original_error=error_message,
                error_message="表不存在",
                sql_statement=sql_statement,
                retry_strategy=RetryStrategy.CLARIFY_INTENT,
                confidence=0.6
            )
        
        # 权限错误关键词
        permission_keywords = ['access denied', 'permission', 'privilege', 'unauthorized']
        if any(keyword in error_message_lower for keyword in permission_keywords):
            return SQLError(
                error_type=SQLErrorType.PERMISSION_ERROR,
                original_error=error_message,
                error_message="权限不足",
                sql_statement=sql_statement,
                retry_strategy=RetryStrategy.NO_RETRY,
                confidence=0.8
            )
        
        # 连接错误关键词
        connection_keywords = ['connection', 'connect', 'timeout', 'network']
        if any(keyword in error_message_lower for keyword in connection_keywords):
            return SQLError(
                error_type=SQLErrorType.CONNECTION_ERROR,
                original_error=error_message,
                error_message="连接错误",
                sql_statement=sql_statement,
                retry_strategy=RetryStrategy.BACKOFF_RETRY,
                confidence=0.7
            )
        
        # 默认未知错误
        return SQLError(
            error_type=SQLErrorType.UNKNOWN_ERROR,
            original_error=error_message,
            error_message="未知错误",
            sql_statement=sql_statement,
            retry_strategy=RetryStrategy.NO_RETRY,
            confidence=0.0
        )
    
    def _determine_retry_strategy(self, error_type: SQLErrorType) -> RetryStrategy:
        """确定重试策略"""
        strategy_map = {
            SQLErrorType.SYNTAX_ERROR: RetryStrategy.REGENERATE_SQL,
            SQLErrorType.FIELD_NOT_EXISTS: RetryStrategy.REGENERATE_SQL,
            SQLErrorType.TABLE_NOT_EXISTS: RetryStrategy.CLARIFY_INTENT,
            SQLErrorType.TYPE_MISMATCH: RetryStrategy.REGENERATE_SQL,
            SQLErrorType.PERMISSION_ERROR: RetryStrategy.NO_RETRY,
            SQLErrorType.CONNECTION_ERROR: RetryStrategy.BACKOFF_RETRY,
            SQLErrorType.CONSTRAINT_VIOLATION: RetryStrategy.REGENERATE_SQL,
            SQLErrorType.TIMEOUT_ERROR: RetryStrategy.IMMEDIATE_RETRY,
            SQLErrorType.UNKNOWN_ERROR: RetryStrategy.NO_RETRY,
        }
        return strategy_map.get(error_type, RetryStrategy.NO_RETRY)
    
    def _add_to_history(self, sql_error: SQLError):
        """添加错误到历史记录"""
        self.error_history.append(sql_error)
        
        # 保持历史记录大小限制
        if len(self.error_history) > 1000:
            self.error_history = self.error_history[-500:]
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """获取错误统计信息"""
        if not self.error_history:
            return {"total_errors": 0}
        
        error_counts = {}
        for error in self.error_history:
            error_type = error.error_type.value
            error_counts[error_type] = error_counts.get(error_type, 0) + 1
        
        recent_errors = [
            error for error in self.error_history 
            if error.timestamp > datetime.now() - timedelta(hours=24)
        ]
        
        return {
            "total_errors": len(self.error_history),
            "error_counts": error_counts,
            "recent_errors_24h": len(recent_errors),
            "most_common_error": max(error_counts.items(), key=lambda x: x[1])[0] if error_counts else None
        }
    
    def learn_from_error_pattern(self, error_message: str, correct_classification: SQLErrorType):
        """从错误模式中学习"""
        if not self.pattern_learning_enabled:
            return
        
        # 简单的学习机制：如果分类错误，降低对应模式的置信度
        classified_error = self.classify_error(error_message, "")
        if classified_error.error_type != correct_classification:
            # 找到匹配的模式并降低置信度
            for pattern in self.error_patterns:
                if re.search(pattern.pattern, error_message, re.IGNORECASE):
                    pattern.confidence = max(0.1, pattern.confidence - 0.1)
                    logger.info(f"Reduced confidence for pattern: {pattern.pattern}")
                    break


class SQLErrorRetryHandler:
    """SQL错误重试处理器"""
    
    def __init__(self, classifier: SQLErrorClassifier):
        self.classifier = classifier
        self.retry_config = RetryConfig()
        self.retry_history: Dict[str, List[SQLError]] = {}
    
    async def handle_error_with_retry(
        self,
        error_message: str,
        sql_statement: str,
        session_id: str,
        retry_callback: callable = None
    ) -> Tuple[bool, Optional[Any], SQLError]:
        """
        处理错误并执行重试
        
        Args:
            error_message: 错误消息
            sql_statement: SQL语句
            session_id: 会话ID
            retry_callback: 重试回调函数
            
        Returns:
            Tuple[bool, Optional[Any], SQLError]: (是否成功, 结果, 错误信息)
        """
        sql_error = self.classifier.classify_error(error_message, sql_statement)
        
        # 记录重试历史
        if session_id not in self.retry_history:
            self.retry_history[session_id] = []
        self.retry_history[session_id].append(sql_error)
        
        # 检查是否应该重试
        if not self._should_retry(sql_error, session_id):
            return False, None, sql_error
        
        # 执行重试策略
        success, result = await self._execute_retry_strategy(
            sql_error, session_id, retry_callback
        )
        
        return success, result, sql_error
    
    def _should_retry(self, sql_error: SQLError, session_id: str) -> bool:
        """判断是否应该重试"""
        # 检查重试策略
        if sql_error.retry_strategy == RetryStrategy.NO_RETRY:
            return False
        
        # 检查重试次数限制
        session_errors = self.retry_history.get(session_id, [])
        retry_count = len([e for e in session_errors if e.error_type == sql_error.error_type])
        
        if retry_count >= self.retry_config.max_retries:
            logger.warning(f"Max retries exceeded for error type: {sql_error.error_type}")
            return False
        
        return True
    
    async def _execute_retry_strategy(
        self,
        sql_error: SQLError,
        session_id: str,
        retry_callback: callable
    ) -> Tuple[bool, Optional[Any]]:
        """执行重试策略"""
        if not retry_callback:
            return False, None
        
        try:
            if sql_error.retry_strategy == RetryStrategy.IMMEDIATE_RETRY:
                return await retry_callback("immediate", sql_error)
            
            elif sql_error.retry_strategy == RetryStrategy.BACKOFF_RETRY:
                # 计算退避延迟
                retry_count = len(self.retry_history.get(session_id, []))
                delay = min(
                    self.retry_config.base_delay * (self.retry_config.backoff_factor ** retry_count),
                    self.retry_config.max_delay
                )
                
                await asyncio.sleep(delay)
                return await retry_callback("backoff", sql_error)
            
            elif sql_error.retry_strategy == RetryStrategy.REGENERATE_SQL:
                return await retry_callback("regenerate", sql_error)
            
            elif sql_error.retry_strategy == RetryStrategy.CLARIFY_INTENT:
                return await retry_callback("clarify", sql_error)
            
            else:
                return False, None
                
        except Exception as e:
            logger.error(f"Error executing retry strategy: {e}")
            return False, None
    
    def get_retry_statistics(self, session_id: str) -> Dict[str, Any]:
        """获取重试统计信息"""
        session_errors = self.retry_history.get(session_id, [])
        
        if not session_errors:
            return {"total_retries": 0}
        
        retry_counts = {}
        for error in session_errors:
            error_type = error.error_type.value
            retry_counts[error_type] = retry_counts.get(error_type, 0) + 1
        
        return {
            "total_retries": len(session_errors),
            "retry_counts": retry_counts,
            "last_error_type": session_errors[-1].error_type.value if session_errors else None
        }


class ErrorFeedbackGenerator:
    """错误反馈生成器"""
    
    def __init__(self, classifier: SQLErrorClassifier):
        self.classifier = classifier
    
    def generate_feedback_for_ai(self, sql_error: SQLError, context: Dict[str, Any]) -> ErrorFeedback:
        """
        为AI模型生成结构化错误反馈
        
        Args:
            sql_error: SQL错误信息
            context: 上下文信息
            
        Returns:
            ErrorFeedback: 结构化错误反馈
        """
        feedback_message = self._build_feedback_message(sql_error, context)
        
        return ErrorFeedback(
            session_id=context.get("session_id", ""),
            original_question=context.get("original_question", ""),
            generated_sql=sql_error.sql_statement,
            error_info=sql_error,
            context=context,
            feedback_for_ai=feedback_message
        )
    
    def _build_feedback_message(self, sql_error: SQLError, context: Dict[str, Any]) -> str:
        """构建反馈消息"""
        feedback_parts = []
        
        # 基本错误信息
        feedback_parts.append(f"SQL执行失败，错误类型：{sql_error.error_type.value}")
        feedback_parts.append(f"错误描述：{sql_error.error_message}")
        
        # 根据错误类型提供具体建议
        if sql_error.error_type == SQLErrorType.FIELD_NOT_EXISTS:
            feedback_parts.append("建议：检查字段名是否正确，或者字段是否在指定的表中")
            if sql_error.suggested_fields:
                feedback_parts.append(f"可能的字段名：{', '.join(sql_error.suggested_fields)}")
        
        elif sql_error.error_type == SQLErrorType.TABLE_NOT_EXISTS:
            feedback_parts.append("建议：检查表名是否正确，或者表是否在当前数据库中")
            if sql_error.suggested_tables:
                feedback_parts.append(f"可能的表名：{', '.join(sql_error.suggested_tables)}")
        
        elif sql_error.error_type == SQLErrorType.SYNTAX_ERROR:
            feedback_parts.append("建议：检查SQL语法，特别是关键字拼写和标点符号")
        
        elif sql_error.error_type == SQLErrorType.TYPE_MISMATCH:
            feedback_parts.append("建议：检查数据类型是否匹配字段定义")
        
        # 添加上下文信息
        if context.get("available_tables"):
            feedback_parts.append(f"可用表：{', '.join(context['available_tables'])}")
        
        if context.get("available_fields"):
            feedback_parts.append(f"可用字段：{', '.join(context['available_fields'])}")
        
        return "\n".join(feedback_parts)
    
    def format_feedback_for_logging(self, feedback: ErrorFeedback) -> str:
        """格式化反馈信息用于日志记录"""
        return json.dumps({
            "session_id": feedback.session_id,
            "error_type": feedback.error_info.error_type.value,
            "error_message": feedback.error_info.error_message,
            "sql_statement": feedback.generated_sql,
            "timestamp": feedback.timestamp.isoformat(),
            "feedback": feedback.feedback_for_ai
        }, ensure_ascii=False, indent=2)


class SQLErrorRecoveryService:
    """SQL错误恢复服务"""
    
    def __init__(self):
        self.classifier = SQLErrorClassifier()
        self.retry_handler = SQLErrorRetryHandler(self.classifier)
        self.feedback_generator = ErrorFeedbackGenerator(self.classifier)
    
    async def handle_sql_error(
        self,
        error_message: str,
        sql_statement: str,
        session_id: str,
        context: Dict[str, Any],
        retry_callback: callable = None
    ) -> Dict[str, Any]:
        """
        处理SQL错误的主入口
        
        Args:
            error_message: 错误消息
            sql_statement: SQL语句
            session_id: 会话ID
            context: 上下文信息
            retry_callback: 重试回调函数
            
        Returns:
            Dict[str, Any]: 处理结果
        """
        try:
            # 分类错误
            sql_error = self.classifier.classify_error(error_message, sql_statement)
            
            # 生成反馈
            feedback = self.feedback_generator.generate_feedback_for_ai(sql_error, context)
            
            # 尝试重试
            success, result, _ = await self.retry_handler.handle_error_with_retry(
                error_message, sql_statement, session_id, retry_callback
            )
            
            # 记录日志
            logger.info(f"SQL error handled: {sql_error.error_type.value}")
            logger.debug(self.feedback_generator.format_feedback_for_logging(feedback))
            
            return {
                "success": success,
                "result": result,
                "error_info": asdict(sql_error),
                "feedback": asdict(feedback),
                "retry_statistics": self.retry_handler.get_retry_statistics(session_id)
            }
            
        except Exception as e:
            logger.error(f"Error in SQL error recovery service: {e}")
            return {
                "success": False,
                "result": None,
                "error_info": {"error_type": "service_error", "message": str(e)},
                "feedback": None,
                "retry_statistics": {}
            }
    
    def get_service_statistics(self) -> Dict[str, Any]:
        """获取服务统计信息"""
        return {
            "classifier_stats": self.classifier.get_error_statistics(),
            "total_sessions": len(self.retry_handler.retry_history)
        }
    
    def learn_from_feedback(self, error_message: str, correct_classification: str):
        """从反馈中学习"""
        try:
            error_type = SQLErrorType(correct_classification)
            self.classifier.learn_from_error_pattern(error_message, error_type)
        except ValueError:
            logger.warning(f"Invalid error type for learning: {correct_classification}")