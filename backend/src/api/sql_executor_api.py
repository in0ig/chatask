"""
SQL执行服务API

提供SQL查询执行、分页查询、流式查询、结果格式化等功能
"""

import logging
from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any

from src.schemas.sql_executor_schema import (
    ExecutionRequest,
    PaginatedExecutionRequest,
    StreamExecutionRequest,
    QueryResultResponse,
    ExecutionStatisticsResponse,
    HealthStatusResponse,
    FormatRequest,
    BatchExecutionRequest,
    BatchExecutionResponse,
    PageInfo
)
from src.services.sql_executor_service import (
    SQLExecutorService,
    ExecutionConfig,
    SQLExecutionError
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/sql-executor", tags=["SQL执行"])

# 全局SQL执行服务实例
_executor_service: SQLExecutorService = None


def get_executor_service() -> SQLExecutorService:
    """获取SQL执行服务实例"""
    global _executor_service
    if _executor_service is None:
        _executor_service = SQLExecutorService()
    return _executor_service


@router.post("/execute", response_model=QueryResultResponse)
async def execute_query(
    request: ExecutionRequest,
    executor: SQLExecutorService = Depends(get_executor_service)
):
    """
    执行SQL查询
    
    - **sql**: SQL查询语句
    - **data_source_id**: 数据源ID
    - **use_cache**: 是否使用缓存（默认true）
    - **timeout_seconds**: 超时时间（默认30秒）
    - **max_rows**: 最大返回行数（默认10000）
    """
    try:
        logger.info(f"收到SQL执行请求: data_source_id={request.data_source_id}")
        
        # TODO: 从数据库获取数据源配置
        # 这里使用模拟配置
        data_source_config = {
            'type': 'mysql',
            'host': 'localhost',
            'port': 3306,
            'username': 'root',
            'password': 'password',
            'database': 'test_db'
        }
        
        # 更新执行配置
        if request.timeout_seconds:
            executor.config.timeout_seconds = request.timeout_seconds
        if request.max_rows:
            executor.config.max_rows = request.max_rows
        
        # 执行查询
        result = await executor.execute_query(
            sql=request.sql,
            data_source_config=data_source_config,
            use_cache=request.use_cache
        )
        
        # 转换为响应格式
        return QueryResultResponse(
            columns=result.columns,
            rows=result.rows,
            row_count=result.row_count,
            execution_time=result.execution_time,
            is_truncated=result.is_truncated,
            has_more=result.has_more,
            page_info=PageInfo(**result.page_info) if result.page_info else None,
            metadata=result.metadata
        )
        
    except SQLExecutionError as e:
        logger.error(f"SQL执行失败: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail={
                'error': str(e),
                'error_code': e.error_code
            }
        )
    except Exception as e:
        logger.error(f"SQL执行异常: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"SQL执行异常: {str(e)}")


@router.post("/execute/paginated", response_model=QueryResultResponse)
async def execute_query_paginated(
    request: PaginatedExecutionRequest,
    executor: SQLExecutorService = Depends(get_executor_service)
):
    """
    分页执行SQL查询
    
    - **sql**: SQL查询语句
    - **data_source_id**: 数据源ID
    - **page**: 页码（从1开始，默认1）
    - **page_size**: 每页大小（默认1000）
    """
    try:
        logger.info(f"收到分页SQL执行请求: data_source_id={request.data_source_id}, page={request.page}")
        
        # TODO: 从数据库获取数据源配置
        data_source_config = {
            'type': 'mysql',
            'host': 'localhost',
            'port': 3306,
            'username': 'root',
            'password': 'password',
            'database': 'test_db'
        }
        
        # 执行分页查询
        result = await executor.execute_query_paginated(
            sql=request.sql,
            data_source_config=data_source_config,
            page=request.page,
            page_size=request.page_size
        )
        
        # 转换为响应格式
        return QueryResultResponse(
            columns=result.columns,
            rows=result.rows,
            row_count=result.row_count,
            execution_time=result.execution_time,
            is_truncated=result.is_truncated,
            has_more=result.has_more,
            page_info=PageInfo(**result.page_info) if result.page_info else None,
            metadata=result.metadata
        )
        
    except SQLExecutionError as e:
        logger.error(f"分页SQL执行失败: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail={
                'error': str(e),
                'error_code': e.error_code
            }
        )
    except Exception as e:
        logger.error(f"分页SQL执行异常: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"分页SQL执行异常: {str(e)}")


@router.post("/execute/batch", response_model=BatchExecutionResponse)
async def execute_queries_batch(
    request: BatchExecutionRequest,
    executor: SQLExecutorService = Depends(get_executor_service)
):
    """
    批量执行SQL查询（最多10个）
    
    - **queries**: 查询列表
    """
    try:
        logger.info(f"收到批量SQL执行请求: 查询数量={len(request.queries)}")
        
        import time
        start_time = time.time()
        
        results = []
        successful_count = 0
        failed_count = 0
        
        for query_request in request.queries:
            try:
                # TODO: 从数据库获取数据源配置
                data_source_config = {
                    'type': 'mysql',
                    'host': 'localhost',
                    'port': 3306,
                    'username': 'root',
                    'password': 'password',
                    'database': 'test_db'
                }
                
                # 执行查询
                result = await executor.execute_query(
                    sql=query_request.sql,
                    data_source_config=data_source_config,
                    use_cache=query_request.use_cache
                )
                
                results.append(QueryResultResponse(
                    columns=result.columns,
                    rows=result.rows,
                    row_count=result.row_count,
                    execution_time=result.execution_time,
                    is_truncated=result.is_truncated,
                    has_more=result.has_more,
                    page_info=PageInfo(**result.page_info) if result.page_info else None,
                    metadata=result.metadata
                ))
                successful_count += 1
                
            except Exception as e:
                logger.error(f"批量执行中的查询失败: {str(e)}")
                results.append(QueryResultResponse(
                    columns=[],
                    rows=[],
                    row_count=0,
                    execution_time=0.0,
                    is_truncated=False,
                    has_more=False,
                    metadata={'error': str(e)}
                ))
                failed_count += 1
        
        total_execution_time = time.time() - start_time
        
        return BatchExecutionResponse(
            results=results,
            total_execution_time=total_execution_time,
            successful_count=successful_count,
            failed_count=failed_count
        )
        
    except Exception as e:
        logger.error(f"批量SQL执行异常: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"批量SQL执行异常: {str(e)}")


@router.get("/statistics", response_model=ExecutionStatisticsResponse)
async def get_statistics(
    executor: SQLExecutorService = Depends(get_executor_service)
):
    """
    获取SQL执行统计信息
    
    返回总查询数、成功率、平均执行时间、缓存命中率等统计信息
    """
    try:
        stats = executor.get_statistics()
        
        return ExecutionStatisticsResponse(
            total_queries=stats['total_queries'],
            successful_queries=stats['successful_queries'],
            failed_queries=stats['failed_queries'],
            timeout_queries=stats['timeout_queries'],
            success_rate=stats['success_rate'],
            average_execution_time=stats['average_execution_time'],
            total_rows_returned=stats['total_rows_returned'],
            cache_hits=stats['cache_hits'],
            cache_hit_rate=stats['cache_hit_rate'],
            active_queries=stats['active_queries'],
            cache_size=stats['cache_size']
        )
        
    except Exception as e:
        logger.error(f"获取统计信息失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取统计信息失败: {str(e)}")


@router.get("/health", response_model=HealthStatusResponse)
async def get_health_status(
    executor: SQLExecutorService = Depends(get_executor_service)
):
    """
    获取SQL执行服务健康状态
    
    返回服务状态、活跃查询数、缓存大小等健康信息
    """
    try:
        health = executor.get_health_status()
        
        return HealthStatusResponse(
            status=health['status'],
            active_queries=health['active_queries'],
            max_concurrent_queries=health['max_concurrent_queries'],
            cache_size=health['cache_size'],
            statistics=ExecutionStatisticsResponse(**health['statistics'])
        )
        
    except Exception as e:
        logger.error(f"获取健康状态失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取健康状态失败: {str(e)}")


@router.post("/cache/clear")
async def clear_cache(
    executor: SQLExecutorService = Depends(get_executor_service)
):
    """
    清空查询结果缓存
    
    清空所有缓存的查询结果
    """
    try:
        executor.clear_cache()
        return {'message': '缓存已清空', 'success': True}
        
    except Exception as e:
        logger.error(f"清空缓存失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"清空缓存失败: {str(e)}")


@router.post("/format")
async def format_result(
    result: QueryResultResponse,
    format_request: FormatRequest,
    executor: SQLExecutorService = Depends(get_executor_service)
):
    """
    格式化查询结果
    
    - **format_type**: 格式类型（json/csv/table）
    """
    try:
        from src.services.sql_executor_service import QueryResult
        
        # 转换为QueryResult对象
        query_result = QueryResult(
            columns=result.columns,
            rows=result.rows,
            row_count=result.row_count,
            execution_time=result.execution_time,
            is_truncated=result.is_truncated,
            has_more=result.has_more,
            page_info=result.page_info.dict() if result.page_info else None,
            metadata=result.metadata
        )
        
        # 格式化结果
        formatted = executor.format_result_for_display(
            query_result,
            format_type=format_request.format_type
        )
        
        return {
            'format_type': format_request.format_type,
            'formatted_result': formatted
        }
        
    except Exception as e:
        logger.error(f"格式化结果失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"格式化结果失败: {str(e)}")
