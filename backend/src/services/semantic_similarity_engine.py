"""
语义相似度计算引擎

任务 5.2.2 的实现：
- 基于用户问题进行关键词提取和语义分析
- 实现表名、字段名、业务含义的多维度相似度计算
- 支持中文业务术语到技术字段的智能映射
- 添加知识库术语的语义匹配和权重计算

验收标准: 语义匹配准确率>85%，支持复杂业务术语理解
需求: 4.2, 8.4
"""

import logging
import re
import math
from typing import Dict, List, Set, Tuple, Optional, Any
from dataclasses import dataclass
from collections import defaultdict, Counter
import jieba
import jieba.posseg as pseg

logger = logging.getLogger(__name__)


@dataclass
class SemanticMatch:
    """语义匹配结果"""
    target_id: str
    target_name: str
    target_type: str  # 'table', 'field', 'business_term', 'knowledge_term'
    similarity_score: float
    match_reasons: List[str]
    matched_keywords: List[str]
    business_meaning: Optional[str] = None
    technical_mapping: Optional[str] = None


@dataclass
class KeywordAnalysis:
    """关键词分析结果"""
    chinese_terms: List[str]
    english_terms: List[str]
    business_keywords: List[str]
    technical_keywords: List[str]
    domain_keywords: List[str]
    all_keywords: Set[str]


@dataclass
class SimilarityWeights:
    """相似度权重配置"""
    exact_match: float = 1.0
    partial_match: float = 0.7
    semantic_match: float = 0.6
    business_term_match: float = 0.8
    knowledge_term_match: float = 0.7
    field_type_match: float = 0.5
    comment_match: float = 0.4


class SemanticSimilarityEngine:
    """
    语义相似度计算引擎
    
    这是任务 5.2.2 的核心实现，提供：
    1. 基于用户问题进行关键词提取和语义分析
    2. 实现表名、字段名、业务含义的多维度相似度计算
    3. 支持中文业务术语到技术字段的智能映射
    4. 添加知识库术语的语义匹配和权重计算
    """
    
    def __init__(self):
        self.weights = SimilarityWeights()
        
        # 初始化jieba分词
        jieba.initialize()
        
        # 业务术语映射词典
        self.business_term_mappings = {
            # 通用业务术语
            '用户': ['user', 'customer', 'member'],
            '订单': ['order', 'purchase', 'transaction'],
            '商品': ['product', 'item', 'goods'],
            '价格': ['price', 'cost', 'amount'],
            '时间': ['time', 'date', 'datetime', 'timestamp'],
            '数量': ['quantity', 'count', 'number', 'amount'],
            '状态': ['status', 'state', 'flag'],
            '类型': ['type', 'category', 'kind'],
            '名称': ['name', 'title', 'label'],
            '描述': ['description', 'comment', 'remark'],
            '创建': ['create', 'add', 'insert'],
            '更新': ['update', 'modify', 'change'],
            '删除': ['delete', 'remove', 'drop'],
            '查询': ['select', 'query', 'search'],
            
            # 财务相关
            '收入': ['income', 'revenue', 'earning'],
            '支出': ['expense', 'cost', 'spending'],
            '利润': ['profit', 'margin', 'gain'],
            '销售': ['sales', 'sell', 'revenue'],
            
            # 人力资源
            '员工': ['employee', 'staff', 'worker'],
            '部门': ['department', 'division', 'team'],
            '职位': ['position', 'job', 'role'],
            '薪资': ['salary', 'wage', 'pay'],
            
            # 库存管理
            '库存': ['inventory', 'stock', 'storage'],
            '入库': ['inbound', 'receive', 'stock_in'],
            '出库': ['outbound', 'ship', 'stock_out'],
            '仓库': ['warehouse', 'storage', 'depot']
        }
        
        # 技术术语映射
        self.technical_term_mappings = {
            'id': ['标识', '编号', '主键'],
            'name': ['名称', '姓名', '标题'],
            'code': ['代码', '编码', '代号'],
            'type': ['类型', '种类', '分类'],
            'status': ['状态', '情况', '标志'],
            'date': ['日期', '时间'],
            'time': ['时间', '时刻'],
            'count': ['数量', '计数', '总数'],
            'amount': ['金额', '数量', '总额'],
            'price': ['价格', '单价', '费用'],
            'total': ['总计', '合计', '总数'],
            'avg': ['平均', '均值'],
            'max': ['最大', '最高'],
            'min': ['最小', '最低']
        }
        
        # 停用词
        self.stop_words = {
            '的', '是', '在', '有', '和', '与', '或', '但', '了', '着', '过',
            '这', '那', '些', '个', '中', '上', '下', '来', '去', '出', '到',
            'the', 'is', 'in', 'and', 'or', 'but', 'a', 'an', 'to', 'of',
            'for', 'with', 'by', 'from', 'at', 'on', 'as', 'be', 'are'
        }
        
        logger.info("语义相似度计算引擎初始化完成")
    
    def analyze_user_question(self, user_question: str) -> KeywordAnalysis:
        """
        基于用户问题进行关键词提取和语义分析
        
        这是任务 5.2.2 的第一个功能点。
        
        Args:
            user_question: 用户自然语言问题
            
        Returns:
            关键词分析结果
        """
        try:
            logger.info(f"分析用户问题: {user_question[:100]}...")
            
            # 1. 中文分词和词性标注
            chinese_terms = self._extract_chinese_terms(user_question)
            
            # 2. 英文词汇提取
            english_terms = self._extract_english_terms(user_question)
            
            # 3. 业务关键词识别
            business_keywords = self._identify_business_keywords(chinese_terms + english_terms)
            
            # 4. 技术关键词识别
            technical_keywords = self._identify_technical_keywords(chinese_terms + english_terms)
            
            # 5. 领域关键词识别
            domain_keywords = self._identify_domain_keywords(user_question)
            
            # 6. 合并所有关键词
            all_keywords = set()
            all_keywords.update(chinese_terms)
            all_keywords.update(english_terms)
            all_keywords.update(business_keywords)
            all_keywords.update(technical_keywords)
            all_keywords.update(domain_keywords)
            
            # 过滤停用词
            all_keywords = {kw for kw in all_keywords if kw not in self.stop_words and len(kw) > 1}
            
            result = KeywordAnalysis(
                chinese_terms=chinese_terms,
                english_terms=english_terms,
                business_keywords=business_keywords,
                technical_keywords=technical_keywords,
                domain_keywords=domain_keywords,
                all_keywords=all_keywords
            )
            
            logger.info(f"关键词分析完成，提取到 {len(all_keywords)} 个关键词")
            return result
            
        except Exception as e:
            logger.error(f"用户问题分析失败: {str(e)}", exc_info=True)
            return KeywordAnalysis([], [], [], [], [], set())
    
    def calculate_table_similarity(
        self,
        keyword_analysis: KeywordAnalysis,
        table_info: Dict[str, Any]
    ) -> SemanticMatch:
        """
        计算表的语义相似度
        
        这是任务 5.2.2 的第二个功能点：表名相似度计算。
        
        Args:
            keyword_analysis: 关键词分析结果
            table_info: 表信息 {'id', 'table_name', 'table_comment', 'fields'}
            
        Returns:
            语义匹配结果
        """
        try:
            table_name = table_info.get('table_name', '').lower()
            table_comment = table_info.get('table_comment', '') or ''
            
            similarity_score = 0.0
            match_reasons = []
            matched_keywords = []
            
            # 1. 表名精确匹配
            for keyword in keyword_analysis.all_keywords:
                if keyword.lower() in table_name:
                    similarity_score += self.weights.exact_match
                    match_reasons.append(f"表名精确匹配: {keyword}")
                    matched_keywords.append(keyword)
            
            # 2. 表注释匹配
            if table_comment:
                comment_lower = table_comment.lower()
                for keyword in keyword_analysis.all_keywords:
                    if keyword.lower() in comment_lower:
                        similarity_score += self.weights.comment_match
                        match_reasons.append(f"表注释匹配: {keyword}")
                        matched_keywords.append(keyword)
            
            # 3. 业务术语映射匹配
            business_score = self._calculate_business_term_match(
                keyword_analysis.business_keywords,
                table_name,
                table_comment
            )
            if business_score > 0:
                similarity_score += business_score
                match_reasons.append("业务术语映射匹配")
            
            # 4. 字段名间接匹配
            fields = table_info.get('fields', [])
            field_match_score = self._calculate_field_indirect_match(
                keyword_analysis.all_keywords,
                fields
            )
            if field_match_score > 0:
                similarity_score += field_match_score * 0.3  # 降权
                match_reasons.append("字段名间接匹配")
            
            # 归一化分数
            similarity_score = min(1.0, similarity_score)
            
            return SemanticMatch(
                target_id=table_info.get('id', ''),
                target_name=table_name,
                target_type='table',
                similarity_score=similarity_score,
                match_reasons=match_reasons,
                matched_keywords=list(set(matched_keywords)),
                business_meaning=table_comment
            )
            
        except Exception as e:
            logger.error(f"计算表相似度失败: {str(e)}")
            return SemanticMatch('', '', 'table', 0.0, [], [])
    
    def calculate_field_similarity(
        self,
        keyword_analysis: KeywordAnalysis,
        field_info: Dict[str, Any],
        table_context: Optional[Dict[str, Any]] = None
    ) -> SemanticMatch:
        """
        计算字段的语义相似度
        
        这是任务 5.2.2 的第二个功能点：字段名相似度计算。
        
        Args:
            keyword_analysis: 关键词分析结果
            field_info: 字段信息 {'field_name', 'field_type', 'field_comment'}
            table_context: 表上下文信息（可选）
            
        Returns:
            语义匹配结果
        """
        try:
            field_name = field_info.get('field_name', '').lower()
            field_type = field_info.get('field_type', '').lower()
            field_comment = field_info.get('field_comment', '') or ''
            
            similarity_score = 0.0
            match_reasons = []
            matched_keywords = []
            
            # 1. 字段名精确匹配
            for keyword in keyword_analysis.all_keywords:
                if keyword.lower() == field_name:
                    similarity_score += self.weights.exact_match
                    match_reasons.append(f"字段名精确匹配: {keyword}")
                    matched_keywords.append(keyword)
                elif keyword.lower() in field_name:
                    similarity_score += self.weights.partial_match
                    match_reasons.append(f"字段名部分匹配: {keyword}")
                    matched_keywords.append(keyword)
            
            # 2. 字段注释匹配
            if field_comment:
                comment_lower = field_comment.lower()
                for keyword in keyword_analysis.all_keywords:
                    if keyword.lower() in comment_lower:
                        similarity_score += self.weights.comment_match
                        match_reasons.append(f"字段注释匹配: {keyword}")
                        matched_keywords.append(keyword)
            
            # 3. 业务术语到技术字段的智能映射
            mapping_score = self._calculate_business_to_technical_mapping(
                keyword_analysis.business_keywords,
                field_name,
                field_comment
            )
            if mapping_score > 0:
                similarity_score += mapping_score
                match_reasons.append("业务术语到技术字段映射")
            
            # 4. 字段类型语义匹配
            type_score = self._calculate_field_type_match(
                keyword_analysis.all_keywords,
                field_type
            )
            if type_score > 0:
                similarity_score += type_score
                match_reasons.append("字段类型语义匹配")
            
            # 5. 表上下文增强
            if table_context:
                context_score = self._calculate_table_context_boost(
                    keyword_analysis.all_keywords,
                    field_name,
                    table_context
                )
                if context_score > 0:
                    similarity_score += context_score
                    match_reasons.append("表上下文增强")
            
            # 归一化分数
            similarity_score = min(1.0, similarity_score)
            
            return SemanticMatch(
                target_id=field_info.get('id', field_name),
                target_name=field_name,
                target_type='field',
                similarity_score=similarity_score,
                match_reasons=match_reasons,
                matched_keywords=list(set(matched_keywords)),
                business_meaning=field_comment,
                technical_mapping=self._get_technical_mapping(field_name)
            )
            
        except Exception as e:
            logger.error(f"计算字段相似度失败: {str(e)}")
            return SemanticMatch('', '', 'field', 0.0, [], [])
    
    def calculate_business_term_similarity(
        self,
        keyword_analysis: KeywordAnalysis,
        business_term: Dict[str, Any]
    ) -> SemanticMatch:
        """
        计算业务含义的语义相似度
        
        这是任务 5.2.2 的第二个功能点：业务含义相似度计算。
        
        Args:
            keyword_analysis: 关键词分析结果
            business_term: 业务术语信息 {'name', 'description', 'aliases'}
            
        Returns:
            语义匹配结果
        """
        try:
            term_name = business_term.get('name', '').lower()
            term_description = business_term.get('description', '') or ''
            term_aliases = business_term.get('aliases', [])
            
            similarity_score = 0.0
            match_reasons = []
            matched_keywords = []
            
            # 1. 术语名称匹配
            for keyword in keyword_analysis.all_keywords:
                if keyword.lower() == term_name:
                    similarity_score += self.weights.exact_match
                    match_reasons.append(f"术语名称精确匹配: {keyword}")
                    matched_keywords.append(keyword)
                elif keyword.lower() in term_name:
                    similarity_score += self.weights.partial_match
                    match_reasons.append(f"术语名称部分匹配: {keyword}")
                    matched_keywords.append(keyword)
            
            # 2. 术语别名匹配
            for alias in term_aliases:
                alias_lower = alias.lower()
                for keyword in keyword_analysis.all_keywords:
                    if keyword.lower() == alias_lower:
                        similarity_score += self.weights.business_term_match
                        match_reasons.append(f"术语别名匹配: {keyword}")
                        matched_keywords.append(keyword)
            
            # 3. 术语描述匹配
            if term_description:
                desc_lower = term_description.lower()
                for keyword in keyword_analysis.all_keywords:
                    if keyword.lower() in desc_lower:
                        similarity_score += self.weights.comment_match
                        match_reasons.append(f"术语描述匹配: {keyword}")
                        matched_keywords.append(keyword)
            
            # 4. 语义相似度计算
            semantic_score = self._calculate_semantic_similarity(
                keyword_analysis.chinese_terms,
                [term_name] + term_aliases
            )
            if semantic_score > 0.5:
                similarity_score += semantic_score * self.weights.semantic_match
                match_reasons.append("语义相似度匹配")
            
            # 归一化分数
            similarity_score = min(1.0, similarity_score)
            
            return SemanticMatch(
                target_id=business_term.get('id', term_name),
                target_name=term_name,
                target_type='business_term',
                similarity_score=similarity_score,
                match_reasons=match_reasons,
                matched_keywords=list(set(matched_keywords)),
                business_meaning=term_description
            )
            
        except Exception as e:
            logger.error(f"计算业务术语相似度失败: {str(e)}")
            return SemanticMatch('', '', 'business_term', 0.0, [], [])
    
    def calculate_knowledge_term_similarity(
        self,
        keyword_analysis: KeywordAnalysis,
        knowledge_item: Dict[str, Any]
    ) -> SemanticMatch:
        """
        计算知识库术语的语义匹配和权重
        
        这是任务 5.2.2 的第四个功能点：知识库术语语义匹配。
        
        Args:
            keyword_analysis: 关键词分析结果
            knowledge_item: 知识库项目 {'name', 'description', 'type', 'keywords'}
            
        Returns:
            语义匹配结果
        """
        try:
            item_name = knowledge_item.get('name', '').lower()
            item_description = knowledge_item.get('description', '') or ''
            item_type = knowledge_item.get('type', 'TERM')
            item_keywords = knowledge_item.get('keywords', [])
            
            similarity_score = 0.0
            match_reasons = []
            matched_keywords = []
            
            # 1. 知识项名称匹配
            for keyword in keyword_analysis.all_keywords:
                if keyword.lower() == item_name:
                    similarity_score += self.weights.knowledge_term_match
                    match_reasons.append(f"知识项名称精确匹配: {keyword}")
                    matched_keywords.append(keyword)
                elif keyword.lower() in item_name:
                    similarity_score += self.weights.knowledge_term_match * 0.7
                    match_reasons.append(f"知识项名称部分匹配: {keyword}")
                    matched_keywords.append(keyword)
            
            # 2. 知识项关键词匹配
            for item_keyword in item_keywords:
                keyword_lower = item_keyword.lower()
                for user_keyword in keyword_analysis.all_keywords:
                    if user_keyword.lower() == keyword_lower:
                        similarity_score += self.weights.knowledge_term_match
                        match_reasons.append(f"知识项关键词匹配: {user_keyword}")
                        matched_keywords.append(user_keyword)
            
            # 3. 知识项描述匹配
            if item_description:
                desc_lower = item_description.lower()
                for keyword in keyword_analysis.all_keywords:
                    if keyword.lower() in desc_lower:
                        similarity_score += self.weights.comment_match
                        match_reasons.append(f"知识项描述匹配: {keyword}")
                        matched_keywords.append(keyword)
            
            # 4. 根据知识项类型调整权重
            type_weight = self._get_knowledge_type_weight(item_type)
            similarity_score *= type_weight
            
            # 5. 领域相关性增强
            domain_boost = self._calculate_domain_relevance(
                keyword_analysis.domain_keywords,
                item_name,
                item_description
            )
            if domain_boost > 0:
                similarity_score += domain_boost
                match_reasons.append("领域相关性增强")
            
            # 归一化分数
            similarity_score = min(1.0, similarity_score)
            
            return SemanticMatch(
                target_id=knowledge_item.get('id', item_name),
                target_name=item_name,
                target_type='knowledge_term',
                similarity_score=similarity_score,
                match_reasons=match_reasons,
                matched_keywords=list(set(matched_keywords)),
                business_meaning=item_description
            )
            
        except Exception as e:
            logger.error(f"计算知识库术语相似度失败: {str(e)}")
            return SemanticMatch('', '', 'knowledge_term', 0.0, [], [])
    
    def rank_semantic_matches(
        self,
        matches: List[SemanticMatch],
        min_score: float = 0.3,
        max_results: int = 10
    ) -> List[SemanticMatch]:
        """
        对语义匹配结果进行排序和过滤
        
        Args:
            matches: 语义匹配结果列表
            min_score: 最小相似度阈值
            max_results: 最大返回结果数
            
        Returns:
            排序后的匹配结果
        """
        try:
            # 过滤低分结果
            filtered_matches = [match for match in matches if match.similarity_score >= min_score]
            
            # 按相似度排序
            filtered_matches.sort(key=lambda x: x.similarity_score, reverse=True)
            
            # 限制结果数量
            return filtered_matches[:max_results]
            
        except Exception as e:
            logger.error(f"排序语义匹配结果失败: {str(e)}")
            return []
    
    # 私有辅助方法
    
    def _extract_chinese_terms(self, text: str) -> List[str]:
        """提取中文词汇"""
        try:
            # 使用jieba分词
            words = jieba.cut(text, cut_all=False)
            chinese_terms = []
            
            for word in words:
                # 过滤纯中文词汇
                if re.match(r'^[\u4e00-\u9fff]+$', word) and len(word) >= 2:
                    chinese_terms.append(word)
            
            return chinese_terms
        except Exception as e:
            logger.error(f"中文词汇提取失败: {str(e)}")
            return []
    
    def _extract_english_terms(self, text: str) -> List[str]:
        """提取英文词汇"""
        try:
            # 提取英文单词
            english_words = re.findall(r'[a-zA-Z]+', text.lower())
            # 过滤长度
            return [word for word in english_words if len(word) >= 2]
        except Exception as e:
            logger.error(f"英文词汇提取失败: {str(e)}")
            return []
    
    def _identify_business_keywords(self, terms: List[str]) -> List[str]:
        """识别业务关键词"""
        business_keywords = []
        
        for term in terms:
            term_lower = term.lower()
            # 检查是否在业务术语映射中
            if term in self.business_term_mappings:
                business_keywords.append(term)
            # 检查是否是业务术语的映射值
            for business_term, mappings in self.business_term_mappings.items():
                if term_lower in [m.lower() for m in mappings]:
                    business_keywords.append(term)
        
        return list(set(business_keywords))
    
    def _identify_technical_keywords(self, terms: List[str]) -> List[str]:
        """识别技术关键词"""
        technical_keywords = []
        
        for term in terms:
            term_lower = term.lower()
            # 检查是否在技术术语映射中
            if term_lower in self.technical_term_mappings:
                technical_keywords.append(term)
            # 检查是否是技术术语的映射值
            for tech_term, mappings in self.technical_term_mappings.items():
                if term in mappings:
                    technical_keywords.append(term)
        
        return list(set(technical_keywords))
    
    def _identify_domain_keywords(self, text: str) -> List[str]:
        """识别领域关键词"""
        domain_patterns = {
            '财务': ['收入', '支出', '利润', '成本', '预算', '财务', '会计'],
            '销售': ['销售', '客户', '订单', '产品', '市场', '营销'],
            '人力资源': ['员工', '人事', '薪资', '招聘', '培训', '绩效'],
            '库存': ['库存', '仓库', '入库', '出库', '盘点', '物料'],
            '生产': ['生产', '制造', '工艺', '质量', '设备', '产能']
        }
        
        domain_keywords = []
        text_lower = text.lower()
        
        for domain, keywords in domain_patterns.items():
            for keyword in keywords:
                if keyword in text_lower:
                    domain_keywords.append(domain)
                    break
        
        return domain_keywords
    
    def _calculate_business_term_match(
        self,
        business_keywords: List[str],
        table_name: str,
        table_comment: str
    ) -> float:
        """计算业务术语匹配分数"""
        score = 0.0
        
        for keyword in business_keywords:
            # 检查业务术语映射
            if keyword in self.business_term_mappings:
                mappings = self.business_term_mappings[keyword]
                for mapping in mappings:
                    if mapping.lower() in table_name.lower():
                        score += self.weights.business_term_match
                    if mapping.lower() in table_comment.lower():
                        score += self.weights.business_term_match * 0.5
        
        return score
    
    def _calculate_field_indirect_match(
        self,
        keywords: Set[str],
        fields: List[Dict[str, Any]]
    ) -> float:
        """计算字段间接匹配分数"""
        score = 0.0
        
        for field in fields:
            field_name = field.get('field_name', '').lower()
            for keyword in keywords:
                if keyword.lower() in field_name:
                    score += 0.1  # 间接匹配权重较低
        
        return score
    
    def _calculate_business_to_technical_mapping(
        self,
        business_keywords: List[str],
        field_name: str,
        field_comment: str
    ) -> float:
        """
        计算业务术语到技术字段的智能映射
        
        这是任务 5.2.2 的第三个功能点的核心实现。
        """
        score = 0.0
        
        for keyword in business_keywords:
            # 业务术语到技术字段的映射
            if keyword in self.business_term_mappings:
                technical_terms = self.business_term_mappings[keyword]
                for tech_term in technical_terms:
                    if tech_term.lower() in field_name.lower():
                        score += self.weights.business_term_match
                    if tech_term.lower() in field_comment.lower():
                        score += self.weights.business_term_match * 0.5
            
            # 反向映射：技术字段到业务术语
            field_lower = field_name.lower()
            for tech_term, business_terms in self.technical_term_mappings.items():
                if tech_term in field_lower:
                    if keyword in business_terms:
                        score += self.weights.business_term_match
        
        return score
    
    def _calculate_field_type_match(
        self,
        keywords: Set[str],
        field_type: str
    ) -> float:
        """计算字段类型语义匹配"""
        score = 0.0
        
        # 数据类型语义映射
        type_mappings = {
            'int': ['数量', '计数', '编号', 'count', 'number', 'id'],
            'varchar': ['名称', '描述', '文本', 'name', 'text', 'description'],
            'decimal': ['金额', '价格', '费用', 'amount', 'price', 'cost'],
            'datetime': ['时间', '日期', 'time', 'date'],
            'text': ['描述', '备注', '说明', 'description', 'comment', 'remark']
        }
        
        field_type_lower = field_type.lower()
        for type_key, type_keywords in type_mappings.items():
            if type_key in field_type_lower:
                for keyword in keywords:
                    if keyword.lower() in [tk.lower() for tk in type_keywords]:
                        score += self.weights.field_type_match
        
        return score
    
    def _calculate_table_context_boost(
        self,
        keywords: Set[str],
        field_name: str,
        table_context: Dict[str, Any]
    ) -> float:
        """计算表上下文增强分数"""
        score = 0.0
        
        table_name = table_context.get('table_name', '').lower()
        
        # 如果字段名包含表名相关信息，增加分数
        for keyword in keywords:
            if keyword.lower() in table_name and keyword.lower() in field_name.lower():
                score += 0.2
        
        return score
    
    def _get_technical_mapping(self, field_name: str) -> Optional[str]:
        """获取技术字段的业务映射"""
        field_lower = field_name.lower()
        
        for tech_term, business_terms in self.technical_term_mappings.items():
            if tech_term in field_lower:
                return ', '.join(business_terms)
        
        return None
    
    def _calculate_semantic_similarity(
        self,
        terms1: List[str],
        terms2: List[str]
    ) -> float:
        """计算语义相似度（简化版）"""
        if not terms1 or not terms2:
            return 0.0
        
        # 简单的Jaccard相似度
        set1 = set(term.lower() for term in terms1)
        set2 = set(term.lower() for term in terms2)
        
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        
        return intersection / union if union > 0 else 0.0
    
    def _get_knowledge_type_weight(self, knowledge_type: str) -> float:
        """获取知识类型权重"""
        type_weights = {
            'TERM': 1.0,
            'LOGIC': 0.8,
            'EVENT': 0.6
        }
        return type_weights.get(knowledge_type, 0.5)
    
    def _calculate_domain_relevance(
        self,
        domain_keywords: List[str],
        item_name: str,
        item_description: str
    ) -> float:
        """计算领域相关性"""
        score = 0.0
        
        combined_text = (item_name + ' ' + item_description).lower()
        
        for domain in domain_keywords:
            if domain.lower() in combined_text:
                score += 0.1
        
        return score
    
    def get_similarity_statistics(self) -> Dict[str, Any]:
        """获取相似度计算统计信息"""
        return {
            'business_term_mappings_count': len(self.business_term_mappings),
            'technical_term_mappings_count': len(self.technical_term_mappings),
            'stop_words_count': len(self.stop_words),
            'weights': {
                'exact_match': self.weights.exact_match,
                'partial_match': self.weights.partial_match,
                'semantic_match': self.weights.semantic_match,
                'business_term_match': self.weights.business_term_match,
                'knowledge_term_match': self.weights.knowledge_term_match,
                'field_type_match': self.weights.field_type_match,
                'comment_match': self.weights.comment_match
            }
        }