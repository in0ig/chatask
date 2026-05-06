"""
语义上下文聚合引擎

实现五模块元数据的智能聚合和相关性评分、动态上下文裁剪和优化算法、
按需加载的条件性模块注入、Token使用量的精确控制和预算管理。
"""

import json
import logging
import re
from typing import Dict, Any, List, Optional, Set, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import asyncio
from collections import defaultdict

from src.services.data_source_semantic_injection import DataSourceSemanticInjectionService
from src.services.table_structure_semantic_injection import TableStructureSemanticInjectionService
from src.services.table_relation_semantic_injection import TableRelationSemanticInjectionService
from src.services.semantic_injection_service import SemanticInjectionService
from src.services.knowledge_semantic_injection import KnowledgeSemanticInjectionService
from src.services.query_decomposer import QueryDecomposer
from src.services.context_reranker import ContextReranker

logger = logging.getLogger(__name__)


class ModuleType(str, Enum):
    """模块类型枚举"""
    DATA_SOURCE = "data_source"
    TABLE_STRUCTURE = "table_structure"
    TABLE_RELATION = "table_relation"
    DICTIONARY = "dictionary"
    KNOWLEDGE = "knowledge"


class ContextPriority(str, Enum):
    """上下文优先级枚举"""
    CRITICAL = "critical"    # 关键信息，必须包含
    HIGH = "high"           # 高优先级，优先包含
    MEDIUM = "medium"       # 中等优先级，空间允许时包含
    LOW = "low"            # 低优先级，最后考虑


@dataclass
class TokenBudget:
    """Token预算管理"""
    total_budget: int = 4000        # 总Token预算
    reserved_for_response: int = 1000  # 为响应预留的Token
    available_for_context: int = field(init=False)  # 可用于上下文的Token
    
    def __post_init__(self):
        self.available_for_context = self.total_budget - self.reserved_for_response


# 🔧 开发阶段：降低Token阈值以便测试摘要功能
DEV_MODE_TOKEN_THRESHOLD = 30  # 开发模式下的Token阈值


@dataclass
class SemanticModule:
    """语义模块信息"""
    module_type: ModuleType
    service: Any
    priority: ContextPriority
    estimated_tokens: int = 0
    relevance_score: float = 0.0
    is_loaded: bool = False
    content: Optional[Dict[str, Any]] = None


@dataclass
class AggregationContext:
    """聚合上下文"""
    user_question: str
    table_ids: Optional[List[str]] = None
    include_global: bool = True
    retrieval_profile: str = "normal"
    token_budget: TokenBudget = field(default_factory=TokenBudget)
    modules: List[SemanticModule] = field(default_factory=list)
    aggregated_content: Dict[str, Any] = field(default_factory=dict)
    total_tokens_used: int = 0


@dataclass
class AggregationResult:
    """聚合结果"""
    enhanced_context: str
    modules_used: List[str]
    total_tokens_used: int
    token_budget_remaining: int
    relevance_scores: Dict[str, float]
    optimization_summary: Dict[str, Any]
    aggregated_content: Dict[str, Any] = field(default_factory=dict)  # 🆕 添加原始聚合内容


class SemanticContextAggregator:
    """语义上下文聚合引擎"""
    
    def __init__(self, db_session=None):
        self.db = db_session
        
        # 初始化五个语义模块服务
        self.data_source_service = DataSourceSemanticInjectionService(db_session)
        self.table_structure_service = TableStructureSemanticInjectionService(db_session)
        self.table_relation_service = TableRelationSemanticInjectionService(db_session)
        self.dictionary_service = SemanticInjectionService()  # 不需要db_session参数
        self.knowledge_service = KnowledgeSemanticInjectionService(db_session)
        self.query_decomposer = QueryDecomposer()
        self.context_reranker = ContextReranker()
        self.retrieval_limits = {
            "normal": {
                "max_terms": 30,
                "max_logics": 20,
                "max_events": 10,
                "table_keep": 30,
                "global_keep": 10,
                "dictionary_keep": 30,
            },
            "expanded": {
                "max_terms": 80,
                "max_logics": 50,
                "max_events": 20,
                "table_keep": 60,
                "global_keep": 20,
                "dictionary_keep": 60,
            },
        }
        try:
            from src.config import get_config

            cfg = get_config()
            self.retrieval_limits = {
                "normal": {
                    "max_terms": int(cfg.retrieval_normal_max_terms),
                    "max_logics": int(cfg.retrieval_normal_max_logics),
                    "max_events": int(cfg.retrieval_normal_max_events),
                    "table_keep": int(cfg.retrieval_normal_table_keep),
                    "global_keep": int(cfg.retrieval_normal_global_keep),
                    "dictionary_keep": int(cfg.retrieval_normal_dictionary_keep),
                },
                "expanded": {
                    "max_terms": int(cfg.retrieval_expanded_max_terms),
                    "max_logics": int(cfg.retrieval_expanded_max_logics),
                    "max_events": int(cfg.retrieval_expanded_max_events),
                    "table_keep": int(cfg.retrieval_expanded_table_keep),
                    "global_keep": int(cfg.retrieval_expanded_global_keep),
                    "dictionary_keep": int(cfg.retrieval_expanded_dictionary_keep),
                },
            }
        except Exception as exc:
            logger.warning(f"加载召回阈值配置失败，使用默认值: {str(exc)}")
        
        # Token估算配置
        self.token_estimation_config = {
            ModuleType.DATA_SOURCE: {"base": 200, "per_source": 100},
            ModuleType.TABLE_STRUCTURE: {"base": 300, "per_table": 150},
            ModuleType.TABLE_RELATION: {"base": 250, "per_relation": 80},
            ModuleType.DICTIONARY: {"base": 400, "per_field": 50},
            ModuleType.KNOWLEDGE: {"base": 300, "per_item": 100}
        }
        
        # 缓存
        self.context_cache: Dict[str, AggregationResult] = {}
        self.relevance_cache: Dict[str, Dict[str, float]] = {}

    def _get_retrieval_limits(self, profile: str) -> Dict[str, int]:
        profile_key = "expanded" if profile == "expanded" else "normal"
        return self.retrieval_limits.get(profile_key, self.retrieval_limits["normal"])

    @staticmethod
    def _is_safe_identifier(name: str) -> bool:
        """仅允许字母/数字/下划线（可带 schema.table）的标识符。"""
        if not name:
            return False
        return bool(re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*)*", str(name).strip()))

    @staticmethod
    def _is_string_like_type(data_type: str) -> bool:
        normalized = str(data_type or "").strip().lower()
        return any(
            token in normalized
            for token in (
                "char", "text", "string", "enum", "set", "bool", "bit", "json"
            )
        )

    @staticmethod
    def _is_high_cardinality_or_temporal_field(field_name: str, data_type: str) -> bool:
        name = str(field_name or "").strip().lower()
        dt = str(data_type or "").strip().lower()
        high_card_keywords = ("id", "uuid", "guid", "date", "time", "timestamp", "created", "updated")
        if any(k in name for k in high_card_keywords):
            return True
        if any(k in dt for k in ("date", "time", "timestamp", "int", "bigint", "decimal", "float", "double", "numeric")):
            return True
        return False

    def _pick_enum_candidate_fields(self, fields: List[Any], user_question: str) -> List[Any]:
        """根据问题和字段特征，选择最可能需要枚举值感知的字段。"""
        question = str(user_question or "").lower()
        keyword_hits = (
            "是否", "工作日", "节假日", "类型", "类别", "状态", "标记", "holiday", "weekday",
            "type", "status", "flag", "category", "kind"
        )
        question_has_enum_intent = any(k in question for k in keyword_hits)

        scored_fields: List[Tuple[int, Any]] = []
        for field in fields:
            name = str(getattr(field, "field_name", "") or "")
            data_type = str(getattr(field, "data_type", "") or "")
            if not self._is_safe_identifier(name):
                continue
            if self._is_high_cardinality_or_temporal_field(name, data_type):
                continue
            if not self._is_string_like_type(data_type):
                continue

            score = 0
            lname = name.lower()
            if re.search(r"(^is_|_flag$|_type$|_status$|holiday|weekday|workday|category|kind|level)", lname):
                score += 3
            if question_has_enum_intent:
                score += 2
            if getattr(field, "dictionary_id", None):
                score -= 1  # 有字典时优先用字典，采样作为补充即可
            scored_fields.append((score, field))

        scored_fields.sort(key=lambda x: x[0], reverse=True)
        max_candidates = 6 if question_has_enum_intent else 3
        return [f for score, f in scored_fields[:max_candidates] if score > 0]

    async def _sample_distinct_values(
        self,
        sql_executor: Any,
        data_source_config: Dict[str, Any],
        table_name: str,
        field_name: str,
        sample_limit: int = 8
    ) -> List[str]:
        if not self._is_safe_identifier(table_name) or not self._is_safe_identifier(field_name):
            return []
        # 使用 GROUP BY + ORDER BY COUNT(*)，优先返回更常见的枚举值
        sql = (
            f"SELECT {field_name} AS sample_value "
            f"FROM {table_name} "
            f"WHERE {field_name} IS NOT NULL "
            f"GROUP BY {field_name} "
            f"ORDER BY COUNT(*) DESC "
            f"LIMIT {sample_limit}"
        )
        try:
            result = await sql_executor.execute_query(
                sql=sql,
                data_source_config=data_source_config,
                use_cache=True,
                stream=False
            )
            values: List[str] = []
            for row in result.rows or []:
                value = row[0] if isinstance(row, (list, tuple)) and row else row
                if value is None:
                    continue
                text = str(value).strip()
                if not text:
                    continue
                values.append(text)
            # 去重保序
            seen: Set[str] = set()
            unique_values = []
            for val in values:
                if val not in seen:
                    seen.add(val)
                    unique_values.append(val)
            return unique_values[:sample_limit]
        except Exception as exc:
            logger.info(f"字段值采样失败 {table_name}.{field_name}: {str(exc)}")
            return []

    async def _collect_field_value_samples(
        self,
        table: Any,
        fields: List[Any],
        user_question: str
    ) -> Dict[str, List[str]]:
        """按表采样候选字段的离散值，增强模型对实际取值的感知。"""
        if not self.db or not table or not fields:
            return {}

        table_name = str(getattr(table, "table_name", "") or "").strip()
        source_id = str(getattr(table, "data_source_id", "") or "").strip()
        if not table_name or not source_id or not self._is_safe_identifier(table_name):
            return {}

        from src.models.data_source_model import DataSource
        from src.utils.encryption import decrypt_password
        from src.services.sql_executor_service import SQLExecutorService, ExecutionConfig

        source = (
            self.db.query(DataSource)
            .filter(DataSource.id == source_id)
            .first()
        )
        if not source:
            return {}

        raw_db_type = str(source.db_type or "").strip().lower()
        db_type_mapping = {
            "mysql": "mysql",
            "sqlserver": "sqlserver",
            "sql server": "sqlserver",
            "sql_server": "sqlserver",
            "postgresql": "postgresql",
            "postgres": "postgresql",
        }
        normalized_db_type = db_type_mapping.get(raw_db_type, raw_db_type.replace(" ", "").replace("_", ""))

        data_source_config = {
            "type": normalized_db_type or "mysql",
            "host": source.host,
            "port": source.port,
            "database": source.database_name,
            "username": source.username,
            "password": decrypt_password(source.password) if source.password else "",
            "auth_type": source.auth_type,
            "domain": source.domain,
        }

        candidates = self._pick_enum_candidate_fields(fields, user_question)
        if not candidates:
            return {}

        executor = SQLExecutorService(
            config=ExecutionConfig(
                timeout_seconds=8,
                max_rows=200,
                max_concurrent_queries=2,
                enable_streaming=False,
            )
        )
        samples: Dict[str, List[str]] = {}
        for field in candidates:
            field_name = str(getattr(field, "field_name", "") or "").strip()
            if not field_name:
                continue
            values = await self._sample_distinct_values(
                sql_executor=executor,
                data_source_config=data_source_config,
                table_name=table_name,
                field_name=field_name,
                sample_limit=8,
            )
            if values:
                samples[field_name] = values
        return samples

    @staticmethod
    def _is_binary_value_set(values: List[str]) -> bool:
        normalized = {str(v).strip().upper() for v in (values or []) if str(v).strip()}
        binary_sets = (
            {"Y", "N"},
            {"1", "0"},
            {"TRUE", "FALSE"},
            {"T", "F"},
            {"YES", "NO"},
        )
        return any(normalized.issubset(bs) and len(normalized) >= 2 for bs in binary_sets)

    @staticmethod
    def _build_field_semantic_hints(fields: List[Any], field_value_samples: Dict[str, List[str]]) -> List[str]:
        """
        基于字段描述与值样本生成通用判定提示（非表定制）。
        目标：让模型优先按枚举值精确比较，避免用 IS NOT NULL / != '' 误判类别。
        """
        hints: List[str] = []
        for field in fields or []:
            field_name = str(getattr(field, "field_name", "") or "").strip()
            if not field_name:
                continue
            samples = (field_value_samples or {}).get(field_name, [])
            if not samples:
                continue

            upper_samples = [str(v).strip().upper() for v in samples if str(v).strip()]
            lname = field_name.lower()
            desc = str(getattr(field, "description", "") or "")

            if SemanticContextAggregator._is_binary_value_set(samples):
                hint = (
                    f"- 字段 `{field_name}` 为二值标记，值样本={samples}。"
                    f"分类判断必须使用等值比较（如 `{field_name}='Y'` / `{field_name}='N'`），"
                    "禁止使用 `IS NOT NULL`、`!= ''`、`<> ''` 代表某一类别。"
                )
                if "holiday" in lname or "节假日" in desc:
                    hint += f" 若业务含义为节假日，请优先按 `{field_name}='Y'` 判定节假日。"
                if "weekday" in lname or "workday" in lname or "工作日" in desc:
                    hint += f" 若业务含义为工作日，请优先按 `{field_name}='Y'` 判定工作日。"
                hints.append(hint)
                continue

            # 低基数枚举字段通用规则
            if len(samples) <= 10:
                hints.append(
                    f"- 字段 `{field_name}` 为低基数枚举，值样本={samples}。"
                    "筛选时必须使用 `=` 或 `IN (...)` 的显式枚举值，禁止用非空判断代替类别判断。"
                )

        return hints

    @staticmethod
    def _infer_table_granularity(table_name: str) -> str:
        name = (table_name or "").lower()
        if name == "survey_attendance_mock":
            return "财务周粒度（每个财周在客群维度上有多行明细）"
        if name == "fiscal_calendar_holidays":
            return "自然日粒度（每日一行，包含财周/财月映射）"
        if name == "park_seasonal_campaign":
            return "活动区间粒度（每个活动一行，含开始/结束日期）"
        return "未标注"
    
    async def aggregate_semantic_context(
        self,
        user_question: str,
        table_ids: Optional[List[str]] = None,
        include_global: bool = True,
        retrieval_profile: str = "normal",
        token_budget: Optional[TokenBudget] = None,
        module_priorities: Optional[Dict[ModuleType, ContextPriority]] = None
    ) -> AggregationResult:
        """
        聚合语义上下文
        
        Args:
            user_question: 用户问题
            table_ids: 相关表ID列表
            include_global: 是否包含全局知识
            token_budget: Token预算
            module_priorities: 模块优先级配置
            
        Returns:
            聚合结果
        """
        try:
            logger.info("=" * 80)
            logger.info("🔍 开始语义上下文聚合")
            logger.info(f"📝 用户问题: {user_question[:100]}{'...' if len(user_question) > 100 else ''}")
            logger.info(f"📋 选定的表: {table_ids if table_ids else '无'}")
            logger.info(f"🌐 包含全局知识: {include_global}")
            logger.info("=" * 80)
            
            # 创建聚合上下文
            context = AggregationContext(
                user_question=user_question,
                table_ids=table_ids,
                include_global=include_global,
                retrieval_profile=retrieval_profile,
                token_budget=token_budget or TokenBudget()
            )
            
            logger.info(f"💰 Token预算: {context.token_budget.available_for_context}")
            
            # 1. 初始化语义模块
            await self._initialize_semantic_modules(context, module_priorities)
            
            # 2. 计算模块相关性评分
            await self._calculate_module_relevance(context)
            
            # 3. 动态上下文裁剪和优化
            await self._optimize_context_selection(context)
            
            # 4. 按需加载选中的模块
            await self._load_selected_modules(context)
            
            # 5. 生成最终的聚合上下文
            enhanced_context = await self._generate_aggregated_context(context)
            
            # 6. 生成优化摘要
            optimization_summary = self._generate_optimization_summary(context)
            
            result = AggregationResult(
                enhanced_context=enhanced_context,
                modules_used=[m.module_type.value for m in context.modules if m.is_loaded],
                total_tokens_used=context.total_tokens_used,
                token_budget_remaining=context.token_budget.available_for_context - context.total_tokens_used,
                relevance_scores={m.module_type.value: m.relevance_score for m in context.modules},
                optimization_summary=optimization_summary,
                aggregated_content=context.aggregated_content  # 🆕 包含原始聚合内容
            )
            
            logger.info("=" * 80)
            logger.info("✅ 语义上下文聚合完成")
            logger.info(f"📊 使用的模块: {result.modules_used}")
            logger.info(f"📊 Token使用量: {result.total_tokens_used}")
            logger.info(f"📊 剩余Token: {result.token_budget_remaining}")
            logger.info(f"📊 相关性评分: {result.relevance_scores}")
            logger.info("=" * 80)
            logger.info("📝 完整语义上下文:")
            logger.info(enhanced_context)
            logger.info("=" * 80)
            
            return result
            
        except Exception as e:
            logger.error("=" * 80)
            logger.error(f"❌ 语义上下文聚合失败: {str(e)}", exc_info=True)
            logger.error("=" * 80)
            # 返回基础上下文
            return AggregationResult(
                enhanced_context=f"用户问题: {user_question}",
                modules_used=[],
                total_tokens_used=0,
                token_budget_remaining=token_budget.available_for_context if token_budget else 3000,
                relevance_scores={},
                optimization_summary={"error": str(e)}
            )
    
    async def _initialize_semantic_modules(
        self,
        context: AggregationContext,
        module_priorities: Optional[Dict[ModuleType, ContextPriority]] = None
    ):
        """初始化语义模块"""
        logger.info("=" * 80)
        logger.info("🔧 开始初始化语义模块")
        
        default_priorities = {
            ModuleType.TABLE_STRUCTURE: ContextPriority.CRITICAL,
            ModuleType.DICTIONARY: ContextPriority.HIGH,
            ModuleType.DATA_SOURCE: ContextPriority.HIGH,
            ModuleType.TABLE_RELATION: ContextPriority.MEDIUM,
            ModuleType.KNOWLEDGE: ContextPriority.MEDIUM
        }
        
        priorities = module_priorities or default_priorities
        
        # 验证所有服务是否正确初始化
        logger.info("📋 验证语义服务初始化状态:")
        logger.info(f"  ✓ DataSourceSemanticInjectionService: {self.data_source_service is not None}")
        logger.info(f"  ✓ TableStructureSemanticInjectionService: {self.table_structure_service is not None}")
        logger.info(f"  ✓ TableRelationSemanticInjectionService: {self.table_relation_service is not None}")
        logger.info(f"  ✓ SemanticInjectionService (Dictionary): {self.dictionary_service is not None}")
        logger.info(f"  ✓ KnowledgeSemanticInjectionService: {self.knowledge_service is not None}")
        
        # 创建语义模块
        modules = [
            SemanticModule(
                module_type=ModuleType.DATA_SOURCE,
                service=self.data_source_service,
                priority=priorities.get(ModuleType.DATA_SOURCE, ContextPriority.MEDIUM)
            ),
            SemanticModule(
                module_type=ModuleType.TABLE_STRUCTURE,
                service=self.table_structure_service,
                priority=priorities.get(ModuleType.TABLE_STRUCTURE, ContextPriority.CRITICAL)
            ),
            SemanticModule(
                module_type=ModuleType.TABLE_RELATION,
                service=self.table_relation_service,
                priority=priorities.get(ModuleType.TABLE_RELATION, ContextPriority.MEDIUM)
            ),
            SemanticModule(
                module_type=ModuleType.DICTIONARY,
                service=self.dictionary_service,
                priority=priorities.get(ModuleType.DICTIONARY, ContextPriority.HIGH)
            ),
            SemanticModule(
                module_type=ModuleType.KNOWLEDGE,
                service=self.knowledge_service,
                priority=priorities.get(ModuleType.KNOWLEDGE, ContextPriority.MEDIUM)
            )
        ]
        
        context.modules = modules
        
        # 详细记录每个模块的初始化信息
        logger.info(f"📦 成功创建 {len(modules)} 个语义模块:")
        for i, module in enumerate(modules, 1):
            logger.info(f"  {i}. {module.module_type.value}")
            logger.info(f"     - 优先级: {module.priority.value}")
            logger.info(f"     - 服务类型: {type(module.service).__name__}")
            logger.info(f"     - 服务状态: {'已初始化' if module.service else '未初始化'}")
        
        logger.info("✅ 语义模块初始化完成")
        logger.info("=" * 80)
    
    async def _calculate_module_relevance(self, context: AggregationContext):
        """计算模块相关性评分"""
        try:
            # 提取问题关键词
            keywords = self._extract_keywords(context.user_question)
            
            for module in context.modules:
                # 基于模块类型和问题内容计算相关性
                relevance_score = await self._calculate_relevance_for_module(
                    module, keywords, context
                )
                module.relevance_score = relevance_score
                
                # 估算Token使用量
                estimated_tokens = self._estimate_module_tokens(module, context)
                module.estimated_tokens = estimated_tokens
                
                logger.debug(f"模块 {module.module_type.value} 相关性: {relevance_score:.2f}, 估算Token: {estimated_tokens}")
                
        except Exception as e:
            logger.error(f"计算模块相关性失败: {str(e)}", exc_info=True)
    
    async def _calculate_relevance_for_module(
        self,
        module: SemanticModule,
        keywords: Set[str],
        context: AggregationContext
    ) -> float:
        """计算单个模块的相关性评分"""
        base_score = 0.0
        
        # 基于模块类型的基础评分
        type_scores = {
            ModuleType.TABLE_STRUCTURE: 0.9,  # 表结构几乎总是需要的
            ModuleType.DICTIONARY: 0.8,       # 数据字典很重要
            ModuleType.DATA_SOURCE: 0.7,      # 数据源信息重要
            ModuleType.TABLE_RELATION: 0.6,   # 表关联中等重要
            ModuleType.KNOWLEDGE: 0.5          # 知识库依情况而定
        }
        
        base_score = type_scores.get(module.module_type, 0.5)
        
        # 基于关键词匹配的评分调整
        keyword_bonus = 0.0
        
        if module.module_type == ModuleType.TABLE_STRUCTURE:
            # 表结构相关关键词
            structure_keywords = {'表', '字段', '列', '结构', 'table', 'column', 'field'}
            keyword_bonus = len(keywords.intersection(structure_keywords)) * 0.1
            
        elif module.module_type == ModuleType.DICTIONARY:
            # 数据字典相关关键词
            dict_keywords = {'含义', '业务', '字典', '映射', 'meaning', 'business', 'dictionary'}
            keyword_bonus = len(keywords.intersection(dict_keywords)) * 0.1
            
        elif module.module_type == ModuleType.TABLE_RELATION:
            # 表关联相关关键词
            relation_keywords = {'关联', '连接', '关系', 'join', 'relation', 'link'}
            keyword_bonus = len(keywords.intersection(relation_keywords)) * 0.15
            
        elif module.module_type == ModuleType.KNOWLEDGE:
            # 知识库相关关键词
            knowledge_keywords = {'规则', '逻辑', '术语', '事件', 'rule', 'logic', 'term', 'event'}
            keyword_bonus = len(keywords.intersection(knowledge_keywords)) * 0.2
        
        # 基于表ID的相关性调整
        table_bonus = 0.0
        if context.table_ids:
            if module.module_type in [ModuleType.TABLE_STRUCTURE, ModuleType.DICTIONARY, ModuleType.TABLE_RELATION]:
                table_bonus = 0.2  # 有具体表时，这些模块更重要
        
        final_score = min(1.0, base_score + keyword_bonus + table_bonus)
        return final_score
    
    def _estimate_module_tokens(self, module: SemanticModule, context: AggregationContext) -> int:
        """估算模块Token使用量"""
        config = self.token_estimation_config.get(module.module_type, {"base": 200, "per_item": 50})
        base_tokens = config["base"]
        
        # 🔧 开发模式：使用较小的Token估算以便触发摘要
        # 在生产环境中应该移除这个调整
        base_tokens = max(10, base_tokens // 10)  # 降低到原来的1/10
        
        # 基于上下文估算额外Token
        extra_tokens = 0
        
        if module.module_type == ModuleType.TABLE_STRUCTURE and context.table_ids:
            extra_tokens = len(context.table_ids) * config.get("per_table", 150) // 10
        elif module.module_type == ModuleType.DICTIONARY and context.table_ids:
            # 假设每个表平均有10个字段
            estimated_fields = len(context.table_ids) * 10
            extra_tokens = estimated_fields * config.get("per_field", 50) // 10
        elif module.module_type == ModuleType.TABLE_RELATION and context.table_ids:
            # 假设表之间有一些关联
            estimated_relations = max(0, len(context.table_ids) - 1) * 2
            extra_tokens = estimated_relations * config.get("per_relation", 80) // 10
        elif module.module_type == ModuleType.KNOWLEDGE:
            # 基于问题长度估算知识项数量
            estimated_items = min(10, len(context.user_question.split()) // 3)
            extra_tokens = estimated_items * config.get("per_item", 100) // 10
        
        estimated = base_tokens + extra_tokens
        logger.debug(f"📊 模块 {module.module_type.value} Token估算: {estimated} (基础: {base_tokens}, 额外: {extra_tokens})")
        return estimated
    
    async def _optimize_context_selection(self, context: AggregationContext):
        """动态上下文裁剪和优化"""
        try:
            logger.info("=" * 80)
            logger.info("🎯 开始上下文优化选择")
            logger.info(f"💰 可用Token预算: {context.token_budget.available_for_context}")
            
            # 按优先级和相关性排序模块
            context.modules.sort(
                key=lambda m: (
                    self._get_priority_weight(m.priority),
                    m.relevance_score
                ),
                reverse=True
            )
            
            logger.info("📋 模块排序结果（按优先级和相关性）:")
            for i, module in enumerate(context.modules, 1):
                logger.info(f"   {i}. {module.module_type.value}")
                logger.info(f"      - 优先级: {module.priority.value} (权重: {self._get_priority_weight(module.priority)})")
                logger.info(f"      - 相关性: {module.relevance_score:.3f}")
                logger.info(f"      - 估算Token: {module.estimated_tokens}")
            
            # 贪心算法选择模块，在Token预算内最大化价值
            selected_modules = []
            remaining_budget = context.token_budget.available_for_context
            
            logger.info("=" * 80)
            logger.info("🔍 开始模块选择（CRITICAL优先级）:")
            
            # 首先处理CRITICAL模块
            critical_modules = [m for m in context.modules if m.priority == ContextPriority.CRITICAL]
            for module in critical_modules:
                logger.info(f"   📦 处理CRITICAL模块: {module.module_type.value}")
                logger.info(f"      - 需要Token: {module.estimated_tokens}")
                logger.info(f"      - 剩余预算: {remaining_budget}")
                
                if remaining_budget >= module.estimated_tokens:
                    selected_modules.append(module)
                    remaining_budget -= module.estimated_tokens
                    logger.info(f"      ✅ 已选中，剩余预算: {remaining_budget}")
                else:
                    logger.warning(f"      ❌ 预算不足被跳过")
            
            logger.info("=" * 80)
            logger.info("🔍 开始模块选择（HIGH优先级）:")
            
            # 然后处理HIGH优先级模块（dictionary和data_source）
            # 这些模块对SQL生成至关重要，应该总是包含
            high_priority_modules = [m for m in context.modules if m.priority == ContextPriority.HIGH]
            for module in high_priority_modules:
                logger.info(f"   📦 处理HIGH优先级模块: {module.module_type.value}")
                logger.info(f"      - 需要Token: {module.estimated_tokens}")
                logger.info(f"      - 剩余预算: {remaining_budget}")
                
                if remaining_budget >= module.estimated_tokens:
                    selected_modules.append(module)
                    remaining_budget -= module.estimated_tokens
                    logger.info(f"      ✅ 已选中（HIGH优先级自动包含），剩余预算: {remaining_budget}")
                else:
                    logger.warning(f"      ⚠️ 预算不足，但HIGH优先级模块很重要")
                    # 即使预算紧张，也尝试包含HIGH优先级模块
                    if remaining_budget > 0:
                        selected_modules.append(module)
                        remaining_budget = max(0, remaining_budget - module.estimated_tokens)
                        logger.info(f"      ✅ 强制包含HIGH优先级模块，剩余预算: {remaining_budget}")
            
            logger.info("=" * 80)
            logger.info("🔍 开始模块选择（MEDIUM/LOW优先级）:")
            
            # 最后处理其他模块，使用价值密度筛选
            other_modules = [m for m in context.modules if m.priority not in [ContextPriority.CRITICAL, ContextPriority.HIGH]]
            for module in other_modules:
                # 计算模块的价值密度（相关性/Token成本）
                if module.estimated_tokens > 0:
                    value_density = module.relevance_score / module.estimated_tokens
                else:
                    value_density = module.relevance_score
                
                logger.info(f"   📦 处理模块: {module.module_type.value}")
                logger.info(f"      - 优先级: {module.priority.value}")
                logger.info(f"      - 相关性: {module.relevance_score:.3f}")
                logger.info(f"      - 估算Token: {module.estimated_tokens}")
                logger.info(f"      - 价值密度: {value_density:.3f}")
                logger.info(f"      - 剩余预算: {remaining_budget}")
                
                # 对于MEDIUM/LOW优先级，使用更宽松的价值密度阈值
                # 降低阈值从0.3到0.01，以便在开发模式下也能包含这些模块
                value_density_threshold = 0.01
                
                if remaining_budget >= module.estimated_tokens and value_density > value_density_threshold:
                    selected_modules.append(module)
                    remaining_budget -= module.estimated_tokens
                    logger.info(f"      ✅ 已选中，剩余预算: {remaining_budget}")
                elif value_density <= value_density_threshold:
                    logger.info(f"      ❌ 价值密度过低被跳过 ({value_density:.3f} <= {value_density_threshold})")
                else:
                    logger.info(f"      ❌ 预算不足被跳过")
            
            # 更新模块选择状态
            for module in context.modules:
                module.is_loaded = module in selected_modules
            
            logger.info("=" * 80)
            logger.info(f"✅ 优化完成")
            logger.info(f"   - 选中模块数: {len(selected_modules)}")
            logger.info(f"   - 选中模块: {[m.module_type.value for m in selected_modules]}")
            logger.info(f"   - 剩余预算: {remaining_budget}")
            logger.info("=" * 80)
            
        except Exception as e:
            logger.error(f"上下文优化失败: {str(e)}", exc_info=True)
    
    def _get_priority_weight(self, priority: ContextPriority) -> int:
        """获取优先级权重"""
        weights = {
            ContextPriority.CRITICAL: 4,
            ContextPriority.HIGH: 3,
            ContextPriority.MEDIUM: 2,
            ContextPriority.LOW: 1
        }
        return weights.get(priority, 1)
    
    async def _load_selected_modules(self, context: AggregationContext):
        """按需加载选中的模块"""
        try:
            logger.info("=" * 80)
            logger.info("📥 开始加载选中的语义模块")
            
            loaded_count = 0
            skipped_count = 0
            
            for module in context.modules:
                if not module.is_loaded:
                    skipped_count += 1
                    logger.debug(f"⏭️  跳过模块: {module.module_type.value} (未被选中)")
                    continue
                
                logger.info(f"📦 加载模块: {module.module_type.value}")
                logger.info(f"   - 优先级: {module.priority.value}")
                logger.info(f"   - 相关性评分: {module.relevance_score:.3f}")
                logger.info(f"   - 估算Token: {module.estimated_tokens}")
                
                # 根据模块类型调用相应的服务
                if module.module_type == ModuleType.DATA_SOURCE:
                    content = await self._load_data_source_content(context)
                elif module.module_type == ModuleType.TABLE_STRUCTURE:
                    content = await self._load_table_structure_content(context)
                elif module.module_type == ModuleType.TABLE_RELATION:
                    content = await self._load_table_relation_content(context)
                elif module.module_type == ModuleType.DICTIONARY:
                    content = await self._load_dictionary_content(context)
                elif module.module_type == ModuleType.KNOWLEDGE:
                    content = await self._load_knowledge_content(context)
                else:
                    content = {}
                
                module.content = content
                context.aggregated_content[module.module_type.value] = content
                
                # 🔍 详细记录模块内容以便调试
                logger.info(f"   📋 模块内容详情:")
                logger.info(f"      - 内容键: {list(content.keys())}")
                logger.info(f"      - 内容是否为空: {not bool(content)}")
                if "content" in content:
                    content_str = str(content.get("content", ""))
                    logger.info(f"      - content字段长度: {len(content_str)}")
                    logger.info(f"      - content字段是否为空: {not bool(content_str)}")
                    if content_str:
                        logger.info(f"      - content字段前200字符: {content_str[:200]}")
                else:
                    logger.warning(f"      ⚠️ 模块 {module.module_type.value} 缺少 'content' 键!")
                
                # 更新实际Token使用量
                actual_tokens = self._calculate_actual_tokens(content)
                context.total_tokens_used += actual_tokens
                
                # 记录模块内容摘要
                content_preview = str(content.get("content", ""))[:200]
                if len(content_preview) == 200:
                    content_preview += "..."
                
                logger.info(f"   ✅ 模块加载完成")
                logger.info(f"   - 实际Token: {actual_tokens}")
                logger.info(f"   - 内容预览: {content_preview}")
                
                loaded_count += 1
            
            logger.info("=" * 80)
            logger.info(f"📊 模块加载统计:")
            logger.info(f"   - 已加载: {loaded_count} 个")
            logger.info(f"   - 已跳过: {skipped_count} 个")
            logger.info(f"   - 总Token使用: {context.total_tokens_used}")
            logger.info("=" * 80)
                
        except Exception as e:
            logger.error(f"❌ 模块加载失败: {str(e)}", exc_info=True)
    
    async def _load_data_source_content(self, context: AggregationContext) -> Dict[str, Any]:
        """加载数据源语义内容"""
        try:
            # 基于当前上下文中的表ID推断实际数据源类型，避免硬编码为 MySQL
            db_label = "未知类型"
            sql_dialect = {"note": "请根据当前数据源类型选择方言语法（MySQL/SQL Server）"}
            performance_tips = ["使用索引优化查询", "避免全表扫描"]

            if self.db and context.table_ids:
                from src.models.data_preparation_model import DataTable
                from src.models.data_source_model import DataSource

                table = (
                    self.db.query(DataTable)
                    .filter(DataTable.id == context.table_ids[0])
                    .first()
                )
                if table:
                    source = (
                        self.db.query(DataSource)
                        .filter(DataSource.id == table.data_source_id)
                        .first()
                    )
                    if source and source.db_type:
                        raw_type = str(source.db_type).strip().lower()
                        normalized = raw_type.replace("_", "").replace(" ", "")
                        if normalized == "sqlserver":
                            db_label = "SQL Server"
                            sql_dialect = {"top_syntax": "TOP {limit}"}
                            performance_tips = ["优先按 schema 过滤表范围", "避免对大表执行全量 COUNT(*)"]
                        elif normalized == "postgresql":
                            db_label = "PostgreSQL"
                            sql_dialect = {"limit_syntax": "LIMIT {limit}"}
                            performance_tips = ["合理使用索引与统计信息", "避免不必要的全表扫描"]

            return {
                "module_type": "data_source",
                "content": f"数据源语义信息：{db_label}数据库",
                "sql_dialect": sql_dialect,
                "performance_tips": performance_tips
            }
        except Exception as e:
            logger.error(f"加载数据源内容失败: {str(e)}")
            return {}
    
    async def _load_table_structure_content(self, context: AggregationContext) -> Dict[str, Any]:
        """加载表结构语义内容"""
        try:
            if not context.table_ids:
                return {}
            
            # 调用表结构语义注入服务获取完整的表结构信息
            from src.services.data_table_service import DataTableService
            
            if not self.db:
                logger.warning("数据库会话不存在，无法加载表结构")
                return {}
            
            table_service = DataTableService()
            tables_info = []
            
            for table_id in context.table_ids:
                try:
                    # 获取表信息
                    table = table_service.get_table_by_id(self.db, table_id)
                    if not table:
                        logger.warning(f"表 {table_id} 不存在")
                        continue
                    
                    # 获取表的字段信息
                    fields = table_service.get_table_columns(self.db, table_id)
                    field_value_samples = await self._collect_field_value_samples(
                        table=table,
                        fields=fields,
                        user_question=context.user_question
                    )
                    semantic_hints = self._build_field_semantic_hints(fields, field_value_samples)
                    
                    # 构建表结构描述
                    field_descriptions = []
                    for field in fields:
                        field_desc = f"  - {field.field_name} ({field.data_type})"
                        if field.is_primary_key:
                            field_desc += " [主键]"
                        if field.is_nullable == False:
                            field_desc += " [非空]"
                        if field.description:
                            field_desc += f" - {field.description}"
                        sampled_values = field_value_samples.get(field.field_name) if field_value_samples else None
                        if sampled_values:
                            sample_text = ", ".join(sampled_values[:8])
                            field_desc += f" [值样本: {sample_text}]"
                        field_descriptions.append(field_desc)
                    
                    table_info = {
                        "table_id": table_id,
                        "table_name": table.table_name,  # 使用实际的表名
                        "description": table.description or "",  # 表描述
                        "granularity": self._infer_table_granularity(table.table_name),
                        "fields": [f.field_name for f in fields],
                        "field_details": field_descriptions,
                        "field_value_samples": field_value_samples,
                        "semantic_hints": semantic_hints,
                    }
                    tables_info.append(table_info)
                    
                except Exception as e:
                    logger.warning(f"获取表 {table_id} 的字段信息失败: {str(e)}")
                    continue
            
            # 构建完整的表结构描述（包含表描述，帮助模型理解数据粒度和业务含义）
            structure_content = f"表结构信息（共 {len(tables_info)} 个表）：\n\n"
            for table_info in tables_info:
                structure_content += f"表名: {table_info['table_name']}\n"
                if table_info.get('description'):
                    structure_content += f"表描述: {table_info['description']}\n"
                if table_info.get('granularity'):
                    structure_content += f"分析粒度: {table_info['granularity']}\n"
                structure_content += "字段列表:\n"
                structure_content += "\n".join(table_info['field_details'])
                if table_info.get("semantic_hints"):
                    structure_content += "\n字段判定提示:\n"
                    structure_content += "\n".join(table_info["semantic_hints"])
                structure_content += "\n\n"

            structure_content += (
                "【跨粒度处理规则（必须遵守）】\n"
                "- 当周粒度事实表与日粒度维表关联时，先在日表筛选并去重到财周键（如 FY_N/FW_N），再回到周表取值。\n"
                "- 禁止直接将周粒度事实表按日期展开到日粒度后再聚合，否则会造成重复放大。\n"
                "- 当存在任何日期区间条件（活动/事件/自定义开始结束日）时，先将日期区间映射到财周集合，再与周粒度事实表关联。\n"
            )
            
            return {
                "module_type": "table_structure",
                "content": structure_content,
                "tables": tables_info,
                "table_count": len(tables_info)
            }
        except Exception as e:
            logger.error(f"加载表结构内容失败: {str(e)}")
            return {}
    
    async def _load_table_relation_content(self, context: AggregationContext) -> Dict[str, Any]:
        """加载表关联语义内容"""
        try:
            if not context.table_ids or len(context.table_ids) < 1:
                logger.info("没有指定table_ids或只有一个表，跳过表关联加载")
                return {}
            
            # 调用表关联语义注入服务
            from src.models.data_preparation_model import TableRelation
            from sqlalchemy import or_
            
            if not self.db:
                logger.warning("数据库会话不存在，无法加载表关联")
                return {}
            
            # 查询涉及这些表的所有关联关系
            # 注意：TableRelation使用primary_table_id和foreign_table_id
            relations = []
            for table_id in context.table_ids:
                # 查找以该表为主表或外键表的关联
                table_relations = self.db.query(TableRelation).filter(
                    or_(
                        TableRelation.primary_table_id == table_id,
                        TableRelation.foreign_table_id == table_id
                    ),
                    TableRelation.status == True
                ).all()
                
                logger.info(f"表 {table_id} 找到 {len(table_relations)} 个关联关系")
                
                for rel in table_relations:
                    # 获取字段名称
                    primary_field_name = rel.primary_field.field_name if rel.primary_field else "unknown"
                    foreign_field_name = rel.foreign_field.field_name if rel.foreign_field else "unknown"
                    
                    relation_info = {
                        "source_table": rel.primary_table_id,
                        "target_table": rel.foreign_table_id,
                        "source_field": primary_field_name,
                        "target_field": foreign_field_name,
                        "relation_type": "one_to_many",  # 默认类型
                        "join_type": rel.join_type or "INNER"
                    }
                    relations.append(relation_info)
            
            if not relations:
                logger.info("未找到任何表关联关系，返回空内容")
                return {}
            
            # 构建关联描述
            relation_content = f"表关联信息（共 {len(relations)} 个关联）：\n\n"
            for rel in relations:
                relation_content += f"- {rel['source_table']}.{rel['source_field']} "
                relation_content += f"{rel['join_type']} JOIN "
                relation_content += f"{rel['target_table']}.{rel['target_field']}\n"
                relation_content += f"  关联类型: {rel['relation_type']}\n\n"
            
            logger.info(f"成功构建表关联内容，长度: {len(relation_content)}")
            
            return {
                "module_type": "table_relation",
                "content": relation_content,
                "relations": relations,
                "relation_count": len(relations)
            }
        except Exception as e:
            logger.error(f"加载表关联内容失败: {str(e)}", exc_info=True)
            return {}
    
    @staticmethod
    def _format_dictionary_content(field_dict_info_list: List[Dict[str, Any]]) -> str:
        """
        将字段字典信息列表格式化为业务术语映射字符串。
        
        输出格式：
          ## 业务术语与字段映射（SQL生成时必须严格遵守）
          字段 <field_name> 的业务含义：
            业务术语: <key> → 过滤条件: <field_name> = '<key>'
            ...
            完整枚举值: <key>=<value>, ...
        """
        dict_content = "## 业务术语与字段映射（SQL生成时必须严格遵守）\n\n"
        
        from collections import defaultdict
        fields_by_table: Dict[str, List] = defaultdict(list)
        for field_dict_info in field_dict_info_list:
            fields_by_table[field_dict_info['table_id']].append(field_dict_info)
        
        for table_id, field_dicts in fields_by_table.items():
            dict_content += f"表: {table_id}\n"
            for field_dict_info in field_dicts:
                field_name = field_dict_info['field_name']
                dict_content += f"\n字段 {field_name} 的业务含义：\n"
                
                for item in field_dict_info['items'][:20]:
                    key = item['key']
                    dict_content += f"  业务术语: {key} → 过滤条件: {field_name} = '{key}'\n"
                
                if len(field_dict_info['items']) > 20:
                    dict_content += f"  ... 还有 {len(field_dict_info['items']) - 20} 个字典项\n"
                
                enum_values = ", ".join(
                    f"{item['key']}={item['value']}"
                    for item in field_dict_info['items'][:20]
                )
                dict_content += f"  完整枚举值: {enum_values}\n"
                dict_content += "\n"
        
        return dict_content

    async def _load_dictionary_content(self, context: AggregationContext) -> Dict[str, Any]:
        """加载数据字典语义内容（字段关联的字典及其字典项）"""
        try:
            if not context.table_ids:
                logger.info("没有指定table_ids，跳过数据字典加载")
                return {}
            
            if not self.db:
                logger.warning("数据库会话不存在，无法加载数据字典")
                return {}
            
            # 导入模型
            from src.models.data_preparation_model import TableField, Dictionary, DictionaryItem
            
            field_dict_info_list = []
            
            for table_id in context.table_ids:
                # 查询表的所有字段
                fields = self.db.query(TableField).filter(
                    TableField.table_id == table_id
                ).all()
                
                logger.info(f"表 {table_id} 找到 {len(fields)} 个字段")
                
                for field in fields:
                    # 只处理关联了字典的字段
                    if field.dictionary_id:
                        logger.info(f"  字段 {field.field_name} 关联了字典 {field.dictionary_id}")
                        
                        # 查询字典信息
                        dictionary = self.db.query(Dictionary).filter(
                            Dictionary.id == field.dictionary_id
                        ).first()
                        
                        if dictionary:
                            # 查询字典项
                            dict_items = self.db.query(DictionaryItem).filter(
                                DictionaryItem.dictionary_id == field.dictionary_id
                            ).all()
                            
                            logger.info(f"    字典 {dictionary.name} 有 {len(dict_items)} 个字典项")
                            
                            # 构建字典项列表
                            items_list = []
                            for item in dict_items:
                                items_list.append({
                                    "key": item.item_key,
                                    "value": item.item_value,
                                    "description": item.description if hasattr(item, 'description') else ""
                                })
                            
                            field_dict_info = {
                                "table_id": table_id,
                                "field_name": field.field_name,
                                "field_type": field.data_type,
                                "dictionary_id": field.dictionary_id,
                                "dictionary_name": dictionary.name,
                                "dictionary_code": dictionary.code,
                                "dictionary_type": dictionary.dict_type,  # 🔧 修正：使用 dict_type
                                "items": items_list,
                                "items_count": len(items_list)
                            }
                            field_dict_info_list.append(field_dict_info)
                        else:
                            logger.warning(f"    字典 {field.dictionary_id} 不存在")
            
            if not field_dict_info_list:
                logger.info("未找到任何字段关联的字典，返回空内容")
                return {}

            # C1: 仅保留问题相关字典，避免无关字典淹没上下文
            keep_limit = self._get_retrieval_limits(context.retrieval_profile)["dictionary_keep"]
            filtered_dict_items = self._filter_dictionary_by_query(
                user_question=context.user_question,
                field_dict_info_list=field_dict_info_list,
                keep_limit=keep_limit,
            )
            
            # 使用静态方法格式化字典内容
            dict_content = self._format_dictionary_content(filtered_dict_items)
            
            logger.info(f"成功构建数据字典内容，长度: {len(dict_content)}")
            
            return {
                "module_type": "dictionary",
                "content": dict_content,
                "field_dict_info_list": filtered_dict_items,
                "field_count": len(filtered_dict_items),
                "raw_field_count": len(field_dict_info_list),
            }
        except Exception as e:
            logger.error(f"加载数据字典内容失败: {str(e)}", exc_info=True)
            return {}
    
    async def _load_knowledge_content(self, context: AggregationContext) -> Dict[str, Any]:
        """加载知识库语义内容（区分全局知识和表级别知识）"""
        try:
            logger.info("=" * 80)
            logger.info("📚 开始加载知识库内容")
            logger.info(f"📝 用户问题: {context.user_question}")
            logger.info(f"📋 表 IDs: {context.table_ids}")
            logger.info(f"🌐 包含全局知识: {context.include_global}")
            logger.info("=" * 80)
            
            intents = self.query_decomposer.decompose(context.user_question)
            if not intents:
                intents = []
            intent_queries = [intent.text for intent in intents] or [context.user_question]
            logger.info(f"🧩 问题拆解为 {len(intent_queries)} 个检索点")

            merged_items: Dict[str, Dict[str, Any]] = {}
            limits = self._get_retrieval_limits(context.retrieval_profile)
            fetch_max_terms = limits["max_terms"]
            fetch_max_logics = limits["max_logics"]
            fetch_max_events = limits["max_events"]
            table_keep = limits["table_keep"]
            global_keep = limits["global_keep"]

            for intent_query in intent_queries:
                result = self.knowledge_service.inject_knowledge_semantics(
                    user_question=intent_query,
                    table_ids=context.table_ids,
                    include_global=context.include_global,
                    max_terms=fetch_max_terms,
                    max_logics=fetch_max_logics,
                    max_events=fetch_max_events,
                )

                for term in result.knowledge_info.terms:
                    item = {
                        "knowledge_type": "TERM",
                        "knowledge_content": f"{term.name}: {term.explanation}",
                        "related_table_ids": [term.table_id] if term.table_id else [],
                        "scope": term.scope,
                        "relevance_score": float(term.relevance_score),
                    }
                    key = f"TERM::{item['knowledge_content']}::{','.join(item['related_table_ids'])}"
                    if key not in merged_items or item["relevance_score"] > merged_items[key]["relevance_score"]:
                        merged_items[key] = item

                for logic in result.knowledge_info.logics:
                    item = {
                        "knowledge_type": "LOGIC",
                        "knowledge_content": logic.explanation,
                        "related_table_ids": [logic.table_id] if logic.table_id else [],
                        "scope": logic.scope,
                        "relevance_score": float(logic.relevance_score),
                    }
                    key = f"LOGIC::{item['knowledge_content']}::{','.join(item['related_table_ids'])}"
                    if key not in merged_items or item["relevance_score"] > merged_items[key]["relevance_score"]:
                        merged_items[key] = item

                for event in result.knowledge_info.events:
                    status = "进行中" if event.is_active else "已结束"
                    item = {
                        "knowledge_type": "EVENT",
                        "knowledge_content": f"[{status}] {event.explanation}",
                        "related_table_ids": [event.table_id] if event.table_id else [],
                        "scope": event.scope,
                        "relevance_score": float(event.relevance_score),
                    }
                    key = f"EVENT::{item['knowledge_content']}::{','.join(item['related_table_ids'])}"
                    if key not in merged_items or item["relevance_score"] > merged_items[key]["relevance_score"]:
                        merged_items[key] = item

            merged_list = list(merged_items.values())
            reranked = self.context_reranker.rerank_knowledge(
                knowledge_items=merged_list,
                selected_table_ids=context.table_ids or [],
                user_question=context.user_question,
            )

            selected_set = set(context.table_ids or [])
            table_knowledge = [
                item for item in reranked
                if item.get("related_table_ids")
                and any(tid in selected_set for tid in item.get("related_table_ids", []))
            ]
            global_knowledge = [item for item in reranked if not item.get("related_table_ids")]

            table_knowledge = table_knowledge[:table_keep]
            global_knowledge = global_knowledge[:global_keep]
            matched_knowledge = table_knowledge + global_knowledge

            knowledge_context = self._build_knowledge_context(table_knowledge, global_knowledge)
            logger.info("=" * 80)
            logger.info(
                f"✅ 知识库加载完成：总候选 {len(merged_list)}，重排后保留 {len(matched_knowledge)} "
                f"(表级 {len(table_knowledge)} / 全局 {len(global_knowledge)})"
            )
            logger.info("=" * 80)

            return {
                "module_type": "knowledge",
                "content": knowledge_context,
                "global_knowledge": global_knowledge,
                "table_knowledge": table_knowledge,
                "matched_knowledge": matched_knowledge,
                "knowledge_info": {
                    "global_count": len(global_knowledge),
                    "table_count": len(table_knowledge),
                    "candidate_count": len(merged_list),
                    "decomposed_intents": len(intent_queries),
                },
                "total_relevance_score": sum(float(item.get("relevance_score", 0.0)) for item in matched_knowledge),
            }
        except Exception as e:
            logger.error(f"加载知识库内容失败: {str(e)}", exc_info=True)
            return {
                "module_type": "knowledge",
                "content": "",
                "global_knowledge": [],
                "table_knowledge": [],
                "matched_knowledge": [],
            }

    def _filter_dictionary_by_query(
        self,
        user_question: str,
        field_dict_info_list: List[Dict[str, Any]],
        keep_limit: int = 30,
    ) -> List[Dict[str, Any]]:
        """按问题关键词过滤字典，降低无关字段噪音。"""
        if not field_dict_info_list:
            return []

        keywords = self._extract_keywords(user_question)
        if not keywords:
            return field_dict_info_list[:keep_limit]

        scored: List[Tuple[float, Dict[str, Any]]] = []
        for item in field_dict_info_list:
            field_name = str(item.get("field_name", "")).lower()
            dict_name = str(item.get("dictionary_name", "")).lower()
            score = 0.0

            for keyword in keywords:
                key = keyword.lower()
                if key in field_name:
                    score += 2.0
                if key in dict_name:
                    score += 1.2
                for dict_item in item.get("items", [])[:30]:
                    k = str(dict_item.get("key", "")).lower()
                    v = str(dict_item.get("value", "")).lower()
                    if key in k or key in v:
                        score += 0.2

            scored.append((score, item))

        scored.sort(key=lambda pair: pair[0], reverse=True)
        filtered = [item for score, item in scored if score > 0]
        if not filtered:
            filtered = [item for _, item in scored[:10]]
        return filtered[:keep_limit]

    @staticmethod
    def _build_knowledge_context(
        table_knowledge: List[Dict[str, Any]],
        global_knowledge: List[Dict[str, Any]],
    ) -> str:
        lines = ["知识库增强信息："]
        if table_knowledge:
            lines.append("\n表级知识（优先）：")
            for item in table_knowledge:
                lines.append(
                    f"- [{item.get('knowledge_type')}] {item.get('knowledge_content')}"
                )
        if global_knowledge:
            lines.append("\n全局知识（Top-K）：")
            for item in global_knowledge:
                lines.append(
                    f"- [{item.get('knowledge_type')}] {item.get('knowledge_content')}"
                )
        if len(lines) == 1:
            return ""
        return "\n".join(lines)
    
    def _calculate_actual_tokens(self, content: Dict[str, Any]) -> int:
        """计算实际Token使用量"""
        try:
            # 简单的Token估算：每4个字符约等于1个Token
            content_str = json.dumps(content, ensure_ascii=False)
            return len(content_str) // 4
        except Exception:
            return 0
    
    async def _generate_aggregated_context(self, context: AggregationContext) -> str:
        """生成最终的聚合上下文"""
        try:
            logger.info("=" * 80)
            logger.info("📝 开始生成最终聚合上下文")
            
            context_parts = [f"用户问题: {context.user_question}"]
            
            # 按优先级顺序添加模块内容
            sorted_modules = sorted(context.modules, key=lambda m: self._get_priority_weight(m.priority), reverse=True)
            
            logger.info(f"📋 处理 {len(sorted_modules)} 个模块（按优先级排序）:")
            
            for module in sorted_modules:
                logger.info(f"   🔍 检查模块: {module.module_type.value}")
                logger.info(f"      - is_loaded: {module.is_loaded}")
                logger.info(f"      - has content: {bool(module.content)}")
                
                if not module.is_loaded:
                    logger.info(f"      ⏭️  跳过（未加载）")
                    continue
                    
                if not module.content:
                    logger.warning(f"      ⚠️ 跳过（content为空）")
                    continue
                
                module_content = module.content.get("content", "")
                logger.info(f"      - content字段长度: {len(module_content) if module_content else 0}")
                
                if module_content:
                    module_title = module.module_type.value.replace('_', ' ').title()
                    context_parts.append(f"\n{module_title}:")
                    context_parts.append(module_content)
                    logger.info(f"      ✅ 已添加到聚合上下文")
                else:
                    logger.warning(f"      ⚠️ 跳过（content字段为空字符串）")
            
            final_context = "\n".join(context_parts)
            logger.info(f"📊 最终聚合上下文统计:")
            logger.info(f"   - 总长度: {len(final_context)} 字符")
            logger.info(f"   - 包含模块数: {len(context_parts) - 1}")  # 减去用户问题
            logger.info("=" * 80)
            
            return final_context
            
        except Exception as e:
            logger.error(f"生成聚合上下文失败: {str(e)}", exc_info=True)
            return f"用户问题: {context.user_question}"
    
    def _generate_optimization_summary(self, context: AggregationContext) -> Dict[str, Any]:
        """生成优化摘要"""
        return {
            "total_modules_available": len(context.modules),
            "modules_selected": len([m for m in context.modules if m.is_loaded]),
            "token_budget_used": context.total_tokens_used,
            "token_budget_total": context.token_budget.available_for_context,
            "token_utilization_rate": context.total_tokens_used / context.token_budget.available_for_context,
            "modules_by_priority": {
                priority.value: len([m for m in context.modules if m.priority == priority and m.is_loaded])
                for priority in ContextPriority
            },
            "average_relevance_score": sum(m.relevance_score for m in context.modules if m.is_loaded) / max(1, len([m for m in context.modules if m.is_loaded]))
        }
    
    def _extract_keywords(self, text: str) -> Set[str]:
        """提取文本关键词"""
        # 简单的关键词提取，支持中文分词
        import re
        
        # 对于中文文本，我们使用简单的字符级分割和常见词汇识别
        # 首先提取中文字符序列和英文单词
        chinese_chars = re.findall(r'[\u4e00-\u9fff]', text)
        english_words = re.findall(r'[a-zA-Z]+', text.lower())
        
        # 简单的中文词汇识别（基于常见词汇模式）
        chinese_text = ''.join(chinese_chars)
        chinese_keywords = set()
        
        # 常见的中文词汇模式
        common_words = ['查询', '用户', '表', '字段', '信息', '业务', '含义', '数据', '分析', '统计', '报表', '图表']
        for word in common_words:
            if word in chinese_text:
                chinese_keywords.add(word)
        
        # 合并中英文关键词
        keywords = chinese_keywords.union(set(english_words))
        
        # 过滤停用词
        stop_words = {'的', '是', '在', '有', '和', '与', '或', '但', '如果', '那么', '这', '那', '什么', '怎么', '为什么', 'the', 'is', 'in', 'and', 'or', 'but'}
        keywords = {word for word in keywords if len(word) > 1 and word not in stop_words}
        
        return keywords
    
    def clear_cache(self):
        """清空缓存"""
        self.context_cache.clear()
        self.relevance_cache.clear()
        logger.info("语义上下文聚合器缓存已清空")