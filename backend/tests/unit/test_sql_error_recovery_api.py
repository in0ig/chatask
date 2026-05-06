"""
SQL错误恢复API测试

测试SQL错误恢复API的各个端点功能。
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, AsyncMock
import json
from datetime import datetime

from src.main import app
from src.services.sql_error_classifier import SQLErrorType, RetryStrategy


class TestSQLErrorRecoveryAPI:
    """SQL错误恢复API测试类"""
    
    def setup_method(self):
        """测试前置设置"""
        self.client = TestClient(app)
    
    def test_classify_sql_error_endpoint(self):
        """测试SQL错误分类端点"""
        response = self.client.post(
            "/api/sql-error-recovery/classify",
            params={
                "error_message": "Unknown column 'user_name' in 'field list'",
                "sql_statement": "SELECT user_name FROM users",
                "session_id": "test_session"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert data["message"] == "错误分类成功"
        assert "error_type" in data["data"]
        assert "confidence" in data["data"]
        assert "retry_strategy" in data["data"]
    
    def test_classify_syntax_error(self):
        """测试语法错误分类"""
        response = self.client.post(
            "/api/sql-error-recovery/classify",
            params={
                "error_message": "You have an error in your SQL syntax",
                "sql_statement": "SELECT * FROM users WHRE id = 1"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["data"]["error_type"] == SQLErrorType.SYNTAX_ERROR.value
        assert data["data"]["retry_strategy"] == RetryStrategy.REGENERATE_SQL.value
        assert data["data"]["confidence"] >= 0.9
    
    def test_classify_field_not_exists_error(self):
        """测试字段不存在错误分类"""
        response = self.client.post(
            "/api/sql-error-recovery/classify",
            params={
                "error_message": "Unknown column 'invalid_field' in 'field list'",
                "sql_statement": "SELECT invalid_field FROM users"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["data"]["error_type"] == SQLErrorType.FIELD_NOT_EXISTS.value
        assert "invalid_field" in data["data"]["suggested_fields"]
    
    def test_classify_table_not_exists_error(self):
        """测试表不存在错误分类"""
        response = self.client.post(
            "/api/sql-error-recovery/classify",
            params={
                "error_message": "Table 'test.invalid_table' doesn't exist",
                "sql_statement": "SELECT * FROM invalid_table"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["data"]["error_type"] == SQLErrorType.TABLE_NOT_EXISTS.value
        assert data["data"]["retry_strategy"] == RetryStrategy.CLARIFY_INTENT.value
    
    def test_classify_permission_error(self):
        """测试权限错误分类"""
        response = self.client.post(
            "/api/sql-error-recovery/classify",
            params={
                "error_message": "Access denied for user 'test'@'localhost'",
                "sql_statement": "SELECT * FROM sensitive_table"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["data"]["error_type"] == SQLErrorType.PERMISSION_ERROR.value
        assert data["data"]["retry_strategy"] == RetryStrategy.NO_RETRY.value
    
    def test_classify_connection_error(self):
        """测试连接错误分类"""
        response = self.client.post(
            "/api/sql-error-recovery/classify",
            params={
                "error_message": "Can't connect to MySQL server on 'localhost'",
                "sql_statement": "SELECT 1"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["data"]["error_type"] == SQLErrorType.CONNECTION_ERROR.value
        assert data["data"]["retry_strategy"] == RetryStrategy.BACKOFF_RETRY.value
    
    @patch('backend.src.api.sql_error_recovery_api.sql_error_recovery_service')
    def test_recover_from_sql_error_endpoint(self, mock_service):
        """测试SQL错误恢复端点"""
        # 模拟服务返回
        mock_service.handle_sql_error = AsyncMock(return_value={
            "success": True,
            "result": "recovery_result",
            "error_info": {"error_type": "syntax_error"},
            "feedback": {"feedback_for_ai": "test feedback"},
            "retry_statistics": {"total_retries": 1}
        })
        
        response = self.client.post(
            "/api/sql-error-recovery/recover",
            params={
                "error_message": "Syntax error",
                "sql_statement": "SELECT * FROM",
                "session_id": "test_session",
                "enable_retry": True
            },
            json={"context": {"original_question": "测试问题"}}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert "error_info" in data["data"]
        assert "feedback" in data["data"]
    
    def test_generate_error_feedback_endpoint(self):
        """测试错误反馈生成端点"""
        response = self.client.post(
            "/api/sql-error-recovery/feedback",
            params={
                "error_message": "Unknown column 'test_field'",
                "sql_statement": "SELECT test_field FROM users",
                "session_id": "test_session",
                "original_question": "查询测试字段"
            },
            json={"context": {"available_fields": ["id", "name", "email"]}}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert data["message"] == "错误反馈生成成功"
        assert "feedback_for_ai" in data["data"]
        assert "error_type" in data["data"]
    
    def test_get_error_statistics_global(self):
        """测试获取全局错误统计"""
        response = self.client.get("/api/sql-error-recovery/statistics")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert data["message"] == "全局统计信息获取成功"
        assert "classifier_stats" in data["data"]
        assert "total_sessions" in data["data"]
    
    def test_get_error_statistics_session(self):
        """测试获取会话错误统计"""
        response = self.client.get(
            "/api/sql-error-recovery/statistics",
            params={"session_id": "test_session"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert data["message"] == "会话统计信息获取成功"
        assert "session_id" in data["data"]
        assert "retry_statistics" in data["data"]
    
    def test_learn_from_error_endpoint(self):
        """测试从错误中学习端点"""
        response = self.client.post(
            "/api/sql-error-recovery/learn",
            params={
                "error_message": "Test error for learning",
                "correct_classification": SQLErrorType.SYNTAX_ERROR.value
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert data["message"] == "学习任务已提交"
        assert data["data"]["correct_classification"] == SQLErrorType.SYNTAX_ERROR.value
    
    def test_learn_from_error_invalid_classification(self):
        """测试无效分类的学习请求"""
        response = self.client.post(
            "/api/sql-error-recovery/learn",
            params={
                "error_message": "Test error",
                "correct_classification": "invalid_type"
            }
        )
        
        assert response.status_code == 400
        assert "无效的错误分类" in response.json()["detail"]
    
    def test_get_error_types_endpoint(self):
        """测试获取错误类型列表端点"""
        response = self.client.get("/api/sql-error-recovery/error-types")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert data["message"] == "错误类型列表获取成功"
        assert "error_types" in data["data"]
        
        error_types = data["data"]["error_types"]
        assert len(error_types) > 0
        
        # 检查错误类型结构
        for error_type in error_types:
            assert "value" in error_type
            assert "name" in error_type
            assert "description" in error_type
    
    def test_get_retry_strategies_endpoint(self):
        """测试获取重试策略列表端点"""
        response = self.client.get("/api/sql-error-recovery/retry-strategies")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert data["message"] == "重试策略列表获取成功"
        assert "retry_strategies" in data["data"]
        
        strategies = data["data"]["retry_strategies"]
        assert len(strategies) > 0
        
        # 检查重试策略结构
        for strategy in strategies:
            assert "value" in strategy
            assert "name" in strategy
            assert "description" in strategy
    
    def test_health_check_endpoint(self):
        """测试健康检查端点"""
        response = self.client.get("/api/sql-error-recovery/health")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert data["message"] == "SQL错误恢复服务运行正常"
        assert "service_status" in data["data"]
        assert data["data"]["service_status"] == "healthy"
        assert "timestamp" in data["data"]
        assert "statistics" in data["data"]
    
    def test_error_handling_invalid_request(self):
        """测试无效请求的错误处理"""
        # 测试缺少必需参数的请求
        response = self.client.post("/api/sql-error-recovery/classify")
        
        assert response.status_code == 422  # FastAPI validation error
    
    @patch('backend.src.api.sql_error_recovery_api.sql_error_recovery_service')
    def test_service_error_handling(self, mock_service):
        """测试服务错误处理"""
        # 模拟服务抛出异常
        mock_service.classifier.classify_error.side_effect = Exception("Service error")
        
        response = self.client.post(
            "/api/sql-error-recovery/classify",
            params={
                "error_message": "Test error",
                "sql_statement": "SELECT * FROM test"
            }
        )
        
        assert response.status_code == 500
        assert "错误分类失败" in response.json()["detail"]


class TestAPIResponseFormats:
    """API响应格式测试类"""
    
    def setup_method(self):
        """测试前置设置"""
        self.client = TestClient(app)
    
    def test_classification_response_format(self):
        """测试分类响应格式"""
        response = self.client.post(
            "/api/sql-error-recovery/classify",
            params={
                "error_message": "Test error",
                "sql_statement": "SELECT * FROM test"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # 检查基本响应结构
        assert "success" in data
        assert "message" in data
        assert "data" in data
        
        # 检查数据字段
        result_data = data["data"]
        required_fields = [
            "error_type", "error_message", "confidence", 
            "retry_strategy", "suggested_fields", "suggested_tables",
            "error_location", "timestamp"
        ]
        
        for field in required_fields:
            assert field in result_data
    
    def test_feedback_response_format(self):
        """测试反馈响应格式"""
        response = self.client.post(
            "/api/sql-error-recovery/feedback",
            params={
                "error_message": "Test error",
                "sql_statement": "SELECT * FROM test",
                "session_id": "test_session",
                "original_question": "测试问题"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # 检查反馈响应结构
        result_data = data["data"]
        required_fields = [
            "feedback_for_ai", "error_type", "error_message",
            "confidence", "timestamp"
        ]
        
        for field in required_fields:
            assert field in result_data
    
    def test_statistics_response_format(self):
        """测试统计响应格式"""
        response = self.client.get("/api/sql-error-recovery/statistics")
        
        assert response.status_code == 200
        data = response.json()
        
        # 检查统计响应结构
        result_data = data["data"]
        assert "classifier_stats" in result_data
        assert "total_sessions" in result_data


if __name__ == "__main__":
    pytest.main([__file__])