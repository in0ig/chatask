"""
查询多点意图拆解器。
"""

import re
from dataclasses import dataclass
from typing import List


@dataclass
class QueryIntent:
    intent_type: str
    text: str


class QueryDecomposer:
    """将复杂问题拆成多个检索子意图。"""

    def decompose(self, user_question: str) -> List[QueryIntent]:
        question = (user_question or "").strip()
        if not question:
            return []

        intents: List[QueryIntent] = [QueryIntent(intent_type="full", text=question)]
        fragments = [seg.strip() for seg in re.split(r"[，,。；;、\n]", question) if seg.strip()]

        time_markers = {"今年", "去年", "本月", "上月", "季度", "周", "FY", "FW", "FM"}
        metric_markers = {"销售", "金额", "数量", "收入", "利润", "占比", "增长"}
        filter_markers = {"地区", "渠道", "品类", "客户", "状态", "类型"}
        compare_markers = {"对比", "同比", "环比", "增长", "下降", "差异"}

        for fragment in fragments:
            added = False
            if any(marker in fragment for marker in time_markers):
                intents.append(QueryIntent(intent_type="time", text=fragment))
                added = True
            if any(marker in fragment for marker in metric_markers):
                intents.append(QueryIntent(intent_type="metric", text=fragment))
                added = True
            if any(marker in fragment for marker in filter_markers):
                intents.append(QueryIntent(intent_type="filter", text=fragment))
                added = True
            if any(marker in fragment for marker in compare_markers):
                intents.append(QueryIntent(intent_type="compare", text=fragment))
                added = True
            if not added and len(fragment) >= 4:
                intents.append(QueryIntent(intent_type="subquery", text=fragment))

        # 去重（按文本）
        dedup: List[QueryIntent] = []
        seen = set()
        for intent in intents:
            key = (intent.intent_type, intent.text.lower())
            if key in seen:
                continue
            seen.add(key)
            dedup.append(intent)

        return dedup
