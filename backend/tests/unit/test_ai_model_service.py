"""
AI 模型服务单元测试
测试云端 Qwen 模型适配器和本地 OpenAI 模型适配器
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import json
import time
from typing import Dict, Any

from src.services.ai_model_service import (
    AIModelService,
    QwenCloudAdapter,
    OpenAILocalAdapter,
    ModelType,
    ModelResponse,
    TokenUsage,
    AIModelError
)


class TestQwenCloudAdapter:
    """测试云端 Qwen 模型适配器"""

    @pytest.fixture
    def qwen_config(self):
        """Qwen 模型配置"""
        return {
            'api_key': 'test_api_key',
            'base_url': 'https://test.api.com',
            'model_name': 'qwen-turbo',
            'max_tokens': 2000,
            'temperature': 0.1,
            'retry_count': 3,
            'retry_delay': 0.1
        }

    @pytest.fixture
    def qwen_adapter(self, qwen_config):
        """创建 Qwen 适配器实例"""
        return QwenCloudAdapter(qwen_config)

    @pytest.mark.asyncio
    async def test_qwen_adapter_initialization(self, qwen_adapter):
        """测试 Qwen 适配器初始化"""
        assert qwen_adapter.model_type == ModelType.QWEN_CLOUD
        assert qwen_adapter.api_key == 'test_api_key'
        assert qwen_adapter.model_name == 'qwen-turbo'
        assert qwen_adapter.max_tokens == 2000
        assert qwen_adapter.temperature == 0.1

    @pytest.mark.asyncio
    async def test_successful_generation(self, qwen_adapter):
        """测试成功生成响应"""
        # Mock HTTP 响应 - 阿里云 DashScope 格式
        mock_response = {
            'code': 200,
            'output': {
                'choices': [{
                    'message': {
                        'content': 'SELECT * FROM users WHERE id = 1;'
                    }
                }]
            },
            'usage': {
                'input_tokens': 100,
                'output_tokens': 50,
                'total_tokens': 150
            }
        }

        # 创建 Mock 响应对象
        mock_http_response = Mock()
        mock_http_response.json.return_value = mock_response
        mock_http_response.raise_for_status.return_value = None

        with patch.object(qwen_adapter.client, 'post', return_value=mock_http_response) as mock_post:
            response = await qwen_adapter.generate("Generate SQL for user query")

            assert isinstance(response, ModelResponse)
            assert response.content == 'SELECT * FROM users WHERE id = 1;'
            assert response.model_type == ModelType.QWEN_CLOUD
            assert response.tokens_used == 150
            assert response.response_time > 0
            assert 'usage' in response.metadata

    @pytest.mark.asyncio
    async def test_api_error_handling(self, qwen_adapter):
        """测试 API 错误处理"""
        mock_response = {
            'code': 400,
            'message': 'Invalid request'
        }

        # 创建 Mock 响应对象
        mock_http_response = Mock()
        mock_http_response.json.return_value = mock_response
        mock_http_response.raise_for_status.return_value = None

        with patch.object(qwen_adapter.client, 'post', return_value=mock_http_response):
            with pytest.raises(AIModelError) as exc_info:
                await qwen_adapter.generate("Test prompt")

            assert "Qwen API error" in str(exc_info.value)
            assert exc_info.value.model_type == ModelType.QWEN_CLOUD

    @pytest.mark.asyncio
    async def test_retry_mechanism(self, qwen_adapter):
        """测试重试机制"""
        # 前两次调用失败，第三次成功
        mock_responses = [
            Exception("Network error"),
            Exception("Timeout error"),
            Mock(json=lambda: {
                'code': 200,
                'output': {'choices': [{'message': {'content': 'Success'}}]},
                'usage': {'input_tokens': 10, 'output_tokens': 5, 'total_tokens': 15}
            })
        ]

        call_count = 0
        async def mock_post_side_effect(*args, **kwargs):
            nonlocal call_count
            response = mock_responses[call_count]
            call_count += 1
            if isinstance(response, Exception):
                raise response
            response.raise_for_status = Mock()
            return response

        with patch.object(qwen_adapter.client, 'post', side_effect=mock_post_side_effect):
            response = await qwen_adapter.generate("Test prompt")

            assert response.content == 'Success'
            assert call_count == 3  # 两次重试 + 一次成功

    @pytest.mark.asyncio
    async def test_max_retries_exceeded(self, qwen_adapter):
        """测试超过最大重试次数"""
        with patch.object(qwen_adapter.client, 'post', side_effect=Exception("Persistent error")):
            with pytest.raises(AIModelError) as exc_info:
                await qwen_adapter.generate("Test prompt")

            assert "Failed after 3 retries" in str(exc_info.value)
            assert exc_info.value.retry_count == 3

    def test_sql_extraction_markdown(self, qwen_adapter):
        """测试从 Markdown 代码块提取 SQL"""
        response_text = """
        Here's the SQL query you requested:

        ```sql
        SELECT name, age FROM users WHERE age > 18;
        ```

        This query will return all users older than 18.
        """

        sql = qwen_adapter.extract_sql_from_response(response_text)
        assert sql == "SELECT name, age FROM users WHERE age > 18;"

    def test_sql_extraction_direct(self, qwen_adapter):
        """测试直接提取 SQL 语句"""
        response_text = "SELECT * FROM products WHERE price > 100"

        sql = qwen_adapter.extract_sql_from_response(response_text)
        assert sql == "SELECT * FROM products WHERE price > 100;"

    def test_sql_extraction_no_match(self, qwen_adapter):
        """测试无法提取 SQL 的情况"""
        response_text = "I cannot generate SQL for this request."

        sql = qwen_adapter.extract_sql_from_response(response_text)
        assert sql is None

    def test_token_usage_stats_update(self, qwen_adapter):
        """测试 Token 使用量统计更新"""
        usage = TokenUsage(
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
            cost_estimate=0.3
        )

        initial_stats = qwen_adapter.get_token_usage_stats()
        assert initial_stats['total_requests'] == 0
        assert initial_stats['total_tokens'] == 0

        qwen_adapter._update_token_stats(usage)

        updated_stats = qwen_adapter.get_token_usage_stats()
        assert updated_stats['total_requests'] == 1
        assert updated_stats['total_tokens'] == 150
        assert updated_stats['total_cost'] == 0.3

    def test_cost_calculation(self, qwen_adapter):
        """测试成本计算"""
        cost = qwen_adapter._calculate_cost(1000)  # 1000 tokens
        assert cost == 0.002  # $0.002 per 1K tokens

        cost = qwen_adapter._calculate_cost(2500)  # 2500 tokens
        assert cost == 0.005  # $0.005

    def test_prompt_sanitization_warning(self, qwen_adapter):
        """测试 prompt 清洗警告"""
        sensitive_prompt = "SELECT * FROM users WHERE created_at = '2023-01-01' AND balance = 1000.50"

        with patch('src.services.ai_model_service.logger') as mock_logger:
            sanitized = qwen_adapter._sanitize_prompt(sensitive_prompt)

            # 应该记录警告
            assert mock_logger.warning.called
            # 目前返回原始 prompt（实际实现中应该有更严格的清洗）
            assert sanitized == sensitive_prompt


class TestOpenAILocalAdapter:
    """测试本地 OpenAI 模型适配器"""

    @pytest.fixture
    def openai_config(self):
        """OpenAI 模型配置（兼容模式）"""
        return {
            'api_key': 'sk-test-key',
            'base_url': 'http://localhost:11434/v1',  # 兼容模式
            'model_name': 'qwen3.5',
            'max_tokens': 2000,
            'temperature': 0.7,
            'retry_count': 2,
            'retry_delay': 0.1,
            'max_concurrent_requests': 5,
            'request_timeout': 60,
            'audit_logging': True
        }

    @pytest.fixture
    def openai_adapter(self, openai_config):
        """创建 OpenAI 适配器实例"""
        return OpenAILocalAdapter(openai_config)

    @pytest.mark.asyncio
    async def test_openai_adapter_initialization(self, openai_adapter):
        """测试 OpenAI 适配器初始化"""
        assert openai_adapter.model_type == ModelType.OPENAI_LOCAL
        assert openai_adapter.api_key == 'sk-test-key'
        assert openai_adapter.model_name == 'qwen3.5'
        assert openai_adapter.temperature == 0.7
        assert openai_adapter.max_concurrent_requests == 5
        assert openai_adapter.audit_logging is True

    @pytest.mark.asyncio
    async def test_successful_local_generation(self, openai_adapter):
        """测试本地模型成功生成"""
        # Mock OpenAI 兼容 API 响应
        mock_response = {
            'choices': [{
                'message': {
                    'content': '根据数据分析，用户活跃度呈上升趋势。'
                }
            }],
            'usage': {'total_tokens': 200}
        }

        mock_http_response = Mock()
        mock_http_response.json.return_value = mock_response
        mock_http_response.raise_for_status.return_value = None

        with patch.object(openai_adapter.client, 'post', return_value=mock_http_response):
            response = await openai_adapter.generate("分析用户数据")

            assert isinstance(response, ModelResponse)
            assert response.content == '根据数据分析，用户活跃度呈上升趋势。'
            assert response.model_type == ModelType.OPENAI_LOCAL
            assert response.tokens_used == 200
            assert response.metadata['data_analysis'] is True

    @pytest.mark.asyncio
    async def test_analyze_query_result(self, openai_adapter):
        """测试查询结果分析"""
        query_result = {
            'data': [
                ['张三', 25, '北京'],
                ['李四', 30, '上海'],
                ['王五', 28, '广州']
            ],
            'columns': ['姓名', '年龄', '城市']
        }

        # Mock OpenAI 兼容 API 响应
        mock_response = {
            'choices': [{
                'message': {
                    'content': '数据显示用户年龄分布在 25-30 岁之间，主要来自一线城市。'
                }
            }],
            'usage': {'total_tokens': 150}
        }

        mock_http_response = Mock()
        mock_http_response.json.return_value = mock_response
        mock_http_response.raise_for_status.return_value = None

        with patch.object(openai_adapter.client, 'post', return_value=mock_http_response):
            response = await openai_adapter.analyze_query_result(query_result, "分析用户分布")

            assert '数据显示用户年龄分布' in response.content or '用户年龄分布' in response.content
            assert response.metadata.get('data_points', 0) >= 0

    @pytest.mark.asyncio
    async def test_handle_followup_question(self, openai_adapter):
        """测试追问处理"""
        current_data = {
            'data': [['产品 A', 100], ['产品 B', 200]],
            'columns': ['产品', '销量']
        }

        previous_data = [
            {
                'data': [['产品 A', 80], ['产品 B', 150]],
                'columns': ['产品', '销量']
            }
        ]

        # Mock OpenAI 兼容 API 响应
        mock_response = {
            'choices': [{
                'message': {
                    'content': '对比上期数据，产品 A 销量增长 25%，产品 B 销量增长 33%。'
                }
            }],
            'usage': {'total_tokens': 120}
        }

        mock_http_response = Mock()
        mock_http_response.json.return_value = mock_response
        mock_http_response.raise_for_status.return_value = None

        with patch.object(openai_adapter.client, 'post', return_value=mock_http_response):
            response = await openai_adapter.handle_followup_question(
                "与上期相比增长如何？", current_data, previous_data
            )

            assert '增长' in response.content
            assert response.metadata.get('data_analysis', True) is True

    def test_build_analysis_prompt(self, openai_adapter):
        """测试分析 prompt 构建"""
        query_result = {
            'data': [['张三', 25], ['李四', 30]],
            'columns': ['姓名', '年龄']
        }

        prompt = openai_adapter._build_analysis_prompt(query_result, "用户年龄分析")

        assert "用户年龄分析" in prompt
        assert "2 行记录" in prompt
        assert '"姓名"' in prompt or "'姓名'" in prompt
        assert "张三" in prompt
        assert "数据概览和关键发现" in prompt

    def test_build_followup_prompt(self, openai_adapter):
        """测试追问 prompt 构建"""
        current_data = {
            'data': [['A', 100]],
            'columns': ['产品', '销量']
        }

        previous_data = [
            {
                'data': [['A', 80]],
                'columns': ['产品', '销量']
            }
        ]

        prompt = openai_adapter._build_followup_prompt("增长如何？", current_data, previous_data)

        assert "增长如何？" in prompt
        assert "当前数据" in prompt
        assert "历史数据对比" in prompt
        assert "历史查询" in prompt

    def test_summarize_data(self, openai_adapter):
        """测试数据摘要"""
        data_dict = {
            'data': [['张三', 25], ['李四', 30]],
            'columns': ['姓名', '年龄']
        }

        summary = openai_adapter._summarize_data(data_dict)

        assert "包含 2 行记录" in summary
        assert "字段：姓名" in summary or "字段：姓名" in summary
        assert "样本数据：['张三', 25]" in summary

    def test_processing_stats(self, openai_adapter):
        """测试处理统计"""
        # 模拟更新统计
        openai_adapter.processing_stats['total_requests'] = 10
        openai_adapter.processing_stats['successful_requests'] = 8
        openai_adapter.processing_stats['failed_requests'] = 2
        openai_adapter.processing_stats['data_analysis_count'] = 5
        openai_adapter.processing_stats['followup_questions_count'] = 3

        stats = openai_adapter.get_processing_stats()

        assert stats['total_requests'] == 10
        assert stats['successful_requests'] == 8
        assert stats['success_rate'] == 0.8
        assert stats['data_analysis_count'] == 5
        assert stats['followup_questions_count'] == 3

    def test_update_avg_response_time(self, openai_adapter):
        """测试平均响应时间更新"""
        # 第一次请求
        openai_adapter.processing_stats['total_requests'] = 1
        openai_adapter._update_avg_response_time(2.0)
        assert openai_adapter.processing_stats['avg_response_time'] == 2.0

        # 第二次请求
        openai_adapter.processing_stats['total_requests'] = 2
        openai_adapter._update_avg_response_time(4.0)
        assert openai_adapter.processing_stats['avg_response_time'] == 3.0  # (2.0 + 4.0) / 2


class TestAIModelService:
    """测试 AI 模型服务"""

    @pytest.fixture
    def service_config(self):
        """服务配置"""
        return {
            'qwen_cloud': {
                'api_key': 'test_key',
                'model_name': 'qwen-turbo'
            },
            'openai_local': {
                'base_url': 'http://localhost:11434/v1',
                'model_name': 'llama2'
            }
        }

    @pytest.fixture
    def ai_service(self, service_config):
        """创建 AI 模型服务实例"""
        return AIModelService(service_config)

    def test_service_initialization(self, ai_service):
        """测试服务初始化"""
        assert ModelType.QWEN_CLOUD in ai_service.adapters
        assert ModelType.OPENAI_LOCAL in ai_service.adapters
        assert isinstance(ai_service.adapters[ModelType.QWEN_CLOUD], QwenCloudAdapter)
        assert isinstance(ai_service.adapters[ModelType.OPENAI_LOCAL], OpenAILocalAdapter)

    @pytest.mark.asyncio
    async def test_generate_sql(self, ai_service):
        """测试 SQL 生成"""
        mock_response = ModelResponse(
            content="```sql\nSELECT * FROM users;\n```",
            model_type=ModelType.QWEN_CLOUD,
            tokens_used=100,
            response_time=1.0
        )

        with patch.object(ai_service.adapters[ModelType.QWEN_CLOUD], 'generate', return_value=mock_response):
            with patch.object(ai_service.adapters[ModelType.QWEN_CLOUD], 'extract_sql_from_response', return_value="SELECT * FROM users;"):
                response = await ai_service.generate_sql("Show all users")

                assert response.model_type == ModelType.QWEN_CLOUD
                assert 'extracted_sql' in response.metadata
                assert response.metadata['extracted_sql'] == "SELECT * FROM users;"

    @pytest.mark.asyncio
    async def test_analyze_data_locally(self, ai_service):
        """测试本地数据分析"""
        mock_response = ModelResponse(
            content="The data shows an upward trend...",
            model_type=ModelType.OPENAI_LOCAL,
            tokens_used=150,
            response_time=2.0
        )

        with patch.object(ai_service.adapters[ModelType.OPENAI_LOCAL], 'generate', return_value=mock_response):
            response = await ai_service.analyze_data_locally("Analyze this trend")

            assert response.model_type == ModelType.OPENAI_LOCAL
            assert "upward trend" in response.content

    @pytest.mark.asyncio
    async def test_analyze_query_result_locally(self, ai_service):
        """测试本地查询结果分析"""
        query_result = {
            'data': [['用户 A', 100], ['用户 B', 200]],
            'columns': ['用户', '积分']
        }

        mock_response = ModelResponse(
            content="用户积分分析结果...",
            model_type=ModelType.OPENAI_LOCAL,
            tokens_used=120,
            response_time=1.8,
            metadata={'analysis_type': 'query_result', 'data_points': 2}
        )

        with patch.object(ai_service.adapters[ModelType.OPENAI_LOCAL], 'analyze_query_result', return_value=mock_response):
            response = await ai_service.analyze_query_result_locally(query_result, "分析用户积分")

            assert response.model_type == ModelType.OPENAI_LOCAL
            assert "积分分析" in response.content
            assert response.metadata['analysis_type'] == 'query_result'

    @pytest.mark.asyncio
    async def test_handle_followup_question_locally(self, ai_service):
        """测试本地追问处理"""
        current_data = {'data': [['产品 A', 100]], 'columns': ['产品', '销量']}
        previous_data = [{'data': [['产品 A', 80]], 'columns': ['产品', '销量']}]

        mock_response = ModelResponse(
            content="销量增长了 25%",
            model_type=ModelType.OPENAI_LOCAL,
            tokens_used=90,
            response_time=1.5,
            metadata={'analysis_type': 'followup', 'has_comparison': True}
        )

        with patch.object(ai_service.adapters[ModelType.OPENAI_LOCAL], 'handle_followup_question', return_value=mock_response):
            response = await ai_service.handle_followup_question_locally(
                "增长了多少？", current_data, previous_data
            )

            assert response.model_type == ModelType.OPENAI_LOCAL
            assert "增长" in response.content
            assert response.metadata['has_comparison'] is True

    @pytest.mark.asyncio
    async def test_model_not_configured_error(self):
        """测试模型未配置的错误"""
        # 创建没有配置任何模型的服务
        empty_service = AIModelService({})

        with pytest.raises(AIModelError) as exc_info:
            await empty_service.generate_sql("Test prompt")

        assert "not configured" in str(exc_info.value)
        assert exc_info.value.model_type == ModelType.QWEN_CLOUD

    def test_get_token_usage_stats(self, ai_service):
        """测试获取 Token 使用量统计"""
        # Mock 统计数据
        mock_stats = {
            'total_requests': 10,
            'total_tokens': 1500,
            'total_cost': 3.0
        }

        with patch.object(ai_service.adapters[ModelType.QWEN_CLOUD], 'get_token_usage_stats', return_value=mock_stats):
            stats = ai_service.get_token_usage_stats(ModelType.QWEN_CLOUD)

            assert stats == mock_stats

    @pytest.mark.asyncio
    async def test_service_close(self, ai_service):
        """测试服务关闭"""
        # Mock 适配器的 close 方法
        for adapter in ai_service.adapters.values():
            adapter.close = AsyncMock()

        await ai_service.close()

        # 验证所有适配器的 close 方法都被调用
        for adapter in ai_service.adapters.values():
            adapter.close.assert_called_once()


class TestErrorHandling:
    """测试错误处理"""

    def test_ai_model_error_creation(self):
        """测试 AI 模型错误创建"""
        error = AIModelError("Test error", ModelType.QWEN_CLOUD, 2)

        assert str(error) == "Test error"
        assert error.model_type == ModelType.QWEN_CLOUD
        assert error.retry_count == 2

    @pytest.mark.asyncio
    async def test_network_timeout_handling(self):
        """测试网络超时处理"""
        config = {
            'api_key': 'test_key',
            'retry_count': 1,
            'retry_delay': 0.1
        }
        adapter = QwenCloudAdapter(config)

        with patch.object(adapter.client, 'post', side_effect=asyncio.TimeoutError("Request timeout")):
            with pytest.raises(AIModelError) as exc_info:
                await adapter.generate("Test prompt")

            assert "Failed after 1 retries" in str(exc_info.value)


class TestIntegration:
    """集成测试"""

    @pytest.mark.asyncio
    async def test_basic_ai_service_integration(self):
        """基础 AI 服务集成测试"""
        config = {
            'qwen_cloud': {
                'api_key': 'test_key',
                'model_name': 'qwen-turbo',
                'retry_count': 1
            },
            'openai_local': {
                'api_key': 'test_local_key',
                'model_name': 'local-test'
            }
        }

        service = AIModelService(config)

        # 验证服务初始化
        assert ModelType.QWEN_CLOUD in service.adapters
        assert ModelType.OPENAI_LOCAL in service.adapters

        # 测试配置获取
        qwen_stats = service.get_token_usage_stats(ModelType.QWEN_CLOUD)
        assert isinstance(qwen_stats, dict)


if __name__ == '__main__':
    pytest.main(['-v'])
