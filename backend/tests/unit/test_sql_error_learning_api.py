"""
SQL错误学习API单元测试

测试错误反馈学习循环的API接口功能。
"""

import pytest
import json
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

from src.main import app
from src.services.sql_error_learning_service import (
    SQLErrorLearningService,
    LearningSession,
    AIFeedbackMessage,
    ErrorPattern
)
from src.services.sql_error_classifier import SQLError, SQLErrorType


class TestSQLErrorLearningAPI:
    """SQL错误学习API测试"""
    
    def setup_method(self):
        """测试前设置"""
        self.client = TestClient(app)
        self.base_url = "/api/sql-error-learning"
    
    @patch('src.api.sql_error_learning_api.learning_service')
    def test_start_learning_session(self, mock_learning_service):
        """测试开始学习会话API"""
        # 模拟服务响应
        mock_session = LearningSession(
            session_id="test_session_001",
            original_question="查询用户信息",
            error_sequence=[]
        )
        mock_learning_service.start_learning_session = AsyncMock(return_value=mock_session)
        
        # 发送请求
        response = self.client.post(
            f"{self.base_url}/sessions/start",
            params={
                "session_id": "test_session_001",
                "original_question": "查询用户信息"
            }
        )
        
        # 验证响应
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert data["data"]["session_id"] == "test_session_001"
        assert data["data"]["original_question"] == "查询用户信息"
        assert "created_at" in data["data"]
    
    @patch('src.api.sql_error_learning_api.learning_service')
    @patch('src.api.sql_error_learning_api.error_recovery_service')
    def test_record_error(self, mock_error_recovery_service, mock_learning_service):
        """测试记录错误API"""
        # 模拟错误分类器响应
        mock_sql_error = SQLError(
            error_type=SQLErrorType.FIELD_NOT_EXISTS,
            original_error="Unknown column 'test_field'",
            error_message="字段不存在",
            sql_statement="SELECT test_field FROM users",
            confidence=0.9
        )
        mock_error_recovery_service.classifier.classify_error.return_value = mock_sql_error
        
        # 模拟学习服务响应
        mock_pattern = ErrorPattern(
            pattern_id="pattern_001",
            error_type=SQLErrorType.FIELD_NOT_EXISTS,
            pattern_regex="Unknown column '<IDENTIFIER>'",
            frequency=1,
            confidence=0.5,
            context_keywords=["users"],
            common_fixes=[],
            created_at=datetime.now(),
            last_seen=datetime.now()
        )
        mock_learning_service.record_error = AsyncMock(return_value=mock_pattern)
        
        # 发送请求
        response = self.client.post(
            f"{self.base_url}/errors/record",
            params={
                "session_id": "test_session_001",
                "error_message": "Unknown column 'test_field'",
                "sql_statement": "SELECT test_field FROM users"
            },
            json={
                "table_names": ["users"],
                "field_names": ["id", "name", "email"]
            }
        )
        
        # 验证响应
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert data["data"]["session_id"] == "test_session_001"
        assert data["data"]["error_recorded"] == True
        assert data["data"]["error_type"] == "field_not_exists"
        assert "learned_pattern" in data["data"]
        assert data["data"]["learned_pattern"]["pattern_id"] == "pattern_001"
    
    @patch('src.api.sql_error_learning_api.learning_service')
    def test_record_success(self, mock_learning_service):
        """测试记录成功SQL API"""
        # 模拟服务响应
        mock_learning_service.record_success = AsyncMock()
        
        # 发送请求
        response = self.client.post(
            f"{self.base_url}/success/record",
            params={
                "session_id": "test_session_001",
                "successful_sql": "SELECT id, name FROM users WHERE active = 1"
            }
        )
        
        # 验证响应
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert data["data"]["session_id"] == "test_session_001"
        assert data["data"]["successful_sql"] == "SELECT id, name FROM users WHERE active = 1"
        
        # 验证服务调用
        mock_learning_service.record_success.assert_called_once_with(
            "test_session_001",
            "SELECT id, name FROM users WHERE active = 1"
        )
    
    @patch('src.api.sql_error_learning_api.learning_service')
    def test_generate_ai_feedback(self, mock_learning_service):
        """测试生成AI反馈API"""
        # 模拟反馈消息
        mock_feedback = AIFeedbackMessage(
            message_id="feedback_001",
            session_id="test_session_001",
            feedback_type="error_learning",
            original_question="查询用户信息",
            failed_sql="SELECT invalid_field FROM users",
            error_analysis="字段不存在错误分析",
            suggested_improvements=["验证字段名", "使用表结构信息"],
            context_enhancement={"error_history": []}
        )
        
        # 模拟服务响应
        mock_learning_service.generate_feedback_for_ai = AsyncMock(return_value=mock_feedback)
        mock_learning_service.feedback_generator.format_feedback_for_ai_model.return_value = "格式化的反馈信息"
        
        # 发送请求
        response = self.client.post(
            f"{self.base_url}/feedback/generate",
            params={"session_id": "test_session_001"},
            json={"table_names": ["users"]}
        )
        
        # 验证响应
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert data["data"]["message_id"] == "feedback_001"
        assert data["data"]["session_id"] == "test_session_001"
        assert data["data"]["feedback_type"] == "error_learning"
        assert len(data["data"]["suggested_improvements"]) == 2
        assert data["data"]["formatted_feedback"] == "格式化的反馈信息"
    
    @patch('src.api.sql_error_learning_api.learning_service')
    def test_generate_ai_feedback_no_errors(self, mock_learning_service):
        """测试无错误时的AI反馈生成API"""
        # 模拟服务返回None（无错误）
        mock_learning_service.generate_feedback_for_ai = AsyncMock(return_value=None)
        
        # 发送请求
        response = self.client.post(
            f"{self.base_url}/feedback/generate",
            params={"session_id": "test_session_001"}
        )
        
        # 验证响应
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == False
        assert "无法生成反馈" in data["message"]
    
    @patch('src.api.sql_error_learning_api.learning_service')
    def test_get_error_patterns(self, mock_learning_service):
        """测试获取错误模式API"""
        # 模拟错误模式
        mock_patterns = [
            ErrorPattern(
                pattern_id="pattern_001",
                error_type=SQLErrorType.FIELD_NOT_EXISTS,
                pattern_regex="Unknown column '<IDENTIFIER>'",
                frequency=5,
                confidence=0.8,
                context_keywords=["users", "查询"],
                common_fixes=["验证字段名"],
                created_at=datetime.now(),
                last_seen=datetime.now(),
                success_rate_after_fix=0.7
            ),
            ErrorPattern(
                pattern_id="pattern_002",
                error_type=SQLErrorType.SYNTAX_ERROR,
                pattern_regex="SQL syntax error",
                frequency=3,
                confidence=0.9,
                context_keywords=["语法", "错误"],
                common_fixes=["检查SQL语法"],
                created_at=datetime.now(),
                last_seen=datetime.now(),
                success_rate_after_fix=0.9
            )
        ]
        
        mock_learning_service.pattern_learner.get_frequent_patterns.return_value = mock_patterns
        
        # 发送请求
        response = self.client.get(
            f"{self.base_url}/patterns",
            params={"min_frequency": 3}
        )
        
        # 验证响应
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert len(data["data"]["patterns"]) == 2
        assert data["data"]["total_patterns"] == 2
        
        # 验证第一个模式
        pattern1 = data["data"]["patterns"][0]
        assert pattern1["pattern_id"] == "pattern_001"
        assert pattern1["error_type"] == "field_not_exists"
        assert pattern1["frequency"] == 5
        assert pattern1["confidence"] == 0.8
        assert "users" in pattern1["context_keywords"]
    
    @patch('src.api.sql_error_learning_api.learning_service')
    def test_get_error_patterns_with_filter(self, mock_learning_service):
        """测试带过滤条件的错误模式获取API"""
        # 模拟过滤后的模式
        mock_patterns = [
            ErrorPattern(
                pattern_id="pattern_001",
                error_type=SQLErrorType.FIELD_NOT_EXISTS,
                pattern_regex="Unknown column '<IDENTIFIER>'",
                frequency=5,
                confidence=0.8,
                context_keywords=["users"],
                common_fixes=[],
                created_at=datetime.now(),
                last_seen=datetime.now()
            )
        ]
        
        mock_learning_service.pattern_learner.get_frequent_patterns.return_value = mock_patterns
        
        # 发送请求（按错误类型过滤）
        response = self.client.get(
            f"{self.base_url}/patterns",
            params={
                "min_frequency": 3,
                "error_type": "field_not_exists"
            }
        )
        
        # 验证响应
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert len(data["data"]["patterns"]) == 1
        assert data["data"]["patterns"][0]["error_type"] == "field_not_exists"
        assert data["data"]["filter_applied"]["error_type"] == "field_not_exists"
    
    def test_get_error_patterns_invalid_type(self):
        """测试无效错误类型的模式获取API"""
        # 发送请求（无效错误类型）
        response = self.client.get(
            f"{self.base_url}/patterns",
            params={"error_type": "invalid_error_type"}
        )
        
        # 验证响应
        assert response.status_code == 400
        assert "无效的错误类型" in response.json()["detail"]
    
    @patch('src.api.sql_error_learning_api.learning_service')
    def test_get_error_predictions(self, mock_learning_service):
        """测试获取错误预测API"""
        # 模拟预测结果
        mock_predictions = {
            "field_not_exists": 0.7,
            "syntax_error": 0.3
        }
        mock_learning_service.get_error_predictions.return_value = mock_predictions
        
        # 发送请求
        response = self.client.get(
            f"{self.base_url}/predictions",
            params={
                "original_question": "查询用户信息",
                "table_names": ["users", "orders"],
                "field_names": ["id", "name", "email"]
            }
        )
        
        # 验证响应
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert data["data"]["predictions"] == mock_predictions
        assert "context" in data["data"]
        assert data["data"]["context"]["original_question"] == "查询用户信息"
    
    @patch('src.api.sql_error_learning_api.learning_service')
    def test_get_improvement_suggestions(self, mock_learning_service):
        """测试获取改进建议API"""
        # 模拟改进建议
        mock_suggestions = [
            "验证字段名是否存在",
            "使用表结构信息进行校验",
            "检查SQL语法"
        ]
        mock_learning_service.get_improvement_suggestions.return_value = mock_suggestions
        
        # 发送请求
        response = self.client.get(f"{self.base_url}/suggestions/test_session_001")
        
        # 验证响应
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert data["data"]["session_id"] == "test_session_001"
        assert data["data"]["suggestions"] == mock_suggestions
        assert data["data"]["suggestion_count"] == 3
    
    @patch('src.api.sql_error_learning_api.learning_service')
    def test_get_learning_statistics(self, mock_learning_service):
        """测试获取学习统计信息API"""
        # 模拟统计信息
        mock_stats = {
            "learning_enabled": True,
            "total_learning_sessions": 10,
            "total_errors_recorded": 25,
            "successful_sessions": 8,
            "success_rate": 0.8,
            "pattern_statistics": {
                "total_patterns": 5,
                "frequent_patterns": 3,
                "high_confidence_patterns": 2
            },
            "feedback_messages_generated": 15
        }
        mock_learning_service.get_learning_statistics.return_value = mock_stats
        
        # 发送请求
        response = self.client.get(f"{self.base_url}/statistics")
        
        # 验证响应
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert data["data"] == mock_stats
    
    @patch('src.api.sql_error_learning_api.learning_service')
    def test_cleanup_old_sessions(self, mock_learning_service):
        """测试清理旧会话API"""
        # 模拟清理方法
        mock_learning_service.cleanup_old_sessions = Mock()
        
        # 发送请求
        response = self.client.post(
            f"{self.base_url}/sessions/cleanup",
            params={"max_age_hours": 48}
        )
        
        # 验证响应
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert data["data"]["max_age_hours"] == 48
        
        # 验证服务调用
        mock_learning_service.cleanup_old_sessions.assert_called_once_with(48)
    
    @patch('src.api.sql_error_learning_api.learning_service')
    def test_export_learning_data(self, mock_learning_service):
        """测试导出学习数据API"""
        # 模拟导出数据
        mock_export_data = {
            "error_patterns": {
                "pattern_001": {
                    "pattern_id": "pattern_001",
                    "error_type": "field_not_exists",
                    "frequency": 5
                }
            },
            "learning_sessions": {
                "session_001": {
                    "session_id": "session_001",
                    "original_question": "查询用户",
                    "error_count": 2
                }
            },
            "feedback_history": []
        }
        mock_learning_service.export_learning_data.return_value = mock_export_data
        
        # 发送请求
        response = self.client.get(f"{self.base_url}/export")
        
        # 验证响应
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert "export_timestamp" in data["data"]
        assert data["data"]["learning_data"] == mock_export_data
    
    @patch('src.api.sql_error_learning_api.learning_service')
    def test_learn_from_pattern(self, mock_learning_service):
        """测试从错误模式学习API"""
        # 模拟学习方法
        mock_learning_service.pattern_learner.learn_from_error_pattern = Mock()
        
        # 发送请求
        response = self.client.post(
            f"{self.base_url}/patterns/learn",
            params={
                "error_message": "Unknown column 'test_field'",
                "correct_classification": "field_not_exists"
            }
        )
        
        # 验证响应
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert data["data"]["error_message"] == "Unknown column 'test_field'"
        assert data["data"]["correct_classification"] == "field_not_exists"
    
    def test_learn_from_pattern_invalid_classification(self):
        """测试无效分类的模式学习API"""
        # 发送请求（无效分类）
        response = self.client.post(
            f"{self.base_url}/patterns/learn",
            params={
                "error_message": "Some error message",
                "correct_classification": "invalid_classification"
            }
        )
        
        # 验证响应
        assert response.status_code == 400
        assert "无效的错误分类" in response.json()["detail"]
    
    @patch('src.api.sql_error_learning_api.learning_service')
    def test_health_check(self, mock_learning_service):
        """测试健康检查API"""
        # 模拟统计信息
        mock_stats = {
            "learning_enabled": True,
            "total_learning_sessions": 5,
            "pattern_statistics": {
                "total_patterns": 3
            }
        }
        mock_learning_service.get_learning_statistics.return_value = mock_stats
        
        # 发送请求
        response = self.client.get(f"{self.base_url}/health")
        
        # 验证响应
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert "SQL错误学习服务运行正常" in data["message"]
        assert data["data"]["service_status"] == "healthy"
        assert data["data"]["learning_enabled"] == True
        assert data["data"]["total_sessions"] == 5
        assert data["data"]["total_patterns"] == 3
    
    @patch('src.api.sql_error_learning_api.learning_service')
    def test_enable_learning(self, mock_learning_service):
        """测试启用学习功能API"""
        # 发送请求
        response = self.client.post(f"{self.base_url}/enable")
        
        # 验证响应
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert data["message"] == "学习功能已启用"
        assert data["data"]["learning_enabled"] == True
        
        # 验证服务状态更新
        assert mock_learning_service.learning_enabled == True
    
    @patch('src.api.sql_error_learning_api.learning_service')
    def test_disable_learning(self, mock_learning_service):
        """测试禁用学习功能API"""
        # 发送请求
        response = self.client.post(f"{self.base_url}/disable")
        
        # 验证响应
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert data["message"] == "学习功能已禁用"
        assert data["data"]["learning_enabled"] == False
        
        # 验证服务状态更新
        assert mock_learning_service.learning_enabled == False


if __name__ == "__main__":
    pytest.main([__file__])