"""
知识库语义注入服务

实现业务术语（TERM）的智能匹配和注入、业务逻辑（LOGIC）的上下文增强和规则应用、
事件知识（EVENT）的时间维度和业务场景处理，以及全局知识和表级知识的分层注入策略。
"""

from typing import List, Dict, Any, Optional, Set, Tuple
from datetime import datetime, date
from dataclasses import dataclass
from enum import Enum
import re
import logging
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from src.models.knowledge_base_model import KnowledgeBase
from src.models.knowledge_item_model import KnowledgeItem
from src.utils import get_db_session

logger = logging.getLogger(__name__)


class KnowledgeType(str, Enum):
    """知识类型枚举"""
    TERM = "TERM"      # 业务术语
    LOGIC = "LOGIC"    # 业务逻辑
    EVENT = "EVENT"    # 事件知识


class KnowledgeScope(str, Enum):
    """知识范围枚举"""
    GLOBAL = "GLOBAL"  # 全局知识
    TABLE = "TABLE"    # 表级知识


@dataclass
class TermKnowledge:
    """业务术语知识"""
    id: str
    name: str
    explanation: str
    example_question: Optional[str] = None
    scope: str = "GLOBAL"
    table_id: Optional[str] = None
    relevance_score: float = 0.0


@dataclass
class LogicKnowledge:
    """业务逻辑知识"""
    id: str
    explanation: str
    example_question: Optional[str] = None
    scope: str = "GLOBAL"
    table_id: Optional[str] = None
    relevance_score: float = 0.0


@dataclass
class EventKnowledge:
    """事件知识"""
    id: str
    explanation: str
    event_date_start: Optional[datetime] = None
    event_date_end: Optional[datetime] = None
    scope: str = "GLOBAL"
    table_id: Optional[str] = None
    relevance_score: float = 0.0
    is_active: bool = False  # 是否在当前时间范围内活跃


@dataclass
class KnowledgeSemanticInfo:
    """知识库语义信息"""
    terms: List[TermKnowledge]
    logics: List[LogicKnowledge]
    events: List[EventKnowledge]
    total_relevance_score: float = 0.0


@dataclass
class SemanticInjectionResult:
    """语义注入结果"""
    enhanced_context: str
    knowledge_info: KnowledgeSemanticInfo
    injection_summary: Dict[str, Any]


class KnowledgeSemanticInjectionService:
    """知识库语义注入服务"""
    
    def __init__(self, db_session: Optional[Session] = None):
        self.db = db_session or next(get_db_session())
        self.term_cache: Dict[str, List[TermKnowledge]] = {}
        self.logic_cache: Dict[str, List[LogicKnowledge]] = {}
        self.event_cache: Dict[str, List[EventKnowledge]] = {}
        
    def inject_knowledge_semantics(
        self,
        user_question: str,
        table_ids: Optional[List[str]] = None,
        include_global: bool = True,
        max_terms: int = 10,
        max_logics: int = 5,
        max_events: int = 3
    ) -> SemanticInjectionResult:
        """
        注入知识库语义信息
        
        Args:
            user_question: 用户问题
            table_ids: 相关表ID列表
            include_global: 是否包含全局知识
            max_terms: 最大术语数量
            max_logics: 最大逻辑数量
            max_events: 最大事件数量
            
        Returns:
            语义注入结果
        """
        try:
            logger.info(f"开始知识库语义注入，问题: {user_question[:100]}...")
            
            # 1. 提取问题关键词
            keywords = self._extract_keywords(user_question)
            logger.debug(f"提取的关键词: {keywords}")
            
            # 2. 匹配业务术语
            terms = self._match_terms(keywords, table_ids, include_global, max_terms)
            logger.debug(f"匹配到 {len(terms)} 个业务术语")
            
            # 3. 匹配业务逻辑
            logics = self._match_logics(keywords, table_ids, include_global, max_logics)
            logger.debug(f"匹配到 {len(logics)} 个业务逻辑")
            
            # 4. 匹配事件知识
            events = self._match_events(keywords, table_ids, include_global, max_events)
            logger.debug(f"匹配到 {len(events)} 个事件知识")
            
            # 5. 构建知识库语义信息
            knowledge_info = KnowledgeSemanticInfo(
                terms=terms,
                logics=logics,
                events=events,
                total_relevance_score=sum([t.relevance_score for t in terms]) +
                                    sum([l.relevance_score for l in logics]) +
                                    sum([e.relevance_score for e in events])
            )
            
            # 6. 生成增强上下文
            enhanced_context = self._generate_enhanced_context(
                user_question, knowledge_info
            )
            
            # 7. 生成注入摘要
            injection_summary = self._generate_injection_summary(knowledge_info)
            
            result = SemanticInjectionResult(
                enhanced_context=enhanced_context,
                knowledge_info=knowledge_info,
                injection_summary=injection_summary
            )
            
            logger.info(f"知识库语义注入完成，总相关性得分: {knowledge_info.total_relevance_score:.2f}")
            return result
            
        except Exception as e:
            logger.error(f"知识库语义注入失败: {str(e)}", exc_info=True)
            # 返回空结果而不是抛出异常
            return SemanticInjectionResult(
                enhanced_context=user_question,
                knowledge_info=KnowledgeSemanticInfo(terms=[], logics=[], events=[]),
                injection_summary={"error": str(e)}
            )
    
    def _extract_keywords(self, text: str) -> Set[str]:
        """提取文本关键词"""
        # 简单的关键词提取，实际可以使用更复杂的NLP技术
        # 移除标点符号，转换为小写
        cleaned_text = re.sub(r'[^\w\s]', ' ', text.lower())
        
        # 中文分词：简单按字符分割，保留英文单词
        words = []
        current_word = ""
        
        for char in cleaned_text:
            if char.isspace():
                if current_word:
                    words.append(current_word)
                    current_word = ""
            elif char.isascii() and char.isalpha():
                # 英文字符，累积成单词
                current_word += char
            else:
                # 中文字符，先保存当前英文单词，再添加中文字符
                if current_word:
                    words.append(current_word)
                    current_word = ""
                if not char.isspace():
                    words.append(char)
        
        # 添加最后一个单词
        if current_word:
            words.append(current_word)
        
        # 过滤停用词和短词
        stop_words = {'的', '是', '在', '有', '和', '与', '或', '但', '如果', '那么', '这', '那', '什么', '怎么', '为什么'}
        keywords = {word for word in words if len(word) > 0 and word not in stop_words}
        
        return keywords
    
    def _match_terms(
        self,
        keywords: Set[str],
        table_ids: Optional[List[str]],
        include_global: bool,
        max_terms: int
    ) -> List[TermKnowledge]:
        """匹配业务术语"""
        try:
            # 构建查询
            query = self.db.query(KnowledgeItem).join(KnowledgeBase).filter(
                KnowledgeItem.type == KnowledgeType.TERM.value,
                KnowledgeBase.status == True
            )
            
            # 添加范围过滤
            scope_filters = []
            if include_global:
                scope_filters.append(KnowledgeBase.scope == KnowledgeScope.GLOBAL.value)
            if table_ids:
                scope_filters.append(
                    and_(
                        KnowledgeBase.scope == KnowledgeScope.TABLE.value,
                        KnowledgeBase.table_id.in_(table_ids)
                    )
                )
            
            if scope_filters:
                query = query.filter(or_(*scope_filters))
            
            knowledge_items = query.all()
            
            # 计算相关性并转换为TermKnowledge
            terms = []
            for item in knowledge_items:
                relevance_score = self._calculate_term_relevance(item, keywords)
                if relevance_score > 0:
                    term = TermKnowledge(
                        id=item.id,
                        name=item.name or "",
                        explanation=item.explanation,
                        example_question=item.example_question,
                        scope=item.knowledge_base.scope,
                        table_id=item.knowledge_base.table_id,
                        relevance_score=relevance_score
                    )
                    terms.append(term)
            
            # 按相关性排序并限制数量
            terms.sort(key=lambda x: x.relevance_score, reverse=True)
            return terms[:max_terms]
            
        except Exception as e:
            logger.error(f"匹配业务术语失败: {str(e)}", exc_info=True)
            return []
    
    def _match_logics(
        self,
        keywords: Set[str],
        table_ids: Optional[List[str]],
        include_global: bool,
        max_logics: int
    ) -> List[LogicKnowledge]:
        """匹配业务逻辑"""
        try:
            # 构建查询
            query = self.db.query(KnowledgeItem).join(KnowledgeBase).filter(
                KnowledgeItem.type == KnowledgeType.LOGIC.value,
                KnowledgeBase.status == True
            )
            
            # 添加范围过滤
            scope_filters = []
            if include_global:
                scope_filters.append(KnowledgeBase.scope == KnowledgeScope.GLOBAL.value)
            if table_ids:
                scope_filters.append(
                    and_(
                        KnowledgeBase.scope == KnowledgeScope.TABLE.value,
                        KnowledgeBase.table_id.in_(table_ids)
                    )
                )
            
            if scope_filters:
                query = query.filter(or_(*scope_filters))
            
            knowledge_items = query.all()
            
            # 计算相关性并转换为LogicKnowledge
            logics = []
            for item in knowledge_items:
                relevance_score = self._calculate_logic_relevance(item, keywords)
                if relevance_score > 0:
                    logic = LogicKnowledge(
                        id=item.id,
                        explanation=item.explanation,
                        example_question=item.example_question,
                        scope=item.knowledge_base.scope,
                        table_id=item.knowledge_base.table_id,
                        relevance_score=relevance_score
                    )
                    logics.append(logic)
            
            # 按相关性排序并限制数量
            logics.sort(key=lambda x: x.relevance_score, reverse=True)
            return logics[:max_logics]
            
        except Exception as e:
            logger.error(f"匹配业务逻辑失败: {str(e)}", exc_info=True)
            return []
    
    def _match_events(
        self,
        keywords: Set[str],
        table_ids: Optional[List[str]],
        include_global: bool,
        max_events: int
    ) -> List[EventKnowledge]:
        """匹配事件知识"""
        try:
            # 构建查询
            query = self.db.query(KnowledgeItem).join(KnowledgeBase).filter(
                KnowledgeItem.type == KnowledgeType.EVENT.value,
                KnowledgeBase.status == True
            )
            
            # 添加范围过滤
            scope_filters = []
            if include_global:
                scope_filters.append(KnowledgeBase.scope == KnowledgeScope.GLOBAL.value)
            if table_ids:
                scope_filters.append(
                    and_(
                        KnowledgeBase.scope == KnowledgeScope.TABLE.value,
                        KnowledgeBase.table_id.in_(table_ids)
                    )
                )
            
            if scope_filters:
                query = query.filter(or_(*scope_filters))
            
            knowledge_items = query.all()
            
            # 计算相关性并转换为EventKnowledge
            events = []
            current_time = datetime.now()
            
            for item in knowledge_items:
                relevance_score = self._calculate_event_relevance(item, keywords)
                if relevance_score > 0:
                    # 判断事件是否在当前时间范围内活跃
                    is_active = self._is_event_active(item, current_time)
                    
                    event = EventKnowledge(
                        id=item.id,
                        explanation=item.explanation,
                        event_date_start=item.event_date_start,
                        event_date_end=item.event_date_end,
                        scope=item.knowledge_base.scope,
                        table_id=item.knowledge_base.table_id,
                        relevance_score=relevance_score,
                        is_active=is_active
                    )
                    events.append(event)
            
            # 按相关性排序，活跃事件优先
            events.sort(key=lambda x: (x.is_active, x.relevance_score), reverse=True)
            return events[:max_events]
            
        except Exception as e:
            logger.error(f"匹配事件知识失败: {str(e)}", exc_info=True)
            return []
    
    def _calculate_term_relevance(self, item: KnowledgeItem, keywords: Set[str]) -> float:
        """计算业务术语相关性"""
        # 🆕 全局知识库总是包含，给予基础分数
        if item.knowledge_base.scope == KnowledgeScope.GLOBAL.value:
            score = 1.0  # 全局知识基础分数
        else:
            score = 0.5  # 表级知识基础分数
        
        # 检查术语名称匹配
        if item.name:
            name_words = self._extract_keywords(item.name.lower())
            name_matches = len(keywords.intersection(name_words))
            score += name_matches * 2.0  # 名称匹配权重更高
        
        # 检查解释内容匹配
        explanation_words = self._extract_keywords(item.explanation.lower())
        explanation_matches = len(keywords.intersection(explanation_words))
        score += explanation_matches * 1.0
        
        # 检查示例问题匹配
        if item.example_question:
            example_words = self._extract_keywords(item.example_question.lower())
            example_matches = len(keywords.intersection(example_words))
            score += example_matches * 1.5
        
        return score
    
    def _calculate_logic_relevance(self, item: KnowledgeItem, keywords: Set[str]) -> float:
        """计算业务逻辑相关性"""
    def _calculate_logic_relevance(self, item: KnowledgeItem, keywords: Set[str]) -> float:
        """计算业务逻辑相关性"""
        # 🆕 全局知识库总是包含，给予基础分数
        if item.knowledge_base.scope == KnowledgeScope.GLOBAL.value:
            score = 1.0  # 全局知识基础分数
        else:
            score = 0.5  # 表级知识基础分数
        
        # 检查解释内容匹配
        explanation_words = self._extract_keywords(item.explanation.lower())
        explanation_matches = len(keywords.intersection(explanation_words))
        score += explanation_matches * 1.0
        
        # 检查示例问题匹配
        if item.example_question:
            example_words = self._extract_keywords(item.example_question.lower())
            example_matches = len(keywords.intersection(example_words))
            score += example_matches * 1.5
        
        # 业务逻辑关键词加权
        logic_keywords = {'规', '则', '逻', '辑', '条', '件', '如', '果', '那', '么', '计', '算', '公', '式', '算', '法'}
        logic_matches = len(keywords.intersection(logic_keywords))
        score += logic_matches * 2.0
        
        return score
    
    def _calculate_event_relevance(self, item: KnowledgeItem, keywords: Set[str]) -> float:
        """计算事件知识相关性"""
        # 🆕 全局知识库总是包含，给予基础分数
        if item.knowledge_base.scope == KnowledgeScope.GLOBAL.value:
            score = 1.0  # 全局知识基础分数
        else:
            score = 0.5  # 表级知识基础分数
        
        # 检查解释内容匹配
        explanation_words = self._extract_keywords(item.explanation.lower())
        explanation_matches = len(keywords.intersection(explanation_words))
        score += explanation_matches * 1.0
        
        # 事件相关关键词加权
        event_keywords = {'事', '件', '活', '动', '促', '销', '节', '日', '时', '间', '期', '间', '开', '始', '结', '束'}
        event_matches = len(keywords.intersection(event_keywords))
        score += event_matches * 2.0
        
        return score
    
    def _is_event_active(self, item: KnowledgeItem, current_time: datetime) -> bool:
        """判断事件是否在当前时间范围内活跃"""
        if not item.event_date_start:
            return False
        
        # 事件已开始
        if current_time < item.event_date_start:
            return False
        
        # 如果有结束时间，检查是否已结束
        if item.event_date_end and current_time > item.event_date_end:
            return False
        
        return True
    
    def _generate_enhanced_context(
        self,
        user_question: str,
        knowledge_info: KnowledgeSemanticInfo
    ) -> str:
        """生成增强上下文"""
        context_parts = [f"用户问题: {user_question}"]
        
        # 添加业务术语上下文
        if knowledge_info.terms:
            context_parts.append("\n业务术语:")
            for term in knowledge_info.terms:
                context_parts.append(f"- {term.name}: {term.explanation}")
                if term.example_question:
                    context_parts.append(f"  示例: {term.example_question}")
        
        # 添加业务逻辑上下文
        if knowledge_info.logics:
            context_parts.append("\n业务逻辑:")
            for logic in knowledge_info.logics:
                context_parts.append(f"- {logic.explanation}")
                if logic.example_question:
                    context_parts.append(f"  示例: {logic.example_question}")
        
        # 添加事件知识上下文
        if knowledge_info.events:
            context_parts.append("\n相关事件:")
            for event in knowledge_info.events:
                status = "进行中" if event.is_active else "已结束"
                context_parts.append(f"- [{status}] {event.explanation}")
                if event.event_date_start:
                    date_info = f"开始时间: {event.event_date_start.strftime('%Y-%m-%d')}"
                    if event.event_date_end:
                        date_info += f", 结束时间: {event.event_date_end.strftime('%Y-%m-%d')}"
                    context_parts.append(f"  {date_info}")
        
        return "\n".join(context_parts)
    
    def _generate_injection_summary(self, knowledge_info: KnowledgeSemanticInfo) -> Dict[str, Any]:
        """生成注入摘要"""
        return {
            "total_knowledge_items": len(knowledge_info.terms) + len(knowledge_info.logics) + len(knowledge_info.events),
            "terms_count": len(knowledge_info.terms),
            "logics_count": len(knowledge_info.logics),
            "events_count": len(knowledge_info.events),
            "active_events_count": sum(1 for e in knowledge_info.events if e.is_active),
            "total_relevance_score": knowledge_info.total_relevance_score,
            "average_relevance_score": (
                knowledge_info.total_relevance_score / 
                max(1, len(knowledge_info.terms) + len(knowledge_info.logics) + len(knowledge_info.events))
            ),
            "knowledge_distribution": {
                "global_knowledge": sum(1 for item in 
                    knowledge_info.terms + knowledge_info.logics + knowledge_info.events 
                    if item.scope == "GLOBAL"),
                "table_knowledge": sum(1 for item in 
                    knowledge_info.terms + knowledge_info.logics + knowledge_info.events 
                    if item.scope == "TABLE")
            }
        }
    
    def get_knowledge_by_table(self, table_id: str) -> KnowledgeSemanticInfo:
        """获取指定表的所有知识"""
        try:
            # 查询表级知识
            query = self.db.query(KnowledgeItem).join(KnowledgeBase).filter(
                KnowledgeBase.scope == KnowledgeScope.TABLE.value,
                KnowledgeBase.table_id == table_id,
                KnowledgeBase.status == True
            )
            
            knowledge_items = query.all()
            
            terms = []
            logics = []
            events = []
            current_time = datetime.now()
            
            for item in knowledge_items:
                if item.type == KnowledgeType.TERM.value:
                    term = TermKnowledge(
                        id=item.id,
                        name=item.name or "",
                        explanation=item.explanation,
                        example_question=item.example_question,
                        scope=item.knowledge_base.scope,
                        table_id=item.knowledge_base.table_id,
                        relevance_score=1.0  # 表级知识默认高相关性
                    )
                    terms.append(term)
                elif item.type == KnowledgeType.LOGIC.value:
                    logic = LogicKnowledge(
                        id=item.id,
                        explanation=item.explanation,
                        example_question=item.example_question,
                        scope=item.knowledge_base.scope,
                        table_id=item.knowledge_base.table_id,
                        relevance_score=1.0
                    )
                    logics.append(logic)
                elif item.type == KnowledgeType.EVENT.value:
                    is_active = self._is_event_active(item, current_time)
                    event = EventKnowledge(
                        id=item.id,
                        explanation=item.explanation,
                        event_date_start=item.event_date_start,
                        event_date_end=item.event_date_end,
                        scope=item.knowledge_base.scope,
                        table_id=item.knowledge_base.table_id,
                        relevance_score=1.0,
                        is_active=is_active
                    )
                    events.append(event)
            
            return KnowledgeSemanticInfo(
                terms=terms,
                logics=logics,
                events=events,
                total_relevance_score=len(terms) + len(logics) + len(events)
            )
            
        except Exception as e:
            logger.error(f"获取表级知识失败: {str(e)}", exc_info=True)
            return KnowledgeSemanticInfo(terms=[], logics=[], events=[])
    
    def get_global_knowledge(self) -> KnowledgeSemanticInfo:
        """获取全局知识"""
        try:
            # 查询全局知识
            query = self.db.query(KnowledgeItem).join(KnowledgeBase).filter(
                KnowledgeBase.scope == KnowledgeScope.GLOBAL.value,
                KnowledgeBase.status == True
            )
            
            knowledge_items = query.all()
            
            terms = []
            logics = []
            events = []
            current_time = datetime.now()
            
            for item in knowledge_items:
                if item.type == KnowledgeType.TERM.value:
                    term = TermKnowledge(
                        id=item.id,
                        name=item.name or "",
                        explanation=item.explanation,
                        example_question=item.example_question,
                        scope=item.knowledge_base.scope,
                        table_id=item.knowledge_base.table_id,
                        relevance_score=0.8  # 全局知识默认中等相关性
                    )
                    terms.append(term)
                elif item.type == KnowledgeType.LOGIC.value:
                    logic = LogicKnowledge(
                        id=item.id,
                        explanation=item.explanation,
                        example_question=item.example_question,
                        scope=item.knowledge_base.scope,
                        table_id=item.knowledge_base.table_id,
                        relevance_score=0.8
                    )
                    logics.append(logic)
                elif item.type == KnowledgeType.EVENT.value:
                    is_active = self._is_event_active(item, current_time)
                    event = EventKnowledge(
                        id=item.id,
                        explanation=item.explanation,
                        event_date_start=item.event_date_start,
                        event_date_end=item.event_date_end,
                        scope=item.knowledge_base.scope,
                        table_id=item.knowledge_base.table_id,
                        relevance_score=0.8,
                        is_active=is_active
                    )
                    events.append(event)
            
            return KnowledgeSemanticInfo(
                terms=terms,
                logics=logics,
                events=events,
                total_relevance_score=len(terms) * 0.8 + len(logics) * 0.8 + len(events) * 0.8
            )
            
        except Exception as e:
            logger.error(f"获取全局知识失败: {str(e)}", exc_info=True)
            return KnowledgeSemanticInfo(terms=[], logics=[], events=[])
    
    def clear_cache(self):
        """清空缓存"""
        self.term_cache.clear()
        self.logic_cache.clear()
        self.event_cache.clear()
        logger.info("知识库语义注入缓存已清空")