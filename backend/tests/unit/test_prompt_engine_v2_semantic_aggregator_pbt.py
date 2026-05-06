# -*- coding: utf-8 -*-
"""
ChatBI Prompt Engine v2 - SemanticContextAggregator 属性测试
Property 7: SemanticContextAggregator 输出包含业务术语映射格式
Validates: Requirements 4.5

Feature: chatbi-prompt-engine-v2, Property 7: SemanticContextAggregator 输出包含业务术语映射格式
"""

import pytest
from hypothesis import given, settings, strategies as st

from src.services.semantic_context_aggregator import SemanticContextAggregator


# ---------------------------------------------------------------------------
# 生成器：合法的字段名、字典项 key/value（避免空字符串导致无意义输出）
# ---------------------------------------------------------------------------

field_name_strategy = st.text(
    alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd"), whitelist_characters="_"),
    min_size=1,
    max_size=30,
)

dict_key_strategy = st.text(
    alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd"), whitelist_characters="_"),
    min_size=1,
    max_size=20,
)

dict_value_strategy = st.text(min_size=1, max_size=50)


def build_field_dict_info(table_id: str, field_name: str, items: list) -> dict:
    """构建 field_dict_info 结构体"""
    return {
        "table_id": table_id,
        "field_name": field_name,
        "field_type": "VARCHAR",
        "dictionary_id": 1,
        "dictionary_name": "test_dict",
        "dictionary_code": "TEST",
        "dictionary_type": "field",
        "items": items,
        "items_count": len(items),
    }


# ---------------------------------------------------------------------------
# Property 7: 输出包含 "业务术语:" 和 "过滤条件:" 格式
# Feature: chatbi-prompt-engine-v2, Property 7
# Validates: Requirements 4.5
# ---------------------------------------------------------------------------

@given(
    field_name=field_name_strategy,
    keys=st.lists(dict_key_strategy, min_size=1, max_size=10, unique=True),
    values=st.lists(dict_value_strategy, min_size=1, max_size=10),
)
@settings(max_examples=100)
def test_format_dictionary_content_contains_business_term_mapping(
    field_name, keys, values
):
    """
    Property 7: SemanticContextAggregator 输出包含业务术语映射格式
    对于任意字段名和字典项，_format_dictionary_content 的输出必须包含
    '业务术语:' 和 '过滤条件:' 格式的映射行。
    Validates: Requirements 4.5
    """
    # 对齐 keys 和 values 长度
    n = min(len(keys), len(values))
    items = [{"key": keys[i], "value": values[i]} for i in range(n)]

    field_dict_info_list = [
        build_field_dict_info("table_test", field_name, items)
    ]

    result = SemanticContextAggregator._format_dictionary_content(field_dict_info_list)

    # 输出必须包含顶部标题
    assert "## 业务术语与字段映射" in result, (
        f"输出缺少标题 '## 业务术语与字段映射'，实际输出:\n{result}"
    )

    # 每个字典项都必须生成 "业务术语:" 行
    assert "业务术语:" in result, (
        f"输出缺少 '业务术语:' 格式，实际输出:\n{result}"
    )

    # 每个字典项都必须生成 "过滤条件:" 行
    assert "过滤条件:" in result, (
        f"输出缺少 '过滤条件:' 格式，实际输出:\n{result}"
    )


@given(
    field_name=field_name_strategy,
    key=dict_key_strategy,
    value=dict_value_strategy,
)
@settings(max_examples=100)
def test_format_dictionary_content_filter_condition_uses_field_name_and_key(
    field_name, key, value
):
    """
    Property 7 (精确格式): 过滤条件行必须包含字段名和 key 值。
    即：过滤条件: <field_name> = '<key>'
    Validates: Requirements 4.5
    """
    items = [{"key": key, "value": value}]
    field_dict_info_list = [
        build_field_dict_info("table_test", field_name, items)
    ]

    result = SemanticContextAggregator._format_dictionary_content(field_dict_info_list)

    expected_filter = f"过滤条件: {field_name} = '{key}'"
    assert expected_filter in result, (
        f"输出缺少精确过滤条件 '{expected_filter}'，实际输出:\n{result}"
    )


@given(
    field_name=field_name_strategy,
    key=dict_key_strategy,
    value=dict_value_strategy,
)
@settings(max_examples=100)
def test_format_dictionary_content_preserves_enum_values(
    field_name, key, value
):
    """
    Property 7 (枚举值保留): 输出必须保留完整枚举值列表。
    Validates: Requirements 4.5
    """
    items = [{"key": key, "value": value}]
    field_dict_info_list = [
        build_field_dict_info("table_test", field_name, items)
    ]

    result = SemanticContextAggregator._format_dictionary_content(field_dict_info_list)

    assert "完整枚举值:" in result, (
        f"输出缺少 '完整枚举值:' 行，实际输出:\n{result}"
    )
    # 枚举值行应包含 key=value 格式
    assert f"{key}={value}" in result, (
        f"枚举值行缺少 '{key}={value}'，实际输出:\n{result}"
    )
