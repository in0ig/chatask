"""
动态字典配置相关的 Pydantic 模式
"""
import re
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator


class DynamicDictionaryConfigCreate(BaseModel):
    """创建动态字典配置的请求模式"""
    dictionary_id: str = Field(..., description="字典ID")
    data_source_id: str = Field(..., description="数据源ID")
    sql_query: str = Field(..., description="SQL查询语句")
    key_field: str = Field(..., description="键字段名")
    value_field: str = Field(..., description="值字段名")
    refresh_interval: int = Field(default=3600, description="刷新间隔（秒）", ge=60)

    @validator('sql_query')
    def validate_sql_query(cls, v):
        """验证SQL查询语句"""
        if not v or not v.strip():
            raise ValueError("SQL查询语句不能为空")
        
        # 基本的SQL注入防护 - 检查整个查询语句
        dangerous_keywords = ['DROP', 'DELETE', 'UPDATE', 'INSERT', 'ALTER', 'CREATE', 'TRUNCATE']
        upper_query = v.upper().strip()
        
        # 检查是否包含危险关键字（作为独立单词）
        for keyword in dangerous_keywords:
            # 使用正则表达式确保关键字是独立的单词
            pattern = r'\b' + keyword + r'\b'
            if re.search(pattern, upper_query):
                raise ValueError(f"SQL查询不允许包含 {keyword} 操作")
        
        # 确保查询以SELECT开头
        if not upper_query.startswith('SELECT'):
            raise ValueError("只允许SELECT查询语句")
        
        return v.strip()

    @validator('key_field', 'value_field')
    def validate_field_names(cls, v):
        """验证字段名"""
        if not v or not v.strip():
            raise ValueError("字段名不能为空")
        return v.strip()


class DynamicDictionaryConfigUpdate(BaseModel):
    """更新动态字典配置的请求模式"""
    data_source_id: Optional[str] = Field(None, description="数据源ID")
    sql_query: Optional[str] = Field(None, description="SQL查询语句")
    key_field: Optional[str] = Field(None, description="键字段名")
    value_field: Optional[str] = Field(None, description="值字段名")
    refresh_interval: Optional[int] = Field(None, description="刷新间隔（秒）", ge=60)

    @validator('sql_query')
    def validate_sql_query(cls, v):
        """验证SQL查询语句"""
        if v is not None:
            if not v.strip():
                raise ValueError("SQL查询语句不能为空")
            
            # 基本的SQL注入防护 - 检查整个查询语句
            dangerous_keywords = ['DROP', 'DELETE', 'UPDATE', 'INSERT', 'ALTER', 'CREATE', 'TRUNCATE']
            upper_query = v.upper().strip()
            
            # 检查是否包含危险关键字（作为独立单词）
            for keyword in dangerous_keywords:
                # 使用正则表达式确保关键字是独立的单词
                pattern = r'\b' + keyword + r'\b'
                if re.search(pattern, upper_query):
                    raise ValueError(f"SQL查询不允许包含 {keyword} 操作")
            
            # 确保查询以SELECT开头
            if not upper_query.startswith('SELECT'):
                raise ValueError("只允许SELECT查询语句")
            
            return v.strip()
        return v

    @validator('key_field', 'value_field')
    def validate_field_names(cls, v):
        """验证字段名"""
        if v is not None and not v.strip():
            raise ValueError("字段名不能为空")
        return v.strip() if v else v


class DynamicDictionaryConfigResponse(BaseModel):
    """动态字典配置的响应模式"""
    id: str = Field(..., description="配置ID")
    dictionary_id: str = Field(..., description="字典ID")
    data_source_id: str = Field(..., description="数据源ID")
    sql_query: str = Field(..., description="SQL查询语句")
    key_field: str = Field(..., description="键字段名")
    value_field: str = Field(..., description="值字段名")
    refresh_interval: int = Field(..., description="刷新间隔（秒）")
    last_refresh_time: Optional[datetime] = Field(None, description="最后刷新时间")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")

    class Config:
        from_attributes = True


class QueryTestRequest(BaseModel):
    """测试SQL查询的请求模式"""
    data_source_id: str = Field(..., description="数据源ID")
    sql_query: str = Field(..., description="SQL查询语句")
    key_field: str = Field(..., description="键字段名")
    value_field: str = Field(..., description="值字段名")

    @validator('sql_query')
    def validate_sql_query(cls, v):
        """验证SQL查询语句"""
        if not v or not v.strip():
            raise ValueError("SQL查询语句不能为空")
        
        # 基本的SQL注入防护 - 检查整个查询语句
        dangerous_keywords = ['DROP', 'DELETE', 'UPDATE', 'INSERT', 'ALTER', 'CREATE', 'TRUNCATE']
        upper_query = v.upper().strip()
        
        # 检查是否包含危险关键字（作为独立单词）
        for keyword in dangerous_keywords:
            # 使用正则表达式确保关键字是独立的单词
            pattern = r'\b' + keyword + r'\b'
            if re.search(pattern, upper_query):
                raise ValueError(f"SQL查询不允许包含 {keyword} 操作")
        
        # 确保查询以SELECT开头
        if not upper_query.startswith('SELECT'):
            raise ValueError("只允许SELECT查询语句")
        
        return v.strip()


class QueryTestResponse(BaseModel):
    """测试SQL查询的响应模式"""
    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="结果消息")
    sample_data: Optional[List[Dict[str, Any]]] = Field(None, description="示例数据（最多10条）")
    total_count: Optional[int] = Field(None, description="总记录数")
    execution_time_ms: Optional[int] = Field(None, description="执行时间（毫秒）")


class RefreshResult(BaseModel):
    """刷新结果模式"""
    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="结果消息")
    items_added: int = Field(default=0, description="新增字典项数量")
    items_updated: int = Field(default=0, description="更新字典项数量")
    items_removed: int = Field(default=0, description="删除字典项数量")
    total_items: int = Field(default=0, description="总字典项数量")
    refresh_time: datetime = Field(..., description="刷新时间")
    execution_time_ms: int = Field(..., description="执行时间（毫秒）")


class DynamicDictionaryListResponse(BaseModel):
    """动态字典配置列表响应模式"""
    items: List[DynamicDictionaryConfigResponse] = Field(..., description="配置列表")
    total: int = Field(..., description="总数量")
    page: int = Field(..., description="当前页码")
    page_size: int = Field(..., description="每页大小")