from src.services.query_decomposer import QueryDecomposer


def test_query_decomposer_splits_multi_intents():
    decomposer = QueryDecomposer()
    intents = decomposer.decompose("对比今年和去年华东地区销售金额，并看渠道差异")
    intent_types = {item.intent_type for item in intents}

    assert "full" in intent_types
    assert "time" in intent_types
    assert "metric" in intent_types
    assert "filter" in intent_types or "compare" in intent_types
