# -*- coding: utf-8 -*-
"""
增强版Prompt模板管理API单元测试
"""

import pytest
import json
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from fastapi import FastAPI

import sys
import pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent.parent / "src"))

from api.prompt_template_api import router
from services.prompt_template_manager import TemplateVersion, ABTestStatus
from services.few_shot_sample_manager import SampleType, SampleStatus


# 创建测试应用
app = FastAPI()
app.include_router(router)
client = TestClient(app)


class TestTemplateVersionAPI:
    """模板版本管理API测试"""
    
    @patch('src.api.prompt_template_api.enhanced_prompt_manager')
    def test_create_template_version_success(self, mock_manager):
        """测试成功创建模板版本"""
        # 模拟版本管理器返回
        mock_version = MagicMock()
        mock_version.version_id = "test_version_1"
        mock_version.name = "test_template"
        mock_version.version.value = "draft"
        mock_version.created_at.isoformat.return_value = "2024-01-01T00:00:00"
        
        mock_manager.version_manager.create_version.return_value = mock_version
        
        # 发送请求
        response = client.post("/api/prompt-templates/versions", json={
            "name": "test_template",
            "content": "Hello {{name}}!",
            "variables": ["name"],
            "description": "测试模板",
            "created_by": "test_user"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["message"] == "模板版本创建成功"
        assert data["data"]["version_id"] == "test_version_1"
        assert data["data"]["name"] == "test_template"
        
        # 验证调用
        mock_manager.version_manager.create_version.assert_called_once()
    
    @patch('src.api.prompt_template_api.enhanced_prompt_manager')
    def test_create_template_version_error(self, mock_manager):
        """测试创建模板版本失败"""
        mock_manager.version_manager.create_version.side_effect = Exception("创建失败")
        
        response = client.post("/api/prompt-templates/versions", json={
            "name": "test_template",
            "content": "Hello {{name}}!",
            "variables": ["name"]
        })
        
        assert response.status_code == 500
        data = response.json()
        assert "创建模板版本失败" in data["detail"]
    
    @patch('src.api.prompt_template_api.enhanced_prompt_manager')
    def test_list_template_versions(self, mock_manager):
        """测试列出模板版本"""
        # 模拟版本列表
        mock_version1 = MagicMock()
        mock_version1.version_id = "version_1"
        mock_version1.name = "test_template"
        mock_version1.version.value = "active"
        mock_version1.created_at.isoformat.return_value = "2024-01-01T00:00:00"
        mock_version1.created_by = "user1"
        mock_version1.description = "版本1"
        mock_version1.parent_version_id = None
        mock_version1.metrics.usage_count = 10
        mock_version1.metrics.success_rate = 0.9
        mock_version1.metrics.avg_response_time = 1.5
        mock_version1.metrics.user_satisfaction = 4.0
        mock_version1.metrics.error_rate = 0.1
        mock_version1.metrics.token_efficiency = 0.8
        mock_version1.metrics.last_updated.isoformat.return_value = "2024-01-02T00:00:00"
        
        mock_manager.version_manager.list_versions.return_value = [mock_version1]
        
        response = client.get("/api/prompt-templates/versions/test_template")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]["versions"]) == 1
        assert data["data"]["versions"][0]["version_id"] == "version_1"
        assert data["data"]["versions"][0]["metrics"]["usage_count"] == 10
    
    @patch('src.api.prompt_template_api.enhanced_prompt_manager')
    def test_activate_template_version_success(self, mock_manager):
        """测试成功激活模板版本"""
        mock_manager.version_manager.activate_version.return_value = True
        
        response = client.put("/api/prompt-templates/versions/test_version_1/activate")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["message"] == "模板版本激活成功"
        assert data["data"]["version_id"] == "test_version_1"
    
    @patch('src.api.prompt_template_api.enhanced_prompt_manager')
    def test_activate_template_version_not_found(self, mock_manager):
        """测试激活不存在的模板版本"""
        mock_manager.version_manager.activate_version.return_value = False
        
        response = client.put("/api/prompt-templates/versions/nonexistent/activate")
        
        assert response.status_code == 404
        data = response.json()
        assert data["detail"] == "模板版本未找到"
    
    @patch('src.api.prompt_template_api.enhanced_prompt_manager')
    def test_get_template_version_success(self, mock_manager):
        """测试成功获取模板版本详情"""
        mock_version = MagicMock()
        mock_version.version_id = "test_version_1"
        mock_version.name = "test_template"
        mock_version.content = "Hello {{name}}!"
        mock_version.variables = ["name"]
        mock_version.version.value = "active"
        mock_version.created_at.isoformat.return_value = "2024-01-01T00:00:00"
        mock_version.created_by = "test_user"
        mock_version.description = "测试模板"
        mock_version.metadata = {"key": "value"}
        mock_version.parent_version_id = None
        mock_version.metrics.usage_count = 5
        mock_version.metrics.success_rate = 0.8
        mock_version.metrics.avg_response_time = 2.0
        mock_version.metrics.user_satisfaction = 3.5
        mock_version.metrics.error_rate = 0.2
        mock_version.metrics.token_efficiency = 0.7
        mock_version.metrics.last_updated.isoformat.return_value = "2024-01-02T00:00:00"
        
        mock_manager.version_manager.get_version.return_value = mock_version
        
        response = client.get("/api/prompt-templates/versions/test_version_1")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["version_id"] == "test_version_1"
        assert data["data"]["content"] == "Hello {{name}}!"
        assert data["data"]["variables"] == ["name"]
        assert data["data"]["metrics"]["usage_count"] == 5
    
    @patch('src.api.prompt_template_api.enhanced_prompt_manager')
    def test_get_template_version_not_found(self, mock_manager):
        """测试获取不存在的模板版本"""
        mock_manager.version_manager.get_version.return_value = None
        
        response = client.get("/api/prompt-templates/versions/nonexistent")
        
        assert response.status_code == 404
        data = response.json()
        assert data["detail"] == "模板版本未找到"


class TestABTestAPI:
    """A/B测试管理API测试"""
    
    @patch('src.api.prompt_template_api.enhanced_prompt_manager')
    def test_create_ab_test_success(self, mock_manager):
        """测试成功创建A/B测试"""
        mock_ab_test = MagicMock()
        mock_ab_test.test_id = "test_ab_1"
        mock_ab_test.name = "Test A/B"
        mock_ab_test.status.value = "planning"
        mock_ab_test.start_date.isoformat.return_value = "2024-01-01T00:00:00"
        mock_ab_test.end_date.isoformat.return_value = "2024-01-08T00:00:00"
        
        mock_manager.version_manager.create_ab_test.return_value = mock_ab_test
        
        response = client.post("/api/prompt-templates/ab-tests", json={
            "name": "Test A/B",
            "description": "测试A/B测试",
            "template_a_id": "template_a",
            "template_b_id": "template_b",
            "traffic_split": 0.6,
            "duration_days": 7
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["message"] == "A/B测试创建成功"
        assert data["data"]["test_id"] == "test_ab_1"
    
    @patch('src.api.prompt_template_api.enhanced_prompt_manager')
    def test_start_ab_test_success(self, mock_manager):
        """测试成功开始A/B测试"""
        mock_manager.version_manager.start_ab_test.return_value = True
        
        response = client.put("/api/prompt-templates/ab-tests/test_ab_1/start")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["message"] == "A/B测试已开始"
    
    @patch('src.api.prompt_template_api.enhanced_prompt_manager')
    def test_stop_ab_test_success(self, mock_manager):
        """测试成功停止A/B测试"""
        mock_manager.version_manager.stop_ab_test.return_value = True
        
        response = client.put("/api/prompt-templates/ab-tests/test_ab_1/stop")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["message"] == "A/B测试已停止"
    
    @patch('src.api.prompt_template_api.enhanced_prompt_manager')
    def test_analyze_ab_test_success(self, mock_manager):
        """测试成功分析A/B测试"""
        mock_analysis = {
            "test_id": "test_ab_1",
            "test_name": "Test A/B",
            "status": "completed",
            "primary_metric": "success_rate",
            "template_a": {
                "version_id": "template_a",
                "usage_count": 100,
                "success_rate": 0.8,
                "primary_metric_value": 0.8
            },
            "template_b": {
                "version_id": "template_b",
                "usage_count": 100,
                "success_rate": 0.9,
                "primary_metric_value": 0.9
            },
            "statistical_significance": {"significant": True},
            "winner": "B",
            "recommendation": "建议采用版本B"
        }
        
        mock_manager.version_manager.analyze_ab_test.return_value = mock_analysis
        
        response = client.get("/api/prompt-templates/ab-tests/test_ab_1/analysis")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["winner"] == "B"
        assert data["data"]["recommendation"] == "建议采用版本B"
    
    @patch('src.api.prompt_template_api.enhanced_prompt_manager')
    def test_analyze_ab_test_not_found(self, mock_manager):
        """测试分析不存在的A/B测试"""
        mock_manager.version_manager.analyze_ab_test.return_value = {"error": "A/B test not found"}
        
        response = client.get("/api/prompt-templates/ab-tests/nonexistent/analysis")
        
        assert response.status_code == 404
        data = response.json()
        assert data["detail"] == "A/B test not found"


class TestPromptRenderAPI:
    """Prompt渲染API测试"""
    
    @patch('src.api.prompt_template_api.enhanced_prompt_manager')
    def test_render_prompt_success(self, mock_manager):
        """测试成功渲染Prompt"""
        mock_manager.render_prompt_with_ab_test.return_value = ("Hello World!", "version_1")
        
        response = client.post("/api/prompt-templates/render", json={
            "prompt_type": "greeting",
            "variables": {"name": "World"},
            "user_id": "user123"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["rendered_prompt"] == "Hello World!"
        assert data["data"]["version_id"] == "version_1"
        assert data["data"]["prompt_type"] == "greeting"
    
    @patch('src.api.prompt_template_api.enhanced_prompt_manager')
    def test_render_prompt_error(self, mock_manager):
        """测试渲染Prompt失败"""
        mock_manager.render_prompt_with_ab_test.side_effect = Exception("渲染失败")
        
        response = client.post("/api/prompt-templates/render", json={
            "prompt_type": "greeting",
            "variables": {"name": "World"}
        })
        
        assert response.status_code == 500
        data = response.json()
        assert "渲染Prompt失败" in data["detail"]


class TestMetricsAPI:
    """指标管理API测试"""
    
    @patch('src.api.prompt_template_api.enhanced_prompt_manager')
    def test_update_metrics_success(self, mock_manager):
        """测试成功更新指标"""
        response = client.post("/api/prompt-templates/metrics/update", json={
            "version_id": "version_1",
            "success": True,
            "response_time": 1.5,
            "satisfaction": 4.0,
            "token_count": 100
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["message"] == "指标更新成功"
        
        # 验证调用
        mock_manager.record_usage.assert_called_once_with(
            version_id="version_1",
            success=True,
            response_time=1.5,
            satisfaction=4.0,
            token_count=100
        )
    
    @patch('src.api.prompt_template_api.enhanced_prompt_manager')
    def test_get_template_performance_success(self, mock_manager):
        """测试成功获取模板性能报告"""
        mock_performance = {
            "template_name": "test_template",
            "active_version": "version_1",
            "total_versions": 2,
            "versions": [
                {
                    "version_id": "version_1",
                    "metrics": {
                        "usage_count": 100,
                        "success_rate": 0.9
                    }
                }
            ]
        }
        
        mock_manager.get_template_performance.return_value = mock_performance
        
        response = client.get("/api/prompt-templates/performance/test_template")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["template_name"] == "test_template"
        assert data["data"]["total_versions"] == 2
    
    @patch('src.api.prompt_template_api.enhanced_prompt_manager')
    def test_get_template_performance_not_found(self, mock_manager):
        """测试获取不存在模板的性能报告"""
        mock_manager.get_template_performance.return_value = {"error": "No versions found"}
        
        response = client.get("/api/prompt-templates/performance/nonexistent")
        
        assert response.status_code == 404
        data = response.json()
        assert data["detail"] == "No versions found"


class TestFewShotSampleAPI:
    """Few-Shot样本管理API测试"""
    
    @patch('src.api.prompt_template_api.enhanced_few_shot_manager')
    def test_create_sample_success(self, mock_manager):
        """测试成功创建样本"""
        mock_manager.add_sample.return_value = (True, [])
        
        response = client.post("/api/prompt-templates/samples", json={
            "prompt_type": "sql_generation",
            "input_text": "查询用户信息",
            "output_text": '{"sql": "SELECT * FROM users;"}',
            "sample_type": "positive",
            "description": "测试样本",
            "tags": ["sql", "users"],
            "created_by": "test_user"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["message"] == "样本创建成功"
    
    @patch('src.api.prompt_template_api.enhanced_few_shot_manager')
    def test_create_sample_with_warnings(self, mock_manager):
        """测试创建样本带警告"""
        mock_manager.add_sample.return_value = (True, ["Auto-fixed: 清理了输入"])
        
        response = client.post("/api/prompt-templates/samples", json={
            "prompt_type": "sql_generation",
            "input_text": "查询用户信息",
            "output_text": '{"sql": "SELECT * FROM users;"}',
            "sample_type": "positive"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["warnings"] == ["Auto-fixed: 清理了输入"]
    
    @patch('src.api.prompt_template_api.enhanced_few_shot_manager')
    def test_create_sample_failure(self, mock_manager):
        """测试创建样本失败"""
        mock_manager.add_sample.return_value = (False, ["输入文本过短"])
        
        response = client.post("/api/prompt-templates/samples", json={
            "prompt_type": "sql_generation",
            "input_text": "短",
            "output_text": "短",
            "sample_type": "positive"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert data["data"]["errors"] == ["输入文本过短"]
    
    @patch('src.api.prompt_template_api.enhanced_few_shot_manager')
    def test_get_similar_samples_success(self, mock_manager):
        """测试成功获取相似样本"""
        mock_sample = MagicMock()
        mock_sample.sample_id = "sample_1"
        mock_sample.input_text = "查询用户信息"
        mock_sample.output_text = '{"sql": "SELECT * FROM users;"}'
        mock_sample.sample_type.value = "positive"
        mock_sample.description = "测试样本"
        mock_sample.tags = ["sql", "users"]
        mock_sample.metrics.usage_count = 10
        mock_sample.metrics.success_rate = 0.9
        mock_sample.metrics.user_feedback_score = 4.0
        
        mock_manager.get_similar_samples.return_value = [(mock_sample, 0.8)]
        
        response = client.get(
            "/api/prompt-templates/samples/sql_generation/similar",
            params={
                "query_text": "查询用户数据",
                "max_samples": 3,
                "min_similarity": 0.3
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]["samples"]) == 1
        assert data["data"]["samples"][0]["sample_id"] == "sample_1"
        assert data["data"]["samples"][0]["similarity_score"] == 0.8
    
    @patch('src.api.prompt_template_api.enhanced_few_shot_manager')
    def test_get_best_samples_success(self, mock_manager):
        """测试成功获取最佳样本"""
        mock_sample = MagicMock()
        mock_sample.sample_id = "sample_1"
        mock_sample.input_text = "查询用户信息"
        mock_sample.output_text = '{"sql": "SELECT * FROM users;"}'
        mock_sample.sample_type.value = "positive"
        mock_sample.status.value = "validated"
        mock_sample.description = "测试样本"
        mock_sample.tags = ["sql", "users"]
        mock_sample.created_at.isoformat.return_value = "2024-01-01T00:00:00"
        mock_sample.metrics.usage_count = 10
        mock_sample.metrics.success_rate = 0.9
        mock_sample.metrics.user_feedback_score = 4.0
        mock_sample.metrics.validation_score = 0.95
        
        mock_manager.get_best_samples.return_value = [mock_sample]
        
        response = client.get(
            "/api/prompt-templates/samples/sql_generation/best",
            params={"max_samples": 5}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]["samples"]) == 1
        assert data["data"]["samples"][0]["sample_id"] == "sample_1"
    
    @patch('src.api.prompt_template_api.enhanced_few_shot_manager')
    def test_get_sample_statistics_success(self, mock_manager):
        """测试成功获取样本统计信息"""
        mock_stats = {
            "total_samples": 100,
            "status_distribution": {"validated": 80, "draft": 20},
            "type_distribution": {"positive": 90, "negative": 10},
            "quality_metrics": {
                "avg_validation_score": 0.85,
                "avg_success_rate": 0.9,
                "avg_user_feedback": 4.2
            }
        }
        
        mock_manager.get_sample_statistics.return_value = mock_stats
        
        response = client.get("/api/prompt-templates/samples/statistics")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["total_samples"] == 100
        assert "quality_metrics" in data["data"]
    
    @patch('src.api.prompt_template_api.enhanced_few_shot_manager')
    def test_update_sample_feedback_success(self, mock_manager):
        """测试成功更新样本反馈"""
        mock_manager.update_sample_feedback.return_value = True
        
        response = client.post(
            "/api/prompt-templates/samples/sample_1/feedback",
            json={"success": True, "user_feedback": 4.5}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["message"] == "样本反馈更新成功"
    
    @patch('src.api.prompt_template_api.enhanced_few_shot_manager')
    def test_update_sample_feedback_not_found(self, mock_manager):
        """测试更新不存在样本的反馈"""
        mock_manager.update_sample_feedback.return_value = False
        
        response = client.post(
            "/api/prompt-templates/samples/nonexistent/feedback",
            json={"success": True}
        )
        
        assert response.status_code == 404
        data = response.json()
        assert data["detail"] == "样本未找到"
    
    @patch('src.api.prompt_template_api.enhanced_few_shot_manager')
    def test_cleanup_low_quality_samples_success(self, mock_manager):
        """测试成功清理低质量样本"""
        mock_manager.cleanup_low_quality_samples.return_value = 5
        
        response = client.delete(
            "/api/prompt-templates/samples/cleanup",
            params={
                "min_validation_score": 0.5,
                "min_success_rate": 0.3,
                "min_usage_count": 5
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "移除了 5 个低质量样本" in data["message"]
        assert data["data"]["removed_count"] == 5


if __name__ == "__main__":
    pytest.main([__file__])