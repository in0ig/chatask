"""
上下文契约 Envelope Schema 定义。

用于 thinking / sql_generation 阶段前的结构化校验。
"""

from typing import Any, Dict, List, Literal

from pydantic import BaseModel, Field


class TableFieldSchema(BaseModel):
    field_name: str = Field(..., description="字段名")
    data_type: str = Field(default="", description="字段类型")
    description: str = Field(default="", description="字段描述")


class TableSchemaItem(BaseModel):
    table_id: str = Field(..., description="表ID")
    table_name: str = Field(..., description="物理表名")
    description: str = Field(default="", description="表描述")
    fields: List[TableFieldSchema] = Field(default_factory=list, description="字段列表")


class DictionaryMappingItem(BaseModel):
    table_id: str = Field(..., description="表ID")
    field_name: str = Field(..., description="字段名")
    dictionary_name: str = Field(default="", description="字典名称")
    items: List[Dict[str, Any]] = Field(default_factory=list, description="字典项")


class KnowledgeHitItem(BaseModel):
    source: str = Field(default="", description="知识来源")
    title: str = Field(default="", description="知识标题")
    score: float = Field(default=0.0, description="相关性分数")
    table_ids: List[str] = Field(default_factory=list, description="关联表")


class JoinEdgeItem(BaseModel):
    primary_table_id: str = Field(..., description="主表ID")
    primary_table_name: str = Field(..., description="主表名称")
    primary_field_name: str = Field(..., description="主表字段")
    foreign_table_id: str = Field(..., description="从表ID")
    foreign_table_name: str = Field(..., description="从表名称")
    foreign_field_name: str = Field(..., description="从表字段")
    join_type: str = Field(default="INNER", description="JOIN 类型")


class InferredJoinCandidateItem(BaseModel):
    primary_table_id: str = Field(..., description="主表ID")
    primary_table_name: str = Field(..., description="主表名称")
    primary_field_name: str = Field(..., description="主表字段")
    foreign_table_id: str = Field(..., description="从表ID")
    foreign_table_name: str = Field(..., description="从表名称")
    foreign_field_name: str = Field(..., description="从表字段")
    score: float = Field(default=0.0, description="推断置信度")
    reason: str = Field(default="", description="推断依据")
    join_type: str = Field(default="INNER", description="建议JOIN类型")


class JoinConstraintsSchema(BaseModel):
    mode: Literal["strict", "inferred"] = Field(default="strict", description="关系模式")
    connected: bool = Field(default=True, description="所选表是否连通")
    connected_components: List[List[str]] = Field(default_factory=list, description="连通分量")
    allowed_edges: List[JoinEdgeItem] = Field(default_factory=list, description="允许的关联边")
    inferred_candidates: List[InferredJoinCandidateItem] = Field(
        default_factory=list, description="推断候选关联边"
    )
    required_table_ids: List[str] = Field(default_factory=list, description="必须覆盖的表ID")
    required_table_names: List[str] = Field(default_factory=list, description="必须覆盖的表名")
    recommended_paths: List[List[str]] = Field(default_factory=list, description="建议连接路径")


class TimePolicySchema(BaseModel):
    prefer_fiscal_period_filters: bool = Field(default=False, description="是否优先财务期间口径")
    resolved_ranges: List[Dict[str, Any]] = Field(default_factory=list, description="预解析时间范围")


class ContextEnvelopeSchema(BaseModel):
    stage: Literal["thinking", "sql_generation"] = Field(..., description="阶段")
    selected_tables: List[str] = Field(default_factory=list, description="已选表ID")
    table_schemas: List[TableSchemaItem] = Field(default_factory=list, description="表结构信息")
    dictionary_mappings: List[DictionaryMappingItem] = Field(default_factory=list, description="字典映射")
    knowledge_hits: List[KnowledgeHitItem] = Field(default_factory=list, description="知识命中")
    join_constraints: JoinConstraintsSchema = Field(default_factory=JoinConstraintsSchema, description="JOIN 约束")
    time_policy: TimePolicySchema = Field(default_factory=TimePolicySchema, description="时间策略")
