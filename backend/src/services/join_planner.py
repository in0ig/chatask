"""
JoinPlanner: 基于表关联配置生成 JOIN 约束。
"""

from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Any, Dict, List, Set, Tuple

from sqlalchemy import or_
from sqlalchemy.orm import Session

from src.models.data_preparation_model import DataTable, TableField, TableRelation


@dataclass
class JoinPlanningResult:
    mode: str
    connected: bool
    connected_components: List[List[str]]
    allowed_edges: List[Dict[str, Any]]
    inferred_candidates: List[Dict[str, Any]]
    required_table_ids: List[str]
    required_table_names: List[str]
    recommended_paths: List[List[str]]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mode": self.mode,
            "connected": self.connected,
            "connected_components": self.connected_components,
            "allowed_edges": self.allowed_edges,
            "inferred_candidates": self.inferred_candidates,
            "required_table_ids": self.required_table_ids,
            "required_table_names": self.required_table_names,
            "recommended_paths": self.recommended_paths,
        }


class JoinPlanner:
    def __init__(self, db: Session):
        self.db = db

    def plan(self, selected_table_ids: List[str]) -> JoinPlanningResult:
        table_ids = [str(tid) for tid in selected_table_ids if str(tid).strip()]
        if not table_ids:
            return JoinPlanningResult("strict", True, [], [], [], [], [], [])

        tables = self.db.query(DataTable).filter(DataTable.id.in_(table_ids)).all()
        table_name_map = {str(t.id): t.table_name for t in tables}
        required_table_names = [table_name_map[tid] for tid in table_ids if tid in table_name_map]

        if len(table_ids) == 1:
            return JoinPlanningResult(
                mode="strict",
                connected=True,
                connected_components=[table_ids],
                allowed_edges=[],
                inferred_candidates=[],
                required_table_ids=table_ids,
                required_table_names=required_table_names,
                recommended_paths=[],
            )

        relations = (
            self.db.query(TableRelation)
            .filter(
                or_(
                    TableRelation.primary_table_id.in_(table_ids),
                    TableRelation.foreign_table_id.in_(table_ids),
                ),
                TableRelation.status == True,
            )
            .all()
        )

        selected_set = set(table_ids)
        adjacency: Dict[str, Set[str]] = defaultdict(set)
        allowed_edges: List[Dict[str, Any]] = []

        for rel in relations:
            primary_id = str(rel.primary_table_id)
            foreign_id = str(rel.foreign_table_id)
            if primary_id not in selected_set or foreign_id not in selected_set:
                continue

            primary_field = rel.primary_field.field_name if rel.primary_field else ""
            foreign_field = rel.foreign_field.field_name if rel.foreign_field else ""
            join_type = str(rel.join_type or "INNER").upper()

            allowed_edges.append(
                {
                    "primary_table_id": primary_id,
                    "primary_table_name": table_name_map.get(primary_id, primary_id),
                    "primary_field_name": primary_field,
                    "foreign_table_id": foreign_id,
                    "foreign_table_name": table_name_map.get(foreign_id, foreign_id),
                    "foreign_field_name": foreign_field,
                    "join_type": join_type,
                }
            )

            adjacency[primary_id].add(foreign_id)
            adjacency[foreign_id].add(primary_id)

        connected_components = self._connected_components(table_ids, adjacency)
        connected = len(connected_components) <= 1
        recommended_paths = self._recommended_paths(table_ids, adjacency)

        # 有显式配置关系：强约束模式，必须按配置走
        if allowed_edges:
            return JoinPlanningResult(
                mode="strict",
                connected=connected,
                connected_components=connected_components,
                allowed_edges=allowed_edges,
                inferred_candidates=[],
                required_table_ids=table_ids,
                required_table_names=required_table_names,
                recommended_paths=recommended_paths,
            )

        # 无显式配置关系：尝试推断候选 JOIN
        inferred_candidates = self._infer_join_candidates(table_ids, table_name_map)
        inferred_adjacency: Dict[str, Set[str]] = defaultdict(set)
        for cand in inferred_candidates:
            left = str(cand["primary_table_id"])
            right = str(cand["foreign_table_id"])
            inferred_adjacency[left].add(right)
            inferred_adjacency[right].add(left)
        inferred_components = self._connected_components(table_ids, inferred_adjacency)
        inferred_connected = len(inferred_components) <= 1
        inferred_paths = self._recommended_paths(table_ids, inferred_adjacency)

        return JoinPlanningResult(
            mode="inferred",
            connected=inferred_connected,
            connected_components=inferred_components,
            allowed_edges=[],
            inferred_candidates=inferred_candidates,
            required_table_ids=table_ids,
            required_table_names=required_table_names,
            recommended_paths=inferred_paths,
        )

    def _infer_join_candidates(
        self, table_ids: List[str], table_name_map: Dict[str, str]
    ) -> List[Dict[str, Any]]:
        fields = (
            self.db.query(TableField)
            .filter(TableField.table_id.in_(table_ids), TableField.is_queryable == True)
            .all()
        )
        by_table: Dict[str, List[TableField]] = defaultdict(list)
        for field in fields:
            by_table[str(field.table_id)].append(field)

        candidates: List[Dict[str, Any]] = []
        for i in range(len(table_ids)):
            for j in range(i + 1, len(table_ids)):
                left_id = table_ids[i]
                right_id = table_ids[j]
                best = self._best_candidate_for_pair(
                    left_id=left_id,
                    right_id=right_id,
                    left_fields=by_table.get(left_id, []),
                    right_fields=by_table.get(right_id, []),
                    table_name_map=table_name_map,
                )
                if best:
                    candidates.append(best)
        return candidates

    def _best_candidate_for_pair(
        self,
        left_id: str,
        right_id: str,
        left_fields: List[TableField],
        right_fields: List[TableField],
        table_name_map: Dict[str, str],
    ) -> Dict[str, Any]:
        best_score = 0.0
        best_item: Dict[str, Any] = {}
        for lf in left_fields:
            for rf in right_fields:
                score, reason = self._score_field_pair(
                    left_name=str(lf.field_name or ""),
                    right_name=str(rf.field_name or ""),
                    left_type=str(lf.data_type or ""),
                    right_type=str(rf.data_type or ""),
                    left_dict=str(lf.dictionary_id or ""),
                    right_dict=str(rf.dictionary_id or ""),
                )
                if score > best_score:
                    best_score = score
                    best_item = {
                        "primary_table_id": left_id,
                        "primary_table_name": table_name_map.get(left_id, left_id),
                        "primary_field_name": str(lf.field_name or ""),
                        "foreign_table_id": right_id,
                        "foreign_table_name": table_name_map.get(right_id, right_id),
                        "foreign_field_name": str(rf.field_name or ""),
                        "score": round(score, 3),
                        "reason": reason,
                        "join_type": "INNER",
                    }

        # 最小阈值，避免胡乱连表
        if best_score >= 0.72:
            return best_item
        return {}

    @staticmethod
    def _score_field_pair(
        left_name: str,
        right_name: str,
        left_type: str,
        right_type: str,
        left_dict: str,
        right_dict: str,
    ) -> Tuple[float, str]:
        left_norm = left_name.strip().lower()
        right_norm = right_name.strip().lower()
        score = 0.0
        reasons: List[str] = []

        if left_norm and right_norm and left_norm == right_norm:
            score += 0.65
            reasons.append("field_name_exact_match")

        if left_norm.endswith("_id") and right_norm in {"id", left_norm}:
            score += 0.55
            reasons.append("id_pattern_match")
        if right_norm.endswith("_id") and left_norm in {"id", right_norm}:
            score += 0.55
            reasons.append("id_pattern_match")

        left_type_norm = left_type.strip().lower()
        right_type_norm = right_type.strip().lower()
        if left_type_norm and right_type_norm and left_type_norm == right_type_norm:
            score += 0.2
            reasons.append("data_type_match")

        if left_dict and right_dict and left_dict == right_dict:
            score += 0.35
            reasons.append("same_dictionary")

        return score, ",".join(reasons) or "weak_match"

    @staticmethod
    def _connected_components(table_ids: List[str], adjacency: Dict[str, Set[str]]) -> List[List[str]]:
        remaining = set(table_ids)
        components: List[List[str]] = []
        while remaining:
            start = next(iter(remaining))
            queue = deque([start])
            component: List[str] = []
            remaining.remove(start)
            while queue:
                node = queue.popleft()
                component.append(node)
                for nxt in adjacency.get(node, set()):
                    if nxt in remaining:
                        remaining.remove(nxt)
                        queue.append(nxt)
            components.append(component)
        return components

    @staticmethod
    def _recommended_paths(table_ids: List[str], adjacency: Dict[str, Set[str]]) -> List[List[str]]:
        if not table_ids:
            return []

        root = table_ids[0]
        paths: List[List[str]] = []
        for target in table_ids[1:]:
            path = JoinPlanner._shortest_path(root, target, adjacency)
            if path:
                paths.append(path)
        return paths

    @staticmethod
    def _shortest_path(start: str, end: str, adjacency: Dict[str, Set[str]]) -> List[str]:
        if start == end:
            return [start]

        queue = deque([(start, [start])])
        visited = {start}
        while queue:
            node, path = queue.popleft()
            for nxt in adjacency.get(node, set()):
                if nxt in visited:
                    continue
                if nxt == end:
                    return path + [nxt]
                visited.add(nxt)
                queue.append((nxt, path + [nxt]))
        return []
