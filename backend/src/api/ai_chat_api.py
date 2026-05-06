"""
AI对话API - 混合云+端架构
提供智能对话、SQL生成、数据分析等功能
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List, AsyncIterator
import json
import asyncio
import logging
from datetime import datetime

from ..services.ai_model_service import (
    get_ai_service,
    AIModelService,
    ModelType,
    AIModelError
)
from ..database import get_db
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ai", tags=["AI Chat"])


# 请求模型
class ChatRequest(BaseModel):
    """对话请求"""
    message: str = Field(..., description="用户消息")
    session_id: Optional[str] = Field(None, description="会话ID")
    context: Optional[Dict[str, Any]] = Field(None, description="上下文信息")


class SQLGenerationRequest(BaseModel):
    """SQL生成请求"""
    question: str = Field(..., description="用户问题")
    table_schemas: List[Dict[str, Any]] = Field(..., description="表结构信息")
    dictionaries: Optional[List[Dict[str, Any]]] = Field(None, description="数据字典")
    knowledge_base: Optional[List[Dict[str, Any]]] = Field(None, description="知识库")
    session_id: Optional[str] = Field(None, description="会话ID")


class DataAnalysisRequest(BaseModel):
    """数据分析请求"""
    question: str = Field(..., description="分析问题")
    query_result: Dict[str, Any] = Field(..., description="查询结果数据")
    previous_context: Optional[List[Dict[str, Any]]] = Field(None, description="历史上下文")
    session_id: Optional[str] = Field(None, description="会话ID")


# 响应模型
class ChatResponse(BaseModel):
    """对话响应"""
    content: str
    model_type: str
    tokens_used: int
    response_time: float
    session_id: str
    metadata: Optional[Dict[str, Any]] = None


class SQLGenerationResponse(BaseModel):
    """SQL生成响应"""
    sql: Optional[str]
    explanation: str
    confidence: float
    tokens_used: int
    response_time: float
    session_id: str
    metadata: Optional[Dict[str, Any]] = None


class DataAnalysisResponse(BaseModel):
    """数据分析响应"""
    analysis: str
    insights: List[str]
    recommendations: List[str]
    tokens_used: int
    response_time: float
    session_id: str
    metadata: Optional[Dict[str, Any]] = None


class TokenUsageResponse(BaseModel):
    """Token使用量响应"""
    total_requests: int
    total_tokens: int
    total_cost: float
    daily_usage: Dict[str, Dict[str, Any]]
    model_type: str


class StreamChunk(BaseModel):
    """流式响应块"""
    type: str  # 'thinking', 'result', 'sql', 'analysis', 'error'
    content: str
    metadata: Optional[Dict[str, Any]] = None
    timestamp: datetime


# API端点
@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    ai_service: AIModelService = Depends(get_ai_service),
    db: Session = Depends(get_db)
):
    """
    通用对话接口
    根据消息内容自动选择合适的模型进行处理
    """
    try:
        # 生成会话ID
        session_id = request.session_id or f"chat_{int(datetime.now().timestamp())}"
        
        # 简单的意图识别（后续会被专门的意图识别服务替代）
        if _is_sql_related(request.message):
            # 使用云端Qwen模型处理SQL相关问题
            response = await ai_service.generate_sql(
                _build_sql_prompt(request.message, request.context)
            )
        else:
            # 使用本地OpenAI模型处理一般对话
            response = await ai_service.analyze_data_locally(request.message)
        
        return ChatResponse(
            content=response.content,
            model_type=response.model_type.value,
            tokens_used=response.tokens_used,
            response_time=response.response_time,
            session_id=session_id,
            metadata=response.metadata
        )
        
    except AIModelError as e:
        logger.error(f"AI model error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"AI model error: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error in chat: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )


@router.post("/generate-sql", response_model=SQLGenerationResponse)
async def generate_sql(
    request: SQLGenerationRequest,
    ai_service: AIModelService = Depends(get_ai_service),
    db: Session = Depends(get_db)
):
    """
    SQL生成接口
    使用云端Qwen模型生成SQL查询语句
    """
    try:
        session_id = request.session_id or f"sql_{int(datetime.now().timestamp())}"
        
        # 构建SQL生成的prompt
        prompt = _build_comprehensive_sql_prompt(
            question=request.question,
            table_schemas=request.table_schemas,
            dictionaries=request.dictionaries or [],
            knowledge_base=request.knowledge_base or []
        )
        
        # 使用云端Qwen模型生成SQL
        response = await ai_service.generate_sql(prompt)
        
        # 提取SQL和解释
        extracted_sql = response.metadata.get('extracted_sql') if response.metadata else None
        explanation = _extract_explanation_from_response(response.content)
        confidence = _calculate_confidence(response.content, extracted_sql)
        
        return SQLGenerationResponse(
            sql=extracted_sql,
            explanation=explanation,
            confidence=confidence,
            tokens_used=response.tokens_used,
            response_time=response.response_time,
            session_id=session_id,
            metadata=response.metadata
        )
        
    except AIModelError as e:
        logger.error(f"SQL generation error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"SQL generation failed: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error in SQL generation: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )


@router.post("/analyze-data", response_model=DataAnalysisResponse)
async def analyze_data(
    request: DataAnalysisRequest,
    ai_service: AIModelService = Depends(get_ai_service),
    db: Session = Depends(get_db)
):
    """
    数据分析接口
    使用本地OpenAI模型分析查询结果数据
    """
    try:
        session_id = request.session_id or f"analysis_{int(datetime.now().timestamp())}"
        
        # 构建数据分析的prompt
        prompt = _build_data_analysis_prompt(
            question=request.question,
            query_result=request.query_result,
            previous_context=request.previous_context or []
        )
        
        # 使用本地OpenAI模型分析数据
        response = await ai_service.analyze_data_locally(prompt)
        
        # 解析分析结果
        analysis_result = _parse_analysis_response(response.content)
        
        return DataAnalysisResponse(
            analysis=analysis_result['analysis'],
            insights=analysis_result['insights'],
            recommendations=analysis_result['recommendations'],
            tokens_used=response.tokens_used,
            response_time=response.response_time,
            session_id=session_id,
            metadata=response.metadata
        )
        
    except AIModelError as e:
        logger.error(f"Data analysis error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Data analysis failed: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error in data analysis: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )


@router.get("/chat/stream/{session_id}")
async def chat_stream(
    session_id: str,
    message: str,
    ai_service: AIModelService = Depends(get_ai_service)
):
    """
    流式对话接口
    实时推送AI生成过程
    """
    async def generate_stream():
        try:
            # 确定使用的模型类型
            model_type = ModelType.QWEN_CLOUD if _is_sql_related(message) else ModelType.OPENAI_LOCAL
            
            # 发送开始信号
            yield _format_stream_chunk("thinking", "正在思考中...", session_id)
            
            # 流式生成响应
            content_buffer = ""
            async for chunk in ai_service.generate_stream(model_type, message):
                content_buffer += chunk
                yield _format_stream_chunk("result", chunk, session_id)
            
            # 如果是SQL相关，尝试提取SQL
            if model_type == ModelType.QWEN_CLOUD:
                adapter = ai_service.adapters[ModelType.QWEN_CLOUD]
                if hasattr(adapter, 'extract_sql_from_response'):
                    sql = adapter.extract_sql_from_response(content_buffer)
                    if sql:
                        yield _format_stream_chunk("sql", sql, session_id, {"extracted": True})
            
            # 发送完成信号
            yield _format_stream_chunk("complete", "", session_id)
            
        except Exception as e:
            logger.error(f"Stream error: {str(e)}")
            yield _format_stream_chunk("error", str(e), session_id)
    
    return StreamingResponse(
        generate_stream(),
        media_type="text/plain",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
    )


@router.get("/token-usage/{model_type}", response_model=TokenUsageResponse)
async def get_token_usage(
    model_type: str,
    ai_service: AIModelService = Depends(get_ai_service)
):
    """
    获取Token使用量统计
    """
    try:
        model_enum = ModelType(model_type)
        stats = ai_service.get_token_usage_stats(model_enum)
        
        return TokenUsageResponse(
            total_requests=stats.get('total_requests', 0),
            total_tokens=stats.get('total_tokens', 0),
            total_cost=stats.get('total_cost', 0.0),
            daily_usage=stats.get('daily_usage', {}),
            model_type=model_type
        )
        
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid model type: {model_type}"
        )
    except Exception as e:
        logger.error(f"Error getting token usage: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )


@router.post("/models/health-check")
async def health_check(
    ai_service: AIModelService = Depends(get_ai_service)
):
    """
    AI模型健康检查
    """
    health_status = {
        "qwen_cloud": {"status": "unknown", "error": None},
        "openai_local": {"status": "unknown", "error": None}
    }
    
    # 检查云端Qwen模型
    if ModelType.QWEN_CLOUD in ai_service.adapters:
        try:
            test_response = await ai_service.generate_sql("SELECT 1;")
            health_status["qwen_cloud"]["status"] = "healthy"
        except Exception as e:
            health_status["qwen_cloud"]["status"] = "unhealthy"
            health_status["qwen_cloud"]["error"] = str(e)
    
    # 检查本地OpenAI模型
    if ModelType.OPENAI_LOCAL in ai_service.adapters:
        try:
            test_response = await ai_service.analyze_data_locally("Test message")
            health_status["openai_local"]["status"] = "healthy"
        except Exception as e:
            health_status["openai_local"]["status"] = "unhealthy"
            health_status["openai_local"]["error"] = str(e)
    
    return health_status


# 辅助函数
def _is_sql_related(message: str) -> bool:
    """判断消息是否与SQL相关"""
    sql_keywords = [
        'select', 'query', 'table', 'database', 'sql', 'show', 'find', 'get',
        '查询', '表', '数据库', '显示', '查找', '获取'
    ]
    message_lower = message.lower()
    return any(keyword in message_lower for keyword in sql_keywords)


def _build_sql_prompt(message: str, context: Optional[Dict[str, Any]]) -> str:
    """构建SQL生成的简单prompt"""
    prompt = f"用户问题: {message}\n\n"
    
    if context and 'table_schemas' in context:
        prompt += "可用表结构:\n"
        for schema in context['table_schemas']:
            prompt += f"- {schema}\n"
    
    prompt += "\n请生成相应的SQL查询语句。"
    return prompt


def _build_comprehensive_sql_prompt(
    question: str,
    table_schemas: List[Dict[str, Any]],
    dictionaries: List[Dict[str, Any]],
    knowledge_base: List[Dict[str, Any]]
) -> str:
    """构建完整的SQL生成prompt"""
    prompt = f"""请根据用户问题生成SQL查询语句：

用户问题: {question}

可用表结构:
"""
    
    # 添加表结构信息
    for schema in table_schemas:
        prompt += f"""
表名: {schema.get('table_name', 'unknown')}
字段: {', '.join(schema.get('columns', []))}
"""
    
    # 添加数据字典信息
    if dictionaries:
        prompt += "\n数据字典 (字段业务含义):\n"
        for dict_item in dictionaries:
            prompt += f"- {dict_item.get('field_name', '')}: {dict_item.get('business_meaning', '')}\n"
    
    # 添加知识库信息
    if knowledge_base:
        prompt += "\n相关业务规则:\n"
        for kb_item in knowledge_base:
            prompt += f"- {kb_item.get('rule', '')}\n"
    
    prompt += """
请生成标准的SQL查询语句，要求:
1. 语法正确
2. 字段名和表名准确
3. 查询逻辑符合用户需求
4. 包含必要的WHERE条件
5. 结果集大小合理

请以以下格式返回:
```sql
[SQL语句]
```

解释: [SQL逻辑说明]
"""
    
    return prompt


def _build_data_analysis_prompt(
    question: str,
    query_result: Dict[str, Any],
    previous_context: List[Dict[str, Any]]
) -> str:
    """构建数据分析prompt"""
    prompt = f"""请分析以下查询结果数据：

用户问题: {question}

查询结果:
列名: {query_result.get('columns', [])}
数据行数: {len(query_result.get('rows', []))}
数据样本: {query_result.get('rows', [])[:5]}  # 只显示前5行
"""
    
    if previous_context:
        prompt += "\n历史上下文:\n"
        for ctx in previous_context[-3:]:  # 只使用最近3个上下文
            prompt += f"- {ctx}\n"
    
    prompt += """
请提供:
1. 数据分析总结
2. 关键洞察点
3. 业务建议

请以结构化的方式回答。
"""
    
    return prompt


def _extract_explanation_from_response(response: str) -> str:
    """从响应中提取解释"""
    # 查找"解释:"后的内容
    if "解释:" in response:
        return response.split("解释:", 1)[1].strip()
    elif "说明:" in response:
        return response.split("说明:", 1)[1].strip()
    else:
        # 如果没有明确的解释标识，返回去除SQL代码块后的内容
        import re
        cleaned = re.sub(r'```sql.*?```', '', response, flags=re.DOTALL)
        return cleaned.strip()


def _calculate_confidence(response: str, extracted_sql: Optional[str]) -> float:
    """计算SQL生成的置信度"""
    confidence = 0.5  # 基础置信度
    
    # 如果成功提取到SQL，增加置信度
    if extracted_sql:
        confidence += 0.3
    
    # 如果响应包含解释，增加置信度
    if any(keyword in response for keyword in ["解释", "说明", "因为", "由于"]):
        confidence += 0.1
    
    # 如果SQL包含常见关键词，增加置信度
    if extracted_sql:
        sql_lower = extracted_sql.lower()
        if any(keyword in sql_lower for keyword in ["select", "from", "where", "group by", "order by"]):
            confidence += 0.1
    
    return min(confidence, 1.0)


def _parse_analysis_response(response: str) -> Dict[str, Any]:
    """解析数据分析响应"""
    # 简单的解析逻辑，实际实现中可能需要更复杂的NLP处理
    lines = response.split('\n')
    
    analysis = ""
    insights = []
    recommendations = []
    
    current_section = "analysis"
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        if "洞察" in line or "insight" in line.lower():
            current_section = "insights"
            continue
        elif "建议" in line or "recommendation" in line.lower():
            current_section = "recommendations"
            continue
        
        if current_section == "analysis":
            analysis += line + " "
        elif current_section == "insights" and line.startswith(('-', '•', '1.', '2.', '3.')):
            insights.append(line.lstrip('-•123. '))
        elif current_section == "recommendations" and line.startswith(('-', '•', '1.', '2.', '3.')):
            recommendations.append(line.lstrip('-•123. '))
    
    return {
        "analysis": analysis.strip() or response,
        "insights": insights or ["数据分析完成"],
        "recommendations": recommendations or ["建议进一步分析"]
    }


def _format_stream_chunk(chunk_type: str, content: str, session_id: str, metadata: Optional[Dict[str, Any]] = None) -> str:
    """格式化流式响应块"""
    chunk = StreamChunk(
        type=chunk_type,
        content=content,
        metadata=metadata,
        timestamp=datetime.now()
    )
    return f"data: {chunk.json()}\n\n"