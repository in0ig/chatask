"""
阶段上下文契约校验器。
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List

from pydantic import ValidationError

from src.schemas.context_envelope_schema import ContextEnvelopeSchema


@dataclass
class StageValidationResult:
    is_valid: bool
    error_code: str = ""
    error_message: str = ""
    retryable: bool = False
    missing_fields: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)


class ContextContractValidator:
    """thinking / sql_generation 阶段契约校验。"""

    def validate_stage_context(self, stage: str, envelope_data: Dict[str, Any]) -> StageValidationResult:
        try:
            envelope = ContextEnvelopeSchema.model_validate(envelope_data)
        except ValidationError as exc:
            return StageValidationResult(
                is_valid=False,
                error_code="CTX_ENVELOPE_SCHEMA_INVALID",
                error_message="上下文契约结构不合法",
                retryable=True,
                details={"validation_errors": exc.errors()},
            )

        missing_fields: List[str] = []
        mode = str(envelope.join_constraints.mode or "strict")
        if not envelope.selected_tables:
            missing_fields.append("selected_tables")
        if not envelope.table_schemas:
            missing_fields.append("table_schemas")

        if stage == "thinking":
            if len(envelope.selected_tables) > 1:
                if mode == "strict" and not envelope.join_constraints.allowed_edges:
                    missing_fields.append("join_constraints.allowed_edges")
                if mode == "inferred" and not envelope.join_constraints.inferred_candidates:
                    missing_fields.append("join_constraints.inferred_candidates")
                if not envelope.join_constraints.connected_components:
                    missing_fields.append("join_constraints.connected_components")
        elif stage == "sql_generation":
            if len(envelope.selected_tables) > 1:
                if mode == "strict" and not envelope.join_constraints.allowed_edges:
                    missing_fields.append("join_constraints.allowed_edges")
                if mode == "inferred" and not envelope.join_constraints.inferred_candidates:
                    missing_fields.append("join_constraints.inferred_candidates")
            if not envelope.join_constraints.required_table_names:
                missing_fields.append("join_constraints.required_table_names")

        if missing_fields:
            return StageValidationResult(
                is_valid=False,
                error_code="CTX_STAGE_REQUIRED_FIELDS_MISSING",
                error_message=f"{stage} 阶段上下文缺失关键字段",
                retryable=True,
                missing_fields=missing_fields,
            )

        if (
            len(envelope.selected_tables) > 1
            and not envelope.join_constraints.connected
            and mode != "inferred"
        ):
            return StageValidationResult(
                is_valid=False,
                error_code="CTX_TABLE_RELATION_DISCONNECTED",
                error_message="多表未连通，请先配置表关联关系",
                retryable=False,
                details={
                    "connected_components": envelope.join_constraints.connected_components,
                    "recommended_paths": envelope.join_constraints.recommended_paths,
                },
            )

        if len(envelope.selected_tables) > 1 and mode == "inferred" and not envelope.join_constraints.inferred_candidates:
            return StageValidationResult(
                is_valid=False,
                error_code="CTX_INFERRED_CANDIDATES_EMPTY",
                error_message="当前未配置表关联，且系统无法推断可用关联，请先配置表关联",
                retryable=False,
            )

        return StageValidationResult(is_valid=True)
