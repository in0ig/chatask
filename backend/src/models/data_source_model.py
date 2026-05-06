"""
数据源模型
"""
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, Enum, Integer, Text, func
from sqlalchemy.orm import relationship
import uuid

from .base import Base


class DataSource(Base):
    """
    数据源配置模型
    支持 DATABASE 和 FILE 两种类型
    支持 SQL_AUTH 和 WINDOWS_AUTH 认证方式
    """
    __tablename__ = 'data_sources'

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), comment='数据源ID（UUID）')
    name = Column(String(100), nullable=False, index=True, comment='数据源名称')
    source_type = Column(Enum('DATABASE', 'FILE'), nullable=False, index=True, comment='数据源类型：DATABASE或FILE')
    db_type = Column(String(50), nullable=True, comment='数据库类型：MySQL、SQL Server、PostgreSQL、ClickHouse')
    host = Column(String(255), nullable=True, comment='数据库主机')
    port = Column(Integer(), nullable=True, comment='数据库端口')
    database_name = Column(String(100), nullable=True, comment='数据库名称')
    auth_type = Column(Enum('SQL_AUTH', 'WINDOWS_AUTH'), nullable=True, comment='认证方式：SQL_AUTH或WINDOWS_AUTH')
    username = Column(String(100), nullable=True, comment='用户名')
    password = Column(String(255), nullable=True, comment='密码（加密存储）')
    domain = Column(String(100), nullable=True, comment='域（Windows认证使用）')
    file_path = Column(String(500), nullable=True, comment='文件路径（当source_type为FILE时）')
    connection_status = Column(Enum('CONNECTED', 'DISCONNECTED', 'TESTING', 'FAILED'), nullable=True, comment='连接状态')
    last_test_time = Column(DateTime(), nullable=True, comment='最后测试时间')
    description = Column(Text(), nullable=True, comment='描述')
    status = Column(Boolean(), default=True, index=True, comment='是否启用')
    created_by = Column(String(100), nullable=False, comment='创建人')
    created_at = Column(DateTime(), default=func.now(), comment='创建时间')
    updated_at = Column(DateTime(), default=func.now(), onupdate=func.now(), comment='更新时间')

    # 关系：一个数据源可以有多个数据表
    data_tables = relationship('DataTable', back_populates='data_source')
    
    # 关系：一个数据源可以有多个动态字典配置
    dynamic_configs = relationship('DynamicDictionaryConfig', back_populates='data_source')

    def __repr__(self):
        return f"<DataSource(id={self.id}, name='{self.name}', type='{self.source_type}', status={self.status})>"

    def to_dict(self):
        """转换为字典格式，便于序列化"""
        return {
            'id': self.id,
            'name': self.name,
            'source_type': self.source_type,
            'db_type': self.db_type,
            'host': self.host,
            'port': self.port,
            'database_name': self.database_name,
            'auth_type': self.auth_type,
            'username': self.username,
            # 密码不返回
            'domain': self.domain,
            'file_path': self.file_path,
            'connection_status': self.connection_status,
            'last_test_time': self.last_test_time.isoformat() if self.last_test_time else None,
            'description': self.description,
            'status': self.status,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
