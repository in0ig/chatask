"""
测试数据库设置

这个模块专门用于在测试模式下初始化数据库连接和表结构，避免循环导入问题。

它不被任何其他模块直接导入，而是由测试文件在导入任何其他模块之前执行。
"""
import os
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# 确保在模块加载时立即设置测试模式环境变量
if "TEST_MODE" not in os.environ:
    os.environ["TEST_MODE"] = "true"

# 确保src模块在Python路径中
sys.path.insert(0, "/Users/zhanh391/PC/ChatBI/backend")

# 导入所有模型以确保Base.metadata包含所有表
from src.models.base import Base
from src.models.data_preparation_model import DataTable, TableField
from src.models.data_source_model import DataSource
from src.models.database_models import PromptConfig, SessionContext, ConversationMessage, TokenUsageStats

# 创建SQLite内存数据库引擎（直接创建，不依赖src.database）
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    connect_args={"check_same_thread": False}
)

# 创建所有表
Base.metadata.create_all(bind=engine)

# 创建会话工厂
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 导出全局变量
__all__ = ["engine", "TestingSessionLocal"]