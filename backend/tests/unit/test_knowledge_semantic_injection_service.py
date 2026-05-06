"""
知识库语义注入服务测试

测试知识库语义注入服务的所有核心功能，包括业务术语匹配、业务逻辑增强、
事件知识处理、分层注入策略等。
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from sqlalchemy.orm import Session

from src.services.knowledge_semantic_injection import (
    KnowledgeSemanticInjectionService,
    KnowledgeType,
    KnowledgeScope,
    TermKnowledge,
    LogicKnowledge,
    EventKnowledge,
    KnowledgeSemanticInfo,
    SemanticInjectionResult
)
from src.models.knowledge_base_model import KnowledgeBase
from src.models.knowledge_item_model import KnowledgeItem


class TestKnowledgeSemanticInjectionService:
    """知识库语义注入服务测试类"""
    
    @pytest.fixture
    def mock_db_session(self):
        """模拟数据库会话"""
        return Mock(spec=Session)
    
    @pytest.fixture
    def service(self, mock_db_session):
        """创建服务实例"""
        return KnowledgeSemanticInjectionService(mock_db_session)
    
    @pytest.fixture
    def sample_knowledge_base(self):
        """示例知识库"""
        kb = Mock(spec=KnowledgeBase)
        kb.id = "kb_001"
        kb.name = "测试知识库"
        kb.type = "TERM"
        kb.scope = "GLOBAL"
        kb.status = True
        kb.table_id = None
        return kb
    
    @pytest.fixture
    def sample_term_item(self, sample_knowledge_base):
        """示例业务术语知识项"""
        item = Mock(spec=KnowledgeItem)
        item.id = "item_001"
        item.knowledge_base_id = "kb_001"
        item.type = "TERM"
        item.name = "客户"
        item.explanation = "购买产品或服务的个人或企业"
        item.example_question = "有多少客户购买了产品？"
        item.event_date_start = None
        item.event_date_end = None
        item.knowledge_base = sample_knowledge_base
        return item
    
    @pytest.fixture
    def sample_logic_item(self, sample_knowledge_base):
        """示例业务逻辑知识项"""
        item = Mock(spec=KnowledgeItem)
        item.id = "item_002"
        item.knowledge_base_id = "kb_001"
        item.type = "LOGIC"
        item.name = None
        item.explanation = "VIP客户是指消费金额超过10000元的客户"
        item.example_question = "哪些是VIP客户？"
        item.event_date_start = None
        item.event_date_end = None
        item.knowledge_base = sample_knowledge_base
        return item
    
    @pytest.fixture
    def sample_event_item(self, sample_knowledge_base):
        """示例事件知识项"""
        item = Mock(spec=KnowledgeItem)
        item.id = "item_003"
        item.knowledge_base_id = "kb_001"
        item.type = "EVENT"
        item.name = None
        item.explanation = "双十一促销活动，全场商品8折优惠"
        item.example_question = None
        item.event_date_start = datetime(2024, 11, 11)
        item.event_date_end = datetime(2024, 11, 11, 23, 59, 59)
        item.knowledge_base = sample_knowledge_base
        return item
    
    def test_extract_keywords(self, service):
        """测试关键词提取功能"""
        # 测试中文文本关键词提取
        text = "查询客户的购买记录和订单信息"
        keywords = service._extract_keywords(text)
        
        assert "客" in keywords
        assert "户" in keywords
        assert "购" in keywords
        assert "买" in keywords
        assert "记" in keywords
        assert "录" in keywords
        assert "订" in keywords
        assert "单" in keywords
        assert "信" in keywords
        assert "息" in keywords
        assert "的" not in keywords  # 停用词应被过滤
        assert "和" not in keywords  # 停用词应被过滤
    
    def test_extract_keywords_english(self, service):
        """测试英文关键词提取"""
        text = "Show me customer purchase history and order details"
        keywords = service._extract_keywords(text)
        
        assert "show" in keywords
        assert "customer" in keywords
        assert "purchase" in keywords
        assert "history" in keywords
        assert "order" in keywords
        assert "details" in keywords
    
    def test_extract_keywords_mixed(self, service):
        """测试中英文混合关键词提取"""
        text = "查询customer的order信息"
        keywords = service._extract_keywords(text)
        
        assert "查" in keywords
        assert "询" in keywords
        assert "customer" in keywords
        assert "order" in keywords
        assert "信" in keywords
        assert "息" in keywords
    
    def test_calculate_term_relevance(self, service, sample_term_item):
        """测试业务术语相关性计算"""
        # 确保Mock对象的属性能被正确访问
        sample_term_item.name = "客户"
        sample_term_item.explanation = "购买产品或服务的个人或企业"
        sample_term_item.example_question = "有多少客户购买了产品？"
        
        keywords = {"客", "户", "购", "买", "产", "品"}
        
        score = service._calculate_term_relevance(sample_term_item, keywords)
        
        # 验证计算逻辑正确，分数应该大于0
        assert score > 0
        # 验证包含名称匹配、解释匹配和示例问题匹配的分数
        assert score >= 4.0  # 至少包含名称匹配的分数
    
    def test_calculate_logic_relevance(self, service, sample_logic_item):
        """测试业务逻辑相关性计算"""
        # 确保Mock对象的属性能被正确访问
        sample_logic_item.explanation = "VIP客户是指消费金额超过10000元的客户"
        sample_logic_item.example_question = "哪些是VIP客户？"
        
        keywords = {"vip", "客", "户", "消", "费", "规", "则"}
        
        score = service._calculate_logic_relevance(sample_logic_item, keywords)
        
        # 验证计算逻辑正确，分数应该大于0
        assert score > 0
        # 验证包含解释匹配、示例问题匹配和业务逻辑关键词匹配的分数
        assert score >= 2.0  # 至少包含业务逻辑关键词匹配的分数
    
    def test_calculate_event_relevance(self, service, sample_event_item):
        """测试事件知识相关性计算"""
        # 确保Mock对象的属性能被正确访问
        sample_event_item.explanation = "双十一促销活动，全场商品8折优惠"
        
        keywords = {"促", "销", "活", "动", "优", "惠", "事", "件"}
        
        score = service._calculate_event_relevance(sample_event_item, keywords)
        
        # 验证计算逻辑正确，分数应该大于0
        assert score > 0
        # 验证包含解释匹配和事件关键词匹配的分数
        assert score >= 2.0  # 至少包含事件关键词匹配的分数
    
    def test_is_event_active_current(self, service, sample_event_item):
        """测试事件活跃状态判断 - 当前时间在事件期间"""
        # 设置事件时间为当前时间前后
        current_time = datetime.now()
        sample_event_item.event_date_start = current_time - timedelta(hours=1)
        sample_event_item.event_date_end = current_time + timedelta(hours=1)
        
        is_active = service._is_event_active(sample_event_item, current_time)
        assert is_active is True
    
    def test_is_event_active_past(self, service, sample_event_item):
        """测试事件活跃状态判断 - 事件已结束"""
        current_time = datetime.now()
        sample_event_item.event_date_start = current_time - timedelta(days=2)
        sample_event_item.event_date_end = current_time - timedelta(days=1)
        
        is_active = service._is_event_active(sample_event_item, current_time)
        assert is_active is False
    
    def test_is_event_active_future(self, service, sample_event_item):
        """测试事件活跃状态判断 - 事件未开始"""
        current_time = datetime.now()
        sample_event_item.event_date_start = current_time + timedelta(days=1)
        sample_event_item.event_date_end = current_time + timedelta(days=2)
        
        is_active = service._is_event_active(sample_event_item, current_time)
        assert is_active is False
    
    def test_is_event_active_no_end_date(self, service, sample_event_item):
        """测试事件活跃状态判断 - 无结束时间"""
        current_time = datetime.now()
        sample_event_item.event_date_start = current_time - timedelta(hours=1)
        sample_event_item.event_date_end = None
        
        is_active = service._is_event_active(sample_event_item, current_time)
        assert is_active is True
    
    def test_is_event_active_no_start_date(self, service, sample_event_item):
        """测试事件活跃状态判断 - 无开始时间"""
        current_time = datetime.now()
        sample_event_item.event_date_start = None
        sample_event_item.event_date_end = current_time + timedelta(hours=1)
        
        is_active = service._is_event_active(sample_event_item, current_time)
        assert is_active is False
    
    def test_match_terms_success(self, service, sample_term_item):
        """测试业务术语匹配成功"""
        keywords = {"客", "户", "购", "买"}  # 使用单字符关键词匹配中文分词逻辑
        
        # 确保Mock对象的属性能被正确访问
        sample_term_item.name = "客户"
        sample_term_item.explanation = "购买产品或服务的个人或企业"
        sample_term_item.example_question = "有多少客户购买了产品？"
        
        # 模拟数据库查询
        mock_query = Mock()
        mock_query.join.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = [sample_term_item]
        service.db.query.return_value = mock_query
        
        terms = service._match_terms(keywords, None, True, 10)
        
        assert len(terms) == 1
        assert terms[0].id == "item_001"
        assert terms[0].name == "客户"
        assert terms[0].relevance_score > 0
    
    def test_match_logics_success(self, service, sample_logic_item):
        """测试业务逻辑匹配成功"""
        keywords = {"vip", "客户", "规则"}
        
        # 模拟数据库查询
        mock_query = Mock()
        mock_query.join.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = [sample_logic_item]
        service.db.query.return_value = mock_query
        
        logics = service._match_logics(keywords, None, True, 5)
        
        assert len(logics) == 1
        assert logics[0].id == "item_002"
        assert logics[0].relevance_score > 0
    
    def test_match_events_success(self, service, sample_event_item):
        """测试事件知识匹配成功"""
        keywords = {"促", "销", "活", "动"}  # 使用单字符关键词匹配中文分词逻辑
        
        # 确保Mock对象的属性能被正确访问
        sample_event_item.explanation = "双十一促销活动，全场商品8折优惠"
        
        # 模拟数据库查询
        mock_query = Mock()
        mock_query.join.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = [sample_event_item]
        service.db.query.return_value = mock_query
        
        events = service._match_events(keywords, None, True, 3)
        
        assert len(events) == 1
        assert events[0].id == "item_003"
        assert events[0].relevance_score > 0
    
    def test_match_terms_with_table_filter(self, service, sample_term_item):
        """测试带表过滤的业务术语匹配"""
        keywords = {"客户"}
        table_ids = ["table_001"]
        
        # 模拟数据库查询
        mock_query = Mock()
        mock_query.join.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = [sample_term_item]
        service.db.query.return_value = mock_query
        
        terms = service._match_terms(keywords, table_ids, False, 10)
        
        # 验证查询调用
        service.db.query.assert_called()
        mock_query.join.assert_called()
        mock_query.filter.assert_called()
    
    def test_match_terms_database_error(self, service):
        """测试业务术语匹配数据库错误"""
        keywords = {"客户"}
        
        # 模拟数据库错误
        service.db.query.side_effect = Exception("Database error")
        
        terms = service._match_terms(keywords, None, True, 10)
        
        # 应该返回空列表而不是抛出异常
        assert terms == []
    
    def test_generate_enhanced_context_complete(self, service):
        """测试生成完整增强上下文"""
        user_question = "查询客户购买记录"
        
        # 创建知识库语义信息
        terms = [TermKnowledge(
            id="term_001",
            name="客户",
            explanation="购买产品的个人或企业",
            example_question="有多少客户？",
            relevance_score=2.0
        )]
        
        logics = [LogicKnowledge(
            id="logic_001",
            explanation="VIP客户消费超过10000元",
            example_question="哪些是VIP客户？",
            relevance_score=1.5
        )]
        
        events = [EventKnowledge(
            id="event_001",
            explanation="双十一促销活动",
            event_date_start=datetime(2024, 11, 11),
            event_date_end=datetime(2024, 11, 11, 23, 59, 59),
            relevance_score=1.0,
            is_active=False
        )]
        
        knowledge_info = KnowledgeSemanticInfo(
            terms=terms,
            logics=logics,
            events=events
        )
        
        context = service._generate_enhanced_context(user_question, knowledge_info)
        
        assert "用户问题: 查询客户购买记录" in context
        assert "业务术语:" in context
        assert "客户: 购买产品的个人或企业" in context
        assert "业务逻辑:" in context
        assert "VIP客户消费超过10000元" in context
        assert "相关事件:" in context
        assert "[已结束] 双十一促销活动" in context
    
    def test_generate_enhanced_context_empty(self, service):
        """测试生成空知识的增强上下文"""
        user_question = "查询数据"
        knowledge_info = KnowledgeSemanticInfo(terms=[], logics=[], events=[])
        
        context = service._generate_enhanced_context(user_question, knowledge_info)
        
        assert context == "用户问题: 查询数据"
    
    def test_generate_injection_summary(self, service):
        """测试生成注入摘要"""
        terms = [TermKnowledge(id="1", name="客户", explanation="", relevance_score=2.0, scope="GLOBAL")]
        logics = [LogicKnowledge(id="2", explanation="", relevance_score=1.5, scope="TABLE")]
        events = [EventKnowledge(id="3", explanation="", relevance_score=1.0, scope="GLOBAL", is_active=True)]
        
        knowledge_info = KnowledgeSemanticInfo(
            terms=terms,
            logics=logics,
            events=events,
            total_relevance_score=4.5
        )
        
        summary = service._generate_injection_summary(knowledge_info)
        
        assert summary["total_knowledge_items"] == 3
        assert summary["terms_count"] == 1
        assert summary["logics_count"] == 1
        assert summary["events_count"] == 1
        assert summary["active_events_count"] == 1
        assert summary["total_relevance_score"] == 4.5
        assert summary["average_relevance_score"] == 1.5
        assert summary["knowledge_distribution"]["global_knowledge"] == 2
        assert summary["knowledge_distribution"]["table_knowledge"] == 1
    
    def test_inject_knowledge_semantics_success(self, service):
        """测试知识库语义注入成功"""
        user_question = "查询客户购买记录"
        
        # 直接Mock三个匹配方法，返回预期的结果
        with patch.object(service, '_match_terms') as mock_match_terms, \
             patch.object(service, '_match_logics') as mock_match_logics, \
             patch.object(service, '_match_events') as mock_match_events:
            
            # 设置Mock返回值
            mock_match_terms.return_value = [TermKnowledge(
                id="term_001",
                name="客户",
                explanation="购买产品的个人或企业",
                relevance_score=2.0
            )]
            
            mock_match_logics.return_value = [LogicKnowledge(
                id="logic_001",
                explanation="VIP客户消费超过10000元",
                relevance_score=1.5
            )]
            
            mock_match_events.return_value = [EventKnowledge(
                id="event_001",
                explanation="双十一促销活动",
                relevance_score=1.0,
                is_active=False
            )]
            
            result = service.inject_knowledge_semantics(user_question)
            
            assert isinstance(result, SemanticInjectionResult)
            assert user_question in result.enhanced_context
            assert result.knowledge_info.total_relevance_score == 4.5
            assert "total_knowledge_items" in result.injection_summary
            assert result.injection_summary["total_knowledge_items"] == 3
    
    def test_inject_knowledge_semantics_with_table_ids(self, service, sample_term_item):
        """测试带表ID的知识库语义注入"""
        user_question = "查询客户数据"
        table_ids = ["table_001", "table_002"]
        
        # 模拟数据库查询
        mock_query = Mock()
        mock_query.join.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = [sample_term_item]
        service.db.query.return_value = mock_query
        
        result = service.inject_knowledge_semantics(
            user_question=user_question,
            table_ids=table_ids,
            include_global=False,
            max_terms=5,
            max_logics=3,
            max_events=2
        )
        
        assert isinstance(result, SemanticInjectionResult)
        assert user_question in result.enhanced_context
    
    def test_inject_knowledge_semantics_error_handling(self, service):
        """测试知识库语义注入错误处理"""
        user_question = "查询数据"
        
        # 模拟主方法直接抛出异常（而不是子方法）
        with patch.object(service, '_extract_keywords') as mock_extract:
            mock_extract.side_effect = Exception("Keyword extraction failed")
            
            result = service.inject_knowledge_semantics(user_question)
            
            # 应该返回默认结果而不是抛出异常
            assert isinstance(result, SemanticInjectionResult)
            assert result.enhanced_context == user_question  # 错误时直接返回原问题
            assert len(result.knowledge_info.terms) == 0
            assert "error" in result.injection_summary
            assert "Keyword extraction failed" in result.injection_summary["error"]
    
    def test_get_knowledge_by_table_success(self, service, sample_term_item, sample_logic_item):
        """测试获取表级知识成功"""
        table_id = "table_001"
        
        # 模拟数据库查询
        mock_query = Mock()
        mock_query.join.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = [sample_term_item, sample_logic_item]
        service.db.query.return_value = mock_query
        
        knowledge_info = service.get_knowledge_by_table(table_id)
        
        assert isinstance(knowledge_info, KnowledgeSemanticInfo)
        assert len(knowledge_info.terms) == 1
        assert len(knowledge_info.logics) == 1
        assert knowledge_info.total_relevance_score == 2.0  # 每个项目默认1.0分
    
    def test_get_knowledge_by_table_error(self, service):
        """测试获取表级知识错误处理"""
        table_id = "table_001"
        
        # 模拟数据库错误
        service.db.query.side_effect = Exception("Database error")
        
        knowledge_info = service.get_knowledge_by_table(table_id)
        
        # 应该返回空结果
        assert isinstance(knowledge_info, KnowledgeSemanticInfo)
        assert len(knowledge_info.terms) == 0
        assert len(knowledge_info.logics) == 0
        assert len(knowledge_info.events) == 0
    
    def test_get_global_knowledge_success(self, service, sample_term_item, sample_event_item):
        """测试获取全局知识成功"""
        # 模拟数据库查询
        mock_query = Mock()
        mock_query.join.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = [sample_term_item, sample_event_item]
        service.db.query.return_value = mock_query
        
        knowledge_info = service.get_global_knowledge()
        
        assert isinstance(knowledge_info, KnowledgeSemanticInfo)
        assert len(knowledge_info.terms) == 1
        assert len(knowledge_info.events) == 1
        assert knowledge_info.total_relevance_score == 1.6  # 每个项目默认0.8分
    
    def test_get_global_knowledge_error(self, service):
        """测试获取全局知识错误处理"""
        # 模拟数据库错误
        service.db.query.side_effect = Exception("Database error")
        
        knowledge_info = service.get_global_knowledge()
        
        # 应该返回空结果
        assert isinstance(knowledge_info, KnowledgeSemanticInfo)
        assert len(knowledge_info.terms) == 0
        assert len(knowledge_info.logics) == 0
        assert len(knowledge_info.events) == 0
    
    def test_clear_cache(self, service):
        """测试清空缓存"""
        # 添加一些缓存数据
        service.term_cache["test"] = []
        service.logic_cache["test"] = []
        service.event_cache["test"] = []
        
        service.clear_cache()
        
        assert len(service.term_cache) == 0
        assert len(service.logic_cache) == 0
        assert len(service.event_cache) == 0
    
    def test_knowledge_type_enum(self):
        """测试知识类型枚举"""
        assert KnowledgeType.TERM == "TERM"
        assert KnowledgeType.LOGIC == "LOGIC"
        assert KnowledgeType.EVENT == "EVENT"
    
    def test_knowledge_scope_enum(self):
        """测试知识范围枚举"""
        assert KnowledgeScope.GLOBAL == "GLOBAL"
        assert KnowledgeScope.TABLE == "TABLE"
    
    def test_term_knowledge_dataclass(self):
        """测试业务术语知识数据类"""
        term = TermKnowledge(
            id="test_id",
            name="测试术语",
            explanation="测试解释",
            example_question="测试问题？",
            scope="GLOBAL",
            table_id=None,
            relevance_score=1.5
        )
        
        assert term.id == "test_id"
        assert term.name == "测试术语"
        assert term.explanation == "测试解释"
        assert term.example_question == "测试问题？"
        assert term.scope == "GLOBAL"
        assert term.table_id is None
        assert term.relevance_score == 1.5
    
    def test_logic_knowledge_dataclass(self):
        """测试业务逻辑知识数据类"""
        logic = LogicKnowledge(
            id="test_id",
            explanation="测试逻辑",
            example_question="测试问题？",
            scope="TABLE",
            table_id="table_001",
            relevance_score=2.0
        )
        
        assert logic.id == "test_id"
        assert logic.explanation == "测试逻辑"
        assert logic.example_question == "测试问题？"
        assert logic.scope == "TABLE"
        assert logic.table_id == "table_001"
        assert logic.relevance_score == 2.0
    
    def test_event_knowledge_dataclass(self):
        """测试事件知识数据类"""
        start_date = datetime(2024, 11, 11)
        end_date = datetime(2024, 11, 11, 23, 59, 59)
        
        event = EventKnowledge(
            id="test_id",
            explanation="测试事件",
            event_date_start=start_date,
            event_date_end=end_date,
            scope="GLOBAL",
            table_id=None,
            relevance_score=1.0,
            is_active=True
        )
        
        assert event.id == "test_id"
        assert event.explanation == "测试事件"
        assert event.event_date_start == start_date
        assert event.event_date_end == end_date
        assert event.scope == "GLOBAL"
        assert event.table_id is None
        assert event.relevance_score == 1.0
        assert event.is_active is True
    
    def test_knowledge_semantic_info_dataclass(self):
        """测试知识库语义信息数据类"""
        terms = [TermKnowledge(id="1", name="术语", explanation="", relevance_score=1.0)]
        logics = [LogicKnowledge(id="2", explanation="逻辑", relevance_score=1.5)]
        events = [EventKnowledge(id="3", explanation="事件", relevance_score=2.0, is_active=True)]
        
        info = KnowledgeSemanticInfo(
            terms=terms,
            logics=logics,
            events=events,
            total_relevance_score=4.5
        )
        
        assert len(info.terms) == 1
        assert len(info.logics) == 1
        assert len(info.events) == 1
        assert info.total_relevance_score == 4.5
    
    def test_semantic_injection_result_dataclass(self):
        """测试语义注入结果数据类"""
        knowledge_info = KnowledgeSemanticInfo(terms=[], logics=[], events=[])
        injection_summary = {"total_items": 0}
        
        result = SemanticInjectionResult(
            enhanced_context="测试上下文",
            knowledge_info=knowledge_info,
            injection_summary=injection_summary
        )
        
        assert result.enhanced_context == "测试上下文"
        assert result.knowledge_info == knowledge_info
        assert result.injection_summary == injection_summary