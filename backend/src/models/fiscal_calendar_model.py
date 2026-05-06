"""
财务日历数据模型

存储财周/财月/财季/财年与自然日期的映射关系，
供 TimeResolver 中间件查询使用。
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Date, Integer, DateTime, Index, func

from .base import Base


class FiscalCalendar(Base):
    """
    财务日历表

    每行代表一个财周（FW），包含该财周所属的财月、财季、财年信息，
    以及对应的自然日期范围。
    """
    __tablename__ = 'fiscal_calendar'

    id = Column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        comment='主键（UUID）'
    )
    fw_label = Column(
        String(10),
        nullable=False,
        index=True,
        comment='财周标签，如 FW22（同一财年内唯一）'
    )
    fw_start_date = Column(
        Date,
        nullable=False,
        comment='财周开始日期，格式 YYYY-MM-DD'
    )
    fw_end_date = Column(
        Date,
        nullable=False,
        comment='财周结束日期，格式 YYYY-MM-DD'
    )
    fiscal_month = Column(
        String(10),
        nullable=False,
        comment='所属财月标签，如 FM3'
    )
    fiscal_quarter = Column(
        String(10),
        nullable=False,
        comment='所属财季标签，如 FQ1'
    )
    fiscal_year = Column(
        String(10),
        nullable=False,
        comment='所属财年标签，如 FY2026'
    )
    natural_year = Column(
        Integer,
        nullable=False,
        comment='自然年，如 2026'
    )
    created_at = Column(
        DateTime,
        default=func.now(),
        comment='记录创建时间'
    )

    # 复合索引，加速按财月/财季/财年查询
    __table_args__ = (
        # 同一财年内 fw_label 唯一（多财年可复用 FW01~FW52）
        Index('uq_fiscal_year_fw_label', 'fiscal_year', 'fw_label', unique=True),
        Index('idx_fiscal_month', 'fiscal_month'),
        Index('idx_fiscal_quarter', 'fiscal_quarter'),
        Index('idx_fiscal_year', 'fiscal_year'),
        Index('idx_fw_start_date', 'fw_start_date'),
    )

    def __repr__(self):
        return (
            f"<FiscalCalendar("
            f"fw_label='{self.fw_label}', "
            f"fw_start_date={self.fw_start_date}, "
            f"fw_end_date={self.fw_end_date}, "
            f"fiscal_year='{self.fiscal_year}'"
            f")>"
        )

    def to_dict(self):
        """转换为字典格式，便于 JSON 序列化"""
        return {
            'id': self.id,
            'fw_label': self.fw_label,
            'fw_start_date': self.fw_start_date.isoformat() if self.fw_start_date else None,
            'fw_end_date': self.fw_end_date.isoformat() if self.fw_end_date else None,
            'fiscal_month': self.fiscal_month,
            'fiscal_quarter': self.fiscal_quarter,
            'fiscal_year': self.fiscal_year,
            'natural_year': self.natural_year,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
