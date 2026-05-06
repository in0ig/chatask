# -*- coding: utf-8 -*-
"""
增强版Prompt模板管理系统单元测试
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

from services.prompt_template_manager import (
    TemplateVersionManager,
    EnhancedPromptManager,
    PromptTemplateVersion,
    ABTestConfig,
    TemplateVersion,
    ABTestStatus,
    TemplateMetrics
)


class TestTemplateMetrics:
    """模板指标测试"""
    
    def test_metrics_initialization(self):
        """测试指标初始化"""
        metrics = TemplateMetrics()
        
        assert metrics.usage_count == 0
        assert metrics.success_rate == 0.0
        assert metrics.avg_response_time == 0.0
        assert metrics.user_satisfaction == 0.0
        assert metrics.error_rate == 0.0
        assert metrics.token_efficiency == 0.0
        assert isinstance(metrics.last_updated, datetime)
    
    def test_update_metrics_success(self):
        """测试成功更新指标"""
        metrics = TemplateMetrics()
        
        # 第一次更新
        metrics.update_metrics(success=True, response_time=1.5, satisfaction=4.0, token_count=100)
        
        assert metrics.usage_count == 1
        assert metrics.success_rate == 1.0
        assert metrics.avg_response_time == 1.5
        assert metrics.user_satisfaction == 4.0
        assert metrics.error_rate == 0.0
        assert metrics.token_efficiency == 0.01  # 1/100
        
        # 第二次更新
        metrics.update_metrics(success=False, response_time=2.0, satisfaction=3.0, token_count=200)
        
        assert metrics.usage_count == 2
        assert metrics.success_rate == 0.5  # 1/2
        assert metrics.avg_response_time == 1.75  # (1.5 + 2.0) / 2
        assert metrics.user_satisfaction == 3.5  # (4.0 + 3.0) / 2
        assert metrics.error_rate == 0.5  # 1/2
        assert metrics.token_efficiency == 0.0075  # (0.01 + 0.005) / 2
    
    def test_update_metrics_without_optional_params(self):
        """测试不带可选参数的指标更新"""
        metrics = TemplateMetrics()
        
        metrics.update_metrics(success=True, response_time=1.0)
        
        assert metrics.usage_count == 1
        assert metrics.success_rate == 1.0
        assert metrics.avg_response_time == 1.0
        assert metrics.user_satisfaction == 0.0
        assert metrics.token_efficiency == 0.0


class TestPromptTemplateVersion:
    """Prompt模板版本测试"""
    
    def test_version_initialization(self):
        """测试版本初始化"""
        version = PromptTemplateVersion(
            version_id="test_v1",
            name="test_template",
            content="Hello {{name}}!",
            variables=["name"],
            version=TemplateVersion.DRAFT,
            created_at=datetime.now(),
            created_by="test_user"
        )
        
        assert version.version_id == "test_v1"
        assert version.name == "test_template"
        assert version.content == "Hello {{name}}!"
        assert version.variables == ["name"]
        assert version.version == TemplateVersion.DRAFT
        assert version.created_by == "test_user"
        assert isinstance(version.metrics, TemplateMetrics)
    
    def test_version_id_generation(self):
        """测试版本ID自动生成"""
        version = PromptTemplateVersion(
            version_id="",  # 空ID，应该自动生成
            name="test_template",
            content="Hello {{name}}!",
            variables=["name"],
            version=TemplateVersion.DRAFT,
            created_at=datetime.now(),
            created_by="test_user"
        )
        
        assert version.version_id != ""
        assert "test_template" in version.version_id


class TestABTestConfig:
    """A/B测试配置测试"""
    
    def test_ab_test_initialization(self):
        """测试A/B测试初始化"""
        ab_test = ABTestConfig(
            test_id="test_ab_1",
            name="Test A/B",
            description="Test description",
            template_a_id="template_a",
            template_b_id="template_b"
        )
        
        assert ab_test.test_id == "test_ab_1"
        assert ab_test.name == "Test A/B"
        assert ab_test.template_a_id == "template_a"
        assert ab_test.template_b_id == "template_b"
        assert ab_test.traffic_split == 0.5
        assert ab_test.status == ABTestStatus.PLANNING
        assert ab_test.min_sample_size == 100
        assert ab_test.confidence_level == 0.95
    
    def test_ab_test_id_generation(self):
        """测试A/B测试ID自动生成"""
        ab_test = ABTestConfig(
            test_id="",  # 空ID，应该自动生成
            name="Test A/B",
            description="Test description",
            template_a_id="template_a",
            template_b_id="template_b"
        )
        
        assert ab_test.test_id != ""
        assert "ab_test" in ab_test.test_id
    
    def test_ab_test_end_date_generation(self):
        """测试A/B测试结束日期自动生成"""
        start_date = datetime.now()
        ab_test = ABTestConfig(
            test_id="test_ab_1",
            name="Test A/B",
            description="Test description",
            template_a_id="template_a",
            template_b_id="template_b",
            start_date=start_date
        )
        
        expected_end_date = start_date + timedelta(days=7)
        assert abs((ab_test.end_date - expected_end_date).total_seconds()) < 1


class TestTemplateVersionManager:
    """模板版本管理器测试"""
    
    @pytest.fixture
    def temp_storage_path(self):
        """创建临时存储路径"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name
        yield temp_path
        # 清理
        if os.path.exists(temp_path):
            os.unlink(temp_path)
    
    @pytest.fixture
    def version_manager(self, temp_storage_path):
        """创建版本管理器实例"""
        return TemplateVersionManager(storage_path=temp_storage_path)
    
    def test_create_version(self, version_manager):
        """测试创建版本"""
        version = version_manager.create_version(
            name="test_template",
            content="Hello {{name}}!",
            variables=["name"],
            created_by="test_user",
            description="Test template"
        )
        
        assert version.name == "test_template"
        assert version.content == "Hello {{name}}!"
        assert version.variables == ["name"]
        assert version.version == TemplateVersion.DRAFT
        assert version.created_by == "test_user"
        assert version.description == "Test template"
        
        # 检查是否保存到存储中
        assert "test_template" in version_manager.versions
        assert len(version_manager.versions["test_template"]) == 1
    
    def test_activate_version(self, version_manager):
        """测试激活版本"""
        # 创建两个版本
        version1 = version_manager.create_version(
            name="test_template",
            content="Version 1",
            variables=[],
            created_by="test_user"
        )
        
        version2 = version_manager.create_version(
            name="test_template",
            content="Version 2",
            variables=[],
            created_by="test_user"
        )
        
        # 激活第二个版本
        success = version_manager.activate_version(version2.version_id)
        assert success
        
        # 检查激活状态
        active_version = version_manager.get_active_version("test_template")
        assert active_version.version_id == version2.version_id
        assert active_version.version == TemplateVersion.ACTIVE
        
        # 检查第一个版本是否被归档
        assert version1.version == TemplateVersion.ARCHIVED
    
    def test_activate_nonexistent_version(self, version_manager):
        """测试激活不存在的版本"""
        success = version_manager.activate_version("nonexistent_id")
        assert not success
    
    def test_get_version(self, version_manager):
        """测试获取指定版本"""
        version = version_manager.create_version(
            name="test_template",
            content="Test content",
            variables=[],
            created_by="test_user"
        )
        
        retrieved_version = version_manager.get_version(version.version_id)
        assert retrieved_version is not None
        assert retrieved_version.version_id == version.version_id
        assert retrieved_version.content == "Test content"
        
        # 测试获取不存在的版本
        nonexistent_version = version_manager.get_version("nonexistent_id")
        assert nonexistent_version is None
    
    def test_list_versions(self, version_manager):
        """测试列出版本"""
        # 创建多个版本
        version1 = version_manager.create_version(
            name="test_template",
            content="Version 1",
            variables=[],
            created_by="test_user"
        )
        
        version2 = version_manager.create_version(
            name="test_template",
            content="Version 2",
            variables=[],
            created_by="test_user"
        )
        
        versions = version_manager.list_versions("test_template")
        assert len(versions) == 2
        
        # 检查是否按创建时间倒序排列
        assert versions[0].created_at >= versions[1].created_at
        
        # 测试不存在的模板
        empty_versions = version_manager.list_versions("nonexistent_template")
        assert len(empty_versions) == 0
    
    def test_update_metrics(self, version_manager):
        """测试更新指标"""
        version = version_manager.create_version(
            name="test_template",
            content="Test content",
            variables=[],
            created_by="test_user"
        )
        
        # 更新指标
        version_manager.update_metrics(
            version_id=version.version_id,
            success=True,
            response_time=1.5,
            satisfaction=4.0,
            token_count=100
        )
        
        # 检查指标是否更新
        updated_version = version_manager.get_version(version.version_id)
        assert updated_version.metrics.usage_count == 1
        assert updated_version.metrics.success_rate == 1.0
        assert updated_version.metrics.avg_response_time == 1.5
        assert updated_version.metrics.user_satisfaction == 4.0
        assert updated_version.metrics.token_efficiency == 0.01
    
    def test_create_ab_test(self, version_manager):
        """测试创建A/B测试"""
        # 创建两个版本
        version_a = version_manager.create_version(
            name="test_template",
            content="Version A",
            variables=[],
            created_by="test_user"
        )
        
        version_b = version_manager.create_version(
            name="test_template",
            content="Version B",
            variables=[],
            created_by="test_user"
        )
        
        # 创建A/B测试
        ab_test = version_manager.create_ab_test(
            name="Test A/B",
            description="Test description",
            template_a_id=version_a.version_id,
            template_b_id=version_b.version_id,
            traffic_split=0.6,
            duration_days=14
        )
        
        assert ab_test.name == "Test A/B"
        assert ab_test.template_a_id == version_a.version_id
        assert ab_test.template_b_id == version_b.version_id
        assert ab_test.traffic_split == 0.6
        assert ab_test.status == ABTestStatus.PLANNING
        
        # 检查是否保存到存储中
        assert ab_test.test_id in version_manager.ab_tests
    
    def test_start_stop_ab_test(self, version_manager):
        """测试开始和停止A/B测试"""
        # 创建版本和A/B测试
        version_a = version_manager.create_version(
            name="test_template", content="Version A", variables=[], created_by="test_user"
        )
        version_b = version_manager.create_version(
            name="test_template", content="Version B", variables=[], created_by="test_user"
        )
        
        ab_test = version_manager.create_ab_test(
            name="Test A/B",
            description="Test description",
            template_a_id=version_a.version_id,
            template_b_id=version_b.version_id
        )
        
        # 开始测试
        success = version_manager.start_ab_test(ab_test.test_id)
        assert success
        assert version_manager.ab_tests[ab_test.test_id].status == ABTestStatus.RUNNING
        
        # 停止测试
        success = version_manager.stop_ab_test(ab_test.test_id)
        assert success
        assert version_manager.ab_tests[ab_test.test_id].status == ABTestStatus.COMPLETED
        
        # 测试不存在的测试ID
        assert not version_manager.start_ab_test("nonexistent_id")
        assert not version_manager.stop_ab_test("nonexistent_id")
    
    def test_get_ab_test_template(self, version_manager):
        """测试获取A/B测试模板"""
        # 创建版本
        version_a = version_manager.create_version(
            name="test_template", content="Version A", variables=[], created_by="test_user"
        )
        version_b = version_manager.create_version(
            name="test_template", content="Version B", variables=[], created_by="test_user"
        )
        
        # 激活一个版本作为默认版本
        version_manager.activate_version(version_a.version_id)
        
        # 创建并开始A/B测试
        ab_test = version_manager.create_ab_test(
            name="Test A/B",
            description="Test description",
            template_a_id=version_a.version_id,
            template_b_id=version_b.version_id,
            traffic_split=0.5
        )
        version_manager.start_ab_test(ab_test.test_id)
        
        # 测试流量分配
        # 使用固定的用户ID来测试确定性分配
        template_for_user1 = version_manager.get_ab_test_template("test_template", "user1")
        template_for_user2 = version_manager.get_ab_test_template("test_template", "user2")
        
        assert template_for_user1 is not None
        assert template_for_user2 is not None
        assert template_for_user1.name == "test_template"
        assert template_for_user2.name == "test_template"
        
        # 测试没有A/B测试时返回激活版本
        version_manager.stop_ab_test(ab_test.test_id)
        template_default = version_manager.get_ab_test_template("test_template", "user3")
        assert template_default.version_id == version_a.version_id
    
    def test_analyze_ab_test(self, version_manager):
        """测试A/B测试分析"""
        # 创建版本
        version_a = version_manager.create_version(
            name="test_template", content="Version A", variables=[], created_by="test_user"
        )
        version_b = version_manager.create_version(
            name="test_template", content="Version B", variables=[], created_by="test_user"
        )
        
        # 添加一些指标数据
        version_a.metrics.usage_count = 100
        version_a.metrics.success_rate = 0.8
        version_a.metrics.avg_response_time = 1.5
        
        version_b.metrics.usage_count = 100
        version_b.metrics.success_rate = 0.9
        version_b.metrics.avg_response_time = 1.2
        
        # 创建A/B测试
        ab_test = version_manager.create_ab_test(
            name="Test A/B",
            description="Test description",
            template_a_id=version_a.version_id,
            template_b_id=version_b.version_id,
            min_sample_size=50
        )
        
        # 分析测试结果
        analysis = version_manager.analyze_ab_test(ab_test.test_id)
        
        assert "error" not in analysis
        assert analysis["test_id"] == ab_test.test_id
        assert analysis["test_name"] == "Test A/B"
        assert analysis["primary_metric"] == "success_rate"
        assert analysis["template_a"]["usage_count"] == 100
        assert analysis["template_b"]["usage_count"] == 100
        assert analysis["winner"] == "B"  # B版本成功率更高
        assert "recommendation" in analysis
        
        # 测试不存在的测试
        error_analysis = version_manager.analyze_ab_test("nonexistent_id")
        assert "error" in error_analysis
    
    def test_save_and_load_versions(self, temp_storage_path):
        """测试保存和加载版本数据"""
        # 创建版本管理器并添加数据
        manager1 = TemplateVersionManager(storage_path=temp_storage_path)
        
        version = manager1.create_version(
            name="test_template",
            content="Test content",
            variables=["var1"],
            created_by="test_user",
            description="Test description"
        )
        
        ab_test = manager1.create_ab_test(
            name="Test A/B",
            description="Test description",
            template_a_id=version.version_id,
            template_b_id=version.version_id
        )
        
        # 创建新的管理器实例，应该能加载之前的数据
        manager2 = TemplateVersionManager(storage_path=temp_storage_path)
        
        # 验证数据是否正确加载
        loaded_version = manager2.get_version(version.version_id)
        assert loaded_version is not None
        assert loaded_version.name == "test_template"
        assert loaded_version.content == "Test content"
        assert loaded_version.variables == ["var1"]
        assert loaded_version.created_by == "test_user"
        assert loaded_version.description == "Test description"
        
        assert ab_test.test_id in manager2.ab_tests
        loaded_ab_test = manager2.ab_tests[ab_test.test_id]
        assert loaded_ab_test.name == "Test A/B"


class TestEnhancedPromptManager:
    """增强版Prompt管理器测试"""
    
    @pytest.fixture
    def enhanced_manager(self):
        """创建增强版管理器实例"""
        with patch('src.services.prompt_template_manager.PromptManager') as mock_base_manager:
            with patch('src.services.prompt_template_manager.TemplateVersionManager') as mock_version_manager:
                manager = EnhancedPromptManager()
                manager.base_manager = mock_base_manager.return_value
                manager.version_manager = mock_version_manager.return_value
                return manager
    
    def test_render_prompt_with_ab_test_version_found(self, enhanced_manager):
        """测试使用A/B测试版本渲染Prompt"""
        # 模拟版本管理器返回版本
        mock_version = MagicMock()
        mock_version.version_id = "test_version_1"
        mock_version.content = "Hello {{name}}!"
        mock_version.variables = ["name"]
        
        enhanced_manager.version_manager.get_ab_test_template.return_value = mock_version
        
        # 模拟渲染器
        with patch.object(enhanced_manager, 'renderer') as mock_renderer:
            mock_renderer.render_template_version.return_value = "Hello World!"
            
            rendered, version_id = enhanced_manager.render_prompt_with_ab_test(
                prompt_type="test_type",
                variables={"name": "World"},
                user_id="user123"
            )
            
            assert rendered == "Hello World!"
            assert version_id == "test_version_1"
            
            # 验证调用
            enhanced_manager.version_manager.get_ab_test_template.assert_called_once_with("test_type", "user123")
            mock_renderer.render_template_version.assert_called_once_with(mock_version, {"name": "World"})
    
    def test_render_prompt_with_ab_test_fallback_to_base(self, enhanced_manager):
        """测试回退到基础管理器"""
        # 模拟版本管理器返回None
        enhanced_manager.version_manager.get_ab_test_template.return_value = None
        
        # 模拟基础管理器
        enhanced_manager.base_manager.render_prompt.return_value = "Base template result"
        
        with patch('src.services.prompt_template_manager.PromptType') as mock_prompt_type:
            mock_prompt_type.return_value = "test_enum"
            
            rendered, version_id = enhanced_manager.render_prompt_with_ab_test(
                prompt_type="test_type",
                variables={"name": "World"},
                user_id="user123"
            )
            
            assert rendered == "Base template result"
            assert version_id == "base_template"
    
    def test_record_usage(self, enhanced_manager):
        """测试记录使用情况"""
        enhanced_manager.record_usage(
            version_id="test_version_1",
            success=True,
            response_time=1.5,
            satisfaction=4.0,
            token_count=100
        )
        
        enhanced_manager.version_manager.update_metrics.assert_called_once_with(
            "test_version_1", True, 1.5, 4.0, 100
        )
    
    def test_get_template_performance(self, enhanced_manager):
        """测试获取模板性能报告"""
        # 模拟版本管理器返回性能数据
        mock_performance = {
            "template_name": "test_template",
            "active_version": "version_1",
            "total_versions": 2,
            "versions": []
        }
        
        enhanced_manager.version_manager.list_versions.return_value = []
        enhanced_manager.version_manager.get_active_version.return_value = None
        
        performance = enhanced_manager.get_template_performance("test_template")
        
        assert performance["template_name"] == "test_template"
        assert "total_versions" in performance
        assert "versions" in performance


if __name__ == "__main__":
    pytest.main([__file__])