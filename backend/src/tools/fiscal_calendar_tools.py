"""
财务日历工具：供纯模型调用，从 fiscal_calendar 表查询权威日期范围。

说明（与 fiscal_calendar 表数据一致）：
- fiscal_year 存为 FY2026 形式。
- fiscal_month 存为 **FM1..FM12**。模型可传 FM10 / P10 / 10，由 normalize_fiscal_period_label 统一为 FM10。
- 所有区间查询均带 fiscal_year，避免跨财年同名财期合并错误。
"""
from __future__ import annotations

import logging
import re
from datetime import date
from typing import Any, Dict, List, Optional, Union

from sqlalchemy import func
from sqlalchemy.orm import Session

from src.models.fiscal_calendar_model import FiscalCalendar
from src.services.time_resolver import FiscalCalendarRepository, _to_str

logger = logging.getLogger(__name__)

_repo = FiscalCalendarRepository()


def normalize_fiscal_year_label(raw: Optional[Union[str, int]]) -> Optional[str]:
    """
    将用户或模型传入的财年写法规范为 FYYYYY。

    支持：FY2026、FY26、2026、26（两位默认 20xx）。
    """
    if raw is None:
        return None
    s = str(raw).strip().upper().replace(" ", "")
    if re.fullmatch(r"FY\d{4}", s):
        return s
    m = re.fullmatch(r"FY(\d{2})", s)
    if m:
        return f"FY20{m.group(1)}"
    m = re.fullmatch(r"(\d{4})", s)
    if m:
        return f"FY{m.group(1)}"
    m = re.fullmatch(r"(\d{2})", s)
    if m:
        return f"FY20{m.group(1)}"
    return None


def normalize_fw_label(raw: Optional[str]) -> Optional[str]:
    """FW1 / fw01 -> FW01，与库内 fw_label 一致。"""
    if not raw:
        return None
    s = raw.strip().upper()
    m = re.fullmatch(r"FW0*(\d{1,2})", s)
    if not m:
        return None
    return f"FW{int(m.group(1)):02d}"


def normalize_fiscal_period_label(raw: Optional[Union[str, int]]) -> Optional[str]:
    """
    将财月/财期写法规范为 FM1..FM12（与本库 fiscal_month 列一致）。

    支持：FM10、P10（历史写法）、10（纯数字 1-12）。
    """
    if raw is None:
        return None
    if isinstance(raw, int):
        if 1 <= raw <= 12:
            return f"FM{raw}"
        return None
    s = str(raw).strip().upper().replace(" ", "")
    m = re.fullmatch(r"FM0*(\d{1,2})", s)
    if m:
        n = int(m.group(1))
        if 1 <= n <= 12:
            return f"FM{n}"
        return None
    m = re.fullmatch(r"P0*(\d{1,2})", s)
    if m:
        n = int(m.group(1))
        if 1 <= n <= 12:
            return f"FM{n}"
        return None
    m = re.fullmatch(r"(\d{1,2})", s)
    if m:
        n = int(m.group(1))
        if 1 <= n <= 12:
            return f"FM{n}"
        return None
    return None


def _row_to_fw_dict(r: FiscalCalendar) -> Dict[str, Any]:
    return {
        "fw_label": r.fw_label,
        "fw_start_date": _to_str(r.fw_start_date),
        "fw_end_date": _to_str(r.fw_end_date),
        "fiscal_month": r.fiscal_month,
        "fiscal_quarter": r.fiscal_quarter,
        "fiscal_year": r.fiscal_year,
        "natural_year": r.natural_year,
    }


def tool_get_fiscal_week(
    db: Session, fw_label: str, fiscal_year: Optional[str] = None
) -> Dict[str, Any]:
    """按财周标签查询单周；建议始终传 fiscal_year 以免跨财年重复 FW 编号歧义。"""
    fy = normalize_fiscal_year_label(fiscal_year) if fiscal_year else None
    fl = normalize_fw_label(fw_label) if fw_label else None
    if not fl:
        return {"ok": False, "error": f"无效的 fw_label: {fw_label}"}
    row = _repo.find_by_fw_label(db, fl, fy)
    if not row:
        return {
            "ok": False,
            "error": f"未找到财周 {fl}" + (f"（财年 {fy}）" if fy else "（请指定 fiscal_year 或检查数据）"),
        }
    return {"ok": True, "fiscal_week": _row_to_fw_dict(row)}


def tool_get_fiscal_year_range(db: Session, fiscal_year: str) -> Dict[str, Any]:
    fy = normalize_fiscal_year_label(fiscal_year)
    if not fy:
        return {"ok": False, "error": f"无法解析财年: {fiscal_year}"}
    if not db.query(FiscalCalendar).filter(FiscalCalendar.fiscal_year == fy).first():
        return {"ok": False, "error": f"财年中无数据: {fy}"}

    bounds = _repo.find_range_by_fiscal_year(db, fy)
    if not bounds:
        return {"ok": False, "error": f"无法计算财年范围: {fy}"}
    return {
        "ok": True,
        "fiscal_year": fy,
        "start_date": bounds.start_date,
        "end_date": bounds.end_date,
        "label": bounds.label,
    }


def tool_get_fiscal_period_range(
    db: Session, fiscal_year: str, fiscal_period: Union[str, int]
) -> Dict[str, Any]:
    """某财年内一个财期（FM1..FM12）的起止日期（合并该期内所有财周）。"""
    fy = normalize_fiscal_year_label(fiscal_year)
    period = normalize_fiscal_period_label(fiscal_period)
    if not fy:
        return {"ok": False, "error": f"无法解析财年: {fiscal_year}"}
    if not period:
        return {"ok": False, "error": f"无法解析财期: {fiscal_period}"}

    agg = (
        db.query(
            func.min(FiscalCalendar.fw_start_date).label("s"),
            func.max(FiscalCalendar.fw_end_date).label("e"),
        )
        .filter(
            FiscalCalendar.fiscal_year == fy,
            FiscalCalendar.fiscal_month == period,
        )
        .first()
    )
    if not agg or agg.s is None:
        return {
            "ok": False,
            "error": f"未找到 {fy} {period} 的数据（请确认 fiscal_calendar 中是否存在该财年财期）",
        }
    return {
        "ok": True,
        "fiscal_year": fy,
        "fiscal_period": period,
        "start_date": _to_str(agg.s),
        "end_date": _to_str(agg.e),
    }


def tool_list_weeks_in_fiscal_period(
    db: Session, fiscal_year: str, fiscal_period: Union[str, int]
) -> Dict[str, Any]:
    fy = normalize_fiscal_year_label(fiscal_year)
    period = normalize_fiscal_period_label(fiscal_period)
    if not fy:
        return {"ok": False, "error": f"无法解析财年: {fiscal_year}"}
    if not period:
        return {"ok": False, "error": f"无法解析财期: {fiscal_period}"}

    rows = (
        db.query(FiscalCalendar)
        .filter(
            FiscalCalendar.fiscal_year == fy,
            FiscalCalendar.fiscal_month == period,
        )
        .order_by(FiscalCalendar.fw_start_date.asc())
        .all()
    )
    if not rows:
        return {"ok": False, "error": f"{fy} {period} 下无财周记录"}
    return {
        "ok": True,
        "fiscal_year": fy,
        "fiscal_period": period,
        "weeks": [_row_to_fw_dict(r) for r in rows],
        "week_count": len(rows),
    }


def tool_get_nth_week_in_fiscal_period(
    db: Session,
    fiscal_year: str,
    fiscal_period: Union[str, int],
    week_index: int,
) -> Dict[str, Any]:
    """
    财期内第 N 个财周：week_index 从 1 开始；-1 表示该期最后一个财周。
    """
    listed = tool_list_weeks_in_fiscal_period(db, fiscal_year, fiscal_period)
    if not listed.get("ok"):
        return listed
    weeks: List[Dict[str, Any]] = listed["weeks"]
    n = len(weeks)
    if week_index == -1:
        idx = n - 1
    elif 1 <= week_index <= n:
        idx = week_index - 1
    else:
        return {
            "ok": False,
            "error": f"week_index={week_index} 越界，该财期共 {n} 个财周",
        }
    return {"ok": True, "fiscal_week": weeks[idx], "week_index_resolved": idx + 1}


def tool_list_weeks_in_natural_month(
    db: Session, year: int, month: int
) -> Dict[str, Any]:
    """自然年月中，按 fw_start_date 落在该自然月内的财周（与 TimeResolver 一致）。"""
    if not (1 <= month <= 12):
        return {"ok": False, "error": "month 必须在 1-12"}
    rows = _repo.find_fiscal_weeks_by_natural_month(db, year, month)
    if not rows:
        return {"ok": False, "error": f"{year}年{month}月无财周记录"}
    return {
        "ok": True,
        "natural_year": year,
        "natural_month": month,
        "weeks": [_row_to_fw_dict(r) for r in rows],
        "week_count": len(rows),
    }


def tool_get_natural_month_nth_fiscal_week(
    db: Session, year: int, month: int, week_index: int
) -> Dict[str, Any]:
    """自然年月中第 N 个财周（1 起；-1 为最后一个）。"""
    listed = tool_list_weeks_in_natural_month(db, year, month)
    if not listed.get("ok"):
        return listed
    weeks = listed["weeks"]
    n = len(weeks)
    if week_index == -1:
        idx = n - 1
    elif 1 <= week_index <= n:
        idx = week_index - 1
    else:
        return {
            "ok": False,
            "error": f"week_index={week_index} 越界，该自然月共 {n} 个财周",
        }
    return {"ok": True, "fiscal_week": weeks[idx], "week_index_resolved": idx + 1}


# --- OpenAI-compatible tool definitions ---

FISCAL_CALENDAR_TOOL_DEFINITIONS: List[Dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "fiscal_get_week",
            "description": "按财周标签查询单周的起止日期与所属财期、财年。跨财年可能重复 FW01，务必传 fiscal_year。",
            "parameters": {
                "type": "object",
                "properties": {
                    "fw_label": {"type": "string", "description": "如 FW40"},
                    "fiscal_year": {
                        "type": "string",
                        "description": "如 FY2026、FY26",
                    },
                },
                "required": ["fw_label"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "fiscal_get_year_range",
            "description": "查询整个财年的自然日起止范围。",
            "parameters": {
                "type": "object",
                "properties": {
                    "fiscal_year": {"type": "string", "description": "如 FY2026"},
                },
                "required": ["fiscal_year"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "fiscal_get_period_range",
            "description": "查询某一财年下指定财期（FM1-FM12；也可传 P10/10）的合并起止日期。",
            "parameters": {
                "type": "object",
                "properties": {
                    "fiscal_year": {"type": "string"},
                    "fiscal_period": {
                        "type": "string",
                        "description": "P10 / FM10 / 10 均可",
                    },
                },
                "required": ["fiscal_year", "fiscal_period"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "fiscal_list_weeks_in_period",
            "description": "列出某一财年、某一财期内的所有财周（按时间升序）。",
            "parameters": {
                "type": "object",
                "properties": {
                    "fiscal_year": {"type": "string"},
                    "fiscal_period": {"type": "string"},
                },
                "required": ["fiscal_year", "fiscal_period"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "fiscal_get_nth_week_in_period",
            "description": "财期内第 N 个财周（首周=1）；week_index=-1 表示最后一财周。",
            "parameters": {
                "type": "object",
                "properties": {
                    "fiscal_year": {"type": "string"},
                    "fiscal_period": {"type": "string"},
                    "week_index": {"type": "integer"},
                },
                "required": ["fiscal_year", "fiscal_period", "week_index"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "fiscal_list_weeks_in_natural_month",
            "description": "列出某自然年月中（按财周开始日落入该月）包含的所有财周。",
            "parameters": {
                "type": "object",
                "properties": {
                    "year": {"type": "integer"},
                    "month": {"type": "integer"},
                },
                "required": ["year", "month"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "fiscal_get_nth_week_in_natural_month",
            "description": "自然月中第 N 个财周；week_index=-1 为最后一个。",
            "parameters": {
                "type": "object",
                "properties": {
                    "year": {"type": "integer"},
                    "month": {"type": "integer"},
                    "week_index": {"type": "integer"},
                },
                "required": ["year", "month", "week_index"],
            },
        },
    },
]


def dispatch_fiscal_calendar_tool(
    name: str, arguments: Dict[str, Any], db: Session
) -> Dict[str, Any]:
    """
    根据工具名与参数执行查询，返回可被模型消费的 JSON 字典。
    """
    try:
        if name == "fiscal_get_week":
            return tool_get_fiscal_week(
                db,
                arguments.get("fw_label", ""),
                arguments.get("fiscal_year"),
            )
        if name == "fiscal_get_year_range":
            return tool_get_fiscal_year_range(db, arguments.get("fiscal_year", ""))
        if name == "fiscal_get_period_range":
            return tool_get_fiscal_period_range(
                db,
                arguments.get("fiscal_year", ""),
                arguments.get("fiscal_period", ""),
            )
        if name == "fiscal_list_weeks_in_period":
            return tool_list_weeks_in_fiscal_period(
                db,
                arguments.get("fiscal_year", ""),
                arguments.get("fiscal_period", ""),
            )
        if name == "fiscal_get_nth_week_in_period":
            return tool_get_nth_week_in_fiscal_period(
                db,
                arguments.get("fiscal_year", ""),
                arguments.get("fiscal_period", ""),
                int(arguments.get("week_index", 0)),
            )
        if name == "fiscal_list_weeks_in_natural_month":
            return tool_list_weeks_in_natural_month(
                db,
                int(arguments.get("year", 0)),
                int(arguments.get("month", 0)),
            )
        if name == "fiscal_get_nth_week_in_natural_month":
            return tool_get_natural_month_nth_fiscal_week(
                db,
                int(arguments.get("year", 0)),
                int(arguments.get("month", 0)),
                int(arguments.get("week_index", 0)),
            )
        return {"ok": False, "error": f"未知工具: {name}"}
    except Exception as e:
        logger.exception("fiscal_calendar_tool failed: %s %s", name, arguments)
        return {"ok": False, "error": str(e)}
