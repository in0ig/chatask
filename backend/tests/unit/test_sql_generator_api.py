"""
SQL生成服务API单元测试

任务 5.4.1 的API层测试
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock, Mock
from datetime import datetime

from src.main import app
from src.services.sql_generator_service import (
    SQLGenerationResult,
    SQLDialect
)


client = TestClient(app)


@pytest.fixture
def mock_sql_generator_service():
    """Mock SQL生成服务"""
    with patch('src.api.sql_generator_api.sql_generator_service') as mock_service:
        yield mock_service


def test_generate_sql_success(mock_sql_generator_service):
    """测试SQL生成成功"""
    # Mock服务返回
    mock_result = SQLGenerationResult(
        sql="SELECT * FROM products LIMIT 10;",
        explanation="查询产品列表",
        estimated_rows=10,
        execution_plan="索引扫描",
        confidence=0.95,
        generation_time=1.5,
        semantic_context_used={"modules_used": ["table_structure"]},
        validation_result={"is_valid": True, "security_level": "safe", "violations": []}
    )
    mock_sql_generator_service.generate_sql = AsyncMock(return_value=mock_result)
    
    # 发送请求
    response = client.post(
        "/api/sql-generator/generate",
        json={
            "user_question": "查询所有产品",
            "sql_dialect": "mysql",
            "max_rows": 10
        }
    )
    
    # 验证响应
    assert response.status_code == 200
    data = response.json()
    assert data["sql"] == "SELECT * FROM products LIMIT 10;"
    assert data["confidence"] == 0.95
    assert data["validation_result"]["is_valid"] is True


def test_generate_sql_with_table_ids(mock_sql_generator_service):
    """测试带表ID的SQL生成"""
    mock_result = SQLGenerationResult(
        sql="SELECT * FROM products;",
        explanation="查询产品",
        estimated_rows=100,
        execution_plan="全表扫描",
        confidence=0.9,
        generation_time=1.2,
        semantic_context_used={},
        validation_result={"is_valid": True}
    )
    mock_sql_generator_service.generate_sql = AsyncMock(return_value=mock_result)
    
    response = client.post(
        "/api/sql-generator/generate",
        json={
            "user_question": "查询产品",
            "table_ids": ["tbl_001", "tbl_002"],
            "data_source_id": "ds_001",
            "sql_dialect": "mysql"
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "sql" in data


def test_generate_sql_with_sqlserver_dialect(mock_sql_generator_service):
    """测试SQL Server方言"""
    mock_result = SQLGenerationResult(
        sql="SELECT TOP 10 * FROM products;",
        explanation="查询前10个产品",
        estimated_rows=10,
        execution_plan="索引扫描",
        confidence=0.92,
        generation_time=1.3,
        semantic_context_used={},
        validation_result={"is_valid": True}
    )
    mock_sql_generator_service.generate_sql = AsyncMock(return_value=mock_result)
    
    response = client.post(
        "/api/sql-generator/generate",
        json={
            "user_question": "查询产品",
            "sql_dialect": "sqlserver",
            "max_rows": 10
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "TOP" in data["sql"]


def test_generate_sql_error(mock_sql_generator_service):
    """测试SQL生成错误"""
    mock_sql_generator_service.generate_sql = AsyncMock(side_effect=Exception("生成失败"))
    
    response = client.post(
        "/api/sql-generator/generate",
        json={
            "user_question": "查询产品",
            "sql_dialect": "mysql"
        }
    )
    
    assert response.status_code == 500
    assert "错误" in response.json()["detail"]


def test_generate_sql_invalid_request():
    """测试无效请求"""
    response = client.post(
        "/api/sql-generator/generate",
        json={
            "user_question": "",  # 空问题
            "sql_dialect": "mysql"
        }
    )
    
    assert response.status_code == 422  # Validation error


def test_batch_generate_sql_success(mock_sql_generator_service):
    """测试批量SQL生成成功"""
    mock_result = SQLGenerationResult(
        sql="SELECT * FROM products;",
        explanation="查询产品",
        estimated_rows=100,
        execution_plan="索引扫描",
        confidence=0.9,
        generation_time=1.0,
        semantic_context_used={},
        validation_result={"is_valid": True}
    )
    mock_sql_generator_service.generate_sql = AsyncMock(return_value=mock_result)
    
    response = client.post(
        "/api/sql-generator/generate/batch",
        json={
            "requests": [
                {
                    "user_question": "查询产品",
                    "sql_dialect": "mysql"
                },
                {
                    "user_question": "查询订单",
                    "sql_dialect": "mysql"
                }
            ]
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert len(data["results"]) == 2
    assert data["success_count"] == 2
    assert data["error_count"] == 0


def test_batch_generate_sql_partial_failure(mock_sql_generator_service):
    """测试批量SQL生成部分失败"""
    # 第一个请求成功，第二个失败
    mock_result = SQLGenerationResult(
        sql="SELECT * FROM products;",
        explanation="查询产品",
        estimated_rows=100,
        execution_plan="索引扫描",
        confidence=0.9,
        generation_time=1.0,
        semantic_context_used={},
        validation_result={"is_valid": True}
    )
    
    call_count = [0]
    async def mock_generate(*args, **kwargs):
        call_count[0] += 1
        if call_count[0] == 1:
            return mock_result
        else:
            raise Exception("生成失败")
    
    mock_sql_generator_service.generate_sql = mock_generate
    
    response = client.post(
        "/api/sql-generator/generate/batch",
        json={
            "requests": [
                {"user_question": "查询产品", "sql_dialect": "mysql"},
                {"user_question": "查询订单", "sql_dialect": "mysql"}
            ]
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert len(data["results"]) == 2
    assert data["success_count"] == 1
    assert data["error_count"] == 1


def test_batch_generate_sql_too_many_requests():
    """测试批量请求数量超限"""
    response = client.post(
        "/api/sql-generator/generate/batch",
        json={
            "requests": [
                {"user_question": f"查询{i}", "sql_dialect": "mysql"}
                for i in range(11)  # 超过10个
            ]
        }
    )
    
    assert response.status_code == 422  # Validation error


def test_validate_sql_success(mock_sql_generator_service):
    """测试SQL验证成功"""
    mock_validation = Mock(
        is_valid=True,
        security_level=Mock(value="safe"),
        violations=[],
        complexity=Mock(
            complexity_score=30.0,
            estimated_cost="LOW",
            table_count=1,
            join_count=0
        )
    )
    mock_sql_generator_service.sql_validator.validate_sql = Mock(return_value=mock_validation)
    
    response = client.post(
        "/api/sql-generator/validate",
        params={"sql": "SELECT * FROM products LIMIT 10;"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["is_valid"] is True
    assert data["security_level"] == "safe"
    assert len(data["violations"]) == 0


def test_validate_sql_with_violations(mock_sql_generator_service):
    """测试SQL验证有违规"""
    mock_violation = Mock(
        level=Mock(value="warning"),
        type="DANGEROUS_KEYWORD",
        message="检测到危险关键词"
    )
    mock_validation = Mock(
        is_valid=True,
        security_level=Mock(value="warning"),
        violations=[mock_violation],
        complexity=Mock(
            complexity_score=50.0,
            estimated_cost="MEDIUM",
            table_count=2,
            join_count=1
        )
    )
    mock_sql_generator_service.sql_validator.validate_sql = Mock(return_value=mock_validation)
    
    response = client.post(
        "/api/sql-generator/validate",
        params={"sql": "SELECT * FROM products WHERE name LIKE '%test%';"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["is_valid"] is True
    assert data["security_level"] == "warning"
    assert len(data["violations"]) == 1


def test_validate_sql_invalid(mock_sql_generator_service):
    """测试SQL验证失败"""
    mock_violation = Mock(
        level=Mock(value="blocked"),
        type="SQL_INJECTION",
        message="检测到SQL注入"
    )
    mock_validation = Mock(
        is_valid=False,
        security_level=Mock(value="blocked"),
        violations=[mock_violation],
        complexity=Mock(
            complexity_score=0.0,
            estimated_cost="UNKNOWN",
            table_count=0,
            join_count=0
        )
    )
    mock_sql_generator_service.sql_validator.validate_sql = Mock(return_value=mock_validation)
    
    response = client.post(
        "/api/sql-generator/validate",
        params={"sql": "SELECT * FROM products WHERE 1=1; DROP TABLE products;"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["is_valid"] is False
    assert data["security_level"] == "blocked"


def test_get_generation_statistics(mock_sql_generator_service):
    """测试获取生成统计"""
    mock_sql_generator_service.get_generation_statistics = Mock(return_value={
        "total_generations": 100,
        "successful_generations": 98,
        "failed_generations": 2,
        "success_rate": 0.98,
        "average_generation_time": 1.5,
        "average_confidence": 0.92,
        "syntax_correctness_rate": 0.98,
        "semantic_accuracy_rate": 0.95
    })
    
    response = client.get("/api/sql-generator/statistics")
    
    assert response.status_code == 200
    data = response.json()
    assert data["total_generations"] == 100
    assert data["success_rate"] == 0.98
    assert data["average_generation_time"] == 1.5


def test_health_check_healthy(mock_sql_generator_service):
    """测试健康检查（健康）"""
    mock_sql_generator_service.get_generation_statistics = Mock(return_value={
        "total_generations": 100,
        "success_rate": 0.98,
        "average_generation_time": 1.5
    })
    mock_sql_generator_service.ai_service = Mock()  # AI服务可用
    
    response = client.get("/api/sql-generator/health")
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "sql_generator"
    assert "statistics" in data
    assert "dependencies" in data


def test_health_check_unhealthy(mock_sql_generator_service):
    """测试健康检查（不健康）"""
    mock_sql_generator_service.get_generation_statistics = Mock(side_effect=Exception("服务错误"))
    
    response = client.get("/api/sql-generator/health")
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "unhealthy"
    assert "error" in data


def test_generate_sql_with_all_parameters(mock_sql_generator_service):
    """测试使用所有参数的SQL生成"""
    mock_result = SQLGenerationResult(
        sql="SELECT * FROM products WHERE category_id = 1 LIMIT 100;",
        explanation="查询特定类别的产品",
        estimated_rows=100,
        execution_plan="索引扫描 + 过滤",
        confidence=0.93,
        generation_time=1.8,
        semantic_context_used={
            "modules_used": ["table_structure", "dictionary", "knowledge_base"],
            "total_tokens_used": 2000
        },
        validation_result={
            "is_valid": True,
            "security_level": "safe",
            "violations": [],
            "complexity": {"score": 40.0, "estimated_cost": "MEDIUM"}
        }
    )
    mock_sql_generator_service.generate_sql = AsyncMock(return_value=mock_result)
    
    response = client.post(
        "/api/sql-generator/generate",
        json={
            "user_question": "查询电子产品类别的所有产品",
            "table_ids": ["tbl_products", "tbl_categories"],
            "data_source_id": "ds_001",
            "sql_dialect": "mysql",
            "include_explanation": True,
            "max_rows": 100
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["sql"] != ""
    assert data["explanation"] != ""
    assert data["confidence"] > 0.9
    assert "semantic_context_used" in data


def test_generate_sql_postgresql_dialect(mock_sql_generator_service):
    """测试PostgreSQL方言"""
    mock_result = SQLGenerationResult(
        sql='SELECT * FROM "products" LIMIT 10;',
        explanation="查询产品",
        estimated_rows=10,
        execution_plan="索引扫描",
        confidence=0.91,
        generation_time=1.4,
        semantic_context_used={},
        validation_result={"is_valid": True}
    )
    mock_sql_generator_service.generate_sql = AsyncMock(return_value=mock_result)
    
    response = client.post(
        "/api/sql-generator/generate",
        json={
            "user_question": "查询产品",
            "sql_dialect": "postgresql",
            "max_rows": 10
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert '"products"' in data["sql"] or "products" in data["sql"]


def test_validate_sql_error(mock_sql_generator_service):
    """测试SQL验证错误"""
    mock_sql_generator_service.sql_validator.validate_sql = Mock(side_effect=Exception("验证失败"))
    
    response = client.post(
        "/api/sql-generator/validate",
        params={"sql": "SELECT * FROM products;"}
    )
    
    assert response.status_code == 500


def test_batch_generate_sql_empty_requests():
    """测试批量请求为空"""
    response = client.post(
        "/api/sql-generator/generate/batch",
        json={"requests": []}
    )
    
    assert response.status_code == 422  # Validation error
