"""
财务日历管理 API

提供财务日历数据的导入、查询和解析接口。
"""
import logging
from datetime import date
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from src.database import get_db
from src.models.fiscal_calendar_model import FiscalCalendar
from src.services.time_resolver import FiscalCalendarRepository, TimeResolver

import uuid

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/fiscal-calendar", tags=["财务日历"])

repo = FiscalCalendarRepository()
resolver = TimeResolver()


# ============================================================================
# Pydantic 模型
# ============================================================================

class FiscalCalendarItem(BaseModel):
    """单条财务日历导入数据"""
    fw_label: str
    fw_start_date: str   # YYYY-MM-DD
    fw_end_date: str     # YYYY-MM-DD
    fiscal_month: str
    fiscal_quarter: str
    fiscal_year: str
    natural_year: Optional[int] = None

    @field_validator("fw_start_date", "fw_end_date")
    @classmethod
    def validate_date_format(cls, v: str) -> str:
        try:
            date.fromisoformat(v)
        except ValueError:
            raise ValueError(f"日期格式不正确，应为 YYYY-MM-DD，实际为: {v}")
        return v

    @field_validator("fw_label")
    @classmethod
    def validate_fw_label(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("fw_label 不能为空")
        return v.strip().upper()

    @field_validator("fiscal_month", "fiscal_quarter", "fiscal_year")
    @classmethod
    def validate_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("字段不能为空")
        return v.strip()


class ImportRequest(BaseModel):
    """批量导入请求体"""
    records: List[FiscalCalendarItem]


class ImportResponse(BaseModel):
    """批量导入响应"""
    success: bool
    imported: int
    updated: int
    errors: List[Dict[str, Any]] = []


class ResolveResponse(BaseModel):
    """时间表达解析响应"""
    expr: str
    resolved: bool
    date_ranges: List[Dict[str, str]] = []
    rewritten: Optional[str] = None
    message: Optional[str] = None


class FiscalCalendarRecord(BaseModel):
    """财务日历记录响应"""
    id: str
    fw_label: str
    fw_start_date: str
    fw_end_date: str
    fiscal_month: str
    fiscal_quarter: str
    fiscal_year: str
    natural_year: int
    created_at: Optional[str] = None


class ListResponse(BaseModel):
    """列表查询响应"""
    total: int
    page: int
    size: int
    records: List[FiscalCalendarRecord]


# ============================================================================
# 路由实现
# ============================================================================

@router.post("/import", response_model=ImportResponse)
async def import_fiscal_calendar(
    body: ImportRequest,
    db: Session = Depends(get_db),
):
    """
    批量导入财务日历数据（支持 upsert）。

    相同 fw_label 的记录会被更新，不会报错。
    Requirements: 5.1, 5.4, 5.5
    """
    imported = 0
    updated = 0
    errors: List[Dict[str, Any]] = []

    for idx, item in enumerate(body.records):
        try:
            start = date.fromisoformat(item.fw_start_date)
            end = date.fromisoformat(item.fw_end_date)
            if start > end:
                errors.append({
                    "index": idx,
                    "fw_label": item.fw_label,
                    "error": f"fw_start_date ({item.fw_start_date}) 不能晚于 fw_end_date ({item.fw_end_date})",
                })
                continue

            # 计算 natural_year（若未提供，从 fw_start_date 推断）
            natural_year = item.natural_year if item.natural_year is not None else start.year

            existing = repo.find_by_fw_label(db, item.fw_label, item.fiscal_year)
            if existing:
                # 更新已有记录
                existing.fw_start_date = start
                existing.fw_end_date = end
                existing.fiscal_month = item.fiscal_month
                existing.fiscal_quarter = item.fiscal_quarter
                existing.fiscal_year = item.fiscal_year
                existing.natural_year = natural_year
                updated += 1
            else:
                # 新增记录
                record = FiscalCalendar(
                    id=str(uuid.uuid4()),
                    fw_label=item.fw_label,
                    fw_start_date=start,
                    fw_end_date=end,
                    fiscal_month=item.fiscal_month,
                    fiscal_quarter=item.fiscal_quarter,
                    fiscal_year=item.fiscal_year,
                    natural_year=natural_year,
                )
                db.add(record)
                imported += 1

        except Exception as e:
            errors.append({
                "index": idx,
                "fw_label": getattr(item, "fw_label", "unknown"),
                "error": str(e),
            })

    try:
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"财务日历导入提交失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"数据库提交失败: {str(e)}")

    logger.info(f"财务日历导入完成: 新增 {imported} 条，更新 {updated} 条，错误 {len(errors)} 条")
    return ImportResponse(
        success=len(errors) == 0,
        imported=imported,
        updated=updated,
        errors=errors,
    )


@router.get("/resolve", response_model=ResolveResponse)
async def resolve_time_expression(
    expr: str = Query(..., description="时间表达字符串，如 '本财周'、'FW22'"),
    db: Session = Depends(get_db),
):
    """
    解析时间表达字符串，返回对应的日期范围。

    Requirements: 5.2
    """
    if not expr or not expr.strip():
        raise HTTPException(status_code=400, detail="expr 参数不能为空")

    try:
        ctx = await resolver.resolve(expr, db)
    except Exception as e:
        logger.error(f"时间解析异常: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"解析失败: {str(e)}")

    if ctx is None:
        return ResolveResponse(
            expr=expr,
            resolved=False,
            message="未识别到时间表达，或时间标签在财务日历中不存在",
        )

    date_ranges = [
        {
            "label": dr.label,
            "expr_type": dr.expr_type,
            "start_date": dr.start_date,
            "end_date": dr.end_date,
        }
        for dr in ctx.date_ranges
    ]

    return ResolveResponse(
        expr=expr,
        resolved=True,
        date_ranges=date_ranges,
        rewritten=ctx.rewritten_question,
    )


@router.get("/list", response_model=ListResponse)
async def list_fiscal_calendar(
    page: int = Query(1, ge=1, description="页码，从 1 开始"),
    size: int = Query(20, ge=1, le=200, description="每页记录数"),
    fiscal_year: Optional[str] = Query(None, description="按财年过滤，如 FY2026"),
    db: Session = Depends(get_db),
):
    """
    列表查询财务日历记录，支持分页和财年过滤。

    Requirements: 5.3
    """
    query = db.query(FiscalCalendar)
    if fiscal_year:
        query = query.filter(FiscalCalendar.fiscal_year == fiscal_year)

    total = query.count()
    records_db = (
        query
        .order_by(FiscalCalendar.fw_start_date.asc())
        .offset((page - 1) * size)
        .limit(size)
        .all()
    )

    records = [
        FiscalCalendarRecord(
            id=r.id,
            fw_label=r.fw_label,
            fw_start_date=r.fw_start_date.isoformat() if r.fw_start_date else "",
            fw_end_date=r.fw_end_date.isoformat() if r.fw_end_date else "",
            fiscal_month=r.fiscal_month,
            fiscal_quarter=r.fiscal_quarter,
            fiscal_year=r.fiscal_year,
            natural_year=r.natural_year,
            created_at=r.created_at.isoformat() if r.created_at else None,
        )
        for r in records_db
    ]

    return ListResponse(total=total, page=page, size=size, records=records)


class ToolInvokeRequest(BaseModel):
    """调试/内部调用：执行单个财务日历工具。"""

    tool_name: str = Field(..., description="工具名，如 fiscal_get_nth_week_in_period")
    arguments: Dict[str, Any] = Field(default_factory=dict)


@router.get("/tools/definitions")
async def get_fiscal_tool_definitions():
    """返回 OpenAI-style 的 function definitions，供模型侧注册 tools。"""
    from src.tools.fiscal_calendar_tools import FISCAL_CALENDAR_TOOL_DEFINITIONS

    return {"tools": FISCAL_CALENDAR_TOOL_DEFINITIONS}


@router.post("/tools/invoke")
async def invoke_fiscal_tool(
    body: ToolInvokeRequest,
    db: Session = Depends(get_db),
):
    """按名称与参数执行财务日历工具（便于联调；生产可限制权限或仅内网）。"""
    from src.tools.fiscal_calendar_tools import dispatch_fiscal_calendar_tool

    return dispatch_fiscal_calendar_tool(body.tool_name, body.arguments, db)
