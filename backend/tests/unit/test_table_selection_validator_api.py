"""
选表结果解析和验证 API 测试

任务 5.2.4 的API测试实现
"""

import pytest
import json
from unittest.mock import Mock, AsyncMock, patch, PropertyMock
from fastapi.testclient import TestClient
from datetime import datetime

from src.main import app
from src.services.table_selection_validator import (
    SelectionValidationResult,
    TableValidationResult,
    RelationValidationResult,
    ValidationIssue,
    ValidationSeverity,
    ValidationCategory
)


class TestTableSelectionValidatorAPI:
    """选表结果验证API测试"""
    
    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        return TestClient(app)
    
    @pytest.fixture
    def sample_validation_request(self):
        """创建示例验证请求"""
        return {
            "selection_result": {
                "primary_tables": [
                    {
                        "table_id": "tbl_001",
                        "table_name": "products",
                        "table_comment": "产品信息表",
                        "relevance_score": 0.95,
                        "confidence": "high",
                        "selection_reasons": ["包含产品相关字段"],
                        "matched_keywords": ["产品"],
                        "business_meaning": "存储产品基本信息",
                        "relation_paths": []
                    }
                ],
                "related_tables": [],
                "selection_strategy": "ai_based",
                "total_relevance_score": 0.95,
                "recommended_joins": [],
                "selection_explanation": "选择了产品表",
                "processing_time": 1.23,
                "ai_reasoning": "用户询问产品信息"
            },
            "data_source_id": "ds_001",
            "validation_options": {
                "enable_deep_validation": True,
                "check_data_samples": True
            }
        }
    
    @pytest.fixture
    def sample_validation_result(self):
        """创建示例验证结果"""
        return SelectionValidationResult(
            is_valid=True,
            overall_confidence=0.92,
            table_validations=[
                TableValidationResult(
                    table_name="products",
                    table_id="tbl_001",
                    is_valid=True,
                    exists=True,
                    accessible=True,
                    data_integrity_score=0.9,
                    issues=[],
                    metadata={"field_count": 10, "has_data": True}
                )
            ],
            relation_validations=[],
            selection_explanation="所有选中的表都通过了验证",
            transparency_report={
                "selection_summary": {
                    "primary_tables_count": 1,
                    "related_tables_count": 0,
                    "total_relevance_score": 0.95
                },
                "validation_summary": {
                    "valid_tables": 1,
                    "total_tables": 1,
                    "total_issues": 0
                }
            },
            recommendations=["所有表都可以安全使用"],
            processing_time=2.34
        )
    
    def test_validate_selection_result_success(self, client, sample_validation_request, sample_validation_result):
        """测试验证选表结果成功"""
        with patch('src.api.table_selection_validator_api.validator_service.validate_selection_result') as mock_validate:
            mock_validate.return_value = sample_validation_result
            
            response = client.post(
                "/api/table-selection-validator/validate",
                json=sample_validation_request
            )
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["is_valid"] is True
            assert data["overall_confidence"] == 0.92
            assert len(data["table_validations"]) == 1
            assert data["table_validations"][0]["table_name"] == "products"
            assert data["table_validations"][0]["is_valid"] is True
            assert len(data["relation_validations"]) == 0
            assert data["processing_time"] == 2.34
            assert len(data["recommendations"]) == 1
    
    def test_validate_selection_result_with_issues(self, client, sample_validation_request):
        """测试验证选表结果包含问题"""
        validation_result = SelectionValidationResult(
            is_valid=False,
            overall_confidence=0.3,
            table_validations=[
                TableValidationResult(
                    table_name="products",
                    table_id="tbl_001",
                    is_valid=False,
                    exists=False,
                    accessible=False,
                    data_integrity_score=0.0,
                    issues=[
                        ValidationIssue(
                            category=ValidationCategory.EXISTENCE,
                            severity=ValidationSeverity.ERROR,
                            table_name="products",
                            field_name=None,
                            message="表不存在",
                            suggestion="检查表名是否正确",
                            details={"table_id": "tbl_001"}
                        )
                    ],
                    metadata={}
                )
            ],
            relation_validations=[],
            selection_explanation="发现表存在性问题",
            transparency_report={},
            recommendations=["检查表配置"],
            processing_time=1.5
        )
        
        with patch('src.api.table_selection_validator_api.validator_service.validate_selection_result') as mock_validate:
            mock_validate.return_value = validation_result
            
            response = client.post(
                "/api/table-selection-validator/validate",
                json=sample_validation_request
            )
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["is_valid"] is False
            assert data["overall_confidence"] == 0.3
            assert len(data["table_validations"]) == 1
            assert data["table_validations"][0]["is_valid"] is False
            assert len(data["table_validations"][0]["issues"]) == 1
            assert data["table_validations"][0]["issues"][0]["severity"] == "error"
            assert data["table_validations"][0]["issues"][0]["message"] == "表不存在"
    
    def test_validate_selection_result_with_relations(self, client, sample_validation_request):
        """测试验证包含关联关系的选表结果"""
        # 添加关联表到请求
        sample_validation_request["selection_result"]["related_tables"] = [
            {
                "table_id": "tbl_002",
                "table_name": "categories",
                "table_comment": "分类表",
                "relevance_score": 0.75,
                "confidence": "medium",
                "selection_reasons": ["产品分类相关"],
                "matched_keywords": ["分类"],
                "business_meaning": "产品分类信息",
                "relation_paths": []
            }
        ]
        
        sample_validation_request["selection_result"]["recommended_joins"] = [
            {
                "left_table": "products",
                "right_table": "categories",
                "join_type": "INNER",
                "join_condition": "products.category_id = categories.id",
                "confidence": 0.9
            }
        ]
        
        validation_result = SelectionValidationResult(
            is_valid=True,
            overall_confidence=0.88,
            table_validations=[
                TableValidationResult(
                    table_name="products",
                    table_id="tbl_001",
                    is_valid=True,
                    exists=True,
                    accessible=True,
                    data_integrity_score=0.9,
                    issues=[],
                    metadata={}
                ),
                TableValidationResult(
                    table_name="categories",
                    table_id="tbl_002",
                    is_valid=True,
                    exists=True,
                    accessible=True,
                    data_integrity_score=0.85,
                    issues=[],
                    metadata={}
                )
            ],
            relation_validations=[
                RelationValidationResult(
                    source_table="products",
                    target_table="categories",
                    is_valid=True,
                    relation_exists=True,
                    join_feasible=True,
                    business_reasonable=True,
                    confidence_score=0.9,
                    issues=[],
                    recommended_join={
                        "join_type": "INNER",
                        "join_condition": "products.category_id = categories.id"
                    }
                )
            ],
            selection_explanation="验证了表和关联关系",
            transparency_report={},
            recommendations=["关联关系有效"],
            processing_time=3.2
        )
        
        with patch('src.api.table_selection_validator_api.validator_service.validate_selection_result') as mock_validate:
            mock_validate.return_value = validation_result
            
            response = client.post(
                "/api/table-selection-validator/validate",
                json=sample_validation_request
            )
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["is_valid"] is True
            assert len(data["table_validations"]) == 2
            assert len(data["relation_validations"]) == 1
            assert data["relation_validations"][0]["is_valid"] is True
            assert data["relation_validations"][0]["confidence_score"] == 0.9
            assert data["relation_validations"][0]["recommended_join"] is not None
    
    def test_validate_selection_result_invalid_request(self, client):
        """测试无效请求"""
        invalid_request = {
            "selection_result": {
                # 缺少必需字段
                "primary_tables": []
            }
        }
        
        response = client.post(
            "/api/table-selection-validator/validate",
            json=invalid_request
        )
        
        assert response.status_code == 422  # 验证错误
    
    def test_validate_selection_result_service_error(self, client, sample_validation_request):
        """测试服务层错误"""
        with patch('src.api.table_selection_validator_api.validator_service.validate_selection_result') as mock_validate:
            mock_validate.side_effect = Exception("Service error")
            
            response = client.post(
                "/api/table-selection-validator/validate",
                json=sample_validation_request
            )
            
            assert response.status_code == 500
            data = response.json()
            assert "错误" in data["detail"]
    
    def test_quick_validate_selection_result_success(self, client, sample_validation_request, sample_validation_result):
        """测试快速验证选表结果成功"""
        with patch('src.api.table_selection_validator_api.validator_service.validate_selection_result') as mock_validate:
            mock_validate.return_value = sample_validation_result
            
            response = client.post(
                "/api/table-selection-validator/validate/quick",
                json=sample_validation_request
            )
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["is_valid"] is True
            assert data["processing_time"] == 2.34
            
            # 验证调用时使用了快速验证选项
            mock_validate.assert_called_once()
            call_args = mock_validate.call_args
            validation_options = call_args.kwargs["validation_options"]
            assert validation_options["enable_deep_validation"] is False
            assert validation_options["check_data_samples"] is False
            assert validation_options["validate_relations"] is False
            assert validation_options["max_validation_time"] == 10.0
    
    def test_quick_validate_with_user_options(self, client, sample_validation_request, sample_validation_result):
        """测试快速验证合并用户选项"""
        # 用户指定了一些选项
        sample_validation_request["validation_options"]["min_confidence_threshold"] = 0.7
        
        with patch('src.api.table_selection_validator_api.validator_service.validate_selection_result') as mock_validate:
            mock_validate.return_value = sample_validation_result
            
            response = client.post(
                "/api/table-selection-validator/validate/quick",
                json=sample_validation_request
            )
            
            assert response.status_code == 200
            
            # 验证用户选项被合并
            call_args = mock_validate.call_args
            validation_options = call_args.kwargs["validation_options"]
            assert validation_options["min_confidence_threshold"] == 0.7
            assert validation_options["enable_deep_validation"] is False  # 快速验证覆盖
    
    def test_get_validation_statistics_success(self, client):
        """测试获取验证统计信息成功"""
        mock_stats = {
            "total_validations": 100,
            "successful_validations": 85,
            "success_rate": 0.85,
            "average_processing_time": 2.5,
            "common_issues": {
                "existence_warning": 5,
                "integrity_info": 10
            },
            "configuration": {
                "min_confidence_threshold": 0.5,
                "enable_deep_validation": True
            }
        }
        
        with patch('src.api.table_selection_validator_api.validator_service.get_validation_statistics') as mock_get_stats:
            mock_get_stats.return_value = mock_stats
            
            response = client.get("/api/table-selection-validator/statistics")
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["total_validations"] == 100
            assert data["successful_validations"] == 85
            assert data["success_rate"] == 0.85
            assert data["average_processing_time"] == 2.5
            assert "common_issues" in data
            assert "configuration" in data
    
    def test_get_validation_statistics_error(self, client):
        """测试获取验证统计信息错误"""
        with patch('src.api.table_selection_validator_api.validator_service.get_validation_statistics') as mock_get_stats:
            mock_get_stats.side_effect = Exception("Stats error")
            
            response = client.get("/api/table-selection-validator/statistics")
            
            assert response.status_code == 500
            data = response.json()
            assert "错误" in data["detail"]
    
    def test_get_validation_config_success(self, client):
        """测试获取验证配置成功"""
        mock_config = {
            "min_confidence_threshold": 0.5,
            "max_validation_time": 30.0,
            "enable_deep_validation": True,
            "check_data_samples": True,
            "validate_relations": True
        }
        
        with patch('src.api.table_selection_validator_api.validator_service.validation_config', mock_config):
            response = client.get("/api/table-selection-validator/config")
            
            assert response.status_code == 200
            data = response.json()
            
            assert "configuration" in data
            assert "description" in data
            assert data["configuration"]["min_confidence_threshold"] == 0.5
            assert data["configuration"]["enable_deep_validation"] is True
            
            # 验证描述信息
            assert "最小置信度阈值" in data["description"]["min_confidence_threshold"]
    
    def test_update_validation_config_success(self, client):
        """测试更新验证配置成功"""
        new_config = {
            "min_confidence_threshold": 0.7,
            "max_validation_time": 20.0,
            "enable_deep_validation": False
        }
        
        with patch('src.api.table_selection_validator_api.validator_service') as mock_service:
            mock_service.validation_config = {
                "min_confidence_threshold": 0.5,
                "max_validation_time": 30.0,
                "enable_deep_validation": True,
                "check_data_samples": True,
                "validate_relations": True
            }
            
            response = client.put(
                "/api/table-selection-validator/config",
                json=new_config
            )
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["message"] == "验证配置更新成功"
            assert "updated_config" in data
            assert "timestamp" in data
            
            # 验证配置被更新
            updated_config = data["updated_config"]
            assert updated_config["min_confidence_threshold"] == 0.7
            assert updated_config["max_validation_time"] == 20.0
            assert updated_config["enable_deep_validation"] is False
    
    def test_update_validation_config_partial(self, client):
        """测试部分更新验证配置"""
        partial_config = {
            "min_confidence_threshold": 0.8
            # 只更新一个字段
        }
        
        with patch('src.api.table_selection_validator_api.validator_service') as mock_service:
            original_config = {
                "min_confidence_threshold": 0.5,
                "max_validation_time": 30.0,
                "enable_deep_validation": True
            }
            mock_service.validation_config = original_config.copy()
            
            response = client.put(
                "/api/table-selection-validator/config",
                json=partial_config
            )
            
            assert response.status_code == 200
            data = response.json()
            
            # 验证只有指定字段被更新
            updated_config = data["updated_config"]
            assert updated_config["min_confidence_threshold"] == 0.8
            assert updated_config["max_validation_time"] == 30.0  # 保持原值
            assert updated_config["enable_deep_validation"] is True  # 保持原值
    
    def test_update_validation_config_error(self, client):
        """测试更新验证配置错误"""
        new_config = {
            "min_confidence_threshold": 0.7
        }
        
        with patch('src.api.table_selection_validator_api.validator_service') as mock_service:
            # 模拟 validation_config 属性访问时抛出异常
            type(mock_service).validation_config = PropertyMock(side_effect=Exception("Config access error"))
            
            response = client.put(
                "/api/table-selection-validator/config",
                json=new_config
            )
            
            assert response.status_code == 500
            data = response.json()
            assert "错误" in data["detail"]
    
    def test_health_check_success(self, client):
        """测试健康检查成功"""
        mock_stats = {
            "total_validations": 50,
            "success_rate": 0.9,
            "average_processing_time": 2.0
        }
        
        mock_config = {
            "min_confidence_threshold": 0.5,
            "enable_deep_validation": True
        }
        
        with patch('src.api.table_selection_validator_api.validator_service.get_validation_statistics') as mock_get_stats, \
             patch('src.api.table_selection_validator_api.validator_service.validation_config', mock_config):
            
            mock_get_stats.return_value = mock_stats
            
            response = client.get("/api/table-selection-validator/health")
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["status"] == "healthy"
            assert data["service"] == "table_selection_validator"
            assert data["version"] == "1.0.0"
            assert "timestamp" in data
            assert "statistics" in data
            assert "dependencies" in data
            assert "configuration" in data
            
            # 验证统计信息
            assert data["statistics"]["total_validations"] == 50
            assert data["statistics"]["success_rate"] == 0.9
            
            # 验证依赖状态
            assert data["dependencies"]["data_source_service"] == "available"
            assert data["dependencies"]["data_table_service"] == "available"
            assert data["dependencies"]["relation_service"] == "available"
    
    def test_health_check_error(self, client):
        """测试健康检查错误"""
        with patch('src.api.table_selection_validator_api.validator_service.get_validation_statistics') as mock_get_stats:
            mock_get_stats.side_effect = Exception("Health check error")
            
            response = client.get("/api/table-selection-validator/health")
            
            assert response.status_code == 200  # 健康检查即使失败也返回200
            data = response.json()
            
            assert data["status"] == "unhealthy"
            assert data["service"] == "table_selection_validator"
            assert "error" in data
            assert "timestamp" in data
    
    def test_validation_request_model_validation(self, client):
        """测试验证请求模型验证"""
        # 测试缺少必需字段
        invalid_requests = [
            {},  # 完全空的请求
            {"selection_result": {}},  # 空的选择结果
            {
                "selection_result": {
                    "primary_tables": [],
                    "related_tables": [],
                    # 缺少其他必需字段
                }
            }
        ]
        
        for invalid_request in invalid_requests:
            response = client.post(
                "/api/table-selection-validator/validate",
                json=invalid_request
            )
            assert response.status_code == 422
    
    def test_validation_options_model_defaults(self, client, sample_validation_request, sample_validation_result):
        """测试验证选项模型默认值"""
        # 移除验证选项，测试默认值
        del sample_validation_request["validation_options"]
        
        with patch('src.api.table_selection_validator_api.validator_service.validate_selection_result') as mock_validate:
            mock_validate.return_value = sample_validation_result
            
            response = client.post(
                "/api/table-selection-validator/validate",
                json=sample_validation_request
            )
            
            assert response.status_code == 200
            
            # 验证使用了默认的验证选项（None）
            call_args = mock_validate.call_args
            assert call_args.kwargs["validation_options"] is None
    
    def test_convert_functions(self):
        """测试转换函数"""
        from src.api.table_selection_validator_api import (
            convert_validation_issue_to_response,
            convert_table_validation_to_response,
            convert_relation_validation_to_response
        )
        
        # 测试验证问题转换
        issue = ValidationIssue(
            category=ValidationCategory.EXISTENCE,
            severity=ValidationSeverity.ERROR,
            table_name="test_table",
            field_name="test_field",
            message="Test message",
            suggestion="Test suggestion",
            details={"key": "value"}
        )
        
        issue_response = convert_validation_issue_to_response(issue)
        assert issue_response.category == "existence"
        assert issue_response.severity == "error"
        assert issue_response.table_name == "test_table"
        assert issue_response.field_name == "test_field"
        assert issue_response.message == "Test message"
        
        # 测试表验证转换
        table_validation = TableValidationResult(
            table_name="test_table",
            table_id="tbl_test",
            is_valid=True,
            exists=True,
            accessible=True,
            data_integrity_score=0.8,
            issues=[issue],
            metadata={"test": "data"}
        )
        
        table_response = convert_table_validation_to_response(table_validation)
        assert table_response.table_name == "test_table"
        assert table_response.is_valid is True
        assert table_response.data_integrity_score == 0.8
        assert len(table_response.issues) == 1
        
        # 测试关联验证转换
        relation_validation = RelationValidationResult(
            source_table="table1",
            target_table="table2",
            is_valid=True,
            relation_exists=True,
            join_feasible=True,
            business_reasonable=True,
            confidence_score=0.9,
            issues=[],
            recommended_join={"type": "INNER"}
        )
        
        relation_response = convert_relation_validation_to_response(relation_validation)
        assert relation_response.source_table == "table1"
        assert relation_response.target_table == "table2"
        assert relation_response.is_valid is True
        assert relation_response.confidence_score == 0.9
        assert relation_response.recommended_join == {"type": "INNER"}