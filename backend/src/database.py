"""
数据库工具模块

提供数据库会话获取函数，供FastAPI依赖注入使用。
"""
import os
import logging
import tempfile
from src.database_engine import SessionLocal as ProductionSessionLocal
from src.database_engine import engine as ProductionEngine
from src.database_engine import Base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# 设置日志记录器
logger = logging.getLogger(__name__)

# 检查是否在测试模式下
if os.getenv("TEST_MODE", "false").lower() == "true":
    # 在测试模式下，使用SQLite文件数据库，确保连接共享
    # 创建临时文件作为SQLite数据库文件
    TEST_DB_PATH = os.path.join(tempfile.gettempdir(), "test_data_table.db")
    
    # 创建测试数据库引擎，使用文件数据库而非内存数据库
    TEST_ENGINE = create_engine(
        f"sqlite:///{TEST_DB_PATH}",
        connect_args={"check_same_thread": False},
        echo=False
    )
    
    # 创建测试会话工厂
    TEST_SESSION_LOCAL = sessionmaker(autocommit=False, autoflush=False, bind=TEST_ENGINE)
    
    # 在测试模式下，不在此处创建表，由src/database_engine.py负责创建
    # 这样可以确保表创建逻辑只在一个地方
    
    # 导出测试数据库会话生成器函数，供FastAPI依赖注入使用
    def get_db():
        db = TEST_SESSION_LOCAL()
        try:
            yield db
        finally:
            db.close()
    
    # 导出测试引擎供测试使用
    engine = TEST_ENGINE
    SessionLocal = TEST_SESSION_LOCAL
    logger.info("测试模式已启用，使用SQLite文件数据库")
else:
    # 使用生产模式的数据库连接生成器函数
    def get_db():
        db = ProductionSessionLocal()
        try:
            yield db
        finally:
            db.close()
    
    # 导出生产引擎
    engine = ProductionEngine
    SessionLocal = ProductionSessionLocal
    logger.info("生产模式已启用，使用MySQL数据库")