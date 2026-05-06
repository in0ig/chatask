# -*- coding: utf-8 -*-
"""
增强版Prompt模板管理和渲染引擎
实现版本管理、A/B测试、模板效果评估和优化
"""

import os
import yaml
import json
import re
import hashlib
from typing import Dict, List, Optional, Any, Union, Tuple
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from datetime import datetime, timedelta
import statistics
from collections import defaultdict

from src.utils import logger


class TemplateVersion(Enum):
    """模板版本类型"""
    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"
    TESTING = "testing"


class ABTestStatus(Enum):
    """A/B测试状态"""
    PLANNING = "planning"
    RUNNING = "running"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


@dataclass
class TemplateMetrics:
    """模板效果指标"""
    usage_count: int = 0
    success_rate: float = 0.0
    avg_response_time: float = 0.0
    user_satisfaction: float = 0.0
    error_rate: float = 0.0
    token_efficiency: float = 0.0
    last_updated: datetime = field(default_factory=datetime.now)
    
    def update_metrics(self, success: bool, response_time: float, 
                      satisfaction: Optional[float] = None, 
                      token_count: Optional[int] = None):
        """更新指标"""
        self.usage_count += 1
        
        # 更新成功率
        current_success_count = int(self.success_rate * (self.usage_count - 1))
        if success:
            current_success_count += 1
        self.success_rate = current_success_count / self.usage_count
        
        # 更新平均响应时间
        total_time = self.avg_response_time * (self.usage_count - 1) + response_time
        self.avg_response_time = total_time / self.usage_count
        
        # 更新用户满意度
        if satisfaction is not None:
            if self.user_satisfaction == 0:
                self.user_satisfaction = satisfaction
            else:
                self.user_satisfaction = (self.user_satisfaction + satisfaction) / 2
        
        # 更新错误率
        if not success:
            error_count = int(self.error_rate * (self.usage_count - 1)) + 1
            self.error_rate = error_count / self.usage_count
        
        # 更新Token效率
        if token_count is not None:
            if self.token_efficiency == 0:
                self.token_efficiency = 1.0 / token_count if token_count > 0 else 1.0
            else:
                current_efficiency = 1.0 / token_count if token_count > 0 else 1.0
                self.token_efficiency = (self.token_efficiency + current_efficiency) / 2
        
        self.last_updated = datetime.now()


@dataclass
class PromptTemplateVersion:
    """Prompt模板版本"""
    version_id: str
    name: str
    content: str
    variables: List[str]
    version: TemplateVersion
    created_at: datetime
    created_by: str
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    metrics: TemplateMetrics = field(default_factory=TemplateMetrics)
    parent_version_id: Optional[str] = None
    
    def __post_init__(self):
        if not self.version_id:
            self.version_id = self._generate_version_id()
    
    def _generate_version_id(self) -> str:
        """生成版本ID"""
        content_hash = hashlib.md5(self.content.encode()).hexdigest()[:8]
        timestamp = int(datetime.now().timestamp())
        return f"{self.name}_{timestamp}_{content_hash}"


@dataclass
class ABTestConfig:
    """A/B测试配置"""
    test_id: str
    name: str
    description: str
    template_a_id: str
    template_b_id: str
    traffic_split: float = 0.5  # A版本流量比例
    start_date: datetime = field(default_factory=datetime.now)
    end_date: Optional[datetime] = None
    status: ABTestStatus = ABTestStatus.PLANNING
    min_sample_size: int = 100
    confidence_level: float = 0.95
    success_metric: str = "success_rate"  # success_rate, response_time, user_satisfaction
    
    def __post_init__(self):
        if not self.test_id:
            self.test_id = f"ab_test_{int(datetime.now().timestamp())}"
        if self.end_date is None:
            self.end_date = self.start_date + timedelta(days=7)


class TemplateVersionManager:
    """模板版本管理器"""
    
    def __init__(self, storage_path: str = "backend/config/template_versions.json"):
        self.storage_path = storage_path
        self.versions: Dict[str, List[PromptTemplateVersion]] = defaultdict(list)
        self.ab_tests: Dict[str, ABTestConfig] = {}
        
        # 加载版本数据
        self._load_versions()
        
        logger.info(f"Template version manager initialized with {len(self.versions)} template families")
    
    def _load_versions(self) -> None:
        """加载版本数据"""
        try:
            if os.path.exists(self.storage_path):
                with open(self.storage_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # 加载模板版本
                for template_name, versions_data in data.get('versions', {}).items():
                    for version_data in versions_data:
                        version = PromptTemplateVersion(
                            version_id=version_data['version_id'],
                            name=version_data['name'],
                            content=version_data['content'],
                            variables=version_data['variables'],
                            version=TemplateVersion(version_data['version']),
                            created_at=datetime.fromisoformat(version_data['created_at']),
                            created_by=version_data['created_by'],
                            description=version_data.get('description', ''),
                            metadata=version_data.get('metadata', {}),
                            parent_version_id=version_data.get('parent_version_id')
                        )
                        
                        # 加载指标
                        if 'metrics' in version_data:
                            metrics_data = version_data['metrics']
                            version.metrics = TemplateMetrics(
                                usage_count=metrics_data.get('usage_count', 0),
                                success_rate=metrics_data.get('success_rate', 0.0),
                                avg_response_time=metrics_data.get('avg_response_time', 0.0),
                                user_satisfaction=metrics_data.get('user_satisfaction', 0.0),
                                error_rate=metrics_data.get('error_rate', 0.0),
                                token_efficiency=metrics_data.get('token_efficiency', 0.0),
                                last_updated=datetime.fromisoformat(metrics_data.get('last_updated', datetime.now().isoformat()))
                            )
                        
                        self.versions[template_name].append(version)
                
                # 加载A/B测试配置
                for test_id, test_data in data.get('ab_tests', {}).items():
                    ab_test = ABTestConfig(
                        test_id=test_data['test_id'],
                        name=test_data['name'],
                        description=test_data['description'],
                        template_a_id=test_data['template_a_id'],
                        template_b_id=test_data['template_b_id'],
                        traffic_split=test_data.get('traffic_split', 0.5),
                        start_date=datetime.fromisoformat(test_data['start_date']),
                        end_date=datetime.fromisoformat(test_data['end_date']) if test_data.get('end_date') else None,
                        status=ABTestStatus(test_data.get('status', 'planning')),
                        min_sample_size=test_data.get('min_sample_size', 100),
                        confidence_level=test_data.get('confidence_level', 0.95),
                        success_metric=test_data.get('success_metric', 'success_rate')
                    )
                    self.ab_tests[test_id] = ab_test
        
        except Exception as e:
            logger.error(f"Error loading template versions: {str(e)}")
    
    def _save_versions(self) -> None:
        """保存版本数据"""
        try:
            data = {
                'versions': {},
                'ab_tests': {}
            }
            
            # 保存模板版本
            for template_name, versions in self.versions.items():
                data['versions'][template_name] = []
                for version in versions:
                    version_data = {
                        'version_id': version.version_id,
                        'name': version.name,
                        'content': version.content,
                        'variables': version.variables,
                        'version': version.version.value,
                        'created_at': version.created_at.isoformat(),
                        'created_by': version.created_by,
                        'description': version.description,
                        'metadata': version.metadata,
                        'parent_version_id': version.parent_version_id,
                        'metrics': {
                            'usage_count': version.metrics.usage_count,
                            'success_rate': version.metrics.success_rate,
                            'avg_response_time': version.metrics.avg_response_time,
                            'user_satisfaction': version.metrics.user_satisfaction,
                            'error_rate': version.metrics.error_rate,
                            'token_efficiency': version.metrics.token_efficiency,
                            'last_updated': version.metrics.last_updated.isoformat()
                        }
                    }
                    data['versions'][template_name].append(version_data)
            
            # 保存A/B测试配置
            for test_id, ab_test in self.ab_tests.items():
                data['ab_tests'][test_id] = {
                    'test_id': ab_test.test_id,
                    'name': ab_test.name,
                    'description': ab_test.description,
                    'template_a_id': ab_test.template_a_id,
                    'template_b_id': ab_test.template_b_id,
                    'traffic_split': ab_test.traffic_split,
                    'start_date': ab_test.start_date.isoformat(),
                    'end_date': ab_test.end_date.isoformat() if ab_test.end_date else None,
                    'status': ab_test.status.value,
                    'min_sample_size': ab_test.min_sample_size,
                    'confidence_level': ab_test.confidence_level,
                    'success_metric': ab_test.success_metric
                }
            
            os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        
        except Exception as e:
            logger.error(f"Error saving template versions: {str(e)}")
    
    def create_version(self, name: str, content: str, variables: List[str],
                      created_by: str, description: str = "",
                      parent_version_id: Optional[str] = None,
                      metadata: Optional[Dict[str, Any]] = None) -> PromptTemplateVersion:
        """创建新版本"""
        version = PromptTemplateVersion(
            version_id="",  # 将在__post_init__中生成
            name=name,
            content=content,
            variables=variables,
            version=TemplateVersion.DRAFT,
            created_at=datetime.now(),
            created_by=created_by,
            description=description,
            metadata=metadata or {},
            parent_version_id=parent_version_id
        )
        
        self.versions[name].append(version)
        self._save_versions()
        
        logger.info(f"Created new template version: {version.version_id}")
        return version
    
    def activate_version(self, version_id: str) -> bool:
        """激活版本"""
        for template_name, versions in self.versions.items():
            for version in versions:
                if version.version_id == version_id:
                    # 将其他版本设为非激活状态
                    for v in versions:
                        if v.version == TemplateVersion.ACTIVE:
                            v.version = TemplateVersion.ARCHIVED
                    
                    # 激活当前版本
                    version.version = TemplateVersion.ACTIVE
                    self._save_versions()
                    
                    logger.info(f"Activated template version: {version_id}")
                    return True
        
        logger.warning(f"Template version not found: {version_id}")
        return False
    
    def get_active_version(self, template_name: str) -> Optional[PromptTemplateVersion]:
        """获取激活版本"""
        for version in self.versions.get(template_name, []):
            if version.version == TemplateVersion.ACTIVE:
                return version
        return None
    
    def get_version(self, version_id: str) -> Optional[PromptTemplateVersion]:
        """获取指定版本"""
        for versions in self.versions.values():
            for version in versions:
                if version.version_id == version_id:
                    return version
        return None
    
    def list_versions(self, template_name: str) -> List[PromptTemplateVersion]:
        """列出模板的所有版本"""
        return sorted(
            self.versions.get(template_name, []),
            key=lambda v: v.created_at,
            reverse=True
        )
    
    def update_metrics(self, version_id: str, success: bool, response_time: float,
                      satisfaction: Optional[float] = None,
                      token_count: Optional[int] = None) -> None:
        """更新版本指标"""
        version = self.get_version(version_id)
        if version:
            version.metrics.update_metrics(success, response_time, satisfaction, token_count)
            self._save_versions()
            logger.debug(f"Updated metrics for version: {version_id}")
    
    def create_ab_test(self, name: str, description: str,
                      template_a_id: str, template_b_id: str,
                      traffic_split: float = 0.5,
                      duration_days: int = 7,
                      min_sample_size: int = 100,
                      success_metric: str = "success_rate") -> ABTestConfig:
        """创建A/B测试"""
        ab_test = ABTestConfig(
            test_id="",  # 将在__post_init__中生成
            name=name,
            description=description,
            template_a_id=template_a_id,
            template_b_id=template_b_id,
            traffic_split=traffic_split,
            start_date=datetime.now(),
            end_date=datetime.now() + timedelta(days=duration_days),
            min_sample_size=min_sample_size,
            success_metric=success_metric
        )
        
        self.ab_tests[ab_test.test_id] = ab_test
        self._save_versions()
        
        logger.info(f"Created A/B test: {ab_test.test_id}")
        return ab_test
    
    def start_ab_test(self, test_id: str) -> bool:
        """开始A/B测试"""
        if test_id in self.ab_tests:
            self.ab_tests[test_id].status = ABTestStatus.RUNNING
            self._save_versions()
            logger.info(f"Started A/B test: {test_id}")
            return True
        return False
    
    def stop_ab_test(self, test_id: str) -> bool:
        """停止A/B测试"""
        if test_id in self.ab_tests:
            self.ab_tests[test_id].status = ABTestStatus.COMPLETED
            self._save_versions()
            logger.info(f"Stopped A/B test: {test_id}")
            return True
        return False
    
    def get_ab_test_template(self, template_name: str, user_id: str) -> Optional[PromptTemplateVersion]:
        """根据A/B测试获取模板版本"""
        # 查找正在运行的A/B测试
        for ab_test in self.ab_tests.values():
            if ab_test.status == ABTestStatus.RUNNING:
                template_a = self.get_version(ab_test.template_a_id)
                template_b = self.get_version(ab_test.template_b_id)
                
                if template_a and template_a.name == template_name:
                    # 基于用户ID进行流量分配
                    user_hash = hash(user_id) % 100
                    if user_hash < ab_test.traffic_split * 100:
                        return template_a
                    else:
                        return template_b
        
        # 如果没有A/B测试，返回激活版本
        return self.get_active_version(template_name)
    
    def analyze_ab_test(self, test_id: str) -> Dict[str, Any]:
        """分析A/B测试结果"""
        if test_id not in self.ab_tests:
            return {"error": "A/B test not found"}
        
        ab_test = self.ab_tests[test_id]
        template_a = self.get_version(ab_test.template_a_id)
        template_b = self.get_version(ab_test.template_b_id)
        
        if not template_a or not template_b:
            return {"error": "Template versions not found"}
        
        # 获取指标
        metrics_a = template_a.metrics
        metrics_b = template_b.metrics
        
        # 计算统计显著性（简化版）
        def calculate_significance(metric_a: float, metric_b: float, 
                                 count_a: int, count_b: int) -> Dict[str, Any]:
            if count_a < ab_test.min_sample_size or count_b < ab_test.min_sample_size:
                return {"significant": False, "reason": "Insufficient sample size"}
            
            # 简化的统计检验
            diff = abs(metric_a - metric_b)
            pooled_metric = (metric_a * count_a + metric_b * count_b) / (count_a + count_b)
            
            if pooled_metric == 0:
                return {"significant": False, "reason": "No baseline metric"}
            
            relative_diff = diff / pooled_metric
            
            return {
                "significant": relative_diff > 0.05,  # 5%差异阈值
                "relative_difference": relative_diff,
                "absolute_difference": diff
            }
        
        # 分析主要指标
        primary_metric = ab_test.success_metric
        if primary_metric == "success_rate":
            metric_a_val = metrics_a.success_rate
            metric_b_val = metrics_b.success_rate
        elif primary_metric == "response_time":
            metric_a_val = metrics_a.avg_response_time
            metric_b_val = metrics_b.avg_response_time
        elif primary_metric == "user_satisfaction":
            metric_a_val = metrics_a.user_satisfaction
            metric_b_val = metrics_b.user_satisfaction
        else:
            metric_a_val = metrics_a.success_rate
            metric_b_val = metrics_b.success_rate
        
        significance = calculate_significance(
            metric_a_val, metric_b_val,
            metrics_a.usage_count, metrics_b.usage_count
        )
        
        # 确定获胜者
        if primary_metric == "response_time":
            winner = "A" if metric_a_val < metric_b_val else "B"  # 响应时间越低越好
        else:
            winner = "A" if metric_a_val > metric_b_val else "B"  # 其他指标越高越好
        
        return {
            "test_id": test_id,
            "test_name": ab_test.name,
            "status": ab_test.status.value,
            "primary_metric": primary_metric,
            "template_a": {
                "version_id": template_a.version_id,
                "usage_count": metrics_a.usage_count,
                "success_rate": metrics_a.success_rate,
                "avg_response_time": metrics_a.avg_response_time,
                "user_satisfaction": metrics_a.user_satisfaction,
                "primary_metric_value": metric_a_val
            },
            "template_b": {
                "version_id": template_b.version_id,
                "usage_count": metrics_b.usage_count,
                "success_rate": metrics_b.success_rate,
                "avg_response_time": metrics_b.avg_response_time,
                "user_satisfaction": metrics_b.user_satisfaction,
                "primary_metric_value": metric_b_val
            },
            "statistical_significance": significance,
            "winner": winner if significance["significant"] else "No clear winner",
            "recommendation": self._generate_recommendation(ab_test, template_a, template_b, significance, winner)
        }
    
    def _generate_recommendation(self, ab_test: ABTestConfig, 
                               template_a: PromptTemplateVersion,
                               template_b: PromptTemplateVersion,
                               significance: Dict[str, Any],
                               winner: str) -> str:
        """生成A/B测试建议"""
        if not significance["significant"]:
            if template_a.metrics.usage_count < ab_test.min_sample_size:
                return f"继续测试，需要更多样本（当前: {template_a.metrics.usage_count + template_b.metrics.usage_count}, 最少需要: {ab_test.min_sample_size * 2}）"
            else:
                return "两个版本性能相近，可以选择任一版本或继续优化"
        
        winner_template = template_a if winner == "A" else template_b
        improvement = significance.get("relative_difference", 0) * 100
        
        return f"建议采用版本 {winner} ({winner_template.version_id})，性能提升约 {improvement:.1f}%"


class EnhancedPromptManager:
    """增强版Prompt管理器"""
    
    def __init__(self, config_path: Optional[str] = None):
        # 初始化基础组件
        from .prompt_manager import PromptManager, PromptRenderer
        
        self.base_manager = PromptManager(config_path)
        self.renderer = PromptRenderer()
        self.version_manager = TemplateVersionManager()
        
        logger.info("Enhanced prompt manager initialized")
    
    def render_prompt_with_ab_test(self, prompt_type: str, variables: Dict[str, Any],
                                  user_id: str = "default") -> Tuple[str, str]:
        """使用A/B测试渲染Prompt"""
        # 获取A/B测试版本
        template_version = self.version_manager.get_ab_test_template(prompt_type, user_id)
        
        if template_version:
            # 使用版本化模板
            rendered = self.renderer.render_template_version(template_version, variables)
            return rendered, template_version.version_id
        else:
            # 回退到基础管理器
            from .prompt_manager import PromptType
            try:
                prompt_enum = PromptType(prompt_type)
                rendered = self.base_manager.render_prompt(prompt_enum, variables)
                return rendered, "base_template"
            except ValueError:
                raise ValueError(f"Unknown prompt type: {prompt_type}")
    
    def record_usage(self, version_id: str, success: bool, response_time: float,
                    satisfaction: Optional[float] = None,
                    token_count: Optional[int] = None) -> None:
        """记录使用情况"""
        self.version_manager.update_metrics(
            version_id, success, response_time, satisfaction, token_count
        )
    
    def get_template_performance(self, template_name: str) -> Dict[str, Any]:
        """获取模板性能报告"""
        versions = self.version_manager.list_versions(template_name)
        
        if not versions:
            return {"error": "No versions found"}
        
        active_version = self.version_manager.get_active_version(template_name)
        
        performance_data = {
            "template_name": template_name,
            "active_version": active_version.version_id if active_version else None,
            "total_versions": len(versions),
            "versions": []
        }
        
        for version in versions:
            version_data = {
                "version_id": version.version_id,
                "version_status": version.version.value,
                "created_at": version.created_at.isoformat(),
                "created_by": version.created_by,
                "description": version.description,
                "metrics": {
                    "usage_count": version.metrics.usage_count,
                    "success_rate": version.metrics.success_rate,
                    "avg_response_time": version.metrics.avg_response_time,
                    "user_satisfaction": version.metrics.user_satisfaction,
                    "error_rate": version.metrics.error_rate,
                    "token_efficiency": version.metrics.token_efficiency,
                    "last_updated": version.metrics.last_updated.isoformat()
                }
            }
            performance_data["versions"].append(version_data)
        
        return performance_data


# 扩展PromptRenderer以支持版本化模板
class PromptRenderer:
    """增强版Prompt渲染器"""
    
    def __init__(self):
        self.variable_pattern = re.compile(r'\{\{(\w+)\}\}')
    
    def render_template_version(self, template_version: PromptTemplateVersion, 
                               variables: Dict[str, Any]) -> str:
        """渲染版本化模板"""
        # 验证变量完整性
        missing_vars = []
        for var in template_version.variables:
            if var not in variables:
                missing_vars.append(var)
        
        if missing_vars:
            raise ValueError(f"Missing required variables: {missing_vars}")
        
        # 渲染模板
        rendered = template_version.content
        
        # 替换变量
        for var_name, var_value in variables.items():
            placeholder = f"{{{{{var_name}}}}}"
            
            # 处理不同类型的变量值
            if isinstance(var_value, (list, dict)):
                var_str = self._format_complex_variable(var_value)
            else:
                var_str = str(var_value)
            
            rendered = rendered.replace(placeholder, var_str)
        
        # 检查是否还有未替换的变量
        remaining_vars = self.variable_pattern.findall(rendered)
        if remaining_vars:
            logger.warning(f"Unresolved variables in template {template_version.version_id}: {remaining_vars}")
        
        return rendered
    
    def _format_complex_variable(self, value: Union[List, Dict]) -> str:
        """格式化复杂变量（列表、字典）"""
        if isinstance(value, list):
            if not value:
                return "无"
            
            # 如果是字符串列表，直接连接
            if all(isinstance(item, str) for item in value):
                return "\n".join(f"- {item}" for item in value)
            
            # 如果是字典列表，格式化每个字典
            if all(isinstance(item, dict) for item in value):
                formatted_items = []
                for item in value:
                    formatted_items.append(self._format_dict(item))
                return "\n".join(formatted_items)
        
        elif isinstance(value, dict):
            return self._format_dict(value)
        
        return str(value)
    
    def _format_dict(self, d: Dict[str, Any], indent: int = 0) -> str:
        """格式化字典"""
        lines = []
        prefix = "  " * indent
        
        for key, value in d.items():
            if isinstance(value, dict):
                lines.append(f"{prefix}{key}:")
                lines.append(self._format_dict(value, indent + 1))
            elif isinstance(value, list):
                lines.append(f"{prefix}{key}:")
                for item in value:
                    if isinstance(item, dict):
                        lines.append(self._format_dict(item, indent + 1))
                    else:
                        lines.append(f"{prefix}  - {item}")
            else:
                lines.append(f"{prefix}{key}: {value}")
        
        return "\n".join(lines)


# 全局实例
enhanced_prompt_manager = EnhancedPromptManager()

# 导出主要类和函数
__all__ = [
    "EnhancedPromptManager",
    "TemplateVersionManager",
    "PromptTemplateVersion",
    "ABTestConfig",
    "TemplateMetrics",
    "TemplateVersion",
    "ABTestStatus",
    "enhanced_prompt_manager"
]