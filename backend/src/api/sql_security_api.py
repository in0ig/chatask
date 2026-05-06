"""
SQL安全校验API

提供SQL安全校验和字段验证的REST API接口
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Optional, Dict, Any
import logging

from ..services.sql_security_validator import SQLSecurityService, ValidationResult
from ..schemas.base_schema import BaseResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/sql-security", tags=["SQL安全校验"])

# 全局服务实例
sql_security_service = SQLSecurityService()


@router.post("/validate", response_model=BaseResponse)
async def validate_sql(
    sql_query: str,
    data_source_id: Optional[int] = None
):
    """
    验证SQL查询的安全性和有效性
    
    Args:
        sql_query: SQL查询语句
        data_source_id: 数据源ID（可选，用于字段存在性验证）
        
    Returns:
        BaseResponse: 包含验证结果的响应
    """
    try:
        if not sql_query or not sql_query.strip():
            raise HTTPException(status_code=400, detail="SQL查询不能为空")
        
        # 执行SQL安全验证
        result = await sql_security_service.validate_and_secure_sql(
            sql_query=sql_query.strip(),
            data_source_id=data_source_id
        )
        
        # 生成安全报告
        security_report = sql_security_service.get_security_report(result)
        
        return BaseResponse(
            success=True,
            message="SQL验证完成",
            data={
                "validation_result": {
                    "is_valid": result.is_valid,
                    "security_level": result.security_level.value,
                    "operation": result.operation.value,
                    "sanitized_sql": result.sanitized_sql
                },
                "security_report": security_report
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"SQL验证API错误: {e}")
        raise HTTPException(status_code=500, detail=f"SQL验证失败: {str(e)}")


@router.post("/analyze-complexity", response_model=BaseResponse)
async def analyze_sql_complexity(sql_query: str):
    """
    分析SQL查询复杂度
    
    Args:
        sql_query: SQL查询语句
        
    Returns:
        BaseResponse: 包含复杂度分析结果的响应
    """
    try:
        if not sql_query or not sql_query.strip():
            raise HTTPException(status_code=400, detail="SQL查询不能为空")
        
        # 执行复杂度分析
        result = await sql_security_service.validate_and_secure_sql(sql_query.strip())
        
        return BaseResponse(
            success=True,
            message="SQL复杂度分析完成",
            data={
                "complexity": {
                    "score": result.complexity.complexity_score,
                    "estimated_cost": result.complexity.estimated_cost,
                    "table_count": result.complexity.table_count,
                    "join_count": result.complexity.join_count,
                    "subquery_count": result.complexity.subquery_count,
                    "function_count": result.complexity.function_count,
                    "condition_count": result.complexity.condition_count
                },
                "recommendations": _get_complexity_recommendations(result.complexity)
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"SQL复杂度分析API错误: {e}")
        raise HTTPException(status_code=500, detail=f"复杂度分析失败: {str(e)}")


@router.post("/check-injection", response_model=BaseResponse)
async def check_sql_injection(sql_query: str):
    """
    检查SQL注入风险
    
    Args:
        sql_query: SQL查询语句
        
    Returns:
        BaseResponse: 包含注入检查结果的响应
    """
    try:
        if not sql_query or not sql_query.strip():
            raise HTTPException(status_code=400, detail="SQL查询不能为空")
        
        # 执行注入检查
        result = await sql_security_service.validate_and_secure_sql(sql_query.strip())
        
        # 筛选注入相关的违规
        injection_violations = [
            v for v in result.violations 
            if v.type in ["SQL_INJECTION", "DANGEROUS_OPERATION", "DANGEROUS_KEYWORD"]
        ]
        
        return BaseResponse(
            success=True,
            message="SQL注入检查完成",
            data={
                "injection_risk": {
                    "has_risk": len(injection_violations) > 0,
                    "risk_level": result.security_level.value,
                    "violation_count": len(injection_violations)
                },
                "violations": [
                    {
                        "level": v.level.value,
                        "type": v.type,
                        "message": v.message,
                        "location": v.location,
                        "suggestion": v.suggestion
                    }
                    for v in injection_violations
                ],
                "sanitized_sql": result.sanitized_sql
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"SQL注入检查API错误: {e}")
        raise HTTPException(status_code=500, detail=f"注入检查失败: {str(e)}")


@router.post("/validate-fields", response_model=BaseResponse)
async def validate_field_existence(
    sql_query: str,
    data_source_id: int
):
    """
    验证SQL中引用的表和字段是否存在
    
    Args:
        sql_query: SQL查询语句
        data_source_id: 数据源ID
        
    Returns:
        BaseResponse: 包含字段验证结果的响应
    """
    try:
        if not sql_query or not sql_query.strip():
            raise HTTPException(status_code=400, detail="SQL查询不能为空")
        
        if not data_source_id:
            raise HTTPException(status_code=400, detail="数据源ID不能为空")
        
        # 执行字段存在性验证
        result = await sql_security_service.validate_and_secure_sql(
            sql_query=sql_query.strip(),
            data_source_id=data_source_id
        )
        
        # 筛选存在性相关的违规
        existence_violations = [
            v for v in result.violations 
            if v.type in ["TABLE_NOT_FOUND", "FIELD_NOT_FOUND"]
        ]
        
        return BaseResponse(
            success=True,
            message="字段存在性验证完成",
            data={
                "existence_check": {
                    "all_exist": len(existence_violations) == 0,
                    "violation_count": len(existence_violations)
                },
                "violations": [
                    {
                        "level": v.level.value,
                        "type": v.type,
                        "message": v.message,
                        "suggestion": v.suggestion
                    }
                    for v in existence_violations
                ],
                "references": {
                    "tables": [
                        {
                            "name": t.table_name,
                            "alias": t.alias,
                            "schema": t.schema
                        }
                        for t in result.table_references
                    ],
                    "fields": [
                        {
                            "name": f.field_name,
                            "table": f.table_name,
                            "table_alias": f.table_alias
                        }
                        for f in result.field_references
                    ]
                }
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"字段验证API错误: {e}")
        raise HTTPException(status_code=500, detail=f"字段验证失败: {str(e)}")


@router.get("/security-config", response_model=BaseResponse)
async def get_security_config():
    """
    获取SQL安全配置信息
    
    Returns:
        BaseResponse: 包含安全配置的响应
    """
    try:
        validator = sql_security_service.validator
        
        return BaseResponse(
            success=True,
            message="获取安全配置成功",
            data={
                "limits": {
                    "max_table_count": validator.max_table_count,
                    "max_join_count": validator.max_join_count,
                    "max_subquery_count": validator.max_subquery_count,
                    "max_complexity_score": validator.max_complexity_score
                },
                "dangerous_keywords": list(validator.dangerous_keywords),
                "allowed_operations": ["SELECT"],
                "blocked_operations": ["DROP", "DELETE", "TRUNCATE", "ALTER", "CREATE"],
                "warning_operations": ["INSERT", "UPDATE"]
            }
        )
        
    except Exception as e:
        logger.error(f"获取安全配置API错误: {e}")
        raise HTTPException(status_code=500, detail=f"获取配置失败: {str(e)}")


@router.post("/sanitize", response_model=BaseResponse)
async def sanitize_sql(sql_query: str):
    """
    清理SQL查询
    
    Args:
        sql_query: SQL查询语句
        
    Returns:
        BaseResponse: 包含清理后SQL的响应
    """
    try:
        if not sql_query or not sql_query.strip():
            raise HTTPException(status_code=400, detail="SQL查询不能为空")
        
        # 执行SQL清理
        result = await sql_security_service.validate_and_secure_sql(sql_query.strip())
        
        return BaseResponse(
            success=True,
            message="SQL清理完成",
            data={
                "original_sql": sql_query,
                "sanitized_sql": result.sanitized_sql,
                "security_level": result.security_level.value,
                "changes_made": result.sanitized_sql != sql_query.strip()
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"SQL清理API错误: {e}")
        raise HTTPException(status_code=500, detail=f"SQL清理失败: {str(e)}")


def _get_complexity_recommendations(complexity) -> list:
    """获取复杂度优化建议"""
    recommendations = []
    
    if complexity.table_count > 5:
        recommendations.append("考虑减少查询涉及的表数量")
    
    if complexity.join_count > 4:
        recommendations.append("过多的JOIN可能影响性能，考虑优化查询逻辑")
    
    if complexity.subquery_count > 2:
        recommendations.append("考虑使用JOIN替代子查询以提高性能")
    
    if complexity.complexity_score > 50:
        recommendations.append("查询复杂度较高，建议分解为多个简单查询")
    
    if complexity.estimated_cost == "VERY_HIGH":
        recommendations.append("查询成本很高，强烈建议优化")
    
    if not recommendations:
        recommendations.append("查询复杂度在合理范围内")
    
    return recommendations