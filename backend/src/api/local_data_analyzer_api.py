"""
本地数据分析引擎API路由
"""

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from typing import AsyncGenerator
from datetime import datetime
import os

from ..schemas.local_data_analyzer_schema import (
    AnalysisRequest,
    AnalysisResponse,
    ComparisonRequest,
    AnalysisStatsResponse
)
from ..services.local_data_analyzer import (
    LocalDataAnalyzer,
    AnalysisContext,
    QueryResult
)

router = APIRouter(prefix="/api/local-analyzer", tags=["本地数据分析"])

# 全局分析器实例（实际应用中应该使用依赖注入）
_analyzer_instance = None


def get_analyzer() -> LocalDataAnalyzer:
    """获取分析器实例"""
    global _analyzer_instance
    
    if _analyzer_instance is None:
        # 从环境变量获取配置
        api_key = os.getenv("LOCAL_OPENAI_API_KEY", "not-needed")
        base_url = os.getenv("LOCAL_OPENAI_BASE_URL", "http://localhost:11434/v1")
        model_name = os.getenv("LOCAL_OPENAI_MODEL", "qwen2.5:latest")
        
        _analyzer_instance = LocalDataAnalyzer(
            openai_api_key=api_key,
            openai_base_url=base_url,
            model_name=model_name
        )
    
    return _analyzer_instance


@router.post("/analyze", response_model=AnalysisResponse)
async def analyze_data(
    request: AnalysisRequest,
    analyzer: LocalDataAnalyzer = Depends(get_analyzer)
):
    """
    分析查询结果数据并回答用户问题
    
    **数据隐私保护**：
    - 所有数据仅在本地处理
    - 不会发送到云端服务
    - 使用本地OpenAI模型
    """
    try:
        # 转换为内部数据结构
        current_result = QueryResult(
            query_id=request.query_result.query_id,
            sql=request.query_result.sql,
            data=request.query_result.data,
            columns=request.query_result.columns,
            row_count=request.query_result.row_count,
            executed_at=request.query_result.executed_at
        )
        
        previous_results = [
            QueryResult(
                query_id=r.query_id,
                sql=r.sql,
                data=r.data,
                columns=r.columns,
                row_count=r.row_count,
                executed_at=r.executed_at
            )
            for r in request.previous_results
        ]
        
        context = AnalysisContext(
            current_result=current_result,
            previous_results=previous_results,
            conversation_history=request.conversation_history,
            user_question=request.user_question
        )
        
        # 执行分析
        result = await analyzer.analyze_data(context, stream=False)
        
        return AnalysisResponse(
            analysis_id=result.analysis_id,
            question=result.question,
            answer=result.answer,
            insights=result.insights,
            data_points=result.data_points,
            created_at=result.created_at
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"数据分析失败: {str(e)}")


@router.post("/analyze/stream")
async def analyze_data_stream(
    request: AnalysisRequest,
    analyzer: LocalDataAnalyzer = Depends(get_analyzer)
):
    """
    流式分析查询结果数据
    
    **数据隐私保护**：
    - 所有数据仅在本地处理
    - 不会发送到云端服务
    - 使用本地OpenAI模型
    """
    try:
        # 转换为内部数据结构
        current_result = QueryResult(
            query_id=request.query_result.query_id,
            sql=request.query_result.sql,
            data=request.query_result.data,
            columns=request.query_result.columns,
            row_count=request.query_result.row_count,
            executed_at=request.query_result.executed_at
        )
        
        previous_results = [
            QueryResult(
                query_id=r.query_id,
                sql=r.sql,
                data=r.data,
                columns=r.columns,
                row_count=r.row_count,
                executed_at=r.executed_at
            )
            for r in request.previous_results
        ]
        
        context = AnalysisContext(
            current_result=current_result,
            previous_results=previous_results,
            conversation_history=request.conversation_history,
            user_question=request.user_question
        )
        
        async def generate_stream() -> AsyncGenerator[str, None]:
            """生成流式响应"""
            async for chunk in analyzer.analyze_data_stream(context):
                yield chunk
        
        return StreamingResponse(
            generate_stream(),
            media_type="text/plain"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"流式分析失败: {str(e)}")


@router.post("/compare", response_model=AnalysisResponse)
async def compare_data(
    request: ComparisonRequest,
    analyzer: LocalDataAnalyzer = Depends(get_analyzer)
):
    """
    对比两个查询结果
    
    **数据隐私保护**：
    - 所有数据仅在本地处理
    - 不会发送到云端服务
    """
    try:
        # 转换为内部数据结构
        current_result = QueryResult(
            query_id=request.current_result.query_id,
            sql=request.current_result.sql,
            data=request.current_result.data,
            columns=request.current_result.columns,
            row_count=request.current_result.row_count,
            executed_at=request.current_result.executed_at
        )
        
        previous_result = QueryResult(
            query_id=request.previous_result.query_id,
            sql=request.previous_result.sql,
            data=request.previous_result.data,
            columns=request.previous_result.columns,
            row_count=request.previous_result.row_count,
            executed_at=request.previous_result.executed_at
        )
        
        # 执行对比分析
        result = await analyzer.compare_data(
            current_result=current_result,
            previous_result=previous_result,
            comparison_question=request.comparison_question
        )
        
        return AnalysisResponse(
            analysis_id=result.analysis_id,
            question=result.question,
            answer=result.answer,
            insights=result.insights,
            data_points=result.data_points,
            created_at=result.created_at
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"数据对比失败: {str(e)}")


@router.get("/stats", response_model=AnalysisStatsResponse)
async def get_analysis_stats(
    analyzer: LocalDataAnalyzer = Depends(get_analyzer)
):
    """获取分析统计信息"""
    try:
        stats = analyzer.get_stats()
        
        # 计算成功率
        total = stats["total_analyses"]
        success_rate = (stats["successful_analyses"] / total * 100) if total > 0 else 0.0
        
        return AnalysisStatsResponse(
            total_analyses=stats["total_analyses"],
            successful_analyses=stats["successful_analyses"],
            failed_analyses=stats["failed_analyses"],
            total_tokens_used=stats["total_tokens_used"],
            average_response_time=stats["average_response_time"],
            success_rate=success_rate
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取统计信息失败: {str(e)}")


@router.post("/stats/reset")
async def reset_analysis_stats(
    analyzer: LocalDataAnalyzer = Depends(get_analyzer)
):
    """重置分析统计信息"""
    try:
        analyzer.reset_stats()
        return {"message": "统计信息已重置"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"重置统计信息失败: {str(e)}")


@router.get("/health")
async def health_check(
    analyzer: LocalDataAnalyzer = Depends(get_analyzer)
):
    """健康检查"""
    return {
        "status": "healthy",
        "service": "local_data_analyzer",
        "model": analyzer.model_name,
        "base_url": analyzer.client.base_url
    }


@router.post("/analyze/time-series")
async def analyze_time_series(
    query_result: dict,
    time_column: str,
    value_column: str,
    predict_steps: int = 3,
    analyzer: LocalDataAnalyzer = Depends(get_analyzer)
):
    """
    分析时间序列数据
    
    **功能**：
    - 趋势分析（上升/下降/稳定）
    - 异常值检测
    - 简单预测
    
    **参数**：
    - query_result: 查询结果数据
    - time_column: 时间列名
    - value_column: 数值列名
    - predict_steps: 预测步数（默认3）
    """
    try:
        # 转换为QueryResult对象
        result = QueryResult(
            query_id=query_result.get("query_id", ""),
            sql=query_result.get("sql", ""),
            data=query_result.get("data", []),
            columns=query_result.get("columns", []),
            row_count=query_result.get("row_count", 0),
            executed_at=query_result.get("executed_at", datetime.now())
        )
        
        # 执行时间序列分析
        analysis_result = await analyzer.analyze_time_series(
            result=result,
            time_column=time_column,
            value_column=value_column,
            predict_steps=predict_steps
        )
        
        return analysis_result.to_dict()
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"时间序列分析失败: {str(e)}")


@router.post("/compare/detailed")
async def compare_results_detailed(
    current_result: dict,
    previous_result: dict,
    analyzer: LocalDataAnalyzer = Depends(get_analyzer)
):
    """
    详细对比两个查询结果
    
    **功能**：
    - 行数变化分析
    - 数值列平均值变化
    - 自动生成对比洞察
    
    **数据隐私保护**：
    - 所有数据仅在本地处理
    """
    try:
        # 转换为QueryResult对象
        current = QueryResult(
            query_id=current_result.get("query_id", ""),
            sql=current_result.get("sql", ""),
            data=current_result.get("data", []),
            columns=current_result.get("columns", []),
            row_count=current_result.get("row_count", 0),
            executed_at=current_result.get("executed_at", datetime.now())
        )
        
        previous = QueryResult(
            query_id=previous_result.get("query_id", ""),
            sql=previous_result.get("sql", ""),
            data=previous_result.get("data", []),
            columns=previous_result.get("columns", []),
            row_count=previous_result.get("row_count", 0),
            executed_at=previous_result.get("executed_at", datetime.now())
        )
        
        # 执行详细对比
        comparison_result = await analyzer.compare_results_detailed(
            current_result=current,
            previous_result=previous
        )
        
        return comparison_result.to_dict()
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"详细对比失败: {str(e)}")


@router.post("/detect-anomalies")
async def detect_anomalies(
    query_result: dict,
    column_name: str,
    threshold: float = 2.0,
    analyzer: LocalDataAnalyzer = Depends(get_analyzer)
):
    """
    检测数据异常
    
    **功能**：
    - 基于标准差的异常值检测
    - Z-score计算
    - 异常率统计
    
    **参数**：
    - query_result: 查询结果数据
    - column_name: 要检测的列名
    - threshold: 异常阈值（标准差倍数，默认2.0）
    """
    try:
        # 转换为QueryResult对象
        result = QueryResult(
            query_id=query_result.get("query_id", ""),
            sql=query_result.get("sql", ""),
            data=query_result.get("data", []),
            columns=query_result.get("columns", []),
            row_count=query_result.get("row_count", 0),
            executed_at=query_result.get("executed_at", datetime.now())
        )
        
        # 执行异常检测
        anomaly_result = await analyzer.detect_anomalies(
            result=result,
            column_name=column_name,
            threshold=threshold
        )
        
        return anomaly_result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"异常检测失败: {str(e)}")


@router.post("/analyze/multi-dimensional")
async def multi_dimensional_analysis(
    query_result: dict,
    dimensions: list,
    metric: str,
    analyzer: LocalDataAnalyzer = Depends(get_analyzer)
):
    """
    多维度数据分析
    
    **功能**：
    - 按维度分组统计
    - 计算各组的统计量（均值、中位数、标准差等）
    - 自动排序和洞察生成
    
    **参数**：
    - query_result: 查询结果数据
    - dimensions: 维度列名列表
    - metric: 指标列名
    """
    try:
        # 转换为QueryResult对象
        result = QueryResult(
            query_id=query_result.get("query_id", ""),
            sql=query_result.get("sql", ""),
            data=query_result.get("data", []),
            columns=query_result.get("columns", []),
            row_count=query_result.get("row_count", 0),
            executed_at=query_result.get("executed_at", datetime.now())
        )
        
        # 执行多维度分析
        analysis_result = await analyzer.multi_dimensional_analysis(
            result=result,
            dimensions=dimensions,
            metric=metric
        )
        
        return analysis_result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"多维度分析失败: {str(e)}")
