"""
SQL生成服务 API

任务 5.4.1 的API实现
"""

from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime
import logging

from src.services.sql_generator_service import (
    SQLGeneratorService,
    SQLGenerationRequest,
    SQLGenerationResult,
    SQLDialect
)
from src.schemas.sql_generator_schema import (
    SQLGenerationRequestSchema,
    SQLGenerationResultSchema,
    BatchSQLGenerationRequestSchema,
    BatchSQLGenerationResponseSchema,
    GenerationStatisticsSchema,
    HealthCheckResponseSchema,
    ValidationResultSchema,
    ValidationViolationSchema
)

logger = logging.getLogger(__name__)

# 创建路由器
router = APIRouter(prefix="/api/sql-generator", tags=["SQL生成"])

# 全局服务实例
sql_generator_service = SQLGeneratorService()


# 辅助函数
def convert_validation_result_to_schema(validation_result: Dict[str, Any]) -> ValidationResultSchema:
    """将验证结果转换为Schema"""
    violations = []
    if "violations" in validation_result:
        violations = [
            ValidationViolationSchema(
                level=v["level"],
                type=v["type"],
                message=v["message"]
            )
            for v in validation_result["violations"]
        ]
    
    return ValidationResultSchema(
        is_valid=validation_result.get("is_valid", False),
        security_level=validation_result.get("security_level"),
        violations=violations,
        complexity=validation_result.get("complexity"),
        error=validation_result.get("error")
    )


def convert_generation_result_to_schema(result: SQLGenerationResult) -> SQLGenerationResultSchema:
    """将生成结果转换为Schema"""
    validation_schema = None
    if result.validation_result:
        validation_schema = convert_validation_result_to_schema(result.validation_result)
    
    return SQLGenerationResultSchema(
        sql=result.sql,
        explanation=result.explanation,
        estimated_rows=result.estimated_rows,
        execution_plan=result.execution_plan,
        confidence=result.confidence,
        generation_time=result.generation_time,
        semantic_context_used=result.semantic_context_used,
        validation_result=validation_schema
    )


# API端点
@router.post("/generate", response_model=SQLGenerationResultSchema, summary="生成SQL查询")
async def generate_sql(request: SQLGenerationRequestSchema):
    """
    基于用户问题生成SQL查询
    
    - **user_question**: 用户的自然语言问题
    - **table_ids**: 可选的相关表ID列表
    - **data_source_id**: 可选的数据源ID
    - **sql_dialect**: SQL方言类型（mysql/sqlserver/postgresql）
    - **include_explanation**: 是否包含解释
    - **max_rows**: 最大返回行数
    
    返回生成的SQL查询、解释、验证结果等信息。
    """
    try:
        logger.info(f"收到SQL生成请求: {request.user_question}")
        
        # 转换请求
        generation_request = SQLGenerationRequest(
            user_question=request.user_question,
            table_ids=request.table_ids,
            data_source_id=request.data_source_id,
            sql_dialect=SQLDialect(request.sql_dialect.value),
            include_explanation=request.include_explanation,
            max_rows=request.max_rows
        )
        
        # 调用服务层生成SQL
        result = await sql_generator_service.generate_sql(generation_request)
        
        # 转换为响应模型
        response = convert_generation_result_to_schema(result)
        
        logger.info(f"SQL生成完成，置信度: {response.confidence:.2f}")
        return response
        
    except Exception as e:
        logger.error(f"SQL生成失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"SQL生成过程中发生错误: {str(e)}"
        )


@router.post("/generate/batch", response_model=BatchSQLGenerationResponseSchema, summary="批量生成SQL查询")
async def batch_generate_sql(request: BatchSQLGenerationRequestSchema):
    """
    批量生成SQL查询
    
    支持一次处理多个SQL生成请求，提高处理效率。
    最多支持10个并发请求。
    """
    try:
        logger.info(f"收到批量SQL生成请求，数量: {len(request.requests)}")
        
        results = []
        success_count = 0
        error_count = 0
        total_start_time = datetime.now()
        
        # 处理每个请求
        for req in request.requests:
            try:
                generation_request = SQLGenerationRequest(
                    user_question=req.user_question,
                    table_ids=req.table_ids,
                    data_source_id=req.data_source_id,
                    sql_dialect=SQLDialect(req.sql_dialect.value),
                    include_explanation=req.include_explanation,
                    max_rows=req.max_rows
                )
                
                result = await sql_generator_service.generate_sql(generation_request)
                response = convert_generation_result_to_schema(result)
                results.append(response)
                success_count += 1
                
            except Exception as e:
                logger.error(f"批量请求中的单个请求失败: {str(e)}")
                # 添加错误结果
                error_result = SQLGenerationResultSchema(
                    sql="",
                    explanation=f"生成失败: {str(e)}",
                    estimated_rows=0,
                    execution_plan="",
                    confidence=0.0,
                    generation_time=0.0,
                    semantic_context_used={},
                    validation_result=ValidationResultSchema(
                        is_valid=False,
                        error=str(e)
                    )
                )
                results.append(error_result)
                error_count += 1
        
        total_processing_time = (datetime.now() - total_start_time).total_seconds()
        
        response = BatchSQLGenerationResponseSchema(
            results=results,
            total_processing_time=total_processing_time,
            success_count=success_count,
            error_count=error_count
        )
        
        logger.info(f"批量SQL生成完成，成功: {success_count}, 失败: {error_count}")
        return response
        
    except Exception as e:
        logger.error(f"批量SQL生成失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"批量SQL生成过程中发生错误: {str(e)}"
        )


@router.post("/validate", response_model=ValidationResultSchema, summary="验证SQL查询")
async def validate_sql(sql: str):
    """
    验证SQL查询的语法和安全性
    
    - **sql**: 要验证的SQL查询语句
    
    返回验证结果，包括是否有效、安全级别、违规信息等。
    """
    try:
        logger.info(f"收到SQL验证请求")
        
        # 使用SQL验证器
        validation_result = sql_generator_service.sql_validator.validate_sql(sql)
        
        # 转换为响应模型
        violations = [
            ValidationViolationSchema(
                level=v.level.value,
                type=v.type,
                message=v.message
            )
            for v in validation_result.violations
        ]
        
        response = ValidationResultSchema(
            is_valid=validation_result.is_valid,
            security_level=validation_result.security_level.value,
            violations=violations,
            complexity={
                "score": validation_result.complexity.complexity_score,
                "estimated_cost": validation_result.complexity.estimated_cost,
                "table_count": validation_result.complexity.table_count,
                "join_count": validation_result.complexity.join_count
            }
        )
        
        logger.info(f"SQL验证完成，有效性: {response.is_valid}")
        return response
        
    except Exception as e:
        logger.error(f"SQL验证失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"SQL验证过程中发生错误: {str(e)}"
        )


@router.get("/statistics", response_model=GenerationStatisticsSchema, summary="获取生成统计信息")
async def get_generation_statistics():
    """
    获取SQL生成的统计信息
    
    包括总生成次数、成功率、平均生成时间、平均置信度、语法正确率等指标。
    """
    try:
        stats = sql_generator_service.get_generation_statistics()
        return GenerationStatisticsSchema(**stats)
        
    except Exception as e:
        logger.error(f"获取统计信息失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"获取统计信息时发生错误: {str(e)}"
        )


@router.get("/health", response_model=HealthCheckResponseSchema, summary="健康检查")
async def health_check():
    """
    SQL生成服务健康检查
    
    检查服务状态和依赖组件的可用性。
    """
    try:
        # 检查服务状态
        stats = sql_generator_service.get_generation_statistics()
        
        health_status = {
            "status": "healthy",
            "service": "sql_generator",
            "version": "1.0.0",
            "timestamp": datetime.now().isoformat(),
            "statistics": {
                "total_generations": stats["total_generations"],
                "success_rate": stats["success_rate"],
                "average_generation_time": stats["average_generation_time"]
            },
            "dependencies": {
                "ai_service": "available" if sql_generator_service.ai_service else "unavailable",
                "semantic_aggregator": "available",
                "sql_validator": "available"
            }
        }
        
        return HealthCheckResponseSchema(**health_status)
        
    except Exception as e:
        logger.error(f"健康检查失败: {str(e)}", exc_info=True)
        return HealthCheckResponseSchema(
            status="unhealthy",
            service="sql_generator",
            version="1.0.0",
            timestamp=datetime.now().isoformat(),
            statistics={},
            dependencies={},
            error=str(e)
        )
