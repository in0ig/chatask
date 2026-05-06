# -*- coding: utf-8 -*-
"""
ChatBI Prompt Engine v2 - sql_generation 模板测试
验证 Properties 5, 6（条件聚合规则、语义字典强制查阅规则）
Validates: Requirements 3.1, 3.2, 3.3, 3.4, 4.1, 4.2, 4.3
"""

import pathlib
import yaml
import pytest

# 定位 prompts.yml 路径
PROMPTS_YML_PATH = pathlib.Path(__file__).parent.parent.parent / "config" / "prompts.yml"


def load_sql_generation_content() -> str:
    """加载 sql_generation 模板内容"""
    with open(PROMPTS_YML_PATH, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    return config["sql_generation"]["content"]


def load_sql_generation_template() -> dict:
    """加载 sql_generation 完整模板配置"""
    with open(PROMPTS_YML_PATH, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    return config["sql_generation"]


class TestSqlGenerationTemplateExists:
    """验证模板基本结构"""

    def test_template_exists_in_config(self):
        """验证 sql_generation 模板存在于配置文件中"""
        with open(PROMPTS_YML_PATH, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        assert "sql_generation" in config

    def test_template_has_content(self):
        """验证模板有内容"""
        content = load_sql_generation_content()
        assert content is not None
        assert len(content.strip()) > 0

    def test_template_has_semantic_context_variable(self):
        """验证模板变量列表包含 semantic_context"""
        template = load_sql_generation_template()
        variables = template.get("variables", [])
        assert "semantic_context" in variables, (
            f"semantic_context 未在 variables 列表中，当前 variables: {variables}"
        )


class TestConditionalAggregationRules:
    """
    Property 5: 条件聚合规则存在于 sql_generation Prompt
    验证模板包含 CASE WHEN 条件聚合规范
    Validates: Requirements 3.1, 3.2, 3.3, 3.4
    """

    def test_case_when_syntax_example_exists(self):
        """
        Property 5a: 验证模板包含 SUM(CASE WHEN 示例文本
        Validates: Requirements 3.1, 3.4
        """
        content = load_sql_generation_content()
        assert "SUM(CASE WHEN" in content, (
            "模板中未找到 'SUM(CASE WHEN' 条件聚合示例，违反 Requirements 3.1, 3.4"
        )

    def test_nullif_division_protection_exists(self):
        """
        Property 5b: 验证模板包含 NULLIF 防除零示例
        Validates: Requirements 3.3
        """
        content = load_sql_generation_content()
        assert "NULLIF" in content, (
            "模板中未找到 'NULLIF' 防除零规则，违反 Requirements 3.3"
        )

    def test_prohibit_nested_join_rule_exists(self):
        """
        Property 5c: 验证模板包含禁止嵌套 JOIN 的规则文本
        Validates: Requirements 3.2
        """
        content = load_sql_generation_content()
        # 检查禁止嵌套 JOIN 的规则
        has_prohibition = (
            "禁止" in content and "JOIN" in content
        ) or (
            "prohibit" in content.lower() and "join" in content.lower()
        )
        assert has_prohibition, (
            "模板中未找到禁止嵌套 JOIN 的规则，违反 Requirements 3.2"
        )

    def test_abs_change_and_pct_change_rule_exists(self):
        """
        验证模板包含 SELECT 子句必须包含绝对差值和变化率的规则
        Validates: Requirements 3.3
        """
        content = load_sql_generation_content()
        # 检查绝对差值规则
        has_abs_change = "abs_change" in content or "绝对差值" in content or "absolute" in content.lower()
        # 检查变化率规则
        has_pct_change = "pct_change" in content or "变化率" in content or "percentage" in content.lower()
        assert has_abs_change, "模板中未找到绝对差值规则，违反 Requirements 3.3"
        assert has_pct_change, "模板中未找到变化率规则，违反 Requirements 3.3"

    def test_top_n_subquery_pattern_exists(self):
        """
        验证模板包含 Top-N 增长排名的子查询模式
        Validates: Requirements 3.5
        """
        content = load_sql_generation_content()
        # 检查子查询模式（ORDER BY + LIMIT 在外层）
        has_subquery_pattern = (
            "ORDER BY" in content and "LIMIT" in content
            and ("growth_rate" in content or "增长率" in content or "Top-N" in content or "Top N" in content)
        )
        assert has_subquery_pattern, (
            "模板中未找到 Top-N 增长排名的子查询模式，违反 Requirements 3.5"
        )

    def test_conditional_aggregation_complete_example_exists(self):
        """
        验证模板包含完整的条件聚合 SQL 示例（Q01-05 模式）
        Validates: Requirements 3.4
        """
        content = load_sql_generation_content()
        # 完整示例应包含 CASE WHEN、NULLIF、GROUP BY
        has_complete_example = (
            "SUM(CASE WHEN" in content
            and "NULLIF" in content
            and "GROUP BY" in content
        )
        assert has_complete_example, (
            "模板中未找到完整的条件聚合 SQL 示例（需包含 SUM(CASE WHEN、NULLIF、GROUP BY），违反 Requirements 3.4"
        )


class TestSemanticDictionaryLookupRules:
    """
    Property 6: 语义字典强制查阅规则存在于 sql_generation Prompt
    验证模板包含语义字典强制查阅规则
    Validates: Requirements 4.1, 4.2, 4.3
    """

    def test_semantic_context_lookup_rule_exists(self):
        """
        Property 6a: 验证模板包含语义字典查阅规则文本
        Validates: Requirements 4.1
        """
        content = load_sql_generation_content()
        # 检查强制查阅规则
        has_lookup_rule = (
            "semantic_context" in content
            and ("查阅" in content or "查找" in content or "look up" in content.lower() or "lookup" in content.lower())
        )
        assert has_lookup_rule, (
            "模板中未找到 semantic_context 强制查阅规则，违反 Requirements 4.1"
        )

    def test_prohibit_guessing_undefined_terms_rule_exists(self):
        """
        Property 6b: 验证模板包含禁止猜测未定义术语的规则
        Validates: Requirements 4.3
        """
        content = load_sql_generation_content()
        # 检查禁止猜测规则
        has_prohibit_guess = (
            "禁止" in content
            and ("猜测" in content or "推断" in content or "guess" in content.lower() or "infer" in content.lower())
        )
        assert has_prohibit_guess, (
            "模板中未找到禁止猜测未定义业务术语的规则，违反 Requirements 4.3"
        )

    def test_apply_exact_filter_condition_rule_exists(self):
        """
        Property 6c: 验证模板包含应用精确过滤条件的规则
        Validates: Requirements 4.2
        """
        content = load_sql_generation_content()
        # 检查应用过滤条件规则（WHERE 子句中应用）
        has_filter_rule = (
            "WHERE" in content
            and ("过滤条件" in content or "filter" in content.lower())
        )
        assert has_filter_rule, (
            "模板中未找到在 WHERE 子句中应用过滤条件的规则，违反 Requirements 4.2"
        )

    def test_semantic_lookup_is_highest_priority(self):
        """
        验证语义字典查阅规则被标记为最高优先级
        Validates: Requirements 4.1
        """
        content = load_sql_generation_content()
        # 检查最高优先级标记
        has_priority = (
            "最高优先级" in content
            or "highest priority" in content.lower()
            or "最先执行" in content
        )
        assert has_priority, (
            "模板中未找到语义字典查阅规则的最高优先级标记，违反 Requirements 4.1"
        )

    def test_value_no_translation_rule_exists(self):
        """
        验证模板包含字段值不翻译规则（禁止翻译 semantic_context 中的原始值）
        Validates: Requirements 1.5
        """
        content = load_sql_generation_content()
        # 检查值不翻译规则
        has_no_translate = (
            "不翻译" in content
            or "禁止翻译" in content
            or "原始值" in content
            or "值不翻译" in content
        )
        assert has_no_translate, (
            "模板中未找到字段值不翻译规则，违反 Requirements 1.5"
        )
