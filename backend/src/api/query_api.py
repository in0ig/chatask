import logging
from fastapi import APIRouter, HTTPException
from typing import Dict, Optional
import json
from src.models.query_result_model import QueryResult
from src.services.nlu_service import NLUParser
from src.services.query_service import QueryService

# 创建日志记录器
logger = logging.getLogger(__name__)

router = APIRouter(tags=["Query"])

nlu_parser = NLUParser()
query_service = QueryService()

@router.post("/", response_model=None)
async def process_query(text: str, session_id: Optional[str] = None):
    """
    处理自然语言查询
    
    Args:
        text: 自然语言查询文本
        session_id: 可选的会话ID，如果提供则将查询保存到会话历史中
    """
    logger.info(f"Received query request: {text[:100]}{'...' if len(text) > 100 else ''}")
    
    if not text or not isinstance(text, str):
        error_msg = "Query text is required"
        logger.warning(f"Invalid request: {error_msg}")
        raise HTTPException(status_code=400, detail=error_msg)
    
    # 1. NLU 解析
    try:
        logger.debug(f"Starting NLU parsing for query: {text}")
        nlu_result = await nlu_parser.process_natural_language_query(text)
        logger.info(f"NLU parsing completed: entities={nlu_result['entities']}, time_range={nlu_result['time_range']['type']}")
        
        # 2. 执行查询（基于解析结果）
        logger.info(f"Executing query with NLU result: {nlu_result['entities']['metric']} by {nlu_result['entities']['dimension']}")
        result = query_service.execute_query(nlu_result)
        logger.info(f"Query executed successfully, returned {len(result.get('data', []))} data points")
        
        # 3. 推断图表类型
        chart_type = query_service.infer_chart_type(result)
        logger.info(f"Inferred chart type: {chart_type}")
        
        # 4. 准备响应数据结构
        response_data = {
            "sql": result.get('sql', ''),
            "data": result.get('data', []),
            "chart_type": chart_type,
            "headers": result.get('headers', []),
            "rows": result.get('rows', [])
        }
        
        # 5. 如果提供了 session_id，将查询保存到会话历史中
        if session_id:
            logger.info(f"Saving query to session {session_id}")
            query_service.save_to_session_history(session_id, text, result.get('sql', ''), chart_type)
        
        # 6. 返回结构化响应
        response = {
            "result": response_data,
            "metadata": {
                "timeRange": nlu_result['time_range'],
                "entities": nlu_result['entities']
            }
        }
        
        logger.info(f"Query API response prepared successfully, response size: {len(json.dumps(response))} bytes")
        return response
    except Exception as e:
        error_msg = f"Failed to process query: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to process query")