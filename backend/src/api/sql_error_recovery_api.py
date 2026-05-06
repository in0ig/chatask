"""
SQL错误恢复API

提供SQL错误分类、重试和反馈的API接口。
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from typing import Dict, Any, Optional, List
import logging
from datetime import datetime

from ..services.sql_error_classifier import (
    SQLErrorRecoveryService,
    SQLErrorType,
    RetryStrategy
)
from ..schemas.base_schema import BaseResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/sql-error-recovery", tags=["SQL错误恢复"])

# 全局服务实例
sql_error_recovery_service = SQLErrorRecoveryService()


class SQLErrorRequest:
    """SQL错误请求模型"""
    def __init__(
        self,
        error_message: str,
        sql_statement: str,
        session_id: str,
        context: Dict[str, Any] = None
    ):
        self.error_message = error_message
        self.sql_statement = sql_statement
        self.session_id = session_id
        self.context = context or {}


class ErrorClassificationResponse(BaseResponse):
    """错误分类响应模型"""
    def __init__(self, data: Dict[str, Any]):
        super().__init__(
            success=True,
            message="错误分类成功",
            data=data
        )


class ErrorRecoveryResponse(BaseResponse):
    """错误恢复响应模型"""
    def __init__(self, data: Dict[str, Any]):
        super().__init__(
            success=data.get("success", False),
            message="错误恢复处理完成" if data.get("success") else "错误恢复失败",
            data=data
        )


@router.post("/classify", response_model=ErrorClassificationResponse)
async def classify_sql_error(
    error_message: str,
    sql_statement: str,
    session_id: Optional[str] = None
):
    """
    分类SQL错误
    
    Args:
        error_message: 错误消息
        sql_statement: SQL语句
        session_id: 会话ID（可选）
    
    Returns:
        ErrorClassificationResponse: 错误分类结果
    """
    try:
        sql_error = sql_error_recovery_service.classifier.classify_error(
            error_message, sql_statement
        )
        
        return ErrorClassificationResponse({
            "error_type": sql_error.error_type.value,
            "error_message": sql_error.error_message,
            "confidence": sql_error.confidence,
            "retry_strategy": sql_error.retry_strategy.value,
            "suggested_fields": sql_error.suggested_fields,
            "suggested_tables": sql_error.suggested_tables,
            "error_location": sql_error.error_location,
            "timestamp": sql_error.timestamp.isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error classifying SQL error: {e}")
        raise HTTPException(status_code=500, detail=f"错误分类失败: {str(e)}")


@router.post("/recover", response_model=ErrorRecoveryResponse)
async def recover_from_sql_error(
    error_message: str,
    sql_statement: str,
    session_id: str,
    context: Dict[str, Any] = None,
    enable_retry: bool = True
):
    """
    从SQL错误中恢复
    
    Args:
        error_message: 错误消息
        sql_statement: SQL语句
        session_id: 会话ID
        context: 上下文信息
        enable_retry: 是否启用重试
    
    Returns:
        ErrorRecoveryResponse: 错误恢复结果
    """
    try:
        # 定义重试回调函数（这里是示例，实际应该根据业务需求实现）
        async def retry_callback(retry_type: str, sql_error):
            logger.info(f"Executing retry strategy: {retry_type}")
            # 这里应该实现具体的重试逻辑
            # 例如：重新生成SQL、澄清意图等
            return False, None  # 示例返回
        
        result = await sql_error_recovery_service.handle_sql_error(
            error_message=error_message,
            sql_statement=sql_statement,
            session_id=session_id,
            context=context or {},
            retry_callback=retry_callback if enable_retry else None
        )
        
        return ErrorRecoveryResponse(result)
        
    except Exception as e:
        logger.error(f"Error in SQL error recovery: {e}")
        raise HTTPException(status_code=500, detail=f"错误恢复失败: {str(e)}")


@router.post("/feedback", response_model=BaseResponse)
async def generate_error_feedback(
    error_message: str,
    sql_statement: str,
    session_id: str,
    original_question: str,
    context: Dict[str, Any] = None
):
    """
    生成错误反馈
    
    Args:
        error_message: 错误消息
        sql_statement: SQL语句
        session_id: 会话ID
        original_question: 原始问题
        context: 上下文信息
    
    Returns:
        BaseResponse: 错误反馈结果
    """
    try:
        # 分类错误
        sql_error = sql_error_recovery_service.classifier.classify_error(
            error_message, sql_statement
        )
        
        # 准备上下文
        feedback_context = context or {}
        feedback_context.update({
            "session_id": session_id,
            "original_question": original_question
        })
        
        # 生成反馈
        feedback = sql_error_recovery_service.feedback_generator.generate_feedback_for_ai(
            sql_error, feedback_context
        )
        
        return BaseResponse(
            success=True,
            message="错误反馈生成成功",
            data={
                "feedback_for_ai": feedback.feedback_for_ai,
                "error_type": feedback.error_info.error_type.value,
                "error_message": feedback.error_info.error_message,
                "confidence": feedback.error_info.confidence,
                "timestamp": feedback.timestamp.isoformat()
            }
        )
        
    except Exception as e:
        logger.error(f"Error generating feedback: {e}")
        raise HTTPException(status_code=500, detail=f"反馈生成失败: {str(e)}")


@router.get("/statistics", response_model=BaseResponse)
async def get_error_statistics(session_id: Optional[str] = None):
    """
    获取错误统计信息
    
    Args:
        session_id: 会话ID（可选，如果提供则返回该会话的统计信息）
    
    Returns:
        BaseResponse: 统计信息
    """
    try:
        if session_id:
            # 获取特定会话的统计信息
            retry_stats = sql_error_recovery_service.retry_handler.get_retry_statistics(session_id)
            return BaseResponse(
                success=True,
                message="会话统计信息获取成功",
                data={
                    "session_id": session_id,
                    "retry_statistics": retry_stats
                }
            )
        else:
            # 获取全局统计信息
            service_stats = sql_error_recovery_service.get_service_statistics()
            return BaseResponse(
                success=True,
                message="全局统计信息获取成功",
                data=service_stats
            )
        
    except Exception as e:
        logger.error(f"Error getting statistics: {e}")
        raise HTTPException(status_code=500, detail=f"统计信息获取失败: {str(e)}")


@router.post("/learn", response_model=BaseResponse)
async def learn_from_error(
    error_message: str,
    correct_classification: str,
    background_tasks: BackgroundTasks
):
    """
    从错误中学习
    
    Args:
        error_message: 错误消息
        correct_classification: 正确的分类
        background_tasks: 后台任务
    
    Returns:
        BaseResponse: 学习结果
    """
    try:
        # 验证分类是否有效
        try:
            SQLErrorType(correct_classification)
        except ValueError:
            raise HTTPException(
                status_code=400, 
                detail=f"无效的错误分类: {correct_classification}"
            )
        
        # 在后台执行学习任务
        background_tasks.add_task(
            sql_error_recovery_service.learn_from_feedback,
            error_message,
            correct_classification
        )
        
        return BaseResponse(
            success=True,
            message="学习任务已提交",
            data={
                "error_message": error_message,
                "correct_classification": correct_classification,
                "timestamp": datetime.now().isoformat()
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in learning from error: {e}")
        raise HTTPException(status_code=500, detail=f"学习失败: {str(e)}")


@router.get("/error-types", response_model=BaseResponse)
async def get_error_types():
    """
    获取支持的错误类型列表
    
    Returns:
        BaseResponse: 错误类型列表
    """
    try:
        error_types = [
            {
                "value": error_type.value,
                "name": error_type.name,
                "description": _get_error_type_description(error_type)
            }
            for error_type in SQLErrorType
        ]
        
        return BaseResponse(
            success=True,
            message="错误类型列表获取成功",
            data={"error_types": error_types}
        )
        
    except Exception as e:
        logger.error(f"Error getting error types: {e}")
        raise HTTPException(status_code=500, detail=f"错误类型获取失败: {str(e)}")


@router.get("/retry-strategies", response_model=BaseResponse)
async def get_retry_strategies():
    """
    获取支持的重试策略列表
    
    Returns:
        BaseResponse: 重试策略列表
    """
    try:
        retry_strategies = [
            {
                "value": strategy.value,
                "name": strategy.name,
                "description": _get_retry_strategy_description(strategy)
            }
            for strategy in RetryStrategy
        ]
        
        return BaseResponse(
            success=True,
            message="重试策略列表获取成功",
            data={"retry_strategies": retry_strategies}
        )
        
    except Exception as e:
        logger.error(f"Error getting retry strategies: {e}")
        raise HTTPException(status_code=500, detail=f"重试策略获取失败: {str(e)}")


@router.get("/health", response_model=BaseResponse)
async def health_check():
    """
    健康检查
    
    Returns:
        BaseResponse: 健康状态
    """
    try:
        stats = sql_error_recovery_service.get_service_statistics()
        
        return BaseResponse(
            success=True,
            message="SQL错误恢复服务运行正常",
            data={
                "service_status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "statistics": stats
            }
        )
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=500, detail=f"健康检查失败: {str(e)}")


def _get_error_type_description(error_type: SQLErrorType) -> str:
    """获取错误类型描述"""
    descriptions = {
        SQLErrorType.SYNTAX_ERROR: "SQL语法错误",
        SQLErrorType.FIELD_NOT_EXISTS: "字段不存在错误",
        SQLErrorType.TABLE_NOT_EXISTS: "表不存在错误",
        SQLErrorType.TYPE_MISMATCH: "数据类型不匹配错误",
        SQLErrorType.PERMISSION_ERROR: "权限错误",
        SQLErrorType.CONNECTION_ERROR: "连接错误",
        SQLErrorType.CONSTRAINT_VIOLATION: "约束违反错误",
        SQLErrorType.TIMEOUT_ERROR: "超时错误",
        SQLErrorType.UNKNOWN_ERROR: "未知错误"
    }
    return descriptions.get(error_type, "未知错误类型")


def _get_retry_strategy_description(strategy: RetryStrategy) -> str:
    """获取重试策略描述"""
    descriptions = {
        RetryStrategy.NO_RETRY: "不重试",
        RetryStrategy.IMMEDIATE_RETRY: "立即重试",
        RetryStrategy.BACKOFF_RETRY: "退避重试",
        RetryStrategy.REGENERATE_SQL: "重新生成SQL",
        RetryStrategy.CLARIFY_INTENT: "澄清意图"
    }
    return descriptions.get(strategy, "未知重试策略")