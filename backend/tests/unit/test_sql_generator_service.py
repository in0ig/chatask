"""
SQL生成服务单元测试

任务 5.4.1 的服务层测试
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

from src.services.sql_generator_service import (
    SQLGeneratorService,
    SQLGenerationRequest,
    SQLGenerationResult,
    SQLDialect
)


@pytest.fixture
def sql_generator_service():
    """创建SQL生成服务实例"""
    return SQLGeneratorService()


@pytest.fixture
def sample_request():
    """创建示例请求"""
    return SQLGenerationRequest(
        user_question="查询销售额最高的前10个产品",
        table_ids=["tbl_products", "tbl_sales"],
        data_source_id="ds_001",
        sql_dialect=SQLDialect.MYSQL,
        include_explanation=True,
        max_rows=1000
    )


@pytest.mark.asyncio
async def test_generate_sql_success(sql_generator_service, sample_request):
    """测试SQL生成成功"""
    # Mock依赖
    with patch.object(sql_generator_service, '_get_semantic_context', new_callable=AsyncMock) as mock_context, \
         patch.object(sql_generator_service, '_build_sql_generation_prompt', new_callable=AsyncMock) as mock_prompt, \
         patch.object(sql_generator_service, '_generate_sql_with_qwen', new_callable=AsyncMock) as mock_qwen, \
         patch.object(sql_generator_service, '_extract_sql_from_response') as mock_extract, \
         patch.object(sql_generator_service, '_validate_sql', new_callable=AsyncMock) as mock_validate:
        
        # 设置Mock返回值
        mock_context.return_value = {
            "enhanced_context": "测试上下文",
            "modules_used": ["table_structure"],
            "total_tokens_used": 1000,
            "relevance_scores": {}
        }
        mock_prompt.return_value = "测试Prompt"
        mock_qwen.return_value = '{"sql": "SELECT * FROM products LIMIT 10;", "explanation": "查询产品", "confidence": 0.95}'
        mock_extract.return_value = "SELECT * FROM products LIMIT 10;"
        mock_validate.return_value = {"is_valid": True, "security_level": "safe", "violations": []}
        
        # 执行测试
        result = await sql_generator_service.generate_sql(sample_request)
        
        # 验证结果
        assert isinstance(result, SQLGenerationResult)
        assert result.sql == "SELECT * FROM products LIMIT 10;"
        assert result.confidence > 0
        assert result.generation_time > 0
        assert result.validation_result is not None


@pytest.mark.asyncio
async def test_generate_sql_with_error(sql_generator_service, sample_request):
    """测试SQL生成失败"""
    # Mock依赖抛出异常
    with patch.object(sql_generator_service, '_get_semantic_context', new_callable=AsyncMock) as mock_context:
        mock_context.side_effect = Exception("测试错误")
        
        # 执行测试
        result = await sql_generator_service.generate_sql(sample_request)
        
        # 验证错误结果
        assert isinstance(result, SQLGenerationResult)
        assert result.sql == ""
        assert "SQL生成失败" in result.explanation
        assert result.confidence == 0.0


@pytest.mark.asyncio
async def test_get_semantic_context(sql_generator_service, sample_request):
    """测试获取语义上下文"""
    # Mock语义聚合器
    with patch.object(sql_generator_service.semantic_aggregator, 'aggregate_semantic_context', new_callable=AsyncMock) as mock_aggregate:
        mock_aggregate.return_value = Mock(
            enhanced_context="测试上下文",
            modules_used=["table_structure", "dictionary"],
            total_tokens_used=1500,
            relevance_scores={"table_structure": 0.9}
        )
        
        # 执行测试
        context = await sql_generator_service._get_semantic_context(sample_request)
        
        # 验证结果
        assert "enhanced_context" in context
        assert "modules_used" in context
        assert context["total_tokens_used"] == 1500


@pytest.mark.asyncio
async def test_build_sql_generation_prompt(sql_generator_service, sample_request):
    """测试构建SQL生成Prompt"""
    semantic_context = {
        "enhanced_context": "测试上下文",
        "modules_used": ["table_structure"],
        "total_tokens_used": 1000,
        "relevance_scores": {}
    }
    
    # 执行测试
    prompt = await sql_generator_service._build_sql_generation_prompt(sample_request, semantic_context)
    
    # 验证结果
    assert isinstance(prompt, str)
    assert len(prompt) > 0
    assert sample_request.user_question in prompt
    assert "mysql" in prompt.lower()


def test_get_dialect_syntax(sql_generator_service):
    """测试获取SQL方言语法"""
    # 测试MySQL
    mysql_syntax = sql_generator_service._get_dialect_syntax(SQLDialect.MYSQL)
    assert "LIMIT" in mysql_syntax
    assert "反引号" in mysql_syntax
    
    # 测试SQL Server
    sqlserver_syntax = sql_generator_service._get_dialect_syntax(SQLDialect.SQLSERVER)
    assert "TOP" in sqlserver_syntax
    assert "方括号" in sqlserver_syntax
    
    # 测试PostgreSQL
    postgresql_syntax = sql_generator_service._get_dialect_syntax(SQLDialect.POSTGRESQL)
    assert "LIMIT" in postgresql_syntax
    assert "双引号" in postgresql_syntax


def test_extract_sql_from_json_response(sql_generator_service):
    """测试从JSON响应中提取SQL"""
    response = '{"sql": "SELECT * FROM products;", "explanation": "查询产品"}'
    
    sql = sql_generator_service._extract_sql_from_response(response)
    
    assert sql == "SELECT * FROM products;"


def test_extract_sql_from_markdown_response(sql_generator_service):
    """测试从Markdown响应中提取SQL"""
    response = """
这是一个SQL查询：

```sql
SELECT * FROM products
WHERE price > 100
LIMIT 10;
```

这个查询会返回价格大于100的产品。
"""
    
    sql = sql_generator_service._extract_sql_from_response(response)
    
    assert "SELECT" in sql
    assert "FROM products" in sql
    assert "WHERE price > 100" in sql


def test_extract_sql_from_plain_text(sql_generator_service):
    """测试从纯文本响应中提取SQL"""
    response = "SELECT * FROM products WHERE price > 100 LIMIT 10;"
    
    sql = sql_generator_service._extract_sql_from_response(response)
    
    assert "SELECT" in sql
    assert "FROM products" in sql


def test_extract_sql_failure(sql_generator_service):
    """测试SQL提取失败"""
    response = "这是一段没有SQL的文本"
    
    with pytest.raises(Exception) as exc_info:
        sql_generator_service._extract_sql_from_response(response)
    
    assert "无法从模型响应中提取有效的SQL语句" in str(exc_info.value)


@pytest.mark.asyncio
async def test_validate_sql(sql_generator_service):
    """测试SQL验证"""
    sql = "SELECT * FROM products LIMIT 10;"
    request = SQLGenerationRequest(
        user_question="查询产品",
        sql_dialect=SQLDialect.MYSQL
    )
    
    # Mock验证器
    with patch.object(sql_generator_service.sql_validator, 'validate_sql') as mock_validate:
        mock_validate.return_value = Mock(
            is_valid=True,
            security_level=Mock(value="safe"),
            violations=[],
            complexity=Mock(
                complexity_score=30.0,
                estimated_cost="LOW"
            )
        )
        
        # 执行测试
        validation_result = await sql_generator_service._validate_sql(sql, request)
        
        # 验证结果
        assert validation_result["is_valid"] is True
        assert validation_result["security_level"] == "safe"
        assert len(validation_result["violations"]) == 0


def test_update_generation_stats_success(sql_generator_service):
    """测试更新生成统计（成功）"""
    result = SQLGenerationResult(
        sql="SELECT * FROM products;",
        explanation="查询产品",
        estimated_rows=100,
        execution_plan="索引扫描",
        confidence=0.95,
        generation_time=1.5,
        semantic_context_used={},
        validation_result={"is_valid": True}
    )
    
    # 执行测试
    sql_generator_service._update_generation_stats(result, True)
    
    # 验证统计
    stats = sql_generator_service.get_generation_statistics()
    assert stats["total_generations"] == 1
    assert stats["successful_generations"] == 1
    assert stats["failed_generations"] == 0
    assert stats["average_generation_time"] == 1.5
    assert stats["average_confidence"] == 0.95


def test_update_generation_stats_failure(sql_generator_service):
    """测试更新生成统计（失败）"""
    # 执行测试
    sql_generator_service._update_generation_stats(None, False)
    
    # 验证统计
    stats = sql_generator_service.get_generation_statistics()
    assert stats["total_generations"] == 1
    assert stats["successful_generations"] == 0
    assert stats["failed_generations"] == 1


def test_get_generation_statistics(sql_generator_service):
    """测试获取生成统计"""
    # 执行测试
    stats = sql_generator_service.get_generation_statistics()
    
    # 验证结果
    assert "total_generations" in stats
    assert "successful_generations" in stats
    assert "failed_generations" in stats
    assert "success_rate" in stats
    assert "average_generation_time" in stats
    assert "average_confidence" in stats
    assert "syntax_correctness_rate" in stats
    assert "semantic_accuracy_rate" in stats


def test_build_basic_sql_prompt_mysql(sql_generator_service):
    """测试构建MySQL基础Prompt"""
    request = SQLGenerationRequest(
        user_question="查询销售额最高的产品",
        sql_dialect=SQLDialect.MYSQL,
        max_rows=100
    )
    semantic_context = {
        "enhanced_context": "测试上下文",
        "modules_used": [],
        "total_tokens_used": 0,
        "relevance_scores": {}
    }
    
    prompt = sql_generator_service._build_basic_sql_prompt(request, semantic_context)
    
    assert "mysql" in prompt.lower()
    assert "LIMIT" in prompt
    assert "100" in prompt
    assert request.user_question in prompt


def test_build_basic_sql_prompt_sqlserver(sql_generator_service):
    """测试构建SQL Server基础Prompt"""
    request = SQLGenerationRequest(
        user_question="查询销售额最高的产品",
        sql_dialect=SQLDialect.SQLSERVER,
        max_rows=100
    )
    semantic_context = {
        "enhanced_context": "测试上下文",
        "modules_used": [],
        "total_tokens_used": 0,
        "relevance_scores": {}
    }
    
    prompt = sql_generator_service._build_basic_sql_prompt(request, semantic_context)
    
    assert "sqlserver" in prompt.lower()
    assert "TOP" in prompt
    assert request.user_question in prompt


def test_parse_generation_result_with_json(sql_generator_service):
    """测试解析包含JSON的生成结果"""
    sql = "SELECT * FROM products LIMIT 10;"
    response = '{"sql": "SELECT * FROM products LIMIT 10;", "explanation": "查询产品", "estimated_rows": 10, "execution_plan": "索引扫描", "confidence": 0.95}'
    semantic_context = {"enhanced_context": "测试"}
    validation_result = {"is_valid": True}
    start_time = datetime.now().timestamp()
    
    result = sql_generator_service._parse_generation_result(
        sql, response, semantic_context, validation_result, start_time
    )
    
    assert result.sql == sql
    assert result.explanation == "查询产品"
    assert result.estimated_rows == 10
    assert result.execution_plan == "索引扫描"
    assert result.confidence == 0.95


def test_parse_generation_result_without_json(sql_generator_service):
    """测试解析不包含JSON的生成结果"""
    sql = "SELECT * FROM products LIMIT 10;"
    response = "这是一个简单的SQL查询"
    semantic_context = {"enhanced_context": "测试"}
    validation_result = {"is_valid": True}
    start_time = datetime.now().timestamp()
    
    result = sql_generator_service._parse_generation_result(
        sql, response, semantic_context, validation_result, start_time
    )
    
    assert result.sql == sql
    assert result.explanation == "SQL查询已生成"
    assert result.estimated_rows == 100
    assert result.confidence == 0.8


@pytest.mark.asyncio
async def test_generate_sql_with_different_dialects(sql_generator_service):
    """测试不同SQL方言的生成"""
    dialects = [SQLDialect.MYSQL, SQLDialect.SQLSERVER, SQLDialect.POSTGRESQL]
    
    for dialect in dialects:
        request = SQLGenerationRequest(
            user_question="查询产品",
            sql_dialect=dialect
        )
        
        # Mock依赖
        with patch.object(sql_generator_service, '_get_semantic_context', new_callable=AsyncMock) as mock_context, \
             patch.object(sql_generator_service, '_build_sql_generation_prompt', new_callable=AsyncMock) as mock_prompt, \
             patch.object(sql_generator_service, '_generate_sql_with_qwen', new_callable=AsyncMock) as mock_qwen, \
             patch.object(sql_generator_service, '_extract_sql_from_response') as mock_extract, \
             patch.object(sql_generator_service, '_validate_sql', new_callable=AsyncMock) as mock_validate:
            
            mock_context.return_value = {"enhanced_context": "测试", "modules_used": [], "total_tokens_used": 0, "relevance_scores": {}}
            mock_prompt.return_value = "测试Prompt"
            mock_qwen.return_value = '{"sql": "SELECT * FROM products;", "confidence": 0.9}'
            mock_extract.return_value = "SELECT * FROM products;"
            mock_validate.return_value = {"is_valid": True}
            
            result = await sql_generator_service.generate_sql(request)
            
            assert isinstance(result, SQLGenerationResult)
            assert result.sql != ""


def test_multiple_sql_extractions(sql_generator_service):
    """测试多种SQL提取场景"""
    test_cases = [
        ('{"sql": "SELECT 1;"}', "SELECT 1;"),
        ("```sql\nSELECT 2;\n```", "SELECT 2"),
        ("```\nSELECT 3;\n```", "SELECT 3"),
        ("SELECT 4;", "SELECT 4;"),
    ]
    
    for response, expected_sql in test_cases:
        sql = sql_generator_service._extract_sql_from_response(response)
        assert "SELECT" in sql
