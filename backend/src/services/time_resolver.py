"""
TimeResolver 时间语义解析中间件

在 SQL 生成之前，将用户自然语言中的业务时间表达
（财周、财月、财季、财年）解析为数据库中对应的准确字段值。
"""
import re
import logging
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import List, Optional, Tuple

from sqlalchemy.orm import Session
from sqlalchemy import func

from src.models.fiscal_calendar_model import FiscalCalendar

logger = logging.getLogger(__name__)


# ============================================================================
# 数据类定义
# ============================================================================

@dataclass
class TimeExpression:
    """用户输入中识别到的时间表达"""
    raw_text: str           # 原始文本，如 "本财周"
    expr_type: str          # "fw" | "fm" | "fq" | "fy"
    label: Optional[str]    # 解析后的标签，如 "FW22"（相对表达需查表后填充）
    is_relative: bool       # 是否是相对表达（本财周、上财周等）


@dataclass
class DateRange:
    """解析后的日期范围"""
    start_date: str   # "YYYY-MM-DD"
    end_date: str     # "YYYY-MM-DD"
    label: str        # "FW22" 或 "FM3" 等
    expr_type: str    # "fw" | "fm" | "fq" | "fy"


@dataclass
class ResolvedTimeContext:
    """时间解析结果上下文"""
    expressions: List[TimeExpression]    # 识别到的时间表达列表
    date_ranges: List[DateRange]         # 对应的日期范围列表
    rewritten_question: str              # 替换时间表达后的问题（传给模型）
    force_prompt_note: str               # 强制说明，追加到 Prompt 中
    no_data_years: List[int] = field(default_factory=list)  # 明确指定但无数据的年份


# ============================================================================
# 节假日 → 实际公历日期映射（动态查数据库，不再硬编码财周）
# ============================================================================

# 节假日关键词 → 各年实际公历日期
# 格式：{ 关键词: { 自然年: date } }
# 财周由数据库动态查询，不再硬编码
HOLIDAY_CALENDAR_DATES: dict = {
    "春节": {
        2024: date(2024, 2, 10),
        2025: date(2025, 1, 29),
        2026: date(2026, 2, 17),
    },
    "五一": {
        2024: date(2024, 5, 1),
        2025: date(2025, 5, 1),
        2026: date(2026, 5, 1),
    },
    "国庆": {
        2024: date(2024, 10, 1),
        2025: date(2025, 10, 1),
        2026: date(2026, 10, 1),
    },
    "元旦": {
        2024: date(2024, 1, 1),
        2025: date(2025, 1, 1),
        2026: date(2026, 1, 1),
    },
    "中秋": {
        2024: date(2024, 9, 17),
        2025: date(2025, 10, 6),
        2026: date(2026, 9, 25),
    },
}

# 英文关键词 → 中文关键词（统一映射到同一节假日）
HOLIDAY_EN_TO_ZH: dict = {
    "Spring Festival": "春节",
    "Chinese New Year": "春节",
    "Labor Day": "五一",
    "Golden Week": "国庆",
    "National Day": "国庆",
    "Mid-Autumn": "中秋",
    "New Year": "元旦",
}

# 保留旧名称兼容（不再使用，仅作占位）
HOLIDAY_FW_MAPPING: dict = {}


# ============================================================================
# TimeExpressionExtractor：正则提取，不调用 AI
# ============================================================================

class TimeExpressionExtractor:
    """
    从用户问题中提取时间表达，使用正则表达式匹配，不调用 AI。

    支持：
    - 财周直接引用：FW22、FW 22、第22财周
    - 财周相对表达：本财周、上财周、上上财周、下财周
    - 财月：FM3、本财月、上财月、上个财月
    - 财季：FQ1、FQ2、本财季、上财季
    - 财年：FY2026、本财年、上财年
    - 节假日：春节、五一、国庆
    """

    # 财周直接引用：FW22 / FW 22 / 第22财周
    _RE_FW_DIRECT = re.compile(
        r'(?:FW\s*(\d{1,2})|第\s*(\d{1,2})\s*财周)',
        re.IGNORECASE
    )

    # 财周相对表达
    _RE_FW_RELATIVE = re.compile(
        r'(上上财周|上上个财周|上财周|上个财周|本财周|这财周|当前财周|下财周|下个财周)',
    )

    # 财月直接引用：FM3 / FM 3
    _RE_FM_DIRECT = re.compile(
        r'FM\s*(\d{1,2})',
        re.IGNORECASE
    )

    # 财月相对表达
    _RE_FM_RELATIVE = re.compile(
        r'(上上财月|上上个财月|上财月|上个财月|本财月|这财月|当前财月|下财月|下个财月)',
    )

    # 财季直接引用：FQ1 / FQ 1
    _RE_FQ_DIRECT = re.compile(
        r'FQ\s*([1-4])',
        re.IGNORECASE
    )

    # 财季相对表达
    _RE_FQ_RELATIVE = re.compile(
        r'(上财季|上个财季|本财季|这财季|当前财季|下财季|下个财季)',
    )

    # 财年直接引用：FY2026 / FY 2026
    _RE_FY_DIRECT = re.compile(
        r'FY\s*(\d{4})',
        re.IGNORECASE
    )

    # 财年相对表达
    _RE_FY_RELATIVE = re.compile(
        r'(上财年|上个财年|本财年|这财年|当前财年|下财年|下个财年)',
    )

    # 节假日关键词（中英文）
    _RE_HOLIDAY = re.compile(
        r'(春节|五一|国庆|元旦|中秋'
        r'|Spring\s+Festival|Chinese\s+New\s+Year'
        r'|Labor\s+Day|Golden\s+Week|National\s+Day'
        r'|Mid-Autumn|New\s+Year)',
        re.IGNORECASE,
    )

    # 自然月第N周：匹配 "2026年1月第二周"、"2026年12月第1周"、"January week 2 of 2026" 等
    # 中文：2026年1月第二周 / 2026年1月第2周 / 2026 年 1 月第二周
    _RE_MONTH_WEEK_ZH = re.compile(
        r'(20\d{2})\s*年\s*(\d{1,2})\s*月\s*第\s*([一二三四五六1-6])\s*周',
    )
    # 英文：January week 2 of 2026 / week 2 of January 2026 / 2026 January week 2
    _RE_MONTH_WEEK_EN = re.compile(
        r'(?:'
        r'(January|February|March|April|May|June|July|August|September|October|November|December)'
        r'\s+week\s+(\d)\s+(?:of\s+)?(20\d{2})'
        r'|'
        r'week\s+(\d)\s+of\s+'
        r'(January|February|March|April|May|June|July|August|September|October|November|December)'
        r'\s+(20\d{2})'
        r'|'
        r'(20\d{2})\s+'
        r'(January|February|March|April|May|June|July|August|September|October|November|December)'
        r'\s+week\s+(\d)'
        r')',
        re.IGNORECASE,
    )

    def extract(self, text: str) -> List[TimeExpression]:
        """
        从文本中提取所有时间表达。

        Args:
            text: 用户输入的问题字符串

        Returns:
            识别到的 TimeExpression 列表，未识别到则返回空列表
        """
        if not text:
            return []

        results: List[TimeExpression] = []
        # 记录已匹配的文本区间，避免重复
        matched_spans: List[Tuple[int, int]] = []

        def _add(raw: str, expr_type: str, label: Optional[str], is_relative: bool, span: Tuple[int, int]):
            # 检查是否与已有匹配重叠
            for s, e in matched_spans:
                if not (span[1] <= s or span[0] >= e):
                    return  # 重叠，跳过
            matched_spans.append(span)
            results.append(TimeExpression(
                raw_text=raw,
                expr_type=expr_type,
                label=label,
                is_relative=is_relative,
            ))

        # 1. 财周直接引用
        for m in self._RE_FW_DIRECT.finditer(text):
            num = m.group(1) or m.group(2)
            label = f"FW{int(num):02d}"
            _add(m.group(0), "fw", label, False, m.span())

        # 2. 财周相对表达
        for m in self._RE_FW_RELATIVE.finditer(text):
            _add(m.group(0), "fw", None, True, m.span())

        # 3. 财月直接引用
        for m in self._RE_FM_DIRECT.finditer(text):
            label = f"FM{int(m.group(1))}"
            _add(m.group(0), "fm", label, False, m.span())

        # 4. 财月相对表达
        for m in self._RE_FM_RELATIVE.finditer(text):
            _add(m.group(0), "fm", None, True, m.span())

        # 5. 财季直接引用
        for m in self._RE_FQ_DIRECT.finditer(text):
            label = f"FQ{m.group(1)}"
            _add(m.group(0), "fq", label, False, m.span())

        # 6. 财季相对表达
        for m in self._RE_FQ_RELATIVE.finditer(text):
            _add(m.group(0), "fq", None, True, m.span())

        # 7. 财年直接引用
        for m in self._RE_FY_DIRECT.finditer(text):
            label = f"FY{m.group(1)}"
            _add(m.group(0), "fy", label, False, m.span())

        # 8. 财年相对表达
        for m in self._RE_FY_RELATIVE.finditer(text):
            _add(m.group(0), "fy", None, True, m.span())

        # 9. 节假日关键词
        for m in self._RE_HOLIDAY.finditer(text):
            keyword = m.group(0)
            # 统一英文关键词到中文
            zh_keyword = HOLIDAY_EN_TO_ZH.get(keyword, keyword)
            # label 暂存节假日中文名，年份在 TimeResolver 中根据问题上下文确定
            _add(keyword, "holiday", zh_keyword, False, m.span())

        # 10. 自然月第N周（如 "2026年1月第二周"）
        _ZH_NUM = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6}
        _EN_MONTH = {
            "january": 1, "february": 2, "march": 3, "april": 4,
            "may": 5, "june": 6, "july": 7, "august": 8,
            "september": 9, "october": 10, "november": 11, "december": 12,
        }
        for m in self._RE_MONTH_WEEK_ZH.finditer(text):
            year = int(m.group(1))
            month = int(m.group(2))
            week_raw = m.group(3)
            week_n = _ZH_NUM.get(week_raw, None) or int(week_raw)
            # label 格式: "MW|年|月|第N周"，在 _resolve_label 中查数据库
            label = f"MW|{year}|{month}|{week_n}"
            _add(m.group(0), "month_week", label, False, m.span())

        for m in self._RE_MONTH_WEEK_EN.finditer(text):
            # 三种英文格式，取非 None 的分组
            if m.group(1):  # January week 2 2026
                month_name, week_n, year = m.group(1), int(m.group(2)), int(m.group(3))
            elif m.group(4):  # week 2 of January 2026
                week_n, month_name, year = int(m.group(4)), m.group(5), int(m.group(6))
            else:  # 2026 January week 2
                year, month_name, week_n = int(m.group(7)), m.group(8), int(m.group(9))
            month = _EN_MONTH.get(month_name.lower(), 0)
            if month > 0:
                label = f"MW|{year}|{month}|{week_n}"
                _add(m.group(0), "month_week", label, False, m.span())

        return results


# ============================================================================
# FiscalCalendarRepository：数据库查询层
# ============================================================================

class FiscalCalendarRepository:
    """
    财务日历数据库查询层。

    所有查询均基于 SQLAlchemy Session，不持有长连接。
    """

    def find_by_fw_label(self, db: Session, fw_label: str, fiscal_year: Optional[str] = None) -> Optional[FiscalCalendar]:
        """
        通过财周标签查找记录。

        Args:
            db: SQLAlchemy 会话
            fw_label: 财周标签，如 "FW22"
            fiscal_year: 财年标签，如 "FY2026"；为 None 时取 fw_start_date 最新的记录

        Returns:
            FiscalCalendar 记录，不存在则返回 None
        """
        q = db.query(FiscalCalendar).filter(FiscalCalendar.fw_label == fw_label)
        if fiscal_year:
            return q.filter(FiscalCalendar.fiscal_year == fiscal_year).first()
        # 未指定财年时，返回日期最新的那条（即最近财年）
        return q.order_by(FiscalCalendar.fw_start_date.desc()).first()

    def find_range_by_fiscal_month(
        self, db: Session, fm_label: str, fiscal_year: Optional[str] = None
    ) -> Optional[DateRange]:
        """
        查询财月对应的合并日期范围（min fw_start_date ~ max fw_end_date）。

        Args:
            db: SQLAlchemy 会话
            fm_label: 财月标签，如 "FM3"
            fiscal_year: 财年标签，如 "FY2026"；为空时会跨财年聚合

        Returns:
            DateRange，不存在则返回 None
        """
        q = (
            db.query(
                func.min(FiscalCalendar.fw_start_date).label("start_date"),
                func.max(FiscalCalendar.fw_end_date).label("end_date"),
            )
            .filter(FiscalCalendar.fiscal_month == fm_label)
        )
        if fiscal_year:
            q = q.filter(FiscalCalendar.fiscal_year == fiscal_year)
        row = q.first()
        if row is None or row.start_date is None:
            return None
        return DateRange(
            start_date=_to_str(row.start_date),
            end_date=_to_str(row.end_date),
            label=f"{fm_label}({fiscal_year})" if fiscal_year else fm_label,
            expr_type="fm",
        )

    def find_range_by_fiscal_quarter(self, db: Session, fq_label: str) -> Optional[DateRange]:
        """
        查询财季对应的合并日期范围。

        Args:
            db: SQLAlchemy 会话
            fq_label: 财季标签，如 "FQ1"

        Returns:
            DateRange，不存在则返回 None
        """
        row = (
            db.query(
                func.min(FiscalCalendar.fw_start_date).label("start_date"),
                func.max(FiscalCalendar.fw_end_date).label("end_date"),
            )
            .filter(FiscalCalendar.fiscal_quarter == fq_label)
            .first()
        )
        if row is None or row.start_date is None:
            return None
        return DateRange(
            start_date=_to_str(row.start_date),
            end_date=_to_str(row.end_date),
            label=fq_label,
            expr_type="fq",
        )

    def find_range_by_fiscal_year(self, db: Session, fy_label: str) -> Optional[DateRange]:
        """
        查询财年对应的合并日期范围。

        Args:
            db: SQLAlchemy 会话
            fy_label: 财年标签，如 "FY2026"

        Returns:
            DateRange，不存在则返回 None
        """
        row = (
            db.query(
                func.min(FiscalCalendar.fw_start_date).label("start_date"),
                func.max(FiscalCalendar.fw_end_date).label("end_date"),
            )
            .filter(FiscalCalendar.fiscal_year == fy_label)
            .first()
        )
        if row is None or row.start_date is None:
            return None
        return DateRange(
            start_date=_to_str(row.start_date),
            end_date=_to_str(row.end_date),
            label=fy_label,
            expr_type="fy",
        )

    def find_current_fw(self, db: Session, today: date) -> Optional[FiscalCalendar]:
        """
        查询指定日期所在的财周记录。

        Args:
            db: SQLAlchemy 会话
            today: 查询日期

        Returns:
            FiscalCalendar 记录，不存在则返回 None
        """
        return (
            db.query(FiscalCalendar)
            .filter(
                FiscalCalendar.fw_start_date <= today,
                FiscalCalendar.fw_end_date >= today,
            )
            .first()
        )

    def find_fw_by_date(self, db: Session, target_date: date) -> Optional[FiscalCalendar]:
        """
        查询指定公历日期所在的财周记录。

        Args:
            db: SQLAlchemy 会话
            target_date: 目标日期

        Returns:
            FiscalCalendar 记录，不存在则返回 None
        """
        return (
            db.query(FiscalCalendar)
            .filter(
                FiscalCalendar.fw_start_date <= target_date,
                FiscalCalendar.fw_end_date >= target_date,
            )
            .first()
        )

    def find_fw_by_offset(self, db: Session, base_fw_label: str, offset: int) -> Optional[FiscalCalendar]:
        """
        基于基准财周标签和偏移量查找目标财周。

        通过 fw_start_date 排序后按偏移量定位。

        Args:
            db: SQLAlchemy 会话
            base_fw_label: 基准财周标签，如 "FW22"
            offset: 偏移量，-1 表示上一财周，+1 表示下一财周

        Returns:
            FiscalCalendar 记录，不存在则返回 None
        """
        base = self.find_by_fw_label(db, base_fw_label)
        if base is None:
            return None

        if offset == 0:
            return base

        if offset < 0:
            # 查找 fw_start_date 小于 base 的，按 fw_start_date 降序取第 |offset| 条
            rows = (
                db.query(FiscalCalendar)
                .filter(FiscalCalendar.fw_start_date < base.fw_start_date)
                .order_by(FiscalCalendar.fw_start_date.desc())
                .limit(abs(offset))
                .all()
            )
            if len(rows) < abs(offset):
                return None
            return rows[-1]
        else:
            # 查找 fw_start_date 大于 base 的，按 fw_start_date 升序取第 offset 条
            rows = (
                db.query(FiscalCalendar)
                .filter(FiscalCalendar.fw_start_date > base.fw_start_date)
                .order_by(FiscalCalendar.fw_start_date.asc())
                .limit(offset)
                .all()
            )
            if len(rows) < offset:
                return None
            return rows[-1]

    def find_fiscal_weeks_by_natural_month(
        self, db: Session, year: int, month: int
    ) -> List[FiscalCalendar]:
        """
        查询指定自然年月中包含的所有财周，按 fw_start_date 升序排列。

        判断逻辑：财周与该自然月有日期重叠（允许财周起始日在上月）。

        Args:
            db: SQLAlchemy 会话
            year: 自然年，如 2026
            month: 自然月，如 1（一月）

        Returns:
            该月包含的财周列表（按开始日期升序），不存在则返回空列表
        """
        import calendar
        from datetime import date

        month_start = date(year, month, 1)
        month_end = date(year, month, calendar.monthrange(year, month)[1])
        rows = (
            db.query(FiscalCalendar)
            .filter(
                FiscalCalendar.fw_start_date <= month_end,
                FiscalCalendar.fw_end_date >= month_start,
            )
            .order_by(FiscalCalendar.fw_start_date.asc())
            .all()
        )
        return rows

    def find_fiscal_weeks_by_month_in_fiscal_year(
        self, db: Session, fiscal_year: str, month: int
    ) -> List[FiscalCalendar]:
        """
        查询某财年中与指定自然月（1-12）有重叠的财周，按 fw_start_date 升序。
        """
        from sqlalchemy import extract as sa_extract

        rows = (
            db.query(FiscalCalendar)
            .filter(
                FiscalCalendar.fiscal_year == fiscal_year,
                (
                    (sa_extract("month", FiscalCalendar.fw_start_date) == month)
                    | (sa_extract("month", FiscalCalendar.fw_end_date) == month)
                ),
            )
            .order_by(FiscalCalendar.fw_start_date.asc())
            .all()
        )
        return rows


def _to_str(d) -> str:
    """将 date/datetime/str 统一转为 YYYY-MM-DD 字符串"""
    if d is None:
        return ""
    if isinstance(d, str):
        return d[:10]
    return d.strftime("%Y-%m-%d")


# ============================================================================
# TimeResolver：主服务
# ============================================================================

# 相对时间表达 → 偏移量映射
_FW_RELATIVE_OFFSET = {
    "上上财周": -2, "上上个财周": -2,
    "上财周": -1, "上个财周": -1,
    "本财周": 0, "这财周": 0, "当前财周": 0,
    "下财周": 1, "下个财周": 1,
}

_FM_RELATIVE_OFFSET = {
    "上上财月": -2, "上上个财月": -2,
    "上财月": -1, "上个财月": -1,
    "本财月": 0, "这财月": 0, "当前财月": 0,
    "下财月": 1, "下个财月": 1,
}

_FQ_RELATIVE_OFFSET = {
    "上财季": -1, "上个财季": -1,
    "本财季": 0, "这财季": 0, "当前财季": 0,
    "下财季": 1, "下个财季": 1,
}

_FY_RELATIVE_OFFSET = {
    "上财年": -1, "上个财年": -1,
    "本财年": 0, "这财年": 0, "当前财年": 0,
    "下财年": 1, "下个财年": 1,
}


class TimeResolver:
    """
    时间语义解析主服务。

    职责：
    1. 提取用户问题中的时间表达
    2. 查询财务日历表获取对应日期范围
    3. 重写用户问题，将时间表达替换为精确日期描述
    4. 生成 force_prompt_note 追加到 SQL 生成 Prompt

    失败时返回 None，不抛出异常，不阻断后续流程。
    """

    def __init__(self):
        self._extractor = TimeExpressionExtractor()
        self._repo = FiscalCalendarRepository()

    def _has_explicit_fy_fw(self, expressions: List[TimeExpression]) -> bool:
        """用户是否明确给出了 FY + FW（非相对表达）。"""
        has_fw = any(
            e.expr_type == "fw" and (not e.is_relative) and bool(e.label)
            for e in expressions
        )
        has_fy = any(
            e.expr_type == "fy" and (not e.is_relative) and bool(e.label)
            for e in expressions
        )
        return has_fw and has_fy

    async def resolve(self, user_question: str, db: Session) -> Optional[ResolvedTimeContext]:
        """
        解析用户问题中的时间表达。

        Args:
            user_question: 用户原始问题
            db: SQLAlchemy 会话

        Returns:
            ResolvedTimeContext，未识别到时间表达或解析失败时返回 None
        """
        try:
            expressions = self._extractor.extract(user_question)
            if not expressions:
                return None

            # 从问题中提取所有年份（用于节假日解析），如 "2025 and 2026 Spring Festival" → [2025, 2026]
            question_years = self._extract_years_from_question(user_question)

            # 解析相对时间表达的 label，节假日按年份展开
            resolved_expressions = []
            for expr in expressions:
                if expr.expr_type == "holiday":
                    if len(question_years) > 1:
                        # 多年份：为每个年份各生成一个独立的 TimeExpression
                        for year in question_years:
                            resolved = self._resolve_holiday_label(expr, year, db)
                            if resolved is not None:
                                resolved_expressions.append(resolved)
                    else:
                        # 单年份或无年份：原有逻辑
                        single_year = question_years[0] if question_years else None
                        resolved = self._resolve_holiday_label(expr, single_year, db)
                        if resolved is not None:
                            resolved_expressions.append(resolved)
                        else:
                            resolved_expressions.append(expr)
                else:
                    resolved = self._resolve_label(expr, db)
                    if resolved is not None:
                        resolved_expressions.append(resolved)
                    else:
                        resolved_expressions.append(expr)

            # 兼容表达："FW01 2025" / "FM01 2026"（无 FY 前缀）
            # 规则：当问题中存在唯一自然年，且未显式出现 FY 时，
            # 将 FW/FM 解析绑定到该财年，避免默认取最新年份导致口径漂移。
            has_explicit_fy = any(e.expr_type == "fy" and e.label for e in resolved_expressions)
            if (not has_explicit_fy) and len(question_years) == 1:
                inferred_fy = f"FY{question_years[0]}"
                for expr in resolved_expressions:
                    if (
                        expr.expr_type in ("fw", "fm")
                        and expr.label
                        and (not expr.is_relative)
                        and "|" not in expr.label
                    ):
                        expr.label = f"{expr.label}|{inferred_fy}"
                        logger.info(
                            f"⏰ TimeResolver: 检测到 '{expr.expr_type.upper()} + 年份' 表达，已绑定财年: {expr.label}"
                        )

            # 查询日期范围
            date_ranges: List[DateRange] = []
            no_data_years: List[int] = []
            for expr in resolved_expressions:
                if expr.label is None:
                    logger.warning(f"⏰ TimeResolver: 无法解析时间表达 '{expr.raw_text}'，跳过")
                    continue
                # 收集无数据年份标记
                if expr.expr_type == "holiday" and expr.label.startswith("NO_DATA|"):
                    try:
                        no_data_years.append(int(expr.label.split("|")[1]))
                    except (ValueError, IndexError):
                        pass
                    continue
                dr = self._lookup_date_range(expr, db)
                if dr is not None:
                    # month_week 类型解析后，将 expr.label 同步为实际财周标签（如 FW16），
                    # 以便 rewrite_question 能正确匹配 label_map
                    if expr.expr_type == "month_week" and dr.label != expr.label:
                        expr.label = dr.label
                    date_ranges.append(dr)
                else:
                    logger.warning(
                        f"⏰ TimeResolver: 时间标签 '{expr.label}' 在财务日历中不存在，跳过"
                    )

            # 如果有无数据年份但没有有效日期范围 → 返回"无数据"上下文，阻止 LLM 幻觉
            if no_data_years and not date_ranges:
                years_str = "、".join(str(y) for y in no_data_years)
                force_note = (
                    f"【数据范围限制 - 最高优先级指令】\n"
                    f"用户查询的时间段（{years_str}年）在数据库中不存在对应数据。\n"
                    f"⚠️ 必须执行：生成 SQL 时使用 WHERE 1=0 返回空结果集，或直接告知用户该时间段无数据。\n"
                    f"禁止使用其他年份的数据替代，禁止推断或估算。"
                )
                return ResolvedTimeContext(
                    expressions=resolved_expressions,
                    date_ranges=[],
                    rewritten_question=user_question,
                    force_prompt_note=force_note,
                    no_data_years=no_data_years,
                )

            if not date_ranges:
                return None

            # 口径优先级：
            # - 用户明确给出 FY + FW 时，优先按财务字段过滤（FY_N/FW_N），不强制改写为日期范围。
            # - 其他时间表达仍按日期范围注入。
            if self._has_explicit_fy_fw(resolved_expressions):
                rewritten = user_question
                fw_labels = sorted({
                    e.label for e in resolved_expressions
                    if e.expr_type == "fw" and e.label
                })
                fy_labels = sorted({
                    e.label for e in resolved_expressions
                    if e.expr_type == "fy" and e.label
                })
                force_note = (
                    "【财务周口径优先 - 最高优先级指令】\n"
                    "用户已明确提供 FY + FW。SQL 必须优先使用财务字段过滤：FY_N / FW_N。\n"
                    f"检测到 FY: {', '.join(fy_labels)}；FW: {', '.join(fw_labels)}。\n"
                    "⚠️ 禁止将该查询强制改写为仅使用 FW_START_DATE/FW_END_DATE 的自然日期过滤。"
                )
            else:
                # 重写问题
                rewritten = self.rewrite_question(user_question, resolved_expressions, date_ranges)
                force_note = self._build_force_note(date_ranges)

            return ResolvedTimeContext(
                expressions=resolved_expressions,
                date_ranges=date_ranges,
                rewritten_question=rewritten,
                force_prompt_note=force_note,
                no_data_years=no_data_years,
            )

        except Exception as e:
            logger.error(f"⏰ TimeResolver: 解析异常 {e}", exc_info=True)
            return None

    def rewrite_question(
        self,
        user_question: str,
        expressions: List[TimeExpression],
        date_ranges: List[DateRange],
    ) -> str:
        """
        将用户问题中的时间表达替换为精确日期描述。

        单年份：  "本财周" → "FW22（2026-05-25 到 2026-05-31）"
        多年份节假日："Spring Festival" →
            "Spring Festival 2025（FW05, 2025-01-27 到 2025-02-02）和
             Spring Festival 2026（FW21, 2026-02-16 到 2026-02-22）"

        Args:
            user_question: 原始问题
            expressions: 已解析的时间表达列表
            date_ranges: 对应的日期范围列表

        Returns:
            替换后的问题字符串
        """
        # 建立 label → DateRange 映射
        label_map = {dr.label: dr for dr in date_ranges}

        # 按 raw_text 分组，收集同一原始文本对应的所有 DateRange
        from collections import defaultdict
        raw_to_ranges: dict = defaultdict(list)
        for expr in expressions:
            if expr.label and expr.label in label_map:
                raw_to_ranges[expr.raw_text].append(label_map[expr.label])

        result = user_question
        replaced_raws: set = set()

        for expr in expressions:
            raw = expr.raw_text
            if raw in replaced_raws:
                continue
            ranges = raw_to_ranges.get(raw)
            if not ranges:
                continue

            if len(ranges) == 1:
                # 单个日期范围：直接替换
                dr = ranges[0]
                replacement = f"{dr.label}（{dr.start_date} 到 {dr.end_date}）"
            else:
                # 多个日期范围（多年份节假日）：生成联合描述
                parts = []
                for dr in ranges:
                    # 从 label 中提取财年，如 "FW05(FY2025)" → "FY2025" → "2025"
                    fy_str = ""
                    if "(" in dr.label and "FY" in dr.label:
                        fy_part = dr.label.split("(")[-1].rstrip(")")
                        fy_str = " " + fy_part[2:]  # "FY2025" → " 2025"
                    fw_part = dr.label.split("(")[0]  # "FW05"
                    parts.append(
                        f"{raw}{fy_str}（{fw_part}, {dr.start_date} 到 {dr.end_date}）"
                    )
                replacement = " 和 ".join(parts)

            result = result.replace(raw, replacement, 1)
            replaced_raws.add(raw)

        return result

    def _get_current_fw_label(self, db: Session) -> Optional[str]:
        """基于系统当前日期查询财务日历，获取当前财周标签"""
        today = datetime.now().date()
        record = self._repo.find_current_fw(db, today)
        return record.fw_label if record else None

    def _resolve_label(self, expr: TimeExpression, db: Session) -> Optional[TimeExpression]:
        """
        将相对时间表达解析为具体标签。

        对于非相对表达，直接返回原始 expr。
        对于相对表达，查询数据库计算目标标签。
        """
        if not expr.is_relative:
            return expr

        raw = expr.raw_text

        if expr.expr_type == "fw":
            offset = _FW_RELATIVE_OFFSET.get(raw, 0)
            current_label = self._get_current_fw_label(db)
            if current_label is None:
                return expr  # 财务日历为空，无法解析
            target = self._repo.find_fw_by_offset(db, current_label, offset)
            if target:
                return TimeExpression(
                    raw_text=raw,
                    expr_type="fw",
                    label=target.fw_label,
                    is_relative=True,
                )
            return expr

        if expr.expr_type == "fm":
            offset = _FM_RELATIVE_OFFSET.get(raw, 0)
            current_label = self._get_current_fw_label(db)
            if current_label is None:
                return expr
            current_fw = self._repo.find_by_fw_label(db, current_label)
            if current_fw is None:
                return expr
            current_fm = current_fw.fiscal_month
            # 获取同财年内所有财月，按顺序排列
            target_fm = self._offset_fm_label(db, current_fm, current_fw.fiscal_year, offset)
            if target_fm:
                return TimeExpression(
                    raw_text=raw,
                    expr_type="fm",
                    label=target_fm,
                    is_relative=True,
                )
            return expr

        if expr.expr_type == "fq":
            offset = _FQ_RELATIVE_OFFSET.get(raw, 0)
            current_label = self._get_current_fw_label(db)
            if current_label is None:
                return expr
            current_fw = self._repo.find_by_fw_label(db, current_label)
            if current_fw is None:
                return expr
            current_fq = current_fw.fiscal_quarter
            target_fq = self._offset_fq_label(current_fq, offset)
            if target_fq:
                return TimeExpression(
                    raw_text=raw,
                    expr_type="fq",
                    label=target_fq,
                    is_relative=True,
                )
            return expr

        if expr.expr_type == "fy":
            offset = _FY_RELATIVE_OFFSET.get(raw, 0)
            current_label = self._get_current_fw_label(db)
            if current_label is None:
                return expr
            current_fw = self._repo.find_by_fw_label(db, current_label)
            if current_fw is None:
                return expr
            current_fy = current_fw.fiscal_year  # e.g. "FY2026"
            try:
                year_num = int(current_fy[2:]) + offset
                target_fy = f"FY{year_num}"
                return TimeExpression(
                    raw_text=raw,
                    expr_type="fy",
                    label=target_fy,
                    is_relative=True,
                )
            except (ValueError, IndexError):
                return expr

        return expr

    def _offset_fm_label(
        self, db: Session, current_fm: str, current_fy: str, offset: int
    ) -> Optional[str]:
        """计算偏移后的财月标签（在同财年内）"""
        # 获取当前财年内所有财月，按 fw_start_date 排序
        rows = (
            db.query(FiscalCalendar.fiscal_month)
            .filter(FiscalCalendar.fiscal_year == current_fy)
            .order_by(FiscalCalendar.fw_start_date.asc())
            .distinct()
            .all()
        )
        months = [r[0] for r in rows]
        if current_fm not in months:
            return None
        idx = months.index(current_fm) + offset
        if 0 <= idx < len(months):
            return months[idx]
        return None

    def _offset_fq_label(self, current_fq: str, offset: int) -> Optional[str]:
        """计算偏移后的财季标签（FQ1~FQ4）"""
        try:
            num = int(current_fq[2:]) + offset
            if 1 <= num <= 4:
                return f"FQ{num}"
        except (ValueError, IndexError):
            pass
        return None

    def _lookup_date_range(self, expr: TimeExpression, db: Session) -> Optional[DateRange]:
        """根据时间表达类型查询对应的日期范围"""
        if expr.label is None:
            return None

        if expr.expr_type == "fw":
            fw_label = expr.label
            fiscal_year = None
            if "|" in expr.label:
                fw_label, fiscal_year = expr.label.split("|", 1)
            record = self._repo.find_by_fw_label(db, fw_label, fiscal_year)
            if record:
                return DateRange(
                    start_date=_to_str(record.fw_start_date),
                    end_date=_to_str(record.fw_end_date),
                    label=record.fw_label,
                    expr_type="fw",
                )
            return None

        if expr.expr_type == "fm":
            fm_label = expr.label
            fiscal_year = None
            if "|" in expr.label:
                fm_label, fiscal_year = expr.label.split("|", 1)
            return self._repo.find_range_by_fiscal_month(db, fm_label, fiscal_year)

        if expr.expr_type == "fq":
            return self._repo.find_range_by_fiscal_quarter(db, expr.label)

        if expr.expr_type == "fy":
            return self._repo.find_range_by_fiscal_year(db, expr.label)

        # month_week 类型：label 格式 "MW|年|月|第N周"
        if expr.expr_type == "month_week":
            parts = expr.label.split("|")
            if len(parts) != 4:
                return None
            try:
                year, month, week_n = int(parts[1]), int(parts[2]), int(parts[3])
            except ValueError:
                return None
            fiscal_weeks = self._repo.find_fiscal_weeks_by_natural_month(db, year, month)
            if not fiscal_weeks:
                logger.warning(f"⏰ TimeResolver: {year}年{month}月在财务日历中无财周记录")
                return None
            if week_n < 1 or week_n > len(fiscal_weeks):
                logger.warning(
                    f"⏰ TimeResolver: {year}年{month}月共有 {len(fiscal_weeks)} 个财周，"
                    f"但请求第 {week_n} 周，超出范围"
                )
                return None
            target_fw = fiscal_weeks[week_n - 1]  # 0-indexed
            logger.info(
                f"⏰ TimeResolver: {year}年{month}月第{week_n}周 → "
                f"{target_fw.fw_label}（{target_fw.fw_start_date} 到 {target_fw.fw_end_date}）"
            )
            return DateRange(
                start_date=_to_str(target_fw.fw_start_date),
                end_date=_to_str(target_fw.fw_end_date),
                label=target_fw.fw_label,
                expr_type="fw",
            )

        # holiday 类型：label 已在 _resolve_holiday_label 中转为 "FW21|FY2026" 格式
        if expr.expr_type == "holiday":
            if expr.label and expr.label.startswith("NO_DATA|"):
                # 无数据年份标记，直接返回 None（调用方会收集到 no_data_years）
                return None
            if "|" in (expr.label or ""):
                fw_label, fy_label = expr.label.split("|", 1)
                record = self._repo.find_by_fw_label(db, fw_label, fy_label)
                if record:
                    return DateRange(
                        start_date=_to_str(record.fw_start_date),
                        end_date=_to_str(record.fw_end_date),
                        label=f"{fw_label}({fy_label})",
                        expr_type="fw",
                    )
            return None

        return None

    def _extract_years_from_question(self, text: str) -> List[int]:
        """
        从问题文本中提取所有自然年份数字，去重升序。
        例："2025 and 2026 Spring Festival" → [2025, 2026]
        未找到则返回空列表（调用方使用当前财年）
        """
        years: set = set()
        for m in re.finditer(r'\b(20\d{2})\b', text):
            years.add(int(m.group(1)))
        # 兼容中文年份格式，如 "2024年"
        for m in re.finditer(r'(20\d{2})年', text):
            years.add(int(m.group(1)))
        return sorted(years)

    def _extract_year_from_question(self, text: str) -> Optional[int]:
        """
        从问题文本中提取第一个自然年份数字（向后兼容）。
        例："2025 Spring Festival" → 2025，"2026年春节" → 2026
        未找到则返回 None
        """
        years = self._extract_years_from_question(text)
        return years[0] if years else None

    def _resolve_holiday_label(
        self, expr: TimeExpression, question_year: Optional[int], db: Session
    ) -> TimeExpression:
        """
        将节假日表达解析为具体财周标签。

        策略：
        1. 从问题中提取年份（如 2025）
        2. 在 HOLIDAY_CALENDAR_DATES 中查找该节假日该年的公历日期
        3. 查数据库找包含该日期的财周
        4. 将 label 设为 "FW21|FY2026" 格式供 _lookup_date_range 使用

        Args:
            expr: 节假日时间表达（label 为中文节假日名）
            question_year: 从问题中提取的年份，None 时用当前年
            db: SQLAlchemy 会话
        """
        zh_name = expr.label  # 中文节假日名，如 "春节"
        if zh_name not in HOLIDAY_CALENDAR_DATES:
            logger.warning(f"⏰ TimeResolver: 节假日 '{zh_name}' 不在映射表中")
            return expr

        year_dates = HOLIDAY_CALENDAR_DATES[zh_name]

        # 确定目标年份：优先用问题中的年份，否则用当前自然年
        if question_year and question_year in year_dates:
            target_year = question_year
        elif question_year and question_year not in year_dates:
            # 明确指定了年份但没有数据 → 用特殊 label 标记，不回退
            logger.warning(
                f"⏰ TimeResolver: 节假日 '{zh_name}' 没有 {question_year} 年的数据，标记为无数据"
            )
            return TimeExpression(
                raw_text=expr.raw_text,
                expr_type="holiday",
                label=f"NO_DATA|{question_year}",  # 特殊标记：无数据年份
                is_relative=False,
            )
        else:
            # 未指定年份：回退到最近有数据的年份
            current_year = datetime.now().year
            if current_year in year_dates:
                target_year = current_year
            else:
                target_year = max(year_dates.keys())

        holiday_date = year_dates[target_year]
        record = self._repo.find_fw_by_date(db, holiday_date)
        if record is None:
            logger.warning(
                f"⏰ TimeResolver: 节假日 '{zh_name}' {target_year}年 "
                f"({holiday_date}) 在财务日历中找不到对应财周"
            )
            return expr

        logger.info(
            f"⏰ TimeResolver: 节假日 '{zh_name}' {target_year}年 → "
            f"{record.fw_label} ({record.fiscal_year}) "
            f"{record.fw_start_date}~{record.fw_end_date}"
        )
        return TimeExpression(
            raw_text=expr.raw_text,
            expr_type="holiday",
            label=f"{record.fw_label}|{record.fiscal_year}",
            is_relative=False,
        )

    def _build_force_note(self, date_ranges: List[DateRange]) -> str:
        """构建追加到 Prompt 的强制说明。多个日期范围时额外追加对比 SQL 建议。"""
        lines = [
            "【时间已解析 - 最高优先级指令】",
            "以下时间表达已由后端财务日历数据库精确查询得出，SQL 中必须使用括号内的日期。",
            "⚠️ 此指令覆盖所有其他规则，包括「农历/节假日日期幻觉防止规则」。",
            "原因：日期已由系统从数据库查询，不是模型推算，无需依赖知识库事件数据。",
            "禁止使用 WHERE 1=0 或返回空结果，必须使用下方日期范围生成 SQL：",
        ]
        for dr in date_ranges:
            lines.append(f"- {dr.label}：{dr.start_date} 到 {dr.end_date}")

        # 多个日期范围时，追加对比 SQL 建议
        if len(date_ranges) > 1:
            lines.append("")
            lines.append("本次查询包含多个时间段，需要生成对比 SQL，建议使用以下结构之一：")
            lines.append("")
            lines.append("1. CASE WHEN 结构（单次查询，按时间段分列）：")
            lines.append("   SELECT <分组字段>,")
            # 为每个日期范围生成一列
            for dr in date_ranges:
                col_name = dr.label.replace("(", "_").replace(")", "").replace("|", "_")
                lines.append(
                    f"     SUM(CASE WHEN <日期字段> BETWEEN '{dr.start_date}' AND '{dr.end_date}' THEN <数值字段> END) AS {col_name},"
                )
            lines.append("   FROM <表名>")
            # 整体 WHERE 覆盖所有时间段
            overall_start = min(dr.start_date for dr in date_ranges)
            overall_end = max(dr.end_date for dr in date_ranges)
            lines.append(f"   WHERE <日期字段> BETWEEN '{overall_start}' AND '{overall_end}'")
            lines.append("   GROUP BY <分组字段>")
            lines.append("")
            lines.append("2. UNION ALL 结构（多次查询合并）：")
            for i, dr in enumerate(date_ranges):
                col_name = dr.label.replace("(", "_").replace(")", "").replace("|", "_")
                union_kw = "   SELECT" if i == 0 else "   UNION ALL\n   SELECT"
                lines.append(
                    f"{union_kw} '{col_name}' AS 时间段, <分组字段>, SUM(<数值字段>) FROM <表名>"
                )
                lines.append(
                    f"   WHERE <日期字段> BETWEEN '{dr.start_date}' AND '{dr.end_date}' GROUP BY <分组字段>"
                )

        return "\n".join(lines)
