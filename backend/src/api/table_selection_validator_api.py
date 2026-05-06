"""
选表结果解析和验证 API

任务 5.2.4 的API实现
"""

from typing import Dict, Any, Optional, List
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
import logging
from datetime import datetime

from src.services.table_selection_validator import (
    TableSelectionValidator,
    SelectionValidationResult,
    TableValidationResult,
    RelationValidationResult,
    ValidationIssue,
    ValidationSeverity,
    ValidationCategory
)
from src.services.intelligent_table_selector import TableSelectionResult, TableCandidate

logger = logging.getLogger(__name__)

# 创建路由器
router = APIRouter(prefix="/api/table-selection-validator", tags=["选表结果验证"])

# 全局服务实例
validator_service = TableSelectionValidator()


# 请求模型
class ValidationOptionsModel(BaseModel):
    """验证选项模型"""
    min_confidence_threshold: Optional[float] = Field(0.5, description="最小置信度阈值")
    max_validation_time: Optional[float] = Field(30.0, description="最大验证时间（秒）")
    enable_deep_validation: Optional[bool] = Field(True, description="启用深度验证")
    check_data_samples: Optional[bool] = Field(True, description="检查数据样本")
    validate_relations: Optional[bool] = Field(True, description="验证关联关系")
    
    class Config:
        schema_extra = {
            "example": {
                "min_confidence_threshold": 0.5,
                "max_validation_time": 30.0,
                "enable_deep_validation": True,
                "check_data_samples": True,
                "validate_relations": True
            }
        }


class TableCandidateModel(BaseModel):
    """表候选模型"""
    table_id: str
    table_name: str
    table_comment: str
    relevance_score: float
    confidence: str
    selection_reasons: List[str]
    matched_keywords: List[str]
    business_meaning: str
    relation_paths: List[Dict[str, Any]]
    
    class Config:
        schema_extra = {
            "example": {
                "table_id": "tbl_001",
                "table_name": "products",
                "table_comment": "产品信息表",
                "relevance_score": 0.95,
                "confidence": "high",
                "selection_reasons": ["包含产品相关字段"],
                "matched_keywords": ["产品"],
                "business_meaning": "存储产品基本信息",
                "relation_paths": []
            }
        }


class TableSelectionResultModel(BaseModel):
    """表选择结果模型"""
    primary_tables: List[TableCandidateModel]
    related_tables: List[TableCandidateModel]
    selection_strategy: str
    total_relevance_score: float
    recommended_joins: List[Dict[str, Any]]
    selection_explanation: str
    processing_time: float
    ai_reasoning: str
    
    class Config:
        schema_extra = {
            "example": {
                "primary_tables": [],
                "related_tables": [],
                "selection_strategy": "ai_based",
                "total_relevance_score": 0.95,
                "recommended_joins": [],
                "selection_explanation": "基于AI模型选择了相关表",
                "processing_time": 1.23,
                "ai_reasoning": "AI推理过程"
            }
        }


class ValidationRequest(BaseModel):
    """验证请求模型"""
    selection_result: TableSelectionResultModel = Field(..., description="选表结果")
    data_source_id: Optional[str] = Field(None, description="数据源ID")
    validation_options: Optional[ValidationOptionsModel] = Field(None, description="验证选项")
    
    class Config:
        schema_extra = {
            "example": {
                "selection_result": {
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
                            "relation_paths": []
                        }
                    ],
                    "related_tables": [],
                    "selection_strategy": "ai_based",
                    "total_relevance_score": 0.95,
                    "recommended_joins": [],
                    "selection_explanation": "选择了产品表",
                    "processing_time": 1.23,
                    "ai_reasoning": "用户询问产品信息"
                },
                "data_source_id": "ds_001",
                "validation_options": {
                    "enable_deep_validation": True,
                    "check_data_samples": True
                }
            }
        }


# 响应模型
class ValidationIssueResponse(BaseModel):
    """验证问题响应模型"""
    category: str
    severity: str
    table_name: str
    field_name: Optional[str]
    message: str
    suggestion: str
    details: Dict[str, Any]
    
    class Config:
        schema_extra = {
            "example": {
                "category": "existence",
                "severity": "error",
                "table_name": "products",
                "field_name": None,
                "message": "表不存在",
                "suggestion": "检查表名是否正确",
                "details": {"table_id": "tbl_001"}
            }
        }


class TableValidationResponse(BaseModel):
    """表验证响应模型"""
    table_name: str
    table_id: str
    is_valid: bool
    exists: bool
    accessible: bool
    data_integrity_score: float
    issues: List[ValidationIssueResponse]
    metadata: Dict[str, Any]
    
    class Config:
        schema_extra = {
            "example": {
                "table_name": "products",
                "table_id": "tbl_001",
                "is_valid": True,
                "exists": True,
                "accessible": True,
                "data_integrity_score": 0.95,
                "issues": [],
                "metadata": {
                    "field_count": 10,
                    "has_data": True
                }
            }
        }


class RelationValidationResponse(BaseModel):
    """关联验证响应模型"""
    source_table: str
    target_table: str
    is_valid: bool
    relation_exists: bool
    join_feasible: bool
    business_reasonable: bool
    confidence_score: float
    issues: List[ValidationIssueResponse]
    recommended_join: Optional[Dict[str, Any]]
    
    class Config:
        schema_extra = {
            "example": {
                "source_table": "products",
                "target_table": "categories",
                "is_valid": True,
                "relation_exists": True,
                "join_feasible": True,
                "business_reasonable": True,
                "confidence_score": 0.9,
                "issues": [],
                "recommended_join": {
                    "join_type": "INNER",
                    "join_condition": "products.category_id = categories.id"
                }
            }
        }


class ValidationResponse(BaseModel):
    """验证响应模型"""
    is_valid: bool
    overall_confidence: float
    table_validations: List[TableValidationResponse]
    relation_validations: List[RelationValidationResponse]
    selection_explanation: str
    transparency_report: Dict[str, Any]
    recommendations: List[str]
    processing_time: float
    
    class Config:
        schema_extra = {
            "example": {
                "is_valid": True,
                "overall_confidence": 0.92,
                "table_validations": [],
                "relation_validations": [],
                "selection_explanation": "所有选中的表都通过了验证",
                "transparency_report": {
                    "selection_summary": {
                        "primary_tables_count": 1,
                        "total_relevance_score": 0.95
                    }
                },
                "recommendations": ["所有表都可以安全使用"],
                "processing_time": 2.34
            }
        }


class ValidationStatisticsResponse(BaseModel):
    """验证统计响应模型"""
    total_validations: int
    successful_validations: int
    success_rate: float
    average_processing_time: float
    common_issues: Dict[str, int]
    configuration: Dict[str, Any]
    
    class Config:
        schema_extra = {
            "example": {
                "total_validations": 100,
                "successful_validations": 85,
                "success_rate": 0.85,
                "average_processing_time": 2.5,
                "common_issues": {
                    "existence_warning": 5,
                    "integrity_info": 10
                },
                "configuration": {
                    "min_confidence_threshold": 0.5
                }
            }
        }


# 辅助函数
def convert_table_candidate_model_to_domain(model: TableCandidateModel) -> TableCandidate:
    """将模型转换为领域对象"""
    from src.services.intelligent_table_selector import TableSelectionConfidence
    
    # 转换置信度枚举
    confidence_map = {
        "high": TableSelectionConfidence.HIGH,
        "medium": TableSelectionConfidence.MEDIUM,
        "low": TableSelectionConfidence.LOW
    }
    
    return TableCandidate(
        table_id=model.table_id,
        table_name=model.table_name,
        table_comment=model.table_comment,
        relevance_score=model.relevance_score,
        confidence=confidence_map.get(model.confidence, TableSelectionConfidence.MEDIUM),
        selection_reasons=model.selection_reasons,
        matched_keywords=model.matched_keywords,
        business_meaning=model.business_meaning,
        relation_paths=model.relation_paths,
        semantic_context={}
    )


def convert_selection_result_model_to_domain(model: TableSelectionResultModel) -> TableSelectionResult:
    """将选择结果模型转换为领域对象"""
    return TableSelectionResult(
        primary_tables=[convert_table_candidate_model_to_domain(t) for t in model.primary_tables],
        related_tables=[convert_table_candidate_model_to_domain(t) for t in model.related_tables],
        selection_strategy=model.selection_strategy,
        total_relevance_score=model.total_relevance_score,
        recommended_joins=model.recommended_joins,
        selection_explanation=model.selection_explanation,
        processing_time=model.processing_time,
        ai_reasoning=model.ai_reasoning
    )


def convert_validation_issue_to_response(issue: ValidationIssue) -> ValidationIssueResponse:
    """将验证问题转换为响应模型"""
    return ValidationIssueResponse(
        category=issue.category.value,
        severity=issue.severity.value,
        table_name=issue.table_name,
        field_name=issue.field_name,
        message=issue.message,
        suggestion=issue.suggestion,
        details=issue.details
    )


def convert_table_validation_to_response(validation: TableValidationResult) -> TableValidationResponse:
    """将表验证结果转换为响应模型"""
    return TableValidationResponse(
        table_name=validation.table_name,
        table_id=validation.table_id,
        is_valid=validation.is_valid,
        exists=validation.exists,
        accessible=validation.accessible,
        data_integrity_score=validation.data_integrity_score,
        issues=[convert_validation_issue_to_response(issue) for issue in validation.issues],
        metadata=validation.metadata
    )


def convert_relation_validation_to_response(validation: RelationValidationResult) -> RelationValidationResponse:
    """将关联验证结果转换为响应模型"""
    return RelationValidationResponse(
        source_table=validation.source_table,
        target_table=validation.target_table,
        is_valid=validation.is_valid,
        relation_exists=validation.relation_exists,
        join_feasible=validation.join_feasible,
        business_reasonable=validation.business_reasonable,
        confidence_score=validation.confidence_score,
        issues=[convert_validation_issue_to_response(issue) for issue in validation.issues],
        recommended_join=validation.recommended_join
    )


def convert_validation_result_to_response(result: SelectionValidationResult) -> ValidationResponse:
    """将验证结果转换为响应模型"""
    return ValidationResponse(
        is_valid=result.is_valid,
        overall_confidence=result.overall_confidence,
        table_validations=[convert_table_validation_to_response(tv) for tv in result.table_validations],
        relation_validations=[convert_relation_validation_to_response(rv) for rv in result.relation_validations],
        selection_explanation=result.selection_explanation,
        transparency_report=result.transparency_report,
        recommendations=result.recommendations,
        processing_time=result.processing_time
    )


# API端点
@router.post("/validate", response_model=ValidationResponse, summary="验证选表结果")
async def validate_selection_result(request: ValidationRequest):
    """
    验证智能选表结果
    
    对选表结果进行全面验证，包括：
    - 表存在性和可访问性验证
    - 数据完整性检查
    - 表间关联关系验证
    - 业务逻辑合理性分析
    
    返回详细的验证报告和改进建议。
    """
    try:
        logger.info("收到选表结果验证请求")
        
        # 转换请求模型为领域对象
        selection_result = convert_selection_result_model_to_domain(request.selection_result)
        
        # 转换验证选项
        validation_options = None
        if request.validation_options:
            validation_options = request.validation_options.dict(exclude_none=True)
        
        # 调用验证服务
        validation_result = validator_service.validate_selection_result(
            selection_result=selection_result,
            data_source_id=request.data_source_id,
            validation_options=validation_options
        )
        
        # 转换为响应模型
        response = convert_validation_result_to_response(validation_result)
        
        logger.info(f"选表验证完成，整体有效性: {response.is_valid}, 置信度: {response.overall_confidence:.2f}")
        return response
        
    except Exception as e:
        logger.error(f"选表验证失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"选表验证过程中发生错误: {str(e)}"
        )


@router.post("/validate/quick", response_model=ValidationResponse, summary="快速验证选表结果")
async def quick_validate_selection_result(request: ValidationRequest):
    """
    快速验证选表结果
    
    执行基础验证，跳过耗时的深度检查：
    - 仅检查表存在性
    - 跳过数据样本检查
    - 简化关联关系验证
    
    适用于需要快速反馈的场景。
    """
    try:
        logger.info("收到快速选表验证请求")
        
        # 合并用户选项（如果有）
        quick_options = {}
        if request.validation_options:
            user_options = request.validation_options.dict(exclude_none=True)
            quick_options.update(user_options)
        
        # 强制设置快速验证选项（覆盖用户选项）
        quick_options.update({
            "enable_deep_validation": False,
            "check_data_samples": False,
            "validate_relations": False,
            "max_validation_time": 10.0
        })
        
        # 转换请求模型
        selection_result = convert_selection_result_model_to_domain(request.selection_result)
        
        # 执行快速验证
        validation_result = validator_service.validate_selection_result(
            selection_result=selection_result,
            data_source_id=request.data_source_id,
            validation_options=quick_options
        )
        
        response = convert_validation_result_to_response(validation_result)
        
        logger.info(f"快速验证完成，处理时间: {response.processing_time:.2f}s")
        return response
        
    except Exception as e:
        logger.error(f"快速验证失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"快速验证过程中发生错误: {str(e)}"
        )


@router.get("/statistics", response_model=ValidationStatisticsResponse, summary="获取验证统计信息")
async def get_validation_statistics():
    """
    获取验证统计信息
    
    包括验证次数、成功率、平均处理时间、常见问题等统计数据。
    """
    try:
        stats = validator_service.get_validation_statistics()
        return ValidationStatisticsResponse(**stats)
        
    except Exception as e:
        logger.error(f"获取验证统计失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"获取验证统计时发生错误: {str(e)}"
        )


@router.get("/config", summary="获取验证配置")
async def get_validation_config():
    """
    获取当前验证配置
    
    返回验证服务的配置参数和阈值设置。
    """
    try:
        config = validator_service.validation_config
        return {
            "configuration": config,
            "description": {
                "min_confidence_threshold": "最小置信度阈值，低于此值的结果被认为不可靠",
                "max_validation_time": "最大验证时间限制（秒）",
                "enable_deep_validation": "是否启用深度验证（包括数据完整性检查）",
                "check_data_samples": "是否检查数据样本",
                "validate_relations": "是否验证表间关联关系"
            }
        }
        
    except Exception as e:
        logger.error(f"获取验证配置失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"获取验证配置时发生错误: {str(e)}"
        )


@router.put("/config", summary="更新验证配置")
async def update_validation_config(config: ValidationOptionsModel):
    """
    更新验证配置
    
    允许动态调整验证参数和阈值。
    """
    try:
        # 更新配置
        new_config = config.dict(exclude_none=True)
        validator_service.validation_config.update(new_config)
        
        logger.info(f"验证配置已更新: {new_config}")
        
        return {
            "message": "验证配置更新成功",
            "updated_config": validator_service.validation_config,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"更新验证配置失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"更新验证配置时发生错误: {str(e)}"
        )


@router.get("/health", summary="健康检查")
async def health_check():
    """
    验证服务健康检查
    
    检查服务状态和依赖组件的可用性。
    """
    try:
        stats = validator_service.get_validation_statistics()
        
        health_status = {
            "status": "healthy",
            "service": "table_selection_validator",
            "version": "1.0.0",
            "timestamp": datetime.now().isoformat(),
            "statistics": {
                "total_validations": stats["total_validations"],
                "success_rate": stats["success_rate"],
                "average_processing_time": stats["average_processing_time"]
            },
            "dependencies": {
                "data_source_service": "available",
                "data_table_service": "available",
                "relation_service": "available"
            },
            "configuration": validator_service.validation_config
        }
        
        return health_status
        
    except Exception as e:
        logger.error(f"健康检查失败: {str(e)}", exc_info=True)
        return {
            "status": "unhealthy",
            "service": "table_selection_validator",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }