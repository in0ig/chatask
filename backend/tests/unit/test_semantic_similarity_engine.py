"""
语义相似度计算引擎单元测试

任务 5.2.2 的测试实现
"""

import pytest
from unittest.mock import Mock, patch
from src.services.semantic_similarity_engine import (
    SemanticSimilarityEngine,
    KeywordAnalysis,
    SemanticMatch,
    SimilarityWeights
)


class TestSemanticSimilarityEngine:
    """语义相似度计算引擎测试"""
    
    def setup_method(self):
        """测试前置设置"""
        self.engine = SemanticSimilarityEngine()
    
    def test_analyze_user_question_chinese(self):
        """测试中文问题分析"""
        question = "查询用户订单的销售金额和数量统计"
        
        result = self.engine.analyze_user_question(question)
        
        assert isinstance(result, KeywordAnalysis)
        assert len(result.chinese_terms) > 0
        assert len(result.all_keywords) > 0
        assert '用户' in result.chinese_terms or '用户' in result.business_keywords
        assert '订单' in result.chinese_terms or '订单' in result.business_keywords
    
    def test_analyze_user_question_english(self):
        """测试英文问题分析"""
        question = "Show me user order sales amount and quantity statistics"
        
        result = self.engine.analyze_user_question(question)
        
        assert isinstance(result, KeywordAnalysis)
        assert len(result.english_terms) > 0
        assert 'user' in result.english_terms
        assert 'order' in result.english_terms
        assert 'sales' in result.english_terms
    
    def test_analyze_user_question_mixed(self):
        """测试中英文混合问题分析"""
        question = "查询user表中的order数据，统计sales金额"
        
        result = self.engine.analyze_user_question(question)
        
        assert isinstance(result, KeywordAnalysis)
        assert len(result.chinese_terms) > 0
        assert len(result.english_terms) > 0
        assert len(result.all_keywords) > 0
    
    def test_calculate_table_similarity_exact_match(self):
        """测试表名精确匹配"""
        keyword_analysis = KeywordAnalysis(
            chinese_terms=['用户', '订单'],
            english_terms=['user', 'order'],
            business_keywords=['用户', '订单'],
            technical_keywords=['user'],
            domain_keywords=['销售'],
            all_keywords={'用户', '订单', 'user', 'order', '销售'}
        )
        
        table_info = {
            'id': 'table_1',
            'table_name': 'user_order',
            'table_comment': '用户订单表',
            'fields': []
        }
        
        result = self.engine.calculate_table_similarity(keyword_analysis, table_info)
        
        assert isinstance(result, SemanticMatch)
        assert result.target_type == 'table'
        assert result.similarity_score > 0.5
        assert len(result.match_reasons) > 0
        assert len(result.matched_keywords) > 0
    
    def test_calculate_table_similarity_comment_match(self):
        """测试表注释匹配"""
        keyword_analysis = KeywordAnalysis(
            chinese_terms=['销售'],
            english_terms=['sales'],
            business_keywords=['销售'],
            technical_keywords=[],
            domain_keywords=['销售'],
            all_keywords={'销售', 'sales'}
        )
        
        table_info = {
            'id': 'table_2',
            'table_name': 't_data',
            'table_comment': '销售数据统计表',
            'fields': []
        }
        
        result = self.engine.calculate_table_similarity(keyword_analysis, table_info)
        
        assert isinstance(result, SemanticMatch)
        assert result.similarity_score > 0.0
        assert any('注释匹配' in reason for reason in result.match_reasons)
    
    def test_calculate_field_similarity_exact_match(self):
        """测试字段名精确匹配"""
        keyword_analysis = KeywordAnalysis(
            chinese_terms=['用户'],
            english_terms=['user', 'name'],
            business_keywords=['用户'],
            technical_keywords=['name'],
            domain_keywords=[],
            all_keywords={'用户', 'user', 'name'}
        )
        
        field_info = {
            'id': 'field_1',
            'field_name': 'user_name',
            'field_type': 'varchar(100)',
            'field_comment': '用户姓名'
        }
        
        result = self.engine.calculate_field_similarity(keyword_analysis, field_info)
        
        assert isinstance(result, SemanticMatch)
        assert result.target_type == 'field'
        assert result.similarity_score > 0.5
        assert len(result.match_reasons) > 0
    
    def test_calculate_field_similarity_business_mapping(self):
        """测试业务术语到技术字段的映射"""
        keyword_analysis = KeywordAnalysis(
            chinese_terms=['用户', '名称'],
            english_terms=[],
            business_keywords=['用户'],
            technical_keywords=[],
            domain_keywords=[],
            all_keywords={'用户', '名称'}
        )
        
        field_info = {
            'id': 'field_2',
            'field_name': 'customer_name',
            'field_type': 'varchar(50)',
            'field_comment': '客户姓名'
        }
        
        result = self.engine.calculate_field_similarity(keyword_analysis, field_info)
        
        assert isinstance(result, SemanticMatch)
        assert result.similarity_score > 0.0
        # 应该有业务术语映射匹配
        assert any('映射' in reason for reason in result.match_reasons)
    
    def test_calculate_field_similarity_type_match(self):
        """测试字段类型语义匹配"""
        keyword_analysis = KeywordAnalysis(
            chinese_terms=['金额', '价格'],
            english_terms=['amount'],
            business_keywords=['金额'],
            technical_keywords=[],
            domain_keywords=[],
            all_keywords={'金额', '价格', 'amount'}
        )
        
        field_info = {
            'id': 'field_3',
            'field_name': 'total_amount',
            'field_type': 'decimal(10,2)',
            'field_comment': '总金额'
        }
        
        result = self.engine.calculate_field_similarity(keyword_analysis, field_info)
        
        assert isinstance(result, SemanticMatch)
        assert result.similarity_score > 0.5
        # 应该有字段类型匹配
        assert any('类型' in reason for reason in result.match_reasons)
    
    def test_calculate_business_term_similarity(self):
        """测试业务术语相似度计算"""
        keyword_analysis = KeywordAnalysis(
            chinese_terms=['客户', '用户'],
            english_terms=['customer'],
            business_keywords=['客户'],
            technical_keywords=[],
            domain_keywords=[],
            all_keywords={'客户', '用户', 'customer'}
        )
        
        business_term = {
            'id': 'term_1',
            'name': '客户',
            'description': '购买产品或服务的个人或组织',
            'aliases': ['用户', '顾客']
        }
        
        result = self.engine.calculate_business_term_similarity(keyword_analysis, business_term)
        
        assert isinstance(result, SemanticMatch)
        assert result.target_type == 'business_term'
        assert result.similarity_score > 0.5
        assert len(result.match_reasons) > 0
    
    def test_calculate_knowledge_term_similarity(self):
        """测试知识库术语相似度计算"""
        keyword_analysis = KeywordAnalysis(
            chinese_terms=['销售', '业绩'],
            english_terms=['sales'],
            business_keywords=['销售'],
            technical_keywords=[],
            domain_keywords=['销售'],
            all_keywords={'销售', '业绩', 'sales'}
        )
        
        knowledge_item = {
            'id': 'knowledge_1',
            'name': '销售业绩',
            'description': '销售人员在特定时期内的销售成果',
            'type': 'TERM',
            'keywords': ['销售', '业绩', '成果']
        }
        
        result = self.engine.calculate_knowledge_term_similarity(keyword_analysis, knowledge_item)
        
        assert isinstance(result, SemanticMatch)
        assert result.target_type == 'knowledge_term'
        assert result.similarity_score > 0.5
        assert len(result.match_reasons) > 0
    
    def test_rank_semantic_matches(self):
        """测试语义匹配结果排序"""
        matches = [
            SemanticMatch('1', 'low_match', 'table', 0.2, [], []),
            SemanticMatch('2', 'high_match', 'table', 0.8, [], []),
            SemanticMatch('3', 'medium_match', 'table', 0.5, [], []),
            SemanticMatch('4', 'very_low_match', 'table', 0.1, [], [])
        ]
        
        ranked = self.engine.rank_semantic_matches(matches, min_score=0.3, max_results=5)
        
        assert len(ranked) == 2  # 只有2个超过0.3阈值
        assert ranked[0].similarity_score == 0.8  # 最高分在前
        assert ranked[1].similarity_score == 0.5
    
    def test_extract_chinese_terms(self):
        """测试中文词汇提取"""
        text = "查询用户订单数据统计"
        
        terms = self.engine._extract_chinese_terms(text)
        
        assert isinstance(terms, list)
        assert len(terms) > 0
        # 应该包含一些中文词汇
        assert any(len(term) >= 2 for term in terms)
    
    def test_extract_english_terms(self):
        """测试英文词汇提取"""
        text = "Show user order data statistics"
        
        terms = self.engine._extract_english_terms(text)
        
        assert isinstance(terms, list)
        assert 'user' in terms
        assert 'order' in terms
        assert 'data' in terms
    
    def test_identify_business_keywords(self):
        """测试业务关键词识别"""
        terms = ['用户', '订单', '销售', '价格', 'user', 'order']
        
        business_keywords = self.engine._identify_business_keywords(terms)
        
        assert isinstance(business_keywords, list)
        assert '用户' in business_keywords
        assert '订单' in business_keywords
        assert '销售' in business_keywords
    
    def test_identify_technical_keywords(self):
        """测试技术关键词识别"""
        terms = ['id', 'name', 'type', 'count', '标识', '名称']
        
        technical_keywords = self.engine._identify_technical_keywords(terms)
        
        assert isinstance(technical_keywords, list)
        assert 'id' in technical_keywords
        assert 'name' in technical_keywords
        assert '名称' in technical_keywords
    
    def test_identify_domain_keywords(self):
        """测试领域关键词识别"""
        text = "查询销售部门的财务收入数据"
        
        domain_keywords = self.engine._identify_domain_keywords(text)
        
        assert isinstance(domain_keywords, list)
        assert '销售' in domain_keywords
        assert '财务' in domain_keywords
    
    def test_calculate_business_term_match(self):
        """测试业务术语匹配计算"""
        business_keywords = ['用户', '订单']
        table_name = 'user_order_table'
        table_comment = '用户订单数据表'
        
        score = self.engine._calculate_business_term_match(
            business_keywords, table_name, table_comment
        )
        
        assert isinstance(score, float)
        assert score > 0.0
    
    def test_calculate_business_to_technical_mapping(self):
        """测试业务术语到技术字段映射"""
        business_keywords = ['用户', '名称']
        field_name = 'customer_name'
        field_comment = '客户姓名'
        
        score = self.engine._calculate_business_to_technical_mapping(
            business_keywords, field_name, field_comment
        )
        
        assert isinstance(score, float)
        assert score > 0.0
    
    def test_calculate_field_type_match(self):
        """测试字段类型匹配"""
        keywords = {'金额', '价格', 'amount'}
        field_type = 'decimal(10,2)'
        
        score = self.engine._calculate_field_type_match(keywords, field_type)
        
        assert isinstance(score, float)
        assert score > 0.0
    
    def test_get_technical_mapping(self):
        """测试获取技术映射"""
        field_name = 'user_name'
        
        mapping = self.engine._get_technical_mapping(field_name)
        
        assert mapping is not None
        assert isinstance(mapping, str)
        assert '名称' in mapping or '姓名' in mapping
    
    def test_calculate_semantic_similarity(self):
        """测试语义相似度计算"""
        terms1 = ['用户', '订单', '销售']
        terms2 = ['客户', '订单', '营销']
        
        similarity = self.engine._calculate_semantic_similarity(terms1, terms2)
        
        assert isinstance(similarity, float)
        assert 0.0 <= similarity <= 1.0
        assert similarity > 0.0  # 应该有一些相似性
    
    def test_get_knowledge_type_weight(self):
        """测试知识类型权重"""
        term_weight = self.engine._get_knowledge_type_weight('TERM')
        logic_weight = self.engine._get_knowledge_type_weight('LOGIC')
        event_weight = self.engine._get_knowledge_type_weight('EVENT')
        
        assert term_weight == 1.0
        assert logic_weight == 0.8
        assert event_weight == 0.6
    
    def test_calculate_domain_relevance(self):
        """测试领域相关性计算"""
        domain_keywords = ['销售', '财务']
        item_name = '销售业绩'
        item_description = '销售部门的业绩统计'
        
        relevance = self.engine._calculate_domain_relevance(
            domain_keywords, item_name, item_description
        )
        
        assert isinstance(relevance, float)
        assert relevance > 0.0
    
    def test_get_similarity_statistics(self):
        """测试获取统计信息"""
        stats = self.engine.get_similarity_statistics()
        
        assert isinstance(stats, dict)
        assert 'business_term_mappings_count' in stats
        assert 'technical_term_mappings_count' in stats
        assert 'stop_words_count' in stats
        assert 'weights' in stats
        
        # 验证权重信息
        weights = stats['weights']
        assert 'exact_match' in weights
        assert 'partial_match' in weights
        assert 'semantic_match' in weights
    
    def test_empty_input_handling(self):
        """测试空输入处理"""
        # 空问题
        result = self.engine.analyze_user_question("")
        assert isinstance(result, KeywordAnalysis)
        assert len(result.all_keywords) == 0
        
        # 空表信息
        keyword_analysis = KeywordAnalysis([], [], [], [], [], set())
        table_result = self.engine.calculate_table_similarity(keyword_analysis, {})
        assert isinstance(table_result, SemanticMatch)
        assert table_result.similarity_score == 0.0
    
    def test_special_characters_handling(self):
        """测试特殊字符处理"""
        question = "查询用户@#$%订单！！！数据？？？"
        
        result = self.engine.analyze_user_question(question)
        
        assert isinstance(result, KeywordAnalysis)
        # 应该能正确提取中文词汇，忽略特殊字符
        assert len(result.chinese_terms) > 0
    
    def test_similarity_weights_configuration(self):
        """测试相似度权重配置"""
        weights = self.engine.weights
        
        assert isinstance(weights, SimilarityWeights)
        assert weights.exact_match == 1.0
        assert weights.partial_match == 0.7
        assert weights.semantic_match == 0.6
        assert weights.business_term_match == 0.8
        assert weights.knowledge_term_match == 0.7
        assert weights.field_type_match == 0.5
        assert weights.comment_match == 0.4
    
    def test_comprehensive_similarity_calculation(self):
        """测试综合相似度计算"""
        question = "查询用户订单的销售金额统计"
        keyword_analysis = self.engine.analyze_user_question(question)
        
        # 测试表相似度
        table_info = {
            'id': 'table_1',
            'table_name': 'user_sales_order',
            'table_comment': '用户销售订单表',
            'fields': [
                {'field_name': 'user_id', 'field_comment': '用户ID'},
                {'field_name': 'order_amount', 'field_comment': '订单金额'}
            ]
        }
        
        table_match = self.engine.calculate_table_similarity(keyword_analysis, table_info)
        
        # 测试字段相似度
        field_info = {
            'field_name': 'sales_amount',
            'field_type': 'decimal(10,2)',
            'field_comment': '销售金额'
        }
        
        field_match = self.engine.calculate_field_similarity(keyword_analysis, field_info)
        
        # 验证结果
        assert table_match.similarity_score > 0.5
        assert field_match.similarity_score > 0.5
        assert len(table_match.matched_keywords) > 0
        assert len(field_match.matched_keywords) > 0


class TestSemanticSimilarityEngineEdgeCases:
    """语义相似度计算引擎边界情况测试"""
    
    def setup_method(self):
        """测试前置设置"""
        self.engine = SemanticSimilarityEngine()
    
    def test_very_long_question(self):
        """测试超长问题处理"""
        long_question = "查询" + "用户订单销售数据统计分析报告" * 100
        
        result = self.engine.analyze_user_question(long_question)
        
        assert isinstance(result, KeywordAnalysis)
        # 应该能正常处理，不会崩溃
        assert len(result.all_keywords) > 0
    
    def test_only_special_characters(self):
        """测试纯特殊字符输入"""
        question = "!@#$%^&*()_+-=[]{}|;':\",./<>?"
        
        result = self.engine.analyze_user_question(question)
        
        assert isinstance(result, KeywordAnalysis)
        assert len(result.all_keywords) == 0
    
    def test_mixed_language_complex(self):
        """测试复杂混合语言"""
        question = "查询user表中的订单order数据，统计sales金额amount和数量count"
        
        result = self.engine.analyze_user_question(question)
        
        assert isinstance(result, KeywordAnalysis)
        assert len(result.chinese_terms) > 0
        assert len(result.english_terms) > 0
        assert 'user' in result.english_terms
        assert 'order' in result.english_terms
    
    def test_numeric_values_handling(self):
        """测试数值处理"""
        question = "查询2023年销售金额大于10000的订单数据"
        
        result = self.engine.analyze_user_question(question)
        
        assert isinstance(result, KeywordAnalysis)
        # 数值应该被过滤掉，但其他词汇应该被提取
        assert len(result.chinese_terms) > 0
    
    def test_performance_with_large_dataset(self):
        """测试大数据集性能"""
        keyword_analysis = KeywordAnalysis(
            chinese_terms=['用户'] * 100,
            english_terms=['user'] * 100,
            business_keywords=['用户'] * 50,
            technical_keywords=['user'] * 50,
            domain_keywords=['销售'] * 20,
            all_keywords=set(['用户', 'user', '销售'])
        )
        
        # 大量表信息
        tables = []
        for i in range(100):
            tables.append({
                'id': f'table_{i}',
                'table_name': f'test_table_{i}',
                'table_comment': f'测试表{i}',
                'fields': []
            })
        
        # 计算相似度应该能在合理时间内完成
        matches = []
        for table in tables:
            match = self.engine.calculate_table_similarity(keyword_analysis, table)
            matches.append(match)
        
        assert len(matches) == 100
        # 所有匹配都应该是有效的
        assert all(isinstance(match, SemanticMatch) for match in matches)