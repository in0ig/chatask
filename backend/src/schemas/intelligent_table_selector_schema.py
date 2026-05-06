"""
智能表选择算法相关的数据模型定义

任务 5.2.3 的Schema定义
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from enum import Enum


class TableSelectionConfidenceEnum(str, Enum):
    """表选择置信度等级"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class TableCandidateSchema(BaseModel):
    """表候选信息Schema"""
    table_id: str = Field(..., description="表ID")
    table_name: str = Field(..., description="表名")
    table_comment: str = Field("", description="表注释")
    relevance_score: float = Field(..., ge=0.0, le=1.0, description="相关性评分")
    confidence: TableSelectionConfidenceEnum = Field(..., description="置信度等级")
    selection_reasons: List[str] = Field(default_factory=list, description="选择理由")
    matched_keywords: List[str] = Field(default_factory=list, description="匹配的关键词")
    business_meaning: str = Field("", description="业务含义")
    relation_paths: List[Dict[str, Any]] = Field(default_factory=list, description="关联路径")
    semantic_context: Dict[str, Any] = Field(default_factory=dict, description="语义上下文")
    
    class Config:
        schema_extra = {
            "example": {
                "table_id": "tbl_001",
                "table_name": "products",
                "table_comment": "产品信息表",
                "relevance_score": 0.95,
                "confidence": "high",
                "selection_reasons": ["包含产品相关字段", "与销售查询高度相关"],
                "matched_keywords": ["产品", "销售"],
                "business_meaning": "存储产品基本信息和属性",
                "relation_paths": [
                    {
                        "target_table": "sales",
                        "join_type": "INNER",
                        "join_condition": "products.id = sales.product_id",
                        "confidence": 0.9
                    }
                ],
                "semantic_context": {
                    "data_source_type": "mysql",
                    "table_category": "master_data"
                }
            }
        }


class JoinRecommendationSchema(BaseModel):
    """JOIN推荐Schema"""
    left_table: str = Field(..., description="左表名")
    right_table: str = Field(..., description="右表名")
    join_type: str = Field(..., description="JOIN类型")
    join_condition: str = Field(..., description="JOIN条件")
    confidence: float = Field(..., ge=0.0, le=1.0, description="推荐置信度")
    reasoning: str = Field("", description="推荐理由")
    
    class Config:
        schema_extra = {
            "example": {
                "left_table": "products",
                "right_table": "sales",
                "join_type": "INNER",
                "join_condition": "products.id = sales.product_id",
                "confidence": 0.9,
                "reasoning": "基于外键关系推荐的内连接"
            }
        }


class TableSelectionResultSchema(BaseModel):
    """表选择结果Schema"""
    primary_tables: List[TableCandidateSchema] = Field(default_factory=list, description="主表列表")
    related_tables: List[TableCandidateSchema] = Field(default_factory=list, description="关联表列表")
    selection_strategy: str = Field(..., description="选择策略")
    total_relevance_score: float = Field(..., ge=0.0, description="总体相关性评分")
    recommended_joins: List[JoinRecommendationSchema] = Field(default_factory=list, description="推荐的JOIN语句")
    selection_explanation: str = Field("", description="选择解释")
    processing_time: float = Field(..., ge=0.0, description="处理时间（秒）")
    ai_reasoning: str = Field("", description="AI推理过程")
    
    class Config:
        schema_extra = {
            "example": {
                "primary_tables": [
                    {
                        "table_id": "tbl_001",
                        "table_name": "products",
                        "table_comment": "产品信息表",
                        "relevance_score": 0.95,
                        "confidence": "high",
                        "selection_reasons": ["包含产品相关字段"],
                        "matched_keywords": ["产品"],
                        "business_meaning": "存储产品基本信息",
                        "relation_paths": [],
                        "semantic_context": {}
                    }
                ],
                "related_tables": [
                    {
                        "table_id": "tbl_002",
                        "table_name": "sales",
                        "table_comment": "销售记录表",
                        "relevance_score": 0.85,
                        "confidence": "high",
                        "selection_reasons": ["包含销售相关字段"],
                        "matched_keywords": ["销售"],
                        "business_meaning": "存储销售交易记录",
                        "relation_paths": [],
                        "semantic_context": {}
                    }
                ],
                "selection_strategy": "ai_based",
                "total_relevance_score": 1.8,
                "recommended_joins": [
                    {
                        "left_table": "products",
                        "right_table": "sales",
                        "join_type": "INNER",
                        "join_condition": "products.id = sales.product_id",
                        "confidence": 0.9,
                        "reasoning": "基于外键关系推荐的内连接"
                    }
                ],
                "selection_explanation": "基于用户问题选择了产品表作为主表，销售表作为关联表",
                "processing_time": 1.23,
                "ai_reasoning": "用户询问产品销售额，需要产品表获取产品信息，销售表获取销售数据"
            }
        }


class TableSelectionRequestSchema(BaseModel):
    """表选择请求Schema"""
    user_question: str = Field(..., min_length=1, max_length=1000, description="用户问题")
    data_source_id: Optional[str] = Field(None, description="数据源ID")
    context: Optional[Dict[str, Any]] = Field(None, description="上下文信息")
    
    class Config:
        schema_extra = {
            "example": {
                "user_question": "查询销售额最高的产品",
                "data_source_id": "ds_001",
                "context": {
                    "session_id": "session_123",
                    "previous_tables": ["products", "sales"],
                    "user_preferences": {
                        "max_tables": 5,
                        "include_related": True
                    }
                }
            }
        }


class BatchTableSelectionRequestSchema(BaseModel):
    """批量表选择请求Schema"""
    requests: List[TableSelectionRequestSchema] = Field(..., min_items=1, max_items=10, description="批量请求列表")
    
    class Config:
        schema_extra = {
            "example": {
                "requests": [
                    {
                        "user_question": "查询销售额最高的产品",
                        "data_source_id": "ds_001"
                    },
                    {
                        "user_question": "分析客户购买行为",
                        "data_source_id": "ds_001"
                    }
                ]
            }
        }


class BatchTableSelectionResponseSchema(BaseModel):
    """批量表选择响应Schema"""
    results: List[TableSelectionResultSchema] = Field(..., description="批量结果列表")
    total_processing_time: float = Field(..., ge=0.0, description="总处理时间（秒）")
    success_count: int = Field(..., ge=0, description="成功数量")
    error_count: int = Field(..., ge=0, description="错误数量")
    
    class Config:
        schema_extra = {
            "example": {
                "results": [
                    {
                        "primary_tables": [],
                        "related_tables": [],
                        "selection_strategy": "ai_based",
                        "total_relevance_score": 0.95,
                        "recommended_joins": [],
                        "selection_explanation": "选择结果",
                        "processing_time": 1.23,
                        "ai_reasoning": "AI推理过程"
                    }
                ],
                "total_processing_time": 2.45,
                "success_count": 2,
                "error_count": 0
            }
        }


class SelectionStatisticsSchema(BaseModel):
    """选择统计Schema"""
    total_selections: int = Field(..., ge=0, description="总选择次数")
    successful_selections: int = Field(..., ge=0, description="成功选择次数")
    success_rate: float = Field(..., ge=0.0, le=1.0, description="成功率")
    average_processing_time: float = Field(..., ge=0.0, description="平均处理时间（秒）")
    average_relevance_score: float = Field(..., ge=0.0, le=1.0, description="平均相关性评分")
    configuration: Dict[str, Any] = Field(..., description="配置信息")
    
    class Config:
        schema_extra = {
            "example": {
                "total_selections": 100,
                "successful_selections": 95,
                "success_rate": 0.95,
                "average_processing_time": 1.5,
                "average_relevance_score": 0.85,
                "configuration": {
                    "max_primary_tables": 3,
                    "max_related_tables": 5,
                    "min_relevance_threshold": 0.3,
                    "confidence_thresholds": {
                        "high": 0.8,
                        "medium": 0.5,
                        "low": 0.3
                    }
                }
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
                "service": "intelligent_table_selector",
                "version": "1.0.0",
                "timestamp": "2024-01-01T12:00:00",
                "statistics": {
                    "total_selections": 100,
                    "success_rate": 0.95,
                    "average_processing_time": 1.5
                },
                "dependencies": {
                    "ai_service": "available",
                    "semantic_aggregator": "available",
                    "similarity_engine": "available",
                    "data_integration": "available",
                    "relation_module": "available"
                }
            }
        }


# 错误响应Schema
class ErrorResponseSchema(BaseModel):
    """错误响应Schema"""
    error: str = Field(..., description="错误类型")
    message: str = Field(..., description="错误消息")
    details: Optional[Dict[str, Any]] = Field(None, description="错误详情")
    timestamp: str = Field(..., description="错误时间戳")
    
    class Config:
        schema_extra = {
            "example": {
                "error": "TableSelectionError",
                "message": "表选择过程中发生错误",
                "details": {
                    "user_question": "查询销售额最高的产品",
                    "error_code": "AI_SERVICE_UNAVAILABLE"
                },
                "timestamp": "2024-01-01T12:00:00"
            }
        }