from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from src.services.prompt_service import get_prompt_service
from src.models.database_models import PromptConfig, PromptType
from src.utils import get_db_session

# 创建API路由器
router = APIRouter(
    prefix="/api/prompts",
    tags=["prompts"],
    responses={404: {"description": "未找到"}}
)

# Pydantic 模型用于请求和响应

class PromptCreateRequest(BaseModel):
    project_id: str
    prompt_type: str  # 从PromptType枚举中选择
    prompt_category: str
    system_prompt: str
    user_prompt_template: str
    examples: Optional[dict] = None
    temperature: float = 0.7
    max_tokens: int = 2048
    created_by: str = "system"

class PromptUpdateRequest(BaseModel):
    project_id: Optional[str] = None
    prompt_type: Optional[str] = None
    prompt_category: Optional[str] = None
    system_prompt: Optional[str] = None
    user_prompt_template: Optional[str] = None
    examples: Optional[dict] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    enabled: Optional[bool] = None
    created_by: Optional[str] = None

class PromptResponse(BaseModel):
    id: int
    project_id: str
    prompt_type: str
    prompt_category: str
    system_prompt: str
    user_prompt_template: str
    examples: Optional[dict] = None
    temperature: float
    max_tokens: int
    enabled: bool
    created_by: str
    created_at: str
    updated_at: str
    
    class Config:
        from_attributes = True  # 允许从SQLAlchemy模型转换

# 通用响应模型
class ResponseModel(BaseModel):
    success: bool
    message: str
    data: Optional[dict] = None

# 获取所有Prompt（支持过滤）
@router.get("", response_model=List[PromptResponse])
def get_prompts(
    project_id: str,
    prompt_type: Optional[str] = None,
    db: Session = Depends(get_db_session)
):
    """
    获取指定项目的所有Prompt配置，可按类型过滤
    
    Args:
        project_id: 项目ID
        prompt_type: 可选的Prompt类型过滤
        
    Returns:
        List[PromptResponse]: Prompt配置列表
        
    Raises:
        HTTPException: 参数验证失败或权限不足
    """
    if not project_id or not project_id.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="project_id不能为空"
        )
        
    # 获取服务实例
    service = get_prompt_service(db)
    
    try:
        prompts = service.get_prompts(project_id, prompt_type)
        return prompts
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取Prompt配置失败: {str(e)}"
        )

# 按类型获取Prompt
@router.get("/{prompt_type}", response_model=List[PromptResponse])
def get_prompts_by_type(
    project_id: str,
    prompt_type: str,
    db: Session = Depends(get_db_session)
):
    """
    根据项目ID和Prompt类型获取Prompt配置
    
    Args:
        project_id: 项目ID
        prompt_type: Prompt类型
        
    Returns:
        List[PromptResponse]: Prompt配置列表
        
    Raises:
        HTTPException: 参数验证失败或权限不足
    """
    if not project_id or not project_id.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="project_id不能为空"
        )
        
    if not prompt_type or not prompt_type.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="prompt_type不能为空"
        )
        
    # 验证prompt_type是否为有效的PromptType枚举值
    valid_types = [pt.value for pt in PromptType]
    if prompt_type not in valid_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"无效的prompt_type: {prompt_type}。有效值: {valid_types}"
        )
        
    # 获取服务实例
    service = get_prompt_service(db)
    
    try:
        prompts = service.get_prompts_by_type(project_id, prompt_type)
        return prompts
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取Prompt配置失败: {str(e)}"
        )

# 获取单个Prompt
@router.get("/{prompt_id}", response_model=PromptResponse)
def get_prompt(
    prompt_id: int,
    db: Session = Depends(get_db_session)
):
    """
    根据ID获取Prompt配置
    
    Args:
        prompt_id: Prompt配置ID
        
    Returns:
        PromptResponse: Prompt配置
        
    Raises:
        HTTPException: 未找到或权限不足
    """
    if prompt_id <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="prompt_id必须为正整数"
        )
        
    # 获取服务实例
    service = get_prompt_service(db)
    
    try:
        prompt = service.get_prompt(prompt_id)
        if not prompt:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"未找到ID为{prompt_id}的Prompt配置"
            )
        return prompt
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取Prompt配置失败: {str(e)}"
        )

# 创建新的Prompt
@router.post("", response_model=PromptResponse, status_code=status.HTTP_201_CREATED)
def create_prompt(
    request: PromptCreateRequest,
    db: Session = Depends(get_db_session)
):
    """
    创建新的Prompt配置
    
    Args:
        request: Prompt创建请求
        
    Returns:
        PromptResponse: 创建的Prompt配置
        
    Raises:
        HTTPException: 参数验证失败或权限不足
    """
    # 获取服务实例
    service = get_prompt_service(db)
    
    try:
        # 验证prompt_type是否为有效的PromptType枚举值
        valid_types = [pt.value for pt in PromptType]
        if request.prompt_type not in valid_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"无效的prompt_type: {request.prompt_type}。有效值: {valid_types}"
            )
            
        # 创建Prompt
        prompt = service.create_prompt(
            project_id=request.project_id,
            prompt_type=request.prompt_type,
            prompt_category=request.prompt_category,
            system_prompt=request.system_prompt,
            user_prompt_template=request.user_prompt_template,
            examples=request.examples,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            created_by=request.created_by
        )
        
        return prompt
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建Prompt配置失败: {str(e)}"
        )

# 更新Prompt
@router.put("/{prompt_id}", response_model=PromptResponse)
def update_prompt(
    prompt_id: int,
    request: PromptUpdateRequest,
    db: Session = Depends(get_db_session)
):
    """
    更新Prompt配置
    
    Args:
        prompt_id: Prompt配置ID
        request: Prompt更新请求
        
    Returns:
        PromptResponse: 更新后的Prompt配置
        
    Raises:
        HTTPException: 参数验证失败、未找到或权限不足
    """
    if prompt_id <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="prompt_id必须为正整数"
        )
        
    # 获取服务实例
    service = get_prompt_service(db)
    
    try:
        # 验证prompt_type是否为有效的PromptType枚举值（如果提供）
        if request.prompt_type is not None:
            valid_types = [pt.value for pt in PromptType]
            if request.prompt_type not in valid_types:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"无效的prompt_type: {request.prompt_type}。有效值: {valid_types}"
                )
                
        # 更新Prompt
        prompt = service.update_prompt(prompt_id, **request.dict(exclude_unset=True))
        
        if not prompt:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"未找到ID为{prompt_id}的Prompt配置"
            )
        
        return prompt
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新Prompt配置失败: {str(e)}"
        )

# 删除Prompt
@router.delete("/{prompt_id}", response_model=ResponseModel)
def delete_prompt(
    prompt_id: int,
    db: Session = Depends(get_db_session)
):
    """
    删除Prompt配置
    
    Args:
        prompt_id: Prompt配置ID
        
    Returns:
        ResponseModel: 删除结果
        
    Raises:
        HTTPException: 参数验证失败或权限不足
    """
    if prompt_id <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="prompt_id必须为正整数"
        )
        
    # 获取服务实例
    service = get_prompt_service(db)
    
    try:
        success = service.delete_prompt(prompt_id)
        
        if success:
            return ResponseModel(
                success=True,
                message=f"成功删除ID为{prompt_id}的Prompt配置"
            )
        else:
            return ResponseModel(
                success=False,
                message=f"未找到ID为{prompt_id}的Prompt配置"
            )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"删除Prompt配置失败: {str(e)}"
        )

# 权限验证装饰器（占位符）
# 在真实实现中，应该实现JWT或OAuth2认证
# def verify_permission(user_id: str, project_id: str, prompt_id: Optional[int] = None):
#     # 实现真正的权限验证逻辑
#     pass

# 导出路由器
# 在main.py中导入此路由器
# app.include_router(prompt_api.router)

# 导出路由器
# 在main.py中导入此路由器
# app.include_router(prompt_api.router)
