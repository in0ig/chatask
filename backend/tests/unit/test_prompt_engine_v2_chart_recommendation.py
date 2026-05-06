# -*- coding: utf-8 -*-
"""
ChatBI Prompt Engine v2 - chart_recommendation 模板测试
验证 Property 10（Combo Chart 推荐规则、yAxisIndex 规范、L1 单行 → table 规则）
Validates: Requirements 5.1, 5.2, 5.3, 5.4, 5.7
"""

import pathlib
import yaml
import pytest

# 定位 prompts.yml 路径
PROMPTS_YML_PATH = pathlib.Path(__file__).parent.parent.parent / "config" / "prompts.yml"


def load_chart_recommendation_content() -> str:
    """加载 chart_recommendation 模板内容"""
    with open(PROMPTS_YML_PATH, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    return config["chart_recommendation"]["content"]


def load_chart_recommendation_template() -> dict:
    """加载 chart_recommendation 完整模板配置"""
    with open(PROMPTS_YML_PATH, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    return config["chart_recommendation"]


class TestChartRecommendationTemplateExists:
    """验证模板基本结构"""

    def test_template_exists_in_config(self):
        """验证 chart_recommendation 模板存在于配置文件中"""
        with open(PROMPTS_YML_PATH, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        assert "chart_recommendation" in config

    def test_template_has_content(self):
        """验证模板有内容"""
        content = load_chart_recommendation_content()
        assert content is not None
        assert len(content.strip()) > 0

    def test_recommended_chart_includes_combo(self):
        """
        验证 recommendedChart 的可选值包含 "combo"
        Validates: Requirements 5.1
        """
        content = load_chart_recommendation_content()
        assert '"combo"' in content, (
            "模板中未找到 'combo' 作为 recommendedChart 的可选值，违反 Requirements 5.1"
        )

    def test_recommended_chart_includes_table(self):
        """
        验证 recommendedChart 的可选值包含 "table"
        Validates: Requirements 5.7
        """
        content = load_chart_recommendation_content()
        assert '"table"' in content, (
            "模板中未找到 'table' 作为 recommendedChart 的可选值，违反 Requirements 5.7"
        )


class TestYAxisIndexSpecification:
    """
    Property 10a: yAxisIndex 字段规范存在于 chart_recommendation Prompt
    Validates: Requirements 5.2
    """

    def test_y_axis_index_field_exists(self):
        """
        验证模板包含 yAxisIndex 字段规范文本
        Validates: Requirements 5.2
        """
        content = load_chart_recommendation_content()
        assert "yAxisIndex" in content, (
            "模板中未找到 'yAxisIndex' 字段规范，违反 Requirements 5.2"
        )

    def test_y_axis_index_0_for_absolute_values(self):
        """
        验证模板规定绝对值 series 使用 yAxisIndex: 0（主轴）
        Validates: Requirements 5.2
        """
        content = load_chart_recommendation_content()
        # 检查 yAxisIndex: 0 用于绝对值/bar
        assert "yAxisIndex: 0" in content or '"yAxisIndex": 0' in content, (
            "模板中未找到 yAxisIndex: 0 的规范（绝对值主轴），违反 Requirements 5.2"
        )

    def test_y_axis_index_1_for_rate_values(self):
        """
        验证模板规定比率 series 使用 yAxisIndex: 1（次轴）
        Validates: Requirements 5.2
        """
        content = load_chart_recommendation_content()
        # 检查 yAxisIndex: 1 用于比率/line
        assert "yAxisIndex: 1" in content or '"yAxisIndex": 1' in content, (
            "模板中未找到 yAxisIndex: 1 的规范（比率次轴），违反 Requirements 5.2"
        )


class TestComboChartIdentificationRules:
    """
    Property 10b: Combo Chart 识别规则存在于 chart_recommendation Prompt
    Validates: Requirements 5.1, 5.4
    """

    def test_combo_chart_rule_exists(self):
        """
        Property 10: Combo Chart 推荐规则存在于 chart_recommendation Prompt
        验证模板包含 Combo Chart 识别规则文本
        Validates: Requirements 5.1
        """
        content = load_chart_recommendation_content()
        # 检查 Combo Chart 识别规则
        has_combo_rule = (
            "Combo" in content or "combo" in content
        ) and (
            "绝对值" in content or "absolute" in content.lower()
        ) and (
            "比率" in content or "rate" in content.lower() or "pct" in content.lower()
        )
        assert has_combo_rule, (
            "模板中未找到 Combo Chart 识别规则（需同时含绝对值和比率字段），违反 Requirements 5.1"
        )

    def test_combo_chart_bar_for_absolute_values(self):
        """
        验证 Combo Chart 规则中绝对值 series 使用 bar 类型
        Validates: Requirements 5.2
        """
        content = load_chart_recommendation_content()
        # bar 类型用于绝对值
        assert '"type": "bar"' in content or "'type': 'bar'" in content or "bar" in content, (
            "模板中未找到 Combo Chart 中 bar 类型的规范"
        )

    def test_combo_chart_line_for_rate_values(self):
        """
        验证 Combo Chart 规则中比率 series 使用 line 类型
        Validates: Requirements 5.2
        """
        content = load_chart_recommendation_content()
        # line 类型用于比率
        assert '"type": "line"' in content or "'type': 'line'" in content or "line" in content, (
            "模板中未找到 Combo Chart 中 line 类型的规范"
        )

    def test_combo_chart_not_recommended_for_single_type(self):
        """
        验证模板包含"只含绝对值或只含比率时禁止推荐 Combo"的规则
        Validates: Requirements 5.4
        """
        content = load_chart_recommendation_content()
        # 检查禁止单类型推荐 Combo 的规则
        has_prohibition = (
            "禁止" in content or "不得" in content or "not" in content.lower()
        ) and (
            "Combo" in content or "combo" in content
        )
        assert has_prohibition, (
            "模板中未找到禁止单类型字段推荐 Combo Chart 的规则，违反 Requirements 5.4"
        )


class TestAuxiliaryFieldFilterRules:
    """
    验证辅助字段过滤规则存在于 chart_recommendation Prompt
    Validates: Requirements 5.3
    """

    def test_id_field_filter_rule_exists(self):
        """
        验证模板包含 ID 类字段过滤规则
        Validates: Requirements 5.3
        """
        content = load_chart_recommendation_content()
        # 检查 ID 字段过滤规则
        has_id_filter = (
            "id" in content.lower()
            and ("过滤" in content or "filter" in content.lower() or "排除" in content or "exclude" in content.lower())
        )
        assert has_id_filter, (
            "模板中未找到 ID 类字段过滤规则，违反 Requirements 5.3"
        )

    def test_timestamp_field_filter_rule_exists(self):
        """
        验证模板包含时间戳字段过滤规则
        Validates: Requirements 5.3
        """
        content = load_chart_recommendation_content()
        # 检查时间戳字段过滤规则
        has_timestamp_filter = (
            "created_at" in content or "updated_at" in content or "timestamp" in content.lower()
        )
        assert has_timestamp_filter, (
            "模板中未找到时间戳字段过滤规则（created_at/updated_at），违反 Requirements 5.3"
        )

    def test_single_unique_value_filter_rule_exists(self):
        """
        验证模板包含只有 1 个唯一值的字段过滤规则
        Validates: Requirements 5.3
        """
        content = load_chart_recommendation_content()
        # 检查唯一值过滤规则
        has_unique_filter = (
            "唯一值" in content or "unique" in content.lower() or "1 个" in content
        )
        assert has_unique_filter, (
            "模板中未找到只有 1 个唯一值的字段过滤规则，违反 Requirements 5.3"
        )


class TestL1SingleRowTableRule:
    """
    Property 10c: L1 单行 → table 的规则存在于 chart_recommendation Prompt
    Validates: Requirements 5.7
    """

    def test_l1_single_row_table_rule_exists(self):
        """
        Property 10: L1 单行结果推荐 table 展示的规则存在
        验证模板包含 L1 单行 → table 的规则文本
        Validates: Requirements 5.7
        """
        content = load_chart_recommendation_content()
        # 检查 L1 单行 → table 规则
        has_l1_table_rule = (
            ("1 行" in content or "1行" in content or "single row" in content.lower() or "only 1 row" in content.lower())
            and ("table" in content.lower())
        )
        assert has_l1_table_rule, (
            "模板中未找到 L1 单行结果推荐 table 展示的规则，违反 Requirements 5.7"
        )

    def test_l1_single_metric_column_table_rule_exists(self):
        """
        验证模板包含单一数值列时推荐 table 的规则
        Validates: Requirements 5.7
        """
        content = load_chart_recommendation_content()
        # 检查单一数值列规则
        has_single_metric_rule = (
            "1 个数值列" in content
            or "single metric" in content.lower()
            or "只有 1 个" in content
        )
        assert has_single_metric_rule, (
            "模板中未找到单一数值列推荐 table 的规则，违反 Requirements 5.7"
        )
