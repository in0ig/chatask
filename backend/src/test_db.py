"""
测试数据库连接管理

这个模块专门用于管理测试模式下的数据库连接，避免循环导入问题。
"""
import os
from tests.unit.test_data_table_api import engine, TestingSessionLocal, Base

# 在模块加载时立即创建所有表
Base.metadata.create_all(bind=engine)

# 导出连接用于其他模块使用
__all__ = ["engine", "TestingSessionLocal"]