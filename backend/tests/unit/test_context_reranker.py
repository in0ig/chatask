from src.services.context_reranker import ContextReranker


def test_context_reranker_prefers_table_related_items():
    reranker = ContextReranker()
    items = [
        {
            "knowledge_type": "TERM",
            "knowledge_content": "订单金额口径说明",
            "related_table_ids": ["t_orders"],
            "scope": "TABLE",
            "relevance_score": 0.5,
        },
        {
            "knowledge_type": "TERM",
            "knowledge_content": "通用报表说明",
            "related_table_ids": [],
            "scope": "GLOBAL",
            "relevance_score": 0.8,
        },
    ]
    result = reranker.rerank_knowledge(
        knowledge_items=items,
        selected_table_ids=["t_orders"],
        user_question="查询订单金额",
    )

    assert result[0]["knowledge_content"] == "订单金额口径说明"
