"""
TimeResolver 属性测试

Feature: time-resolver

使用 Hypothesis 进行基于属性的测试，覆盖以下属性：
- Property 1: fw_label 查询 Round-Trip
- Property 2: 日期范围合法性
- Property 3: 财月/财季/财年范围包含性
- Property 4: 空输入安全性
- Property 5: 不存在标签安全性
"""

import asyncio
import os
import sys
import uuid
from datetime import date, timedelta
from typing import List

import pytest
from hypothesis import given, settings, strategies as st, HealthCheck
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# 确保 src 在路径中
src_path = os.path.join(os.path.dirname(__file__), "..", "..", "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from src.models.base import Base
from src.models.fiscal_calendar_model import FiscalCalendar
from src.services.time_resolver import (
    DateRange,
    FiscalCalendarRepository,
    TimeExpressionExtractor,
    TimeResolver,
)

# ============================================================================
# 测试数据库 fixture
# ============================================================================

TEST_DB_URL = "sqlite:///file::memory:?cache=shared&uri=true"


def make_engine():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)
    return engine


def make_session(engine):
    Session = sessionmaker(bind=engine)
    return Session()


# ============================================================================
# 辅助函数
# ============================================================================

def _make_fw_record(
    fw_label: str,
    fw_start_date: date,
    fw_end_date: date,
    fiscal_month: str = "FM1",
    fiscal_quarter: str = "FQ1",
    fiscal_year: str = "FY2026",
    natural_year: int = 2026,
) -> FiscalCalendar:
    return FiscalCalendar(
        id=str(uuid.uuid4()),
        fw_label=fw_label,
        fw_start_date=fw_start_date,
        fw_end_date=fw_end_date,
        fiscal_month=fiscal_month,
        fiscal_quarter=fiscal_quarter,
        fiscal_year=fiscal_year,
        natural_year=natural_year,
    )


def _insert_records(db, records: List[FiscalCalendar]):
    for r in records:
        db.add(r)
    db.commit()


# ============================================================================
# Property 4: 空输入安全性
# Feature: time-resolver, Property 4: 空输入安全性
# Validates: Requirements 2.6
# ============================================================================

class TestTimeExpressionExtractorProperty4:
    """
    Property 4: 空输入安全性
    For any 不包含财周/财月/财季/财年关键词的随机字符串，
    TimeExpressionExtractor.extract() 返回空列表，不抛出异常。
    Validates: Requirements 2.6
    """

    extractor = TimeExpressionExtractor()

    # 生成不含时间关键词的字符串：只用普通汉字、字母、数字，但排除触发词
    _TIME_KEYWORDS = [
        "FW", "fw", "FM", "fm", "FQ", "fq", "FY", "fy",
        "财周", "财月", "财季", "财年",
        "春节", "五一", "国庆", "元旦", "中秋",
        "第", "本", "上", "下",
    ]

    # 只使用不会触发任何时间关键词的安全字符集
    _SAFE_ALPHABET = "abcdeghijklnoprstu vwxz0123456789ABCDEGHIJKLNOPRSTU VWXZ"

    @given(
        text=st.text(
            alphabet=_SAFE_ALPHABET,
            min_size=0,
            max_size=200,
        )
    )
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    def test_no_time_keywords_returns_empty(self, text: str):
        """
        Feature: time-resolver, Property 4: 空输入安全性
        Validates: Requirements 2.6
        """
        result = self.extractor.extract(text)
        assert isinstance(result, list), "应返回列表"
        assert len(result) == 0, f"不含时间关键词的文本应返回空列表，但得到: {result}，输入: {repr(text)}"

    def test_empty_string_returns_empty(self):
        """空字符串应返回空列表"""
        assert self.extractor.extract("") == []

    def test_none_like_empty_returns_empty(self):
        """纯空白字符串应返回空列表"""
        assert self.extractor.extract("   ") == []

    def test_fw_label_extracted(self):
        """FW22 应被正确提取"""
        results = self.extractor.extract("查询FW22的销售数据")
        assert len(results) == 1
        assert results[0].label == "FW22"
        assert results[0].expr_type == "fw"

    def test_relative_fw_extracted(self):
        """本财周 应被正确提取为相对表达"""
        results = self.extractor.extract("本财周的销售情况")
        assert len(results) == 1
        assert results[0].is_relative is True
        assert results[0].expr_type == "fw"

    def test_fm_label_extracted(self):
        """FM3 应被正确提取"""
        results = self.extractor.extract("FM3的汇总数据")
        assert len(results) == 1
        assert results[0].label == "FM3"
        assert results[0].expr_type == "fm"

    def test_fq_label_extracted(self):
        """FQ1 应被正确提取"""
        results = self.extractor.extract("FQ1季度报告")
        assert len(results) == 1
        assert results[0].label == "FQ1"
        assert results[0].expr_type == "fq"

    def test_fy_label_extracted(self):
        """FY2026 应被正确提取"""
        results = self.extractor.extract("FY2026全年数据")
        assert len(results) == 1
        assert results[0].label == "FY2026"
        assert results[0].expr_type == "fy"

    def test_holiday_extracted(self):
        """春节 应被提取为节假日类型"""
        results = self.extractor.extract("春节期间的销售情况")
        assert len(results) == 1
        assert results[0].expr_type == "holiday"
        assert results[0].raw_text == "春节"

    def test_multiple_expressions(self):
        """多个时间表达应全部被提取"""
        results = self.extractor.extract("对比FW22和FW23的数据")
        assert len(results) == 2
        labels = {r.label for r in results}
        assert "FW22" in labels
        assert "FW23" in labels


# ============================================================================
# Property 2 & 3: 日期范围合法性 + 财月范围包含性
# Feature: time-resolver, Property 2 & 3
# Validates: Requirements 1.3, 1.4, 3.2, 3.3, 3.4
# ============================================================================

class TestFiscalCalendarRepositoryProperties:
    """
    Property 2: 日期范围合法性
    For any 解析成功的 DateRange，start_date <= end_date。

    Property 3: 财月/财季/财年范围包含性
    For any 财月标签，其合并日期范围 = min(fw_start) ~ max(fw_end)。

    Validates: Requirements 1.3, 1.4, 3.2, 3.3, 3.4
    """

    repo = FiscalCalendarRepository()

    def _make_sequential_weeks(
        self,
        db,
        count: int,
        fiscal_month: str = "FM1",
        fiscal_quarter: str = "FQ1",
        fiscal_year: str = "FY2026",
        start: date = date(2026, 1, 5),
    ) -> List[FiscalCalendar]:
        """生成连续的财周记录并插入数据库"""
        records = []
        current = start
        for i in range(count):
            fw_label = f"FW{i + 1:02d}"
            fw_start = current
            fw_end = current + timedelta(days=6)
            rec = _make_fw_record(
                fw_label=fw_label,
                fw_start_date=fw_start,
                fw_end_date=fw_end,
                fiscal_month=fiscal_month,
                fiscal_quarter=fiscal_quarter,
                fiscal_year=fiscal_year,
            )
            db.add(rec)
            records.append(rec)
            current = fw_end + timedelta(days=1)
        db.commit()
        return records

    @given(
        week_count=st.integers(min_value=1, max_value=10),
        start_offset=st.integers(min_value=0, max_value=300),
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_property2_date_range_validity_fw(self, week_count: int, start_offset: int):
        """
        Feature: time-resolver, Property 2: 日期范围合法性（财周）
        Validates: Requirements 3.1
        """
        engine = make_engine()
        db = make_session(engine)
        try:
            start = date(2026, 1, 5) + timedelta(days=start_offset)
            records = self._make_sequential_weeks(db, week_count, start=start)
            for rec in records:
                result = self.repo.find_by_fw_label(db, rec.fw_label)
                assert result is not None
                assert result.fw_start_date <= result.fw_end_date, (
                    f"财周 {rec.fw_label}: start_date {result.fw_start_date} > end_date {result.fw_end_date}"
                )
        finally:
            db.close()

    @given(
        week_count=st.integers(min_value=2, max_value=8),
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_property2_date_range_validity_fm(self, week_count: int):
        """
        Feature: time-resolver, Property 2: 日期范围合法性（财月）
        Validates: Requirements 3.2
        """
        engine = make_engine()
        db = make_session(engine)
        try:
            self._make_sequential_weeks(db, week_count, fiscal_month="FM2")
            result = self.repo.find_range_by_fiscal_month(db, "FM2")
            assert result is not None
            start = date.fromisoformat(result.start_date)
            end = date.fromisoformat(result.end_date)
            assert start <= end, f"财月 FM2: start {start} > end {end}"
        finally:
            db.close()

    @given(
        week_count=st.integers(min_value=2, max_value=8),
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_property3_fiscal_month_range_containment(self, week_count: int):
        """
        Feature: time-resolver, Property 3: 财月范围包含性
        For any 财月标签，合并范围 = min(fw_start) ~ max(fw_end)
        Validates: Requirements 1.4, 3.2
        """
        engine = make_engine()
        db = make_session(engine)
        try:
            records = self._make_sequential_weeks(db, week_count, fiscal_month="FM3")
            expected_start = min(r.fw_start_date for r in records)
            expected_end = max(r.fw_end_date for r in records)

            result = self.repo.find_range_by_fiscal_month(db, "FM3")
            assert result is not None
            actual_start = date.fromisoformat(result.start_date)
            actual_end = date.fromisoformat(result.end_date)

            assert actual_start == expected_start, (
                f"财月 FM3 start 应为 {expected_start}，实际为 {actual_start}"
            )
            assert actual_end == expected_end, (
                f"财月 FM3 end 应为 {expected_end}，实际为 {actual_end}"
            )
        finally:
            db.close()

    @given(
        week_count=st.integers(min_value=2, max_value=8),
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_property3_fiscal_quarter_range_containment(self, week_count: int):
        """
        Feature: time-resolver, Property 3: 财季范围包含性
        Validates: Requirements 1.4, 3.3
        """
        engine = make_engine()
        db = make_session(engine)
        try:
            records = self._make_sequential_weeks(db, week_count, fiscal_quarter="FQ2")
            expected_start = min(r.fw_start_date for r in records)
            expected_end = max(r.fw_end_date for r in records)

            result = self.repo.find_range_by_fiscal_quarter(db, "FQ2")
            assert result is not None
            actual_start = date.fromisoformat(result.start_date)
            actual_end = date.fromisoformat(result.end_date)

            assert actual_start == expected_start
            assert actual_end == expected_end
        finally:
            db.close()

    @given(
        week_count=st.integers(min_value=2, max_value=8),
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_property3_fiscal_year_range_containment(self, week_count: int):
        """
        Feature: time-resolver, Property 3: 财年范围包含性
        Validates: Requirements 1.4, 3.4
        """
        engine = make_engine()
        db = make_session(engine)
        try:
            records = self._make_sequential_weeks(db, week_count, fiscal_year="FY2025")
            expected_start = min(r.fw_start_date for r in records)
            expected_end = max(r.fw_end_date for r in records)

            result = self.repo.find_range_by_fiscal_year(db, "FY2025")
            assert result is not None
            actual_start = date.fromisoformat(result.start_date)
            actual_end = date.fromisoformat(result.end_date)

            assert actual_start == expected_start
            assert actual_end == expected_end
        finally:
            db.close()

    def test_nonexistent_label_returns_none(self):
        """不存在的标签应返回 None"""
        engine = make_engine()
        db = make_session(engine)
        try:
            assert self.repo.find_by_fw_label(db, "FW99") is None
            assert self.repo.find_range_by_fiscal_month(db, "FM99") is None
            assert self.repo.find_range_by_fiscal_quarter(db, "FQ9") is None
            assert self.repo.find_range_by_fiscal_year(db, "FY9999") is None
        finally:
            db.close()


# ============================================================================
# Property 1 & 5: fw_label Round-Trip + 不存在标签安全性
# Feature: time-resolver, Property 1 & 5
# Validates: Requirements 1.2, 3.1, 3.5
# ============================================================================

class TestTimeResolverProperties:
    """
    Property 1: fw_label 查询 Round-Trip
    For any 插入到 FiscalCalendar 的 fw_label，通过包含该标签的问题解析，
    应能返回相同的 fw_start_date 和 fw_end_date。

    Property 5: 不存在标签安全性
    For any 不在 FiscalCalendar 表中的时间标签，TimeResolver.resolve() 返回 None，不抛出异常。

    Validates: Requirements 1.2, 3.1, 3.5
    """

    resolver = TimeResolver()

    def _run_async(self, coro):
        return asyncio.get_event_loop().run_until_complete(coro)

    @given(
        week_num=st.integers(min_value=1, max_value=52),
        start_offset=st.integers(min_value=0, max_value=300),
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_property1_fw_label_round_trip(self, week_num: int, start_offset: int):
        """
        Feature: time-resolver, Property 1: fw_label 查询 Round-Trip
        Validates: Requirements 1.2, 3.1
        """
        engine = make_engine()
        db = make_session(engine)
        try:
            fw_label = f"FW{week_num:02d}"
            start = date(2026, 1, 5) + timedelta(days=start_offset)
            end = start + timedelta(days=6)

            record = _make_fw_record(
                fw_label=fw_label,
                fw_start_date=start,
                fw_end_date=end,
            )
            db.add(record)
            db.commit()

            question = f"查询{fw_label}的销售数据"
            ctx = self._run_async(self.resolver.resolve(question, db))

            assert ctx is not None, f"应解析到时间上下文，fw_label={fw_label}"
            assert len(ctx.date_ranges) >= 1

            dr = ctx.date_ranges[0]
            assert dr.label == fw_label, f"标签应为 {fw_label}，实际为 {dr.label}"
            assert dr.start_date == start.isoformat(), (
                f"start_date 应为 {start.isoformat()}，实际为 {dr.start_date}"
            )
            assert dr.end_date == end.isoformat(), (
                f"end_date 应为 {end.isoformat()}，实际为 {dr.end_date}"
            )
        finally:
            db.close()

    @given(
        week_num=st.integers(min_value=53, max_value=99),
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_property5_nonexistent_label_returns_none(self, week_num: int):
        """
        Feature: time-resolver, Property 5: 不存在标签安全性
        For any 不在 FiscalCalendar 表中的时间标签，resolve() 返回 None，不抛出异常。
        Validates: Requirements 3.5
        """
        engine = make_engine()
        db = make_session(engine)
        try:
            # 数据库为空，任何标签都不存在
            fw_label = f"FW{week_num:02d}"
            question = f"查询{fw_label}的数据"
            ctx = self._run_async(self.resolver.resolve(question, db))
            # 标签不存在时应返回 None
            assert ctx is None, f"不存在的标签 {fw_label} 应返回 None，实际返回 {ctx}"
        finally:
            db.close()

    def test_empty_question_returns_none(self):
        """空问题应返回 None"""
        engine = make_engine()
        db = make_session(engine)
        try:
            ctx = self._run_async(self.resolver.resolve("", db))
            assert ctx is None
        finally:
            db.close()

    def test_no_time_expression_returns_none(self):
        """不含时间表达的问题应返回 None"""
        engine = make_engine()
        db = make_session(engine)
        try:
            ctx = self._run_async(self.resolver.resolve("查询所有渠道的销售数据", db))
            assert ctx is None
        finally:
            db.close()

    def test_rewrite_question_replaces_fw_label(self):
        """rewrite_question 应将 FW22 替换为带日期的描述"""
        engine = make_engine()
        db = make_session(engine)
        try:
            record = _make_fw_record(
                fw_label="FW22",
                fw_start_date=date(2026, 5, 25),
                fw_end_date=date(2026, 5, 31),
            )
            db.add(record)
            db.commit()

            ctx = self._run_async(self.resolver.resolve("查询FW22的销售数据", db))
            assert ctx is not None
            assert "2026-05-25" in ctx.rewritten_question
            assert "2026-05-31" in ctx.rewritten_question
        finally:
            db.close()


# ============================================================================
# Property 6: 导入幂等性（Upsert）
# Feature: time-resolver, Property 6: 导入幂等性
# Validates: Requirements 5.4
# ============================================================================

class TestImportIdempotencyProperty6:
    """
    Property 6: 导入幂等性
    For any fw_label，将相同记录导入 N 次后，数据库中该 fw_label 只存在 1 条记录，
    内容为最后一次导入的值。
    Validates: Requirements 5.4
    """

    repo = FiscalCalendarRepository()

    def _upsert_record(
        self,
        db,
        fw_label: str,
        fw_start_date: date,
        fw_end_date: date,
        fiscal_month: str = "FM1",
        fiscal_quarter: str = "FQ1",
        fiscal_year: str = "FY2026",
        natural_year: int = 2026,
    ):
        """模拟 API 的 upsert 逻辑"""
        existing = self.repo.find_by_fw_label(db, fw_label)
        if existing:
            existing.fw_start_date = fw_start_date
            existing.fw_end_date = fw_end_date
            existing.fiscal_month = fiscal_month
            existing.fiscal_quarter = fiscal_quarter
            existing.fiscal_year = fiscal_year
            existing.natural_year = natural_year
        else:
            record = FiscalCalendar(
                id=str(uuid.uuid4()),
                fw_label=fw_label,
                fw_start_date=fw_start_date,
                fw_end_date=fw_end_date,
                fiscal_month=fiscal_month,
                fiscal_quarter=fiscal_quarter,
                fiscal_year=fiscal_year,
                natural_year=natural_year,
            )
            db.add(record)
        db.commit()

    @given(
        week_num=st.integers(min_value=1, max_value=52),
        import_count=st.integers(min_value=2, max_value=5),
        start_offset=st.integers(min_value=0, max_value=300),
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_property6_import_idempotency(
        self, week_num: int, import_count: int, start_offset: int
    ):
        """
        Feature: time-resolver, Property 6: 导入幂等性
        For any fw_label，导入 N 次后数据库只有 1 条记录，内容为最后一次导入的值。
        Validates: Requirements 5.4
        """
        engine = make_engine()
        db = make_session(engine)
        try:
            fw_label = f"FW{week_num:02d}"
            base_start = date(2026, 1, 5) + timedelta(days=start_offset)

            last_start = base_start
            last_end = base_start + timedelta(days=6)

            # 导入 N 次，每次使用不同的日期（模拟更新）
            for i in range(import_count):
                s = base_start + timedelta(days=i)
                e = s + timedelta(days=6)
                self._upsert_record(db, fw_label, s, e)
                last_start = s
                last_end = e

            # 验证：数据库中只有 1 条该 fw_label 的记录
            from sqlalchemy import func as sqlfunc
            count = (
                db.query(sqlfunc.count(FiscalCalendar.id))
                .filter(FiscalCalendar.fw_label == fw_label)
                .scalar()
            )
            assert count == 1, (
                f"fw_label={fw_label} 导入 {import_count} 次后应只有 1 条记录，实际有 {count} 条"
            )

            # 验证：内容为最后一次导入的值
            record = self.repo.find_by_fw_label(db, fw_label)
            assert record is not None
            assert record.fw_start_date == last_start, (
                f"fw_start_date 应为最后一次导入的 {last_start}，实际为 {record.fw_start_date}"
            )
            assert record.fw_end_date == last_end, (
                f"fw_end_date 应为最后一次导入的 {last_end}，实际为 {record.fw_end_date}"
            )
        finally:
            db.close()

    def test_single_import_creates_one_record(self):
        """单次导入应创建 1 条记录"""
        engine = make_engine()
        db = make_session(engine)
        try:
            self._upsert_record(db, "FW10", date(2026, 3, 9), date(2026, 3, 15))
            record = self.repo.find_by_fw_label(db, "FW10")
            assert record is not None
            assert record.fw_label == "FW10"
        finally:
            db.close()

    def test_reimport_updates_dates(self):
        """重复导入相同 fw_label 应更新日期"""
        engine = make_engine()
        db = make_session(engine)
        try:
            self._upsert_record(db, "FW11", date(2026, 3, 16), date(2026, 3, 22))
            self._upsert_record(db, "FW11", date(2026, 3, 17), date(2026, 3, 23))

            record = self.repo.find_by_fw_label(db, "FW11")
            assert record is not None
            assert record.fw_start_date == date(2026, 3, 17)
            assert record.fw_end_date == date(2026, 3, 23)
        finally:
            db.close()
