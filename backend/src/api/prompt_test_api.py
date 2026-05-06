"""
Prompt 测试 API

提供独立的测试端点，用于单独测试每个阶段的 Prompt 和 AI 响应
"""

import logging
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

from src.services.chat_orchestrator import ChatOrchestrator, ChatContext
from src.services.prompt_manager import PromptManager, PromptType
from src.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/prompt-test", tags=["Prompt测试"])


class PromptTestRequest(BaseModel):
    """Prompt 测试请求"""
    user_question: str
    data_source_id: Optional[str] = None
    stage: str  # "intent", "table_selection", "sql_generation", "data_analysis"


class PromptTestResponse(BaseModel):
    """Prompt 测试响应"""
    stage: str
    rendered_prompt: str  # 实际发送给 AI 的 Prompt
    ai_response: Optional[Dict[str, Any]] = None
    semantic_context: Optional[Dict[str, Any]] = None
    success: bool
    error: Optional[str] = None


@router.post("/test-stage", response_model=PromptTestResponse)
async def test_prompt_stage(
    request: PromptTestRequest,
    db: Session = Depends(get_db)
):
    """
    测试单个阶段的 Prompt 和 AI 响应
    
    Args:
        request: 测试请求
        db: 数据库会话
        
    Returns:
        测试响应
    """
    try:
        logger.info(f"开始测试阶段: {request.stage}, 问题: {request.user_question}")
        
        orchestrator = ChatOrchestrator()
        context = ChatContext(f"test-{request.stage}")
        
        if request.stage == "intent":
            return await test_intent_recognition(
                orchestrator, context, request.user_question
            )
        elif request.stage == "table_selection":
            return await test_table_selection(
                orchestrator, context, request.user_question, request.data_source_id, db
            )
        elif request.stage == "sql_generation":
            return await test_sql_generation(
                orchestrator, context, request.user_question, request.data_source_id, db
            )
        elif request.stage == "data_analysis":
            return await test_data_analysis(
                orchestrator, context, request.user_question
            )
        else:
            raise HTTPException(status_code=400, detail=f"未知阶段: {request.stage}")
            
    except Exception as e:
        logger.error(f"测试阶段失败: {str(e)}", exc_info=True)
        return PromptTestResponse(
            stage=request.stage,
            rendered_prompt="",
            success=False,
            error=str(e)
        )


async def test_intent_recognition(
    orchestrator: ChatOrchestrator,
    context: ChatContext,
    user_question: str
) -> PromptTestResponse:
    """测试意图识别阶段"""
    try:
        logger.info("=" * 80)
        logger.info("🧪 测试意图识别阶段")
        logger.info(f"用户问题: {user_question}")
        
        # 1. 渲染 Prompt
        prompt = orchestrator.prompt_manager.render_prompt(
            PromptType.INTENT_RECOGNITION,
            {"user_question": user_question}
        )
        
        logger.info(f"✅ Prompt 渲染完成，长度: {len(prompt)}")
        logger.info(f"📝 Prompt 内容:\n{prompt}")
        
        # 2. 调用 AI
        ai_response = await orchestrator.ai_service.call_cloud_model(
            prompt,
            session_id=context.session_id,
            model_type="qwen"
        )
        
        logger.info(f"✅ AI 响应: {ai_response}")
        logger.info("=" * 80)
        
        return PromptTestResponse(
            stage="intent",
            rendered_prompt=prompt,
            ai_response=ai_response if ai_response["success"] else None,
            success=ai_response["success"],
            error=ai_response.get("error")
        )
    except Exception as e:
        logger.error(f"意图识别测试失败: {str(e)}", exc_info=True)
        return PromptTestResponse(
            stage="intent",
            rendered_prompt="",
            success=False,
            error=str(e)
        )


async def test_table_selection(
    orchestrator: ChatOrchestrator,
    context: ChatContext,
    user_question: str,
    data_source_id: Optional[str],
    db: Session
) -> PromptTestResponse:
    """测试智能选表阶段"""
    try:
        logger.info("=" * 80)
        logger.info("🧪 测试智能选表阶段")
        logger.info(f"用户问题: {user_question}")
        
        # 1. 获取语义上下文
        logger.info("📊 开始获取语义上下文...")
        
        # 重新初始化 semantic_aggregator 并传入 db session
        from src.services.semantic_context_aggregator import SemanticContextAggregator
        orchestrator.semantic_aggregator = SemanticContextAggregator(db)
        
        semantic_context_result = await orchestrator.semantic_aggregator.aggregate_semantic_context(
            user_question=user_question,
            table_ids=None,
            include_global=True
        )
        
        logger.info(f"✅ 语义上下文获取完成")
        logger.info(f"📊 使用的模块: {semantic_context_result.modules_used}")
        logger.info(f"📊 Token 使用量: {semantic_context_result.total_tokens_used}")
        logger.info(f"📊 相关性评分: {semantic_context_result.relevance_scores}")
        logger.info(f"📝 上下文内容预览:\n{semantic_context_result.enhanced_context[:500]}...")
        
        # 2. 渲染 Prompt
        prompt = orchestrator.prompt_manager.render_prompt(
            PromptType.TABLE_SELECTION,
            {
                "user_question": user_question,
                "intent_type": "smart_query",
                "semantic_context": semantic_context_result.enhanced_context
            }
        )
        
        logger.info(f"✅ Prompt 渲染完成，长度: {len(prompt)}")
        logger.info(f"📝 Prompt 内容:\n{prompt}")
        
        # 3. 调用 AI
        ai_response = await orchestrator.ai_service.call_cloud_model(
            prompt,
            session_id=context.session_id,
            model_type="qwen"
        )
        
        logger.info(f"✅ AI 响应: {ai_response}")
        logger.info("=" * 80)
        
        return PromptTestResponse(
            stage="table_selection",
            rendered_prompt=prompt,
            ai_response=ai_response if ai_response["success"] else None,
            semantic_context={
                "modules_used": semantic_context_result.modules_used,
                "total_tokens": semantic_context_result.total_tokens_used,
                "relevance_scores": semantic_context_result.relevance_scores,
                "context_preview": semantic_context_result.enhanced_context[:500] + "..."
            },
            success=ai_response["success"],
            error=ai_response.get("error")
        )
    except Exception as e:
        logger.error(f"智能选表测试失败: {str(e)}", exc_info=True)
        return PromptTestResponse(
            stage="table_selection",
            rendered_prompt="",
            success=False,
            error=str(e)
        )


async def test_sql_generation(
    orchestrator: ChatOrchestrator,
    context: ChatContext,
    user_question: str,
    data_source_id: Optional[str],
    db: Session
) -> PromptTestResponse:
    """测试 SQL 生成阶段"""
    try:
        logger.info("=" * 80)
        logger.info("🧪 测试 SQL 生成阶段")
        logger.info(f"用户问题: {user_question}")
        
        # 1. 获取语义上下文（假设已选择表）
        logger.info("📊 开始获取语义上下文...")
        
        # 重新初始化 semantic_aggregator 并传入 db session
        from src.services.semantic_context_aggregator import SemanticContextAggregator
        orchestrator.semantic_aggregator = SemanticContextAggregator(db)
        
        # 获取第一个可用的表ID用于测试
        from src.models.data_table import DataTable
        test_table = db.query(DataTable).filter(DataTable.status == True).first()
        test_table_ids = [str(test_table.id)] if test_table else []
        
        logger.info(f"📋 使用测试表ID: {test_table_ids}")
        
        semantic_context_result = await orchestrator.semantic_aggregator.aggregate_semantic_context(
            user_question=user_question,
            table_ids=test_table_ids,
            include_global=True
        )
        
        logger.info(f"✅ 语义上下文获取完成")
        logger.info(f"📊 使用的模块: {semantic_context_result.modules_used}")
        logger.info(f"📊 Token 使用量: {semantic_context_result.total_tokens_used}")
        logger.info(f"📝 上下文内容预览:\n{semantic_context_result.enhanced_context[:500]}...")
        
        # 2. 渲染 Prompt
        prompt = orchestrator.prompt_manager.render_prompt(
            PromptType.SQL_GENERATION,
            {
                "original_question": user_question,
                "clarified_requirement": user_question,
                "semantic_context": semantic_context_result.enhanced_context,
                "db_type": "MySQL"
            }
        )
        
        logger.info(f"✅ Prompt 渲染完成，长度: {len(prompt)}")
        logger.info(f"📝 Prompt 内容:\n{prompt}")
        
        # 3. 调用 AI
        ai_response = await orchestrator.ai_service.call_cloud_model(
            prompt,
            session_id=context.session_id,
            model_type="qwen"
        )
        
        logger.info(f"✅ AI 响应: {ai_response}")
        logger.info("=" * 80)
        
        return PromptTestResponse(
            stage="sql_generation",
            rendered_prompt=prompt,
            ai_response=ai_response if ai_response["success"] else None,
            semantic_context={
                "modules_used": semantic_context_result.modules_used,
                "total_tokens": semantic_context_result.total_tokens_used,
                "relevance_scores": semantic_context_result.relevance_scores,
                "context_preview": semantic_context_result.enhanced_context[:500] + "..."
            },
            success=ai_response["success"],
            error=ai_response.get("error")
        )
    except Exception as e:
        logger.error(f"SQL 生成测试失败: {str(e)}", exc_info=True)
        return PromptTestResponse(
            stage="sql_generation",
            rendered_prompt="",
            success=False,
            error=str(e)
        )


async def test_data_analysis(
    orchestrator: ChatOrchestrator,
    context: ChatContext,
    user_question: str
) -> PromptTestResponse:
    """测试数据分析阶段"""
    try:
        logger.info("=" * 80)
        logger.info("🧪 测试数据分析阶段")
        logger.info(f"用户问题: {user_question}")
        
        # 模拟查询结果
        mock_query_result = {
            "columns": ["count"],
            "rows": [[150]],
            "total_rows": 1
        }
        
        logger.info(f"📊 使用模拟查询结果: {mock_query_result}")
        
        # 渲染 Prompt
        prompt = orchestrator.prompt_manager.render_prompt(
            PromptType.DATA_ANALYSIS,
            {
                "user_question": user_question,
                "query_result": str(mock_query_result),
                "previous_data": "无历史数据"
            }
        )
        
        logger.info(f"✅ Prompt 渲染完成，长度: {len(prompt)}")
        logger.info(f"📝 Prompt 内容:\n{prompt}")
        
        # 调用 AI
        ai_response = await orchestrator.ai_service.call_local_model(
            prompt,
            session_id=context.session_id
        )
        
        logger.info(f"✅ AI 响应: {ai_response}")
        logger.info("=" * 80)
        
        return PromptTestResponse(
            stage="data_analysis",
            rendered_prompt=prompt,
            ai_response=ai_response if ai_response["success"] else None,
            success=ai_response["success"],
            error=ai_response.get("error")
        )
    except Exception as e:
        logger.error(f"数据分析测试失败: {str(e)}", exc_info=True)
        return PromptTestResponse(
            stage="data_analysis",
            rendered_prompt="",
            success=False,
            error=str(e)
        )
