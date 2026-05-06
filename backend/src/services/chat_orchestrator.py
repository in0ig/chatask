"""
对话流程编排引擎 - 左右互搏核心
实现"云端生成SQL → 本地执行 → 本地分析"的完整流水线
"""

import asyncio
import json
import logging
import re
import time
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from enum import Enum

from src.services.context_manager import ContextManager
from src.services.ai_model_service import AIModelService, get_ai_service
from src.services.semantic_context_aggregator import SemanticContextAggregator
from src.services.websocket_stream_service import get_websocket_stream_service, StreamMessageType
from src.services.sql_security_validator import SQLSecurityService
from src.services.prompt_manager import PromptManager, PromptType
from src.services.time_resolver import TimeResolver
from src.services.context_contract_validator import ContextContractValidator
from src.services.join_planner import JoinPlanner
from src.services.sql_join_guard import SQLJoinGuard
from src.services.sql_dialect_guard import SQLDialectGuard
from src.services.multi_table_metrics import get_multi_table_metrics
from src.database import get_db
from sqlalchemy.orm import Session
from src.utils.request_logger import request_logger  # 导入日志工具
from src.utils.logger import logger  # 🆕 使用配置好的 logger


class ChatStage(Enum):
    """对话阶段枚举"""
    INTENT_RECOGNITION = "intent_recognition"  # 意图识别
    TABLE_SELECTION = "table_selection"        # 智能选表
    INTENT_CLARIFICATION = "intent_clarification"  # 意图澄清
    THINKING = "thinking"                      # 模型思考
    SQL_GENERATION = "sql_generation"          # SQL生成（取数）
    SQL_EXECUTION = "sql_execution"            # SQL执行
    DATA_ANALYSIS = "data_analysis"            # 数据分析
    CHART_GENERATION = "chart_generation"      # 生成图表配置
    RESULT_DESCRIPTION = "result_description"  # 数据结果描述
    RESULT_PRESENTATION = "result_presentation"  # 结果展示
    ERROR_HANDLING = "error_handling"          # 错误处理
    COMPLETED = "completed"                    # 完成


class ChatIntent(Enum):
    """对话意图枚举"""
    SMART_QUERY = "smart_query"      # 智能问数
    REPORT_GENERATION = "report_generation"  # 生成报告
    DATA_FOLLOWUP = "data_followup"  # 数据追问
    CLARIFICATION = "clarification"  # 澄清确认
    UNKNOWN = "unknown"              # 未知意图


class ChatContext:
    """对话上下文"""
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.current_stage = ChatStage.INTENT_RECOGNITION
        self.intent = ChatIntent.UNKNOWN
        self.selected_tables: List[str] = []
        self.generated_sql: Optional[str] = None
        self.query_result: Optional[Dict[str, Any]] = None
        self.previous_data: List[Dict[str, Any]] = []
        self.error_count = 0
        self.retry_count = 0
        self.metadata: Dict[str, Any] = {}
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
    
    def update_stage(self, stage: ChatStage):
        """更新对话阶段"""
        self.current_stage = stage
        self.updated_at = datetime.now()
        logger.info(f"会话 {self.session_id} 进入阶段: {stage.value}")
    
    def add_error(self, error: str):
        """添加错误记录"""
        self.error_count += 1
        if 'errors' not in self.metadata:
            self.metadata['errors'] = []
        self.metadata['errors'].append({
            'error': error,
            'timestamp': datetime.now().isoformat(),
            'stage': self.current_stage.value
        })
    
    def add_previous_data(self, data: Dict[str, Any]):
        """添加历史数据用于对比分析"""
        self.previous_data.append({
            'data': data,
            'timestamp': datetime.now().isoformat(),
            'sql': self.generated_sql
        })
        # 保持最近5次查询结果
        if len(self.previous_data) > 5:
            self.previous_data = self.previous_data[-5:]


class ChatOrchestrator:
    """对话流程编排引擎"""
    
    def __init__(self):
        self.context_manager = ContextManager()
        
        # 尝试使用全局 AI 服务实例
        try:
            self.ai_service = get_ai_service()
            logger.info("ChatOrchestrator 使用全局 AI 服务实例")
        except RuntimeError:
            # 如果全局实例不存在，使用配置文件初始化
            logger.warning("全局 AI 服务未初始化，使用配置文件创建新实例")
            from src.config.ai_config import get_ai_config
            ai_config = get_ai_config()
            # AIConfig 对象有一个 config 属性包含实际的配置字典
            self.ai_service = AIModelService(ai_config.config)
        
        self.semantic_aggregator = SemanticContextAggregator()
        self.websocket_service = get_websocket_stream_service()
        self.sql_security = SQLSecurityService()
        self.context_contract_validator = ContextContractValidator()
        self.sql_join_guard = SQLJoinGuard()
        self.sql_dialect_guard = SQLDialectGuard()
        self.multi_table_metrics = get_multi_table_metrics()
        
        # 🆕 初始化 PromptManager
        self.prompt_manager = PromptManager()
        logger.info("✅ PromptManager 已初始化，加载了 {} 个模板".format(len(self.prompt_manager.templates)))
        
        # 🆕 初始化 TimeResolver
        self.time_resolver = TimeResolver()
        logger.info("✅ TimeResolver 已初始化")
        
        self.active_contexts: Dict[str, ChatContext] = {}
        self.max_retry_count = 3
        self.max_error_count = 5
        
        # 🆕 加载流式配置
        try:
            from src.config import get_config
            config = get_config()
            self.enable_streaming = config.enable_streaming
            self.streaming_timeout = config.streaming_timeout
            logger.info(f"✅ 流式配置已加载: enable_streaming={self.enable_streaming}, timeout={self.streaming_timeout}s")
        except Exception as e:
            logger.warning(f"⚠️ 加载流式配置失败，使用默认值: {str(e)}")
            self.enable_streaming = True
            self.streaming_timeout = 60

    def _normalize_db_type_for_prompt(self, raw_db_type: Optional[str]) -> str:
        """将数据库类型规范化为 Prompt 使用值。"""
        normalized = str(raw_db_type or "").strip().lower().replace(" ", "").replace("_", "")
        if normalized in ("mysql",):
            return "MySQL"
        if normalized in ("sqlserver", "mssql"):
            return "SQL Server"
        if normalized in ("postgresql", "postgres", "pgsql"):
            return "PostgreSQL"
        if raw_db_type:
            return str(raw_db_type).strip()
        return "MySQL"

    def _resolve_prompt_db_type(self, context: ChatContext, data_source_id: Optional[str]) -> str:
        """解析并缓存当前会话的数据库类型（用于各 stage prompt）。"""
        cached_db_type = context.metadata.get("prompt_db_type")
        if cached_db_type:
            return str(cached_db_type)

        if not data_source_id:
            context.metadata["prompt_db_type"] = "MySQL"
            return "MySQL"

        db = None
        try:
            from src.services.data_source_service import DataSourceService

            db = next(get_db())
            data_source = DataSourceService().get_source_by_id(db, str(data_source_id))
            prompt_db_type = self._normalize_db_type_for_prompt(data_source.db_type if data_source else None)
            context.metadata["prompt_db_type"] = prompt_db_type
            logger.info(f"✅ Prompt 数据库类型解析完成: {prompt_db_type}")
            return prompt_db_type
        except Exception as e:
            logger.warning(f"⚠️ 解析 Prompt 数据库类型失败，回退 MySQL: {str(e)}")
            context.metadata["prompt_db_type"] = "MySQL"
            return "MySQL"
        finally:
            if db is not None:
                try:
                    db.close()
                except Exception:
                    pass

    @staticmethod
    def _normalize_selected_table_ids(selected_tables: List[Any]) -> List[str]:
        table_ids: List[str] = []
        for table in selected_tables or []:
            if isinstance(table, dict):
                value = table.get("tableId") or table.get("id") or table.get("table_id")
            else:
                value = table
            if value is None:
                continue
            text = str(value).strip()
            if text:
                table_ids.append(text)
        return table_ids

    @staticmethod
    def _has_resolved_date_ranges(context: ChatContext) -> bool:
        """是否已由后端解析出可直接使用的日期区间。"""
        resolved_time_context = context.metadata.get("resolved_time_context")
        if not resolved_time_context:
            return False
        date_ranges = getattr(resolved_time_context, "date_ranges", None) or []
        if not date_ranges:
            return False
        for dr in date_ranges:
            if getattr(dr, "start_date", None) and getattr(dr, "end_date", None):
                return True
        return False

    def _relax_required_tables_for_resolved_time(
        self, context: ChatContext, join_constraints: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        当时间已被后端解析为明确日期区间时，放宽活动区间类表的必选约束。

        目标：避免 SQL 已使用权威日期范围却因未强制 JOIN 活动表被 JoinGuard 拦截。
        """
        if not join_constraints:
            return join_constraints
        if not self._has_resolved_date_ranges(context):
            return join_constraints

        required_names = list(join_constraints.get("required_table_names", []) or [])
        required_ids = list(join_constraints.get("required_table_ids", []) or [])
        if not required_names:
            return join_constraints

        removable_keywords = ("campaign", "activity", "event", "season")
        removable_indices = [
            idx for idx, table_name in enumerate(required_names)
            if any(k in str(table_name or "").lower() for k in removable_keywords)
        ]
        if not removable_indices:
            return join_constraints

        relaxed_constraints = dict(join_constraints)
        relaxed_constraints["required_table_names"] = [
            name for idx, name in enumerate(required_names) if idx not in set(removable_indices)
        ]
        if required_ids and len(required_ids) == len(required_names):
            relaxed_constraints["required_table_ids"] = [
                tid for idx, tid in enumerate(required_ids) if idx not in set(removable_indices)
            ]
        relaxed_constraints["required_table_relax_reason"] = "resolved_time_context_date_ranges"
        relaxed_constraints["required_table_relaxed_names"] = [
            name for idx, name in enumerate(required_names) if idx in set(removable_indices)
        ]
        logger.info(
            "⏰ 已放宽必选表约束（时间已解析）: removed=%s, kept=%s",
            relaxed_constraints.get("required_table_relaxed_names", []),
            relaxed_constraints.get("required_table_names", []),
        )
        return relaxed_constraints

    @staticmethod
    def _is_uncertain_fiscal_query(fiscal_query: Dict[str, Any]) -> bool:
        """
        判断 fiscalTimeQueries 是否包含“假设性”描述。

        这类查询不能作为权威时间来源注入 resolved_time_context，
        否则会把“仅年份+活动名”误收敛成某一固定月份/财周。
        """
        description = str(fiscal_query.get("description") or "").strip()
        if not description:
            return False
        uncertain_markers = (
            "假设",
            "需先查活动表确认",
            "待确认",
            "可能",
            "推测",
            "估计",
        )
        return any(marker in description for marker in uncertain_markers)

    def _get_or_build_join_constraints(self, context: ChatContext, table_ids: List[str]) -> Dict[str, Any]:
        cached = context.metadata.get("join_constraints")
        if isinstance(cached, dict) and cached.get("required_table_ids") == table_ids:
            return self._relax_required_tables_for_resolved_time(context, cached)

        if not table_ids:
            empty = {
                "mode": "strict",
                "connected": True,
                "connected_components": [],
                "allowed_edges": [],
                "inferred_candidates": [],
                "required_table_ids": [],
                "required_table_names": [],
                "recommended_paths": [],
            }
            context.metadata["join_constraints"] = empty
            return self._relax_required_tables_for_resolved_time(context, empty)

        db = next(get_db())
        try:
            planner = JoinPlanner(db)
            plan_result = planner.plan(table_ids).to_dict()
            context.metadata["join_constraints"] = plan_result
            return self._relax_required_tables_for_resolved_time(context, plan_result)
        finally:
            db.close()

    @staticmethod
    def _extract_binary_flag_fields(semantic_context_result: Any) -> List[str]:
        """
        从语义上下文提取二值标记字段（值域如 Y/N、1/0、T/F）。
        用于 SQL 语义守卫，防止把枚举分类写成非空判断。
        """
        aggregated = getattr(semantic_context_result, "aggregated_content", {}) or {}
        tables = (aggregated.get("table_structure") or {}).get("tables", []) or []
        binary_fields: List[str] = []
        binary_value_sets = (
            {"Y", "N"},
            {"1", "0"},
            {"TRUE", "FALSE"},
            {"T", "F"},
            {"YES", "NO"},
        )

        for table in tables:
            samples_map = table.get("field_value_samples", {}) if isinstance(table, dict) else {}
            if not isinstance(samples_map, dict):
                continue
            for field_name, values in samples_map.items():
                norm = {str(v).strip().upper() for v in (values or []) if str(v).strip()}
                if any(norm.issubset(vs) and len(norm) >= 2 for vs in binary_value_sets):
                    binary_fields.append(str(field_name))
        # 去重保序
        seen = set()
        ordered = []
        for field in binary_fields:
            key = field.lower()
            if key in seen:
                continue
            seen.add(key)
            ordered.append(field)
        return ordered

    def _validate_sql_enum_flag_predicates(self, sql: str, semantic_context_result: Any) -> Optional[str]:
        """
        通用语义守卫：
        对二值/枚举标记字段，禁止使用 IS NOT NULL 或 != '' 作为类别判断。
        """
        binary_fields = self._extract_binary_flag_fields(semantic_context_result)
        if not binary_fields:
            return None

        bad_patterns = []
        for field in binary_fields:
            # 匹配 field / alias.field / `field`
            field_expr = rf"(?:\b[a-zA-Z_][a-zA-Z0-9_]*\.)?`?{re.escape(field)}`?"
            non_null_pattern = rf"{field_expr}\s+IS\s+NOT\s+NULL"
            non_empty_pattern = rf"{field_expr}\s*(?:!=|<>)\s*''"
            if re.search(non_null_pattern, sql, flags=re.IGNORECASE):
                bad_patterns.append(f"{field}: IS NOT NULL")
            if re.search(non_empty_pattern, sql, flags=re.IGNORECASE):
                bad_patterns.append(f"{field}: != ''")

        if not bad_patterns:
            return None

        return (
            "枚举/二值字段使用了不安全分类条件（应使用显式枚举值等值判断）: "
            + "; ".join(bad_patterns)
        )

    @staticmethod
    def _extract_text_enum_samples(semantic_context_result: Any) -> Dict[str, List[str]]:
        """
        提取文本枚举字段的样本值（用于识别“等值误收敛”）。
        """
        aggregated = getattr(semantic_context_result, "aggregated_content", {}) or {}
        tables = (aggregated.get("table_structure") or {}).get("tables", []) or []
        samples_map: Dict[str, List[str]] = {}
        binary_sets = (
            {"Y", "N"},
            {"1", "0"},
            {"TRUE", "FALSE"},
            {"T", "F"},
            {"YES", "NO"},
        )
        for table in tables:
            field_samples = table.get("field_value_samples", {}) if isinstance(table, dict) else {}
            if not isinstance(field_samples, dict):
                continue
            for field_name, values in field_samples.items():
                cleaned = [str(v).strip() for v in (values or []) if str(v).strip()]
                if not cleaned:
                    continue
                upper = {v.upper() for v in cleaned}
                if any(upper.issubset(bs) and len(upper) >= 2 for bs in binary_sets):
                    continue
                # 仅保留文本枚举：至少有一个非数字字符
                if not any(re.search(r"[^\d]", v) for v in cleaned):
                    continue
                samples_map[str(field_name)] = cleaned
        return samples_map

    def _validate_sql_text_exact_match_risk(self, sql: str, semantic_context_result: Any) -> Optional[str]:
        """
        通用语义守卫：
        当文本枚举字段应做模糊匹配时，拦截误用的精确等值过滤。
        典型场景：活动名用户输入为简称，SQL 却使用 campaign_name = '简称' 导致 0 行。
        """
        samples_map = self._extract_text_enum_samples(semantic_context_result)
        if not samples_map:
            return None

        issues: List[str] = []
        # 捕获 field = 'value'（包含 alias.field、反引号）
        eq_pattern = re.compile(
            r"((?:\b[a-zA-Z_][a-zA-Z0-9_]*\.)?`?([A-Za-z_][A-Za-z0-9_]*)`?)\s*=\s*'([^']+)'",
            re.IGNORECASE,
        )
        for _full_field, field_name, rhs in eq_pattern.findall(sql):
            field_key = str(field_name)
            samples = samples_map.get(field_key) or samples_map.get(field_key.lower()) or []
            if not samples:
                # 忽略大小写匹配
                for k, v in samples_map.items():
                    if k.lower() == field_key.lower():
                        samples = v
                        break
            if not samples:
                continue

            rhs_text = str(rhs).strip()
            if not rhs_text:
                continue
            # 已存在精确值则允许
            if any(rhs_text == s for s in samples):
                continue
            # 若样本中存在“包含关系”，说明更可能应使用 LIKE
            if any((rhs_text in s) or (s in rhs_text) for s in samples):
                issues.append(
                    f"{field_key}='{rhs_text}' 未命中样本精确值，但与样本存在包含关系，建议使用 LIKE"
                )

        if not issues:
            return None
        return "文本枚举字段可能误用精确匹配导致空结果: " + "; ".join(issues)

    @staticmethod
    def _extract_case_when_count_condition(sql: str, alias: str) -> str:
        """
        提取 `SUM(CASE WHEN ... THEN 1 ELSE 0 END) AS <alias>` 的条件表达式。
        """
        pattern = re.compile(
            rf"SUM\s*\(\s*CASE\s+WHEN\s+(?P<cond>.+?)\s+THEN\s+1\s+ELSE\s+0\s+END\s*\)\s+AS\s+`?{re.escape(alias)}`?",
            flags=re.IGNORECASE | re.DOTALL,
        )
        match = pattern.search(sql)
        if not match:
            return ""
        return " ".join(match.group("cond").split())

    def _validate_workday_holiday_split_consistency(self, sql: str, user_question: str) -> Optional[str]:
        """
        语义守卫：
        对“工作日 vs 节假日”拆分场景，检查分类条件是否互斥，避免重复分摊导致总量失真。
        """
        question = (user_question or "").lower()
        is_target_question = (
            ("工作日" in question and "节假日" in question)
            or ("workday" in question and "holiday" in question)
        )
        if not is_target_question:
            return None

        workday_cond = self._extract_case_when_count_condition(sql, "workday_days")
        holiday_cond = self._extract_case_when_count_condition(sql, "holiday_days")
        if not workday_cond or not holiday_cond:
            return None

        workday_has_weekday = bool(
            re.search(r"(?:\b\w+\.)?`?is_weekday`?\s*=\s*'Y'", workday_cond, flags=re.IGNORECASE)
        )
        workday_mentions_holiday = bool(
            re.search(r"(?:\b\w+\.)?`?is_holiday`?", workday_cond, flags=re.IGNORECASE)
        )
        holiday_uses_holiday_flag = bool(
            re.search(r"(?:\b\w+\.)?`?is_holiday`?", holiday_cond, flags=re.IGNORECASE)
        )
        holiday_is_complement = bool(
            re.search(r"\bNOT\s*\(", holiday_cond, flags=re.IGNORECASE)
        )

        # 风险模式：工作日只按 is_weekday='Y'，节假日按 is_holiday 计数，存在交叉命中的可能。
        if (
            workday_has_weekday
            and (not workday_mentions_holiday)
            and holiday_uses_holiday_flag
            and (not holiday_is_complement)
        ):
            return (
                "工作日/节假日拆分条件可能重叠：`workday_days` 仅按 is_weekday='Y' 统计，"
                "`holiday_days` 也基于 is_holiday 统计，可能导致同一天被重复计入。"
                "请改为互斥定义（例如 holiday_days 使用 NOT(workday_condition)）。"
            )
        return None

    async def _peer_review_sql(
        self,
        context: ChatContext,
        user_question: str,
        generated_sql: str,
        semantic_context_result: Any,
        join_constraints: Dict[str, Any],
        prompt_db_type: str,
        retry_index: int,
    ) -> Dict[str, Any]:
        """
        使用独立会话对 SQL 做二次审校。
        - 不替代工程守卫，仅补充业务语义校验。
        - 默认单次审校，失败可触发 SQL 重新生成。
        """
        try:
            prompt = self.prompt_manager.render_prompt(
                PromptType.SQL_PEER_REVIEW,
                {
                    "user_question": user_question,
                    "thinking_result": getattr(context, "thinking_result", "") or "",
                    "semantic_context": getattr(semantic_context_result, "enhanced_context", "") or "",
                    "db_type": prompt_db_type,
                    "generated_sql": generated_sql,
                    "join_constraints": join_constraints or {},
                }
            )
        except Exception as exc:
            logger.warning(f"⚠️ SQL 同侪审校 Prompt 渲染失败，跳过: {str(exc)}")
            return {"success": False, "skip": True, "error": str(exc)}

        review_session_id = f"{context.session_id}_sql_review_{retry_index}_{uuid.uuid4().hex[:8]}"
        logger.info(f"🧪 启动 SQL 同侪审校（独立会话）: {review_session_id}")
        response = await self.ai_service.call_model(
            stage="sql_peer_review",
            prompt=prompt,
            session_id=review_session_id,
            model_type="qwen",
            temperature=0.0,
        )
        if not response.get("success"):
            return {"success": False, "skip": True, "error": response.get("error", "peer review failed")}

        try:
            parsed = self._extract_first_json_object(response.get("content", ""))
        except Exception as exc:
            logger.warning(f"⚠️ SQL 同侪审校结果解析失败，跳过: {str(exc)}")
            return {"success": False, "skip": True, "error": str(exc)}

        is_valid = bool(parsed.get("is_valid", False))
        violations = parsed.get("violations", []) if isinstance(parsed.get("violations", []), list) else []
        corrected_sql = str(parsed.get("corrected_sql", "") or "").strip()
        review_summary = str(parsed.get("review_summary", "") or "").strip()
        confidence = float(parsed.get("confidence", 0.0) or 0.0)

        return {
            "success": True,
            "is_valid": is_valid,
            "violations": violations,
            "corrected_sql": corrected_sql,
            "review_summary": review_summary,
            "confidence": confidence,
            "raw": parsed,
        }

    def _build_context_envelope(
        self,
        context: ChatContext,
        stage: str,
        semantic_context_result: Any,
        join_constraints: Dict[str, Any],
    ) -> Dict[str, Any]:
        aggregated_content = getattr(semantic_context_result, "aggregated_content", {}) or {}
        table_structures = (aggregated_content.get("table_structure") or {}).get("tables", [])
        if not table_structures:
            detailed_tables = context.metadata.get("detailed_tables_info", []) or []
            table_structures = [
                {
                    "table_id": t.get("tableId", ""),
                    "table_name": t.get("tableName", ""),
                    "description": t.get("description", ""),
                    "field_details": [
                        f"{f.get('fieldName', '')}({f.get('dataType', '')})"
                        for f in t.get("fields", [])
                    ],
                }
                for t in detailed_tables
            ]
        dictionaries = (aggregated_content.get("dictionary") or {}).get("field_dict_info_list", [])

        knowledge_module = aggregated_content.get("knowledge") or {}
        knowledge_hits: List[Dict[str, Any]] = []
        for item in knowledge_module.get("matched_knowledge", [])[:20]:
            knowledge_hits.append(
                {
                    "source": item.get("knowledge_type") or item.get("source", ""),
                    "title": item.get("knowledge_content") or item.get("title", ""),
                    "score": float(item.get("relevance_score", item.get("score", 0.0)) or 0.0),
                    "table_ids": item.get("related_table_ids", item.get("table_ids", []))
                    if isinstance(item.get("related_table_ids", item.get("table_ids", [])), list)
                    else [],
                }
            )

        table_schemas: List[Dict[str, Any]] = []
        for table_info in table_structures:
            field_items = []
            for raw_field in table_info.get("field_details", []):
                field_name = ""
                field_type = ""
                if isinstance(raw_field, str):
                    raw = raw_field.strip().lstrip("-").strip()
                    match = re.match(r"([A-Za-z0-9_]+)\s*\(([^)]+)\)", raw)
                    if match:
                        field_name = match.group(1)
                        field_type = match.group(2)
                    else:
                        field_name = raw.split(" ")[0]
                field_items.append(
                    {
                        "field_name": field_name,
                        "data_type": field_type,
                        "description": str(raw_field),
                    }
                )

            table_schemas.append(
                {
                    "table_id": str(table_info.get("table_id", "")),
                    "table_name": str(table_info.get("table_name", "")),
                    "description": str(table_info.get("description", "")),
                    "fields": field_items,
                }
            )

        resolved_time_context = context.metadata.get("resolved_time_context")
        resolved_ranges = []
        if resolved_time_context and hasattr(resolved_time_context, "date_ranges"):
            for dr in (resolved_time_context.date_ranges or []):
                resolved_ranges.append(
                    {
                        "start_date": getattr(dr, "start_date", None),
                        "end_date": getattr(dr, "end_date", None),
                        "description": getattr(dr, "description", ""),
                    }
                )

        selected_table_ids = self._normalize_selected_table_ids(context.selected_tables)
        return {
            "stage": stage,
            "selected_tables": selected_table_ids,
            "table_schemas": table_schemas,
            "dictionary_mappings": dictionaries,
            "knowledge_hits": knowledge_hits,
            "join_constraints": join_constraints or {},
            "time_policy": {
                "prefer_fiscal_period_filters": bool(context.metadata.get("prefer_fiscal_period_filters")),
                "resolved_ranges": resolved_ranges,
            },
        }

    def _build_join_constraint_prompt_block(
        self,
        join_constraints: Dict[str, Any],
        prefer_fiscal_period_filters: bool = False,
    ) -> str:
        if not join_constraints:
            return ""

        mode = str(join_constraints.get("mode") or "strict")
        payload = {
            "JOIN_MODE": mode,
            "ALLOWED_JOINS": join_constraints.get("allowed_edges", []),
            "INFERRED_JOIN_CANDIDATES": join_constraints.get("inferred_candidates", []),
            "REQUIRED_TABLES": join_constraints.get("required_table_names", []),
            "FORBIDDEN_JOINS": [],
            "TIME_FILTER_POLICY": {
                "prefer_fiscal_period_filters": prefer_fiscal_period_filters,
            },
        }
        mode_instruction = (
            "当前为 strict 模式：必须使用 ALLOWED_JOINS 中的配置关系。"
            if mode == "strict"
            else "当前为 inferred 模式：仅允许使用 INFERRED_JOIN_CANDIDATES 中的候选关系。"
        )
        return (
            "\n\n【机器约束（必须严格遵守）】\n"
            + json.dumps(payload, ensure_ascii=False, indent=2)
            + f"\n{mode_instruction}\n输出 SQL 必须严格落在以上约束中。"
        )

    def _validate_stage_contract(
        self,
        context: ChatContext,
        stage: str,
        semantic_context_result: Any,
        join_constraints: Dict[str, Any],
    ) -> Dict[str, Any]:
        envelope = self._build_context_envelope(
            context=context,
            stage=stage,
            semantic_context_result=semantic_context_result,
            join_constraints=join_constraints,
        )
        result = self.context_contract_validator.validate_stage_context(stage, envelope)
        self.multi_table_metrics.inc("stage_validation_total")
        if result.is_valid:
            logger.info(f"✅ stage contract 校验通过: stage={stage}")
            return {"ok": True, "envelope": envelope}

        self.multi_table_metrics.inc("stage_validation_fail_count")
        if result.missing_fields:
            self.multi_table_metrics.inc("context_missing_count")
        logger.warning(
            f"⚠️ stage contract 校验失败: stage={stage}, code={result.error_code}, missing={result.missing_fields}"
        )
        return {
            "ok": False,
            "error": {
                "code": result.error_code,
                "message": result.error_message,
                "retryable": result.retryable,
                "missing_fields": result.missing_fields,
                "details": result.details,
            },
            "envelope": envelope,
        }
    
    async def start_chat(
        self, 
        session_id: str, 
        user_question: str, 
        data_source_id: Optional[str] = None,
        history_messages: Optional[List[Dict[str, Any]]] = None,
        selected_tables: Optional[List[str]] = None,  # 🆕 用户选择的表 ID 列表
        response_language: Optional[str] = None  # 🆕 AI 回复语言，'en' 或 'zh'
    ) -> Dict[str, Any]:
        """
        开始对话流程（支持历史消息上下文和用户选择的表）
        
        Args:
            session_id: 会话ID
            user_question: 用户问题
            data_source_id: 数据源ID（可选）
            history_messages: 历史消息列表（可选），格式：[{"role": "user/assistant", "content": "...", "timestamp": "..."}]
            selected_tables: 用户选择的表 ID 列表（可选）
            response_language: AI 回复语言，'en' 或 'zh'（可选，默认 'zh'）
            
        Returns:
            对话结果
        """
        try:
            logger.info(f"=== ChatOrchestrator.start_chat 开始 ===")
            logger.info(f"会话ID: {session_id}")
            logger.info(f"用户问题: {user_question}")
            logger.info(f"数据源ID: {data_source_id}")
            logger.info(f"选择的表: {selected_tables}")  # 🆕 记录选择的表
            logger.info(f"历史消息数量: {len(history_messages) if history_messages else 0}")
            
            # 🆕 i18n: 确定回复语言（前端传入优先，否则自动检测）
            from src.utils.language_detector import detect_language
            if response_language in ('en', 'zh'):
                lang = response_language
            else:
                lang = detect_language(user_question)
            logger.info(f"🌐 AI 回复语言: {lang} (前端传入: {response_language})")
            
            # 🆕 Task 16: 从数据库加载历史对话（如果存在）
            logger.info("=" * 80)
            logger.info("📂 Task 16: 从数据库加载历史对话")
            logger.info("=" * 80)
            try:
                # 设置数据库会话
                db = next(get_db())
                self.context_manager.set_db_session(db)
                
                # 尝试从数据库加载会话历史
                loaded_session = await self.context_manager.load_session_from_db(session_id)
                
                if loaded_session:
                    logger.info(f"✅ 从数据库加载历史对话成功")
                    logger.info(f"📊 会话ID: {session_id}")
                    logger.info(f"📊 云端消息数: {len(loaded_session.cloud_messages)}")
                    logger.info(f"📊 本地消息数: {len(loaded_session.local_messages)}")
                    logger.info(f"📊 总Token数: {loaded_session.total_tokens}")
                else:
                    logger.info(f"ℹ️ 会话 {session_id} 无历史数据，将创建新会话")
                
                db.close()
            except Exception as e:
                logger.error(f"❌ 从数据库加载历史对话失败: {str(e)}", exc_info=True)
            logger.info("=" * 80)
            
            # 创建或获取对话上下文
            context = self.get_or_create_context(session_id)
            
            # 🆕 i18n: 保存语言设置到上下文
            context.metadata['response_language'] = lang
            
            # 🆕 保存用户选择的表到上下文
            if selected_tables:
                context.metadata['user_selected_tables'] = selected_tables
                logger.info(f"✅ 已保存用户选择的表到上下文: {selected_tables}")
            else:
                context.metadata['user_selected_tables'] = []
                logger.info(f"ℹ️ 用户未选择数据表")
            
            # 保存历史消息到上下文
            if history_messages:
                context.metadata['history_messages'] = history_messages
                logger.info(f"已保存 {len(history_messages)} 条历史消息到上下文")
            
            logger.info(f"对话上下文已创建/获取，当前阶段: {context.current_stage.value}")
            
            # 🆕 Task 14: 添加用户消息到历史记录
            logger.info("=" * 80)
            logger.info("📝 Task 14: 添加用户消息到 ContextManager")
            logger.info("=" * 80)
            try:
                message_id = self.context_manager.add_user_message(session_id, user_question)
                logger.info(f"✅ 用户消息已添加到历史记录")
                logger.info(f"📊 消息ID: {message_id}")
                logger.info(f"📝 消息内容: {user_question}")
                
                # 获取会话统计信息
                session_stats = self.context_manager.get_session_stats(session_id)
                logger.info(f"📊 会话统计: {session_stats}")
            except Exception as e:
                logger.error(f"❌ 添加用户消息到历史记录失败: {str(e)}", exc_info=True)
            logger.info("=" * 80)
            
            # 发送开始消息
            logger.info(f"发送开始消息到 WebSocket...")
            await self.websocket_service.send_status_message(
                session_id, "开始处理您的问题...", 0.1
            )
            logger.info(f"开始消息已发送")
            
            # 等待 WebSocket 连接建立（最多等待 2 秒）
            max_wait = 2.0
            wait_interval = 0.1
            waited = 0.0
            
            while waited < max_wait:
                status = self.websocket_service.get_connection_status(session_id)
                if status["connection_count"] > 0:
                    logger.info(f"✅ WebSocket 连接已建立: {status['connection_count']} 个连接")
                    break
                await asyncio.sleep(wait_interval)
                waited += wait_interval
            
            if waited >= max_wait:
                logger.warning(f"⚠️ WebSocket 连接超时（等待 {max_wait}秒），继续执行（消息可能丢失）")
            
            # 执行完整对话流程
            logger.info(f"开始执行对话流水线...")
            result = await self._execute_chat_pipeline(context, user_question, data_source_id)
            logger.info(f"对话流水线执行完成，结果: {result}")
            
            return result
            
        except Exception as e:
            logger.error(f"对话流程执行失败: {str(e)}", exc_info=True)
            await self.websocket_service.send_error_message(
                session_id, f"对话处理失败: {str(e)}", "CHAT_ORCHESTRATOR_ERROR"
            )
            return {
                "success": False,
                "error": str(e),
                "session_id": session_id
            }
    
    async def continue_chat(self, session_id: str, user_response: str) -> Dict[str, Any]:
        """
        继续对话（处理用户回复）
        
        Args:
            session_id: 会话ID
            user_response: 用户回复
            
        Returns:
            对话结果
        """
        try:
            context = self.active_contexts.get(session_id)
            if not context:
                return {
                    "success": False,
                    "error": "会话不存在或已过期",
                    "session_id": session_id
                }
            
            # 根据当前阶段处理用户回复
            if context.current_stage == ChatStage.INTENT_CLARIFICATION:
                return await self._handle_clarification_response(context, user_response)
            elif context.current_stage == ChatStage.ERROR_HANDLING:
                return await self._handle_error_recovery(context, user_response)
            else:
                # 作为新的追问处理
                return await self._handle_followup_question(context, user_response)
                
        except Exception as e:
            logger.error(f"继续对话失败: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "session_id": session_id
            }
    
    def get_or_create_context(self, session_id: str) -> ChatContext:
        """获取或创建对话上下文"""
        if session_id not in self.active_contexts:
            self.active_contexts[session_id] = ChatContext(session_id)
        return self.active_contexts[session_id]
    
    async def _execute_chat_pipeline(self, context: ChatContext, user_question: str, data_source_id: Optional[str]) -> Dict[str, Any]:
        """执行完整对话流水线"""
        
        try:
            # 阶段1: 意图识别（流式输出，stage 消息在 _recognize_intent 内部发送）
            context.update_stage(ChatStage.INTENT_RECOGNITION)
            
            intent_result = await self._recognize_intent(context, user_question)
            if not intent_result["success"]:
                return await self._handle_pipeline_error(context, "意图识别失败", intent_result.get("error"))
            
            context.intent = ChatIntent(intent_result["intent"])
            
            # 阶段2: 智能选表（stage 生命周期由 _select_tables 内部管理，不在此处重复发送）
            context.update_stage(ChatStage.TABLE_SELECTION)
            
            table_result = await self._select_tables(context, user_question, data_source_id)
            if not table_result["success"]:
                return await self._handle_pipeline_error(context, "智能选表失败", table_result.get("error"))
            
            context.selected_tables = table_result["tables"]
            
            # 🔒 安全 fallback：如果 AI 选表结果为空，但用户已选择了表，直接使用用户选择的表
            user_selected_tables_fallback = context.metadata.get('user_selected_tables', [])
            if not context.selected_tables and user_selected_tables_fallback:
                logger.warning(f"⚠️ AI 选表结果为空，fallback 到用户选择的表: {user_selected_tables_fallback}")
                context.selected_tables = user_selected_tables_fallback
            
            # 🆕 获取详细的表信息（包含字段、数据字典、表关联）
            # 🔥 这些信息将在 SQL 生成阶段使用
            detailed_tables_info = []
            if context.selected_tables:
                from src.services.data_table_service import DataTableService
                from src.services.data_preparation_service import DictionaryService
                from src.database import get_db
                
                db = next(get_db())
                table_service = DataTableService()
                dict_service = DictionaryService()
                
                for table_info in context.selected_tables:
                    table_id = table_info.get("tableId") if isinstance(table_info, dict) else table_info
                    table = table_service.get_table_by_id(db, table_id)
                    
                    if table:
                        # 获取字段信息
                        fields = table_service.get_table_columns(db, table_id)
                        fields_data = []
                        
                        for field in fields:
                            field_data = {
                                "fieldName": field.field_name,
                                "dataType": field.data_type,
                                "isPrimaryKey": field.is_primary_key,
                                "isNullable": field.is_nullable,
                                "description": field.description
                            }
                            
                            # 获取数据字典信息
                            if hasattr(field, 'dictionary_id') and field.dictionary_id:
                                try:
                                    dictionary = dict_service.get_dictionary_by_id(db, field.dictionary_id)
                                    if dictionary:
                                        dict_items = dict_service.get_dictionary_items(db, field.dictionary_id)
                                        field_data["dictionary"] = {
                                            "name": dictionary.name,
                                            "code": dictionary.code,
                                            "items": [f"{item.item_key}={item.item_value}" for item in dict_items[:5]]
                                        }
                                except Exception as e:
                                    logger.warning(f"获取字段 {field.field_name} 的字典信息失败: {str(e)}")
                            
                            fields_data.append(field_data)
                        
                        # 获取表关联信息
                        relations_data = []
                        try:
                            from src.models.data_preparation_model import TableRelation  # 🔧 修复导入路径
                            from sqlalchemy import or_
                            
                            relations = db.query(TableRelation).filter(
                                or_(
                                    TableRelation.primary_table_id == table_id,
                                    TableRelation.foreign_table_id == table_id
                                ),
                                TableRelation.status == True
                            ).all()
                            
                            for rel in relations:
                                primary_table = table_service.get_table_by_id(db, rel.primary_table_id)
                                foreign_table = table_service.get_table_by_id(db, rel.foreign_table_id)
                                
                                relations_data.append({
                                    "relationName": rel.relation_name or "未命名关联",
                                    "primaryTable": primary_table.table_name if primary_table else rel.primary_table_id,
                                    "primaryField": rel.primary_field_name,
                                    "foreignTable": foreign_table.table_name if foreign_table else rel.foreign_table_id,
                                    "foreignField": rel.foreign_field_name,
                                    "joinType": rel.join_type or "INNER JOIN",
                                    "description": rel.description
                                })
                        except Exception as e:
                            logger.warning(f"获取表 {table.table_name} 的关联关系失败: {str(e)}")
                        
                        # 构建完整的表信息
                        detailed_tables_info.append({
                            "tableId": table_id,
                            "tableName": table.table_name,
                            "displayName": table.display_name,
                            "description": table.description,
                            "fields": fields_data,
                            "relations": relations_data
                        })
                
                db.close()
            
            # 🔥 保存详细表信息到 context，供 SQL 生成阶段使用
            context.metadata['detailed_tables_info'] = detailed_tables_info
            logger.info(f"✅ 已保存 {len(detailed_tables_info)} 个表的详细信息到 context")
            
            # 阶段3: 意图澄清（总是执行，只展示理解结果，不阻拦流程）
            context.update_stage(ChatStage.INTENT_CLARIFICATION)
            
            # 调用意图澄清分析
            clarification_result = await self._clarify_intent(
                context=context,
                user_question=user_question,
                intent_type=intent_result.get("intent", "query"),
                selected_tables=context.selected_tables,
                data_source_id=data_source_id
            )
            clarification_result = self._apply_followup_time_scope_override(
                user_question=user_question,
                clarification_result=clarification_result,
            )
            
            # 无论是否需要澄清，都只是展示 AI 的理解结果，不阻拦流程继续执行
            clarification_text = clarification_result.get("clarificationText", "问题明确，无需澄清")
            needs_clarification = clarification_result.get("needsClarification", False)
            
            # 🆕 i18n: 翻译 stage 标签
            from src.utils.language_detector import translate_stage_label
            _lang = context.metadata.get('response_language', 'zh')
            _clarification_stage_name = translate_stage_label("意图澄清", _lang)
            
            # 完成意图澄清阶段（展示 AI 的理解）
            await self.websocket_service.send_stage_complete(
                session_id=context.session_id,
                stage_id="stage_clarification",
                stage_name=_clarification_stage_name,
                content=clarification_text,
                metadata={
                    "progress": 0.5,
                    "needsClarification": needs_clarification,
                    "analysis": clarification_result.get("analysis", {}),
                    "clarificationQuestions": clarification_result.get("clarificationQuestions", [])
                }
            )
            
            logger.info(f"✅ 意图澄清完成（需要澄清: {needs_clarification}），流程继续执行")
            
            # 🆕 处理 AI 意图澄清中的财务日历查询指令（fiscalTimeQueries）
            fiscal_time_resolved = False
            fiscal_date_ranges = []  # 存储 AI 指令查询到的日期范围
            try:
                fiscal_queries = clarification_result.get('fiscalTimeQueries', [])
                if fiscal_queries:
                    logger.info(f"📅 AI 意图澄清产生了 {len(fiscal_queries)} 个财务日历查询指令")
                    from src.services.time_resolver import FiscalCalendarRepository, DateRange, ResolvedTimeContext
                    db = next(get_db())
                    repo = FiscalCalendarRepository()
                    
                    for fq in fiscal_queries:
                        fq_type = fq.get('type', '')
                        fq_desc = fq.get('description', '')

                        if self._is_uncertain_fiscal_query(fq):
                            logger.warning(
                                f"📅 跳过不确定 fiscalTimeQuery（不注入权威时间）: type={fq_type}, desc={fq_desc}"
                            )
                            continue
                        
                        if fq_type == 'month_week':
                            month = fq.get('month')
                            year = fq.get('year')
                            fiscal_year_hint = fq.get('fiscalYear')
                            week_index = fq.get('weekIndex')
                            if month and week_index:
                                weeks = []
                                # 如果带 fiscalYear 提示，优先在该财年内按自然月重叠查找（避免 FY25 的 10月误判成 2025-10）
                                if fiscal_year_hint:
                                    fy_text = str(fiscal_year_hint).strip().upper()
                                    fy_digits = re.sub(r"[^0-9]", "", fy_text)
                                    fy_label = None
                                    if len(fy_digits) == 2:
                                        fy_label = f"FY20{fy_digits}"
                                    elif len(fy_digits) == 4:
                                        fy_label = f"FY{fy_digits}"
                                    if fy_label:
                                        weeks = repo.find_fiscal_weeks_by_month_in_fiscal_year(
                                            db, fy_label, int(month)
                                        )
                                elif year:
                                    weeks = repo.find_fiscal_weeks_by_natural_month(
                                        db, int(year), int(month)
                                    )

                                if weeks:
                                    # weekIndex: 正数从1开始，-1表示最后一个
                                    if week_index == -1:
                                        target = weeks[-1]
                                    elif 1 <= week_index <= len(weeks):
                                        target = weeks[week_index - 1]
                                    else:
                                        logger.warning(f"📅 {fq_desc}: weekIndex={week_index} 超出范围（共{len(weeks)}个财周）")
                                        continue
                                    
                                    dr = DateRange(
                                        start_date=target.fw_start_date.isoformat() if hasattr(target.fw_start_date, 'isoformat') else str(target.fw_start_date),
                                        end_date=target.fw_end_date.isoformat() if hasattr(target.fw_end_date, 'isoformat') else str(target.fw_end_date),
                                        label=target.fw_label,
                                        expr_type="fw",
                                    )
                                    fiscal_date_ranges.append(dr)
                                    logger.info(f"📅 {fq_desc} → {target.fw_label}（{dr.start_date} 到 {dr.end_date}）")
                                else:
                                    logger.warning(f"📅 {fq_desc}: {year}年{month}月在财务日历中无记录")
                        
                        elif fq_type == 'month_range':
                            year = fq.get('year')
                            month = fq.get('month')
                            if year and month:
                                weeks = repo.find_fiscal_weeks_by_natural_month(db, year, month)
                                if weeks:
                                    dr = DateRange(
                                        start_date=weeks[0].fw_start_date.isoformat() if hasattr(weeks[0].fw_start_date, 'isoformat') else str(weeks[0].fw_start_date),
                                        end_date=weeks[-1].fw_end_date.isoformat() if hasattr(weeks[-1].fw_end_date, 'isoformat') else str(weeks[-1].fw_end_date),
                                        label=f"{year}年{month}月",
                                        expr_type="fm",
                                    )
                                    fiscal_date_ranges.append(dr)
                                    logger.info(f"📅 {fq_desc} → {dr.start_date} 到 {dr.end_date}（{len(weeks)}个财周）")
                        
                        elif fq_type == 'fw_offset':
                            base_label = fq.get('baseFwLabel')
                            offset = fq.get('offset', 0)
                            if base_label:
                                target = repo.find_fw_by_offset(db, base_label, offset)
                                if target:
                                    dr = DateRange(
                                        start_date=target.fw_start_date.isoformat() if hasattr(target.fw_start_date, 'isoformat') else str(target.fw_start_date),
                                        end_date=target.fw_end_date.isoformat() if hasattr(target.fw_end_date, 'isoformat') else str(target.fw_end_date),
                                        label=target.fw_label,
                                        expr_type="fw",
                                    )
                                    fiscal_date_ranges.append(dr)
                                    logger.info(f"📅 {fq_desc} → {target.fw_label}（{dr.start_date} 到 {dr.end_date}）")

                        elif fq_type == 'fiscal_month_week':
                            # 显式财务口径：按 fiscal_year + fiscal_month 取该财月第 N 财周
                            fiscal_year_raw = fq.get('fiscalYear') or fq.get('year')
                            fiscal_month_raw = fq.get('fiscalMonth') or fq.get('fiscalPeriod') or fq.get('month')
                            week_index = fq.get('weekIndex')
                            if fiscal_year_raw and fiscal_month_raw and week_index:
                                from src.models.fiscal_calendar_model import FiscalCalendar

                                def _normalize_fy_label(value: Any) -> Optional[str]:
                                    if value is None:
                                        return None
                                    text = str(value).strip().upper()
                                    if text.startswith("FY"):
                                        digits = text[2:]
                                    else:
                                        digits = text
                                    if not digits.isdigit():
                                        return None
                                    if len(digits) == 2:
                                        return f"FY20{digits}"
                                    if len(digits) == 4:
                                        return f"FY{digits}"
                                    return None

                                def _normalize_fm_label(value: Any) -> Optional[str]:
                                    if value is None:
                                        return None
                                    text = str(value).strip().upper()
                                    if text.startswith("FM"):
                                        num_text = text[2:]
                                    elif text.startswith("P"):
                                        num_text = text[1:]
                                    else:
                                        num_text = text
                                    if not num_text.isdigit():
                                        return None
                                    n = int(num_text)
                                    if 1 <= n <= 12:
                                        return f"FM{n}"
                                    return None

                                fy_label = _normalize_fy_label(fiscal_year_raw)
                                fm_label = _normalize_fm_label(fiscal_month_raw)
                                if not fy_label or not fm_label:
                                    logger.warning(
                                        f"📅 {fq_desc}: fiscal_year={fiscal_year_raw}, fiscal_month={fiscal_month_raw} 解析失败"
                                    )
                                    continue

                                weeks = (
                                    db.query(FiscalCalendar)
                                    .filter(
                                        FiscalCalendar.fiscal_year == fy_label,
                                        FiscalCalendar.fiscal_month == fm_label,
                                    )
                                    .order_by(FiscalCalendar.fw_start_date.asc())
                                    .all()
                                )
                                if weeks:
                                    if week_index == -1:
                                        target = weeks[-1]
                                    elif 1 <= week_index <= len(weeks):
                                        target = weeks[week_index - 1]
                                    else:
                                        logger.warning(
                                            f"📅 {fq_desc}: weekIndex={week_index} 超出范围（{fy_label} {fm_label} 共{len(weeks)}个财周）"
                                        )
                                        continue
                                    dr = DateRange(
                                        start_date=target.fw_start_date.isoformat() if hasattr(target.fw_start_date, 'isoformat') else str(target.fw_start_date),
                                        end_date=target.fw_end_date.isoformat() if hasattr(target.fw_end_date, 'isoformat') else str(target.fw_end_date),
                                        label=target.fw_label,
                                        expr_type="fw",
                                    )
                                    fiscal_date_ranges.append(dr)
                                    logger.info(
                                        f"📅 {fq_desc}（{fy_label} {fm_label}）→ {target.fw_label}（{dr.start_date} 到 {dr.end_date}）"
                                    )
                                else:
                                    logger.warning(f"📅 {fq_desc}: {fy_label} {fm_label} 在财务日历中无记录")
                    
                    db.close()
                    
                    if fiscal_date_ranges:
                        fiscal_time_resolved = True
                        logger.info(f"📅 AI 财务日历查询完成，共解析 {len(fiscal_date_ranges)} 个日期范围")
            except Exception as _ftq_err:
                logger.warning(f"📅 处理 fiscalTimeQueries 异常，跳过: {_ftq_err}")
            
            # 🆕 时间解析（在思考阶段之前执行，确保思考模型能看到已解析的日期）
            effective_question = user_question
            try:
                db = next(get_db())
                time_context = await self.time_resolver.resolve(user_question, db)
                db.close()
                if time_context:
                    logger.info(f"⏰ TimeResolver: 识别到时间表达 {[e.raw_text for e in time_context.expressions]}")
                    logger.info(f"⏰ TimeResolver: 重写后问题: {time_context.rewritten_question}")
                    context.metadata['resolved_time_context'] = time_context
                    # 用户明确给出 FY + 财务期间（FW/FM/FQ）时，后续 SQL 生成优先采用财务字段过滤口径
                    has_explicit_fw = any(
                        getattr(expr, "expr_type", "") == "fw"
                        and not getattr(expr, "is_relative", True)
                        and bool(getattr(expr, "label", None))
                        for expr in (time_context.expressions or [])
                    )
                    has_explicit_fm = any(
                        getattr(expr, "expr_type", "") == "fm"
                        and not getattr(expr, "is_relative", True)
                        and bool(getattr(expr, "label", None))
                        for expr in (time_context.expressions or [])
                    )
                    has_explicit_fq = any(
                        getattr(expr, "expr_type", "") == "fq"
                        and not getattr(expr, "is_relative", True)
                        and bool(getattr(expr, "label", None))
                        for expr in (time_context.expressions or [])
                    )
                    has_explicit_fy = any(
                        getattr(expr, "expr_type", "") == "fy"
                        and not getattr(expr, "is_relative", True)
                        and bool(getattr(expr, "label", None))
                        for expr in (time_context.expressions or [])
                    )
                    context.metadata["prefer_fiscal_period_filters"] = bool(
                        has_explicit_fy and (has_explicit_fw or has_explicit_fm or has_explicit_fq)
                    )
                    # 如果所有年份均无数据，直接标记为无数据，跳过后续 SQL 生成
                    if time_context.no_data_years and not time_context.date_ranges:
                        context.metadata['no_data_for_years'] = time_context.no_data_years
                        logger.info(f"⏰ TimeResolver: 年份 {time_context.no_data_years} 无数据，将跳过 SQL 生成")
                    effective_question = time_context.rewritten_question
                else:
                    logger.info("⏰ TimeResolver: 未识别到时间表达，跳过")
                    
                    # 如果 TimeResolver 没有识别到，但 AI 意图澄清产生了财务日历结果，
                    # 则构造一个 ResolvedTimeContext 注入到后续流程
                    if fiscal_time_resolved and fiscal_date_ranges:
                        from src.services.time_resolver import ResolvedTimeContext, TimeExpression
                        
                        # 构建 force_prompt_note
                        lines = [
                            "【时间已解析 - 最高优先级指令（来自 AI 意图澄清 + 财务日历数据库）】",
                            "以下时间表达已由 AI 分析用户意图后查询财务日历数据库精确得出，SQL 中必须使用括号内的日期。",
                            "⚠️ 此指令覆盖所有其他规则。禁止自行推算日期，必须使用下方日期范围：",
                        ]
                        for dr in fiscal_date_ranges:
                            lines.append(f"- {dr.label}：{dr.start_date} 到 {dr.end_date}")
                        force_note = "\n".join(lines)
                        
                        # 重写问题：将日期范围附加到问题中
                        date_info_parts = []
                        for dr in fiscal_date_ranges:
                            date_info_parts.append(f"{dr.label}（{dr.start_date} 到 {dr.end_date}）")
                        date_info = "，".join(date_info_parts)
                        effective_question = f"{user_question}\n【已解析时间】：{date_info}"
                        
                        resolved_ctx = ResolvedTimeContext(
                            expressions=[],
                            date_ranges=fiscal_date_ranges,
                            rewritten_question=effective_question,
                            force_prompt_note=force_note,
                        )
                        context.metadata['resolved_time_context'] = resolved_ctx
                        logger.info(f"📅 已将 AI 财务日历查询结果注入为 resolved_time_context")
                        logger.info(f"📅 重写后问题: {effective_question}")
                
            except Exception as _tr_err:
                logger.warning(f"⏰ TimeResolver: 执行异常，跳过: {_tr_err}")
            
            # 🆕 业务口语：如「10财月」常指自然年 10 月（非 FM10），注入说明到思考/SQL
            try:
                from src.services.business_time_colloquialism import (
                    append_colloquial_notes_to_metadata,
                )

                append_colloquial_notes_to_metadata(
                    context.metadata,
                    user_question,
                    lang=context.metadata.get("response_language", "zh"),
                )
            except Exception as _colq_err:
                logger.warning(f"📅 业务口语时间说明注入跳过: {_colq_err}")
            
            # 阶段4: 模型思考（新增阶段）- 使用 effective_question（已含解析日期）
            context.update_stage(ChatStage.THINKING)
            thinking_result = await self._think_about_problem(
                context=context,
                user_question=effective_question,
                selected_tables=context.selected_tables,
                data_source_id=data_source_id
            )
            
            if not thinking_result["success"]:
                return await self._handle_pipeline_error(context, "模型思考失败", thinking_result.get("error"))
            
            # 阶段5: SQL生成（取数）
            context.update_stage(ChatStage.SQL_GENERATION)
            
            # 🆕 无数据年份早退：直接返回"无数据"描述，跳过 SQL 生成和执行
            if context.metadata.get('no_data_for_years'):
                no_data_years = context.metadata['no_data_for_years']
                years_str = "、".join(str(y) for y in no_data_years)
                no_data_msg = (
                    f"The database does not contain data for the {years_str} period you requested. "
                    f"Currently available data covers up to 2026. "
                    f"Please try querying a different time period."
                ) if any(c.isascii() and c.isalpha() for c in user_question) else (
                    f"数据库中暂无您查询的 {years_str} 年数据，"
                    f"当前数据覆盖范围截止至 2026 年，请尝试查询其他时间段。"
                )
                logger.info(f"⏰ 无数据年份早退：{no_data_years}，返回提示信息")
                return await self._handle_no_data_response(context, no_data_msg)
            
            # 🔄 SQL 生成 + 执行智能重试循环
            # 执行失败时将错误信息和表结构传给 AI 重新生成 SQL，最多重试 3 次
            MAX_SQL_EXEC_RETRIES = 3
            sql_exec_retry = 0
            last_exec_error: Optional[str] = None
            execution_result: Optional[Dict[str, Any]] = None

            while sql_exec_retry < MAX_SQL_EXEC_RETRIES:
                # 阶段5: SQL生成（首次或重试时重新生成）
                context.update_stage(ChatStage.SQL_GENERATION)
                sql_result = await self._generate_sql(
                    context,
                    effective_question,
                    data_source_id,
                    exec_error=last_exec_error  # 首次为 None，重试时传入执行错误
                )
                if not sql_result["success"]:
                    return await self._handle_pipeline_error(context, "SQL生成失败", sql_result.get("error"))

                context.generated_sql = sql_result["sql"]
                logger.info(f"📝 SQL 生成完成（第 {sql_exec_retry + 1} 次）: {context.generated_sql}")

                # 阶段6: SQL执行
                context.update_stage(ChatStage.SQL_EXECUTION)
                from src.utils.language_detector import translate_stage_label as _tsl
                _exec_lang = context.metadata.get('response_language', 'zh')
                _exec_stage_name = _tsl("SQL执行", _exec_lang)

                # 首次发送 stage_start，重试时发送 stage_update 提示正在重试
                if sql_exec_retry == 0:
                    await self.websocket_service.send_stage_start(
                        session_id=context.session_id,
                        stage_id="stage_execute",
                        stage_name=_exec_stage_name,
                        content="正在执行查询...",
                        metadata={"progress": 0.7}
                    )
                else:
                    _retry_hint = (
                        f"SQL execution failed, retrying ({sql_exec_retry + 1}/{MAX_SQL_EXEC_RETRIES})..."
                        if _exec_lang == 'en'
                        else f"SQL执行失败，正在重新生成并重试（第 {sql_exec_retry + 1}/{MAX_SQL_EXEC_RETRIES} 次）..."
                    )
                    await self.websocket_service.send_stage_update(
                        session_id=context.session_id,
                        stage_id="stage_execute",
                        content=_retry_hint
                    )

                execution_result = await self._execute_sql(context, data_source_id)

                if execution_result["success"]:
                    # 执行成功，跳出重试循环
                    logger.info(f"✅ SQL 执行成功（第 {sql_exec_retry + 1} 次尝试）")
                    break

                # 执行失败，收集错误信息准备重试
                last_exec_error = execution_result.get("error", "未知错误")
                sql_exec_retry += 1
                logger.warning(f"⚠️ SQL 执行失败（第 {sql_exec_retry}/{MAX_SQL_EXEC_RETRIES} 次）: {last_exec_error}")

                # 重试前等待 2 秒，避免立即重试导致模型返回相同结果
                if sql_exec_retry < MAX_SQL_EXEC_RETRIES:
                    logger.info(f"⏳ 等待 2 秒后重新生成 SQL（第 {sql_exec_retry + 1} 次尝试）...")
                    await asyncio.sleep(2)

                if sql_exec_retry >= MAX_SQL_EXEC_RETRIES:
                    # 超过最大重试次数，返回失败
                    logger.error(f"❌ SQL 执行失败，已重试 {MAX_SQL_EXEC_RETRIES} 次，放弃")
                    return await self._handle_pipeline_error(
                        context,
                        "SQL执行失败",
                        f"经过 {MAX_SQL_EXEC_RETRIES} 次重试仍无法执行成功。最后错误：{last_exec_error}"
                    )

            if not execution_result or not execution_result["success"]:
                return await self._handle_pipeline_error(context, "SQL执行失败", execution_result.get("error") if execution_result else "未知错误")
            
            context.query_result = execution_result["result"]
            
            # 🆕 Task 14: 不再保存独立的 SQL 消息
            # SQL 已经包含在流式输出的 stages 中（"SQL生成"阶段）
            # 保存独立的 SQL 消息会导致历史对话中重复显示
            logger.info("=" * 80)
            logger.info("📝 Task 14: SQL 已包含在 stages 中，不单独保存")
            logger.info("=" * 80)
            logger.info(f"📝 SQL 内容: {context.generated_sql}")
            logger.info(f"📊 查询结果行数: {context.query_result.get('total_rows', 0)}")
            logger.info("ℹ️ SQL 消息将通过 stages 数据保存，不需要单独保存")
            logger.info("=" * 80)
            
            # 完成SQL执行阶段
            total_rows = context.query_result.get("total_rows", 0)
            _exec_complete_content = (
                f"Query complete: {total_rows} record(s) found"
                if _exec_lang == 'en'
                else f"查询执行完成，共找到 {total_rows} 条记录"
            )
            await self.websocket_service.send_stage_complete(
                session_id=context.session_id,
                stage_id="stage_execute",
                stage_name=_exec_stage_name,
                content=_exec_complete_content,
                metadata={
                    "progress": 0.85,
                    "total_rows": total_rows,
                    # 🔥 修复：保存完整的查询结果，用于历史会话恢复
                    "queryResult": {
                        "columns": context.query_result.get("columns", []),
                        "rows": context.query_result.get("rows", []),
                        "total_rows": total_rows,
                        "column_types": context.query_result.get("column_types", [])
                    }
                }
            )
            
            # 阶段7: 数据结果描述（用自然语言描述查询结果，重要数字用颜色标识）
            context.update_stage(ChatStage.RESULT_DESCRIPTION)
            description_result = await self._describe_result(
                context=context,
                user_question=user_question,
                query_result=context.query_result,
                analysis_text=None  # 在 _describe_result 内部格式化数据
            )
            
            if not description_result["success"]:
                logger.warning(f"⚠️ 数据结果描述失败: {description_result.get('error')}")
                # 结果描述失败不影响整体流程，继续执行
            
            # 阶段8: 生成图表配置（在描述之后生成，避免阻塞用户查看文字内容）
            context.update_stage(ChatStage.CHART_GENERATION)
            chart_result = await self._generate_chart_config(
                context=context,
                user_question=user_question,
                query_result=context.query_result
            )
            
            if not chart_result["success"]:
                logger.warning(f"⚠️ 图表配置生成失败: {chart_result.get('error')}")
                # 图表生成失败不影响整体流程，继续执行
            else:
                context.chart_config = chart_result.get("chart_config")
            
            # 保存历史数据
            context.add_previous_data(context.query_result)
            
            context.update_stage(ChatStage.COMPLETED)
            
            # 🔥 准备图表数据（转换为前端期望的 ChartData 格式）
            chart_data_for_frontend = None
            chart_type_for_frontend = None
            
            logger.info("=" * 80)
            logger.info("🔥 开始准备图表数据")
            logger.info(f"📊 hasattr(context, 'chart_config'): {hasattr(context, 'chart_config')}")
            if hasattr(context, 'chart_config'):
                logger.info(f"📊 context.chart_config: {context.chart_config}")
            logger.info("=" * 80)
            
            if hasattr(context, 'chart_config') and context.chart_config:
                logger.info("✅ context.chart_config 存在且不为空")
                try:
                    # 从查询结果构建 ChartData 格式
                    query_result = context.query_result
                    logger.info(f"📊 query_result 存在: {query_result is not None}")
                    if query_result:
                        logger.info(f"📊 query_result.keys(): {query_result.keys()}")
                    
                    # 🔥 修复：query_result 使用的键是 'rows'，不是 'data'
                    if query_result and "columns" in query_result and "rows" in query_result:
                        logger.info(f"✅ query_result 包含 columns 和 rows")
                        logger.info(f"📊 columns: {query_result['columns']}")
                        logger.info(f"📊 rows 行数: {len(query_result['rows'])}")
                        
                        chart_data_for_frontend = {
                            "columns": query_result["columns"],
                            "rows": [list(row) if isinstance(row, (list, tuple)) else list(row.values()) for row in query_result["rows"]],
                            "metadata": {
                                "columnTypes": query_result.get("column_types", [])
                            }
                        }
                        
                        # 🔥 将 AI 生成的 series 和 xAxis 配置也传给前端
                        # 前端 SmartChart 会优先使用 AI 生成的 series，而不是自己重新构建
                        chart_config_detail = context.chart_config.get("chartConfig", {})
                        if chart_config_detail.get("series"):
                            chart_data_for_frontend["series"] = chart_config_detail["series"]
                        if chart_config_detail.get("xAxis"):
                            chart_data_for_frontend["xAxis"] = chart_config_detail["xAxis"]
                        if chart_config_detail.get("title"):
                            chart_data_for_frontend["title"] = chart_config_detail["title"]
                        # 🔥 传递 AI 推荐的图表类型，前端 SmartChart 据此决定是否使用 AI series
                        recommended_type = context.chart_config.get("recommendedChart")
                        if recommended_type:
                            chart_data_for_frontend["aiRecommendedType"] = recommended_type
                        
                        logger.info(f"✅ chart_data_for_frontend 已构建")
                        logger.info(f"📊 columns 数量: {len(chart_data_for_frontend['columns'])}")
                        logger.info(f"📊 rows 数量: {len(chart_data_for_frontend['rows'])}")
                        
                        # 获取推荐的图表类型
                        chart_type_for_frontend = context.chart_config.get("recommendedChart", "bar")
                        
                        logger.info(f"✅ 图表数据已准备: type={chart_type_for_frontend}, columns={len(chart_data_for_frontend['columns'])}, rows={len(chart_data_for_frontend['rows'])}")
                    else:
                        logger.warning(f"⚠️ query_result 不包含 columns 或 data")
                except Exception as e:
                    logger.error(f"❌ 准备图表数据失败: {str(e)}", exc_info=True)
            else:
                logger.warning(f"⚠️ context.chart_config 不存在或为空")
            
            logger.info("=" * 80)
            logger.info(f"🔥 图表数据准备完成")
            logger.info(f"📊 chart_data_for_frontend: {chart_data_for_frontend is not None}")
            logger.info(f"📊 chart_type_for_frontend: {chart_type_for_frontend}")
            logger.info("=" * 80)
            
            # 🔥 发送 complete 消息，通知前端保存 stages 数据（包含图表数据）
            logger.info("📨 发送 complete 消息到前端")
            complete_metadata = {}
            if chart_data_for_frontend:
                complete_metadata["chartData"] = chart_data_for_frontend
                complete_metadata["chartType"] = chart_type_for_frontend
                logger.info(f"📊 complete 消息包含图表数据")
                logger.info(f"📊 chartData.columns: {chart_data_for_frontend['columns']}")
                logger.info(f"📊 chartData.rows 数量: {len(chart_data_for_frontend['rows'])}")
                logger.info(f"📊 chartType: {chart_type_for_frontend}")
            else:
                logger.warning(f"⚠️ complete 消息不包含图表数据")
            
            await self.websocket_service.send_message(
                session_id=context.session_id,
                message_type=StreamMessageType.COMPLETE,  # 使用新增的 COMPLETE 类型
                content="流程已完成",
                metadata=complete_metadata
            )
            logger.info("✅ complete 消息已发送")
            
            # 🆕 Task 16: 持久化历史对话到数据库
            logger.info("=" * 80)
            logger.info("💾 Task 16: 持久化历史对话到数据库")
            logger.info("=" * 80)
            try:
                # 设置数据库会话
                db = next(get_db())
                self.context_manager.set_db_session(db)
                
                # 持久化会话到数据库
                success = await self.context_manager.persist_session_to_db(context.session_id)
                
                if success:
                    logger.info(f"✅ 历史对话已持久化到数据库")
                    logger.info(f"📊 会话ID: {context.session_id}")
                    
                    # 获取持久化后的统计信息
                    session_stats = self.context_manager.get_session_stats(context.session_id)
                    logger.info(f"📊 会话统计: {session_stats}")
                else:
                    logger.warning(f"⚠️ 历史对话持久化失败")
                
                db.close()
            except Exception as e:
                logger.error(f"❌ 持久化历史对话失败: {str(e)}", exc_info=True)
            logger.info("=" * 80)
            
            return {
                "success": True,
                "session_id": context.session_id,
                "intent": context.intent.value,
                "tables": context.selected_tables,
                "sql": context.generated_sql,
                "result": context.query_result,
                "stage": context.current_stage.value
            }
            
        except Exception as e:
            logger.error(f"对话流水线执行失败: {str(e)}")
            return await self._handle_pipeline_error(context, "流水线执行失败", str(e))
    
    def _map_intent_to_enum(self, intent_str: str) -> str:
        """
        将 AI 返回的意图字符串映射到 ChatIntent 枚举值
        
        Args:
            intent_str: AI 返回的意图字符串（如 "query", "report" 等）
            
        Returns:
            ChatIntent 枚举对应的字符串值
        """
        # 意图映射表
        intent_mapping = {
            "query": "smart_query",           # 智能问数
            "smart_query": "smart_query",     # 已经是正确格式
            "report": "report_generation",    # 生成报告
            "report_generation": "report_generation",  # 已经是正确格式
            "followup": "data_followup",      # 数据追问
            "data_followup": "data_followup", # 已经是正确格式
            "clarification": "clarification", # 澄清确认
            "unknown": "unknown"              # 未知意图
        }
        
        # 转换为小写进行匹配
        intent_lower = intent_str.lower().strip()
        
        # 返回映射后的值，如果找不到则返回 unknown
        mapped_intent = intent_mapping.get(intent_lower, "unknown")
        
        logger.info(f"意图映射: {intent_str} -> {mapped_intent}")
        
        return mapped_intent
    
    async def _recognize_intent(self, context: ChatContext, user_question: str) -> Dict[str, Any]:
        """意图识别（使用 prompts.yml 模板 + 流式输出）"""
        stage_id = "intent_recognition"
        stage_name = "意图识别"
        # 🆕 i18n: 翻译 stage 标签
        from src.utils.language_detector import translate_stage_label
        stage_name = translate_stage_label(stage_name, context.metadata.get('response_language', 'zh'))
        
        try:
            # 🆕 格式化历史对话上下文
            history_messages = context.metadata.get('history_messages', [])
            history_context = self._format_history_context(history_messages)
            
            # 🆕 使用 PromptManager 渲染意图识别模板（包含历史上下文和当前时间）
            prompt = self.prompt_manager.render_prompt(
                PromptType.INTENT_RECOGNITION,
                {
                    "user_question": user_question,
                    "history_context": history_context,
                    "current_date": self._format_current_date_with_ranges()
                }
            )
            
            # 🆕 i18n: 注入语言指令
            from src.utils.language_detector import inject_language_instruction, translate_stage_label
            lang = context.metadata.get('response_language', 'zh')
            prompt = inject_language_instruction(prompt, lang, stage="intent_recognition")
            stage_name = translate_stage_label(stage_name, lang)
            
            logger.info(f"✅ 使用 prompts.yml 中的 intent_recognition 模板")
            logger.info(f"📊 历史消息数量: {len(history_messages)}")
            logger.info(f"📅 当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
            # 📝 记录完整的 AI Prompt
            request_logger.log_ai_prompt(
                prompt_type="意图识别 (Intent Recognition)",
                prompt_content=prompt,
                context={
                    "user_question": user_question,
                    "session_id": context.session_id,
                    "history_messages_count": len(history_messages)
                }
            )
            
            # 🌊 1. 发送 stage_start（空内容）
            logger.info(f"🌊 发送 stage_start: {stage_id}")
            await self.websocket_service.send_stage_start(
                session_id=context.session_id,
                stage_id=stage_id,
                stage_name=stage_name,
                content=""
            )
            
            # 🌊 2. 使用流式调用获取内容块（带超时和错误处理）
            logger.info(f"🌊 开始流式调用模型（路由）...")
            accumulated_content = ""
            chunk_count = 0
            streaming_start_time = time.time()
            STREAMING_TIMEOUT = self.streaming_timeout  # 使用配置的超时时间
            
            # 检查是否启用流式输出
            if not self.enable_streaming:
                logger.info("⚠️ 流式输出已禁用，使用非流式调用")
                response = await self.ai_service.call_model(stage="intent_recognition", 
                    prompt=prompt, 
                    session_id=context.session_id,
                    model_type="qwen"
                )
                if response["success"]:
                    accumulated_content = response["content"]
                    logger.info(f"✅ 非流式调用成功，内容长度: {len(accumulated_content)} 字符")
                else:
                    raise Exception(f"非流式调用失败: {response.get('error')}")
            else:
                try:
                    async for chunk in self.ai_service.call_model_stream(stage="intent_recognition", 
                        prompt=prompt, 
                        session_id=context.session_id,
                        model_type="qwen"
                    ):
                        # 检查超时
                        elapsed_time = time.time() - streaming_start_time
                        if elapsed_time > STREAMING_TIMEOUT:
                            logger.error(f"❌ 流式调用超时: {elapsed_time:.2f}秒 > {STREAMING_TIMEOUT}秒")
                            logger.info(f"📦 超时前已接收 {chunk_count} 个块，累积内容: {len(accumulated_content)} 字符")
                            
                            # 发送已累积的内容
                            if accumulated_content:
                                logger.info(f"⚠️ 发送超时前累积的内容作为最终结果")
                                break
                            else:
                                raise asyncio.TimeoutError(f"流式调用超时（{STREAMING_TIMEOUT}秒），且无累积内容")
                        
                        # 累积内容
                        accumulated_content += chunk
                        chunk_count += 1
                        
                        # 🌊 3. 发送 stage_update（增量块）
                        try:
                            await self.websocket_service.send_stage_update(
                                session_id=context.session_id,
                                stage_id=stage_id,
                                content=chunk
                            )
                            logger.debug(f"📦 发送 chunk #{chunk_count}, 大小: {len(chunk)} 字符")
                        except Exception as ws_error:
                            logger.warning(f"⚠️ 发送 stage_update 失败: {str(ws_error)}", exc_info=True)
                            # 继续累积内容，即使 WebSocket 发送失败
                    
                    logger.info(f"🌊 流式调用完成，共 {chunk_count} 个块，总长度: {len(accumulated_content)} 字符")
                    
                except asyncio.TimeoutError as timeout_error:
                    logger.error(f"❌ 流式调用超时: {str(timeout_error)}", exc_info=True)
                    logger.info(f"📦 超时时已累积内容: {len(accumulated_content)} 字符")
                    
                    # 如果有累积内容，使用它；否则尝试降级
                    if not accumulated_content:
                        logger.warning("⚠️ 超时且无累积内容，降级到非流式调用...")
                        try:
                            response = await self.ai_service.call_model(stage="intent_recognition", 
                                prompt=prompt, 
                                session_id=context.session_id,
                                model_type="qwen"
                            )
                            if response["success"]:
                                accumulated_content = response["content"]
                                logger.info(f"✅ 非流式调用成功，内容长度: {len(accumulated_content)} 字符")
                            else:
                                raise Exception(f"非流式调用也失败: {response.get('error')}")
                        except Exception as fallback_error:
                            logger.error(f"❌ 降级到非流式调用也失败: {str(fallback_error)}")
                            raise Exception(f"流式调用超时且降级失败: {str(fallback_error)}")
                    else:
                        logger.info(f"⚠️ 使用超时前累积的内容: {len(accumulated_content)} 字符")
                        
                except Exception as stream_error:
                    logger.error(f"❌ 流式调用失败: {str(stream_error)}", exc_info=True)
                    logger.info(f"📦 失败时已累积内容: {len(accumulated_content)} 字符")
                    
                    # 如果有累积内容，使用它；否则尝试降级
                    if not accumulated_content:
                        logger.warning("⚠️ 流式失败且无累积内容，降级到非流式调用...")
                        try:
                            response = await self.ai_service.call_model(stage="intent_recognition", 
                                prompt=prompt, 
                                session_id=context.session_id,
                                model_type="qwen"
                            )
                            if response["success"]:
                                accumulated_content = response["content"]
                                logger.info(f"✅ 非流式调用成功，内容长度: {len(accumulated_content)} 字符")
                            else:
                                raise Exception(f"非流式调用也失败: {response.get('error')}")
                        except Exception as fallback_error:
                            logger.error(f"❌ 降级到非流式调用也失败: {str(fallback_error)}")
                            raise Exception(f"流式调用失败且降级失败: {str(fallback_error)}")
                    else:
                        logger.info(f"⚠️ 使用失败前累积的内容: {len(accumulated_content)} 字符")
            
            # 📝 记录 AI 原始响应（详细）
            logger.info("=" * 80)
            logger.info("🤖 AI 原始响应 - 意图识别")
            logger.info("=" * 80)
            logger.info(f"📊 响应长度: {len(accumulated_content)} 字符")
            logger.info("")
            logger.info("-" * 80)
            logger.info(f"📝 AI 返回的原始内容：")
            logger.info("-" * 80)
            logger.info(accumulated_content)
            logger.info("-" * 80)
            logger.info("=" * 80)
            
            # 📝 使用 request_logger 记录（用于审计）
            request_logger.log_ai_response(
                response_type="意图识别响应",
                response_content=accumulated_content,
                metadata={
                    "success": True,
                    "session_id": context.session_id,
                    "streaming": True,
                    "chunk_count": chunk_count
                }
            )
            
            # 🌊 4. 解析累积的完整响应
            try:
                result = json.loads(accumulated_content)
                # 🔧 映射 AI 返回的意图到 ChatIntent 枚举值
                raw_intent = result["intent"]
                mapped_intent = self._map_intent_to_enum(raw_intent)
                
                # 📝 记录解析后的意图结果
                logger.info("=" * 80)
                logger.info("📊 意图识别结果解析")
                logger.info("=" * 80)
                logger.info(f"✅ 原始意图: {raw_intent}")
                logger.info(f"✅ 映射后意图: {mapped_intent}")
                logger.info(f"📊 置信度: {result.get('confidence', 0.8)}")
                logger.info(f"📝 原因: {result.get('reason', '')}")
                logger.info("=" * 80)
                
                # 🌊 5. 格式化最终结果（i18n：根据语言选择文字）
                _ir_lang = context.metadata.get('response_language', 'zh')
                if _ir_lang == 'en':
                    intent_name = "Smart Query" if mapped_intent == "smart_query" else "Report Generation"
                    formatted_result = f"Intent recognized: {intent_name}\nConfidence: {result.get('confidence', 0.8)}"
                else:
                    intent_name = "智能问数" if mapped_intent == "smart_query" else "生成报告"
                    formatted_result = f"意图识别完成：{intent_name}\n置信度：{result.get('confidence', 0.8)}"
                
                # 🌊 6. 发送 stage_complete（格式化结果）
                logger.info(f"🌊 发送 stage_complete: {stage_id}")
                await self.websocket_service.send_stage_complete(
                    session_id=context.session_id,
                    stage_id=stage_id,
                    stage_name=stage_name,
                    content=formatted_result,
                    metadata={
                        "intent": mapped_intent,
                        "intent_name": intent_name,
                        "confidence": result.get("confidence", 0.8),
                        "reason": result.get("reason", "")
                    }
                )
                
                return {
                    "success": True,
                    "intent": mapped_intent,
                    "confidence": result.get("confidence", 0.8),
                    "reason": result.get("reason", "")
                }
                
            except json.JSONDecodeError as json_error:
                # 如果JSON解析失败，使用简单规则
                logger.warning(f"⚠️ JSON 解析失败: {str(json_error)}，使用降级策略")
                fallback_result = self._fallback_intent_recognition(user_question)
                
                # 发送 stage_complete（降级结果）
                _fb_lang = context.metadata.get('response_language', 'zh')
                _fb_content = (
                    f"Intent recognized (fallback): {fallback_result['intent']}"
                    if _fb_lang == 'en'
                    else f"意图识别完成（降级）：{fallback_result['intent']}"
                )
                await self.websocket_service.send_stage_complete(
                    session_id=context.session_id,
                    stage_id=stage_id,
                    stage_name=stage_name,
                    content=_fb_content,
                    metadata=fallback_result
                )
                
                return fallback_result
                
        except Exception as e:
            logger.error(f"意图识别失败: {str(e)}", exc_info=True)
            
            # 发送错误的 stage_complete
            await self.websocket_service.send_stage_complete(
                session_id=context.session_id,
                stage_id=stage_id,
                stage_name=stage_name,
                content=f"意图识别失败: {str(e)}",
                metadata={"error": str(e), "status": "error"}
            )
            
            return {
                "success": False,
                "error": str(e)
            }
    
    def _fallback_intent_recognition(self, user_question: str) -> Dict[str, Any]:
        """意图识别降级策略"""
        question_lower = user_question.lower()
        
        # 简单关键词匹配
        if any(word in question_lower for word in ["查询", "多少", "统计", "数量", "金额"]):
            return {"success": True, "intent": "smart_query", "confidence": 0.7}
        elif any(word in question_lower for word in ["报告", "分析", "总结", "汇总"]):
            return {"success": True, "intent": "report_generation", "confidence": 0.7}
        elif any(word in question_lower for word in ["为什么", "原因", "详细", "进一步"]):
            return {"success": True, "intent": "data_followup", "confidence": 0.7}
        else:
            return {"success": True, "intent": "smart_query", "confidence": 0.5}
    
    async def _select_tables(self, context: ChatContext, user_question: str, data_source_id: Optional[str]) -> Dict[str, Any]:
        """智能选表（使用 prompts.yml 模板，增强版）"""
        try:
            # 🔍 检查用户是否已选择数据表
            user_selected_tables = context.metadata.get('user_selected_tables', [])
            has_user_selection = bool(user_selected_tables)
            
            logger.info("=" * 80)
            logger.info("🔍 智能选表 - 用户选择状态检查")
            logger.info("=" * 80)
            logger.info(f"📋 用户是否已选择数据表: {has_user_selection}")
            if has_user_selection:
                logger.info(f"📋 用户选择的表 ID: {user_selected_tables}")
                logger.info(f"📋 用户选择的表数量: {len(user_selected_tables)}")
            else:
                logger.info(f"⚠️ 用户未选择任何数据表")
            logger.info("=" * 80)
            
            # 获取语义上下文（包含数据源信息和知识库）
            semantic_context_result = await self.semantic_aggregator.aggregate_semantic_context(
                user_question=user_question,
                table_ids=user_selected_tables if has_user_selection else None,
                include_global=True
            )
            
            # 🆕 按照清晰的结构组装语义增强上下文（v5.0 - 修复全局知识库和表级别知识库的提取逻辑）
            context_parts = []
            
            # 1. 数据源类型（从 semantic_context_result 的 Data Source 模块提取）
            context_parts.append("=" * 80)
            context_parts.append("📊 1. 数据源类型")
            context_parts.append("=" * 80)
            
            # 从 semantic_context_result.aggregated_content 中提取数据源信息
            data_source_info_found = False
            if hasattr(semantic_context_result, 'aggregated_content') and 'data_source' in semantic_context_result.aggregated_content:
                data_source_content = semantic_context_result.aggregated_content['data_source']
                if isinstance(data_source_content, dict) and 'content' in data_source_content:
                    context_parts.append(data_source_content['content'])
                    data_source_info_found = True
            
            if not data_source_info_found:
                # 尝试从 enhanced_context 中提取
                if semantic_context_result.enhanced_context:
                    lines = semantic_context_result.enhanced_context.split('\n')
                    for i, line in enumerate(lines):
                        if 'Data Source:' in line:
                            # 找到数据源部分，提取接下来的几行
                            for j in range(i + 1, min(i + 10, len(lines))):
                                next_line = lines[j]
                                if next_line.strip() and not any(keyword in next_line for keyword in ['Knowledge:', 'Table Structure:', '用户问题:']):
                                    context_parts.append(next_line)
                                elif any(keyword in next_line for keyword in ['Knowledge:', 'Table Structure:']):
                                    break
                            data_source_info_found = True
                            break
            
            if not data_source_info_found:
                context_parts.append("数据源类型：关系型数据库")
            
            context_parts.append("")
            
            # 2. 数据表详细信息（表描述、字段描述、数据字典、表关联，来自 _get_enhanced_table_context）
            context_parts.append("=" * 80)
            context_parts.append("📋 2. 数据表详细信息")
            context_parts.append("=" * 80)
            
            # 获取增强的表上下文（包含字段描述、数据字典、表关联）
            enhanced_context_str = await self._get_enhanced_table_context(
                data_source_id=data_source_id,
                user_selected_tables=user_selected_tables if has_user_selection else None
            )
            context_parts.append(enhanced_context_str)
            context_parts.append("")
            
            # 3. 全局知识库（从 semantic_context_result 的 Knowledge 模块提取，类型为"全局"的知识）
            context_parts.append("=" * 80)
            context_parts.append("🌐 3. 全局知识库")
            context_parts.append("=" * 80)
            
            global_knowledge_found = False
            
            logger.info("=" * 80)
            logger.info("🔍 调试：全局知识库提取")
            logger.info("=" * 80)
            logger.info(f"📊 semantic_context_result 类型: {type(semantic_context_result)}")
            logger.info(f"📊 是否有 aggregated_content: {hasattr(semantic_context_result, 'aggregated_content')}")
            
            # 🆕 从 aggregated_content 中提取知识库信息
            if hasattr(semantic_context_result, 'aggregated_content') and semantic_context_result.aggregated_content:
                logger.info(f"📊 aggregated_content 键: {semantic_context_result.aggregated_content.keys()}")
                
                if 'knowledge' in semantic_context_result.aggregated_content:
                    knowledge_content = semantic_context_result.aggregated_content['knowledge']
                    logger.info(f"📊 knowledge_content 类型: {type(knowledge_content)}")
                    logger.info(f"📊 knowledge_content 键: {knowledge_content.keys() if isinstance(knowledge_content, dict) else 'N/A'}")
                    
                    if isinstance(knowledge_content, dict):
                        # 提取全局知识
                        global_knowledge_items = knowledge_content.get('global_knowledge', [])
                        logger.info(f"📊 global_knowledge_items 数量: {len(global_knowledge_items)}")
                        
                        if global_knowledge_items:
                            logger.info(f"📊 第一个 item: {global_knowledge_items[0]}")
                            
                            for idx, item in enumerate(global_knowledge_items):
                                logger.info(f"🔍 处理全局知识项 #{idx + 1}: {item}")
                                
                                # item 是一个字典，包含 knowledge_content 键
                                if isinstance(item, dict):
                                    knowledge_content_str = item.get('knowledge_content', '')
                                    logger.info(f"   ✅ 提取到 knowledge_content: {knowledge_content_str}")
                                    if knowledge_content_str:
                                        context_parts.append(f"  - {knowledge_content_str}")
                                        global_knowledge_found = True
                                    else:
                                        logger.warning(f"   ⚠️ knowledge_content 为空")
                                else:
                                    logger.warning(f"   ⚠️ item 不是字典类型: {type(item)}")
                        else:
                            logger.info("📊 global_knowledge_items 为空列表")
                    else:
                        logger.warning(f"⚠️ knowledge_content 不是字典类型")
                else:
                    logger.warning("⚠️ aggregated_content 中没有 knowledge 键")
            else:
                logger.warning("⚠️ semantic_context_result 没有 aggregated_content 或为空")
            
            logger.info("=" * 80)
            
            if not global_knowledge_found:
                context_parts.append("（暂无全局知识库信息）")
                logger.info("📊 最终结果：未找到全局知识库信息")
            else:
                logger.info(f"📊 最终结果：找到全局知识库信息")
            
            context_parts.append("")
            
            # 4. 表级别知识库（从 semantic_context_result 的 Knowledge 模块提取，类型为"表级别"且关联了用户选择的表的知识）
            context_parts.append("=" * 80)
            context_parts.append("📚 4. 表级别知识库")
            context_parts.append("=" * 80)
            
            table_knowledge_found = False
            
            logger.info("=" * 80)
            logger.info("🔍 调试：表级别知识库提取")
            logger.info("=" * 80)
            
            # 🆕 从 aggregated_content 中提取表级别知识库信息
            if hasattr(semantic_context_result, 'aggregated_content') and semantic_context_result.aggregated_content:
                if 'knowledge' in semantic_context_result.aggregated_content:
                    knowledge_content = semantic_context_result.aggregated_content['knowledge']
                    
                    if isinstance(knowledge_content, dict):
                        # 提取表级别知识
                        table_knowledge_items = knowledge_content.get('table_knowledge', [])
                        logger.info(f"📊 table_knowledge_items 数量: {len(table_knowledge_items)}")
                        
                        if table_knowledge_items:
                            logger.info(f"📊 第一个 item: {table_knowledge_items[0]}")
                            
                            for idx, item in enumerate(table_knowledge_items):
                                logger.info(f"🔍 处理表级别知识项 #{idx + 1}: {item}")
                                
                                # item 是一个字典，包含 knowledge_content 和 related_table_ids 键
                                if isinstance(item, dict):
                                    knowledge_content_str = item.get('knowledge_content', '')
                                    related_table_ids = item.get('related_table_ids', [])
                                    
                                    logger.info(f"   📋 knowledge_content: {knowledge_content_str}")
                                    logger.info(f"   📋 related_table_ids: {related_table_ids}")
                                    logger.info(f"   📋 user_selected_tables: {user_selected_tables}")
                                    
                                    # 检查知识是否关联了用户选择的表
                                    if not has_user_selection or not related_table_ids or any(tid in user_selected_tables for tid in related_table_ids):
                                        if knowledge_content_str:
                                            context_parts.append(f"  - {knowledge_content_str}")
                                            table_knowledge_found = True
                                            logger.info(f"   ✅ 已添加到上下文")
                                        else:
                                            logger.warning(f"   ⚠️ knowledge_content 为空")
                                    else:
                                        logger.info(f"   ⏭️  跳过（表不匹配）")
                                else:
                                    logger.warning(f"   ⚠️ item 不是字典类型: {type(item)}")
                        else:
                            logger.info("📊 table_knowledge_items 为空列表")
                    else:
                        logger.warning(f"⚠️ knowledge_content 不是字典类型")
                else:
                    logger.warning("⚠️ aggregated_content 中没有 knowledge 键")
            else:
                logger.warning("⚠️ semantic_context_result 没有 aggregated_content 或为空")
            
            logger.info("=" * 80)
            
            if not table_knowledge_found:
                context_parts.append("（暂无表级别知识库信息）")
                logger.info("📊 最终结果：未找到表级别知识库信息")
            else:
                logger.info(f"📊 最终结果：找到表级别知识")

            
            context_parts.append("")
            
            # 合并所有上下文
            combined_context = "\n".join(context_parts)
            
            # 🆕 格式化历史对话上下文
            history_messages = context.metadata.get('history_messages', [])
            history_context = self._format_history_context(history_messages)
            
            # 🆕 使用 PromptManager 渲染智能选表模板（包含历史上下文和当前时间）
            prompt = self.prompt_manager.render_prompt(
                PromptType.TABLE_SELECTION,
                {
                    "user_question": user_question,
                    "intent_type": context.intent.value,
                    "semantic_context": combined_context,
                    "history_context": history_context,  # 🆕 添加历史对话上下文
                    "current_date": self._format_current_date_with_ranges()  # 🆕 添加当前时间和预计算范围
                }
            )
            
            # 🆕 i18n: 注入语言指令
            from src.utils.language_detector import inject_language_instruction
            lang = context.metadata.get('response_language', 'zh')
            prompt = inject_language_instruction(prompt, lang, stage="table_selection")
            
            # 🔧 如果用户未选择数据表，添加特殊指令
            if not has_user_selection:
                prompt += """

⚠️ 重要提示：用户尚未选择任何数据表。

请在响应中明确提醒用户：
"您还没有选择数据表，请先在数据准备页面选择需要分析的数据表，然后再提问。"

同时，基于问题内容，建议用户可能需要的表（如果能从上下文中推断）。

响应格式示例：
{
  "selectedTables": [],
  "overallReasoning": "您还没有选择数据表，请先在数据准备页面选择需要分析的数据表。根据您的问题，建议选择以下表：orders（订单表）、users（用户表）。"
}
"""
            
            logger.info(f"✅ 使用 prompts.yml 中的 table_selection 模板（v4.0 - 结构化版本）")
            logger.info(f"📊 用户选表状态: {'已选择' if has_user_selection else '未选择'}")
            
            # 📝 记录完整的 AI Prompt
            request_logger.log_ai_prompt(
                prompt_type="智能选表 (Table Selection - Enhanced)",
                prompt_content=prompt,
                context={
                    "user_question": user_question,
                    "intent_type": context.intent.value,
                    "has_user_selection": has_user_selection,
                    "user_selected_tables": user_selected_tables,
                    "session_id": context.session_id
                }
            )
            
            # 🌊 使用流式调用云端模型进行选表
            stage_id = "table_selection"
            stage_name = "智能选表"
            # 🆕 i18n: 翻译 stage 标签
            from src.utils.language_detector import translate_stage_label
            stage_name = translate_stage_label(stage_name, context.metadata.get('response_language', 'zh'))
            logger.info("🌊 开始流式调用模型进行智能选表...")
            await self.websocket_service.send_stage_start(
                session_id=context.session_id,
                stage_id=stage_id,
                stage_name=stage_name,
                content=""
            )
            accumulated_content = ""
            chunk_count = 0
            
            try:
                async for chunk in self.ai_service.call_model_stream(stage="table_selection", 
                    prompt=prompt,
                    session_id=context.session_id,
                    model_type="qwen"
                ):
                    # 累积内容（chunk 是字符串，不是字典）
                    accumulated_content += chunk
                    chunk_count += 1
                    
                    # 发送流式内容到前端
                    try:
                        await self.websocket_service.send_stage_update(
                            session_id=context.session_id,
                            stage_id=stage_id,
                            content=chunk
                        )
                        logger.debug(f"📦 发送 chunk #{chunk_count}, 大小: {len(chunk)} 字符")
                    except Exception as ws_error:
                        logger.warning(f"⚠️ 发送 stage_update 失败: {str(ws_error)}", exc_info=True)
                        # 继续累积内容，即使 WebSocket 发送失败
                
                logger.info(f"🌊 流式调用完成，共 {chunk_count} 个块，总长度: {len(accumulated_content)} 字符")
                
                # 构建响应对象
                response = {
                    "success": True,
                    "content": accumulated_content
                }
                
            except Exception as stream_error:
                logger.error(f"❌ 流式调用失败: {str(stream_error)}", exc_info=True)
                raise
            
            # 📝 记录 AI 原始响应（详细）
            logger.info("=" * 80)
            logger.info("🤖 AI 原始响应 - 智能选表")
            logger.info("=" * 80)
            logger.info(f"📊 响应状态: {'✅ 成功' if response.get('success') else '❌ 失败'}")
            if not response.get('success'):
                logger.error(f"❌ 错误信息: {response.get('error', 'Unknown error')}")
            logger.info(f"📊 响应长度: {len(response.get('content', ''))} 字符")
            logger.info("")
            logger.info("-" * 80)
            logger.info(f"📝 AI 返回的原始内容：")
            logger.info("-" * 80)
            logger.info(response.get('content', ''))
            logger.info("-" * 80)
            logger.info("=" * 80)
            
            # 📝 使用 request_logger 记录（用于审计）
            request_logger.log_ai_response(
                response_type="智能选表响应",
                response_content=response.get("content", ""),
                metadata={
                    "success": response.get("success"),
                    "has_user_selection": has_user_selection,
                    "session_id": context.session_id
                }
            )
            
            if response["success"]:
                try:
                    raw_content = response.get("content", "")
                    logger.info(f"🔧 原始内容长度: {len(raw_content)} 字符")
                    result = self._extract_first_json_object(raw_content)
                    if not isinstance(result, dict):
                        raise ValueError("选表响应不是 JSON 对象")
                    
                    # 📝 记录解析后的选表结果
                    logger.info("=" * 80)
                    logger.info("📊 智能选表结果解析")
                    logger.info("=" * 80)
                    
                    # 提取选中的表名列表（只用 tableName，不用 tableId，因为 AI 会编造假 ID）
                    selected_table_names = []
                    if "selectedTables" in result and isinstance(result["selectedTables"], list):
                        selected_table_names = [t.get("tableName") for t in result["selectedTables"] if t and t.get("tableName")]
                    
                    # 🔒 验证：如果用户已选择表，确保 AI 返回的表都在用户选择范围内
                    # 需要建立表名 → UUID 的映射
                    selected_tables = []
                    if has_user_selection and selected_table_names:
                        # 建立表名到 UUID 的映射
                        from src.services.data_table_service import DataTableService
                        from src.database import get_db
                        
                        db = next(get_db())
                        table_service = DataTableService()
                        
                        # 获取用户选择的表的名称映射
                        table_name_to_id = {}
                        for table_id in user_selected_tables:
                            table = table_service.get_table_by_id(db, table_id)
                            if table:
                                table_name_to_id[table.table_name] = table_id
                        
                        logger.info(f"📋 表名到 UUID 映射: {table_name_to_id}")
                        
                        # 将 AI 返回的表名转换为 UUID
                        for table_name in selected_table_names:
                            if table_name in table_name_to_id:
                                selected_tables.append(table_name_to_id[table_name])
                            else:
                                logger.warning(f"⚠️ AI 返回的表名 '{table_name}' 不在用户选择的表中")
                        
                        if len(selected_tables) < len(selected_table_names):
                            logger.warning(f"⚠️ 过滤掉了 {len(selected_table_names) - len(selected_tables)} 个用户未选择的表")
                            logger.error(f"📋 用户选择的表 UUID: {user_selected_tables}")
                            logger.error(f"📋 用户选择的表名: {list(table_name_to_id.keys())}")
                            logger.error(f"📋 AI 返回的表名: {selected_table_names}")
                            logger.error(f"📋 映射后的 UUID: {selected_tables}")
                    elif not has_user_selection:
                        # 用户未选择表，AI 返回的是表名，需要转换为 UUID
                        selected_tables = selected_table_names
                    
                    logger.info(f"✅ 选中的表数量: {len(selected_tables)}")
                    if selected_tables:
                        logger.info(f"📋 选中的表: {', '.join(selected_tables)}")
                    logger.info(f"📝 选表原因: {result.get('overallReasoning', '')}")
                    
                    # 如果用户未选表且AI也没有返回表，标记需要用户手动选择
                    needs_manual_selection = not has_user_selection and not selected_tables
                    
                    if needs_manual_selection:
                        logger.warning("⚠️ 需要用户手动选择数据表")
                    
                    logger.info("=" * 80)
                    
                    # 🌊 发送 stage_complete（选表完成）
                    overall_reasoning = result.get("overallReasoning", "")
                    await self.websocket_service.send_stage_complete(
                        session_id=context.session_id,
                        stage_id=stage_id,
                        stage_name=stage_name,
                        content=overall_reasoning,
                        metadata={
                            "selected_tables": selected_tables,
                            "reason": overall_reasoning
                        }
                    )
                    
                    return {
                        "success": True,
                        "tables": selected_tables,
                        "reason": overall_reasoning,
                        "needs_clarification": needs_manual_selection,
                        "clarification_question": overall_reasoning if needs_manual_selection else ""
                    }
                except (json.JSONDecodeError, ValueError) as e:
                    err_msg = getattr(e, "msg", str(e))
                    logger.error("=" * 80)
                    logger.error("❌ JSON 解析失败")
                    if isinstance(e, json.JSONDecodeError):
                        logger.error(f"📍 错误位置: 行 {e.lineno}, 列 {e.colno}")
                    logger.error(f"📝 错误信息: {err_msg}")
                    logger.error(f"📄 原始内容（前500字符）:")
                    logger.error(response.get("content", "")[:500])
                    logger.error("=" * 80)

                    # 兜底：用户已手动选表时，不因模型未输出 JSON 而中断流程
                    if has_user_selection and user_selected_tables:
                        fallback_reason = (
                            "模型未返回结构化选表JSON，已回退使用用户已选择的数据表继续执行。"
                        )
                        logger.warning(
                            f"⚠️ 选表阶段 JSON 解析失败，fallback 到用户选表: {user_selected_tables}"
                        )
                        await self.websocket_service.send_stage_complete(
                            session_id=context.session_id,
                            stage_id=stage_id,
                            stage_name=stage_name,
                            content=fallback_reason,
                            metadata={
                                "selected_tables": user_selected_tables,
                                "reason": fallback_reason,
                                "fallback": "user_selected_tables",
                                "parse_error": err_msg,
                            },
                        )
                        return {
                            "success": True,
                            "tables": user_selected_tables,
                            "reason": fallback_reason,
                            "needs_clarification": False,
                            "clarification_question": "",
                        }

                    # 🌊 发送 stage_complete（解析失败）
                    await self.websocket_service.send_stage_complete(
                        session_id=context.session_id,
                        stage_id=stage_id,
                        stage_name=stage_name,
                        content=f"选表结果解析失败: {err_msg}",
                        metadata={"error": str(e)}
                    )
                    return {
                        "success": False,
                        "error": f"选表结果解析失败: {err_msg}"
                    }
            else:
                # 🌊 发送 stage_complete（AI 调用失败）
                await self.websocket_service.send_stage_complete(
                    session_id=context.session_id,
                    stage_id=stage_id,
                    stage_name=stage_name,
                    content=response.get("error", "选表失败"),
                    metadata={"error": response.get("error")}
                )
                return {
                    "success": False,
                    "error": response.get("error", "选表失败")
                }
                
        except Exception as e:
            logger.error(f"智能选表失败: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _get_enhanced_table_context(
        self,
        data_source_id: Optional[str],
        user_selected_tables: Optional[List[str]] = None
    ) -> str:
        """
        获取增强的表上下文信息
        包含：字段描述、数据字典关联、表关联关系
        """
        try:
            if not data_source_id:
                return "⚠️ 未提供数据源ID，无法获取表信息"
            
            from src.services.data_table_service import DataTableService
            from src.services.data_preparation_service import DictionaryService
            from src.database import get_db
            
            db_session = next(get_db())
            table_service = DataTableService()
            dict_service = DictionaryService()
            
            context_parts = []
            
            # 如果用户已选择表，获取这些表的详细信息
            if user_selected_tables:
                context_parts.append("=" * 80)
                context_parts.append(f"📋 用户已选择的数据表（共 {len(user_selected_tables)} 个）")
                context_parts.append("=" * 80)
                
                for table_id in user_selected_tables:
                    try:
                        # 获取表基本信息
                        table = table_service.get_table_by_id(db_session, table_id)
                        if not table:
                            continue
                        
                        context_parts.append(f"\n表名: {table.table_name}")
                        if table.display_name:
                            context_parts.append(f"显示名称: {table.display_name}")
                        if table.description:
                            context_parts.append(f"表描述: {table.description}")
                        
                        # 获取字段信息（包含字段描述和数据字典关联）
                        fields = table_service.get_table_columns(db_session, table_id)
                        if fields:
                            context_parts.append(f"\n字段列表（共 {len(fields)} 个字段）:")
                            for field in fields:
                                field_info = f"  - {field.field_name} ({field.data_type})"
                                
                                # 添加主键标识
                                if field.is_primary_key:
                                    field_info += " [主键]"
                                
                                # 添加非空标识
                                if not field.is_nullable:
                                    field_info += " [非空]"
                                
                                # 添加字段描述
                                if field.description:
                                    field_info += f"\n    描述: {field.description}"
                                
                                # 🆕 添加数据字典关联信息
                                if hasattr(field, 'dictionary_id') and field.dictionary_id:
                                    try:
                                        logger.info(f"🔍 字段 {field.field_name} 关联了字典 ID: {field.dictionary_id}")
                                        dictionary = dict_service.get_dictionary_by_id(db_session, field.dictionary_id)
                                        if dictionary:
                                            field_info += f"\n    关联字典: {dictionary.name} ({dictionary.code})"
                                            
                                            # 获取字典项（返回字典格式：{'items': [...], 'total': N}）
                                            dict_items_result = dict_service.get_dictionary_items(
                                                db_session, 
                                                field.dictionary_id,
                                                page=1,
                                                page_size=5
                                            )
                                            if dict_items_result and isinstance(dict_items_result, dict) and 'items' in dict_items_result:
                                                items = dict_items_result['items']
                                                total = dict_items_result.get('total', len(items))
                                                if items:
                                                    items_preview = ", ".join([f"{item['item_key']}={item['item_value']}" for item in items])
                                                    if total > len(items):
                                                        items_preview += f" ... (共{total}项)"
                                                    field_info += f"\n    字典项: {items_preview}"
                                        else:
                                            logger.warning(f"⚠️ 字段 {field.field_name} 的字典 {field.dictionary_id} 不存在")
                                    except Exception as e:
                                        logger.warning(f"获取字段 {field.field_name} 的字典信息失败: {str(e)}")
                                else:
                                    # 记录字段没有关联字典（仅用于调试）
                                    if hasattr(field, 'dictionary_id'):
                                        logger.debug(f"字段 {field.field_name} 没有关联字典（dictionary_id={field.dictionary_id}）")
                                
                                context_parts.append(field_info)
                        
                        # 🆕 获取表关联关系
                        try:
                            from src.models.data_preparation_model import TableRelation  # 🔧 修复导入路径
                            from sqlalchemy import or_
                            
                            relations = db_session.query(TableRelation).filter(
                                or_(
                                    TableRelation.primary_table_id == table_id,
                                    TableRelation.foreign_table_id == table_id
                                ),
                                TableRelation.status == True
                            ).all()
                            
                            if relations:
                                context_parts.append(f"\n表关联关系（共 {len(relations)} 个）:")
                                for rel in relations:
                                    # 获取关联表的名称
                                    primary_table = table_service.get_table_by_id(db_session, rel.primary_table_id)
                                    foreign_table = table_service.get_table_by_id(db_session, rel.foreign_table_id)
                                    
                                    primary_table_name = primary_table.table_name if primary_table else rel.primary_table_id
                                    foreign_table_name = foreign_table.table_name if foreign_table else rel.foreign_table_id
                                    
                                    # 🔧 修复：通过关联对象获取字段名
                                    primary_field_name = rel.primary_field.field_name if rel.primary_field else "unknown"
                                    foreign_field_name = rel.foreign_field.field_name if rel.foreign_field else "unknown"
                                    
                                    rel_info = f"  - {rel.relation_name or '未命名关联'}"
                                    rel_info += f"\n    {primary_table_name}.{primary_field_name} → {foreign_table_name}.{foreign_field_name}"
                                    rel_info += f"\n    连接类型: {rel.join_type or 'INNER JOIN'}"
                                    if rel.description:
                                        rel_info += f"\n    描述: {rel.description}"
                                    context_parts.append(rel_info)
                        except Exception as e:
                            logger.warning(f"获取表 {table.table_name} 的关联关系失败: {str(e)}")
                        
                        context_parts.append("")  # 空行分隔
                        
                    except Exception as e:
                        logger.warning(f"获取表 {table_id} 的详细信息失败: {str(e)}")
                        continue
            else:
                # 用户未选择表，获取数据源下所有可用表的概览
                context_parts.append("=" * 80)
                context_parts.append("⚠️ 用户尚未选择数据表")
                context_parts.append("=" * 80)
                context_parts.append("\n可用数据表概览:")
                
                try:
                    # 获取数据源下的所有表
                    tables = table_service.get_tables_by_source(db_session, data_source_id)
                    if tables:
                        for table in tables[:10]:  # 最多显示10个表
                            table_info = f"  - {table.table_name}"
                            if table.display_name:
                                table_info += f" ({table.display_name})"
                            if table.description:
                                table_info += f": {table.description}"
                            context_parts.append(table_info)
                        
                        if len(tables) > 10:
                            context_parts.append(f"  ... 还有 {len(tables) - 10} 个表")
                    else:
                        context_parts.append("  （暂无可用数据表）")
                except Exception as e:
                    logger.warning(f"获取数据源 {data_source_id} 的表列表失败: {str(e)}")
                    context_parts.append("  （无法获取表列表）")
            
            context_parts.append("=" * 80)
            
            return "\n".join(context_parts)
            
        except Exception as e:
            logger.error(f"获取增强表上下文失败: {str(e)}", exc_info=True)
            return f"⚠️ 获取表上下文失败: {str(e)}"
    
    def _count_tokens(self, text: str) -> int:
        """
        估算文本的Token数量
        简单估算：中文字符约1.5 tokens，英文单词约1 token，标点符号约0.5 token
        """
        if not text:
            return 0
        
        # 统计中文字符数
        chinese_chars = sum(1 for char in text if '\u4e00' <= char <= '\u9fff')
        # 统计英文单词数（简单按空格分割）
        english_words = len([word for word in text.split() if any(c.isalpha() for c in word)])
        # 统计标点符号数
        punctuation = sum(1 for char in text if not char.isalnum() and not char.isspace())
        
        # 估算总Token数
        estimated_tokens = int(chinese_chars * 1.5 + english_words * 1.0 + punctuation * 0.5)
        
        return estimated_tokens
    
    def _calculate_history_tokens(self, history_messages: List[Dict[str, Any]]) -> int:
        """计算历史消息的总Token数"""
        total_tokens = 0
        for msg in history_messages:
            content = msg.get('content', '')
            total_tokens += self._count_tokens(content)
        return total_tokens
    
    async def _get_history_context(self, context: ChatContext, user_question: str) -> str:
        """
        获取历史对话上下文（基于 Token 阈值管理）
        
        🆕 Task 15: 使用 ContextManager 获取历史对话
        
        逻辑：
        1. 从 ContextManager 获取云端历史记录（不包含业务数据）
        2. 如果历史对话 Token 数 < 阈值 (2000)
           → 返回完整历史对话
        3. 如果历史对话 Token 数 >= 阈值
           → 调用 _summarize_history_context() 进行摘要
           → 返回摘要 + 最近 3 轮完整对话
        
        Args:
            context: 对话上下文
            user_question: 当前用户问题
            
        Returns:
            格式化的历史对话上下文字符串
        """
        logger.info("=" * 80)
        logger.info("📚 Task 15: 使用 ContextManager 获取历史对话")
        logger.info("=" * 80)
        
        # 🆕 从 ContextManager 获取云端历史记录（用于发送给 AI）
        try:
            cloud_history = self.context_manager.get_cloud_history(
                context.session_id,
                max_messages=20  # 最多获取 20 条消息
            )
            logger.info(f"✅ 从 ContextManager 获取到 {len(cloud_history)} 条云端历史记录")
            
            # 记录每条消息的详细信息
            for i, msg in enumerate(cloud_history):
                logger.info(f"  消息 {i+1}: role={msg.get('role')}, content_length={len(msg.get('content', ''))}")
        except Exception as e:
            logger.error(f"❌ 从 ContextManager 获取历史记录失败: {str(e)}", exc_info=True)
            cloud_history = []
        
        # 转换为统一的消息格式
        history_messages = []
        for msg in cloud_history:
            history_messages.append({
                "role": msg["role"],
                "content": msg["content"],
                "timestamp": msg.get("timestamp", "")
            })
        
        if not history_messages:
            logger.info("ℹ️ 无历史对话上下文")
            logger.info("=" * 80)
            return ""
        
        # 计算历史对话 Token 数
        total_tokens = self._calculate_history_tokens(history_messages)
        TOKEN_THRESHOLD = 2000
        
        logger.info("=" * 80)
        logger.info("📚 历史对话上下文管理")
        logger.info(f"📊 历史消息总数: {len(history_messages)}")
        logger.info(f"📊 历史消息 Token 数: {total_tokens}")
        logger.info(f"📊 Token 阈值: {TOKEN_THRESHOLD}")
        
        if total_tokens > TOKEN_THRESHOLD:
            logger.info(f"⚠️ Token 数超过阈值，进行智能摘要")
            history_context = await self._summarize_history_context(history_messages, user_question)
        else:
            logger.info(f"✅ Token 数未超过阈值，使用完整历史对话")
            history_context = self._format_full_history(history_messages)
        
        logger.info(f"📝 历史上下文 Token 数: {self._count_tokens(history_context)}")
        logger.info("=" * 80)
        
        return history_context
    
    def _format_full_history(self, history_messages: List[Dict[str, Any]]) -> str:
        """
        格式化完整历史对话
        
        Args:
            history_messages: 历史消息列表
            
        Returns:
            格式化的历史对话字符串
        """
        history_lines = []
        for msg in history_messages:
            role_name = "用户" if msg['role'] == 'user' else "AI助手"
            content = msg['content']
            history_lines.append(f"{role_name}: {content}")
        
        if history_lines:
            return "\n\n历史对话上下文（完整对话，用于理解当前问题）：\n" + "\n".join(history_lines)
        
        return ""
    
    def _format_messages_for_summary(self, messages: List[Dict[str, Any]]) -> str:
        """
        格式化消息用于摘要
        
        Args:
            messages: 消息列表
            
        Returns:
            格式化的消息字符串
        """
        formatted_lines = []
        for msg in messages:
            role_name = "用户" if msg['role'] == 'user' else "AI助手"
            # 截断过长的内容（摘要时不需要完整内容）
            content = msg['content'][:500] + "..." if len(msg['content']) > 500 else msg['content']
            formatted_lines.append(f"{role_name}: {content}")
        
        return "\n".join(formatted_lines)
    
    async def _generate_sql(self, context: ChatContext, user_question: str, data_source_id: Optional[str], exec_error: Optional[str] = None) -> Dict[str, Any]:
        """生成SQL（包含完整语义上下文和历史对话上下文，基于Token阈值管理，支持流式输出）
        
        Args:
            exec_error: 上次 SQL 执行的错误信息，非 None 时表示这是执行失败后的重新生成
        """
        stage_id = "sql_generation"
        stage_name = "SQL生成"
        # 🆕 i18n: 翻译 stage 标签
        from src.utils.language_detector import translate_stage_label
        stage_name = translate_stage_label(stage_name, context.metadata.get('response_language', 'zh'))
        
        try:
            prompt_db_type = self._resolve_prompt_db_type(context, data_source_id)
            # 获取完整语义上下文
            logger.info("=" * 80)
            logger.info("🔍 开始获取语义上下文")
            logger.info(f"📝 用户问题: {user_question}")
            logger.info(f"📋 选定的表: {context.selected_tables}")
            
            # 🔥 设置数据库会话（关键修复）
            db = next(get_db())
            self.semantic_aggregator.db = db
            # 🔥 同时更新所有子服务的数据库会话
            self.semantic_aggregator.data_source_service.db = db
            self.semantic_aggregator.table_structure_service.db = db
            self.semantic_aggregator.table_relation_service.db = db
            self.semantic_aggregator.knowledge_service.db = db
            logger.info("✅ 已设置 SemanticContextAggregator 及其所有子服务的数据库会话")
            
            try:
                semantic_context_result = await self.semantic_aggregator.aggregate_semantic_context(
                    user_question=user_question,
                    table_ids=context.selected_tables,
                    include_global=True
                )
                
                logger.info("✅ 语义上下文获取完成")
                logger.info(f"📊 使用的模块: {semantic_context_result.modules_used}")
                logger.info(f"📊 Token使用量: {semantic_context_result.total_tokens_used}")
                logger.info(f"📊 相关性评分: {semantic_context_result.relevance_scores}")
                logger.info("=" * 80)
            finally:
                # 关闭数据库会话
                db.close()
                logger.info("✅ 数据库会话已关闭")
            
            # 📝 记录完整的语义上下文内容（用于验证）
            logger.info("=" * 80)
            logger.info("📝 完整语义上下文内容（将传递给 AI）")
            logger.info("-" * 80)
            logger.info(semantic_context_result.enhanced_context)
            logger.info("-" * 80)
            logger.info(f"📊 语义上下文长度: {len(semantic_context_result.enhanced_context)} 字符")
            logger.info(f"📊 语义上下文 Token 估算: {self._count_tokens(semantic_context_result.enhanced_context)}")
            logger.info("=" * 80)
            
            # ✅ 直接使用 semantic_context_result.enhanced_context（完整的语义上下文）
            if not semantic_context_result.enhanced_context:
                logger.error("❌ 语义上下文为空，无法生成 SQL")
                return {
                    "success": False,
                    "error": "获取语义上下文失败：上下文为空"
                }

            selected_table_ids = self._normalize_selected_table_ids(context.selected_tables)
            if len(selected_table_ids) > 1:
                self.multi_table_metrics.inc("multi_table_total")
            join_constraints = self._get_or_build_join_constraints(context, selected_table_ids)
            contract_result = self._validate_stage_contract(
                context=context,
                stage="sql_generation",
                semantic_context_result=semantic_context_result,
                join_constraints=join_constraints,
            )
            if not contract_result.get("ok"):
                contract_error = contract_result["error"]
                logger.error(f"❌ SQL 生成前置上下文校验失败: {contract_error}")
                return {
                    "success": False,
                    "error": f"上下文校验失败：{contract_error.get('message')}",
                    "error_code": contract_error.get("code"),
                    "details": contract_error,
                }
            
            # 🆕 格式化历史对话上下文
            history_messages = context.metadata.get('history_messages', [])
            history_context = self._format_history_context(history_messages)
            
            logger.info(f"📊 历史消息数量: {len(history_messages)}")
            if history_context and history_context != "无历史对话":
                logger.info(f"✅ 已准备历史对话上下文")
            else:
                logger.info(f"ℹ️ 无历史对话上下文")
            
            # 🔧 获取模型思考结果（如果存在）
            thinking_result = ""
            if hasattr(context, 'thinking_result') and context.thinking_result:
                thinking_result = context.thinking_result
                logger.info(f"✅ 获取到模型思考结果，长度: {len(thinking_result)}")
            
            # 🔧 SQL 生成重试机制（最多 3 次）
            max_retries = 3
            retry_count = 0
            last_error = None
            recall_expanded = False
            semantic_context_for_retry = semantic_context_result
            
            while retry_count < max_retries:
                should_expand_recall = (
                    not recall_expanded
                    and (retry_count > 0 or exec_error is not None)
                    and bool(last_error or exec_error)
                )
                if should_expand_recall:
                    logger.info("🔁 触发自适应扩召回：切换到 expanded profile 重新聚合语义上下文")
                    expanded_context_result = await self.semantic_aggregator.aggregate_semantic_context(
                        user_question=user_question,
                        table_ids=context.selected_tables,
                        include_global=True,
                        retrieval_profile="expanded",
                    )
                    expanded_contract_result = self._validate_stage_contract(
                        context=context,
                        stage="sql_generation",
                        semantic_context_result=expanded_context_result,
                        join_constraints=join_constraints,
                    )
                    if expanded_contract_result.get("ok"):
                        semantic_context_for_retry = expanded_context_result
                        recall_expanded = True
                        self.multi_table_metrics.inc("context_recall_expansion_count")
                        logger.info("✅ 扩召回上下文校验通过，后续重试使用 expanded 上下文")
                    else:
                        logger.warning("⚠️ 扩召回上下文校验失败，继续使用 normal 上下文重试")

                # 🆕 使用 PromptManager 渲染 SQL 生成模板（包含当前时间和思考结果）
                # ✅ 确保使用完整的语义上下文（semantic_context_for_retry.enhanced_context）
                # 🆕 从意图澄清结果中提取继承的上下文（时间范围、筛选条件等）
                clarification_inherited = ""
                if hasattr(context, 'clarification_result') and context.clarification_result:
                    cl_analysis = context.clarification_result.get('analysis', {})
                    is_follow_up = cl_analysis.get('isFollowUp', False)
                    inherited_ctx = cl_analysis.get('inheritedContext', '')
                    time_info = cl_analysis.get('timeInfo', '')
                    filter_info = cl_analysis.get('filterInfo', '')
                    if is_follow_up and (inherited_ctx or time_info or filter_info):
                        clarification_inherited = (
                            f"⚠️ 【追问上下文（必须继承）】\n"
                            f"意图澄清阶段已确认这是一个追问，必须继承以下历史上下文：\n"
                            f"- 继承的上下文：{inherited_ctx}\n"
                            f"- 时间范围：{time_info}\n"
                            f"- 筛选条件：{filter_info}\n"
                            f"- 澄清理解：{context.clarification_result.get('clarificationText', '')}\n"
                            f"请确保 SQL 的 WHERE 条件中包含上述时间范围和筛选条件。\n"
                        )
                        logger.info(f"🔗 已提取追问上下文注入 SQL prompt: isFollowUp={is_follow_up}, time={time_info}")

                prompt = self.prompt_manager.render_prompt(
                    PromptType.SQL_GENERATION,
                    {
                        "original_question": user_question,
                        "clarified_requirement": user_question,  # 如果有澄清则使用澄清后的
                        "semantic_context": semantic_context_for_retry.enhanced_context,  # ✅ 直接使用完整语义上下文
                        "db_type": prompt_db_type,
                        "history_context": history_context,  # 🆕 添加历史对话上下文
                        "current_date": self._format_current_date_with_ranges(),  # 🆕 添加当前时间和预计算范围
                        "thinking_result": thinking_result  # 🆕 添加模型思考结果
                    }
                )
                
                # 🆕 i18n: 注入语言指令
                from src.utils.language_detector import inject_language_instruction
                lang = context.metadata.get('response_language', 'zh')
                prompt = inject_language_instruction(prompt, lang, stage="sql_generation")
                prompt += self._build_join_constraint_prompt_block(
                    join_constraints=join_constraints,
                    prefer_fiscal_period_filters=bool(context.metadata.get("prefer_fiscal_period_filters")),
                )
                
                logger.info(f"✅ 使用 prompts.yml 中的 sql_generation 模板（包含历史上下文和当前时间）")
                logger.info(f"📅 当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                
                # 添加安全要求、重试提示和执行错误信息
                # 构建执行错误注入块（SQL 执行失败时传入错误信息和表结构，帮助 AI 修正 SQL）
                exec_error_block = ""
                if exec_error:
                    # 从 context 中获取表结构信息，帮助 AI 理解正确的字段名和类型
                    detailed_tables = context.metadata.get('detailed_tables_info', [])
                    table_schema_hint = ""
                    if detailed_tables:
                        schema_lines = []
                        for tbl in detailed_tables:
                            fields_desc = ", ".join(
                                f"{f['fieldName']}({f['dataType']})"
                                for f in tbl.get('fields', [])
                            )
                            schema_lines.append(f"  表 {tbl['tableName']}: {fields_desc}")
                        table_schema_hint = "\n可用表结构：\n" + "\n".join(schema_lines)

                    exec_error_block = f"""

🚨 【SQL执行失败，请修正后重新生成】
上次生成的 SQL 执行时报错：
  错误信息：{exec_error}
  失败的 SQL：{context.generated_sql}
{table_schema_hint}

请根据以上错误信息和表结构，修正 SQL 并重新生成。
注意：
- 检查字段名是否正确（区分大小写）
- 检查表名是否正确
- 检查 JOIN 条件是否合理
- 检查 WHERE 条件的数据类型是否匹配
- 保持查询目标与用户原始需求一致：{user_question}
"""

                prompt = prompt + f"""

⚠️ 安全要求：
- 仅允许生成 SELECT 查询语句
- 禁止使用 INSERT, UPDATE, DELETE, DROP, CREATE, ALTER, TRUNCATE 等操作
- 如果用户要求修改数据，请礼貌地说明系统仅支持查询功能

{f"上次生成的 SQL 不符合安全要求：{last_error}，请重新生成符合要求的 SQL。" if last_error else ""}
{exec_error_block}
请生成准确的SQL查询，只返回SQL语句，不要包含其他内容。
如果用户问题涉及"去年"、"上个月"等时间对比，请根据历史对话理解具体时间范围。
"""
                
                # 🆕 注入 TimeResolver 解析结果（如果存在）
                resolved_time_context = context.metadata.get('resolved_time_context')
                if resolved_time_context and resolved_time_context.force_prompt_note:
                    prompt = prompt + f"\n\n{resolved_time_context.force_prompt_note}\n"
                    logger.info(f"⏰ TimeResolver: 已注入 force_prompt_note 到 SQL 生成 Prompt")
                    if context.metadata.get("prefer_fiscal_period_filters"):
                        prompt = prompt + (
                            "\n【时间口径一致性约束（必须遵守）】\n"
                            "本问题为用户显式 FY+FW 口径，优先使用 FY_N/FW_N 过滤；"
                            "不要改写为仅 FW_START_DATE/FW_END_DATE 的自然日期过滤。\n"
                        )
                    else:
                        prompt = prompt + (
                            "\n【时间口径一致性约束（必须遵守）】\n"
                            "若已使用上方解析日期范围（FW_START_DATE/FW_END_DATE），"
                            "禁止再叠加 FY_N/FM_N/FW_N 过滤，避免财务口径与自然日期口径冲突。\n"
                        )
                
                time_notes_sql = context.metadata.get("time_language_notes") or []
                if time_notes_sql:
                    prompt = prompt + "\n\n" + "\n".join(time_notes_sql)
                    logger.info("📅 已注入 time_language_notes 到 SQL 生成 Prompt")
                
                logger.info(f"✅ 使用 prompts.yml 中的 sql_generation 模板")
                
                # 📝 记录完整的 SQL 生成 Prompt（包含语义上下文 + 历史上下文 + 安全要求）
                logger.info("=" * 80)
                logger.info(f"📝 SQL 生成 Prompt（完整）- 第 {retry_count + 1} 次尝试")
                logger.info("=" * 80)
                logger.info("")
                logger.info("📋 Prompt 组成部分：")
                logger.info(f"  1️⃣ 用户问题: {user_question}")
                logger.info(f"  2️⃣ 语义上下文: {'✅ 已包含' if semantic_context_for_retry.enhanced_context else '❌ 缺失'}")
                logger.info(f"     - 数据源信息: {'✅' if 'data_source' in semantic_context_for_retry.modules_used else '❌'}")
                logger.info(f"     - 表结构信息: {'✅' if 'table_structure' in semantic_context_for_retry.modules_used else '❌'}")
                logger.info(f"     - 数据字典信息: {'✅' if 'dictionary' in semantic_context_for_retry.modules_used else '❌'}")
                logger.info(f"     - 表关联信息: {'✅' if 'table_relation' in semantic_context_for_retry.modules_used else '❌'}")
                logger.info(f"     - 知识库信息: {'✅' if 'knowledge' in semantic_context_for_retry.modules_used else '❌'}")
                logger.info(f"  3️⃣ 历史对话上下文: {'✅ 已包含' if history_context else '❌ 无历史对话'}")
                logger.info(f"  4️⃣ 安全要求: ✅ 已包含")
                logger.info("")
                logger.info("📊 Prompt 统计信息：")
                logger.info(f"  - Prompt 总长度: {len(prompt)} 字符")
                logger.info(f"  - Prompt Token 估算: {self._count_tokens(prompt)}")
                logger.info(f"  - 语义上下文长度: {len(semantic_context_for_retry.enhanced_context)} 字符")
                logger.info(f"  - 历史上下文长度: {len(history_context) if history_context else 0} 字符")
                logger.info("")
                logger.info("-" * 80)
                logger.info("📝 完整 Prompt 内容：")
                logger.info("-" * 80)
                logger.info(prompt)
                logger.info("-" * 80)
                logger.info("=" * 80)
                
                # 📝 使用 request_logger 记录（用于审计）
                request_logger.log_ai_prompt(
                    prompt_type=f"SQL生成 (SQL Generation) - 第 {retry_count + 1} 次尝试",
                    prompt_content=prompt,
                    context={
                        "user_question": user_question,
                        "selected_tables": context.selected_tables,
                        "has_semantic_context": bool(semantic_context_for_retry.enhanced_context),
                        "semantic_context_length": len(semantic_context_for_retry.enhanced_context),
                        "has_history_context": bool(history_context),
                        "history_context_length": len(history_context) if history_context else 0,
                        "retry_count": retry_count,
                        "last_error": last_error,
                        "recall_profile": "expanded" if recall_expanded else "normal",
                        "session_id": context.session_id
                    }
                )
                
                # 🌊 1. 发送 stage_start（空内容）- 仅在第一次尝试时发送
                # 如果是执行失败后的重新生成（exec_error 不为 None），发送 stage_reset 重置旧内容
                if retry_count == 0:
                    if exec_error:
                        # 执行失败后重新生成：重置 stage 内容，前端清空旧 SQL 显示最新的
                        logger.info(f"🔄 SQL执行失败，重置 stage: {stage_id}，错误: {exec_error[:100]}")
                        await self.websocket_service.send_stage_reset(
                            session_id=context.session_id,
                            stage_id=stage_id,
                            stage_name=stage_name,
                            content="",
                            metadata={"exec_error": exec_error[:200]}
                        )
                    else:
                        # 首次生成：正常发送 stage_start
                        logger.info(f"🌊 发送 stage_start: {stage_id}")
                        await self.websocket_service.send_stage_start(
                            session_id=context.session_id,
                            stage_id=stage_id,
                            stage_name=stage_name,
                            content=""
                        )
                
                # 🌊 2. 使用流式调用获取内容块（带超时和错误处理）
                logger.info(f"🌊 开始流式调用模型（路由）...")
                accumulated_content = ""
                chunk_count = 0
                streaming_start_time = time.time()
                STREAMING_TIMEOUT = 60  # 60秒超时
                
                try:
                    async for chunk in self.ai_service.call_model_stream(stage="sql_generation", 
                        prompt=prompt,
                        session_id=context.session_id,
                        model_type="qwen",
                        temperature=0.0  # SQL生成必须确定性，避免每次生成不同粒度的SQL
                    ):
                        # 检查超时
                        elapsed_time = time.time() - streaming_start_time
                        if elapsed_time > STREAMING_TIMEOUT:
                            logger.error(f"❌ SQL生成流式调用超时: {elapsed_time:.2f}秒 > {STREAMING_TIMEOUT}秒")
                            logger.info(f"📦 超时前已接收 {chunk_count} 个块，累积内容: {len(accumulated_content)} 字符")
                            
                            # 发送已累积的内容
                            if accumulated_content:
                                logger.info(f"⚠️ 发送超时前累积的内容作为最终结果")
                                break
                            else:
                                raise asyncio.TimeoutError(f"SQL生成流式调用超时（{STREAMING_TIMEOUT}秒），且无累积内容")
                        
                        # 累积内容
                        accumulated_content += chunk
                        chunk_count += 1
                        
                        # 🌊 3. 发送 stage_update（增量块）
                        try:
                            await self.websocket_service.send_stage_update(
                                session_id=context.session_id,
                                stage_id=stage_id,
                                content=chunk
                            )
                            logger.debug(f"📦 发送 chunk #{chunk_count}, 大小: {len(chunk)} 字符")
                        except Exception as ws_error:
                            logger.warning(f"⚠️ 发送 stage_update 失败: {str(ws_error)}", exc_info=True)
                            # 继续累积内容，即使 WebSocket 发送失败
                    
                    logger.info(f"🌊 流式调用完成，共 {chunk_count} 个块，总长度: {len(accumulated_content)} 字符")
                    
                except asyncio.TimeoutError as timeout_error:
                    logger.error(f"❌ SQL生成流式调用超时: {str(timeout_error)}", exc_info=True)
                    logger.info(f"📦 超时时已累积内容: {len(accumulated_content)} 字符")
                    
                    # 如果有累积内容，使用它；否则尝试降级
                    if not accumulated_content:
                        logger.warning("⚠️ 超时且无累积内容，降级到非流式调用...")
                        try:
                            response = await self.ai_service.call_model(stage="sql_generation", 
                                prompt=prompt,
                                session_id=context.session_id,
                                model_type="qwen",
                                temperature=0.0  # SQL生成确定性
                            )
                            if response["success"]:
                                accumulated_content = response["content"]
                                logger.info(f"✅ 非流式调用成功，内容长度: {len(accumulated_content)} 字符")
                            else:
                                raise Exception(f"非流式调用也失败: {response.get('error')}")
                        except Exception as fallback_error:
                            logger.error(f"❌ 降级到非流式调用也失败: {str(fallback_error)}")
                            raise Exception(f"SQL生成流式调用超时且降级失败: {str(fallback_error)}")
                    else:
                        logger.info(f"⚠️ 使用超时前累积的内容: {len(accumulated_content)} 字符")
                        
                except Exception as stream_error:
                    logger.error(f"❌ SQL生成流式调用失败: {str(stream_error)}", exc_info=True)
                    logger.info(f"📦 失败时已累积内容: {len(accumulated_content)} 字符")
                    
                    # 如果有累积内容，使用它；否则尝试降级
                    if not accumulated_content:
                        logger.warning("⚠️ 流式失败且无累积内容，降级到非流式调用...")
                        try:
                            response = await self.ai_service.call_model(stage="sql_generation", 
                                prompt=prompt,
                                session_id=context.session_id,
                                model_type="qwen",
                                temperature=0.0  # SQL生成确定性
                            )
                            if response["success"]:
                                accumulated_content = response["content"]
                                logger.info(f"✅ 非流式调用成功，内容长度: {len(accumulated_content)} 字符")
                            else:
                                raise Exception(f"非流式调用也失败: {response.get('error')}")
                        except Exception as fallback_error:
                            logger.error(f"❌ 降级到非流式调用也失败: {str(fallback_error)}")
                            raise Exception(f"SQL生成流式调用失败且降级失败: {str(fallback_error)}")
                    else:
                        logger.info(f"⚠️ 使用失败前累积的内容: {len(accumulated_content)} 字符")
                
                # 📝 记录 AI 响应（详细）
                logger.info("=" * 80)
                logger.info(f"🤖 AI 响应 - 第 {retry_count + 1} 次尝试")
                logger.info("=" * 80)
                logger.info(f"📊 响应长度: {len(accumulated_content)} 字符")
                logger.info("")
                logger.info("-" * 80)
                logger.info(f"📝 AI 返回内容：")
                logger.info("-" * 80)
                logger.info(accumulated_content)
                logger.info("-" * 80)
                logger.info("=" * 80)
                
                # 📝 使用 request_logger 记录（用于审计）
                request_logger.log_ai_response(
                    response_type=f"SQL生成响应 - 第 {retry_count + 1} 次尝试",
                    response_content=accumulated_content,
                    metadata={
                        "success": True,
                        "retry_count": retry_count,
                        "session_id": context.session_id,
                        "streaming": True,
                        "chunk_count": chunk_count
                    }
                )
                
                # 🌊 4. 提取 SQL 语句从累积的完整响应
                sql = self._extract_sql_from_response(accumulated_content)
                # 🌊 4. 提取 SQL 语句从累积的完整响应
                sql = self._extract_sql_from_response(accumulated_content)
                logger.info("=" * 80)
                logger.info("📝 提取的 SQL 语句")
                logger.info("=" * 80)
                logger.info(f"📊 SQL 长度: {len(sql)} 字符")
                logger.info("")
                logger.info("-" * 80)
                logger.info(sql)
                logger.info("-" * 80)
                logger.info("=" * 80)

                # 🧭 SQL 方言守卫：数据库类型与 SQL 语法必须一致
                dialect_guard_result = self.sql_dialect_guard.validate_sql(
                    sql=sql,
                    db_type=prompt_db_type,
                )
                if not dialect_guard_result.is_valid:
                    retry_count += 1
                    self.multi_table_metrics.inc("sql_retry_count")
                    self.multi_table_metrics.inc("dialect_guard_fail_count")
                    violations = (dialect_guard_result.details or {}).get("violations", [])
                    last_error = (
                        f"{dialect_guard_result.error_code}: {dialect_guard_result.error_message}; "
                        f"{'; '.join(violations)}"
                    )
                    logger.warning(
                        f"⚠️ DialectGuard 校验失败（第 {retry_count}/{max_retries} 次）: {last_error}"
                    )
                    if retry_count >= max_retries:
                        error_message = (
                            f"无法生成符合数据库方言的 SQL（已重试 {max_retries} 次）。"
                            f"最后错误：{dialect_guard_result.error_message}"
                        )
                        await self.websocket_service.send_stage_complete(
                            session_id=context.session_id,
                            stage_id=stage_id,
                            stage_name=stage_name,
                            content=error_message,
                            metadata={
                                "error_code": dialect_guard_result.error_code,
                                "error": dialect_guard_result.error_message,
                                "retry_count": retry_count,
                                "details": dialect_guard_result.details,
                            }
                        )
                        return {"success": False, "error": error_message}
                    continue
                
                # 🔒 SQL 安全验证（黑名单机制）
                logger.info("=" * 80)
                logger.info("🔒 开始 SQL 安全验证...")
                logger.info("=" * 80)
                
                validation_result = await self.sql_security.validate_and_secure_sql(
                    sql, data_source_id or 1
                )
                
                logger.info("=" * 80)
                logger.info("🔒 SQL 安全验证结果")
                logger.info("=" * 80)
                logger.info(f"📊 验证状态: {'✅ 通过' if validation_result.is_valid else '❌ 失败'}")
                logger.info(f"📊 安全级别: {validation_result.security_level.value}")
                if validation_result.violations:
                    logger.warning(f"⚠️ 发现 {len(validation_result.violations)} 个违规项:")
                    for i, violation in enumerate(validation_result.violations, 1):
                        logger.warning(f"   {i}. {violation.message}")
                else:
                    logger.info("✅ 未发现违规项")
                
                if validation_result.sanitized_sql and validation_result.sanitized_sql != sql:
                    logger.info("📝 SQL 已被清理/修改:")
                    logger.info("-" * 80)
                    logger.info(f"原始 SQL:\n{sql}")
                    logger.info("-" * 80)
                    logger.info(f"清理后 SQL:\n{validation_result.sanitized_sql}")
                    logger.info("-" * 80)
                logger.info("=" * 80)
                
                # 如果验证通过，发送 stage_complete 并返回 SQL
                if validation_result.is_valid and validation_result.security_level.value in ["safe", "warning"]:
                    logger.info(f"✅ SQL 安全验证通过: {sql}")
                    
                    # 🌊 5. 格式化最终结果
                    final_sql = validation_result.sanitized_sql or sql
                    peer_review = await self._peer_review_sql(
                        context=context,
                        user_question=user_question,
                        generated_sql=final_sql,
                        semantic_context_result=semantic_context_for_retry,
                        join_constraints=join_constraints,
                        prompt_db_type=prompt_db_type,
                        retry_index=retry_count + 1,
                    )
                    self.multi_table_metrics.inc("sql_peer_review_total")
                    if peer_review.get("success"):
                        if not peer_review.get("is_valid", False):
                            self.multi_table_metrics.inc("sql_peer_review_fail_count")
                            reviewed_sql = str(peer_review.get("corrected_sql", "") or "").strip()
                            violations = peer_review.get("violations", [])
                            summary = peer_review.get("review_summary", "")
                            if reviewed_sql:
                                logger.warning(
                                    f"⚠️ SQL 同侪审校发现问题，已应用修复 SQL: summary={summary}, violations={violations}"
                                )
                                final_sql = reviewed_sql
                                self.multi_table_metrics.inc("sql_peer_review_fix_applied_count")
                            else:
                                retry_count += 1
                                self.multi_table_metrics.inc("sql_retry_count")
                                detail = "; ".join(
                                    str(v.get("message", v)) if isinstance(v, dict) else str(v)
                                    for v in (violations or [])
                                )
                                last_error = (
                                    f"SQL_PEER_REVIEW_REJECTED: {summary or 'peer review failed'}"
                                    + (f"; {detail}" if detail else "")
                                )
                                logger.warning(
                                    f"⚠️ SQL 同侪审校未通过（第 {retry_count}/{max_retries} 次）: {last_error}"
                                )
                                if retry_count >= max_retries:
                                    error_message = (
                                        f"无法生成通过同侪审校的 SQL（已重试 {max_retries} 次）。"
                                        f"最后错误：{last_error}"
                                    )
                                    await self.websocket_service.send_stage_complete(
                                        session_id=context.session_id,
                                        stage_id=stage_id,
                                        stage_name=stage_name,
                                        content=error_message,
                                        metadata={
                                            "error": last_error,
                                            "retry_count": retry_count
                                        }
                                    )
                                    return {
                                        "success": False,
                                        "error": error_message
                                    }
                                continue
                    time_conflict_error = self._check_time_filter_conflict(final_sql, context)
                    if time_conflict_error:
                        retry_count += 1
                        self.multi_table_metrics.inc("sql_retry_count")
                        last_error = time_conflict_error
                        logger.warning(
                            f"⚠️ SQL 时间口径冲突（第 {retry_count}/{max_retries} 次）: {time_conflict_error}"
                        )
                        logger.info("🔄 让 AI 重新生成一致口径的 SQL...")
                        if retry_count >= max_retries:
                            error_message = (
                                f"无法生成时间口径一致的 SQL（已重试 {max_retries} 次）。"
                                f"最后的错误：{time_conflict_error}"
                            )
                            await self.websocket_service.send_stage_complete(
                                session_id=context.session_id,
                                stage_id=stage_id,
                                stage_name=stage_name,
                                content=error_message,
                                metadata={
                                    "error": time_conflict_error,
                                    "retry_count": retry_count
                                }
                            )
                            return {
                                "success": False,
                                "error": error_message
                            }
                        continue
                    enum_flag_error = self._validate_sql_enum_flag_predicates(
                        sql=final_sql,
                        semantic_context_result=semantic_context_for_retry,
                    )
                    if enum_flag_error:
                        retry_count += 1
                        self.multi_table_metrics.inc("sql_retry_count")
                        last_error = enum_flag_error
                        logger.warning(
                            f"⚠️ SQL 枚举语义校验失败（第 {retry_count}/{max_retries} 次）: {enum_flag_error}"
                        )
                        logger.info("🔄 让 AI 重新生成显式枚举判断的 SQL...")
                        if retry_count >= max_retries:
                            error_message = (
                                f"无法生成满足枚举语义约束的 SQL（已重试 {max_retries} 次）。"
                                f"最后的错误：{enum_flag_error}"
                            )
                            await self.websocket_service.send_stage_complete(
                                session_id=context.session_id,
                                stage_id=stage_id,
                                stage_name=stage_name,
                                content=error_message,
                                metadata={
                                    "error": enum_flag_error,
                                    "retry_count": retry_count
                                }
                            )
                            return {
                                "success": False,
                                "error": error_message
                            }
                        continue
                    text_match_risk = self._validate_sql_text_exact_match_risk(
                        sql=final_sql,
                        semantic_context_result=semantic_context_for_retry,
                    )
                    if text_match_risk:
                        retry_count += 1
                        self.multi_table_metrics.inc("sql_retry_count")
                        last_error = text_match_risk
                        logger.warning(
                            f"⚠️ SQL 文本匹配语义校验失败（第 {retry_count}/{max_retries} 次）: {text_match_risk}"
                        )
                        logger.info("🔄 让 AI 重新生成使用正确匹配策略（如 LIKE）的 SQL...")
                        if retry_count >= max_retries:
                            error_message = (
                                f"无法生成满足文本匹配语义约束的 SQL（已重试 {max_retries} 次）。"
                                f"最后的错误：{text_match_risk}"
                            )
                            await self.websocket_service.send_stage_complete(
                                session_id=context.session_id,
                                stage_id=stage_id,
                                stage_name=stage_name,
                                content=error_message,
                                metadata={
                                    "error": text_match_risk,
                                    "retry_count": retry_count
                                }
                            )
                            return {
                                "success": False,
                                "error": error_message
                            }
                        continue
                    split_consistency_error = self._validate_workday_holiday_split_consistency(
                        sql=final_sql,
                        user_question=user_question,
                    )
                    if split_consistency_error:
                        retry_count += 1
                        self.multi_table_metrics.inc("sql_retry_count")
                        last_error = split_consistency_error
                        logger.warning(
                            f"⚠️ SQL 分类拆分语义校验失败（第 {retry_count}/{max_retries} 次）: {split_consistency_error}"
                        )
                        logger.info("🔄 让 AI 重新生成互斥拆分条件，保证分类可回加...")
                        if retry_count >= max_retries:
                            error_message = (
                                f"无法生成满足分类拆分语义约束的 SQL（已重试 {max_retries} 次）。"
                                f"最后的错误：{split_consistency_error}"
                            )
                            await self.websocket_service.send_stage_complete(
                                session_id=context.session_id,
                                stage_id=stage_id,
                                stage_name=stage_name,
                                content=error_message,
                                metadata={
                                    "error": split_consistency_error,
                                    "retry_count": retry_count
                                }
                            )
                            return {
                                "success": False,
                                "error": error_message
                            }
                        continue
                    join_guard_result = self.sql_join_guard.validate_sql(
                        sql=final_sql,
                        join_constraints=join_constraints,
                        db_type=prompt_db_type,
                    )
                    self.multi_table_metrics.inc("join_guard_total")
                    if not join_guard_result.is_valid:
                        retry_count += 1
                        self.multi_table_metrics.inc("sql_retry_count")
                        self.multi_table_metrics.inc("join_guard_fail_count")
                        last_error = (
                            f"{join_guard_result.error_code}: {join_guard_result.error_message}"
                        )
                        logger.warning(
                            f"⚠️ JoinGuard 校验失败（第 {retry_count}/{max_retries} 次）: {last_error}"
                        )
                        if retry_count >= max_retries:
                            error_message = (
                                f"无法生成满足表关联约束的 SQL（已重试 {max_retries} 次）。"
                                f"最后错误：{join_guard_result.error_message}"
                            )
                            await self.websocket_service.send_stage_complete(
                                session_id=context.session_id,
                                stage_id=stage_id,
                                stage_name=stage_name,
                                content=error_message,
                                metadata={
                                    "error_code": join_guard_result.error_code,
                                    "error": join_guard_result.error_message,
                                    "retry_count": retry_count,
                                    "details": join_guard_result.details,
                                }
                            )
                            return {"success": False, "error": error_message}
                        continue
                    formatted_result = f"```sql\n{final_sql}\n```"
                    
                    # 🌊 6. 发送 stage_complete（格式化的 SQL）
                    logger.info(f"🌊 发送 stage_complete: {stage_id}")
                    await self.websocket_service.send_stage_complete(
                        session_id=context.session_id,
                        stage_id=stage_id,
                        stage_name=stage_name,
                        content=formatted_result,
                        metadata={
                            "sql": final_sql,
                            "retry_count": retry_count
                        }
                    )
                    if len(selected_table_ids) > 1:
                        self.multi_table_metrics.inc("multi_table_success_count")
                    
                    return {
                        "success": True,
                        "sql": final_sql
                    }
                
                # 如果验证失败，记录错误并重试
                retry_count += 1
                self.multi_table_metrics.inc("sql_retry_count")
                error_messages = [v.message for v in validation_result.violations]
                last_error = '; '.join(error_messages)
                
                logger.warning(f"⚠️ SQL 安全验证失败（第 {retry_count}/{max_retries} 次）: {last_error}")
                logger.info(f"🔄 让 AI 重新生成符合安全要求的 SQL...")
                
                # 如果是最后一次重试，发送 stage_complete 并返回错误
                if retry_count >= max_retries:
                    logger.error(f"❌ SQL 生成失败：经过 {max_retries} 次重试，仍无法生成符合安全要求的 SQL")
                    
                    # 🌊 发送 stage_complete（错误状态）
                    error_message = f"无法生成符合安全要求的 SQL（已重试 {max_retries} 次）。最后的错误：{last_error}"
                    await self.websocket_service.send_stage_complete(
                        session_id=context.session_id,
                        stage_id=stage_id,
                        stage_name=stage_name,
                        content=error_message,
                        metadata={
                            "error": last_error,
                            "retry_count": retry_count
                        }
                    )
                    
                    return {
                        "success": False,
                        "error": error_message
                    }
            
            # 理论上不会到达这里
            return {
                "success": False,
                "error": "SQL 生成异常终止"
            }
                
        except Exception as e:
            logger.error(f"SQL生成失败: {str(e)}")
            
            # 🌊 发送 stage_complete（异常状态）
            try:
                await self.websocket_service.send_stage_complete(
                    session_id=context.session_id,
                    stage_id="sql_generation",
                    stage_name="SQL生成",
                    content=f"SQL生成失败: {str(e)}",
                    metadata={"error": str(e)}
                )
            except Exception as ws_error:
                logger.error(f"发送 stage_complete 失败: {str(ws_error)}")
            
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _summarize_history_context(self, history_messages: List[Dict[str, Any]], current_question: str) -> str:
        """
        智能摘要历史对话上下文
        策略：保留最近3轮对话（6条消息）完整内容，对更早的对话进行摘要
        """
        try:
            # 🆕 分离最近对话和需要摘要的对话
            RECENT_ROUNDS = 3  # 保留最近3轮对话
            RECENT_MESSAGES_COUNT = RECENT_ROUNDS * 2  # 每轮2条消息（用户+AI）
            
            if len(history_messages) <= RECENT_MESSAGES_COUNT:
                # 如果消息数不超过6条，直接返回完整对话
                history_lines = [
                    f"{'用户' if msg['role'] == 'user' else 'AI助手'}: {msg['content']}"
                    for msg in history_messages
                ]
                return "\n\n历史对话上下文（完整对话）：\n" + "\n".join(history_lines)
            
            # 分离需要摘要的消息和最近的消息
            messages_to_summarize = history_messages[:-RECENT_MESSAGES_COUNT]
            recent_messages = history_messages[-RECENT_MESSAGES_COUNT:]
            
            logger.info(f"📊 需要摘要的消息数: {len(messages_to_summarize)}")
            logger.info(f"📊 保留完整的最近消息数: {len(recent_messages)}")
            
            # 构建摘要 prompt（只摘要早期对话）
            history_text = self._format_messages_for_summary(messages_to_summarize)
            
            summary_prompt = f"""
请对以下早期历史对话进行摘要，提取关键信息以帮助理解当前问题：

早期历史对话：
{history_text}

当前问题：{current_question}

请提取并保留以下关键信息：
1. 用户关注的主要数据表名称和字段名称（必须保留原始名称）
2. 之前查询的时间范围、筛选条件（如"2023年"、"销售额>1000"等）
3. 用户的分析目标和关注点
4. 重要的业务逻辑和计算规则

⚠️ 重要：
- 必须保留所有表名、字段名、时间范围等关键信息的原始名称
- 不要使用"某表"、"某字段"等模糊表述
- 摘要应简洁但信息完整

摘要（不超过300字）：
"""
            
            # 调用模型进行摘要（路由到配置指定的模型）
            response = await self.ai_service.call_model(stage="summary", 
                prompt=summary_prompt,
                session_id="summary"
            )
            
            # 📝 记录 AI 原始响应（详细）
            logger.info("=" * 80)
            logger.info("🤖 AI 原始响应 - 历史对话摘要")
            logger.info("=" * 80)
            logger.info(f"📊 响应状态: {'✅ 成功' if response.get('success') else '❌ 失败'}")
            if not response.get('success'):
                logger.error(f"❌ 错误信息: {response.get('error', 'Unknown error')}")
            logger.info(f"📊 响应长度: {len(response.get('content', ''))} 字符")
            logger.info("")
            logger.info("-" * 80)
            logger.info(f"📝 AI 返回的摘要内容：")
            logger.info("-" * 80)
            logger.info(response.get('content', ''))
            logger.info("-" * 80)
            logger.info("=" * 80)
            
            summary_text = ""
            if response["success"]:
                summary_text = response["content"]
                logger.info(f"✅ 早期对话摘要成功，摘要Token数: {self._count_tokens(summary_text)}")
            else:
                # 摘要失败，使用简化的早期对话
                logger.warning(f"⚠️ 摘要失败，使用简化的早期对话")
                summary_lines = [
                    f"{'用户' if msg['role'] == 'user' else 'AI助手'}: {msg['content'][:100]}..."
                    for msg in messages_to_summarize[-6:]  # 最多保留早期对话的最后3轮
                ]
                summary_text = "\n".join(summary_lines)
            
            # 构建完整的历史上下文：摘要 + 最近完整对话
            recent_lines = [
                f"{'用户' if msg['role'] == 'user' else 'AI助手'}: {msg['content']}"
                for msg in recent_messages
            ]
            
            history_context = f"""

历史对话上下文：

【早期对话摘要】
{summary_text}

【最近对话（最近{RECENT_ROUNDS}轮）】
{chr(10).join(recent_lines)}
"""
            
            logger.info(f"✅ 历史上下文构建完成，总Token数: {self._count_tokens(history_context)}")
            return history_context
                
        except Exception as e:
            logger.error(f"历史对话摘要失败: {str(e)}", exc_info=True)
            # 降级：返回最近 6 条消息（3轮对话）
            recent_messages = history_messages[-6:] if len(history_messages) > 6 else history_messages
            history_lines = [
                f"{'用户' if msg['role'] == 'user' else 'AI助手'}: {msg['content']}"
                for msg in recent_messages
            ]
            return "\n\n历史对话上下文（最近对话）：\n" + "\n".join(history_lines)
    
    def _extract_sql_from_response(self, response: str) -> str:
        """从AI响应中提取SQL"""
        # 🆕 尝试解析 JSON 格式的响应
        try:
            # 移除可能的 markdown 代码块标记
            cleaned_response = response.strip()
            if cleaned_response.startswith('```json'):
                cleaned_response = re.sub(r'^```json\s*', '', cleaned_response)
                cleaned_response = re.sub(r'\s*```$', '', cleaned_response)
            elif cleaned_response.startswith('```'):
                cleaned_response = re.sub(r'^```\s*', '', cleaned_response)
                cleaned_response = re.sub(r'\s*```$', '', cleaned_response)
            
            # 尝试解析 JSON
            json_data = json.loads(cleaned_response)
            
            # 如果是 JSON 对象且包含 sql 字段，提取 sql
            if isinstance(json_data, dict) and 'sql' in json_data:
                sql = json_data['sql']
                logger.info(f"✅ 从 JSON 响应中提取 SQL: {sql[:100]}...")
                return sql.strip()
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            logger.debug(f"响应不是 JSON 格式或不包含 sql 字段，尝试其他提取方式: {e}")
        
        # 尝试提取```sql```包围的SQL
        sql_pattern = r"```sql\s*(.*?)\s*```"
        match = re.search(sql_pattern, response, re.DOTALL | re.IGNORECASE)
        if match:
            sql = match.group(1).strip()
            logger.info(f"✅ 从 ```sql``` 代码块中提取 SQL: {sql[:100]}...")
            return sql
        
        # 尝试提取```包围的内容
        code_pattern = r"```\s*(.*?)\s*```"
        match = re.search(code_pattern, response, re.DOTALL)
        if match:
            sql = match.group(1).strip()
            logger.info(f"✅ 从 ``` 代码块中提取 SQL: {sql[:100]}...")
            return sql
        
        # 🆕 最后手段：用正则从响应中提取 "sql": "..." 字段
        # 处理模型返回超长 explanation 导致 json.loads 失败的情况
        sql_field_pattern = r'"sql"\s*:\s*"((?:[^"\\]|\\.)*)"'
        match = re.search(sql_field_pattern, response, re.DOTALL)
        if match:
            # 反转义 JSON 字符串中的转义字符
            sql = match.group(1).replace('\\"', '"').replace('\\n', '\n').replace('\\\\', '\\')
            logger.info(f"✅ 用正则从 JSON 字段中提取 SQL: {sql[:100]}...")
            return sql.strip()
        
        # 如果没有代码块，返回整个响应
        logger.info(f"⚠️ 未找到代码块或 JSON，返回整个响应作为 SQL")
        return response.strip()

    def _extract_first_json_object(self, content: str) -> Dict[str, Any]:
        """
        从模型返回内容中提取第一个 JSON 对象。
        兼容：纯 JSON、```json 代码块、JSON 后附加解释文字（Extra data）。
        """
        if not content:
            raise ValueError("模型返回为空")

        cleaned = content.strip()

        # 优先尝试代码块中的 JSON
        fence_match = re.search(r"```json\s*(.*?)\s*```", cleaned, re.DOTALL | re.IGNORECASE)
        if fence_match:
            cleaned = fence_match.group(1).strip()
        elif cleaned.startswith("```") and cleaned.endswith("```"):
            cleaned = re.sub(r"^```[a-zA-Z]*\s*", "", cleaned)
            cleaned = re.sub(r"\s*```$", "", cleaned).strip()

        # 1) 先尝试整段解析
        try:
            parsed = json.loads(cleaned)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass

        # 2) 允许 JSON 后有附加文本：使用 raw_decode 只取首个 JSON 对象
        decoder = json.JSONDecoder()
        start_idx = cleaned.find("{")
        if start_idx >= 0:
            obj, _end = decoder.raw_decode(cleaned[start_idx:])
            if isinstance(obj, dict):
                return obj
            raise ValueError("首个 JSON 不是对象")

        raise ValueError("未找到 JSON 对象")

    def _apply_followup_time_scope_override(
        self, user_question: str, clarification_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        时间口径覆盖规则（通用）：
        - 当前问题明确写“X月”（自然月）且未出现“财月/FM/财期”等财务口径关键词时，
        - 若澄清结果将其解析成 fiscal_month_week，则改写为 month_week。
        """
        try:
            if not isinstance(clarification_result, dict):
                return clarification_result

            analysis = clarification_result.get("analysis", {}) or {}

            q = user_question or ""
            has_natural_month = bool(re.search(r"(?<!财)(?:\d{1,2})\s*月", q))
            has_fiscal_marker = bool(
                re.search(r"(财月|财期|FM\s*\d{1,2}|FQ\s*[1-4]|上财月|本财月|下财月)", q, re.IGNORECASE)
            )
            if not has_natural_month or has_fiscal_marker:
                return clarification_result

            fiscal_queries = clarification_result.get("fiscalTimeQueries", [])
            if not isinstance(fiscal_queries, list) or not fiscal_queries:
                return clarification_result

            month_match = re.search(r"(?<!财)(1[0-2]|0?[1-9])\s*月", q)
            year_match = re.search(r"(20\d{2})\s*年", q)
            fy_match = re.search(r"\bFY\s*(\d{2,4})\b", q, re.IGNORECASE)
            natural_month = int(month_match.group(1)) if month_match else None
            natural_year = int(year_match.group(1)) if year_match else None
            has_explicit_gregorian_year = natural_year is not None
            fy_from_question: Optional[str] = None
            if fy_match:
                fy_digits = fy_match.group(1)
                if len(fy_digits) == 2:
                    fy_from_question = f"FY20{fy_digits}"
                elif len(fy_digits) == 4:
                    fy_from_question = f"FY{fy_digits}"

            converted = False
            normalized_queries: List[Dict[str, Any]] = []
            for fq in fiscal_queries:
                if not isinstance(fq, dict):
                    normalized_queries.append(fq)
                    continue

                # 规则A：FY + X月第N周（无 20xx年）时，month_week 不能绑定自然年 year。
                # 否则会把 FY25 10月错误解析到 2025-10（应按 FY25 对应自然年窗口去查）。
                if (
                    fq.get("type") == "month_week"
                    and fy_from_question
                    and not has_explicit_gregorian_year
                ):
                    patched = dict(fq)
                    patched.pop("year", None)
                    patched["fiscalYear"] = fy_from_question
                    normalized_queries.append(patched)
                    converted = True
                    continue

                if fq.get("type") == "fiscal_month_week":
                    week_index = fq.get("weekIndex")
                    if not isinstance(week_index, int):
                        try:
                            week_index = int(week_index)
                        except Exception:
                            week_index = 1

                    # 年份优先取问题里的自然年；没有则沿用 fiscalYear 数字部分
                    target_year = natural_year
                    target_month = natural_month
                    if target_month is None:
                        fm = fq.get("fiscalMonth")
                        fm_digits = re.sub(r"[^0-9]", "", str(fm or ""))
                        if fm_digits:
                            _m = int(fm_digits)
                            target_month = _m if 1 <= _m <= 12 else None

                    if target_month:
                        converted_item: Dict[str, Any] = {
                            "type": "month_week",
                            "month": target_month,
                            "weekIndex": week_index,
                            "description": fq.get(
                                "description",
                                f"{target_month}月第{week_index}周",
                            ),
                        }
                        # 仅当用户问题明确写了自然年时才传 year；
                        # 否则优先使用问题中显式 FY（避免沿用模型误判的 fiscalYear）
                        if target_year:
                            converted_item["year"] = target_year
                        else:
                            fy = fy_from_question or fq.get("fiscalYear")
                            if fy:
                                converted_item["fiscalYear"] = fy
                        normalized_queries.append(converted_item)
                        converted = True
                        continue

                normalized_queries.append(fq)

            if converted:
                clarification_result["fiscalTimeQueries"] = normalized_queries
                note = (
                    "（系统口径覆盖：当前问题使用自然月表达，已按自然月处理）"
                )
                if isinstance(analysis, dict):
                    prev_time = analysis.get("timeInfo", "")
                    analysis["timeInfo"] = f"{prev_time}{note}" if prev_time else note
                    prev_ctx = analysis.get("inheritedContext", "")
                    analysis["inheritedContext"] = (
                        f"{prev_ctx}{note}" if prev_ctx else note
                    )
                    clarification_result["analysis"] = analysis
                logger.info("📅 时间口径覆盖：已将 fiscal_month_week 改写为 month_week（自然月）")

            return clarification_result
        except Exception as _override_err:
            logger.warning(f"📅 时间口径覆盖失败，保持原结果: {_override_err}")
            return clarification_result

    def _check_time_filter_conflict(self, sql: str, context: ChatContext) -> Optional[str]:
        """
        检测 SQL 时间过滤口径冲突：
        当系统已注入明确日期范围时，禁止同时使用财务字段过滤和日期字段过滤。
        """
        resolved_time_context = context.metadata.get("resolved_time_context")
        if not resolved_time_context or not getattr(resolved_time_context, "date_ranges", None):
            return None

        normalized_sql = sql.upper()
        has_fiscal_filter = bool(
            re.search(r"\b(FY_N|FM_N|FW_N)\b\s*(=|IN)\s*", normalized_sql)
        )
        has_date_filter = bool(
            re.search(r"\b(FW_START_DATE|FW_END_DATE)\b\s*(=|>|<|>=|<=|BETWEEN)", normalized_sql)
        )

        if has_fiscal_filter and has_date_filter:
            if context.metadata.get("prefer_fiscal_period_filters"):
                return (
                    "检测到时间口径冲突：当前问题为显式 FY+FW 查询，同一 SQL 同时使用了 FY_N/FM_N/FW_N "
                    "与 FW_START_DATE/FW_END_DATE。请保留 FY_N/FW_N 过滤并移除日期字段过滤。"
                )
            return (
                "检测到时间口径冲突：同一 SQL 同时使用 FY_N/FM_N/FW_N 与 "
                "FW_START_DATE/FW_END_DATE 过滤。请二选一，优先使用已解析日期范围。"
            )
        return None
    
    async def _execute_sql(self, context: ChatContext, data_source_id: Optional[str]) -> Dict[str, Any]:
        """执行SQL（使用真实数据库查询）"""
        try:
            logger.info("=" * 80)
            logger.info("🔍 开始执行 SQL 查询")
            
            # 🔧 修复：确保 generated_sql 是纯 SQL 字符串，而不是 JSON 对象
            sql_to_execute = context.generated_sql
            
            # 检查是否是 JSON 格式（以 { 开头）
            if isinstance(sql_to_execute, str) and sql_to_execute.strip().startswith('{'):
                logger.warning("⚠️ 检测到 SQL 是 JSON 格式，尝试提取 sql 字段")
                try:
                    import json
                    json_data = json.loads(sql_to_execute)
                    if isinstance(json_data, dict) and 'sql' in json_data:
                        sql_to_execute = json_data['sql']
                        logger.info(f"✅ 从 JSON 中提取 SQL 成功: {sql_to_execute[:100]}...")
                        # 更新 context 中的 SQL（避免后续使用时再次出错）
                        context.generated_sql = sql_to_execute
                    else:
                        logger.error(f"❌ JSON 格式不正确，缺少 sql 字段: {json_data}")
                except json.JSONDecodeError as e:
                    logger.error(f"❌ JSON 解析失败: {str(e)}")
                    # 继续使用原始字符串，让后续错误处理机制处理
            
            logger.info(f"SQL: {sql_to_execute}")
            logger.info(f"数据源ID: {data_source_id}")
            
            # 从数据库获取数据源配置
            from src.services.data_source_service import DataSourceService
            from src.database import get_db
            
            db_session = next(get_db())
            data_source_service = DataSourceService()
            
            # 验证数据源ID是否提供
            if not data_source_id:
                logger.error("❌ 未提供数据源ID")
                return {
                    "success": False,
                    "error": "未提供数据源ID，请在前端选择数据源"
                }
            
            # 使用提供的数据源ID查询（UUID字符串）
            data_source = data_source_service.get_source_by_id(db_session, str(data_source_id))
            
            if not data_source:
                logger.error(f"❌ 数据源 {data_source_id} 不存在")
                return {
                    "success": False,
                    "error": f"数据源 {data_source_id} 不存在"
                }
            
            logger.info(f"✅ 数据源配置获取成功: {data_source.name} ({data_source.db_type})")
            
            # 构建数据源配置字典
            from src.utils.encryption import decrypt_password

            raw_db_type = str(data_source.db_type or "").strip().lower()
            db_type_mapping = {
                "mysql": "mysql",
                "sqlserver": "sqlserver",
                "sql server": "sqlserver",
                "sql_server": "sqlserver",
                "postgresql": "postgresql",
            }
            normalized_db_type = db_type_mapping.get(raw_db_type, raw_db_type.replace(" ", "").replace("_", ""))
            
            data_source_config = {
                "type": normalized_db_type,
                "host": data_source.host,
                "port": data_source.port,
                "database": data_source.database_name,
                "username": data_source.username,
                "password": decrypt_password(data_source.password) if data_source.password else "",
                "auth_type": data_source.auth_type,
                "domain": data_source.domain
            }
            
            logger.info(f"📊 数据源配置: host={data_source_config['host']}, database={data_source_config['database']}")
            
            # 使用 SQLExecutorService 执行查询
            from src.services.sql_executor_service import SQLExecutorService, ExecutionConfig
            
            executor_config = ExecutionConfig(
                timeout_seconds=30,
                max_rows=10000,
                enable_streaming=False
            )
            
            sql_executor = SQLExecutorService(config=executor_config)
            
            logger.info("🚀 开始执行真实 SQL 查询...")
            query_result = await sql_executor.execute_query(
                sql=sql_to_execute,  # 🔧 修复：使用提取后的 SQL
                data_source_config=data_source_config,
                use_cache=True,
                stream=False
            )
            
            logger.info(f"✅ SQL 查询执行成功")
            logger.info(f"📊 返回行数: {query_result.row_count}")
            logger.info(f"⏱️ 执行时间: {query_result.execution_time:.3f}s")
            logger.info(f"📋 列名: {query_result.columns}")
            logger.info(f"📄 数据预览（前3行）: {query_result.rows[:3]}")
            logger.info("=" * 80)
            
            # 转换为原有格式
            result = {
                "columns": query_result.columns,
                "rows": query_result.rows,
                "total_rows": query_result.row_count,
                "execution_time": query_result.execution_time,
                "is_truncated": query_result.is_truncated,
                "has_more": query_result.has_more
            }
            
            return {
                "success": True,
                "result": result
            }
            
        except Exception as e:
            logger.error(f"❌ SQL执行失败: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _analyze_data(self, context: ChatContext, user_question: str) -> Dict[str, Any]:
        """数据分析（本地模型，使用 prompts.yml 模板 + 流式输出）"""
        stage_id = "data_analysis"
        stage_name = "数据分析"
        
        try:
            # 构建历史对话上下文字符串
            history_context = ""
            if context.metadata.get('history_messages'):
                history_messages = context.metadata['history_messages']
                # 只取最近 5 轮对话
                recent_messages = history_messages[-10:] if len(history_messages) > 10 else history_messages
                
                history_lines = []
                for msg in recent_messages:
                    role_name = "用户" if msg['role'] == 'user' else "AI助手"
                    # 截断过长的内容
                    content = msg['content'][:200] + "..." if len(msg['content']) > 200 else msg['content']
                    history_lines.append(f"{role_name}: {content}")
                
                if history_lines:
                    history_context = "\n\n历史对话上下文：\n" + "\n".join(history_lines)
                    logger.info(f"包含 {len(recent_messages)} 条历史消息到数据分析 prompt")
            
            # 🆕 使用 PromptManager 渲染数据分析模板
            prompt = self.prompt_manager.render_prompt(
                PromptType.DATA_ANALYSIS,
                {
                    "user_question": user_question,
                    "query_result": json.dumps({
                        "columns": context.query_result['columns'],
                        "total_rows": context.query_result['total_rows'],
                        "rows": context.query_result['rows'][:10]  # 只显示前10行
                    }, ensure_ascii=False),
                    "previous_data": self._format_previous_data(context.previous_data)
                }
            )
            
            # 添加历史对话上下文
            if history_context:
                prompt = prompt + history_context + "\n\n如果用户问题涉及对比分析（如\"和上个月相比\"），请结合历史对话理解对比的基准。"
            
            logger.info(f"✅ 使用 prompts.yml 中的 data_analysis 模板")
            
            # 📝 记录完整的 AI Prompt
            request_logger.log_ai_prompt(
                prompt_type="数据分析 (Data Analysis)",
                prompt_content=prompt,
                context={
                    "user_question": user_question,
                    "total_rows": context.query_result['total_rows'],
                    "columns_count": len(context.query_result['columns']),
                    "has_history_context": bool(history_context),
                    "session_id": context.session_id
                }
            )
            
            # 🌊 1. 发送 stage_start（空内容）
            await self.websocket_service.send_stage_start(
                session_id=context.session_id,
                stage_id=stage_id,
                stage_name=stage_name,
                content=""
            )
            logger.info(f"🌊 已发送 stage_start: {stage_id}")
            
            # 🌊 2. 使用流式方法获取内容并发送 stage_update（带超时和错误处理）
            accumulated_content = ""
            chunk_count = 0
            streaming_start_time = time.time()
            STREAMING_TIMEOUT = 60  # 60秒超时
            
            try:
                async for chunk in self.ai_service.call_model_stream(stage="data_analysis", 
                    prompt=prompt,
                    session_id=context.session_id
                ):
                    # 检查超时
                    elapsed_time = time.time() - streaming_start_time
                    if elapsed_time > STREAMING_TIMEOUT:
                        logger.error(f"❌ 数据分析流式调用超时: {elapsed_time:.2f}秒 > {STREAMING_TIMEOUT}秒")
                        logger.info(f"📦 超时前已接收 {chunk_count} 个块，累积内容: {len(accumulated_content)} 字符")
                        
                        # 发送已累积的内容
                        if accumulated_content:
                            logger.info(f"⚠️ 发送超时前累积的内容作为最终结果")
                            break
                        else:
                            raise asyncio.TimeoutError(f"数据分析流式调用超时（{STREAMING_TIMEOUT}秒），且无累积内容")
                    
                    accumulated_content += chunk
                    chunk_count += 1
                    
                    # 发送 stage_update
                    try:
                        await self.websocket_service.send_stage_update(
                            session_id=context.session_id,
                            stage_id=stage_id,
                            content=chunk
                        )
                        
                        if chunk_count % 10 == 0:
                            logger.debug(f"🌊 已发送 {chunk_count} 个 chunks，累计长度: {len(accumulated_content)}")
                    except Exception as ws_error:
                        logger.warning(f"⚠️ 发送 stage_update 失败: {str(ws_error)}", exc_info=True)
                        # 继续累积内容，即使 WebSocket 发送失败
                
                logger.info(f"🌊 流式输出完成: 共 {chunk_count} 个 chunks，总长度: {len(accumulated_content)}")
                
            except asyncio.TimeoutError as timeout_error:
                logger.error(f"❌ 数据分析流式调用超时: {str(timeout_error)}", exc_info=True)
                logger.info(f"📦 超时时已累积内容: {len(accumulated_content)} 字符")
                
                # 如果有累积内容，使用它；否则尝试降级
                if not accumulated_content:
                    logger.warning("⚠️ 超时且无累积内容，降级到非流式调用...")
                    try:
                        response = await self.ai_service.call_model(stage="data_analysis", 
                            prompt=prompt,
                            session_id=context.session_id
                        )
                        if response["success"]:
                            accumulated_content = response["content"]
                            logger.info(f"✅ 非流式调用成功，内容长度: {len(accumulated_content)} 字符")
                        else:
                            raise Exception(f"非流式调用也失败: {response.get('error')}")
                    except Exception as fallback_error:
                        logger.error(f"❌ 降级到非流式调用也失败: {str(fallback_error)}")
                        raise Exception(f"数据分析流式调用超时且降级失败: {str(fallback_error)}")
                else:
                    logger.info(f"⚠️ 使用超时前累积的内容: {len(accumulated_content)} 字符")
                    
            except Exception as stream_error:
                logger.error(f"❌ 数据分析流式输出过程中出错: {str(stream_error)}", exc_info=True)
                logger.info(f"📦 失败时已累积内容: {len(accumulated_content)} 字符")
                
                # 如果有累积内容，使用它；否则尝试降级
                if not accumulated_content:
                    logger.warning("⚠️ 流式失败且无累积内容，降级到非流式调用...")
                    try:
                        response = await self.ai_service.call_model(stage="data_analysis", 
                            prompt=prompt,
                            session_id=context.session_id
                        )
                        if response["success"]:
                            accumulated_content = response["content"]
                            logger.info(f"✅ 非流式调用成功，内容长度: {len(accumulated_content)} 字符")
                        else:
                            raise Exception(f"非流式调用也失败: {response.get('error')}")
                    except Exception as fallback_error:
                        logger.error(f"❌ 降级到非流式调用也失败: {str(fallback_error)}")
                        raise Exception(f"数据分析流式调用失败且降级失败: {str(fallback_error)}")
                else:
                    logger.info(f"⚠️ 使用失败前累积的内容: {len(accumulated_content)} 字符")
            
            # 📝 记录 AI 原始响应（详细）
            logger.info("=" * 80)
            logger.info("🤖 AI 原始响应 - 数据分析（流式）")
            logger.info("=" * 80)
            logger.info(f"📊 响应状态: ✅ 成功")
            logger.info(f"📊 响应长度: {len(accumulated_content)} 字符")
            logger.info(f"📊 Chunk 数量: {chunk_count}")
            logger.info("")
            logger.info("-" * 80)
            logger.info(f"📝 AI 返回的完整分析内容：")
            logger.info("-" * 80)
            logger.info(accumulated_content)
            logger.info("-" * 80)
            logger.info("=" * 80)
            
            # 📝 使用 request_logger 记录（用于审计）
            request_logger.log_ai_response(
                response_type="数据分析响应（流式）",
                response_content=accumulated_content,
                metadata={
                    "success": True,
                    "session_id": context.session_id,
                    "chunk_count": chunk_count,
                    "streaming": True
                }
            )
            
            # 🌊 3. 发送 stage_complete（完整内容）
            await self.websocket_service.send_stage_complete(
                session_id=context.session_id,
                stage_id=stage_id,
                stage_name=stage_name,
                content=accumulated_content
            )
            logger.info(f"🌊 已发送 stage_complete: {stage_id}")
            
            return {
                "success": True,
                "analysis": accumulated_content
            }
                
        except Exception as e:
            logger.error(f"数据分析失败: {str(e)}", exc_info=True)
            
            # 发送错误的 stage_complete
            await self.websocket_service.send_stage_complete(
                session_id=context.session_id,
                stage_id=stage_id,
                stage_name=stage_name,
                content=f"数据分析失败: {str(e)}",
                metadata={"error": True}
            )
            
            return {
                "success": False,
                "error": str(e)
            }
    
    def _format_previous_data(self, previous_data: List[Dict[str, Any]]) -> str:
        """格式化历史数据用于对比"""
        if not previous_data:
            return "无历史数据"
        
        formatted = []
        for i, data in enumerate(previous_data[-3:]):  # 最近3次
            formatted.append(f"历史查询{i+1}: {data['timestamp'][:19]} - 行数: {data['data'].get('total_rows', 0)}")
        
        return "\n".join(formatted)
    
    async def _present_results(self, context: ChatContext, analysis_result: Dict[str, Any]):
        """展示结果（通过最终阶段完成消息发送AI分析结果）"""
        try:
            # 🆕 不再单独发送 result_message，而是通过 stage_complete 发送
            # 这样可以确保所有内容都在一个消息气泡中
            
            # 构建完整的分析结果内容
            analysis_content = analysis_result["analysis"]
            
            # 如果数据适合图表展示，准备图表数据
            chart_data = None
            if self._should_generate_chart(context.query_result):
                chart_data = self._generate_chart_data(context.query_result)
            
            # 通过最终的 stage_complete 发送完整的分析结果
            # 这样前端会将所有阶段和最终结果显示在同一个消息气泡中
            metadata = {
                "type": "analysis",
                "sql": context.generated_sql,
                "result": context.query_result,
                "execution_time": context.query_result.get("execution_time", 0),
                "total_rows": context.query_result.get("total_rows", 0),
                "progress": 1.0
            }
            
            if chart_data:
                metadata["chart_data"] = chart_data
            
            # 注意：不再调用 send_result_message，避免创建第二个消息气泡
            # 所有内容都通过 stage_complete 在一个气泡中展示
            
        except Exception as e:
            logger.error(f"结果展示失败: {str(e)}")
    
    def _should_generate_chart(self, query_result: Dict[str, Any]) -> bool:
        """判断是否应该生成图表"""
        if not query_result or not query_result.get("rows"):
            return False
        
        # 如果有数值列且行数适中，生成图表
        return (
            len(query_result["rows"]) > 1 and 
            len(query_result["rows"]) <= 100 and
            len(query_result["columns"]) >= 2
        )
    
    def _generate_chart_data(self, query_result: Dict[str, Any]) -> Dict[str, Any]:
        """生成图表数据"""
        columns = query_result["columns"]
        rows = query_result["rows"]
        
        # 简单的图表数据生成逻辑
        if len(columns) >= 2:
            return {
                "type": "bar",
                "data": [
                    {"x": str(row[0]), "y": float(row[1]) if isinstance(row[1], (int, float)) else 0}
                    for row in rows[:20]  # 最多20个数据点
                ],
                "xAxis": columns[0],
                "yAxis": columns[1]
            }
        
        return {"type": "table", "data": {"columns": columns, "rows": rows}}
    
    async def _handle_no_data_response(self, context: ChatContext, message: str) -> Dict[str, Any]:
        """处理无数据年份的响应：直接发送提示消息，跳过 SQL 生成"""
        # 发送 stage_description 阶段的提示内容
        await self.websocket_service.send_stage_start(
            session_id=context.session_id,
            stage_id="stage_description",
            stage_name="Result Description",
            content=""
        )
        await self.websocket_service.send_stage_update(
            session_id=context.session_id,
            stage_id="stage_description",
            content=message
        )
        await self.websocket_service.send_stage_complete(
            session_id=context.session_id,
            stage_id="stage_description",
            stage_name="Result Description",
            content="",
            metadata={"progress": 1.0, "description_complete": True}
        )
        # 发送 complete 消息（无图表数据）
        await self.websocket_service.send_message(
            session_id=context.session_id,
            message_type=StreamMessageType.COMPLETE,
            content="流程已完成",
            metadata={}
        )
        context.update_stage(ChatStage.COMPLETED)
        return {
            "success": True,
            "session_id": context.session_id,
            "intent": context.intent.value if context.intent else "smart_query",
            "tables": context.selected_tables,
            "sql": None,
            "result": None,
            "stage": context.current_stage.value
        }

    async def _handle_pipeline_error(self, context: ChatContext, stage: str, error: str) -> Dict[str, Any]:
        """处理流水线错误"""
        context.add_error(f"{stage}: {error}")
        context.update_stage(ChatStage.ERROR_HANDLING)
        
        await self.websocket_service.send_error_message(
            context.session_id,
            f"{stage}: {error}",
            "PIPELINE_ERROR"
        )

        # 失败场景也持久化：避免“SQL执行失败时对话历史不落库”
        try:
            db = next(get_db())
            self.context_manager.set_db_session(db)
            persisted = await self.context_manager.persist_session_to_db(context.session_id)
            if persisted:
                logger.info(f"✅ 失败场景会话已持久化: {context.session_id}")
            else:
                logger.warning(f"⚠️ 失败场景会话持久化返回失败: {context.session_id}")
            db.close()
        except Exception as persist_error:
            logger.error(f"❌ 失败场景会话持久化异常: {str(persist_error)}", exc_info=True)
        
        # 如果错误次数过多，终止对话
        if context.error_count >= self.max_error_count:
            await self.websocket_service.send_error_message(
                context.session_id,
                "错误次数过多，对话已终止",
                "MAX_ERRORS_EXCEEDED"
            )
            return {
                "success": False,
                "error": "错误次数过多",
                "session_id": context.session_id,
                "terminated": True
            }
        
        return {
            "success": False,
            "error": error,
            "session_id": context.session_id,
            "stage": stage,
            "retry_available": context.retry_count < self.max_retry_count
        }
    
    async def _clarify_intent(
        self,
        context: ChatContext,
        user_question: str,
        intent_type: str,
        selected_tables: List[str],
        data_source_id: Optional[str]
    ) -> Dict[str, Any]:
        """
        意图澄清分析（总是执行）
        
        Args:
            context: 聊天上下文
            user_question: 用户问题
            intent_type: 意图类型
            selected_tables: 选择的表
            data_source_id: 数据源ID
            
        Returns:
            澄清结果
        """
        logger.info("=" * 80)
        logger.info("🔍 开始意图澄清分析（总是执行）")
        logger.info("=" * 80)
        
        try:
            prompt_db_type = self._resolve_prompt_db_type(context, data_source_id)
            # 🆕 i18n: 翻译 stage 标签
            from src.utils.language_detector import translate_stage_label as _tsl_ci
            _ci_lang = context.metadata.get('response_language', 'zh')
            _ci_stage_name = _tsl_ci("意图澄清", _ci_lang)
            _ci_content = "Analyzing question clarity..." if _ci_lang == 'en' else "正在分析问题的明确性..."
            
            # 发送阶段开始消息
            await self.websocket_service.send_stage_start(
                session_id=context.session_id,
                stage_id="stage_clarification",
                stage_name=_ci_stage_name,
                content=_ci_content,
                metadata={"progress": 0.45}
            )
            
            # 🔥 获取完整语义上下文（包含知识库信息）
            logger.info("🔍 开始获取语义上下文（包含知识库）")
            
            # 设置数据库会话
            db = next(get_db())
            self.semantic_aggregator.db = db
            self.semantic_aggregator.data_source_service.db = db
            self.semantic_aggregator.table_structure_service.db = db
            self.semantic_aggregator.table_relation_service.db = db
            self.semantic_aggregator.knowledge_service.db = db
            logger.info("✅ 已设置 SemanticContextAggregator 及其所有子服务的数据库会话")
            
            try:
                semantic_context_result = await self.semantic_aggregator.aggregate_semantic_context(
                    user_question=user_question,
                    table_ids=selected_tables,
                    include_global=True
                )
                
                logger.info("✅ 语义上下文获取完成")
                logger.info(f"📊 使用的模块: {semantic_context_result.modules_used}")
                logger.info(f"📊 知识库信息: {'✅ 已包含' if 'knowledge' in semantic_context_result.modules_used else '❌ 未包含'}")
                
                enhanced_context_str = semantic_context_result.enhanced_context

                selected_table_ids = self._normalize_selected_table_ids(selected_tables)
                join_constraints = self._get_or_build_join_constraints(context, selected_table_ids)
                contract_result = self._validate_stage_contract(
                    context=context,
                    stage="thinking",
                    semantic_context_result=semantic_context_result,
                    join_constraints=join_constraints,
                )
                if not contract_result.get("ok"):
                    contract_error = contract_result["error"]
                    error_message = (
                        f"上下文校验失败（{contract_error.get('code')}）：{contract_error.get('message')}"
                    )
                    await self.websocket_service.send_stage_complete(
                        session_id=context.session_id,
                        stage_id="stage_thinking",
                        stage_name=thinking_stage_name,
                        content=error_message,
                        metadata={"contract_error": contract_error},
                    )
                    return {"success": False, "error": error_message, "contract_error": contract_error}
            finally:
                db.close()
                logger.info("✅ 数据库会话已关闭")
            
            # 🆕 格式化历史对话上下文
            history_messages = context.metadata.get('history_messages', [])
            history_context = self._format_history_context(history_messages)
            
            # 构建 Prompt（包含当前时间和知识库信息）
            prompt = self.prompt_manager.render_prompt(
                PromptType.INTENT_CLARIFICATION,
                {
                    "user_question": user_question,
                    "intent_type": intent_type,
                    "selected_tables": json.dumps(selected_tables, ensure_ascii=False, indent=2),
                    "semantic_context": enhanced_context_str,
                    "history_context": history_context,  # 🆕 添加历史对话上下文
                    "current_date": self._format_current_date_with_ranges(),  # 🆕 添加当前时间和预计算范围
                    "db_type": prompt_db_type
                }
            )
            
            # 🆕 i18n: 注入语言指令
            from src.utils.language_detector import inject_language_instruction
            lang = context.metadata.get('response_language', 'zh')
            prompt = inject_language_instruction(prompt, lang, stage="intent_clarification")
            
            logger.info(f"✅ 使用 prompts.yml 中的 intent_clarification 模板（包含历史上下文、当前时间和知识库）")
            logger.info(f"📅 当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
            # 📝 记录完整的 AI Prompt
            request_logger.log_ai_prompt(
                prompt_type="意图澄清 (Intent Clarification)",
                prompt_content=prompt
            )
            
            logger.info(f"📝 意图澄清 Prompt 已生成")
            logger.info(f"📊 历史消息数量: {len(history_messages)}")
            
            # 调用 AI 模型进行意图澄清分析（流式输出）
            accumulated_content = ""
            async for chunk in self.ai_service.call_model_stream(stage="intent_clarification", 
                prompt=prompt,
                session_id=context.session_id,
                temperature=0.3
            ):
                accumulated_content += chunk
                # 流式发送澄清分析内容
                await self.websocket_service.send_stage_update(
                    session_id=context.session_id,
                    stage_id="stage_clarification",
                    content=chunk
                )
            
            logger.info(f"✅ 意图澄清分析完成")
            logger.info(f"📊 分析结果长度: {len(accumulated_content)} 字符")
            
            # 解析 AI 返回的 JSON
            try:
                result = json.loads(accumulated_content)
                logger.info(f"📋 解析结果: needsClarification={result.get('needsClarification', False)}")
                
                # 🆕 保存澄清结果到 context，以便传递给 thinking 阶段
                context.clarification_result = result
                logger.info(f"✅ 澄清结果已保存到 context")
                
                return result
                
            except json.JSONDecodeError as e:
                logger.error(f"❌ 解析意图澄清结果失败: {str(e)}")
                logger.error(f"📄 原始内容: {accumulated_content[:500]}...")
                
                # 返回默认结果（假设不需要澄清）
                _cl_lang = context.metadata.get('response_language', 'zh')
                _cl_text = "Analysis complete, intent is clear." if _cl_lang == 'en' else "问题分析完成，意图明确。"
                default_result = {
                    "needsClarification": False,
                    "clarificationText": _cl_text,
                    "clarificationQuestions": [],
                    "analysis": {
                        "hasTimeInfo": False,
                        "hasDimensionInfo": False,
                        "hasMetricInfo": False,
                        "hasFilterInfo": False,
                        "isAmbiguous": False
                    }
                }
                context.clarification_result = default_result
                return default_result
                
        except Exception as e:
            logger.error(f"❌ 意图澄清分析失败: {str(e)}", exc_info=True)
            
            # 返回默认结果
            _cl2_lang = context.metadata.get('response_language', 'zh')
            _cl2_text = "Analysis complete, intent is clear." if _cl2_lang == 'en' else "问题分析完成，意图明确。"
            default_result = {
                "needsClarification": False,
                "clarificationText": _cl2_text,
                "clarificationQuestions": [],
                "analysis": {}
            }
            context.clarification_result = default_result
            return default_result
    
    async def _request_clarification(self, context: ChatContext, clarification_question: str, clarification_result: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """请求意图澄清（需要用户回答）"""
        context.update_stage(ChatStage.INTENT_CLARIFICATION)
        
        # 发送澄清问题（包含选项）
        await self.websocket_service.send_stage_complete(
            session_id=context.session_id,
            stage_id="stage_clarification",
            stage_name="意图澄清",
            content=clarification_question,
            metadata={
                "progress": 0.5,
                "needsClarification": True,
                "clarificationQuestions": clarification_result.get("clarificationQuestions", []) if clarification_result else [],
                "analysis": clarification_result.get("analysis", {}) if clarification_result else {}
            }
        )
        
        return {
            "success": True,
            "needs_clarification": True,
            "clarification_question": clarification_question,
            "session_id": context.session_id
        }
    
    async def _handle_clarification_response(self, context: ChatContext, user_response: str) -> Dict[str, Any]:
        """处理澄清回复"""
        # 继续执行流水线
        return await self._execute_chat_pipeline(context, user_response, None)
    
    async def _think_about_problem(
        self,
        context: ChatContext,
        user_question: str,
        selected_tables: List[str],
        data_source_id: Optional[str]
    ) -> Dict[str, Any]:
        """
        模型思考阶段 - 说明如何解决问题（腾讯云 ChatBI 风格）
        
        Args:
            context: 聊天上下文
            user_question: 用户问题
            selected_tables: 选择的表
            data_source_id: 数据源ID
            
        Returns:
            思考结果
        """
        logger.info("=" * 80)
        logger.info("🤔 开始模型思考阶段")
        logger.info("=" * 80)
        
        try:
            prompt_db_type = self._resolve_prompt_db_type(context, data_source_id)
            # 🆕 i18n: 获取语言设置并翻译 stage 标签
            from src.utils.language_detector import inject_language_instruction, translate_stage_label
            lang = context.metadata.get('response_language', 'zh')
            thinking_stage_name = translate_stage_label("模型思考", lang)
            
            # 发送阶段开始消息（i18n：根据语言显示不同文字）
            _thinking_start_content = "Analyzing the problem..." if lang == 'en' else "正在分析问题..."
            await self.websocket_service.send_stage_start(
                session_id=context.session_id,
                stage_id="stage_thinking",
                stage_name=thinking_stage_name,
                content=_thinking_start_content,
                metadata={"progress": 0.55}
            )
            
            # 🔥 获取完整语义上下文（包含知识库信息）
            logger.info("🔍 开始获取语义上下文（包含知识库）")
            
            # 设置数据库会话
            db = next(get_db())
            self.semantic_aggregator.db = db
            self.semantic_aggregator.data_source_service.db = db
            self.semantic_aggregator.table_structure_service.db = db
            self.semantic_aggregator.table_relation_service.db = db
            self.semantic_aggregator.knowledge_service.db = db
            logger.info("✅ 已设置 SemanticContextAggregator 及其所有子服务的数据库会话")
            
            try:
                semantic_context_result = await self.semantic_aggregator.aggregate_semantic_context(
                    user_question=user_question,
                    table_ids=selected_tables,
                    include_global=True
                )
                
                logger.info("✅ 语义上下文获取完成")
                logger.info(f"📊 使用的模块: {semantic_context_result.modules_used}")
                logger.info(f"📊 知识库信息: {'✅ 已包含' if 'knowledge' in semantic_context_result.modules_used else '❌ 未包含'}")
                
                enhanced_context_str = semantic_context_result.enhanced_context
            finally:
                db.close()
                logger.info("✅ 数据库会话已关闭")
            
            # 🆕 格式化历史对话上下文
            history_messages = context.metadata.get('history_messages', [])
            history_context = self._format_history_context(history_messages)
            
            # 🆕 获取澄清结果（如果存在）
            clarification_result = ""
            if hasattr(context, 'clarification_result') and context.clarification_result:
                clarification_result = json.dumps(context.clarification_result, ensure_ascii=False, indent=2)
                logger.info(f"✅ 获取到澄清结果")
            
            # 构建 Prompt（包含当前时间、澄清结果和知识库信息）
            prompt = self.prompt_manager.render_prompt(
                PromptType.THINKING,
                {
                    "user_question": user_question,
                    "selected_tables": json.dumps(selected_tables, ensure_ascii=False, indent=2),
                    "semantic_context": enhanced_context_str,
                    "history_context": history_context,
                    "current_date": self._format_current_date_with_ranges(),  # 🆕 添加当前时间和预计算范围
                    "clarification_result": clarification_result,  # 🆕 添加澄清结果
                    "db_type": prompt_db_type
                }
            )
            
            # 🆕 如果 TimeResolver 已解析节假日/时间，注入覆盖说明，防止幻觉防止规则误触发
            resolved_time_context = context.metadata.get('resolved_time_context')
            if resolved_time_context and resolved_time_context.force_prompt_note:
                prompt = prompt + f"\n\n⚠️ 【时间已由系统预解析，以下规则优先级最高，覆盖所有其他规则】\n{resolved_time_context.force_prompt_note}\n上方日期已由后端财务日历数据库精确查询得出，无需再判断知识库是否包含节假日信息，直接使用上方日期范围进行分析。\n"
                logger.info(f"⏰ TimeResolver: 已注入 force_prompt_note 到 thinking Prompt")
            
            time_notes = context.metadata.get("time_language_notes") or []
            if time_notes:
                prompt = prompt + "\n\n" + "\n".join(time_notes)
                logger.info("📅 已注入 time_language_notes 到 thinking Prompt")
            
            # 🆕 i18n: 注入语言指令
            from src.utils.language_detector import inject_language_instruction, translate_stage_label
            lang = context.metadata.get('response_language', 'zh')
            prompt = inject_language_instruction(prompt, lang, stage="thinking")
            
            logger.info(f"✅ 使用 prompts.yml 中的 thinking 模板（包含历史上下文、当前时间和知识库）")
            logger.info(f"📅 当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            logger.info(f"📊 历史消息数量: {len(history_messages)}")
            
            # 调用 AI 模型进行思考分析（流式输出）
            accumulated_content = ""
            async for chunk in self.ai_service.call_model_stream(stage="thinking", 
                prompt=prompt,
                session_id=context.session_id,
                temperature=0.3
            ):
                accumulated_content += chunk
                # 流式发送思考内容
                await self.websocket_service.send_stage_update(
                    session_id=context.session_id,
                    stage_id="stage_thinking",
                    content=chunk
                )
            
            logger.info(f"✅ 模型思考完成")
            logger.info(f"📊 思考内容长度: {len(accumulated_content)} 字符")
            
            # 🆕 保存思考结果到 context，以便传递给 SQL 生成阶段
            context.thinking_result = accumulated_content
            logger.info(f"✅ 思考结果已保存到 context")
            
            # 完成思考阶段（包含完整内容，以便前端保存到历史记录）
            await self.websocket_service.send_stage_complete(
                session_id=context.session_id,
                stage_id="stage_thinking",
                stage_name=thinking_stage_name,
                content=accumulated_content,  # 🔧 修复：发送完整的思考内容
                metadata={
                    "progress": 0.6,
                    "thinking_complete": True
                }
            )
            
            return {
                "success": True,
                "thinking": accumulated_content
            }
                
        except Exception as e:
            logger.error(f"❌ 模型思考失败: {str(e)}", exc_info=True)
            
            return {
                "success": False,
                "error": str(e)
            }
    
    def _convert_formatted_numbers_in_chart(self, chart_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        转换图表配置中的格式化数值字符串为纯数字
        
        处理以下格式：
        - "200.3K" → 200300
        - "1.5K" → 1500
        - "3.45%" → 3.45 (保留百分比数值，前端显示时再加%)
        - "1,234" → 1234
        
        Args:
            chart_config: 图表配置
            
        Returns:
            转换后的图表配置
        """
        try:
            if "chartConfig" not in chart_config or "series" not in chart_config["chartConfig"]:
                return chart_config
            
            series_list = chart_config["chartConfig"]["series"]
            if not isinstance(series_list, list):
                return chart_config
            
            for series in series_list:
                if "data" not in series or not isinstance(series["data"], list):
                    continue
                
                for data_point in series["data"]:
                    if "value" not in data_point:
                        continue
                    
                    value = data_point["value"]
                    
                    # 如果已经是数字，跳过
                    if isinstance(value, (int, float)):
                        continue
                    
                    # 如果是字符串，尝试转换
                    if isinstance(value, str):
                        converted_value = self._parse_formatted_number(value)
                        if converted_value is not None:
                            data_point["value"] = converted_value
                            logger.debug(f"🔢 转换数值: {value} → {converted_value}")
            
            return chart_config
            
        except Exception as e:
            logger.error(f"转换图表数值失败: {str(e)}")
            return chart_config
    
    def _parse_formatted_number(self, value_str: str) -> Optional[float]:
        """
        解析格式化的数值字符串
        
        Args:
            value_str: 格式化的数值字符串
            
        Returns:
            解析后的数值，如果无法解析则返回 None
        """
        try:
            value_str = value_str.strip()
            
            # 处理 K 后缀 (如 "200.3K" → 200300)
            if value_str.endswith('K') or value_str.endswith('k'):
                num_str = value_str[:-1].strip()
                return float(num_str) * 1000
            
            # 处理百分比 (如 "3.45%" → 3.45，保留数值用于图表显示)
            if value_str.endswith('%'):
                num_str = value_str[:-1].strip()
                return float(num_str)
            
            # 处理千位分隔符 (如 "1,234" → 1234)
            if ',' in value_str:
                num_str = value_str.replace(',', '')
                return float(num_str)
            
            # 尝试直接转换为数字
            return float(value_str)
            
        except (ValueError, AttributeError):
            return None
    
    async def _generate_chart_config(
        self,
        context: ChatContext,
        user_question: str,
        query_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        生成图表配置（分析计算 - 生成绘图代码）
        
        Args:
            context: 聊天上下文
            user_question: 用户问题
            query_result: 查询结果
            
        Returns:
            图表配置结果
        """
        logger.info("=" * 80)
        logger.info("📊 开始生成图表配置")
        logger.info("=" * 80)
        
        try:
            # 🔥 无数据时跳过图表生成
            rows = query_result.get("rows", [])
            if not rows:
                logger.info("⚠️ 查询结果为空，跳过图表生成")
                return {"success": False, "error": "查询结果为空，无需生成图表"}

            # 🆕 i18n: 翻译 stage 标签
            from src.utils.language_detector import translate_stage_label
            _chart_lang = context.metadata.get('response_language', 'zh')
            _chart_stage_name = translate_stage_label("生成图表", _chart_lang)
            
            # 发送阶段开始消息（不包含初始内容，避免显示"正在分析..."）
            await self.websocket_service.send_stage_start(
                session_id=context.session_id,
                stage_id="stage_chart",
                stage_name=_chart_stage_name,
                content="",  # 🔥 不发送初始内容，直接流式输出 JSON
                metadata={"progress": 0.9}
            )
            
            # 分析数据特征
            data_characteristics = self._analyze_data_characteristics(query_result)

            # 获取模型思考结果（包含用户意图、指标语义、分析思路）
            thinking_result = getattr(context, 'thinking_result', '') or ''

            # 构建 Prompt
            prompt = self.prompt_manager.render_prompt(
                PromptType.CHART_RECOMMENDATION,
                {
                    "user_question": user_question,
                    "query_result": json.dumps(query_result, ensure_ascii=False, indent=2),
                    "data_characteristics": json.dumps(data_characteristics, ensure_ascii=False, indent=2),
                    "thinking_result": thinking_result  # 传入思考结果，帮助 AI 理解用户意图
                }
            )
            
            # 🆕 i18n: 注入语言指令
            from src.utils.language_detector import inject_language_instruction
            lang = context.metadata.get('response_language', 'zh')
            prompt = inject_language_instruction(prompt, lang, stage="chart_recommendation")

            # 🆕 多时间段对比：注入 series 分配提示
            resolved_time_context = context.metadata.get('resolved_time_context')
            if resolved_time_context and len(resolved_time_context.date_ranges) > 1:
                date_ranges = resolved_time_context.date_ranges
                range_desc = "\n".join(
                    f"  - {dr.label}：{dr.start_date} 到 {dr.end_date}"
                    for dr in date_ranges
                )
                multi_period_hint = (
                    f"\n\n【多时间段对比提示 - 最高优先级】\n"
                    f"本次查询包含 {len(date_ranges)} 个时间段：\n{range_desc}\n"
                    f"SQL 结果中每列数值（如 sf_2025、sf_2026）对应一个时间段。\n"
                    f"请为每列数值生成独立的 series，确保图表能展示多时间段对比。\n"
                    f"图表类型建议：\n"
                    f"- 分组柱状图（bar）：每个时间段一组柱子，适合按维度对比\n"
                    f"- 折线图（line）：每个时间段一条折线，适合趋势对比\n"
                    f"- 饼图（pie）限制：饼图只能展示单一时间段的占比，无法对比多时间段。\n"
                    f"  如果用户明确要求饼图，请改用分组柱状图（bar）并在 reasoning 中说明原因。\n"
                    f"series 数组示例（{len(date_ranges)} 个系列）：\n"
                    + "\n".join(
                        f'  {{"name": "{dr.label}", "type": "bar", "data": [...]}}'
                        for dr in date_ranges
                    )
                )
                prompt = prompt + multi_period_hint
                logger.info(f"⏰ TimeResolver: 已注入多时间段对比图表提示（{len(date_ranges)} 个时间段）")
            
            logger.info(f"📝 图表推荐 Prompt 已生成")
            
            # 调用 AI 模型生成图表配置（流式输出）
            accumulated_content = ""
            async for chunk in self.ai_service.call_model_stream(stage="chart_recommendation", 
                prompt=prompt,
                session_id=context.session_id,
                temperature=0.1  # 图表类型推荐需要基本确定性，避免每次选不同图表类型
            ):
                accumulated_content += chunk
                # 流式发送图表配置内容
                await self.websocket_service.send_stage_update(
                    session_id=context.session_id,
                    stage_id="stage_chart",
                    content=chunk
                )
            
            logger.info(f"✅ 图表配置生成完成")
            logger.info(f"📊 配置内容长度: {len(accumulated_content)} 字符")
            
            # 解析 AI 返回的 JSON
            try:
                # 剥离 markdown 代码块包装（AI 有时返回 ```json ... ``` 格式）
                clean_content = accumulated_content.strip()
                if clean_content.startswith("```"):
                    # 去掉首行（```json 或 ```）和末尾的 ```
                    lines = clean_content.split("\n")
                    # 找到第一个 ``` 结束的位置（跳过首行）
                    end_idx = len(lines)
                    for i in range(len(lines) - 1, 0, -1):
                        if lines[i].strip() == "```":
                            end_idx = i
                            break
                    clean_content = "\n".join(lines[1:end_idx]).strip()
                chart_config = json.loads(clean_content)
                
                # 🔢 后处理：转换格式化的数值字符串为纯数字
                chart_config = self._convert_formatted_numbers_in_chart(chart_config)
                
                # 🔥 格式校验和修正：确保 series 是数组格式
                if "chartConfig" in chart_config and "series" in chart_config["chartConfig"]:
                    series = chart_config["chartConfig"]["series"]
                    
                    # 如果 series 是对象而不是数组，尝试修正
                    if isinstance(series, dict) and not isinstance(series, list):
                        logger.warning(f"⚠️ 检测到 series 是对象格式，尝试修正为数组格式")
                        logger.warning(f"📄 原始 series: {json.dumps(series, ensure_ascii=False)}")
                        
                        # 尝试将对象转换为数组
                        if "data" in series:
                            # 格式1: {"data": [...]}
                            fixed_series = [{
                                "name": chart_config["chartConfig"].get("title", "数据"),
                                "type": chart_config.get("recommendedChart", "bar"),
                                "data": series["data"]
                            }]
                            chart_config["chartConfig"]["series"] = fixed_series
                            logger.info(f"✅ series 已修正为数组格式")
                            logger.info(f"📄 修正后 series: {json.dumps(fixed_series, ensure_ascii=False)}")
                        else:
                            # 格式2: 无法识别的对象格式，推荐使用表格
                            logger.warning(f"⚠️ 无法修正 series 格式，推荐使用表格展示")
                            chart_config["recommendedChart"] = "table"
                            chart_config["chartConfig"]["series"] = []
                    
                    # 如果 series 是空数组，推荐使用表格
                    elif isinstance(series, list) and len(series) == 0:
                        logger.warning(f"⚠️ series 是空数组，推荐使用表格展示")
                        chart_config["recommendedChart"] = "table"
                
                # 🔥 关键修复：同时发送原始数据和图表配置
                # 前端 SmartChart 需要原始数据 {columns, rows} 来渲染图表
                # 🔥 同时注入 AI series 到 chartData，确保持久化后切换会话仍能恢复
                chart_data = {
                    "columns": query_result.get("columns", []),
                    "rows": query_result.get("rows", []),
                    "total_rows": query_result.get("total_rows", 0)
                }
                
                # 将 AI 生成的 series 和推荐类型注入 chartData，避免切换会话后丢失
                if "chartConfig" in chart_config and "series" in chart_config["chartConfig"]:
                    chart_data["series"] = chart_config["chartConfig"]["series"]
                if "recommendedChart" in chart_config:
                    chart_data["aiRecommendedType"] = chart_config["recommendedChart"]
                
                # 完成图表生成阶段
                await self.websocket_service.send_stage_complete(
                    session_id=context.session_id,
                    stage_id="stage_chart",
                    stage_name=_chart_stage_name,
                    content="",  # 内容已通过 stage_update 发送
                    metadata={
                        "progress": 0.92,
                        "chart_type": chart_config.get("recommendedChart", "bar"),
                        "chart_config": chart_config,
                        "chartData": chart_data  # 🔥 添加原始数据供前端渲染
                    }
                )
                
                return {
                    "success": True,
                    "chart_config": chart_config
                }
                
            except json.JSONDecodeError as e:
                logger.error(f"❌ 解析图表配置失败: {str(e)}")
                logger.error(f"📄 原始内容: {accumulated_content[:500]}...")
                
                # 完成阶段（即使解析失败）
                await self.websocket_service.send_stage_complete(
                    session_id=context.session_id,
                    stage_id="stage_chart",
                    stage_name=_chart_stage_name,
                    content="图表配置生成完成",
                    metadata={"progress": 0.92}
                )
                
                return {
                    "success": False,
                    "error": f"解析图表配置失败: {str(e)}"
                }
                
        except Exception as e:
            logger.error(f"❌ 生成图表配置失败: {str(e)}", exc_info=True)
            
            return {
                "success": False,
                "error": str(e)
            }
    
    def _analyze_data_characteristics(self, query_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        分析数据特征
        
        Args:
            query_result: 查询结果
            
        Returns:
            数据特征
        """
        characteristics = {
            "row_count": query_result.get("total_rows", 0),
            "column_count": len(query_result.get("columns", [])),
            "columns": query_result.get("columns", []),
            "has_numeric_data": False,
            "has_categorical_data": False,
            "has_time_data": False
        }
        
        # 分析列类型
        data = query_result.get("data", [])
        if data and len(data) > 0:
            first_row = data[0]
            for col in characteristics["columns"]:
                value = first_row.get(col)
                if isinstance(value, (int, float)):
                    characteristics["has_numeric_data"] = True
                elif isinstance(value, str):
                    characteristics["has_categorical_data"] = True
                    # 简单判断是否是时间数据
                    if any(keyword in col.lower() for keyword in ["date", "time", "year", "month", "day"]):
                        characteristics["has_time_data"] = True
        
        return characteristics
    
    def _format_query_result_for_description(self, query_result: Dict[str, Any]) -> str:
        """
        格式化完整的查询结果用于数据描述（本地模型）
        
        Args:
            query_result: 查询结果
            
        Returns:
            格式化的完整数据字符串
        """
        try:
            columns = query_result.get("columns", [])
            rows = query_result.get("rows", [])  # 注意：是 rows 不是 data
            total_rows = query_result.get("total_rows", 0)
            
            if not rows:
                return "查询结果为空"
            
            # 本地模型可以处理完整数据，不限制行数
            lines = []
            lines.append(f"查询结果（共 {total_rows} 行）：")
            lines.append("")
            
            # 表头
            header = " | ".join(columns)
            lines.append(header)
            lines.append("-" * len(header))
            
            # 所有数据行（rows 是数组的数组）
            for row in rows:
                row_values = []
                for i, value in enumerate(row):
                    # 格式化数值
                    if isinstance(value, float):
                        value = f"{value:.2f}"
                    elif isinstance(value, int):
                        value = f"{value:,}"  # 添加千位分隔符
                    row_values.append(str(value))
                lines.append(" | ".join(row_values))
            
            return "\n".join(lines)
            
        except Exception as e:
            logger.error(f"格式化查询结果失败: {str(e)}")
            return "查询结果数据"

    def _format_resolved_time_context_for_description(self, context: ChatContext) -> str:
        """
        为 result_description 提供权威时间上下文，避免模型在无时间列时猜测 FW/日期。
        """
        resolved_time_context = context.metadata.get("resolved_time_context")
        if not resolved_time_context:
            return "无（禁止推断或编造 FW/日期）"
        date_ranges = getattr(resolved_time_context, "date_ranges", None) or []
        if not date_ranges:
            return "无（禁止推断或编造 FW/日期）"
        parts = []
        for dr in date_ranges:
            parts.append(f"{dr.label}({dr.start_date} 到 {dr.end_date})")
        return "；".join(parts)
    
    def _format_query_result_summary(self, query_result: Dict[str, Any]) -> str:
        """
        格式化查询结果摘要（前5行数据）
        
        Args:
            query_result: 查询结果
            
        Returns:
            格式化的数据摘要字符串
        """
        try:
            columns = query_result.get("columns", [])
            data = query_result.get("data", [])
            total_rows = query_result.get("total_rows", 0)
            
            if not data:
                return "查询结果为空"
            
            # 只取前5行数据
            sample_data = data[:5]
            
            # 格式化为表格字符串
            lines = []
            lines.append(f"查询结果（共 {total_rows} 行，显示前 {len(sample_data)} 行）：")
            lines.append("")
            
            # 表头
            header = " | ".join(columns)
            lines.append(header)
            lines.append("-" * len(header))
            
            # 数据行
            for row in sample_data:
                row_values = []
                for col in columns:
                    value = row.get(col, "")
                    # 格式化数值
                    if isinstance(value, float):
                        value = f"{value:.2f}"
                    row_values.append(str(value))
                lines.append(" | ".join(row_values))
            
            return "\n".join(lines)
            
        except Exception as e:
            logger.error(f"格式化查询结果摘要失败: {str(e)}")
            return "查询结果数据"
    
    async def _describe_result(
        self,
        context: ChatContext,
        user_question: str,
        query_result: Dict[str, Any],
        analysis_text: str
    ) -> Dict[str, Any]:
        """
        数据结果描述阶段
        
        Args:
            context: 聊天上下文
            user_question: 用户问题
            query_result: 查询结果
            analysis_text: 数据分析文本
            
        Returns:
            描述结果
        """
        logger.info("=" * 80)
        logger.info("📝 开始数据结果描述")
        logger.info("=" * 80)
        
        try:
            # 🆕 i18n: 翻译 stage 标签
            from src.utils.language_detector import translate_stage_label
            _desc_lang = context.metadata.get('response_language', 'zh')
            _desc_stage_name = translate_stage_label("数据结果描述", _desc_lang)
            
            # 发送阶段开始消息
            await self.websocket_service.send_stage_start(
                session_id=context.session_id,
                stage_id="stage_description",
                stage_name=_desc_stage_name,
                content="",  # 不显示"正在生成..."这样的非正式内容
                metadata={"progress": 0.95}
            )
            
            # 从配置文件加载 Prompt 模板
            prompt_template = self.prompt_manager.get_template(PromptType.RESULT_DESCRIPTION)
            
            # 格式化完整的查询结果数据（本地模型可以处理更多数据）
            formatted_data = self._format_query_result_for_description(query_result)
            
            # 准备模板变量
            template_vars = {
                "user_question": user_question,
                "intent_type": context.intent.value if context.intent else "smart_query",
                "total_rows": query_result.get('total_rows', 0),
                "column_count": len(query_result.get('columns', [])),
                "columns": ', '.join(query_result.get('columns', [])),
                "analysis_text": formatted_data,  # 传入完整的格式化数据
                "resolved_time_context": self._format_resolved_time_context_for_description(context),
            }
            
            # 渲染 Prompt
            prompt = self.prompt_manager.render_prompt(PromptType.RESULT_DESCRIPTION, template_vars)
            
            # 🆕 i18n: 注入语言指令
            from src.utils.language_detector import inject_language_instruction
            lang = context.metadata.get('response_language', 'zh')
            prompt = inject_language_instruction(prompt, lang, stage="result_description")
            
            logger.info(f"📝 数据结果描述 Prompt 已生成（使用配置模板 v{prompt_template.version}）")
            logger.info(f"📊 查询结果数据行数: {query_result.get('total_rows', 0)}")
            
            # 使用模型生成描述（流式输出，路由到配置指定的模型）
            accumulated_content = ""
            async for chunk in self.ai_service.call_model_stream(stage="result_description", 
                prompt=prompt,
                session_id=context.session_id,
                temperature=0.1  # 数据描述需要基本确定性，避免数字格式化不一致
            ):
                accumulated_content += chunk
                # 流式发送描述内容
                await self.websocket_service.send_stage_update(
                    session_id=context.session_id,
                    stage_id="stage_description",
                    content=chunk
                )
            
            logger.info(f"✅ 数据结果描述完成")
            logger.info(f"📊 描述内容长度: {len(accumulated_content)} 字符")
            logger.info(f"📝 描述内容:\n{accumulated_content}")
            
            # 完成描述阶段
            await self.websocket_service.send_stage_complete(
                session_id=context.session_id,
                stage_id="stage_description",
                stage_name=_desc_stage_name,
                content="",  # 内容已通过 stage_update 发送
                metadata={
                    "progress": 0.98,
                    "description_complete": True
                }
            )
            
            return {
                "success": True,
                "description": accumulated_content
            }
                
        except Exception as e:
            logger.error(f"❌ 数据结果描述失败: {str(e)}", exc_info=True)
            
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _handle_error_recovery(self, context: ChatContext, user_response: str) -> Dict[str, Any]:
        """处理错误恢复"""
        if user_response.lower() in ["重试", "retry", "再试一次"]:
            context.retry_count += 1
            if context.retry_count <= self.max_retry_count:
                # 重置到上一个成功的阶段
                context.update_stage(ChatStage.INTENT_RECOGNITION)
                return await self._execute_chat_pipeline(context, user_response, None)
            else:
                return {
                    "success": False,
                    "error": "重试次数已达上限",
                    "session_id": context.session_id
                }
        else:
            # 作为新问题处理
            context.update_stage(ChatStage.INTENT_RECOGNITION)
            return await self._execute_chat_pipeline(context, user_response, None)
    
    async def _handle_followup_question(self, context: ChatContext, user_question: str) -> Dict[str, Any]:
        """处理追问"""
        try:
            # 使用本地模型处理追问
            followup_prompt = f"""
            基于之前的查询结果，回答用户的追问：
            
            用户追问: {user_question}
            
            之前的查询结果:
            {context.query_result}
            
            历史数据:
            {self._format_previous_data(context.previous_data)}
            
            请基于已有数据回答用户问题。
            """
            
            await self.websocket_service.send_thinking_message(
                context.session_id, "正在分析您的追问...", {"stage": "followup", "progress": 0.5}
            )
            
            response = await self.ai_service.call_model(stage="data_analysis", 
                prompt=followup_prompt,
                session_id=context.session_id
            )
            
            if response["success"]:
                await self.websocket_service.send_result_message(
                    context.session_id,
                    response["content"],
                    {"type": "followup_answer"}
                )
                
                return {
                    "success": True,
                    "answer": response["content"],
                    "session_id": context.session_id,
                    "type": "followup"
                }
            else:
                return {
                    "success": False,
                    "error": "追问处理失败",
                    "session_id": context.session_id
                }
                
        except Exception as e:
            logger.error(f"追问处理失败: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "session_id": context.session_id
            }
    
    def _extract_key_context_from_ai_message(self, content: str) -> str:
        """
        从 AI 消息中提取关键上下文信息（时间范围、筛选条件、SQL 日期）
        
        AI 消息格式：【意图澄清/Intent Clarification】...【模型思考/Model Thinking】...【SQL生成/SQL Generation】...
        重点提取：意图澄清中的时间/筛选信息 + SQL 中的 WHERE 条件
        """
        import re
        key_parts = []
        
        # 1. 提取意图澄清内容（包含时间范围、筛选条件的自然语言描述）
        clarification_match = re.search(
            r'【(?:意图澄清|Intent Clarification)】\s*(.*?)(?=【|$)', content, re.DOTALL
        )
        if clarification_match:
            cl_text = clarification_match.group(1).strip()
            key_parts.append(f"【意图澄清】\n{cl_text[:400]}")
        
        # 2. 提取模型思考中的时间范围信息（通常在前 500 字符内）
        thinking_match = re.search(
            r'【(?:模型思考|Model Thinking)】\s*(.*?)(?=【|$)', content, re.DOTALL
        )
        if thinking_match:
            thinking_text = thinking_match.group(1).strip()
            key_parts.append(f"【模型思考摘要】\n{thinking_text[:500]}")
        
        # 3. 提取 SQL 中的 WHERE 条件（最关键：包含具体日期范围）
        sql_match = re.search(
            r'【(?:SQL生成|SQL Generation|sql_generation)】\s*(.*?)(?=【|$)', content, re.DOTALL
        )
        if sql_match:
            sql_text = sql_match.group(1).strip()
            # sql_text 可能是 JSON 格式 {"sql": "...", "explanation": "..."}
            # 尝试提取 sql 字段
            sql_field_match = re.search(r'"sql"\s*:\s*"(.*?)"(?:,|\s*})', sql_text, re.DOTALL)
            if sql_field_match:
                actual_sql = sql_field_match.group(1).replace('\\n', '\n').replace('\\"', '"')
                # 提取 WHERE 子句
                where_match = re.search(r'(WHERE\s+.*?)(?:GROUP BY|ORDER BY|LIMIT|$)', actual_sql, re.DOTALL | re.IGNORECASE)
                if where_match:
                    key_parts.append(f"【SQL WHERE条件（时间范围/筛选条件）】\n{where_match.group(1).strip()}")
                else:
                    key_parts.append(f"【SQL生成】\n{actual_sql[:400]}")
            else:
                # 非 JSON 格式，直接提取 WHERE
                where_match = re.search(r'(WHERE\s+.*?)(?:GROUP BY|ORDER BY|LIMIT|$)', sql_text, re.DOTALL | re.IGNORECASE)
                if where_match:
                    key_parts.append(f"【SQL WHERE条件（时间范围/筛选条件）】\n{where_match.group(1).strip()}")
                else:
                    key_parts.append(f"【SQL生成】\n{sql_text[:400]}")
        
        # 如果没有提取到任何结构化内容，直接截取前 800 字符
        if not key_parts:
            return content[:800]
        
        return "\n\n".join(key_parts)

    def _format_history_context(self, history_messages: List[Dict[str, Any]]) -> str:
        """
        格式化历史对话上下文
        
        Args:
            history_messages: 历史消息列表
            
        Returns:
            格式化后的历史对话字符串
        """
        if not history_messages:
            return "无历史对话"
        
        formatted = []
        # 最近5轮对话（10条消息）
        for msg in history_messages[-10:]:
            role = "用户" if msg.get('role') == 'user' else "AI助手"
            content = msg.get('content', '')
            if content:
                if msg.get('role') == 'user':
                    # 用户消息保留完整内容
                    formatted.append(f"{role}: {content}")
                else:
                    # AI 消息：智能提取关键上下文（时间范围、SQL WHERE条件）
                    # 避免因截断导致日期范围丢失
                    key_context = self._extract_key_context_from_ai_message(content)
                    formatted.append(f"{role}:\n{key_context}")
        
        return "\n\n---\n\n".join(formatted) if formatted else "无历史对话"
    
    def _calculate_time_ranges(self, current_date: datetime) -> Dict[str, Any]:
        """
        计算时间范围（财周定义：周日至周六）
        
        Args:
            current_date: 当前日期时间
            
        Returns:
            包含各种时间范围的字典
        """
        from datetime import timedelta
        
        # 获取当前日期的星期几（0=周一, 6=周日）
        weekday = current_date.weekday()
        
        # 计算本周的周日（财周开始）
        # 如果今天是周日（weekday=6），days_since_sunday=0
        # 如果今天是周一（weekday=0），days_since_sunday=1
        # 如果今天是周六（weekday=5），days_since_sunday=6
        if weekday == 6:  # 周日
            days_since_sunday = 0
        else:
            days_since_sunday = weekday + 1
        
        this_week_start = current_date.date() - timedelta(days=days_since_sunday)
        this_week_end = this_week_start + timedelta(days=6)
        
        # 上周 = 本周开始日期 - 7天
        last_week_start = this_week_start - timedelta(days=7)
        last_week_end = this_week_start - timedelta(days=1)
        
        # 格式化星期几的中文名称
        weekday_names = ['一', '二', '三', '四', '五', '六', '日']
        current_weekday_cn = weekday_names[weekday]
        
        return {
            "current_date": current_date.strftime('%Y-%m-%d'),
            "current_weekday": current_weekday_cn,
            "current_datetime": current_date.strftime('%Y-%m-%d %H:%M:%S'),
            "this_week_start": this_week_start.strftime('%Y-%m-%d'),
            "this_week_end": this_week_end.strftime('%Y-%m-%d'),
            "last_week_start": last_week_start.strftime('%Y-%m-%d'),
            "last_week_end": last_week_end.strftime('%Y-%m-%d'),
            "this_month_start": current_date.replace(day=1).strftime('%Y-%m-%d'),
            "yesterday": (current_date.date() - timedelta(days=1)).strftime('%Y-%m-%d')
        }
    
    def _format_current_date_with_ranges(self) -> str:
        """
        格式化当前日期和时间范围信息
        
        Returns:
            包含当前日期和预计算时间范围的字符串
        """
        now = datetime.now()
        ranges = self._calculate_time_ranges(now)
        
        return f"""当前时间: {ranges['current_datetime']} (星期{ranges['current_weekday']})

📅 预计算的时间范围（财周定义：周日至周六）:
- 今天: {ranges['current_date']}
- 昨天: {ranges['yesterday']}
- 本周: {ranges['this_week_start']}（周日）至 {ranges['this_week_end']}（周六）
- 上周: {ranges['last_week_start']}（周日）至 {ranges['last_week_end']}（周六）
- 本月开始: {ranges['this_month_start']}

⚠️ 重要提示：
- 请直接使用上述预计算的日期范围，不要自己重新计算
- "上周"是指最近一个完整的财务周（周日至周六）
- 财务周从周日开始，到周六结束"""
    
    def get_session_status(self, session_id: str) -> Dict[str, Any]:
        """获取会话状态"""
        context = self.active_contexts.get(session_id)
        if not context:
            return {
                "session_id": session_id,
                "exists": False
            }
        
        return {
            "session_id": session_id,
            "exists": True,
            "current_stage": context.current_stage.value,
            "intent": context.intent.value,
            "selected_tables": context.selected_tables,
            "error_count": context.error_count,
            "retry_count": context.retry_count,
            "created_at": context.created_at.isoformat(),
            "updated_at": context.updated_at.isoformat(),
            "has_result": context.query_result is not None,
            "previous_data_count": len(context.previous_data)
        }
    
    def cleanup_session(self, session_id: str) -> bool:
        """清理会话"""
        if session_id in self.active_contexts:
            del self.active_contexts[session_id]
            logger.info(f"会话 {session_id} 已清理")
            return True
        return False
    
    def get_all_sessions_status(self) -> Dict[str, Any]:
        """获取所有会话状态"""
        return {
            "total_sessions": len(self.active_contexts),
            "sessions": {
                session_id: {
                    "current_stage": context.current_stage.value,
                    "intent": context.intent.value,
                    "error_count": context.error_count,
                    "updated_at": context.updated_at.isoformat()
                }
                for session_id, context in self.active_contexts.items()
            }
        }


# 全局实例
_chat_orchestrator = None

def get_chat_orchestrator() -> ChatOrchestrator:
    """获取对话编排器实例"""
    global _chat_orchestrator
    if _chat_orchestrator is None:
        _chat_orchestrator = ChatOrchestrator()
    return _chat_orchestrator