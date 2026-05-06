from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional, Any
from enum import Enum
from datetime import datetime

# 数据源类型枚举
class DataSourceType(str, Enum):
    DATABASE = "DATABASE"
    FILE = "FILE"

# 数据库类型枚举 - ChatBI只支持MySQL和SQL Server
class DatabaseType(str, Enum):
    MYSQL = "MySQL"
    SQL_SERVER = "SQL Server"

# 认证方式枚举
class AuthType(str, Enum):
    SQL_AUTH = "SQL_AUTH"
    WINDOWS_AUTH = "WINDOWS_AUTH"

# 连接状态枚举
class ConnectionStatus(str, Enum):
    CONNECTED = "CONNECTED"
    DISCONNECTED = "DISCONNECTED"
    TESTING = "TESTING"
    FAILED = "FAILED"

# 数据源创建请求模型
class DataSourceCreate(BaseModel):
    """创建数据源请求模型"""
    name: str = Field(..., description="数据源名称")
    source_type: DataSourceType = Field(..., description="数据源类型：DATABASE或FILE")
    db_type: Optional[DatabaseType] = Field(None, description="数据库类型：MySQL、SQL Server")
    host: Optional[str] = Field(None, description="数据库主机")
    port: Optional[int] = Field(None, description="数据库端口")
    database_name: Optional[str] = Field(None, description="数据库名称")
    auth_type: Optional[AuthType] = Field(None, description="认证方式：SQL_AUTH或WINDOWS_AUTH")
    username: Optional[str] = Field(None, description="用户名")
    password: Optional[str] = Field(None, description="密码（加密存储）")
    domain: Optional[str] = Field(None, description="域（Windows认证使用）")
    file_path: Optional[str] = Field(None, description="文件路径（当source_type为FILE时）")
    description: Optional[str] = Field(None, description="描述")
    status: Optional[bool] = Field(True, description="是否启用")
    created_by: str = Field(..., description="创建人")

    @field_validator('password')
    @classmethod
    def password_must_be_valid(cls, v):
        if v is not None and len(v) < 8:
            raise ValueError('密码长度不能少于8位')
        return v

    @model_validator(mode='after')
    def validate_sql_server_auth_type(self) -> 'DataSourceCreate':
        """当数据库类型为SQL Server时，认证方式为必填项"""
        if self.db_type == DatabaseType.SQL_SERVER and not self.auth_type:
            raise ValueError('当数据库类型为SQL Server时，认证方式为必填项')
        return self

# 数据源更新请求模型
class DataSourceUpdate(BaseModel):
    """更新数据源请求模型"""
    name: Optional[str] = Field(None, description="数据源名称")
    source_type: Optional[DataSourceType] = Field(None, description="数据源类型：DATABASE或FILE")
    db_type: Optional[DatabaseType] = Field(None, description="数据库类型：MySQL、SQL Server")
    host: Optional[str] = Field(None, description="数据库主机")
    port: Optional[int] = Field(None, description="数据库端口")
    database_name: Optional[str] = Field(None, description="数据库名称")
    auth_type: Optional[AuthType] = Field(None, description="认证方式：SQL_AUTH或WINDOWS_AUTH")
    username: Optional[str] = Field(None, description="用户名")
    password: Optional[str] = Field(None, description="密码（加密存储）")
    domain: Optional[str] = Field(None, description="域（Windows认证使用）")
    file_path: Optional[str] = Field(None, description="文件路径（当source_type为FILE时）")
    description: Optional[str] = Field(None, description="描述")
    status: Optional[bool] = Field(None, description="是否启用")
    created_by: Optional[str] = Field(None, description="创建人")

    @field_validator('password')
    @classmethod
    def password_must_be_valid(cls, v):
        if v is not None and len(v) < 8:
            raise ValueError('密码长度不能少于8位')
        return v

    @model_validator(mode='after')
    def validate_sql_server_auth_type(self) -> 'DataSourceUpdate':
        """当数据库类型为SQL Server时，认证方式为必填项"""
        if self.db_type == DatabaseType.SQL_SERVER and not self.auth_type:
            raise ValueError('当数据库类型为SQL Server时，认证方式为必填项')
        return self

# 数据源连接测试请求模型
class DataSourceTestConnection(BaseModel):
    """数据源连接测试请求模型"""
    name: str = Field(..., description="数据源名称")
    source_type: DataSourceType = Field(..., description="数据源类型：DATABASE或FILE")
    db_type: Optional[DatabaseType] = Field(None, description="数据库类型：MySQL、SQL Server")
    host: Optional[str] = Field(None, description="数据库主机")
    port: Optional[int] = Field(None, description="数据库端口")
    database_name: Optional[str] = Field(None, description="数据库名称")
    auth_type: Optional[AuthType] = Field(None, description="认证方式：SQL_AUTH或WINDOWS_AUTH")
    username: Optional[str] = Field(None, description="用户名")
    password: Optional[str] = Field(None, description="密码（加密存储）")
    domain: Optional[str] = Field(None, description="域（Windows认证使用）")
    file_path: Optional[str] = Field(None, description="文件路径（当source_type为FILE时）")
    description: Optional[str] = Field(None, description="描述")
    created_by: str = Field(..., description="创建人")

    @model_validator(mode='after')
    def validate_sql_server_auth_type(self) -> 'DataSourceTestConnection':
        """当数据库类型为SQL Server时，认证方式为必填项"""
        if self.db_type == DatabaseType.SQL_SERVER and not self.auth_type:
            raise ValueError('当数据库类型为SQL Server时，认证方式为必填项')
        return self

# 数据源响应模型
class DataSourceResponse(BaseModel):
    """数据源响应模型"""
    id: str = Field(..., description="数据源ID（UUID）")
    name: str = Field(..., description="数据源名称")
    source_type: DataSourceType = Field(..., description="数据源类型：DATABASE或FILE")
    db_type: Optional[DatabaseType] = Field(None, description="数据库类型：MySQL、SQL Server")
    host: Optional[str] = Field(None, description="数据库主机")
    port: Optional[int] = Field(None, description="数据库端口")
    database_name: Optional[str] = Field(None, description="数据库名称")
    auth_type: Optional[AuthType] = Field(None, description="认证方式：SQL_AUTH或WINDOWS_AUTH")
    username: Optional[str] = Field(None, description="用户名")
    domain: Optional[str] = Field(None, description="域（Windows认证使用）")
    file_path: Optional[str] = Field(None, description="文件路径（当source_type为FILE时）")
    connection_status: Optional[ConnectionStatus] = Field(None, description="连接状态")
    last_test_time: Optional[str] = Field(None, description="最后测试时间")
    description: Optional[str] = Field(None, description="描述")
    status: bool = Field(..., description="是否启用")
    created_by: str = Field(..., description="创建人")
    created_at: str = Field(..., description="创建时间")
    updated_at: str = Field(..., description="更新时间")

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm(cls, obj):
        """从 ORM 对象创建响应模型，自动转换 datetime"""
        data = {
            'id': obj.id,
            'name': obj.name,
            'source_type': obj.source_type,
            'db_type': obj.db_type,
            'host': obj.host,
            'port': obj.port,
            'database_name': obj.database_name,
            'auth_type': obj.auth_type,
            'username': obj.username,
            'domain': obj.domain,
            'file_path': obj.file_path,
            'connection_status': obj.connection_status,
            'last_test_time': obj.last_test_time.isoformat() if obj.last_test_time else None,
            'description': obj.description,
            'status': obj.status,
            'created_by': obj.created_by,
            'created_at': obj.created_at.isoformat() if obj.created_at else None,
            'updated_at': obj.updated_at.isoformat() if obj.updated_at else None
        }
        return cls(**data)

# 数据源列表响应模型
class DataSourceListResponse(BaseModel):
    """数据源列表响应模型"""
    data: list[DataSourceResponse] = Field(..., description="数据源列表")
    total: int = Field(..., description="总数量")

    model_config = {"from_attributes": True}