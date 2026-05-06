"""业务口语「N财月」检测与 prompt 块。"""
import pytest

from src.services import business_time_colloquialism as btc


def test_find_hits_10_cai_month(monkeypatch):
    monkeypatch.setattr(btc, "CAI_MONTH_COLLOQUIAL_MEANS_NATURAL_MONTH", True)
    h = btc.find_colloquial_cai_month_hits("FY26 10财月首周付费")
    assert h and h[0][0] == 10


def test_skip_fm_prefixed(monkeypatch):
    monkeypatch.setattr(btc, "CAI_MONTH_COLLOQUIAL_MEANS_NATURAL_MONTH", True)
    h = btc.find_colloquial_cai_month_hits("FY2026 FM10 销售额")
    assert h == []


def test_build_block_zh(monkeypatch):
    monkeypatch.setattr(btc, "CAI_MONTH_COLLOQUIAL_MEANS_NATURAL_MONTH", True)
    b = btc.build_colloquial_cai_month_prompt_block("查看10财月数据", lang="zh")
    assert b is not None
    assert "自然年" in b
    assert "FM10" in b or "财期" in b


def test_disabled(monkeypatch):
    monkeypatch.setattr(btc, "CAI_MONTH_COLLOQUIAL_MEANS_NATURAL_MONTH", False)
    assert btc.build_colloquial_cai_month_prompt_block("10财月", lang="zh") is None
