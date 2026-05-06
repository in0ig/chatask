"""
SQL错误分类器测试

测试SQL错误分类、重试策略和反馈生成功能。
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock

from src.services.sql_error_classifier import (
    SQLErrorClassifier,
    SQLErrorRetryHandler,
    ErrorFeedbackGenerator,
    SQLErrorRecoveryService,
    SQLErrorType,
    RetryStrategy,
    SQLError,
    ErrorPattern,
    RetryConfig
)


class TestSQLErrorClassifier:
    """SQL错误分类器测试类"""
    
    def setup_method(self):
        """测试前置设置"""
        self.classifier = SQLErrorClassifier()
    
    def test_classify_mysql_syntax_error(self):
        """测试MySQL语法错误分类"""
        error_message = "You have an error in your SQL syntax; check the manual"
        sql_statement = "SELECT * FROM users WHRE id = 1"
        
        result = self.classifier.classify_error(error_message, sql_statement)
        
        assert result.error_type == SQLErrorType.SYNTAX_ERROR
        assert result.confidence >= 0.9
        assert result.retry_strategy == RetryStrategy.REGENERATE_SQL
    
    def test_classify_field_not_exists_error(self):
        """测试字段不存在错误分类"""
        error_message = "Unknown column 'user_name' in 'field list'"
        sql_statement = "SELECT user_name FROM users"
        
        result = self.classifier.classify_error(error_message, sql_statement)
        
        assert result.error_type == SQLErrorType.FIELD_NOT_EXISTS
        assert result.confidence >= 0.9
        assert "user_name" in result.suggested_fields
        assert result.retry_strategy == RetryStrategy.REGENERATE_SQL
    
    def test_classify_table_not_exists_error(self):
        """测试表不存在错误分类"""
        error_message = "Table 'test.user_info' doesn't exist"
        sql_statement = "SELECT * FROM user_info"
        
        result = self.classifier.classify_error(error_message, sql_statement)
        
        assert result.error_type == SQLErrorType.TABLE_NOT_EXISTS
        assert result.confidence >= 0.9
        assert result.retry_strategy == RetryStrategy.CLARIFY_INTENT
    
    def test_classify_type_mismatch_error(self):
        """测试类型不匹配错误分类"""
        error_message = "Incorrect integer value: 'abc' for column 'age' at row 1"
        sql_statement = "INSERT INTO users (age) VALUES ('abc')"
        
        result = self.classifier.classify_error(error_message, sql_statement)
        
        assert result.error_type == SQLErrorType.TYPE_MISMATCH
        assert result.confidence >= 0.8
        assert result.retry_strategy == RetryStrategy.REGENERATE_SQL
    
    def test_classify_permission_error(self):
        """测试权限错误分类"""
        error_message = "Access denied for user 'test'@'localhost' to database 'prod'"
        sql_statement = "SELECT * FROM sensitive_data"
        
        result = self.classifier.classify_error(error_message, sql_statement)
        
        assert result.error_type == SQLErrorType.PERMISSION_ERROR
        assert result.retry_strategy == RetryStrategy.NO_RETRY
    
    def test_classify_connection_error(self):
        """测试连接错误分类"""
        error_message = "Can't connect to MySQL server on 'localhost'"
        sql_statement = "SELECT 1"
        
        result = self.classifier.classify_error(error_message, sql_statement)
        
        assert result.error_type == SQLErrorType.CONNECTION_ERROR
        assert result.retry_strategy == RetryStrategy.BACKOFF_RETRY
    
    def test_classify_by_keywords(self):
        """测试基于关键词的分类"""
        # 测试语法错误关键词
        error_message = "Syntax error near 'FROM'"
        result = self.classifier.classify_error(error_message, "SELECT * FROM")
        assert result.error_type == SQLErrorType.SYNTAX_ERROR
        
        # 测试字段错误关键词
        error_message = "Invalid column reference"
        result = self.classifier.classify_error(error_message, "SELECT invalid_col FROM users")
        assert result.error_type == SQLErrorType.FIELD_NOT_EXISTS
    
    def test_unknown_error_classification(self):
        """测试未知错误分类"""
        error_message = "Some unknown database error occurred"
        sql_statement = "SELECT * FROM users"
        
        result = self.classifier.classify_error(error_message, sql_statement)
        
        assert result.error_type == SQLErrorType.UNKNOWN_ERROR
        assert result.retry_strategy == RetryStrategy.NO_RETRY
        assert result.confidence == 0.0
    
    def test_error_history_management(self):
        """测试错误历史管理"""
        initial_count = len(self.classifier.error_history)
        
        # 添加一些错误
        for i in range(5):
            error_message = f"Test error {i}"
            self.classifier.classify_error(error_message, f"SELECT {i}")
        
        assert len(self.classifier.error_history) == initial_count + 5
    
    def test_error_statistics(self):
        """测试错误统计"""
        # 添加一些测试错误
        self.classifier.classify_error("Syntax error", "SELECT *")
        self.classifier.classify_error("Unknown column 'test'", "SELECT test")
        
        stats = self.classifier.get_error_statistics()
        
        assert "total_errors" in stats
        assert "error_counts" in stats
        assert stats["total_errors"] >= 2


class TestSQLErrorRetryHandler:
    """SQL错误重试处理器测试类"""
    
    def setup_method(self):
        """测试前置设置"""
        self.classifier = SQLErrorClassifier()
        self.retry_handler = SQLErrorRetryHandler(self.classifier)
    
    @pytest.mark.asyncio
    async def test_should_retry_logic(self):
        """测试重试逻辑判断"""
        # 创建一个可重试的错误
        sql_error = SQLError(
            error_type=SQLErrorType.SYNTAX_ERROR,
            original_error="Syntax error",
            error_message="SQL语法错误",
            sql_statement="SELECT *",
            retry_strategy=RetryStrategy.REGENERATE_SQL
        )
        
        # 第一次应该可以重试
        should_retry = self.retry_handler._should_retry(sql_error, "test_session")
        assert should_retry is True
        
        # 添加到历史记录
        self.retry_handler.retry_history["test_session"] = [sql_error] * 3
        
        # 超过最大重试次数后不应该重试
        should_retry = self.retry_handler._should_retry(sql_error, "test_session")
        assert should_retry is False
    
    @pytest.mark.asyncio
    async def test_no_retry_strategy(self):
        """测试不重试策略"""
        sql_error = SQLError(
            error_type=SQLErrorType.PERMISSION_ERROR,
            original_error="Access denied",
            error_message="权限不足",
            sql_statement="SELECT *",
            retry_strategy=RetryStrategy.NO_RETRY
        )
        
        should_retry = self.retry_handler._should_retry(sql_error, "test_session")
        assert should_retry is False
    
    @pytest.mark.asyncio
    async def test_handle_error_with_retry(self):
        """测试错误处理和重试"""
        # 创建模拟的重试回调
        retry_callback = AsyncMock(return_value=(True, "success"))
        
        success, result, sql_error = await self.retry_handler.handle_error_with_retry(
            error_message="Syntax error near 'FROM'",
            sql_statement="SELECT * FROM",
            session_id="test_session",
            retry_callback=retry_callback
        )
        
        assert sql_error.error_type == SQLErrorType.SYNTAX_ERROR
        # 注意：由于我们的重试逻辑需要回调函数，这里可能不会实际重试
    
    def test_retry_statistics(self):
        """测试重试统计"""
        session_id = "test_session"
        
        # 添加一些重试记录
        sql_error = SQLError(
            error_type=SQLErrorType.SYNTAX_ERROR,
            original_error="Test error",
            error_message="测试错误",
            sql_statement="SELECT *"
        )
        
        self.retry_handler.retry_history[session_id] = [sql_error, sql_error]
        
        stats = self.retry_handler.get_retry_statistics(session_id)
        
        assert stats["total_retries"] == 2
        assert "retry_counts" in stats
        assert stats["last_error_type"] == SQLErrorType.SYNTAX_ERROR.value


class TestErrorFeedbackGenerator:
    """错误反馈生成器测试类"""
    
    def setup_method(self):
        """测试前置设置"""
        self.classifier = SQLErrorClassifier()
        self.feedback_generator = ErrorFeedbackGenerator(self.classifier)
    
    def test_generate_feedback_for_field_error(self):
        """测试字段错误反馈生成"""
        sql_error = SQLError(
            error_type=SQLErrorType.FIELD_NOT_EXISTS,
            original_error="Unknown column 'user_name'",
            error_message="字段不存在",
            sql_statement="SELECT user_name FROM users",
            suggested_fields=["username", "user_id"]
        )
        
        context = {
            "session_id": "test_session",
            "original_question": "查询用户姓名",
            "available_fields": ["id", "username", "email"]
        }
        
        feedback = self.feedback_generator.generate_feedback_for_ai(sql_error, context)
        
        assert feedback.session_id == "test_session"
        assert feedback.original_question == "查询用户姓名"
        assert "字段不存在" in feedback.feedback_for_ai
        assert "username" in feedback.feedback_for_ai
    
    def test_generate_feedback_for_table_error(self):
        """测试表错误反馈生成"""
        sql_error = SQLError(
            error_type=SQLErrorType.TABLE_NOT_EXISTS,
            original_error="Table 'user_info' doesn't exist",
            error_message="表不存在",
            sql_statement="SELECT * FROM user_info",
            suggested_tables=["users", "user_profiles"]
        )
        
        context = {
            "session_id": "test_session",
            "original_question": "查询用户信息",
            "available_tables": ["users", "orders", "products"]
        }
        
        feedback = self.feedback_generator.generate_feedback_for_ai(sql_error, context)
        
        assert "表不存在" in feedback.feedback_for_ai
        assert "users" in feedback.feedback_for_ai
    
    def test_feedback_logging_format(self):
        """测试反馈日志格式"""
        sql_error = SQLError(
            error_type=SQLErrorType.SYNTAX_ERROR,
            original_error="Syntax error",
            error_message="语法错误",
            sql_statement="SELECT *"
        )
        
        context = {"session_id": "test_session", "original_question": "测试问题"}
        feedback = self.feedback_generator.generate_feedback_for_ai(sql_error, context)
        
        log_format = self.feedback_generator.format_feedback_for_logging(feedback)
        
        assert isinstance(log_format, str)
        assert "session_id" in log_format
        assert "error_type" in log_format


class TestSQLErrorRecoveryService:
    """SQL错误恢复服务测试类"""
    
    def setup_method(self):
        """测试前置设置"""
        self.recovery_service = SQLErrorRecoveryService()
    
    @pytest.mark.asyncio
    async def test_handle_sql_error_complete_flow(self):
        """测试完整的SQL错误处理流程"""
        # 创建模拟的重试回调
        retry_callback = AsyncMock(return_value=(False, None))
        
        result = await self.recovery_service.handle_sql_error(
            error_message="Unknown column 'test_field' in 'field list'",
            sql_statement="SELECT test_field FROM users",
            session_id="test_session",
            context={"original_question": "查询测试字段"},
            retry_callback=retry_callback
        )
        
        assert "success" in result
        assert "error_info" in result
        assert "feedback" in result
        assert result["error_info"]["error_type"] == SQLErrorType.FIELD_NOT_EXISTS.value
    
    def test_service_statistics(self):
        """测试服务统计信息"""
        stats = self.recovery_service.get_service_statistics()
        
        assert "classifier_stats" in stats
        assert "total_sessions" in stats
    
    def test_learn_from_feedback(self):
        """测试从反馈中学习"""
        # 测试有效的学习
        self.recovery_service.learn_from_feedback(
            "Test error message",
            SQLErrorType.SYNTAX_ERROR.value
        )
        
        # 测试无效的分类
        self.recovery_service.learn_from_feedback(
            "Test error message",
            "invalid_classification"
        )
        # 应该不会抛出异常


class TestErrorPatternMatching:
    """错误模式匹配测试类"""
    
    def setup_method(self):
        """测试前置设置"""
        self.classifier = SQLErrorClassifier()
    
    def test_mysql_specific_patterns(self):
        """测试MySQL特定的错误模式"""
        # MySQL语法错误
        result = self.classifier.classify_error(
            "You have an error in your SQL syntax; check the manual that corresponds to your MySQL server version",
            "SELECT * FROM users WHRE id = 1"
        )
        assert result.error_type == SQLErrorType.SYNTAX_ERROR
        
        # MySQL字段错误
        result = self.classifier.classify_error(
            "Unknown column 'user_name' in 'field list'",
            "SELECT user_name FROM users"
        )
        assert result.error_type == SQLErrorType.FIELD_NOT_EXISTS
        assert "user_name" in result.suggested_fields
    
    def test_sql_server_specific_patterns(self):
        """测试SQL Server特定的错误模式"""
        # SQL Server语法错误
        result = self.classifier.classify_error(
            "Incorrect syntax near 'WHRE'",
            "SELECT * FROM users WHRE id = 1"
        )
        assert result.error_type == SQLErrorType.SYNTAX_ERROR
        
        # SQL Server字段错误
        result = self.classifier.classify_error(
            "Invalid column name 'user_name'",
            "SELECT user_name FROM users"
        )
        assert result.error_type == SQLErrorType.FIELD_NOT_EXISTS
    
    def test_pattern_confidence_levels(self):
        """测试模式置信度级别"""
        # 高置信度模式
        result = self.classifier.classify_error(
            "Table 'test.users' doesn't exist",
            "SELECT * FROM users"
        )
        assert result.confidence >= 0.95
        
        # 基于关键词的较低置信度
        result = self.classifier.classify_error(
            "Some syntax issue occurred",
            "SELECT * FROM users"
        )
        assert result.confidence < 0.8


if __name__ == "__main__":
    pytest.main([__file__])