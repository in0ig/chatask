"""
SQL安全校验器单元测试
"""

import pytest
import sqlparse
from unittest.mock import Mock, patch
from src.services.sql_security_validator import (
    SQLSecurityValidator, SQLSecurityService, SecurityLevel, SQLOperation,
    SecurityViolation, TableReference, FieldReference, QueryComplexity
)


class TestSQLSecurityValidator:
    """SQL安全校验器测试"""
    
    def setup_method(self):
        """测试前置设置"""
        self.validator = SQLSecurityValidator()
    
    def test_detect_select_operation(self):
        """测试检测SELECT操作"""
        sql = "SELECT * FROM users"
        parsed = sqlparse.parse(sql)[0]
        operation = self.validator._detect_operation(parsed)
        assert operation == SQLOperation.SELECT
    
    def test_detect_dangerous_operation(self):
        """测试检测危险操作"""
        sql = "DROP TABLE users"
        parsed = sqlparse.parse(sql)[0]
        operation = self.validator._detect_operation(parsed)
        assert operation == SQLOperation.DROP
    
    def test_check_sql_injection_patterns(self):
        """测试SQL注入模式检测"""
        # 测试OR 1=1注入
        sql = "SELECT * FROM users WHERE id = 1 OR 1=1"
        violations = self.validator._check_sql_injection(sql)
        assert len(violations) > 0
        assert any(v.type == "SQL_INJECTION" for v in violations)
        
        # 测试UNION注入
        sql = "SELECT * FROM users UNION SELECT * FROM admin"
        violations = self.validator._check_sql_injection(sql)
        assert len(violations) > 0
        
        # 测试注释注入
        sql = "SELECT * FROM users -- WHERE id = 1"
        violations = self.validator._check_sql_injection(sql)
        assert len(violations) > 0
    
    def test_safe_sql_no_injection(self):
        """测试安全SQL无注入检测"""
        sql = "SELECT id, name FROM users WHERE status = 'active'"
        violations = self.validator._check_sql_injection(sql)
        injection_violations = [v for v in violations if v.type == "SQL_INJECTION"]
        assert len(injection_violations) == 0
    
    def test_dangerous_operations_detection(self):
        """测试危险操作检测"""
        # 测试DROP操作
        sql = "DROP TABLE users"
        parsed = sqlparse.parse(sql)[0]
        operation = self.validator._detect_operation(parsed)
        violations = self.validator._check_dangerous_operations(parsed, operation)
        
        blocked_violations = [v for v in violations if v.level == SecurityLevel.BLOCKED]
        assert len(blocked_violations) > 0
        
        # 测试DELETE操作
        sql = "DELETE FROM users WHERE id = 1"
        parsed = sqlparse.parse(sql)[0]
        operation = self.validator._detect_operation(parsed)
        violations = self.validator._check_dangerous_operations(parsed, operation)
        
        blocked_violations = [v for v in violations if v.level == SecurityLevel.BLOCKED]
        assert len(blocked_violations) > 0
    
    def test_complexity_analysis(self):
        """测试复杂度分析"""
        # 简单查询
        sql = "SELECT * FROM users"
        parsed = sqlparse.parse(sql)[0]
        complexity = self.validator._analyze_complexity(parsed)
        assert complexity.complexity_score < 20
        assert complexity.estimated_cost == "LOW"
        
        # 复杂查询
        sql = """
        SELECT u.id, u.name, COUNT(o.id) as order_count
        FROM users u
        LEFT JOIN orders o ON u.id = o.user_id
        LEFT JOIN products p ON o.product_id = p.id
        WHERE u.status = 'active' AND o.created_at > '2023-01-01'
        GROUP BY u.id, u.name
        HAVING COUNT(o.id) > 5
        """
        parsed = sqlparse.parse(sql)[0]
        complexity = self.validator._analyze_complexity(parsed)
        assert complexity.complexity_score > 20
        assert complexity.join_count >= 2
    
    def test_table_existence_validation(self):
        """测试表存在性验证"""
        available_tables = {
            "users": ["id", "name", "email"],
            "orders": ["id", "user_id", "amount"]
        }
        
        # 存在的表
        table_refs = [TableReference(table_name="users")]
        violations = self.validator._validate_table_existence(table_refs, available_tables)
        assert len(violations) == 0
        
        # 不存在的表
        table_refs = [TableReference(table_name="nonexistent")]
        violations = self.validator._validate_table_existence(table_refs, available_tables)
        assert len(violations) > 0
        assert violations[0].type == "TABLE_NOT_FOUND"
    
    def test_field_existence_validation(self):
        """测试字段存在性验证"""
        available_tables = {
            "users": ["id", "name", "email"],
            "orders": ["id", "user_id", "amount"]
        }
        
        table_refs = [TableReference(table_name="users")]
        
        # 存在的字段
        field_refs = [FieldReference(field_name="name", table_name="users")]
        violations = self.validator._validate_field_existence(field_refs, table_refs, available_tables)
        assert len(violations) == 0
        
        # 不存在的字段
        field_refs = [FieldReference(field_name="nonexistent", table_name="users")]
        violations = self.validator._validate_field_existence(field_refs, table_refs, available_tables)
        assert len(violations) > 0
        assert violations[0].type == "FIELD_NOT_FOUND"
    
    def test_complexity_limits_check(self):
        """测试复杂度限制检查"""
        # 超过表数量限制
        complexity = QueryComplexity(
            table_count=15,  # 超过默认限制10
            join_count=2,
            subquery_count=1,
            function_count=1,
            condition_count=2,
            complexity_score=50.0,
            estimated_cost="MEDIUM"
        )
        
        violations = self.validator._check_complexity_limits(complexity)
        table_violations = [v for v in violations if "表数量过多" in v.message]
        assert len(table_violations) > 0
        
        # 超过复杂度分数限制
        complexity = QueryComplexity(
            table_count=5,
            join_count=2,
            subquery_count=1,
            function_count=1,
            condition_count=2,
            complexity_score=150.0,  # 超过默认限制100
            estimated_cost="VERY_HIGH"
        )
        
        violations = self.validator._check_complexity_limits(complexity)
        complexity_violations = [v for v in violations if "复杂度过高" in v.message]
        assert len(complexity_violations) > 0
    
    def test_security_level_determination(self):
        """测试安全级别确定"""
        # 无违规 - 安全
        violations = []
        level = self.validator._determine_security_level(violations)
        assert level == SecurityLevel.SAFE
        
        # 警告级别违规
        violations = [SecurityViolation(SecurityLevel.WARNING, "TEST", "测试警告")]
        level = self.validator._determine_security_level(violations)
        assert level == SecurityLevel.WARNING
        
        # 危险级别违规
        violations = [SecurityViolation(SecurityLevel.DANGEROUS, "TEST", "测试危险")]
        level = self.validator._determine_security_level(violations)
        assert level == SecurityLevel.DANGEROUS
        
        # 阻止级别违规
        violations = [SecurityViolation(SecurityLevel.BLOCKED, "TEST", "测试阻止")]
        level = self.validator._determine_security_level(violations)
        assert level == SecurityLevel.BLOCKED
    
    def test_sql_sanitization(self):
        """测试SQL清理"""
        # 包含注释的SQL
        sql = "SELECT * FROM users -- this is a comment"
        sanitized = self.validator._sanitize_sql(sql)
        assert "--" not in sanitized
        
        # 包含多行注释的SQL
        sql = "SELECT * FROM users /* multi line comment */"
        sanitized = self.validator._sanitize_sql(sql)
        assert "/*" not in sanitized and "*/" not in sanitized
        
        # 包含多余空白的SQL
        sql = "SELECT   *   FROM    users   "
        sanitized = self.validator._sanitize_sql(sql)
        assert "SELECT * FROM users" == sanitized
    
    def test_validate_sql_integration(self):
        """测试SQL验证集成"""
        # 安全的SELECT查询
        sql = "SELECT id, name FROM users WHERE status = 'active'"
        available_tables = {"users": ["id", "name", "status"]}
        
        result = self.validator.validate_sql(sql, available_tables)
        
        assert result.is_valid is True
        assert result.security_level == SecurityLevel.SAFE
        assert result.operation == SQLOperation.SELECT
        assert len(result.violations) == 0
        
        # 危险的DROP查询
        sql = "DROP TABLE users"
        result = self.validator.validate_sql(sql)
        
        assert result.is_valid is False
        assert result.security_level == SecurityLevel.BLOCKED
        assert result.operation == SQLOperation.DROP
        assert len(result.violations) > 0
    
    def test_validate_sql_with_nonexistent_table(self):
        """测试验证包含不存在表的SQL"""
        sql = "SELECT * FROM nonexistent_table"
        available_tables = {"users": ["id", "name"]}
        
        result = self.validator.validate_sql(sql, available_tables)
        
        assert result.is_valid is False
        assert result.security_level == SecurityLevel.BLOCKED
        table_violations = [v for v in result.violations if v.type == "TABLE_NOT_FOUND"]
        assert len(table_violations) > 0


class TestSQLSecurityService:
    """SQL安全服务测试"""
    
    def setup_method(self):
        """测试前置设置"""
        self.service = SQLSecurityService()
    
    @pytest.mark.asyncio
    async def test_validate_and_secure_sql(self):
        """测试验证和保护SQL"""
        sql = "SELECT id, name FROM users"
        
        with patch.object(self.service, '_get_available_tables') as mock_get_tables:
            mock_get_tables.return_value = {"users": ["id", "name", "email"]}
            
            result = await self.service.validate_and_secure_sql(sql, data_source_id=1)
            
            assert result.is_valid is True
            assert result.security_level == SecurityLevel.SAFE
            assert result.operation == SQLOperation.SELECT
    
    @pytest.mark.asyncio
    async def test_validate_dangerous_sql(self):
        """测试验证危险SQL"""
        sql = "DROP TABLE users"
        
        result = await self.service.validate_and_secure_sql(sql)
        
        assert result.is_valid is False
        assert result.security_level == SecurityLevel.BLOCKED
        assert result.operation == SQLOperation.DROP
    
    @pytest.mark.asyncio
    async def test_validate_sql_with_injection(self):
        """测试验证包含注入的SQL"""
        sql = "SELECT * FROM users WHERE id = 1 OR 1=1"
        
        result = await self.service.validate_and_secure_sql(sql)
        
        assert result.is_valid is False
        assert result.security_level == SecurityLevel.BLOCKED
        injection_violations = [v for v in result.violations if v.type == "SQL_INJECTION"]
        assert len(injection_violations) > 0
    
    @pytest.mark.asyncio
    async def test_get_available_tables_mock(self):
        """测试获取可用表（模拟数据）"""
        tables = await self.service._get_available_tables(1)
        
        assert isinstance(tables, dict)
        assert "users" in tables
        assert "orders" in tables
        assert "products" in tables
        assert isinstance(tables["users"], list)
    
    def test_get_security_report(self):
        """测试生成安全报告"""
        # 创建模拟验证结果
        from src.services.sql_security_validator import ValidationResult
        
        result = ValidationResult(
            is_valid=True,
            security_level=SecurityLevel.SAFE,
            operation=SQLOperation.SELECT,
            violations=[],
            table_references=[TableReference(table_name="users")],
            field_references=[FieldReference(field_name="id", table_name="users")],
            complexity=QueryComplexity(1, 0, 0, 0, 1, 5.0, "LOW"),
            sanitized_sql="SELECT id FROM users"
        )
        
        report = self.service.get_security_report(result)
        
        assert "summary" in report
        assert "violations" in report
        assert "references" in report
        assert "complexity" in report
        assert report["summary"]["is_valid"] is True
        assert report["summary"]["security_level"] == "safe"
        assert len(report["references"]["tables"]) == 1
        assert len(report["references"]["fields"]) == 1
    
    def test_caching_mechanism(self):
        """测试缓存机制"""
        # 导入ValidationResult
        from src.services.sql_security_validator import ValidationResult
        
        # 第一次调用应该计算结果
        sql = "SELECT * FROM users"
        cache_key = f"{hash(sql)}_None"
        
        # 确保缓存为空
        self.service.validation_cache.clear()
        assert cache_key not in self.service.validation_cache
        
        # 手动添加到缓存进行测试
        mock_result = ValidationResult(
            is_valid=True,
            security_level=SecurityLevel.SAFE,
            operation=SQLOperation.SELECT,
            violations=[],
            table_references=[],
            field_references=[],
            complexity=QueryComplexity(1, 0, 0, 0, 1, 5.0, "LOW")
        )
        
        self.service.validation_cache[cache_key] = mock_result
        
        # 验证缓存存在
        assert cache_key in self.service.validation_cache
        assert self.service.validation_cache[cache_key] == mock_result