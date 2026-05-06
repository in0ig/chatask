"""
工具模块

包含数据库会话获取等实用工具函数。
"""
from sqlalchemy.orm import Session
from src.database_engine import SessionLocal

def get_db_session() -> Session:
    """
    获取数据库会话
    
    Returns:
        Session: SQLAlchemy数据库会话
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 导出所有公共函数
__all__ = ["get_db_session"]