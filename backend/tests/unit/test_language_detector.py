"""
语言检测属性测试
Feature: i18n-language-switch, Property 5: Language detection by ASCII ratio
使用 Hypothesis 进行基于属性的测试
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
from src.utils.language_detector import detect_language


# ============================================================================
# Property 5: Language detection by ASCII ratio
# Validates: Requirements 3.4
# ============================================================================


class TestLanguageDetectionProperties:
    """
    Property 5: Language detection by ASCII ratio

    对于任意非空字符串，若 ASCII 字母字符占非空白字符总数的比例 > 0.5，
    detect_language() 应返回 'en'；否则返回 'zh'。
    """

    @settings(max_examples=200)
    @given(st.text(min_size=1))
    def test_ascii_ratio_determines_language(self, text: str):
        """
        # Feature: i18n-language-switch, Property 5: Language detection by ASCII ratio
        对于任意非空字符串，检测结果与 ASCII 字母比例规则一致。
        """
        result = detect_language(text)

        # 计算非空白字符和 ASCII 字母数量（与实现逻辑一致）
        non_whitespace = [ch for ch in text if not ch.isspace()]

        if not non_whitespace:
            # 纯空白字符串应返回 'zh'
            assert result == 'zh'
            return

        ascii_alpha_count = sum(1 for ch in non_whitespace if ch.isascii() and ch.isalpha())
        ratio = ascii_alpha_count / len(non_whitespace)

        if ratio > 0.5:
            assert result == 'en', f"Expected 'en' for ratio={ratio:.3f}, got '{result}'"
        else:
            assert result == 'zh', f"Expected 'zh' for ratio={ratio:.3f}, got '{result}'"

    def test_empty_string_returns_zh(self):
        """空字符串应返回默认值 'zh'"""
        assert detect_language('') == 'zh'

    def test_whitespace_only_returns_zh(self):
        """纯空白字符串应返回默认值 'zh'"""
        assert detect_language('   \t\n') == 'zh'

    def test_pure_english_returns_en(self):
        """纯英文文本应返回 'en'"""
        assert detect_language('Hello world') == 'en'

    def test_pure_chinese_returns_zh(self):
        """纯中文文本应返回 'zh'"""
        assert detect_language('你好世界') == 'zh'

    def test_mixed_majority_english_returns_en(self):
        """ASCII 字母占比超过 0.5 时返回 'en'"""
        # "abc" = 3 ASCII alpha, "你" = 1 non-ASCII → ratio = 3/4 = 0.75 > 0.5
        assert detect_language('abc你') == 'en'

    def test_mixed_majority_chinese_returns_zh(self):
        """ASCII 字母占比不超过 0.5 时返回 'zh'"""
        # "a" = 1 ASCII alpha, "你好" = 2 non-ASCII → ratio = 1/3 ≈ 0.33 ≤ 0.5
        assert detect_language('a你好') == 'zh'

    def test_exactly_half_ascii_returns_zh(self):
        """ASCII 字母占比恰好等于 0.5 时返回 'zh'（规则是严格大于）"""
        # "ab" = 2 ASCII alpha, "你好" = 2 non-ASCII → ratio = 2/4 = 0.5, not > 0.5
        assert detect_language('ab你好') == 'zh'

    def test_return_values_are_valid(self):
        """返回值只能是 'en' 或 'zh'"""
        for text in ['hello', '你好', '', '123', 'abc123', '   ']:
            result = detect_language(text)
            assert result in ('en', 'zh'), f"Invalid return value '{result}' for input '{text}'"


# ============================================================================
# Property 6: Prompt language injection consistency
# Validates: Requirements 3.2, 3.3, 4.1
# ============================================================================


class TestPromptInjectionProperties:
    """
    Property 6: Prompt language injection consistency

    对于任意 prompt 字符串：
    - language='en' 时，结果以英文指令常量开头
    - language='zh' 时，结果与原始 prompt 完全相同
    """

    @settings(max_examples=200)
    @given(st.text())
    def test_english_injection_prepends_instruction(self, prompt: str):
        """
        # Feature: i18n-language-switch, Property 6: Prompt language injection consistency
        对于任意 prompt，language='en' 时结果以 ENGLISH_INSTRUCTION 开头。
        """
        from src.utils.language_detector import inject_language_instruction, ENGLISH_INSTRUCTION
        result = inject_language_instruction(prompt, 'en')
        assert result.startswith(ENGLISH_INSTRUCTION), (
            f"Expected result to start with ENGLISH_INSTRUCTION, got: {result[:80]!r}"
        )

    @settings(max_examples=200)
    @given(st.text())
    def test_chinese_injection_returns_unchanged(self, prompt: str):
        """
        # Feature: i18n-language-switch, Property 6: Prompt language injection consistency
        对于任意 prompt，language='zh' 时结果与原始 prompt 完全相同。
        """
        from src.utils.language_detector import inject_language_instruction
        result = inject_language_instruction(prompt, 'zh')
        assert result == prompt, (
            f"Expected unchanged prompt for 'zh', but got different result"
        )

    @settings(max_examples=200)
    @given(st.text())
    def test_english_injection_contains_original_prompt(self, prompt: str):
        """
        # Feature: i18n-language-switch, Property 6: Prompt language injection consistency
        对于任意 prompt，language='en' 时原始 prompt 内容被保留在结果中。
        """
        from src.utils.language_detector import inject_language_instruction
        result = inject_language_instruction(prompt, 'en')
        assert result.endswith(prompt), (
            f"Expected result to end with original prompt"
        )


# ============================================================================
# Property 7: Stage label translation
# Validates: Requirements 4.3
# ============================================================================


class TestStageLabelTranslationProperties:
    """
    Property 7: Stage label translation

    对于任意已知中文 stage 标签：
    - language='en' 时，返回非空英文字符串
    - language='zh' 时，返回原始中文标签
    """

    @settings(max_examples=100)
    @given(st.sampled_from(["意图识别", "智能选表", "SQL生成", "结果解读", "数据分析"]))
    def test_known_labels_translate_to_english(self, label: str):
        """
        # Feature: i18n-language-switch, Property 7: Stage label translation
        对于任意已知中文 stage 标签，language='en' 时返回非空英文字符串。
        """
        from src.utils.language_detector import translate_stage_label
        result = translate_stage_label(label, 'en')
        assert result, f"Expected non-empty English label for '{label}'"
        assert result != label, f"Expected translation to differ from original for '{label}'"
        # 英文结果应只包含 ASCII 字符
        assert result.isascii(), f"Expected ASCII-only English label, got: {result!r}"

    @settings(max_examples=100)
    @given(st.sampled_from(["意图识别", "智能选表", "SQL生成", "结果解读", "数据分析"]))
    def test_known_labels_unchanged_for_chinese(self, label: str):
        """
        # Feature: i18n-language-switch, Property 7: Stage label translation
        对于任意已知中文 stage 标签，language='zh' 时返回原始标签不变。
        """
        from src.utils.language_detector import translate_stage_label
        result = translate_stage_label(label, 'zh')
        assert result == label, (
            f"Expected unchanged label for 'zh', got '{result}' for input '{label}'"
        )

    def test_unknown_label_returned_as_is(self):
        """未知标签在任何语言下都原样返回"""
        from src.utils.language_detector import translate_stage_label
        assert translate_stage_label("未知阶段", 'en') == "未知阶段"
        assert translate_stage_label("未知阶段", 'zh') == "未知阶段"
