# -*- coding: utf-8 -*-
"""
ChatBI Prompt Engine v2 - result_description 模板测试
验证 Properties 2, 3, 4（L2/L3路由规则、Three-in-One格式、术语不翻译规则）
Validates: Requirements 1.1, 1.2, 1.3, 1.4, 2.1
"""

import os
import yaml
import pytest
import pathlib

# 定位 prompts.yml 路径
PROMPTS_YML_PATH = pathlib.Path(__file__).parent.parent.parent / "config" / "prompts.yml"


def load_result_description_content() -> str:
    """加载 result_description 模板内容"""
    with open(PROMPTS_YML_PATH, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    return config["result_description"]["content"]


def load_result_description_template() -> dict:
    """加载 result_description 完整模板配置"""
    with open(PROMPTS_YML_PATH, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    return config["result_description"]


class TestResultDescriptionTemplateExists:
    """验证模板基本结构"""

    def test_template_exists_in_config(self):
        """验证 result_description 模板存在于配置文件中"""
        with open(PROMPTS_YML_PATH, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        assert "result_description" in config

    def test_template_has_content(self):
        """验证模板有内容"""
        content = load_result_description_content()
        assert content is not None
        assert len(content.strip()) > 0

    def test_template_variables_include_intent_type(self):
        """验证模板变量列表包含 intent_type（新增变量）"""
        template = load_result_description_template()
        variables = template.get("variables", [])
        assert "intent_type" in variables, (
            f"intent_type 未在 variables 列表中，当前 variables: {variables}"
        )

    def test_template_variables_include_total_rows(self):
        """验证模板变量列表包含 total_rows（新增变量）"""
        template = load_result_description_template()
        variables = template.get("variables", [])
        assert "total_rows" in variables, (
            f"total_rows 未在 variables 列表中，当前 variables: {variables}"
        )


class TestL1L2L3RoutingRules:
    """
    Property 2: L2/L3 查询路由规则存在
    验证模板包含明确的 L1/L2/L3 路由规则
    Validates: Requirements 1.2, 1.3
    """

    def test_l1_routing_rule_exists(self):
        """验证模板包含 L1 路由规则文本（Requirements 1.1）"""
        content = load_result_description_content()
        # L1 规则必须存在
        assert "L1" in content, "模板中未找到 L1 路由规则"

    def test_l2_routing_rule_exists(self):
        """验证模板包含 L2 路由规则文本（Requirements 1.2）"""
        content = load_result_description_content()
        assert "L2" in content, "模板中未找到 L2 路由规则"

    def test_l3_routing_rule_exists(self):
        """验证模板包含 L3 路由规则文本（Requirements 1.2）"""
        content = load_result_description_content()
        assert "L3" in content, "模板中未找到 L3 路由规则"

    def test_routing_distinguishes_l1_from_l2_l3(self):
        """
        Property 2: L2/L3 查询路由规则存在
        验证模板包含明确区分 L1 与 L2/L3 的路由规则
        Validates: Requirements 1.2, 1.3
        """
        content = load_result_description_content()
        # 必须同时包含 L1 和 L2/L3 的区分规则
        assert "L1" in content and "L2" in content and "L3" in content, (
            "模板未包含完整的 L1/L2/L3 路由规则"
        )

    def test_l1_prohibits_three_section_format(self):
        """验证 L1 规则明确禁止三段式输出（Requirements 1.1, 1.5）"""
        content = load_result_description_content()
        # L1 应该禁止 Executive Summary / Key Findings / Data Insight
        # 检查模板中有关 L1 禁止三段式的规则
        assert "禁止" in content or "prohibit" in content.lower(), (
            "模板中未找到 L1 禁止三段式的规则"
        )
        # 验证 L1 输出是一句话
        assert "一句话" in content or "single" in content.lower() or "one sentence" in content.lower(), (
            "模板中未找到 L1 一句话输出规则"
        )

    def test_routing_uses_total_rows_for_l1_detection(self):
        """验证路由规则使用 total_rows 来判断 L1（Requirements 1.1）"""
        content = load_result_description_content()
        assert "total_rows" in content or "1 行" in content or "1 row" in content.lower(), (
            "模板中未找到基于 total_rows 的 L1 判断规则"
        )


class TestThreeInOneFormat:
    """
    Property 3: Three-in-One 格式规则存在于 Prompt
    验证模板包含 Three-in-One 格式规范
    Validates: Requirements 2.1, 2.2
    """

    def test_three_in_one_format_vs_py_exists(self):
        """
        Property 3: Three-in-One 格式规则存在于 Prompt
        验证模板包含 vs. PY 标准缩写（Requirements 2.1）
        """
        content = load_result_description_content()
        assert "vs. PY" in content, (
            "模板中未找到 'vs. PY' 标准缩写，Three-in-One 格式规范缺失"
        )

    def test_three_in_one_format_abs_change_exists(self):
        """验证模板包含绝对变化量的格式规范（Requirements 2.1）"""
        content = load_result_description_content()
        # 检查绝对变化量相关规则
        assert "abs_change" in content or "absolute" in content.lower() or "绝对" in content, (
            "模板中未找到绝对变化量格式规范"
        )

    def test_three_in_one_format_pct_change_exists(self):
        """验证模板包含百分比变化的格式规范（Requirements 2.1）"""
        content = load_result_description_content()
        assert "pct_change" in content or "percentage" in content.lower() or "百分比" in content, (
            "模板中未找到百分比变化格式规范"
        )

    def test_three_in_one_format_template_string_exists(self):
        """验证模板包含 Three-in-One 格式模板字符串（Requirements 2.1）"""
        content = load_result_description_content()
        # 格式模板：[entity] [metric] was [current_value], [abs_change] / [pct_change] up/down vs.
        assert "up/down vs." in content or "up vs." in content or "down vs." in content, (
            "模板中未找到 Three-in-One 格式模板字符串"
        )

    def test_top_down_structure_rule_exists(self):
        """验证模板包含顶层总结 → 子分组 → 驱动因素的结构规则（Requirements 2.2）"""
        content = load_result_description_content()
        # 检查结构规则：总体 → 子分组 → 驱动因素
        has_structure = (
            ("总体" in content or "overall" in content.lower() or "Executive Summary" in content)
            and ("子分组" in content or "bullet" in content.lower() or "•" in content)
            and ("驱动" in content or "driver" in content.lower())
        )
        assert has_structure, (
            "模板中未找到顶层总结 → 子分组 → 驱动因素的结构规则"
        )

    def test_trend_chronological_order_rule_exists(self):
        """验证模板包含趋势问题时序列举规则（Requirements 2.5）"""
        content = load_result_description_content()
        # 趋势分析必须先按时间顺序列出各期数据
        has_trend_rule = (
            "时间顺序" in content
            or "chronological" in content.lower()
            or "按时间" in content
            or "L3" in content  # L3 路由规则中包含趋势规则
        )
        assert has_trend_rule, (
            "模板中未找到趋势问题时序列举规则"
        )

    def test_prohibited_words_list_exists(self):
        """验证模板包含禁止词列表（Requirements 2.3）"""
        content = load_result_description_content()
        # 检查禁止词
        prohibited_words = ["跃升", "回落", "拐点"]
        found_any = any(word in content for word in prohibited_words)
        assert found_any, (
            f"模板中未找到禁止词列表，期望包含: {prohibited_words}"
        )


class TestTermNoTranslationRule:
    """
    Property 4: 术语不翻译规则存在于 Prompt
    验证模板包含明确的术语不翻译规则
    Validates: Requirements 1.4, 4.4
    """

    def test_no_translation_rule_exists(self):
        """
        Property 4: 术语不翻译规则存在于 Prompt
        验证模板包含禁止翻译业务术语的规则
        Validates: Requirements 1.4
        """
        content = load_result_description_content()
        # 检查不翻译规则
        has_no_translation_rule = (
            "不翻译" in content
            or "禁止翻译" in content
            or "原样保留" in content
            or "不得翻译" in content
            or "no translation" in content.lower()
            or "do not translate" in content.lower()
        )
        assert has_no_translation_rule, (
            "模板中未找到术语不翻译规则"
        )

    def test_no_translation_rule_covers_english_terms(self):
        """验证不翻译规则覆盖英文术语（如 Paid Attendance）（Requirements 1.4）"""
        content = load_result_description_content()
        # 规则应该明确提到英文术语不得翻译为中文
        assert "Paid Attendance" in content or "Paid" in content, (
            "模板中未找到针对英文术语（如 Paid Attendance）的不翻译规则示例"
        )

    def test_no_translation_rule_covers_chinese_terms(self):
        """验证不翻译规则覆盖中文术语（如 Other China）（Requirements 1.4）"""
        content = load_result_description_content()
        # 规则应该明确提到中文地名不得翻译
        assert "Other China" in content or "上海" in content, (
            "模板中未找到针对地区名称的不翻译规则示例"
        )
