from src.services.context_contract_validator import ContextContractValidator


def _base_envelope(stage: str):
    return {
        "stage": stage,
        "selected_tables": ["t_orders", "t_customers"],
        "table_schemas": [
            {
                "table_id": "t_orders",
                "table_name": "orders",
                "fields": [{"field_name": "customer_id", "data_type": "varchar"}],
            },
            {
                "table_id": "t_customers",
                "table_name": "customers",
                "fields": [{"field_name": "id", "data_type": "varchar"}],
            },
        ],
        "dictionary_mappings": [],
        "knowledge_hits": [],
        "join_constraints": {
            "connected": True,
            "connected_components": [["t_orders", "t_customers"]],
            "allowed_edges": [
                {
                    "primary_table_id": "t_orders",
                    "primary_table_name": "orders",
                    "primary_field_name": "customer_id",
                    "foreign_table_id": "t_customers",
                    "foreign_table_name": "customers",
                    "foreign_field_name": "id",
                    "join_type": "INNER",
                }
            ],
            "required_table_ids": ["t_orders", "t_customers"],
            "required_table_names": ["orders", "customers"],
            "recommended_paths": [["t_orders", "t_customers"]],
        },
        "time_policy": {"prefer_fiscal_period_filters": False, "resolved_ranges": []},
    }


def test_stage_contract_passes_with_complete_sql_generation_envelope():
    validator = ContextContractValidator()
    result = validator.validate_stage_context("sql_generation", _base_envelope("sql_generation"))
    assert result.is_valid is True


def test_stage_contract_blocks_disconnected_multi_table():
    validator = ContextContractValidator()
    envelope = _base_envelope("sql_generation")
    envelope["join_constraints"]["connected"] = False
    envelope["join_constraints"]["connected_components"] = [["t_orders"], ["t_customers"]]
    result = validator.validate_stage_context("sql_generation", envelope)

    assert result.is_valid is False
    assert result.error_code == "CTX_TABLE_RELATION_DISCONNECTED"
    assert result.retryable is False


def test_stage_contract_blocks_missing_required_fields():
    validator = ContextContractValidator()
    envelope = _base_envelope("thinking")
    envelope["join_constraints"]["allowed_edges"] = []
    result = validator.validate_stage_context("thinking", envelope)

    assert result.is_valid is False
    assert result.error_code == "CTX_STAGE_REQUIRED_FIELDS_MISSING"
    assert "join_constraints.allowed_edges" in result.missing_fields


def test_stage_contract_allows_inferred_mode_without_allowed_edges():
    validator = ContextContractValidator()
    envelope = _base_envelope("sql_generation")
    envelope["join_constraints"]["mode"] = "inferred"
    envelope["join_constraints"]["allowed_edges"] = []
    envelope["join_constraints"]["inferred_candidates"] = [
        {
            "primary_table_id": "t_orders",
            "primary_table_name": "orders",
            "primary_field_name": "customer_id",
            "foreign_table_id": "t_customers",
            "foreign_table_name": "customers",
            "foreign_field_name": "id",
            "score": 0.83,
            "reason": "id_pattern_match",
        }
    ]
    result = validator.validate_stage_context("sql_generation", envelope)
    assert result.is_valid is True
