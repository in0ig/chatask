"""
SQL JoinGuard: 校验 SQL JOIN 是否满足 JoinPlanner 约束。
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

from sqlglot import exp, parse_one


@dataclass
class JoinGuardResult:
    is_valid: bool
    error_code: str = ""
    error_message: str = ""
    retryable: bool = True
    details: Dict[str, Any] = field(default_factory=dict)


class SQLJoinGuard:
    def validate_sql(
        self,
        sql: str,
        join_constraints: Dict[str, Any],
        db_type: Optional[str] = None,
    ) -> JoinGuardResult:
        if not join_constraints:
            return JoinGuardResult(True)

        try:
            parsed = parse_one(sql, read=self._to_sqlglot_dialect(db_type))
        except Exception as exc:
            return JoinGuardResult(
                is_valid=False,
                error_code="JOIN_GUARD_PARSE_ERROR",
                error_message=f"无法解析 SQL: {str(exc)}",
                retryable=True,
            )

        alias_map, tables_in_sql, cte_names = self._build_alias_map(parsed)
        derived_aliases = self._collect_derived_subquery_aliases(parsed)
        skip_edge_aliases = set(cte_names) | derived_aliases
        required_table_names = set(join_constraints.get("required_table_names", []) or [])
        if required_table_names:
            missing_tables = sorted(required_table_names - tables_in_sql)
            if missing_tables:
                return JoinGuardResult(
                    is_valid=False,
                    error_code="JOIN_GUARD_MISSING_REQUIRED_TABLES",
                    error_message=f"SQL 缺少必选表: {', '.join(missing_tables)}",
                    retryable=True,
                    details={"missing_tables": missing_tables},
                )

        mode = str(join_constraints.get("mode") or "strict")
        allowed_pairs = self._build_allowed_pairs(join_constraints, mode=mode)
        if not allowed_pairs:
            if mode == "inferred":
                return JoinGuardResult(
                    is_valid=False,
                    error_code="JOIN_GUARD_NO_INFERRED_CANDIDATES",
                    error_message="未找到可用的推断 JOIN 候选",
                    retryable=False,
                )
            return JoinGuardResult(True)

        invalid_join_pairs: List[str] = []
        for join in parsed.find_all(exp.Join):
            on_expr = join.args.get("on")
            if on_expr is None:
                continue
            pair_ok = self._join_condition_has_allowed_pair(
                on_expr=on_expr,
                alias_map=alias_map,
                allowed_pairs=allowed_pairs,
                skip_edge_aliases=skip_edge_aliases,
            )
            if not pair_ok:
                invalid_join_pairs.append(on_expr.sql())

        if invalid_join_pairs:
            return JoinGuardResult(
                is_valid=False,
                error_code="JOIN_GUARD_INVALID_EDGE",
                error_message="SQL 使用了未配置的 JOIN 条件",
                retryable=True,
                details={"invalid_join_conditions": invalid_join_pairs},
            )

        return JoinGuardResult(is_valid=True)

    @staticmethod
    def _to_sqlglot_dialect(db_type: Optional[str]) -> Optional[str]:
        normalized = str(db_type or "").strip().lower().replace(" ", "").replace("_", "")
        if normalized in {"sqlserver", "mssql"}:
            return "tsql"
        if normalized in {"postgresql", "postgres", "pgsql"}:
            return "postgres"
        if normalized in {"mysql"}:
            return "mysql"
        return None

    @staticmethod
    def _build_alias_map(parsed: exp.Expression) -> Tuple[Dict[str, str], Set[str], Set[str]]:
        alias_map: Dict[str, str] = {}
        tables: Set[str] = set()
        cte_names: Set[str] = set()

        for cte in parsed.find_all(exp.CTE):
            cte_alias = cte.alias_or_name
            if cte_alias:
                cte_names.add(str(cte_alias).strip("`\""))

        for table in parsed.find_all(exp.Table):
            table_name = table.name
            if not table_name:
                continue
            table_name = table_name.strip("`\"")
            alias = table.alias_or_name.strip("`\"") if table.alias_or_name else table_name
            alias_map[alias] = table_name
            alias_map[table_name] = table_name
            tables.add(table_name)
        return alias_map, tables, cte_names

    @staticmethod
    def _collect_derived_subquery_aliases(parsed: exp.Expression) -> Set[str]:
        """
        收集 FROM / JOIN 中「派生表」子查询的别名，例如 JOIN (SELECT ...) AS vw。
        与 WITH 的 CTE 一样：与派生表别名的等值连接视为内层已处理，不在最外层做 allowed_edges 硬匹配。
        """
        names: Set[str] = set()
        for sub in parsed.find_all(exp.Subquery):
            alias = sub.alias_or_name
            if alias:
                names.add(str(alias).strip("`\""))
        return names

    @staticmethod
    def _build_allowed_pairs(join_constraints: Dict[str, Any], mode: str = "strict") -> Set[frozenset]:
        allowed_pairs: Set[frozenset] = set()
        edges = join_constraints.get("allowed_edges", []) or []
        if mode == "inferred" and not edges:
            edges = join_constraints.get("inferred_candidates", []) or []

        for edge in edges:
            left = (
                str(edge.get("primary_table_name", "")).strip(),
                str(edge.get("primary_field_name", "")).strip(),
            )
            right = (
                str(edge.get("foreign_table_name", "")).strip(),
                str(edge.get("foreign_field_name", "")).strip(),
            )
            if left[0] and left[1] and right[0] and right[1]:
                allowed_pairs.add(frozenset((left, right)))
        return allowed_pairs

    @staticmethod
    def _join_condition_has_allowed_pair(
        on_expr: exp.Expression,
        alias_map: Dict[str, str],
        allowed_pairs: Set[frozenset],
        skip_edge_aliases: Set[str],
    ) -> bool:
        has_non_cte_eq = False
        for eq_expr in on_expr.find_all(exp.EQ):
            left_col = eq_expr.left
            right_col = eq_expr.right
            if not isinstance(left_col, exp.Column) or not isinstance(right_col, exp.Column):
                continue

            left = SQLJoinGuard._resolve_column(left_col, alias_map)
            right = SQLJoinGuard._resolve_column(right_col, alias_map)
            if not left or not right:
                continue

            left_skip = left[0] in skip_edge_aliases
            right_skip = right[0] in skip_edge_aliases
            if left_skip or right_skip:
                # CTE/派生表连接视为已在上游子查询处理，不做硬边校验
                continue

            has_non_cte_eq = True
            if frozenset((left, right)) in allowed_pairs:
                return True

        # 若 ON 条件中只有 CTE/派生表等值连接（或无等值连接），不在此处判失败
        if not has_non_cte_eq:
            return True
        return False

    @staticmethod
    def _resolve_column(column: exp.Column, alias_map: Dict[str, str]) -> Optional[Tuple[str, str]]:
        table = column.table
        name = column.name
        if not table or not name:
            return None
        table_name = alias_map.get(table.strip("`\""), table.strip("`\""))
        return table_name, name.strip("`\"")
