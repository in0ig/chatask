"""财务日历工具：规范化与调度单测。"""
from unittest.mock import MagicMock

import pytest

from src.tools.fiscal_calendar_tools import (
    dispatch_fiscal_calendar_tool,
    normalize_fiscal_period_label,
    normalize_fiscal_year_label,
    normalize_fw_label,
)


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("FY2026", "FY2026"),
        ("fy26", "FY2026"),
        ("26", "FY2026"),
        ("2026", "FY2026"),
    ],
)
def test_normalize_fiscal_year_label(raw, expected):
    assert normalize_fiscal_year_label(raw) == expected


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("P10", "FM10"),
        ("FM10", "FM10"),
        ("fm3", "FM3"),
        (10, "FM10"),
    ],
)
def test_normalize_fiscal_period_label(raw, expected):
    assert normalize_fiscal_period_label(raw) == expected


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("FW1", "FW01"),
        ("fw40", "FW40"),
    ],
)
def test_normalize_fw_label(raw, expected):
    assert normalize_fw_label(raw) == expected


def test_dispatch_unknown_tool():
    r = dispatch_fiscal_calendar_tool("no_such", {}, MagicMock())
    assert r.get("ok") is False
    assert "未知工具" in r.get("error", "")
