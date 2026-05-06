"""
SQL生成服务相关的数据模型定义

任务 5.4.1 的Schema定义
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from enum import Enum


class SQLDialectEnum(str, Enum):
    """SQL方言类型"""
    MYSQL = "mysql"
    SQLSERVER = "sqlserver"
    POSTGRESQL = "postgresql"


class SQLGenerationRequestSchema(BaseModel):
    """SQL生成请求Schema"""
    user_question: str = Field(..., min_length=1, max_length=1000, description="用户问题")
    table_ids: Optional[List[str]] = Field(None, description="相关表ID列表")
    data_source_id: Optional[str] = Field(None, description="数据源ID")
    sql_dialect: SQLDialectEnum = Field(SQLDialectEnum.MYSQL, description="SQL方言类型")
    include_explanation: bool = Field(True, description="是否包含解释")
    max_rows: Optional[int] = Field(1000, ge=1, le=10000, description="最大返回行数")
    
    class Config:
        schema_extra = {
            "example": {
                "user_question": "查询销售额最高的前10个产品",
                "table_ids": ["tbl_001", "tbl_002"],
                "data_source_id": "ds_001",
                "sql_dialect": "mysql",
                "include_explanation": True,
                "max_rows": 1000
            }
        }


class ValidationViolationSchema(BaseModel):
    """验证违规Schema"""
    level: str = Field(..., description="违规级别")
    type: str = Field(..., description="违规类型")
    message: str = Field(..., description="违规消息")


class ValidationResultSchema(BaseModel):
    """验证结果Schema"""
    is_valid: bool = Field(..., description="是否有效")
    security_level: Optional[str] = Field(None, description="安全级别")
    violations: List[ValidationViolationSchema] = Field(default_factory=list, description="违规列表")
    complexity: Optional[Dict[str, Any]] = Field(None, description="复杂度信息")
    error: Optional[str] = Field(None, description="错误信息")


class SQLGenerationResultSchema(BaseModel):
    """SQL生成结果Schema"""
    sql: str = Field(..., description="生成的SQL语句")
    explanation: str = Field("", description="SQL逻辑说明")
    estimated_rows: int = Field(0, ge=0, description="预估结果行数")
    execution_plan: str = Field("", description="执行计划说明")
    confidence: float = Field(0.0, ge=0.0, le=1.0, description="生成置信度")
    generation_time: float = Field(0.0, ge=0.0, description="生成耗时（秒）")
    semantic_context_used: Dict[str, Any] = Field(default_factory=dict, description="使用的语义上下文")
    validation_result: Optional[ValidationResultSchema] = Field(None, description="验证结果")
    
    class Config:
        schema_extra = {
            "example": {
                "sql": "SELECT product_name, SUM(sales_amount) as total_sales FROM products p JOIN sales s ON p.id = s.product_id GROUP BY product_name ORDER BY total_sales DESC LIMIT 10;",
                "explanation": "查询产品表和销售表，按产品名称分组统计销售额，降序排列取前10名",
                "estimated_rows": 10,
                "execution_plan": "使用索引扫描，GROUP BY聚合，排序后限制结果",
                "confidence": 0.95,
                "generation_time": 1.23,
                "semantic_context_used": {
                    "modules_used": ["table_structure", "dictionary", "data_source"],
                    "total_tokens_used": 1500
                },
                "validation_result": {
                    "is_valid": True,
                    "security_level": "safe",
                    "violations": [],
                    "complexity": {
                        "score": 45.0,
                        "estimated_cost": "MEDIUM"
                    }
                }
            }
        }


class BatchSQLGenerationRequestSchema(BaseModel):
    """批量SQL生成请求Schema"""
    requests: List[SQLGenerationRequestSchema] = Field(..., min_items=1, max_items=10, description="批量请求列表")
    
    class Config:
        schema_extra = {
            "example": {
                "requests": [
                    {
                        "user_question": "查询销售额最高的产品",
                        "sql_dialect": "mysql"
                    },
                    {
                        "user_question": "统计每月订单数量",
                        "sql_dialect": "mysql"
                    }
                ]
            }
        }


class BatchSQLGenerationResponseSchema(BaseModel):
    """批量SQL生成响应Schema"""
    results: List[SQLGenerationResultSchema] = Field(..., description="批量结果列表")
    total_processing_time: float = Field(..., ge=0.0, description="总处理时间（秒）")
    success_count: int = Field(..., ge=0, description="成功数量")
    error_count: int = Field(..., ge=0, description="错误数量")
    
    class Config:
        schema_extra = {
            "example": {
                "results": [
                    {
                        "sql": "SELECT * FROM products ORDER BY sales DESC LIMIT 10;",
                        "explanation": "查询销售额最高的产品",
                        "estimated_rows": 10,
                        "execution_plan": "索引扫描",
                        "confidence": 0.95,
                        "generation_time": 1.2,
                        "semantic_context_used": {},
                        "validation_result": {"is_valid": True}
                    }
                ],
                "total_processing_time": 2.5,
                "success_count": 2,
                "error_count": 0
            }
        }


class GenerationStatisticsSchema(BaseModel):
    """生成统计Schema"""
    total_generations: int = Field(..., ge=0, description="总生成次数")
    successful_generations: int = Field(..., ge=0, description="成功生成次数")
    failed_generations: int = Field(..., ge=0, description="失败生成次数")
    success_rate: float = Field(..., ge=0.0, le=1.0, description="成功率")
    average_generation_time: float = Field(..., ge=0.0, description="平均生成时间（秒）")
    average_confidence: float = Field(..., ge=0.0, le=1.0, description="平均置信度")
    syntax_correctness_rate: float = Field(..., ge=0.0, le=1.0, description="语法正确率")
    semantic_accuracy_rate: float = Field(..., ge=0.0, le=1.0, description="语义准确率")
    
    class Config:
        schema_extra = {
            "example": {
                "total_generations": 100,
                "successful_generations": 98,
                "failed_generations": 2,
                "success_rate": 0.98,
                "average_generation_time": 1.5,
                "average_confidence": 0.92,
                "syntax_correctness_rate": 0.98,
                "semantic_accuracy_rate": 0.95
            }
        }


class HealthCheckResponseSchema(BaseModel):
    """健康检查响应Schema"""
    status: str = Field(..., description="服务状态")
    service: str = Field(..., description="服务名称")
    version: str = Field(..., description="服务版本")
    timestamp: str = Field(..., description="检查时间戳")
    statistics: Dict[str, Any] = Field(..., description="统计信息")
    dependencies: Dict[str, str] = Field(..., description="依赖状态")
    error: Optional[str] = Field(None, description="错误信息")
    
    class Config:
        schema_extra = {
            "example": {
                "status": "healthy",
                "service": "sql_generator",
                "version": "1.0.0",
                "timestamp": "2024-01-01T12:00:00",
                "statistics": {
                    "total_generations": 100,
                    "success_rate": 0.98,
                    "average_generation_time": 1.5
                },
                "dependencies": {
                    "ai_service": "available",
                    "semantic_aggregator": "available",
                    "sql_validator": "available"
                }
            }
        }


class ErrorResponseSchema(BaseModel):
    """错误响应Schema"""
    error: str = Field(..., description="错误类型")
    message: str = Field(..., description="错误消息")
    details: Optional[Dict[str, Any]] = Field(None, description="错误详情")
    timestamp: str = Field(..., description="错误时间戳")
    
    class Config:
        schema_extra = {
            "example": {
                "error": "SQLGenerationError",
                "message": "SQL生成过程中发生错误",
                "details": {
                    "user_question": "查询销售额最高的产品",
                    "error_code": "AI_SERVICE_UNAVAILABLE"
                },
                "timestamp": "2024-01-01T12:00:00"
            }
        }
