"""
本地数据分析引擎服务层单元测试
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from typing import List, Dict, Any

from src.services.local_data_analyzer import (
    LocalDataAnalyzer,
    QueryResult,
    AnalysisContext,
    AnalysisResult
)


@pytest.fixture
def sample_query_result():
    """示例查询结果"""
    return QueryResult(
        query_id="query_001",
        sql="SELECT * FROM sales WHERE date >= '2024-01-01'",
        data=[
            {"date": "2024-01-01", "amount": 1000, "product": "A"},
            {"date": "2024-01-02", "amount": 1500, "product": "B"},
            {"date": "2024-01-03", "amount": 1200, "product": "A"}
        ],
        columns=["date", "amount", "product"],
        row_count=3,
        executed_at=datetime(2024, 1, 1, 10, 0, 0)
    )


@pytest.fixture
def sample_analysis_context(sample_query_result):
    """示例分析上下文"""
    return AnalysisContext(
        current_result=sample_query_result,
        previous_results=[],
        conversation_history=[],
        user_question="这些数据显示了什么趋势？"
    )


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI客户端"""
    with patch('src.services.local_data_analyzer.AsyncOpenAI') as mock:
        client = AsyncMock()
        mock.return_value = client
        yield client


class TestQueryResult:
    """测试QueryResult数据类"""
    
    def test_query_result_creation(self, sample_query_result):
        """测试创建QueryResult"""
        assert sample_query_result.query_id == "query_001"
        assert sample_query_result.row_count == 3
        assert len(sample_query_result.columns) == 3
    
    def test_query_result_to_dict(self, sample_query_result):
        """测试转换为字典"""
        result_dict = sample_query_result.to_dict()
        
        assert result_dict["query_id"] == "query_001"
        assert result_dict["row_count"] == 3
        assert "executed_at" in result_dict


class TestAnalysisContext:
    """测试AnalysisContext数据类"""
    
    def test_context_creation(self, sample_analysis_context):
        """测试创建AnalysisContext"""
        assert sample_analysis_context.user_question == "这些数据显示了什么趋势？"
        assert sample_analysis_context.current_result.row_count == 3
    
    def test_get_data_summary(self, sample_analysis_context):
        """测试获取数据摘要"""
        summary = sample_analysis_context.get_data_summary()
        
        assert "当前查询结果" in summary
        assert "date, amount, product" in summary
        assert "3" in summary
    
    def test_get_data_summary_with_history(self, sample_analysis_context, sample_query_result):
        """测试包含历史的数据摘要"""
        sample_analysis_context.previous_results = [sample_query_result]
        summary = sample_analysis_context.get_data_summary()
        
        assert "历史查询结果" in summary


class TestLocalDataAnalyzer:
    """测试LocalDataAnalyzer类"""
    
    def test_analyzer_initialization(self):
        """测试分析器初始化"""
        analyzer = LocalDataAnalyzer(
            openai_api_key="test_key",
            openai_base_url="http://localhost:11434/v1",
            model_name="qwen2.5:latest"
        )
        
        assert analyzer.model_name == "qwen2.5:latest"
        assert analyzer.max_tokens == 2000
        assert analyzer.temperature == 0.7
        assert analyzer.stats["total_analyses"] == 0
    
    def test_build_analysis_prompt(self, sample_analysis_context):
        """测试构建分析Prompt"""
        analyzer = LocalDataAnalyzer(
            openai_api_key="test_key",
            openai_base_url="http://localhost:11434/v1"
        )
        
        prompt = analyzer._build_analysis_prompt(sample_analysis_context)
        
        assert "专业的数据分析助手" in prompt
        assert "这些数据显示了什么趋势？" in prompt
        assert "date, amount, product" in prompt
    
    def test_build_analysis_prompt_with_history(self, sample_analysis_context):
        """测试包含对话历史的Prompt构建"""
        sample_analysis_context.conversation_history = [
            {"role": "user", "content": "显示销售数据"},
            {"role": "assistant", "content": "已显示销售数据"}
        ]
        
        analyzer = LocalDataAnalyzer(
            openai_api_key="test_key",
            openai_base_url="http://localhost:11434/v1"
        )
        
        prompt = analyzer._build_analysis_prompt(sample_analysis_context)
        
        assert "对话历史" in prompt
        assert "显示销售数据" in prompt
    
    @pytest.mark.asyncio
    async def test_analyze_data_success(self, sample_analysis_context, mock_openai_client):
        """测试成功分析数据"""
        # Mock响应
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "数据显示销售额呈上升趋势。"
        mock_response.usage.total_tokens = 150
        
        mock_openai_client.chat.completions.create = AsyncMock(return_value=mock_response)
        
        analyzer = LocalDataAnalyzer(
            openai_api_key="test_key",
            openai_base_url="http://localhost:11434/v1"
        )
        analyzer.client = mock_openai_client
        
        result = await analyzer.analyze_data(sample_analysis_context, stream=False)
        
        assert isinstance(result, AnalysisResult)
        assert result.question == "这些数据显示了什么趋势？"
        assert "趋势" in result.answer
        assert analyzer.stats["successful_analyses"] == 1
        assert analyzer.stats["total_tokens_used"] == 150
    
    @pytest.mark.asyncio
    async def test_analyze_data_stream_mode_error(self, sample_analysis_context):
        """测试流式模式错误"""
        analyzer = LocalDataAnalyzer(
            openai_api_key="test_key",
            openai_base_url="http://localhost:11434/v1"
        )
        
        with pytest.raises(Exception, match="数据分析失败.*请使用 analyze_data_stream 方法"):
            await analyzer.analyze_data(sample_analysis_context, stream=True)
    
    @pytest.mark.asyncio
    async def test_analyze_data_failure(self, sample_analysis_context, mock_openai_client):
        """测试分析失败"""
        mock_openai_client.chat.completions.create = AsyncMock(
            side_effect=Exception("API调用失败")
        )
        
        analyzer = LocalDataAnalyzer(
            openai_api_key="test_key",
            openai_base_url="http://localhost:11434/v1"
        )
        analyzer.client = mock_openai_client
        
        with pytest.raises(Exception, match="数据分析失败"):
            await analyzer.analyze_data(sample_analysis_context, stream=False)
        
        assert analyzer.stats["failed_analyses"] == 1
    
    @pytest.mark.asyncio
    async def test_analyze_data_stream(self, sample_analysis_context, mock_openai_client):
        """测试流式分析数据"""
        # Mock流式响应
        async def mock_stream():
            chunks = ["数据", "显示", "上升", "趋势"]
            for chunk_text in chunks:
                chunk = MagicMock()
                chunk.choices = [MagicMock()]
                chunk.choices[0].delta.content = chunk_text
                yield chunk
        
        mock_openai_client.chat.completions.create = AsyncMock(return_value=mock_stream())
        
        analyzer = LocalDataAnalyzer(
            openai_api_key="test_key",
            openai_base_url="http://localhost:11434/v1"
        )
        analyzer.client = mock_openai_client
        
        chunks = []
        async for chunk in analyzer.analyze_data_stream(sample_analysis_context):
            chunks.append(chunk)
        
        assert len(chunks) == 4
        assert "".join(chunks) == "数据显示上升趋势"
    
    @pytest.mark.asyncio
    async def test_compare_data(self, sample_query_result, mock_openai_client):
        """测试数据对比"""
        # 创建另一个查询结果
        previous_result = QueryResult(
            query_id="query_000",
            sql="SELECT * FROM sales WHERE date >= '2023-12-01'",
            data=[
                {"date": "2023-12-01", "amount": 800, "product": "A"},
                {"date": "2023-12-02", "amount": 900, "product": "B"}
            ],
            columns=["date", "amount", "product"],
            row_count=2,
            executed_at=datetime(2023, 12, 1, 10, 0, 0)
        )
        
        # Mock响应
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "销售额从上月的平均850增长到本月的平均1233，增长了45%。"
        mock_response.usage.total_tokens = 200
        
        mock_openai_client.chat.completions.create = AsyncMock(return_value=mock_response)
        
        analyzer = LocalDataAnalyzer(
            openai_api_key="test_key",
            openai_base_url="http://localhost:11434/v1"
        )
        analyzer.client = mock_openai_client
        
        result = await analyzer.compare_data(
            current_result=sample_query_result,
            previous_result=previous_result,
            comparison_question="销售额有什么变化？"
        )
        
        assert isinstance(result, AnalysisResult)
        assert "增长" in result.answer
        assert result.analysis_id.startswith("comparison_")
    
    def test_extract_insights(self):
        """测试提取洞察"""
        analyzer = LocalDataAnalyzer(
            openai_api_key="test_key",
            openai_base_url="http://localhost:11434/v1"
        )
        
        answer = "数据显示销售额呈上升趋势。发现产品A的销量最高。异常值出现在1月3日。"
        insights = analyzer._extract_insights(answer)
        
        assert len(insights) > 0
        assert any("趋势" in insight for insight in insights)
    
    def test_get_stats(self):
        """测试获取统计信息"""
        analyzer = LocalDataAnalyzer(
            openai_api_key="test_key",
            openai_base_url="http://localhost:11434/v1"
        )
        
        analyzer.stats["total_analyses"] = 10
        analyzer.stats["successful_analyses"] = 8
        
        stats = analyzer.get_stats()
        
        assert stats["total_analyses"] == 10
        assert stats["successful_analyses"] == 8
    
    def test_reset_stats(self):
        """测试重置统计信息"""
        analyzer = LocalDataAnalyzer(
            openai_api_key="test_key",
            openai_base_url="http://localhost:11434/v1"
        )
        
        analyzer.stats["total_analyses"] = 10
        analyzer.reset_stats()
        
        assert analyzer.stats["total_analyses"] == 0
        assert analyzer.stats["successful_analyses"] == 0


class TestDataPrivacy:
    """测试数据隐私保护"""
    
    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_data_stays_local(self, sample_analysis_context):
        """测试数据保持在本地"""
        # 创建分析器时使用本地URL
        local_url = "http://localhost:11434/v1"
        
        with patch('src.services.local_data_analyzer.AsyncOpenAI') as mock_openai_class:
            # Mock OpenAI客户端
            mock_client = AsyncMock()
            mock_client.base_url = local_url
            mock_openai_class.return_value = mock_client
            
            # Mock响应
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = "分析结果"
            mock_response.usage.total_tokens = 100
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
            
            analyzer = LocalDataAnalyzer(
                openai_api_key="test_key",
                openai_base_url=local_url
            )
            
            # 验证初始化时使用的是本地URL
            assert "localhost" in analyzer.client.base_url or "127.0.0.1" in analyzer.client.base_url
            
            await analyzer.analyze_data(sample_analysis_context, stream=False)
            
            # 验证调用了本地客户端
            assert mock_client.chat.completions.create.called

