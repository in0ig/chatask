"""
上下文重排器：对知识条目做相关性重排。
"""

import re
from typing import Any, Dict, List, Set


class ContextReranker:
    def rerank_knowledge(
        self,
        knowledge_items: List[Dict[str, Any]],
        selected_table_ids: List[str],
        user_question: str,
    ) -> List[Dict[str, Any]]:
        selected = set(str(t) for t in selected_table_ids if str(t).strip())
        keywords = self._extract_keywords(user_question)

        scored = []
        for item in knowledge_items:
            text = f"{item.get('knowledge_content', '')} {item.get('knowledge_type', '')}".lower()
            related_tables = set(str(t) for t in item.get("related_table_ids", []) if t)
            score = float(item.get("relevance_score", 0.0) or 0.0)

            if selected and related_tables.intersection(selected):
                score += 2.0
            if keywords:
                score += 0.3 * sum(1 for kw in keywords if kw in text)
            if item.get("scope") == "TABLE":
                score += 0.4

            new_item = dict(item)
            new_item["relevance_score"] = score
            scored.append(new_item)

        scored.sort(key=lambda x: x.get("relevance_score", 0.0), reverse=True)
        return scored

    @staticmethod
    def _extract_keywords(text: str) -> Set[str]:
        words = re.findall(r"[A-Za-z0-9_]+|[\u4e00-\u9fff]{2,}", (text or "").lower())
        stop_words = {"的", "是", "在", "和", "与", "the", "is", "in", "and", "or"}
        return {w for w in words if len(w) > 1 and w not in stop_words}
