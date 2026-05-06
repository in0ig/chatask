"""
基于云端Qwen的智能表选择算法

任务 5.2.3 的核心实现
"""

from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import logging
import json
from datetime import datetime

from src.services.ai_model_service import AIModelService
from src.services.semantic_context_aggregator import SemanticContextAggregator
from src.services.semantic_similarity_engine import SemanticSimilarityEngine, KeywordAnalysis
from src.services.multi_source_data_integration import MultiSourceDataIntegrationEngine
from src.services.table_relation_semantic_injection import TableRelationSemanticInjectionService

logger = logging.getLogger(__name__)


class TableSelectionConfidence(Enum):
    """表选择置信度等级"""
    HIGH = "high"      # 高置信度 (>0.8)
    MEDIUM = "medium"  # 中等置信度 (0.5-0.8)
    LOW = "low"        # 低置信度 (<0.5)


@dataclass
class TableCandidate:
    """候选表信息"""
    table_id: str
    table_name: str
    table_comment: str
    relevance_score: float
    confidence: TableSelectionConfidence
    selection_reasons: List[str]
    matched_keywords: List[str]
    business_meaning: str
    relation_paths: List[Dict[str, Any]]
    semantic_context: Dict[str, Any]


@dataclass
class TableSelectionResult:
    """表选择结果"""
    primary_tables: List[TableCandidate]
    related_tables: List[TableCandidate]
    selection_strategy: str
    total_relevance_score: float
    recommended_joins: List[Dict[str, Any]]
    selection_explanation: str
    processing_time: float
    ai_reasoning: str


class IntelligentTableSelector:
    """基于云端Qwen的智能表选择算法"""
    
    def __init__(self):
        """初始化智能表选择器"""
        # 创建默认配置用于测试
        default_config = {
            'qwen_cloud': {
                'api_key': 'test_key',
                'base_url': 'https://dashscope.aliyuncs.com/api/v1',
                'model_name': 'qwen-turbo',
                'max_tokens': 2000,
                'temperature': 0.1
            },
            'openai_local': {
                'api_key': 'test_key',
                'base_url': 'http://localhost:11434/v1',
                'model_name': 'llama2',
                'max_tokens': 2000,
                'temperature': 0.1
            }
        }
        
        try:
            self.ai_service = AIModelService(default_config)
        except Exception as e:
            logger.warning(f"AI服务初始化失败，将在运行时处理: {str(e)}")
            self.ai_service = None
            
        self.semantic_aggregator = SemanticContextAggregator()
        self.similarity_engine = SemanticSimilarityEngine()
        self.data_integration = MultiSourceDataIntegrationEngine()
        self.relation_module = TableRelationSemanticInjectionService()
        
        # 配置参数
        self.max_primary_tables = 3  # 最大主表数量
        self.max_related_tables = 5  # 最大关联表数量
        self.min_relevance_threshold = 0.3  # 最小相关性阈值
        self.confidence_thresholds = {
            "high": 0.8,
            "medium": 0.5,
            "low": 0.3
        }
        
        # 统计信息
        self.selection_stats = {
            "total_selections": 0,
            "successful_selections": 0,
            "average_processing_time": 0.0,
            "average_relevance_score": 0.0
        }
    
    async def select_tables(
        self,
        user_question: str,
        data_source_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> TableSelectionResult:
        """
        智能表选择主入口
        
        Args:
            user_question: 用户问题
            data_source_id: 数据源ID（可选）
            context: 上下文信息（可选）
            
        Returns:
            TableSelectionResult: 表选择结果
        """
        start_time = datetime.now()
        
        try:
            logger.info(f"开始智能表选择，用户问题: {user_question}")
            
            # 1. 获取完整的五模块语义上下文
            semantic_context = await self._get_semantic_context(
                user_question, data_source_id, context
            )
            
            # 2. 获取候选表列表
            candidate_tables = await self._get_candidate_tables(
                semantic_context, data_source_id
            )
            
            # 3. 基于Qwen模型进行智能表选择
            selection_result = await self._perform_ai_table_selection(
                user_question, candidate_tables, semantic_context
            )
            
            # 4. 分析表关联路径
            selection_result = await self._analyze_table_relations(
                selection_result, semantic_context
            )
            
            # 5. 生成推荐JOIN语句
            selection_result = await self._generate_recommended_joins(
                selection_result, semantic_context
            )
            
            # 6. 计算处理时间并更新统计
            processing_time = (datetime.now() - start_time).total_seconds()
            selection_result.processing_time = processing_time
            
            self._update_selection_stats(selection_result, processing_time)
            
            logger.info(f"智能表选择完成，处理时间: {processing_time:.2f}s")
            return selection_result
            
        except Exception as e:
            logger.error(f"智能表选择失败: {str(e)}", exc_info=True)
            # 返回空结果而不是抛出异常
            return TableSelectionResult(
                primary_tables=[],
                related_tables=[],
                selection_strategy="error_fallback",
                total_relevance_score=0.0,
                recommended_joins=[],
                selection_explanation=f"表选择过程中发生错误: {str(e)}",
                processing_time=(datetime.now() - start_time).total_seconds(),
                ai_reasoning="由于错误无法完成AI推理"
            )
    
    async def _get_semantic_context(
        self,
        user_question: str,
        data_source_id: Optional[str],
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """获取完整的五模块语义上下文"""
        try:
            # 使用语义上下文聚合器获取完整上下文
            aggregation_request = {
                "user_question": user_question,
                "data_source_id": data_source_id,
                "include_modules": [
                    "data_source", "table_structure", "table_relation",
                    "data_dictionary", "knowledge_base"
                ],
                "token_budget": 4000,  # 为表选择分配足够的Token预算
                "context": context or {}
            }
            
            semantic_context = await self.semantic_aggregator.aggregate_semantic_context(
                aggregation_request
            )
            
            return semantic_context
            
        except Exception as e:
            logger.error(f"获取语义上下文失败: {str(e)}")
            return {
                "keyword_analysis": {"all_keywords": []},
                "modules": {},
                "token_usage": 0
            }
    
    async def _get_candidate_tables(
        self,
        semantic_context: Dict[str, Any],
        data_source_id: Optional[str]
    ) -> List[Dict[str, Any]]:
        """获取候选表列表"""
        try:
            # 从多源数据整合引擎获取表信息
            tables_info = await self.data_integration.get_integrated_metadata(
                data_source_id=data_source_id,
                include_tables=True,
                include_relations=True
            )
            
            return tables_info.get("tables", [])
            
        except Exception as e:
            logger.error(f"获取候选表失败: {str(e)}")
            return []
    
    async def _perform_ai_table_selection(
        self,
        user_question: str,
        candidate_tables: List[Dict[str, Any]],
        semantic_context: Dict[str, Any]
    ) -> TableSelectionResult:
        """基于Qwen模型进行智能表选择"""
        try:
            # 检查AI服务是否可用
            if self.ai_service is None:
                logger.warning("AI服务不可用，直接降级到相似度选择")
                return await self._fallback_similarity_selection(
                    user_question, candidate_tables, semantic_context
                )
            
            # 构建AI模型的输入Prompt
            prompt = self._build_table_selection_prompt(
                user_question, candidate_tables, semantic_context
            )
            
            # 调用Qwen模型
            ai_response = await self.ai_service.generate_response(
                prompt=prompt,
                model_type="qwen",
                temperature=0.1,  # 使用较低的温度确保结果稳定
                max_tokens=2000
            )
            
            # 解析AI响应
            selection_result = self._parse_ai_selection_response(
                ai_response, candidate_tables, semantic_context
            )
            
            return selection_result
            
        except Exception as e:
            logger.error(f"AI表选择失败: {str(e)}")
            # 降级到基于相似度的选择
            return await self._fallback_similarity_selection(
                user_question, candidate_tables, semantic_context
            )
    
    def _build_table_selection_prompt(
        self,
        user_question: str,
        candidate_tables: List[Dict[str, Any]],
        semantic_context: Dict[str, Any]
    ) -> str:
        """构建表选择的AI Prompt"""
        
        # 提取关键信息
        keywords = semantic_context.get("keyword_analysis", {}).get("all_keywords", [])
        business_terms = semantic_context.get("modules", {}).get("data_dictionary", {})
        knowledge_items = semantic_context.get("modules", {}).get("knowledge_base", {})
        
        # 构建候选表信息
        tables_info = []
        for table in candidate_tables[:20]:  # 限制表数量避免Token溢出
            table_info = {
                "id": table.get("id", ""),
                "name": table.get("table_name", ""),
                "comment": table.get("table_comment", ""),
                "fields": [f.get("field_name", "") for f in table.get("fields", [])[:10]]
            }
            tables_info.append(table_info)
        
        prompt = f"""
你是一个专业的数据分析师，需要根据用户问题智能选择最相关的数据表。

用户问题: {user_question}

提取的关键词: {', '.join(keywords[:10])}

可用数据表:
{json.dumps(tables_info, ensure_ascii=False, indent=2)}

业务术语上下文:
{json.dumps(business_terms, ensure_ascii=False, indent=2)[:1000]}

知识库上下文:
{json.dumps(knowledge_items, ensure_ascii=False, indent=2)[:1000]}

请分析用户问题，选择最相关的数据表，并按以下JSON格式返回结果:

{{
    "primary_tables": [
        {{
            "table_id": "表ID",
            "table_name": "表名",
            "relevance_score": 0.95,
            "confidence": "high",
            "selection_reasons": ["选择理由1", "选择理由2"],
            "matched_keywords": ["匹配的关键词"],
            "business_meaning": "业务含义说明"
        }}
    ],
    "related_tables": [
        {{
            "table_id": "关联表ID",
            "table_name": "关联表名",
            "relevance_score": 0.75,
            "confidence": "medium",
            "selection_reasons": ["关联理由"],
            "matched_keywords": ["匹配的关键词"],
            "business_meaning": "关联业务含义"
        }}
    ],
    "selection_strategy": "策略说明",
    "selection_explanation": "详细的选择解释",
    "ai_reasoning": "AI推理过程"
}}

要求:
1. primary_tables: 最多3个最相关的主表
2. related_tables: 最多5个可能需要关联的表
3. relevance_score: 0-1之间的相关性评分
4. confidence: high/medium/low 置信度等级
5. 提供清晰的选择理由和业务含义解释
6. 考虑表之间的关联关系
"""
        
        return prompt
    
    def _parse_ai_selection_response(
        self,
        ai_response: str,
        candidate_tables: List[Dict[str, Any]],
        semantic_context: Dict[str, Any]
    ) -> TableSelectionResult:
        """解析AI选择响应"""
        try:
            # 尝试解析JSON响应
            response_data = json.loads(ai_response)
            
            # 构建主表候选列表
            primary_tables = []
            for table_data in response_data.get("primary_tables", []):
                candidate = self._build_table_candidate(
                    table_data, candidate_tables, semantic_context
                )
                if candidate:
                    primary_tables.append(candidate)
            
            # 构建关联表候选列表
            related_tables = []
            for table_data in response_data.get("related_tables", []):
                candidate = self._build_table_candidate(
                    table_data, candidate_tables, semantic_context
                )
                if candidate:
                    related_tables.append(candidate)
            
            # 计算总体相关性评分
            total_score = sum(t.relevance_score for t in primary_tables)
            if related_tables:
                total_score += sum(t.relevance_score for t in related_tables) * 0.5
            
            return TableSelectionResult(
                primary_tables=primary_tables,
                related_tables=related_tables,
                selection_strategy=response_data.get("selection_strategy", "ai_based"),
                total_relevance_score=total_score,
                recommended_joins=[],  # 将在后续步骤中填充
                selection_explanation=response_data.get("selection_explanation", ""),
                processing_time=0.0,  # 将在调用方设置
                ai_reasoning=response_data.get("ai_reasoning", "")
            )
            
        except json.JSONDecodeError as e:
            logger.error(f"AI响应JSON解析失败: {str(e)}")
            # 尝试从文本中提取表名
            return self._extract_tables_from_text(
                ai_response, candidate_tables, semantic_context
            )
        except Exception as e:
            logger.error(f"解析AI响应失败: {str(e)}")
            return TableSelectionResult(
                primary_tables=[],
                related_tables=[],
                selection_strategy="parse_error",
                total_relevance_score=0.0,
                recommended_joins=[],
                selection_explanation=f"解析AI响应时发生错误: {str(e)}",
                processing_time=0.0,
                ai_reasoning="解析失败"
            )
    
    def _build_table_candidate(
        self,
        table_data: Dict[str, Any],
        candidate_tables: List[Dict[str, Any]],
        semantic_context: Dict[str, Any]
    ) -> Optional[TableCandidate]:
        """构建表候选对象"""
        try:
            table_id = table_data.get("table_id", "")
            table_name = table_data.get("table_name", "")
            
            # 查找对应的候选表信息
            table_info = None
            for candidate in candidate_tables:
                if (candidate.get("id") == table_id or 
                    candidate.get("table_name") == table_name):
                    table_info = candidate
                    break
            
            if not table_info:
                logger.warning(f"未找到表信息: {table_id} / {table_name}")
                return None
            
            # 确定置信度等级
            relevance_score = float(table_data.get("relevance_score", 0.0))
            confidence = self._determine_confidence(relevance_score)
            
            return TableCandidate(
                table_id=table_info.get("id", table_id),
                table_name=table_info.get("table_name", table_name),
                table_comment=table_info.get("table_comment", ""),
                relevance_score=relevance_score,
                confidence=confidence,
                selection_reasons=table_data.get("selection_reasons", []),
                matched_keywords=table_data.get("matched_keywords", []),
                business_meaning=table_data.get("business_meaning", ""),
                relation_paths=[],  # 将在关联分析中填充
                semantic_context=semantic_context
            )
            
        except Exception as e:
            logger.error(f"构建表候选对象失败: {str(e)}")
            return None
    
    def _determine_confidence(self, relevance_score: float) -> TableSelectionConfidence:
        """确定置信度等级"""
        if relevance_score >= self.confidence_thresholds["high"]:
            return TableSelectionConfidence.HIGH
        elif relevance_score >= self.confidence_thresholds["medium"]:
            return TableSelectionConfidence.MEDIUM
        else:
            return TableSelectionConfidence.LOW
    
    async def _fallback_similarity_selection(
        self,
        user_question: str,
        candidate_tables: List[Dict[str, Any]],
        semantic_context: Dict[str, Any]
    ) -> TableSelectionResult:
        """基于相似度的降级选择策略"""
        try:
            logger.info("使用相似度降级选择策略")
            
            # 分析用户问题
            keyword_analysis = self.similarity_engine.analyze_user_question(user_question)
            
            # 计算每个表的相似度
            table_similarities = []
            for table in candidate_tables:
                similarity_match = self.similarity_engine.calculate_table_similarity(
                    keyword_analysis, table
                )
                table_similarities.append((table, similarity_match))
            
            # 排序并选择最相关的表
            table_similarities.sort(key=lambda x: x[1].similarity_score, reverse=True)
            
            # 构建主表列表（前3个）
            primary_tables = []
            for table, match in table_similarities[:self.max_primary_tables]:
                if match.similarity_score >= self.min_relevance_threshold:
                    candidate = TableCandidate(
                        table_id=table.get("id", ""),
                        table_name=table.get("table_name", ""),
                        table_comment=table.get("table_comment", ""),
                        relevance_score=match.similarity_score,
                        confidence=self._determine_confidence(match.similarity_score),
                        selection_reasons=match.match_reasons,
                        matched_keywords=match.matched_keywords,
                        business_meaning=match.business_meaning,
                        relation_paths=[],
                        semantic_context=semantic_context
                    )
                    primary_tables.append(candidate)
            
            # 构建关联表列表（接下来的5个）
            related_tables = []
            for table, match in table_similarities[self.max_primary_tables:self.max_primary_tables + self.max_related_tables]:
                if match.similarity_score >= self.min_relevance_threshold * 0.7:  # 降低关联表阈值
                    candidate = TableCandidate(
                        table_id=table.get("id", ""),
                        table_name=table.get("table_name", ""),
                        table_comment=table.get("table_comment", ""),
                        relevance_score=match.similarity_score,
                        confidence=self._determine_confidence(match.similarity_score),
                        selection_reasons=match.match_reasons,
                        matched_keywords=match.matched_keywords,
                        business_meaning=match.business_meaning,
                        relation_paths=[],
                        semantic_context=semantic_context
                    )
                    related_tables.append(candidate)
            
            total_score = sum(t.relevance_score for t in primary_tables)
            if related_tables:
                total_score += sum(t.relevance_score for t in related_tables) * 0.5
            
            return TableSelectionResult(
                primary_tables=primary_tables,
                related_tables=related_tables,
                selection_strategy="similarity_fallback",
                total_relevance_score=total_score,
                recommended_joins=[],
                selection_explanation="使用基于语义相似度的降级选择策略",
                processing_time=0.0,
                ai_reasoning="降级到相似度匹配算法"
            )
            
        except Exception as e:
            logger.error(f"降级选择策略失败: {str(e)}")
            return TableSelectionResult(
                primary_tables=[],
                related_tables=[],
                selection_strategy="fallback_error",
                total_relevance_score=0.0,
                recommended_joins=[],
                selection_explanation=f"降级选择策略失败: {str(e)}",
                processing_time=0.0,
                ai_reasoning="降级策略执行失败"
            )
    
    def _extract_tables_from_text(
        self,
        ai_response: str,
        candidate_tables: List[Dict[str, Any]],
        semantic_context: Dict[str, Any]
    ) -> TableSelectionResult:
        """从AI文本响应中提取表名"""
        try:
            # 简单的表名提取逻辑
            table_names = []
            for table in candidate_tables:
                table_name = table.get("table_name", "")
                if table_name and table_name.lower() in ai_response.lower():
                    table_names.append(table)
            
            # 构建基本的选择结果
            primary_tables = []
            for i, table in enumerate(table_names[:self.max_primary_tables]):
                candidate = TableCandidate(
                    table_id=table.get("id", ""),
                    table_name=table.get("table_name", ""),
                    table_comment=table.get("table_comment", ""),
                    relevance_score=0.6 - i * 0.1,  # 简单的评分策略
                    confidence=TableSelectionConfidence.MEDIUM,
                    selection_reasons=["从AI响应文本中提取"],
                    matched_keywords=[],
                    business_meaning="",
                    relation_paths=[],
                    semantic_context=semantic_context
                )
                primary_tables.append(candidate)
            
            return TableSelectionResult(
                primary_tables=primary_tables,
                related_tables=[],
                selection_strategy="text_extraction",
                total_relevance_score=sum(t.relevance_score for t in primary_tables),
                recommended_joins=[],
                selection_explanation="从AI文本响应中提取表名",
                processing_time=0.0,
                ai_reasoning="文本提取模式"
            )
            
        except Exception as e:
            logger.error(f"文本提取失败: {str(e)}")
            return TableSelectionResult(
                primary_tables=[],
                related_tables=[],
                selection_strategy="extraction_error",
                total_relevance_score=0.0,
                recommended_joins=[],
                selection_explanation=f"文本提取失败: {str(e)}",
                processing_time=0.0,
                ai_reasoning="文本提取失败"
            )
    
    async def _analyze_table_relations(
        self,
        selection_result: TableSelectionResult,
        semantic_context: Dict[str, Any]
    ) -> TableSelectionResult:
        """分析表关联路径"""
        try:
            all_tables = selection_result.primary_tables + selection_result.related_tables
            if len(all_tables) < 2:
                return selection_result
            
            # 使用表关联语义注入模块分析关联
            for table in all_tables:
                table_info = {
                    "table_name": table.table_name,
                    "table_comment": table.table_comment
                }
                
                # 分析与其他表的关联路径
                relation_paths = []
                for other_table in all_tables:
                    if other_table.table_id != table.table_id:
                        # 查找关联路径
                        other_table_info = {
                            "id": other_table.table_id,
                            "table_name": other_table.table_name,
                            "table_comment": other_table.table_comment
                        }
                        relations = self.relation_module.inject_table_relation_semantics(
                            table_ids=[table_info.get("id"), other_table_info.get("id")]
                        )
                        
                        if relations:
                            # 转换TableRelation对象为字典格式
                            for relation in relations:
                                relation_dict = {
                                    "target_table": relation.to_table,
                                    "recommended_join_type": relation.join_type.value,
                                    "join_condition": f"{relation.from_field} = {relation.to_field}",
                                    "confidence": relation.confidence,
                                    "reasoning": relation.business_description
                                }
                                relation_paths.append(relation_dict)
                
                table.relation_paths = relation_paths
            
            return selection_result
            
        except Exception as e:
            logger.error(f"分析表关联失败: {str(e)}")
            return selection_result
    
    async def _generate_recommended_joins(
        self,
        selection_result: TableSelectionResult,
        semantic_context: Dict[str, Any]
    ) -> TableSelectionResult:
        """生成推荐的JOIN语句"""
        try:
            recommended_joins = []
            
            # 基于主表和关联表生成JOIN推荐
            for primary_table in selection_result.primary_tables:
                for related_table in selection_result.related_tables:
                    # 查找两表之间的关联路径
                    for relation_path in primary_table.relation_paths:
                        if relation_path.get("target_table") == related_table.table_name:
                            join_recommendation = {
                                "left_table": primary_table.table_name,
                                "right_table": related_table.table_name,
                                "join_type": relation_path.get("recommended_join_type", "INNER"),
                                "join_condition": relation_path.get("join_condition", ""),
                                "confidence": relation_path.get("confidence", 0.5),
                                "reasoning": relation_path.get("reasoning", "")
                            }
                            recommended_joins.append(join_recommendation)
            
            selection_result.recommended_joins = recommended_joins
            return selection_result
            
        except Exception as e:
            logger.error(f"生成JOIN推荐失败: {str(e)}")
            return selection_result
    
    def _update_selection_stats(
        self,
        selection_result: TableSelectionResult,
        processing_time: float
    ):
        """更新选择统计信息"""
        try:
            self.selection_stats["total_selections"] += 1
            
            if selection_result.primary_tables:
                self.selection_stats["successful_selections"] += 1
            
            # 更新平均处理时间
            total_time = (self.selection_stats["average_processing_time"] * 
                         (self.selection_stats["total_selections"] - 1) + processing_time)
            self.selection_stats["average_processing_time"] = (
                total_time / self.selection_stats["total_selections"]
            )
            
            # 更新平均相关性评分
            if selection_result.total_relevance_score > 0:
                total_score = (self.selection_stats["average_relevance_score"] * 
                              (self.selection_stats["successful_selections"] - 1) + 
                              selection_result.total_relevance_score)
                self.selection_stats["average_relevance_score"] = (
                    total_score / self.selection_stats["successful_selections"]
                )
            
        except Exception as e:
            logger.error(f"更新统计信息失败: {str(e)}")
    
    def get_selection_statistics(self) -> Dict[str, Any]:
        """获取选择统计信息"""
        return {
            "total_selections": self.selection_stats["total_selections"],
            "successful_selections": self.selection_stats["successful_selections"],
            "success_rate": (
                self.selection_stats["successful_selections"] / 
                max(self.selection_stats["total_selections"], 1)
            ),
            "average_processing_time": self.selection_stats["average_processing_time"],
            "average_relevance_score": self.selection_stats["average_relevance_score"],
            "configuration": {
                "max_primary_tables": self.max_primary_tables,
                "max_related_tables": self.max_related_tables,
                "min_relevance_threshold": self.min_relevance_threshold,
                "confidence_thresholds": self.confidence_thresholds
            }
        }