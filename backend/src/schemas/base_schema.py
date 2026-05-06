"""
基础响应模式定义
"""
from typing import Generic, TypeVar, Optional, Any
from pydantic import BaseModel

T = TypeVar('T')

class BaseResponse(BaseModel, Generic[T]):
    """
    通用API响应模式
    
    Attributes:
        success: 请求是否成功
        message: 响应消息
        data: 响应数据
        error_code: 错误代码（可选）
    """
    success: bool
    message: str
    data: Optional[T] = None
    error_code: Optional[str] = None
    
    class Config:
        """Pydantic配置"""
        # 允许任意类型
        arbitrary_types_allowed = True
        # 使用枚举值
        use_enum_values = True
        # JSON编码器
        json_encoders = {
            # 可以在这里添加自定义编码器
        }

class ErrorResponse(BaseModel):
    """
    错误响应模式
    
    Attributes:
        success: 固定为False
        message: 错误消息
        error_code: 错误代码
        details: 错误详情（可选）
    """
    success: bool = False
    message: str
    error_code: str
    details: Optional[Any] = None

class PaginatedResponse(BaseModel, Generic[T]):
    """
    分页响应模式
    
    Attributes:
        success: 请求是否成功
        message: 响应消息
        data: 响应数据列表
        total: 总记录数
        page: 当前页码
        page_size: 每页大小
        total_pages: 总页数
    """
    success: bool
    message: str
    data: list[T]
    total: int
    page: int
    page_size: int
    total_pages: int
    
    class Config:
        """Pydantic配置"""
        arbitrary_types_allowed = True
        use_enum_values = True