"""
选表结果解析和验证服务测试

任务 5.2.4 的测试实现
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from src.services.table_selection_validator import (
    TableSelectionValidator,
    SelectionValidationResult,
    TableValidationResult,
    RelationValidationResult,
    ValidationIssue,
    ValidationSeverity,
    ValidationCategory
)
from src.services.intelligent_table_selector import (
    TableSelectionResult,
    TableCandidate,
    TableSelectionConfidence
)


class TestTableSelectionValidator:
    """选表结果验证服务测试"""
    
    @pytest.fixture
    def validator(self):
        """创建验证器实例"""
        return TableSelectionValidator()
    
    @pytest.fixture
    def sample_table_candidate(self):
        """创建示例表候选"""
        return TableCandidate(
            table_id="tbl_001",
            table_name="products",
            table_comment="产品信息表",
            relevance_score=0.95,
            confidence=TableSelectionConfidence.HIGH,
            selection_reasons=["包含产品相关字段", "与查询高度相关"],
            matched_keywords=["产品", "商品"],
            business_meaning="存储产品基本信息和属性",
            relation_paths=[],
            semantic_context={}
        )
    
    @pytest.fixture
    def sample_selection_result(self, sample_table_candidate):
        """创建示例选表结果"""
        return TableSelectionResult(
            primary_tables=[sample_table_candidate],
            related_tables=[],
            selection_strategy="ai_based",
            total_relevance_score=0.95,
            recommended_joins=[],
            selection_explanation="基于AI模型选择了产品表",
            processing_time=1.23,
            ai_reasoning="用户询问产品信息，产品表最相关"
        )
    
    def test_validate_selection_result_success(self, validator, sample_selection_result):
        """测试成功验证选表结果"""
        # Mock依赖服务
        with patch.object(validator, '_validate_selected_tables') as mock_validate_tables, \
             patch.object(validator, '_validate_table_relations') as mock_validate_relations:
            
            # 设置Mock返回值
            mock_validate_tables.return_value = [
                TableValidationResult(
                    table_name="products",
                    table_id="tbl_001",
                    is_valid=True,
                    exists=True,
                    accessible=True,
                    data_integrity_score=0.9,
                    issues=[],
                    metadata={"field_count": 10}
                )
            ]
            mock_validate_relations.return_value = []
            
            # 执行验证
            result = validator.validate_selection_result(
                selection_result=sample_selection_result,
                data_source_id="ds_001"
            )
            
            # 验证结果
            assert isinstance(result, SelectionValidationResult)
            assert result.is_valid is True
            assert result.overall_confidence > 0.5
            assert len(result.table_validations) == 1
            assert len(result.relation_validations) == 0
            assert result.processing_time > 0
            assert "产品表" in result.selection_explanation
    
    def test_validate_selection_result_with_invalid_table(self, validator, sample_selection_result):
        """测试验证包含无效表的选表结果"""
        with patch.object(validator, '_validate_selected_tables') as mock_validate_tables, \
             patch.object(validator, '_validate_table_relations') as mock_validate_relations:
            
            # 设置Mock返回值 - 表不存在
            mock_validate_tables.return_value = [
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
            ]
            mock_validate_relations.return_value = []
            
            # 执行验证
            result = validator.validate_selection_result(
                selection_result=sample_selection_result,
                data_source_id="ds_001"
            )
            
            # 验证结果
            assert result.is_valid is False
            assert result.overall_confidence < 0.5
            assert len(result.table_validations) == 1
            assert len(result.table_validations[0].issues) == 1
            assert result.table_validations[0].issues[0].severity == ValidationSeverity.ERROR
    
    def test_validate_selection_result_with_relations(self, validator, sample_selection_result):
        """测试验证包含关联关系的选表结果"""
        # 添加关联表和推荐JOIN
        related_table = TableCandidate(
            table_id="tbl_002",
            table_name="categories",
            table_comment="分类表",
            relevance_score=0.75,
            confidence=TableSelectionConfidence.MEDIUM,
            selection_reasons=["产品分类相关"],
            matched_keywords=["分类"],
            business_meaning="产品分类信息",
            relation_paths=[],
            semantic_context={}
        )
        
        sample_selection_result.related_tables = [related_table]
        sample_selection_result.recommended_joins = [
            {
                "left_table": "products",
                "right_table": "categories",
                "join_type": "INNER",
                "join_condition": "products.category_id = categories.id",
                "confidence": 0.9,
                "reasoning": "产品表通过分类ID关联分类表"
            }
        ]
        
        with patch.object(validator, '_validate_selected_tables') as mock_validate_tables, \
             patch.object(validator, '_validate_table_relations') as mock_validate_relations:
            
            # 设置Mock返回值
            mock_validate_tables.return_value = [
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
            ]
            
            mock_validate_relations.return_value = [
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
            ]
            
            # 执行验证
            result = validator.validate_selection_result(
                selection_result=sample_selection_result,
                data_source_id="ds_001"
            )
            
            # 验证结果
            assert result.is_valid is True
            assert len(result.table_validations) == 2
            assert len(result.relation_validations) == 1
            assert result.relation_validations[0].is_valid is True
            assert result.relation_validations[0].confidence_score == 0.9
    
    def test_validate_single_table_exists_and_accessible(self, validator, sample_table_candidate):
        """测试验证单个表 - 存在且可访问"""
        with patch.object(validator, '_check_table_existence', return_value=True), \
             patch.object(validator, '_check_table_accessibility', return_value=True), \
             patch.object(validator, '_check_data_integrity', return_value=0.9), \
             patch.object(validator, '_validate_table_fields'), \
             patch.object(validator, '_check_data_samples'):
            
            result = validator._validate_single_table(
                table=sample_table_candidate,
                data_source_id="ds_001",
                options={"enable_deep_validation": True, "check_data_samples": True}
            )
            
            assert isinstance(result, TableValidationResult)
            assert result.table_name == "products"
            assert result.is_valid is True
            assert result.exists is True
            assert result.accessible is True
            assert result.data_integrity_score == 0.9
    
    def test_validate_single_table_not_exists(self, validator, sample_table_candidate):
        """测试验证单个表 - 不存在"""
        with patch.object(validator, '_check_table_existence', return_value=False):
            
            result = validator._validate_single_table(
                table=sample_table_candidate,
                data_source_id="ds_001",
                options={}
            )
            
            assert result.is_valid is False
            assert result.exists is False
            assert result.accessible is False
            assert len(result.issues) >= 1
            assert any(issue.category == ValidationCategory.EXISTENCE for issue in result.issues)
            assert any(issue.severity == ValidationSeverity.ERROR for issue in result.issues)
    
    def test_validate_single_table_not_accessible(self, validator, sample_table_candidate):
        """测试验证单个表 - 存在但不可访问"""
        with patch.object(validator, '_check_table_existence', return_value=True), \
             patch.object(validator, '_check_table_accessibility', return_value=False):
            
            result = validator._validate_single_table(
                table=sample_table_candidate,
                data_source_id="ds_001",
                options={}
            )
            
            assert result.is_valid is False
            assert result.exists is True
            assert result.accessible is False
            assert len(result.issues) >= 1
            assert any(issue.category == ValidationCategory.ACCESSIBILITY for issue in result.issues)
    
    def test_check_table_existence_success(self, validator):
        """测试检查表存在性 - 成功"""
        mock_table_candidate = Mock()
        mock_table_candidate.table_name = "products"
        
        with patch.object(validator.data_table_service, 'get_table_by_name_and_source') as mock_get_table:
            mock_get_table.return_value = {"id": "tbl_001", "table_name": "products"}
            
            result = validator._check_table_existence(mock_table_candidate, "ds_001")
            
            assert result is True
    
    def test_check_table_accessibility_success(self, validator):
        """测试检查表可访问性 - 成功"""
        mock_table_candidate = Mock()
        mock_table_candidate.table_name = "products"
        
        with patch.object(validator.data_table_service, 'get_table_columns') as mock_get_structure:
            mock_get_structure.return_value = [
                Mock(field_name="id", field_type="int"),
                Mock(field_name="name", field_type="varchar")
            ]
            
            result = validator._check_table_accessibility(mock_table_candidate, "ds_001")
            
            assert result is True
    
    def test_check_data_integrity_empty_table(self, validator):
        """测试检查数据完整性 - 空表"""
        mock_table_candidate = Mock()
        mock_table_candidate.table_name = "empty_products"
        
        issues = []
        
        with patch.object(validator, '_get_table_row_count', return_value=0), \
             patch.object(validator, '_check_null_rates', return_value={}):
            
            score = validator._check_data_integrity(
                mock_table_candidate, "ds_001", issues
            )
            
            assert score == 0.5  # 空表降低分数
            assert len(issues) == 1
            assert issues[0].category == ValidationCategory.INTEGRITY
            assert issues[0].severity == ValidationSeverity.WARNING
    
    def test_check_data_integrity_high_null_rate(self, validator):
        """测试检查数据完整性 - 高空值率"""
        mock_table_candidate = Mock()
        mock_table_candidate.table_name = "products"
        
        issues = []
        
        with patch.object(validator, '_get_table_row_count', return_value=1000), \
             patch.object(validator, '_check_null_rates', return_value={"description": 0.9}):
            
            score = validator._check_data_integrity(
                mock_table_candidate, "ds_001", issues
            )
            
            assert score < 1.0  # 高空值率降低分数
            assert len(issues) == 1
            assert "空值率过高" in issues[0].message
    
    def test_check_data_samples_success(self, validator):
        """测试检查数据样本 - 成功"""
        mock_table_candidate = Mock()
        mock_table_candidate.table_name = "products"
        
        issues = []
        metadata = {}
        
        with patch.object(validator, '_get_table_sample') as mock_get_sample:
            mock_get_sample.return_value = [
                {"id": 1, "name": "Product 1"},
                {"id": 2, "name": "Product 2"},
                {"id": 3, "name": "Product 3"}
            ]
            
            validator._check_data_samples(
                mock_table_candidate, "ds_001", issues, metadata
            )
            
            assert metadata["sample_row_count"] == 3
            assert metadata["has_data"] is True
            # 3行数据被认为是数据量较少，应该有一个INFO级别的提示
            sample_warnings = [issue for issue in issues if "数据量较少" in issue.message]
            assert len(sample_warnings) == 1
            assert sample_warnings[0].severity == ValidationSeverity.INFO
    
    def test_check_data_samples_insufficient_data(self, validator):
        """测试检查数据样本 - 数据不足"""
        mock_table_candidate = Mock()
        mock_table_candidate.table_name = "products"
        
        issues = []
        metadata = {}
        
        with patch.object(validator, '_get_table_sample') as mock_get_sample:
            mock_get_sample.return_value = [
                {"id": 1, "name": "Product 1"}
            ]
            
            validator._check_data_samples(
                mock_table_candidate, "ds_001", issues, metadata
            )
            
            assert metadata["sample_row_count"] == 1
            assert metadata["has_data"] is True
            # 数据不足，应该有信息提示
            sample_warnings = [issue for issue in issues if "数据量较少" in issue.message]
            assert len(sample_warnings) == 1
            assert sample_warnings[0].severity == ValidationSeverity.INFO
    
    def test_check_data_samples_no_data(self, validator):
        """测试检查数据样本 - 无数据"""
        mock_table_candidate = Mock()
        mock_table_candidate.table_name = "products"
        
        issues = []
        metadata = {}
        
        with patch.object(validator, '_get_table_sample') as mock_get_sample:
            mock_get_sample.return_value = []
            
            validator._check_data_samples(
                mock_table_candidate, "ds_001", issues, metadata
            )
            
            assert metadata["has_data"] is False
            # 无数据，应该有警告
            sample_warnings = [issue for issue in issues if "无法获取数据样本" in issue.message]
            assert len(sample_warnings) == 1
            assert sample_warnings[0].severity == ValidationSeverity.WARNING
    
    def test_validate_single_relation_success(self, validator):
        """测试验证单个关联关系 - 成功"""
        join_recommendation = {
            "left_table": "products",
            "right_table": "categories",
            "join_type": "INNER",
            "join_condition": "products.category_id = categories.id",
            "confidence": 0.9,
            "reasoning": "产品表通过分类ID关联分类表"
        }
        
        all_tables = []  # 简化测试
        
        with patch.object(validator, '_check_relation_exists', return_value=True), \
             patch.object(validator, '_check_join_feasible', return_value=True), \
             patch.object(validator, '_check_business_reasonableness', return_value=True):
            
            result = validator._validate_single_relation(
                join_recommendation, all_tables, "ds_001"
            )
            
            assert isinstance(result, RelationValidationResult)
            assert result.source_table == "products"
            assert result.target_table == "categories"
            assert result.is_valid is True
            assert result.relation_exists is True
            assert result.join_feasible is True
            assert result.business_reasonable is True
            assert result.confidence_score > 0.8
    
    def test_validate_single_relation_no_join_condition(self, validator):
        """测试验证单个关联关系 - 缺少JOIN条件"""
        join_recommendation = {
            "left_table": "products",
            "right_table": "categories",
            "join_type": "INNER",
            "join_condition": "",  # 空的JOIN条件
            "confidence": 0.9
        }
        
        all_tables = []
        
        with patch.object(validator, '_check_relation_exists', return_value=True), \
             patch.object(validator, '_check_business_reasonableness', return_value=True):
            
            result = validator._validate_single_relation(
                join_recommendation, all_tables, "ds_001"
            )
            
            assert result.is_valid is False
            assert result.join_feasible is False
            assert len(result.issues) >= 1
            assert any("缺少JOIN条件" in issue.message for issue in result.issues)
    
    def test_generate_transparency_report(self, validator, sample_selection_result):
        """测试生成透明度报告"""
        table_validations = [
            TableValidationResult(
                table_name="products",
                table_id="tbl_001",
                is_valid=True,
                exists=True,
                accessible=True,
                data_integrity_score=0.9,
                issues=[],
                metadata={}
            )
        ]
        
        relation_validations = []
        
        report = validator._generate_transparency_report(
            sample_selection_result, table_validations, relation_validations
        )
        
        assert "selection_summary" in report
        assert "validation_summary" in report
        assert "decision_factors" in report
        
        assert report["selection_summary"]["primary_tables_count"] == 1
        assert report["selection_summary"]["related_tables_count"] == 0
        assert report["validation_summary"]["valid_tables"] == 1
        assert report["validation_summary"]["total_tables"] == 1
    
    def test_calculate_overall_confidence(self, validator):
        """测试计算整体置信度"""
        table_validations = [
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
                data_integrity_score=0.8,
                issues=[],
                metadata={}
            )
        ]
        
        relation_validations = [
            RelationValidationResult(
                source_table="products",
                target_table="categories",
                is_valid=True,
                relation_exists=True,
                join_feasible=True,
                business_reasonable=True,
                confidence_score=0.9,
                issues=[],
                recommended_join={}
            )
        ]
        
        confidence = validator._calculate_overall_confidence(
            table_validations, relation_validations
        )
        
        assert 0.0 <= confidence <= 1.0
        assert confidence > 0.8  # 应该是高置信度
    
    def test_generate_selection_explanation(self, validator, sample_selection_result):
        """测试生成选择解释"""
        table_validations = [
            TableValidationResult(
                table_name="products",
                table_id="tbl_001",
                is_valid=True,
                exists=True,
                accessible=True,
                data_integrity_score=0.9,
                issues=[],
                metadata={}
            )
        ]
        
        relation_validations = []
        
        explanation = validator._generate_selection_explanation(
            sample_selection_result, table_validations, relation_validations
        )
        
        assert isinstance(explanation, str)
        assert len(explanation) > 0
        assert "products" in explanation
        assert "验证通过" in explanation or "AI模型" in explanation
    
    def test_generate_recommendations_all_valid(self, validator):
        """测试生成推荐 - 全部有效"""
        table_validations = [
            TableValidationResult(
                table_name="products",
                table_id="tbl_001",
                is_valid=True,
                exists=True,
                accessible=True,
                data_integrity_score=0.9,
                issues=[],
                metadata={}
            )
        ]
        
        relation_validations = []
        
        recommendations = validator._generate_recommendations(
            table_validations, relation_validations
        )
        
        assert isinstance(recommendations, list)
        assert len(recommendations) >= 1
        assert any("安全使用" in rec for rec in recommendations)
    
    def test_generate_recommendations_with_issues(self, validator):
        """测试生成推荐 - 有问题"""
        table_validations = [
            TableValidationResult(
                table_name="products",
                table_id="tbl_001",
                is_valid=False,
                exists=False,
                accessible=False,
                data_integrity_score=0.0,
                issues=[],
                metadata={}
            ),
            TableValidationResult(
                table_name="categories",
                table_id="tbl_002",
                is_valid=True,
                exists=True,
                accessible=True,
                data_integrity_score=0.3,  # 低完整性
                issues=[],
                metadata={}
            )
        ]
        
        relation_validations = []
        
        recommendations = validator._generate_recommendations(
            table_validations, relation_validations
        )
        
        assert len(recommendations) >= 2
        assert any("检查" in rec and "products" in rec for rec in recommendations)
        assert any("数据质量" in rec and "categories" in rec for rec in recommendations)
    
    def test_determine_overall_validity_valid(self, validator):
        """测试判断整体有效性 - 有效"""
        table_validations = [
            TableValidationResult(
                table_name="products",
                table_id="tbl_001",
                is_valid=True,
                exists=True,
                accessible=True,
                data_integrity_score=0.9,
                issues=[],
                metadata={}
            )
        ]
        
        relation_validations = []
        overall_confidence = 0.8
        
        is_valid = validator._determine_overall_validity(
            table_validations, relation_validations, overall_confidence
        )
        
        assert is_valid is True
    
    def test_determine_overall_validity_invalid_low_confidence(self, validator):
        """测试判断整体有效性 - 置信度过低"""
        table_validations = [
            TableValidationResult(
                table_name="products",
                table_id="tbl_001",
                is_valid=True,
                exists=True,
                accessible=True,
                data_integrity_score=0.9,
                issues=[],
                metadata={}
            )
        ]
        
        relation_validations = []
        overall_confidence = 0.3  # 低于阈值
        
        is_valid = validator._determine_overall_validity(
            table_validations, relation_validations, overall_confidence
        )
        
        assert is_valid is False
    
    def test_determine_overall_validity_invalid_critical_errors(self, validator):
        """测试判断整体有效性 - 有严重错误"""
        table_validations = [
            TableValidationResult(
                table_name="products",
                table_id="tbl_001",
                is_valid=False,
                exists=True,
                accessible=True,
                data_integrity_score=0.9,
                issues=[
                    ValidationIssue(
                        category=ValidationCategory.EXISTENCE,
                        severity=ValidationSeverity.ERROR,
                        table_name="products",
                        field_name=None,
                        message="严重错误",
                        suggestion="修复错误",
                        details={}
                    )
                ],
                metadata={}
            )
        ]
        
        relation_validations = []
        overall_confidence = 0.8
        
        is_valid = validator._determine_overall_validity(
            table_validations, relation_validations, overall_confidence
        )
        
        assert is_valid is False
    
    def test_get_validation_statistics(self, validator):
        """测试获取验证统计信息"""
        # 模拟一些统计数据
        validator.validation_stats = {
            "total_validations": 10,
            "successful_validations": 8,
            "average_processing_time": 2.5,
            "common_issues": {"existence_error": 2, "integrity_warning": 3}
        }
        
        stats = validator.get_validation_statistics()
        
        assert stats["total_validations"] == 10
        assert stats["successful_validations"] == 8
        assert stats["success_rate"] == 0.8
        assert stats["average_processing_time"] == 2.5
        assert "common_issues" in stats
        assert "configuration" in stats
    
    def test_validate_selection_result_error_handling(self, validator, sample_selection_result):
        """测试验证选表结果的错误处理"""
        with patch.object(validator, '_validate_selected_tables', side_effect=Exception("Mock error")):
            
            result = validator.validate_selection_result(
                selection_result=sample_selection_result,
                data_source_id="ds_001"
            )
            
            # 应该返回错误结果而不是抛出异常
            assert isinstance(result, SelectionValidationResult)
            assert result.is_valid is False
            assert result.overall_confidence == 0.0
            assert "错误" in result.selection_explanation
            assert result.processing_time > 0
    
    def test_update_validation_stats(self, validator):
        """测试更新验证统计信息"""
        # 初始状态
        initial_total = validator.validation_stats["total_validations"]
        initial_successful = validator.validation_stats["successful_validations"]
        
        # 创建成功的验证结果
        validation_result = SelectionValidationResult(
            is_valid=True,
            overall_confidence=0.9,
            table_validations=[],
            relation_validations=[],
            selection_explanation="测试",
            transparency_report={},
            recommendations=[],
            processing_time=1.5
        )
        
        # 更新统计
        validator._update_validation_stats(validation_result, 1.5)
        
        # 验证统计更新
        assert validator.validation_stats["total_validations"] == initial_total + 1
        assert validator.validation_stats["successful_validations"] == initial_successful + 1
        assert validator.validation_stats["average_processing_time"] > 0