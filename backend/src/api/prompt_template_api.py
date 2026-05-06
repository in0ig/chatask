# -*- coding: utf-8 -*-
"""
增强版Prompt模板管理API
提供版本管理、A/B测试、Few-Shot样本管理的API接口
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, status, Query, Body
from pydantic import BaseModel, Field
from datetime import datetime

from src.services.prompt_template_manager import (
    enhanced_prompt_manager, 
    TemplateVersion, 
    ABTestStatus,
    PromptTemplateVersion,
    ABTestConfig
)
from src.services.few_shot_sample_manager import (
    enhanced_few_shot_manager,
    SampleType,
    SampleStatus
)
from src.utils import logger

# 创建API路由器
router = APIRouter(
    prefix="/api/prompt-templates",
    tags=["prompt-templates"],
    responses={404: {"description": "未找到"}}
)

# Pydantic 模型

class TemplateVersionCreateRequest(BaseModel):
    name: str = Field(..., description="模板名称")
    content: str = Field(..., description="模板内容")
    variables: List[str] = Field(..., description="变量列表")
    description: str = Field("", description="版本描述")
    created_by: str = Field("system", description="创建者")
    parent_version_id: Optional[str] = Field(None, description="父版本ID")
    metadata: Optional[Dict[str, Any]] = Field(None, description="元数据")

class ABTestCreateRequest(BaseModel):
    name: str = Field(..., description="A/B测试名称")
    description: str = Field(..., description="测试描述")
    template_a_id: str = Field(..., description="模板A的版本ID")
    template_b_id: str = Field(..., description="模板B的版本ID")
    traffic_split: float = Field(0.5, ge=0.0, le=1.0, description="A版本流量比例")
    duration_days: int = Field(7, ge=1, le=30, description="测试持续天数")
    min_sample_size: int = Field(100, ge=10, description="最小样本量")
    success_metric: str = Field("success_rate", description="成功指标")

class SampleCreateRequest(BaseModel):
    prompt_type: str = Field(..., description="Prompt类型")
    input_text: str = Field(..., description="输入文本")
    output_text: str = Field(..., description="输出文本")
    sample_type: str = Field("positive", description="样本类型")
    description: str = Field("", description="样本描述")
    tags: List[str] = Field([], description="标签列表")
    created_by: str = Field("system", description="创建者")

class MetricsUpdateRequest(BaseModel):
    version_id: str = Field(..., description="版本ID")
    success: bool = Field(..., description="是否成功")
    response_time: float = Field(..., ge=0.0, description="响应时间（秒）")
    satisfaction: Optional[float] = Field(None, ge=0.0, le=5.0, description="用户满意度（0-5）")
    token_count: Optional[int] = Field(None, ge=0, description="Token数量")

class RenderRequest(BaseModel):
    prompt_type: str = Field(..., description="Prompt类型")
    variables: Dict[str, Any] = Field(..., description="变量字典")
    user_id: str = Field("default", description="用户ID（用于A/B测试）")

# 通用响应模型
class ResponseModel(BaseModel):
    success: bool
    message: str
    data: Optional[Any] = None

# 模板版本管理API

@router.post("/versions", response_model=ResponseModel)
def create_template_version(request: TemplateVersionCreateRequest):
    """创建新的模板版本"""
    try:
        version = enhanced_prompt_manager.version_manager.create_version(
            name=request.name,
            content=request.content,
            variables=request.variables,
            created_by=request.created_by,
            description=request.description,
            parent_version_id=request.parent_version_id,
            metadata=request.metadata
        )
        
        return ResponseModel(
            success=True,
            message="模板版本创建成功",
            data={
                "version_id": version.version_id,
                "name": version.name,
                "version_status": version.version.value,
                "created_at": version.created_at.isoformat()
            }
        )
    
    except Exception as e:
        logger.error(f"Error creating template version: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建模板版本失败: {str(e)}"
        )

@router.get("/versions/{template_name}", response_model=ResponseModel)
def list_template_versions(template_name: str):
    """列出模板的所有版本"""
    try:
        versions = enhanced_prompt_manager.version_manager.list_versions(template_name)
        
        versions_data = []
        for version in versions:
            versions_data.append({
                "version_id": version.version_id,
                "name": version.name,
                "version_status": version.version.value,
                "created_at": version.created_at.isoformat(),
                "created_by": version.created_by,
                "description": version.description,
                "parent_version_id": version.parent_version_id,
                "metrics": {
                    "usage_count": version.metrics.usage_count,
                    "success_rate": version.metrics.success_rate,
                    "avg_response_time": version.metrics.avg_response_time,
                    "user_satisfaction": version.metrics.user_satisfaction,
                    "error_rate": version.metrics.error_rate,
                    "token_efficiency": version.metrics.token_efficiency,
                    "last_updated": version.metrics.last_updated.isoformat()
                }
            })
        
        return ResponseModel(
            success=True,
            message=f"获取到 {len(versions_data)} 个版本",
            data={"versions": versions_data}
        )
    
    except Exception as e:
        logger.error(f"Error listing template versions: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取模板版本失败: {str(e)}"
        )

@router.put("/versions/{version_id}/activate", response_model=ResponseModel)
def activate_template_version(version_id: str):
    """激活模板版本"""
    try:
        success = enhanced_prompt_manager.version_manager.activate_version(version_id)
        
        if success:
            return ResponseModel(
                success=True,
                message="模板版本激活成功",
                data={"version_id": version_id}
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="模板版本未找到"
            )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error activating template version: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"激活模板版本失败: {str(e)}"
        )

@router.get("/versions/{version_id}", response_model=ResponseModel)
def get_template_version(version_id: str):
    """获取指定版本详情"""
    try:
        version = enhanced_prompt_manager.version_manager.get_version(version_id)
        
        if not version:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="模板版本未找到"
            )
        
        version_data = {
            "version_id": version.version_id,
            "name": version.name,
            "content": version.content,
            "variables": version.variables,
            "version_status": version.version.value,
            "created_at": version.created_at.isoformat(),
            "created_by": version.created_by,
            "description": version.description,
            "metadata": version.metadata,
            "parent_version_id": version.parent_version_id,
            "metrics": {
                "usage_count": version.metrics.usage_count,
                "success_rate": version.metrics.success_rate,
                "avg_response_time": version.metrics.avg_response_time,
                "user_satisfaction": version.metrics.user_satisfaction,
                "error_rate": version.metrics.error_rate,
                "token_efficiency": version.metrics.token_efficiency,
                "last_updated": version.metrics.last_updated.isoformat()
            }
        }
        
        return ResponseModel(
            success=True,
            message="获取版本详情成功",
            data=version_data
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting template version: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取版本详情失败: {str(e)}"
        )

# A/B测试管理API

@router.post("/ab-tests", response_model=ResponseModel)
def create_ab_test(request: ABTestCreateRequest):
    """创建A/B测试"""
    try:
        ab_test = enhanced_prompt_manager.version_manager.create_ab_test(
            name=request.name,
            description=request.description,
            template_a_id=request.template_a_id,
            template_b_id=request.template_b_id,
            traffic_split=request.traffic_split,
            duration_days=request.duration_days,
            min_sample_size=request.min_sample_size,
            success_metric=request.success_metric
        )
        
        return ResponseModel(
            success=True,
            message="A/B测试创建成功",
            data={
                "test_id": ab_test.test_id,
                "name": ab_test.name,
                "status": ab_test.status.value,
                "start_date": ab_test.start_date.isoformat(),
                "end_date": ab_test.end_date.isoformat() if ab_test.end_date else None
            }
        )
    
    except Exception as e:
        logger.error(f"Error creating A/B test: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建A/B测试失败: {str(e)}"
        )

@router.put("/ab-tests/{test_id}/start", response_model=ResponseModel)
def start_ab_test(test_id: str):
    """开始A/B测试"""
    try:
        success = enhanced_prompt_manager.version_manager.start_ab_test(test_id)
        
        if success:
            return ResponseModel(
                success=True,
                message="A/B测试已开始",
                data={"test_id": test_id}
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="A/B测试未找到"
            )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting A/B test: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"开始A/B测试失败: {str(e)}"
        )

@router.put("/ab-tests/{test_id}/stop", response_model=ResponseModel)
def stop_ab_test(test_id: str):
    """停止A/B测试"""
    try:
        success = enhanced_prompt_manager.version_manager.stop_ab_test(test_id)
        
        if success:
            return ResponseModel(
                success=True,
                message="A/B测试已停止",
                data={"test_id": test_id}
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="A/B测试未找到"
            )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error stopping A/B test: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"停止A/B测试失败: {str(e)}"
        )

@router.get("/ab-tests/{test_id}/analysis", response_model=ResponseModel)
def analyze_ab_test(test_id: str):
    """分析A/B测试结果"""
    try:
        analysis = enhanced_prompt_manager.version_manager.analyze_ab_test(test_id)
        
        if "error" in analysis:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=analysis["error"]
            )
        
        return ResponseModel(
            success=True,
            message="A/B测试分析完成",
            data=analysis
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing A/B test: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"分析A/B测试失败: {str(e)}"
        )

# Prompt渲染API

@router.post("/render", response_model=ResponseModel)
def render_prompt(request: RenderRequest):
    """渲染Prompt（支持A/B测试）"""
    try:
        rendered_prompt, version_id = enhanced_prompt_manager.render_prompt_with_ab_test(
            prompt_type=request.prompt_type,
            variables=request.variables,
            user_id=request.user_id
        )
        
        return ResponseModel(
            success=True,
            message="Prompt渲染成功",
            data={
                "rendered_prompt": rendered_prompt,
                "version_id": version_id,
                "prompt_type": request.prompt_type
            }
        )
    
    except Exception as e:
        logger.error(f"Error rendering prompt: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"渲染Prompt失败: {str(e)}"
        )

# 指标更新API

@router.post("/metrics/update", response_model=ResponseModel)
def update_metrics(request: MetricsUpdateRequest):
    """更新模板使用指标"""
    try:
        enhanced_prompt_manager.record_usage(
            version_id=request.version_id,
            success=request.success,
            response_time=request.response_time,
            satisfaction=request.satisfaction,
            token_count=request.token_count
        )
        
        return ResponseModel(
            success=True,
            message="指标更新成功",
            data={"version_id": request.version_id}
        )
    
    except Exception as e:
        logger.error(f"Error updating metrics: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新指标失败: {str(e)}"
        )

@router.get("/performance/{template_name}", response_model=ResponseModel)
def get_template_performance(template_name: str):
    """获取模板性能报告"""
    try:
        performance = enhanced_prompt_manager.get_template_performance(template_name)
        
        if "error" in performance:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=performance["error"]
            )
        
        return ResponseModel(
            success=True,
            message="获取性能报告成功",
            data=performance
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting template performance: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取性能报告失败: {str(e)}"
        )

# Few-Shot样本管理API

@router.post("/samples", response_model=ResponseModel)
def create_sample(request: SampleCreateRequest):
    """创建Few-Shot样本"""
    try:
        sample_type = SampleType(request.sample_type)
        success, errors = enhanced_few_shot_manager.add_sample(
            prompt_type=request.prompt_type,
            input_text=request.input_text,
            output_text=request.output_text,
            sample_type=sample_type,
            description=request.description,
            tags=request.tags,
            created_by=request.created_by
        )
        
        if success:
            return ResponseModel(
                success=True,
                message="样本创建成功",
                data={"warnings": errors if errors else None}
            )
        else:
            return ResponseModel(
                success=False,
                message="样本创建失败",
                data={"errors": errors}
            )
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"无效的样本类型: {request.sample_type}"
        )
    except Exception as e:
        logger.error(f"Error creating sample: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建样本失败: {str(e)}"
        )

@router.get("/samples/{prompt_type}/similar", response_model=ResponseModel)
def get_similar_samples(
    prompt_type: str,
    query_text: str = Query(..., description="查询文本"),
    max_samples: int = Query(3, ge=1, le=10, description="最大样本数"),
    min_similarity: float = Query(0.3, ge=0.0, le=1.0, description="最小相似度"),
    sample_types: Optional[List[str]] = Query(None, description="样本类型过滤")
):
    """获取相似样本"""
    try:
        # 转换样本类型
        type_filters = None
        if sample_types:
            type_filters = [SampleType(t) for t in sample_types]
        
        similar_samples = enhanced_few_shot_manager.get_similar_samples(
            prompt_type=prompt_type,
            query_text=query_text,
            max_samples=max_samples,
            min_similarity=min_similarity,
            sample_types=type_filters
        )
        
        samples_data = []
        for sample, similarity_score in similar_samples:
            samples_data.append({
                "sample_id": sample.sample_id,
                "input_text": sample.input_text,
                "output_text": sample.output_text,
                "sample_type": sample.sample_type.value,
                "similarity_score": similarity_score,
                "description": sample.description,
                "tags": sample.tags,
                "metrics": {
                    "usage_count": sample.metrics.usage_count,
                    "success_rate": sample.metrics.success_rate,
                    "user_feedback_score": sample.metrics.user_feedback_score
                }
            })
        
        return ResponseModel(
            success=True,
            message=f"找到 {len(samples_data)} 个相似样本",
            data={"samples": samples_data}
        )
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"无效的样本类型: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Error getting similar samples: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取相似样本失败: {str(e)}"
        )

@router.get("/samples/{prompt_type}/best", response_model=ResponseModel)
def get_best_samples(
    prompt_type: str,
    max_samples: int = Query(5, ge=1, le=20, description="最大样本数"),
    sample_types: Optional[List[str]] = Query(None, description="样本类型过滤")
):
    """获取最佳样本"""
    try:
        # 转换样本类型
        type_filters = None
        if sample_types:
            type_filters = [SampleType(t) for t in sample_types]
        
        best_samples = enhanced_few_shot_manager.get_best_samples(
            prompt_type=prompt_type,
            max_samples=max_samples,
            sample_types=type_filters
        )
        
        samples_data = []
        for sample in best_samples:
            samples_data.append({
                "sample_id": sample.sample_id,
                "input_text": sample.input_text,
                "output_text": sample.output_text,
                "sample_type": sample.sample_type.value,
                "status": sample.status.value,
                "description": sample.description,
                "tags": sample.tags,
                "created_at": sample.created_at.isoformat(),
                "metrics": {
                    "usage_count": sample.metrics.usage_count,
                    "success_rate": sample.metrics.success_rate,
                    "user_feedback_score": sample.metrics.user_feedback_score,
                    "validation_score": sample.metrics.validation_score
                }
            })
        
        return ResponseModel(
            success=True,
            message=f"获取到 {len(samples_data)} 个最佳样本",
            data={"samples": samples_data}
        )
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"无效的样本类型: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Error getting best samples: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取最佳样本失败: {str(e)}"
        )

@router.get("/samples/statistics", response_model=ResponseModel)
def get_sample_statistics(prompt_type: Optional[str] = Query(None, description="Prompt类型过滤")):
    """获取样本统计信息"""
    try:
        statistics = enhanced_few_shot_manager.get_sample_statistics(prompt_type)
        
        return ResponseModel(
            success=True,
            message="获取统计信息成功",
            data=statistics
        )
    
    except Exception as e:
        logger.error(f"Error getting sample statistics: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取统计信息失败: {str(e)}"
        )

@router.post("/samples/{sample_id}/feedback", response_model=ResponseModel)
def update_sample_feedback(
    sample_id: str,
    success: bool = Body(..., description="是否成功"),
    user_feedback: Optional[float] = Body(None, ge=0.0, le=5.0, description="用户反馈分数")
):
    """更新样本反馈"""
    try:
        updated = enhanced_few_shot_manager.update_sample_feedback(
            sample_id=sample_id,
            success=success,
            user_feedback=user_feedback
        )
        
        if updated:
            return ResponseModel(
                success=True,
                message="样本反馈更新成功",
                data={"sample_id": sample_id}
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="样本未找到"
            )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating sample feedback: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新样本反馈失败: {str(e)}"
        )

@router.delete("/samples/cleanup", response_model=ResponseModel)
def cleanup_low_quality_samples(
    min_validation_score: float = Query(0.5, ge=0.0, le=1.0, description="最小验证分数"),
    min_success_rate: float = Query(0.3, ge=0.0, le=1.0, description="最小成功率"),
    min_usage_count: int = Query(5, ge=1, description="最小使用次数")
):
    """清理低质量样本"""
    try:
        removed_count = enhanced_few_shot_manager.cleanup_low_quality_samples(
            min_validation_score=min_validation_score,
            min_success_rate=min_success_rate,
            min_usage_count=min_usage_count
        )
        
        return ResponseModel(
            success=True,
            message=f"清理完成，移除了 {removed_count} 个低质量样本",
            data={"removed_count": removed_count}
        )
    
    except Exception as e:
        logger.error(f"Error cleaning up samples: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"清理样本失败: {str(e)}"
        )

# 导出路由器
__all__ = ["router"]