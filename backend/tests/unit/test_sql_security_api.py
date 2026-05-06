"""
SQL安全校验API单元测试
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, AsyncMock
from src.main import app
from src.services.sql_security_validator import (
    ValidationResult, SecurityLevel, SQLOperation, QueryComplexity,
    SecurityViolation, TableReference, FieldReference
)

client = TestClient(app)


class TestSQLSecurityAPI:
    """SQL安全校验API测试"""
    
    def setup_method(self):
        """测试前置设置"""
        self.base_url = "/api/sql-security"
    
    @patch('src.api.sql_security_api.sql_security_service.validate_and_secure_sql')
    def test_validate_sql_success(self, mock_validate):
        """测试SQL验证成功"""
        # 模拟验证结果
        mock_result = ValidationResult(
            is_valid=True,
            security_level=SecurityLevel.SAFE,
            operation=SQLOperation.SELECT,
            violations=[],
            table_references=[TableReference(table_name="users")],
            field_references=[FieldReference(field_name="id", table_name="users")],
            complexity=QueryComplexity(1, 0, 0, 0, 1, 5.0, "LOW"),
            sanitized_sql="SELECT id FROM users"
        )
        mock_validate.return_value = mock_result
        
        # 发送请求
        response = client.post(
            f"{self.base_url}/validate",
            params={"sql_query": "SELECT id FROM users", "data_source_id": 1}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["message"] == "SQL验证完成"
        assert "validation_result" in data["data"]
        assert "security_report" in data["data"]
        assert data["data"]["validation_result"]["is_valid"] is True
        assert data["data"]["validation_result"]["security_level"] == "safe"
    
    def test_validate_sql_empty_query(self):
        """测试验证空SQL查询"""
        response = client.post(
            f"{self.base_url}/validate",
            params={"sql_query": ""}
        )
        
        assert response.status_code == 400
        assert "SQL查询不能为空" in response.json()["detail"]
    
    @patch('src.api.sql_security_api.sql_security_service.validate_and_secure_sql')
    def test_validate_sql_dangerous(self, mock_validate):
        """测试验证危险SQL"""
        # 模拟危险SQL验证结果
        mock_result = ValidationResult(
            is_valid=False,
            security_level=SecurityLevel.BLOCKED,
            operation=SQLOperation.DROP,
            violations=[
                SecurityViolation(
                    level=SecurityLevel.BLOCKED,
                    type="DANGEROUS_OPERATION",
                    message="危险操作被禁止: DROP"
                )
            ],
            table_references=[],
            field_references=[],
            complexity=QueryComplexity(1, 0, 0, 0, 1, 10.0, "LOW")
        )
        mock_validate.return_value = mock_result
        
        response = client.post(
            f"{self.base_url}/validate",
            params={"sql_query": "DROP TABLE users"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["validation_result"]["is_valid"] is False
        assert data["data"]["validation_result"]["security_level"] == "blocked"
        assert len(data["data"]["security_report"]["violations"]) > 0
    
    @patch('src.api.sql_security_api.sql_security_service.validate_and_secure_sql')
    def test_analyze_sql_complexity(self, mock_validate):
        """测试SQL复杂度分析"""
        mock_result = ValidationResult(
            is_valid=True,
            security_level=SecurityLevel.SAFE,
            operation=SQLOperation.SELECT,
            violations=[],
            table_references=[],
            field_references=[],
            complexity=QueryComplexity(3, 2, 1, 2, 5, 45.0, "MEDIUM")
        )
        mock_validate.return_value = mock_result
        
        response = client.post(
            f"{self.base_url}/analyze-complexity",
            params={"sql_query": "SELECT u.id, COUNT(o.id) FROM users u JOIN orders o ON u.id = o.user_id GROUP BY u.id"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["message"] == "SQL复杂度分析完成"
        assert "complexity" in data["data"]
        assert "recommendations" in data["data"]
        assert data["data"]["complexity"]["score"] == 45.0
        assert data["data"]["complexity"]["estimated_cost"] == "MEDIUM"
    
    def test_analyze_complexity_empty_query(self):
        """测试分析空查询复杂度"""
        response = client.post(
            f"{self.base_url}/analyze-complexity",
            params={"sql_query": ""}
        )
        
        assert response.status_code == 400
        assert "SQL查询不能为空" in response.json()["detail"]
    
    @patch('src.api.sql_security_api.sql_security_service.validate_and_secure_sql')
    def test_check_sql_injection(self, mock_validate):
        """测试SQL注入检查"""
        mock_result = ValidationResult(
            is_valid=False,
            security_level=SecurityLevel.BLOCKED,
            operation=SQLOperation.SELECT,
            violations=[
                SecurityViolation(
                    level=SecurityLevel.BLOCKED,
                    type="SQL_INJECTION",
                    message="检测到SQL注入模式: OR 1=1",
                    location="位置 25-32",
                    suggestion="请使用参数化查询避免SQL注入"
                )
            ],
            table_references=[],
            field_references=[],
            complexity=QueryComplexity(1, 0, 0, 0, 2, 10.0, "LOW"),
            sanitized_sql="SELECT * FROM users WHERE id = 1"
        )
        mock_validate.return_value = mock_result
        
        response = client.post(
            f"{self.base_url}/check-injection",
            params={"sql_query": "SELECT * FROM users WHERE id = 1 OR 1=1"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["message"] == "SQL注入检查完成"
        assert data["data"]["injection_risk"]["has_risk"] is True
        assert data["data"]["injection_risk"]["risk_level"] == "blocked"
        assert len(data["data"]["violations"]) > 0
        assert data["data"]["violations"][0]["type"] == "SQL_INJECTION"
    
    @patch('src.api.sql_security_api.sql_security_service.validate_and_secure_sql')
    def test_check_injection_safe_sql(self, mock_validate):
        """测试检查安全SQL无注入"""
        mock_result = ValidationResult(
            is_valid=True,
            security_level=SecurityLevel.SAFE,
            operation=SQLOperation.SELECT,
            violations=[],
            table_references=[],
            field_references=[],
            complexity=QueryComplexity(1, 0, 0, 0, 1, 5.0, "LOW"),
            sanitized_sql="SELECT * FROM users WHERE status = 'active'"
        )
        mock_validate.return_value = mock_result
        
        response = client.post(
            f"{self.base_url}/check-injection",
            params={"sql_query": "SELECT * FROM users WHERE status = 'active'"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["injection_risk"]["has_risk"] is False
        assert data["data"]["injection_risk"]["risk_level"] == "safe"
        assert len(data["data"]["violations"]) == 0
    
    @patch('src.api.sql_security_api.sql_security_service.validate_and_secure_sql')
    def test_validate_field_existence(self, mock_validate):
        """测试字段存在性验证"""
        mock_result = ValidationResult(
            is_valid=False,
            security_level=SecurityLevel.BLOCKED,
            operation=SQLOperation.SELECT,
            violations=[
                SecurityViolation(
                    level=SecurityLevel.BLOCKED,
                    type="FIELD_NOT_FOUND",
                    message="字段不存在: users.nonexistent_field",
                    suggestion="表 users 可用字段: id, name, email"
                )
            ],
            table_references=[TableReference(table_name="users")],
            field_references=[FieldReference(field_name="nonexistent_field", table_name="users")],
            complexity=QueryComplexity(1, 0, 0, 0, 1, 5.0, "LOW")
        )
        mock_validate.return_value = mock_result
        
        response = client.post(
            f"{self.base_url}/validate-fields",
            params={"sql_query": "SELECT nonexistent_field FROM users", "data_source_id": 1}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["message"] == "字段存在性验证完成"
        assert data["data"]["existence_check"]["all_exist"] is False
        assert data["data"]["existence_check"]["violation_count"] == 1
        assert len(data["data"]["violations"]) == 1
        assert data["data"]["violations"][0]["type"] == "FIELD_NOT_FOUND"
    
    def test_validate_fields_missing_data_source(self):
        """测试字段验证缺少数据源ID"""
        response = client.post(
            f"{self.base_url}/validate-fields",
            params={"sql_query": "SELECT * FROM users"}
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_get_security_config(self):
        """测试获取安全配置"""
        response = client.get(f"{self.base_url}/security-config")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["message"] == "获取安全配置成功"
        assert "limits" in data["data"]
        assert "dangerous_keywords" in data["data"]
        assert "allowed_operations" in data["data"]
        assert "blocked_operations" in data["data"]
        assert "warning_operations" in data["data"]
        
        # 验证配置内容
        assert "SELECT" in data["data"]["allowed_operations"]
        assert "DROP" in data["data"]["blocked_operations"]
        assert "INSERT" in data["data"]["warning_operations"]
    
    @patch('src.api.sql_security_api.sql_security_service.validate_and_secure_sql')
    def test_sanitize_sql(self, mock_validate):
        """测试SQL清理"""
        original_sql = "SELECT * FROM users -- comment"
        sanitized_sql = "SELECT * FROM users"
        
        mock_result = ValidationResult(
            is_valid=True,
            security_level=SecurityLevel.SAFE,
            operation=SQLOperation.SELECT,
            violations=[],
            table_references=[],
            field_references=[],
            complexity=QueryComplexity(1, 0, 0, 0, 1, 5.0, "LOW"),
            sanitized_sql=sanitized_sql
        )
        mock_validate.return_value = mock_result
        
        response = client.post(
            f"{self.base_url}/sanitize",
            params={"sql_query": original_sql}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["message"] == "SQL清理完成"
        assert data["data"]["original_sql"] == original_sql
        assert data["data"]["sanitized_sql"] == sanitized_sql
        assert data["data"]["security_level"] == "safe"
        assert data["data"]["changes_made"] is True
    
    @patch('src.api.sql_security_api.sql_security_service.validate_and_secure_sql')
    def test_sanitize_sql_no_changes(self, mock_validate):
        """测试SQL清理无变化"""
        clean_sql = "SELECT * FROM users"
        
        mock_result = ValidationResult(
            is_valid=True,
            security_level=SecurityLevel.SAFE,
            operation=SQLOperation.SELECT,
            violations=[],
            table_references=[],
            field_references=[],
            complexity=QueryComplexity(1, 0, 0, 0, 1, 5.0, "LOW"),
            sanitized_sql=clean_sql
        )
        mock_validate.return_value = mock_result
        
        response = client.post(
            f"{self.base_url}/sanitize",
            params={"sql_query": clean_sql}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["changes_made"] is False
    
    @patch('src.api.sql_security_api.sql_security_service.validate_and_secure_sql')
    def test_api_error_handling(self, mock_validate):
        """测试API错误处理"""
        # 模拟服务异常
        mock_validate.side_effect = Exception("服务内部错误")
        
        response = client.post(
            f"{self.base_url}/validate",
            params={"sql_query": "SELECT * FROM users"}
        )
        
        assert response.status_code == 500
        assert "SQL验证失败" in response.json()["detail"]
    
    def test_complexity_recommendations(self):
        """测试复杂度建议功能"""
        from src.api.sql_security_api import _get_complexity_recommendations
        from src.services.sql_security_validator import QueryComplexity
        
        # 简单查询
        simple_complexity = QueryComplexity(1, 0, 0, 0, 1, 5.0, "LOW")
        recommendations = _get_complexity_recommendations(simple_complexity)
        assert "查询复杂度在合理范围内" in recommendations
        
        # 复杂查询
        complex_complexity = QueryComplexity(8, 6, 3, 5, 10, 120.0, "VERY_HIGH")
        recommendations = _get_complexity_recommendations(complex_complexity)
        assert len(recommendations) > 1
        assert any("减少查询涉及的表数量" in rec for rec in recommendations)
        assert any("JOIN可能影响性能" in rec for rec in recommendations)
        assert any("使用JOIN替代子查询" in rec for rec in recommendations)
        assert any("查询成本很高" in rec for rec in recommendations)
    
    @patch('src.api.sql_security_api.sql_security_service.validate_and_secure_sql')
    def test_validate_sql_with_data_source(self, mock_validate):
        """测试带数据源的SQL验证"""
        mock_result = ValidationResult(
            is_valid=True,
            security_level=SecurityLevel.SAFE,
            operation=SQLOperation.SELECT,
            violations=[],
            table_references=[TableReference(table_name="users")],
            field_references=[FieldReference(field_name="id", table_name="users")],
            complexity=QueryComplexity(1, 0, 0, 0, 1, 5.0, "LOW"),
            sanitized_sql="SELECT id FROM users"
        )
        mock_validate.return_value = mock_result
        
        response = client.post(
            f"{self.base_url}/validate",
            params={"sql_query": "SELECT id FROM users", "data_source_id": 1}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        
        # 验证服务被正确调用
        mock_validate.assert_called_once_with(
            sql_query="SELECT id FROM users",
            data_source_id=1
        )
    
    @patch('src.api.sql_security_api.sql_security_service.validate_and_secure_sql')
    def test_validate_sql_without_data_source(self, mock_validate):
        """测试不带数据源的SQL验证"""
        mock_result = ValidationResult(
            is_valid=True,
            security_level=SecurityLevel.SAFE,
            operation=SQLOperation.SELECT,
            violations=[],
            table_references=[],
            field_references=[],
            complexity=QueryComplexity(1, 0, 0, 0, 1, 5.0, "LOW"),
            sanitized_sql="SELECT 1"
        )
        mock_validate.return_value = mock_result
        
        response = client.post(
            f"{self.base_url}/validate",
            params={"sql_query": "SELECT 1"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        
        # 验证服务被正确调用
        mock_validate.assert_called_once_with(
            sql_query="SELECT 1",
            data_source_id=None
        )