"""
业务口语与时间术语：例如「N财月」在业务中常指自然年 N 月，而非标准财期 FMN。

通过环境变量开启后，在思考/SQL 阶段注入说明：既指出表述不严谨，又约定按自然月取数。
"""
from __future__ import annotations

import os
import re
from typing import List, Optional, Tuple

# 开启时：「10财月」等形式（且非 FM 前缀）按自然月理解；关闭则不做注入。
CAI_MONTH_COLLOQUIAL_MEANS_NATURAL_MONTH = os.getenv(
    "CAI_MONTH_COLLOQUIAL_MEANS_NATURAL_MONTH", "true"
).lower() in ("1", "true", "yes")

# 匹配「10财月」「第10财月」等；不匹配「本财月」「上财月」等（无前置数字）
_RE_N_CAI_MONTH = re.compile(r"(?:第\s*)?(\d{1,2})\s*财月")


def _fm_prefix_at(text: str, digit_start: int) -> bool:
    """数字位前紧邻 FM 时视为标准财期写法，不按口语自然月处理。"""
    if digit_start >= 2 and text[digit_start - 2 : digit_start].upper() == "FM":
        return True
    return False


def find_colloquial_cai_month_hits(text: str) -> List[Tuple[int, str]]:
    """
    返回 (自然月 1-12, 匹配到的原文片段)。
    仅当 CAI_MONTH_COLLOQUIAL_MEANS_NATURAL_MONTH 开启时扫描。
    """
    if not CAI_MONTH_COLLOQUIAL_MEANS_NATURAL_MONTH or not text:
        return []
    out: List[Tuple[int, str]] = []
    for m in _RE_N_CAI_MONTH.finditer(text):
        if _fm_prefix_at(text, m.start(1)):
            continue
        n = int(m.group(1))
        if 1 <= n <= 12:
            out.append((n, m.group(0).strip()))
    return out


def build_colloquial_cai_month_prompt_block(
    text: str, lang: str = "zh"
) -> Optional[str]:
    """
    供思考 / SQL 阶段追加到 prompt：说明术语问题 + 取数约定。

    无命中时返回 None。
    """
    hits = find_colloquial_cai_month_hits(text)
    if not hits:
        return None

    months = sorted({h[0] for h in hits})
    seen = set()
    uniq_phrases: List[str] = []
    for _m, phrase in hits:
        if phrase not in seen:
            seen.add(phrase)
            uniq_phrases.append(phrase)
    examples = "、".join(uniq_phrases)

    if lang == "en":
        ms = ", ".join(str(x) for x in months)
        return (
            "[Business wording vs. fiscal terminology — required]\n"
            f"The phrase(s) 「{examples}」 often colloquially mean **calendar month(s) {ms}**, "
            "which is **not** the same as the formal fiscal period label **FMk** (fiscal month tag) in this system.\n"
            "- Acknowledge briefly that the wording is loose/non-standard.\n"
            f"- For this query, resolve time using **Gregorian month {ms}** (natural-month fiscal weeks), "
            "not by mapping the spoken digit N to **FMN** unless the user explicitly wrote FM / fiscal period.\n"
            "- When calling calendar tools, prefer natural-month week lookup for those months."
        )

    ms_zh = "、".join(str(x) for x in months)
    return (
        "【业务用语与时间术语（必须在分析中向用户说明）】\n"
        f"用户表述中出现：「{examples}」。在口语里这常被用来指「公历 {ms_zh} 月」，"
        "与严格财务含义下的「财月 / 财期（如 FM10）」**不是同一概念**。\n"
        f"• 你须在分析中用一两句话说明：该说法在术语上不严谨，但本次已按业务习惯理解为「自然年 {ms_zh} 月」。\n"
        f"• **取数约定**：时间范围按「自然年 {ms_zh} 月」解析（对应自然月内的财周），"
        "**禁止**仅凭口语里的数字 N 就等价于数据库中的 **FMN 财期标签**（除非用户明确写出 FM、财期编号等）。\n"
        "• 需要查日历时，应对自然年、自然月使用按自然月划分的财周查询，而非直接按 FM 标签过滤。"
    )


def append_colloquial_notes_to_metadata(metadata: dict, user_question: str, lang: str = "zh") -> None:
    """将本模块生成的说明写入 context.metadata['time_language_notes']。"""
    block = build_colloquial_cai_month_prompt_block(user_question, lang=lang)
    if not block:
        return
    metadata.setdefault("time_language_notes", []).append(block)
