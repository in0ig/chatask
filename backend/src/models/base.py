"""
共享的 SQLAlchemy Base
所有模型都应该从这个 Base 继承
"""
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()
