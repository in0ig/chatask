"""
SQL错误反馈学习循环API

提供错误学习、模式识别和AI反馈的API接口。
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from typing import Dict, Any, Optional, List
import logging
from datetime import datetime

from ..services.sql_error_learning_service import (
    SQLErrorLearningService,
    LearningSession,
    AIFeedbackMessage,
    ErrorPattern
)
from ..services.sql_error_classifier import SQLErrorRecoveryService, SQLError, SQLErrorType
from ..schemas.base_schema import BaseResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/sql-error-learning", tags=["SQL错误学习"])

# 全局服务实例
error_recovery_service = SQLErrorRecoveryService()
learning_service = SQLErrorLearningService(error_recovery_service)


class LearningSessionRequest:
    """学习会话请求模型"""
    def __init__(self, session_id: str, original_question: str):
        self.session_id = session_id
        self.original_question = original_question


class ErrorRecordRequest:
    """错误记录请求模型"""
    def __init__(
        self,
        session_id: str,
        error_message: str,
        sql_statement: str,
        context: Dict[str, Any] = None
    ):
        self.session_id = session_id
        self.error_message = error_message
        self.sql_statement = sql_statement
        self.context = context or {}


class SuccessRecordRequest:
    """成功记录请求模型"""
    def __init__(self, session_id: str, successful_sql: str):
        self.session_id = session_id
        self.successful_sql = successful_sql


class FeedbackRequest:
    """反馈请求模型"""
    def __init__(self, session_id: str, context: Dict[str, Any] = None):
        self.session_id = session_id
        self.context = context or {}


@router.post("/sessions/start", response_model=BaseResponse)
async def start_learning_session(
    session_id: str,
    original_question: str
):
    """
    开始学习会话
    
    Args:
        session_id: 会话ID
        original_question: 原始问题
    
    Returns:
        BaseResponse: 学习会话信息
    """
    try:
        learning_session = await learning_service.start_learning_session(
            session_id, original_question
        )
        
        return BaseResponse(
            success=True,
            message="学习会话已开始",
            data={
                "session_id": learning_session.session_id,
                "original_question": learning_session.original_question,
                "created_at": learning_session.created_at.isoformat()
            }
        )
        
    except Exception as e:
        logger.error(f"Error starting learning session: {e}")
        raise HTTPException(status_code=500, detail=f"开始学习会话失败: {str(e)}")


@router.post("/errors/record", response_model=BaseResponse)
async def record_error(
    session_id: str,
    error_message: str,
    sql_statement: str,
    context: Dict[str, Any] = None
):
    """
    记录错误并学习
    
    Args:
        session_id: 会话ID
        error_message: 错误消息
        sql_statement: SQL语句
        context: 上下文信息
    
    Returns:
        BaseResponse: 错误记录结果
    """
    try:
        # 首先分类错误
        sql_error = error_recovery_service.classifier.classify_error(
            error_message, sql_statement
        )
        
        # 记录错误并学习
        learned_pattern = await learning_service.record_error(
            session_id, sql_error, context or {}
        )
        
        response_data = {
            "session_id": session_id,
            "error_recorded": True,
            "error_type": sql_error.error_type.value,
            "error_confidence": sql_error.confidence,
            "timestamp": datetime.now().isoformat()
        }
        
        if learned_pattern:
            response_data["learned_pattern"] = {
                "pattern_id": learned_pattern.pattern_id,
                "frequency": learned_pattern.frequency,
                "confidence": learned_pattern.confidence
            }
        
        return BaseResponse(
            success=True,
            message="错误已记录并学习",
            data=response_data
        )
        
    except Exception as e:
        logger.error(f"Error recording error: {e}")
        raise HTTPException(status_code=500, detail=f"错误记录失败: {str(e)}")


@router.post("/success/record", response_model=BaseResponse)
async def record_success(
    session_id: str,
    successful_sql: str
):
    """
    记录成功的SQL
    
    Args:
        session_id: 会话ID
        successful_sql: 成功的SQL
    
    Returns:
        BaseResponse: 成功记录结果
    """
    try:
        await learning_service.record_success(session_id, successful_sql)
        
        return BaseResponse(
            success=True,
            message="成功SQL已记录",
            data={
                "session_id": session_id,
                "successful_sql": successful_sql,
                "timestamp": datetime.now().isoformat()
            }
        )
        
    except Exception as e:
        logger.error(f"Error recording success: {e}")
        raise HTTPException(status_code=500, detail=f"成功记录失败: {str(e)}")


@router.post("/feedback/generate", response_model=BaseResponse)
async def generate_ai_feedback(
    session_id: str,
    context: Dict[str, Any] = None
):
    """
    为AI模型生成反馈
    
    Args:
        session_id: 会话ID
        context: 上下文信息
    
    Returns:
        BaseResponse: AI反馈信息
    """
    try:
        feedback = await learning_service.generate_feedback_for_ai(
            session_id, context or {}
        )
        
        if not feedback:
            return BaseResponse(
                success=False,
                message="无法生成反馈：会话不存在或无错误记录",
                data={"session_id": session_id}
            )
        
        # 格式化反馈供AI模型使用
        formatted_feedback = learning_service.feedback_generator.format_feedback_for_ai_model(feedback)
        
        return BaseResponse(
            success=True,
            message="AI反馈已生成",
            data={
                "message_id": feedback.message_id,
                "session_id": feedback.session_id,
                "feedback_type": feedback.feedback_type,
                "error_analysis": feedback.error_analysis,
                "suggested_improvements": feedback.suggested_improvements,
                "formatted_feedback": formatted_feedback,
                "timestamp": feedback.timestamp.isoformat()
            }
        )
        
    except Exception as e:
        logger.error(f"Error generating AI feedback: {e}")
        raise HTTPException(status_code=500, detail=f"反馈生成失败: {str(e)}")


@router.get("/patterns", response_model=BaseResponse)
async def get_error_patterns(
    min_frequency: Optional[int] = None,
    error_type: Optional[str] = None
):
    """
    获取错误模式
    
    Args:
        min_frequency: 最小频率（可选）
        error_type: 错误类型过滤（可选）
    
    Returns:
        BaseResponse: 错误模式列表
    """
    try:
        # 获取频繁模式
        frequent_patterns = learning_service.pattern_learner.get_frequent_patterns(min_frequency)
        
        # 按错误类型过滤
        if error_type:
            try:
                filter_type = SQLErrorType(error_type)
                frequent_patterns = [p for p in frequent_patterns if p.error_type == filter_type]
            except ValueError:
                raise HTTPException(status_code=400, detail=f"无效的错误类型: {error_type}")
        
        patterns_data = []
        for pattern in frequent_patterns:
            patterns_data.append({
                "pattern_id": pattern.pattern_id,
                "error_type": pattern.error_type.value,
                "frequency": pattern.frequency,
                "confidence": pattern.confidence,
                "context_keywords": pattern.context_keywords,
                "common_fixes": pattern.common_fixes,
                "success_rate_after_fix": pattern.success_rate_after_fix,
                "created_at": pattern.created_at.isoformat(),
                "last_seen": pattern.last_seen.isoformat()
            })
        
        return BaseResponse(
            success=True,
            message="错误模式获取成功",
            data={
                "patterns": patterns_data,
                "total_patterns": len(patterns_data),
                "filter_applied": {
                    "min_frequency": min_frequency,
                    "error_type": error_type
                }
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting error patterns: {e}")
        raise HTTPException(status_code=500, detail=f"错误模式获取失败: {str(e)}")


@router.get("/predictions", response_model=BaseResponse)
async def get_error_predictions(
    original_question: Optional[str] = None,
    table_names: Optional[List[str]] = None,
    field_names: Optional[List[str]] = None
):
    """
    获取错误预测
    
    Args:
        original_question: 原始问题（可选）
        table_names: 表名列表（可选）
        field_names: 字段名列表（可选）
    
    Returns:
        BaseResponse: 错误预测结果
    """
    try:
        context = {}
        if original_question:
            context["original_question"] = original_question
        if table_names:
            context["table_names"] = table_names
        if field_names:
            context["field_names"] = field_names
        
        predictions = learning_service.get_error_predictions(context)
        
        return BaseResponse(
            success=True,
            message="错误预测获取成功",
            data={
                "predictions": predictions,
                "context": context,
                "timestamp": datetime.now().isoformat()
            }
        )
        
    except Exception as e:
        logger.error(f"Error getting error predictions: {e}")
        raise HTTPException(status_code=500, detail=f"错误预测失败: {str(e)}")


@router.get("/suggestions/{session_id}", response_model=BaseResponse)
async def get_improvement_suggestions(session_id: str):
    """
    获取改进建议
    
    Args:
        session_id: 会话ID
    
    Returns:
        BaseResponse: 改进建议
    """
    try:
        suggestions = learning_service.get_improvement_suggestions(session_id)
        
        return BaseResponse(
            success=True,
            message="改进建议获取成功",
            data={
                "session_id": session_id,
                "suggestions": suggestions,
                "suggestion_count": len(suggestions),
                "timestamp": datetime.now().isoformat()
            }
        )
        
    except Exception as e:
        logger.error(f"Error getting improvement suggestions: {e}")
        raise HTTPException(status_code=500, detail=f"改进建议获取失败: {str(e)}")


@router.get("/statistics", response_model=BaseResponse)
async def get_learning_statistics():
    """
    获取学习统计信息
    
    Returns:
        BaseResponse: 学习统计信息
    """
    try:
        stats = learning_service.get_learning_statistics()
        
        return BaseResponse(
            success=True,
            message="学习统计信息获取成功",
            data=stats
        )
        
    except Exception as e:
        logger.error(f"Error getting learning statistics: {e}")
        raise HTTPException(status_code=500, detail=f"学习统计信息获取失败: {str(e)}")


@router.post("/sessions/cleanup", response_model=BaseResponse)
async def cleanup_old_sessions(
    max_age_hours: int = 24,
    background_tasks: BackgroundTasks = None
):
    """
    清理旧的学习会话
    
    Args:
        max_age_hours: 最大保留时间（小时）
        background_tasks: 后台任务
    
    Returns:
        BaseResponse: 清理结果
    """
    try:
        if background_tasks:
            background_tasks.add_task(
                learning_service.cleanup_old_sessions,
                max_age_hours
            )
            message = "清理任务已提交到后台执行"
        else:
            learning_service.cleanup_old_sessions(max_age_hours)
            message = "清理任务已完成"
        
        return BaseResponse(
            success=True,
            message=message,
            data={
                "max_age_hours": max_age_hours,
                "timestamp": datetime.now().isoformat()
            }
        )
        
    except Exception as e:
        logger.error(f"Error cleaning up sessions: {e}")
        raise HTTPException(status_code=500, detail=f"会话清理失败: {str(e)}")


@router.get("/export", response_model=BaseResponse)
async def export_learning_data():
    """
    导出学习数据
    
    Returns:
        BaseResponse: 学习数据导出
    """
    try:
        learning_data = learning_service.export_learning_data()
        
        return BaseResponse(
            success=True,
            message="学习数据导出成功",
            data={
                "export_timestamp": datetime.now().isoformat(),
                "learning_data": learning_data
            }
        )
        
    except Exception as e:
        logger.error(f"Error exporting learning data: {e}")
        raise HTTPException(status_code=500, detail=f"学习数据导出失败: {str(e)}")


@router.post("/patterns/learn", response_model=BaseResponse)
async def learn_from_pattern(
    error_message: str,
    correct_classification: str,
    background_tasks: BackgroundTasks
):
    """
    从错误模式中学习
    
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
            learning_service.pattern_learner.learn_from_error_pattern,
            error_message,
            SQLErrorType(correct_classification)
        )
        
        return BaseResponse(
            success=True,
            message="模式学习任务已提交",
            data={
                "error_message": error_message,
                "correct_classification": correct_classification,
                "timestamp": datetime.now().isoformat()
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in pattern learning: {e}")
        raise HTTPException(status_code=500, detail=f"模式学习失败: {str(e)}")


@router.get("/health", response_model=BaseResponse)
async def health_check():
    """
    健康检查
    
    Returns:
        BaseResponse: 健康状态
    """
    try:
        stats = learning_service.get_learning_statistics()
        
        return BaseResponse(
            success=True,
            message="SQL错误学习服务运行正常",
            data={
                "service_status": "healthy",
                "learning_enabled": stats["learning_enabled"],
                "total_sessions": stats["total_learning_sessions"],
                "total_patterns": stats["pattern_statistics"]["total_patterns"],
                "timestamp": datetime.now().isoformat()
            }
        )
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=500, detail=f"健康检查失败: {str(e)}")


@router.post("/enable", response_model=BaseResponse)
async def enable_learning():
    """
    启用学习功能
    
    Returns:
        BaseResponse: 操作结果
    """
    try:
        learning_service.learning_enabled = True
        
        return BaseResponse(
            success=True,
            message="学习功能已启用",
            data={
                "learning_enabled": True,
                "timestamp": datetime.now().isoformat()
            }
        )
        
    except Exception as e:
        logger.error(f"Error enabling learning: {e}")
        raise HTTPException(status_code=500, detail=f"启用学习功能失败: {str(e)}")


@router.post("/disable", response_model=BaseResponse)
async def disable_learning():
    """
    禁用学习功能
    
    Returns:
        BaseResponse: 操作结果
    """
    try:
        learning_service.learning_enabled = False
        
        return BaseResponse(
            success=True,
            message="学习功能已禁用",
            data={
                "learning_enabled": False,
                "timestamp": datetime.now().isoformat()
            }
        )
        
    except Exception as e:
        logger.error(f"Error disabling learning: {e}")
        raise HTTPException(status_code=500, detail=f"禁用学习功能失败: {str(e)}")