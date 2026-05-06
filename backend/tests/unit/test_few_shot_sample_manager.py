# -*- coding: utf-8 -*-
"""
增强版Few-Shot样本管理系统单元测试
"""

import pytest
import json
import os
import tempfile
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

import sys
import pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent.parent / "src"))

from services.few_shot_sample_manager import (
    EnhancedFewShotManager,
    FewShotSample,
    SampleType,
    SampleStatus,
    SampleMetrics,
    SemanticSimilarityCalculator,
    SampleValidator
)


class TestSampleMetrics:
    """样本指标测试"""
    
    def test_metrics_initialization(self):
        """测试指标初始化"""
        metrics = SampleMetrics()
        
        assert metrics.usage_count == 0
        assert metrics.success_rate == 0.0
        assert metrics.avg_similarity_score == 0.0
        assert metrics.user_feedback_score == 0.0
        assert metrics.last_used is None
        assert metrics.validation_score == 0.0
    
    def test_update_usage(self):
        """测试更新使用情况"""
        metrics = SampleMetrics()
        
        # 第一次更新
        metrics.update_usage(success=True, similarity_score=0.8, user_feedback=4.0)
        
        assert metrics.usage_count == 1
        assert metrics.success_rate == 1.0
        assert metrics.avg_similarity_score == 0.8
        assert metrics.user_feedback_score == 4.0
        assert metrics.last_used is not None
        
        # 第二次更新
        metrics.update_usage(success=False, similarity_score=0.6, user_feedback=3.0)
        
        assert metrics.usage_count == 2
        assert metrics.success_rate == 0.5  # 1/2
        assert metrics.avg_similarity_score == 0.7  # (0.8 + 0.6) / 2
        assert metrics.user_feedback_score == 3.5  # (4.0 + 3.0) / 2


class TestFewShotSample:
    """Few-Shot样本测试"""
    
    def test_sample_initialization(self):
        """测试样本初始化"""
        sample = FewShotSample(
            sample_id="test_sample_1",
            prompt_type="sql_generation",
            input_text="查询用户信息",
            output_text='{"sql": "SELECT * FROM users;"}',
            sample_type=SampleType.POSITIVE,
            status=SampleStatus.VALIDATED,
            created_by="test_user",
            description="测试样本",
            tags=["sql", "users"]
        )
        
        assert sample.sample_id == "test_sample_1"
        assert sample.prompt_type == "sql_generation"
        assert sample.input_text == "查询用户信息"
        assert sample.output_text == '{"sql": "SELECT * FROM users;"}'
        assert sample.sample_type == SampleType.POSITIVE
        assert sample.status == SampleStatus.VALIDATED
        assert sample.created_by == "test_user"
        assert sample.description == "测试样本"
        assert sample.tags == ["sql", "users"]
        assert isinstance(sample.metrics, SampleMetrics)
        assert isinstance(sample.created_at, datetime)
    
    def test_sample_id_generation(self):
        """测试样本ID自动生成"""
        sample = FewShotSample(
            sample_id="",  # 空ID，应该自动生成
            prompt_type="sql_generation",
            input_text="测试输入",
            output_text="测试输出"
        )
        
        assert sample.sample_id != ""
        assert "sql_generation" in sample.sample_id


class TestSemanticSimilarityCalculator:
    """语义相似度计算器测试"""
    
    @pytest.fixture
    def calculator(self):
        """创建计算器实例"""
        return SemanticSimilarityCalculator()
    
    def test_tokenize(self, calculator):
        """测试分词功能"""
        text = "Hello, World! This is a test."
        tokens = calculator._tokenize(text)
        
        expected_tokens = ["hello", "world", "this", "is", "test"]
        assert tokens == expected_tokens
    
    def test_calculate_tf(self, calculator):
        """测试词频计算"""
        tokens = ["hello", "world", "hello", "test"]
        tf = calculator._calculate_tf(tokens)
        
        assert tf["hello"] == 0.5  # 2/4
        assert tf["world"] == 0.25  # 1/4
        assert tf["test"] == 0.25  # 1/4
    
    def test_calculate_idf(self, calculator):
        """测试逆文档频率计算"""
        documents = [
            ["hello", "world"],
            ["hello", "test"],
            ["world", "test"]
        ]
        
        idf = calculator._calculate_idf(documents)
        
        # hello出现在2个文档中，idf = log(3/2)
        # world出现在2个文档中，idf = log(3/2)
        # test出现在2个文档中，idf = log(3/2)
        import math
        expected_idf = math.log(3/2)
        
        assert abs(idf["hello"] - expected_idf) < 0.001
        assert abs(idf["world"] - expected_idf) < 0.001
        assert abs(idf["test"] - expected_idf) < 0.001
    
    def test_calculate_similarity_jaccard(self, calculator):
        """测试Jaccard相似度计算"""
        text1 = "hello world test"
        text2 = "hello world example"
        
        similarity = calculator.calculate_similarity(text1, text2)
        
        # 交集: {hello, world}，并集: {hello, world, test, example}
        # Jaccard = 2/4 = 0.5
        assert abs(similarity - 0.5) < 0.001
    
    def test_calculate_similarity_empty_text(self, calculator):
        """测试空文本相似度计算"""
        similarity1 = calculator.calculate_similarity("", "hello world")
        similarity2 = calculator.calculate_similarity("hello world", "")
        similarity3 = calculator.calculate_similarity("", "")
        
        assert similarity1 == 0.0
        assert similarity2 == 0.0
        assert similarity3 == 0.0
    
    def test_find_most_similar(self, calculator):
        """测试查找最相似文本"""
        query_text = "查询用户信息"
        candidate_texts = [
            "查询所有用户",
            "删除用户数据",
            "更新用户信息",
            "查询产品信息"
        ]
        
        similarities = calculator.find_most_similar(query_text, candidate_texts, top_k=2)
        
        assert len(similarities) == 2
        assert similarities[0][1] >= similarities[1][1]  # 按相似度降序排列
        
        # 第一个应该是"查询所有用户"或"更新用户信息"（包含"查询"或"用户信息"）
        top_candidate_idx = similarities[0][0]
        assert top_candidate_idx in [0, 2]


class TestSampleValidator:
    """样本验证器测试"""
    
    @pytest.fixture
    def validator(self):
        """创建验证器实例"""
        return SampleValidator()
    
    def test_validate_valid_sample(self, validator):
        """测试验证有效样本"""
        sample = FewShotSample(
            sample_id="test_sample",
            prompt_type="sql_generation",
            input_text="查询用户信息，包含姓名和邮箱",
            output_text='{"sql": "SELECT name, email FROM users;", "explanation": "查询用户表"}',
            sample_type=SampleType.POSITIVE
        )
        
        is_valid, errors = validator.validate_sample(sample)
        
        assert is_valid
        assert len(errors) == 0
        assert sample.metrics.validation_score == 1.0
    
    def test_validate_short_input(self, validator):
        """测试验证输入过短的样本"""
        sample = FewShotSample(
            sample_id="test_sample",
            prompt_type="sql_generation",
            input_text="短",  # 太短
            output_text='{"sql": "SELECT * FROM users;"}',
            sample_type=SampleType.POSITIVE
        )
        
        is_valid, errors = validator.validate_sample(sample)
        
        assert not is_valid
        assert len(errors) > 0
        assert "输入文本过短" in errors[0]
        assert sample.metrics.validation_score < 1.0
    
    def test_validate_long_input(self, validator):
        """测试验证输入过长的样本"""
        sample = FewShotSample(
            sample_id="test_sample",
            prompt_type="sql_generation",
            input_text="x" * 3000,  # 太长
            output_text='{"sql": "SELECT * FROM users;"}',
            sample_type=SampleType.POSITIVE
        )
        
        is_valid, errors = validator.validate_sample(sample)
        
        assert not is_valid
        assert len(errors) > 0
        assert "输入文本过长" in errors[0]
    
    def test_validate_forbidden_patterns(self, validator):
        """测试验证禁用模式"""
        sample = FewShotSample(
            sample_id="test_sample",
            prompt_type="sql_generation",
            input_text="查询用户信息<script>alert('xss')</script>",
            output_text='{"sql": "SELECT * FROM users;"}',
            sample_type=SampleType.POSITIVE
        )
        
        is_valid, errors = validator.validate_sample(sample)
        
        assert not is_valid
        assert len(errors) > 0
        assert "禁用模式" in errors[0]
    
    def test_validate_invalid_json_output(self, validator):
        """测试验证无效JSON输出"""
        sample = FewShotSample(
            sample_id="test_sample",
            prompt_type="sql_generation",
            input_text="查询用户信息，包含姓名和邮箱",
            output_text='{"sql": "SELECT * FROM users;", invalid json}',  # 无效JSON
            sample_type=SampleType.POSITIVE
        )
        
        is_valid, errors = validator.validate_sample(sample)
        
        assert not is_valid
        assert len(errors) > 0
        assert "不是有效的JSON格式" in errors[0]
    
    def test_auto_fix_sample(self, validator):
        """测试自动修复样本"""
        sample = FewShotSample(
            sample_id="test_sample",
            prompt_type="sql_generation",
            input_text="  查询用户<script>alert('xss')</script>  ",
            output_text="  结果输出  ",
            sample_type=SampleType.POSITIVE
        )
        
        fixed_sample = validator.auto_fix_sample(sample)
        
        assert fixed_sample.input_text == "查询用户"  # 去除空格和脚本
        assert fixed_sample.output_text == "结果输出"  # 去除空格


class TestEnhancedFewShotManager:
    """增强版Few-Shot样本管理器测试"""
    
    @pytest.fixture
    def temp_samples_path(self):
        """创建临时样本存储路径"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name
        yield temp_path
        # 清理
        if os.path.exists(temp_path):
            os.unlink(temp_path)
    
    @pytest.fixture
    def few_shot_manager(self, temp_samples_path):
        """创建Few-Shot管理器实例"""
        return EnhancedFewShotManager(samples_path=temp_samples_path)
    
    def test_add_valid_sample(self, few_shot_manager):
        """测试添加有效样本"""
        success, errors = few_shot_manager.add_sample(
            prompt_type="sql_generation",
            input_text="查询用户信息，包含姓名和邮箱地址",
            output_text='{"sql": "SELECT name, email FROM users;", "explanation": "查询用户表的姓名和邮箱字段"}',
            sample_type=SampleType.POSITIVE,
            description="基础查询示例",
            tags=["sql", "users", "basic"],
            created_by="test_user"
        )
        
        assert success
        assert len(errors) == 0
        
        # 检查样本是否添加到存储中
        assert "sql_generation" in few_shot_manager.samples
        assert len(few_shot_manager.samples["sql_generation"]) > 0
        
        # 检查样本属性
        added_sample = few_shot_manager.samples["sql_generation"][-1]
        assert added_sample.input_text == "查询用户信息，包含姓名和邮箱地址"
        assert added_sample.sample_type == SampleType.POSITIVE
        assert added_sample.status == SampleStatus.VALIDATED
        assert added_sample.created_by == "test_user"
        assert added_sample.description == "基础查询示例"
        assert added_sample.tags == ["sql", "users", "basic"]
    
    def test_add_invalid_sample_with_auto_fix(self, few_shot_manager):
        """测试添加无效样本并自动修复"""
        success, errors = few_shot_manager.add_sample(
            prompt_type="sql_generation",
            input_text="  查询用户信息包含姓名和邮箱<script>alert('test')</script>  ",
            output_text='{"sql": "SELECT * FROM users;"}',
            sample_type=SampleType.POSITIVE
        )
        
        assert success
        assert len(errors) > 0  # 有警告信息（自动修复）
        assert "Auto-fixed" in errors[0]
        
        # 检查样本是否被修复并添加
        added_sample = few_shot_manager.samples["sql_generation"][-1]
        assert "<script>" not in added_sample.input_text
        assert added_sample.validation_notes.startswith("Auto-fixed")
    
    def test_add_invalid_sample_cannot_fix(self, few_shot_manager):
        """测试添加无法修复的无效样本"""
        success, errors = few_shot_manager.add_sample(
            prompt_type="sql_generation",
            input_text="短",  # 太短，无法修复
            output_text="短",  # 太短，无法修复
            sample_type=SampleType.POSITIVE
        )
        
        assert not success
        assert len(errors) > 0
        assert "过短" in str(errors)
    
    def test_get_similar_samples(self, few_shot_manager):
        """测试获取相似样本"""
        # 添加一些样本
        few_shot_manager.add_sample(
            prompt_type="sql_generation",
            input_text="查询所有用户的姓名和邮箱",
            output_text='{"sql": "SELECT name, email FROM users;"}',
            sample_type=SampleType.POSITIVE
        )
        
        few_shot_manager.add_sample(
            prompt_type="sql_generation",
            input_text="删除用户数据",
            output_text='{"sql": "DELETE FROM users WHERE id = ?;"}',
            sample_type=SampleType.POSITIVE
        )
        
        few_shot_manager.add_sample(
            prompt_type="sql_generation",
            input_text="查询产品信息",
            output_text='{"sql": "SELECT * FROM products;"}',
            sample_type=SampleType.POSITIVE
        )
        
        # 查询相似样本
        similar_samples = few_shot_manager.get_similar_samples(
            prompt_type="sql_generation",
            query_text="查询用户信息",
            max_samples=2,
            min_similarity=0.1
        )
        
        assert len(similar_samples) <= 2
        
        if similar_samples:
            sample, similarity_score = similar_samples[0]
            assert isinstance(sample, FewShotSample)
            assert 0.0 <= similarity_score <= 1.0
            assert sample.prompt_type == "sql_generation"
            
            # 检查使用统计是否更新
            assert sample.metrics.usage_count > 0
    
    def test_get_best_samples(self, few_shot_manager):
        """测试获取最佳样本"""
        # 添加样本并设置不同的指标
        few_shot_manager.add_sample(
            prompt_type="sql_generation",
            input_text="查询用户信息包含姓名和邮箱地址",
            output_text='{"sql": "SELECT * FROM users;"}',
            sample_type=SampleType.POSITIVE
        )
        
        # 手动设置指标以测试排序
        sample = few_shot_manager.samples["sql_generation"][-1]
        sample.metrics.validation_score = 0.9
        sample.metrics.success_rate = 0.8
        sample.metrics.user_feedback_score = 4.0
        sample.metrics.usage_count = 50
        
        few_shot_manager.add_sample(
            prompt_type="sql_generation",
            input_text="查询产品信息包含名称和价格",
            output_text='{"sql": "SELECT * FROM products;"}',
            sample_type=SampleType.POSITIVE
        )
        
        # 设置较低的指标
        sample2 = few_shot_manager.samples["sql_generation"][-1]
        sample2.metrics.validation_score = 0.7
        sample2.metrics.success_rate = 0.6
        sample2.metrics.user_feedback_score = 3.0
        sample2.metrics.usage_count = 10
        
        # 获取最佳样本
        best_samples = few_shot_manager.get_best_samples(
            prompt_type="sql_generation",
            max_samples=2
        )
        
        assert len(best_samples) <= 2
        
        if len(best_samples) >= 2:
            # 第一个样本应该有更高的综合评分
            assert best_samples[0].metrics.validation_score >= best_samples[1].metrics.validation_score
    
    def test_update_sample_feedback(self, few_shot_manager):
        """测试更新样本反馈"""
        # 添加样本
        few_shot_manager.add_sample(
            prompt_type="sql_generation",
            input_text="查询用户信息包含姓名和邮箱地址",
            output_text='{"sql": "SELECT * FROM users;"}',
            sample_type=SampleType.POSITIVE
        )
        
        sample = few_shot_manager.samples["sql_generation"][-1]
        sample_id = sample.sample_id
        
        # 更新反馈
        success = few_shot_manager.update_sample_feedback(
            sample_id=sample_id,
            success=True,
            user_feedback=4.5
        )
        
        assert success
        assert sample.metrics.usage_count > 0
        assert sample.metrics.user_feedback_score == 4.5
        
        # 测试不存在的样本ID
        success = few_shot_manager.update_sample_feedback(
            sample_id="nonexistent_id",
            success=True
        )
        assert not success
    
    def test_get_sample_statistics(self, few_shot_manager):
        """测试获取样本统计信息"""
        # 添加不同类型的样本
        few_shot_manager.add_sample(
            prompt_type="sql_generation",
            input_text="查询用户信息包含姓名和邮箱地址",
            output_text='{"sql": "SELECT * FROM users;"}',
            sample_type=SampleType.POSITIVE
        )
        
        few_shot_manager.add_sample(
            prompt_type="sql_generation",
            input_text="错误的查询示例包含无效语法",
            output_text='{"error": "Invalid query"}',
            sample_type=SampleType.NEGATIVE
        )
        
        few_shot_manager.add_sample(
            prompt_type="intent_recognition",
            input_text="生成本月销售报告包含详细数据",
            output_text='{"intent": "report"}',
            sample_type=SampleType.POSITIVE
        )
        
        # 获取所有样本的统计信息
        stats = few_shot_manager.get_sample_statistics()
        
        assert stats["total_samples"] >= 3
        assert "status_distribution" in stats
        assert "type_distribution" in stats
        assert "quality_metrics" in stats
        assert "recent_activity" in stats
        
        # 获取特定类型的统计信息
        sql_stats = few_shot_manager.get_sample_statistics("sql_generation")
        assert sql_stats["total_samples"] >= 2
    
    def test_cleanup_low_quality_samples(self, few_shot_manager):
        """测试清理低质量样本"""
        # 添加样本并设置不同的质量指标
        few_shot_manager.add_sample(
            prompt_type="sql_generation",
            input_text="高质量样本查询用户信息",
            output_text='{"sql": "SELECT * FROM users;"}',
            sample_type=SampleType.POSITIVE
        )
        
        high_quality_sample = few_shot_manager.samples["sql_generation"][-1]
        high_quality_sample.metrics.validation_score = 0.9
        high_quality_sample.metrics.success_rate = 0.8
        high_quality_sample.metrics.usage_count = 10
        
        few_shot_manager.add_sample(
            prompt_type="sql_generation",
            input_text="低质量样本查询产品信息",
            output_text='{"sql": "SELECT * FROM users;"}',
            sample_type=SampleType.POSITIVE
        )
        
        low_quality_sample = few_shot_manager.samples["sql_generation"][-1]
        low_quality_sample.metrics.validation_score = 0.3  # 低于阈值
        low_quality_sample.metrics.success_rate = 0.2  # 低于阈值
        low_quality_sample.metrics.usage_count = 10  # 足够的使用次数
        
        # 清理低质量样本
        removed_count = few_shot_manager.cleanup_low_quality_samples(
            min_validation_score=0.5,
            min_success_rate=0.3,
            min_usage_count=5
        )
        
        assert removed_count >= 1
        
        # 检查高质量样本是否保留
        remaining_samples = few_shot_manager.samples["sql_generation"]
        high_quality_found = any(
            sample.metrics.validation_score >= 0.5 and sample.metrics.success_rate >= 0.3
            for sample in remaining_samples
            if sample.metrics.usage_count >= 5
        )
        assert high_quality_found
    
    def test_save_and_load_samples(self, temp_samples_path):
        """测试保存和加载样本数据"""
        # 创建管理器并添加样本
        manager1 = EnhancedFewShotManager(samples_path=temp_samples_path)
        
        manager1.add_sample(
            prompt_type="sql_generation",
            input_text="查询用户信息包含姓名和邮箱地址",
            output_text='{"sql": "SELECT * FROM users;"}',
            sample_type=SampleType.POSITIVE,
            description="测试样本",
            tags=["test"],
            created_by="test_user"
        )
        
        sample = manager1.samples["sql_generation"][-1]
        sample_id = sample.sample_id
        
        # 创建新的管理器实例，应该能加载之前的数据
        manager2 = EnhancedFewShotManager(samples_path=temp_samples_path)
        
        # 验证数据是否正确加载
        assert "sql_generation" in manager2.samples
        assert len(manager2.samples["sql_generation"]) > 0
        
        loaded_sample = None
        for sample in manager2.samples["sql_generation"]:
            if sample.sample_id == sample_id:
                loaded_sample = sample
                break
        
        assert loaded_sample is not None
        assert loaded_sample.input_text == "查询用户信息包含姓名和邮箱地址"
        assert loaded_sample.output_text == '{"sql": "SELECT * FROM users;"}'
        assert loaded_sample.sample_type == SampleType.POSITIVE
        assert loaded_sample.description == "测试样本"
        assert loaded_sample.tags == ["test"]
        assert loaded_sample.created_by == "test_user"


if __name__ == "__main__":
    pytest.main([__file__])