# -*- coding: utf-8 -*-
"""
Prompt模板管理和渲染引擎
实现模块化Prompt模板系统和动态变量替换
"""

import os
import yaml
import json
import re
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from src.utils import logger


class PromptType(Enum):
    """Prompt类型枚举"""
    INTENT_RECOGNITION = "intent_recognition"
    TABLE_SELECTION = "table_selection"
    INTENT_CLARIFICATION = "intent_clarification"
    THINKING = "thinking"
    SQL_GENERATION = "sql_generation"
    SQL_PEER_REVIEW = "sql_peer_review"
    DATA_ANALYSIS = "data_analysis"
    RESULT_DESCRIPTION = "result_description"
    CHART_RECOMMENDATION = "chart_recommendation"
    ERROR_RECOVERY = "error_recovery"


@dataclass
class PromptTemplate:
    """Prompt模板数据结构"""
    name: str
    type: PromptType
    version: str
    description: str
    content: str
    variables: List[str]
    metadata: Optional[Dict[str, Any]] = None
    
    def validate_variables(self, provided_vars: Dict[str, Any]) -> List[str]:
        """验证提供的变量是否完整"""
        missing_vars = []
        for var in self.variables:
            if var not in provided_vars:
                missing_vars.append(var)
        return missing_vars


class PromptRenderer:
    """Prompt渲染引擎"""
    
    def __init__(self):
        self.variable_pattern = re.compile(r'\{\{(\w+)\}\}')
        
    def render(self, template: PromptTemplate, variables: Dict[str, Any]) -> str:
        """渲染Prompt模板"""
        
        # 验证变量完整性
        missing_vars = template.validate_variables(variables)
        if missing_vars:
            raise ValueError(f"Missing required variables: {missing_vars}")
        
        # 渲染模板
        rendered = template.content
        
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
            logger.warning(f"Unresolved variables in template {template.name}: {remaining_vars}")
        
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


class PromptManager:
    """Prompt模板管理器"""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or self._get_default_config_path()
        self.templates: Dict[PromptType, PromptTemplate] = {}
        self.renderer = PromptRenderer()
        
        # 加载模板配置
        self._load_templates()
        
        logger.info(f"Prompt manager initialized with {len(self.templates)} templates")
    
    def _get_default_config_path(self) -> str:
        """获取默认配置文件路径"""
        # 查找配置文件
        possible_paths = [
            "backend/config/prompts.yml",
            "config/prompts.yml",
            "prompts.yml"
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                return path
        
        # 如果没有找到配置文件，创建默认配置
        default_path = "backend/config/prompts.yml"
        self._create_default_config(default_path)
        return default_path
    
    def _create_default_config(self, config_path: str) -> None:
        """创建默认配置文件"""
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        
        default_config = self._get_default_templates()
        
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(default_config, f, default_flow_style=False, allow_unicode=True)
        
        logger.info(f"Created default prompt config at {config_path}")
    
    def _load_templates(self) -> None:
        """加载Prompt模板"""
        try:
            if not os.path.exists(self.config_path):
                logger.warning(f"Prompt config file not found: {self.config_path}")
                return
            
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            for template_key, template_data in config.items():
                try:
                    prompt_type = PromptType(template_key)
                    
                    template = PromptTemplate(
                        name=template_data.get('name', template_key),
                        type=prompt_type,
                        version=template_data.get('version', '1.0'),
                        description=template_data.get('description', ''),
                        content=template_data.get('content', ''),
                        variables=template_data.get('variables', []),
                        metadata=template_data.get('metadata', {})
                    )
                    
                    self.templates[prompt_type] = template
                    
                except ValueError as e:
                    logger.warning(f"Unknown prompt type: {template_key}, skipping")
                except Exception as e:
                    logger.error(f"Error loading template {template_key}: {str(e)}")
        
        except Exception as e:
            logger.error(f"Error loading prompt config: {str(e)}")
    
    def get_template(self, prompt_type: PromptType) -> Optional[PromptTemplate]:
        """获取指定类型的模板"""
        return self.templates.get(prompt_type)
    
    def render_prompt(self, prompt_type: PromptType, variables: Dict[str, Any]) -> str:
        """渲染指定类型的Prompt"""
        template = self.get_template(prompt_type)
        if not template:
            raise ValueError(f"Template not found for type: {prompt_type.value}")
        
        return self.renderer.render(template, variables)
    
    def list_templates(self) -> List[Dict[str, Any]]:
        """列出所有模板信息"""
        return [
            {
                'type': template.type.value,
                'name': template.name,
                'version': template.version,
                'description': template.description,
                'variables': template.variables
            }
            for template in self.templates.values()
        ]
    
    def reload_templates(self) -> None:
        """重新加载模板"""
        self.templates.clear()
        self._load_templates()
        logger.info("Prompt templates reloaded")
    
    def _get_default_templates(self) -> Dict[str, Any]:
        """获取默认模板配置"""
        return {
            "intent_recognition": {
                "name": "意图识别",
                "version": "1.0",
                "description": "识别用户问题的意图类型",
                "variables": ["user_question"],
                "content": """请分析用户的问题，判断用户的意图类型：

用户问题：{{user_question}}

请从以下两种意图中选择一种：
1. 智能问数：用户想要查询具体的数据，获取数值、统计结果等
2. 生成报告：用户想要生成综合性的分析报告或总结

请以JSON格式返回结果：
{
  "intent": "query" | "report",
  "confidence": 0.0-1.0,
  "reasoning": "判断理由"
}"""
            },
            
            "table_selection": {
                "name": "智能选表",
                "version": "1.0",
                "description": "根据用户问题选择相关数据表",
                "variables": ["user_question", "intent_type", "semantic_context"],
                "content": """基于用户问题和可用的数据资源，请选择最相关的数据表：

用户问题：{{user_question}}
意图类型：{{intent_type}}

语义增强上下文：
{{semantic_context}}

请分析用户问题中的关键词，结合表结构、字段含义和业务知识，选择最相关的表。

请以JSON格式返回结果：
{
  "selectedTables": [
    {
      "tableId": "表ID",
      "tableName": "表名",
      "relevanceScore": 0.0-1.0,
      "reasoning": "选择理由",
      "relevantFields": ["相关字段列表"]
    }
  ],
  "overallReasoning": "整体选择逻辑"
}"""
            },
            
            "intent_clarification": {
                "name": "意图澄清",
                "version": "1.0",
                "description": "生成意图澄清问题",
                "variables": ["user_question", "selected_tables"],
                "content": """基于用户问题和选择的数据表，生成意图澄清问题：

用户原始问题：{{user_question}}

选择的数据表：
{{selected_tables}}

请分析可能的歧义点和需要确认的细节，生成澄清问题。

请以JSON格式返回：
{
  "clarificationNeeded": true/false,
  "questions": [
    {
      "question": "澄清问题",
      "options": ["选项1", "选项2", "选项3"],
      "type": "single_choice" | "multiple_choice" | "text_input"
    }
  ],
  "summary": "理解总结：我理解您想要..."
}"""
            },
            
            "sql_generation": {
                "name": "SQL生成",
                "version": "1.0",
                "description": "根据澄清后的需求生成SQL查询",
                "variables": ["original_question", "clarified_requirement", "semantic_context", "db_type"],
                "content": """请根据用户需求生成SQL查询语句：

用户原始问题：{{original_question}}
澄清后的需求：{{clarified_requirement}}

语义增强上下文：
{{semantic_context}}

数据库类型：{{db_type}}

请生成标准的SQL查询语句，要求：
1. 语法正确，符合{{db_type}}数据库规范
2. 字段名和表名准确
3. 查询逻辑符合用户需求
4. 包含必要的WHERE条件和GROUP BY子句
5. 结果集大小合理（建议添加LIMIT）

请以JSON格式返回：
{
  "sql": "生成的SQL语句",
  "explanation": "SQL逻辑说明",
  "estimatedRows": "预估结果行数",
  "executionPlan": "执行计划说明"
}"""
            },
            
            "data_analysis": {
                "name": "数据分析",
                "version": "1.0",
                "description": "分析查询结果数据",
                "variables": ["user_question", "query_result", "previous_data"],
                "content": """请分析查询结果数据，回答用户问题：

用户问题：{{user_question}}

当前查询结果：
{{query_result}}

历史数据（用于对比）：
{{previous_data}}

请基于数据进行分析，提供以下内容：
1. 数据摘要和关键指标
2. 趋势分析和变化情况
3. 异常数据和洞察发现
4. 业务建议和后续行动

请以自然语言回答，重点突出数据洞察。"""
            },
            
            "chart_recommendation": {
                "name": "图表推荐",
                "version": "1.1",
                "description": "推荐合适的图表类型",
                "variables": ["user_question", "query_result", "data_characteristics"],
                "content": """基于查询结果和数据特征，推荐最合适的图表类型：

用户问题：{{user_question}}

查询结果：
{{query_result}}

数据特征：
{{data_characteristics}}

请分析数据类型、维度数量、数据分布等特征，推荐最佳图表类型。

⚠️ 重要：当查询结果包含多列数值（如 CASE WHEN 对比查询产生的 sf_2025、sf_2026 等多列），
series 必须是包含多个系列的数组，每列数值对应一个系列。

请以JSON格式返回：
{
  "recommendedChart": "bar" | "line" | "pie" | "scatter" | "heatmap" | "radar",
  "confidence": 0.0-1.0,
  "reasoning": "推荐理由",
  "alternatives": ["备选图表类型"],
  "chartConfig": {
    "title": "图表标题",
    "xAxis": "X轴字段",
    "yAxis": "Y轴字段",
    "series": [
      {"name": "系列名称1", "type": "bar", "data": [{"name": "分类1", "value": 100}]},
      {"name": "系列名称2", "type": "bar", "data": [{"name": "分类1", "value": 200}]}
    ]
  }
}

注意：series 必须是数组格式，即使只有一个系列也要用数组包裹。"""
            },
            
            "error_recovery": {
                "name": "错误恢复",
                "version": "1.0",
                "description": "SQL错误分析和恢复",
                "variables": ["original_sql", "error_message", "semantic_context"],
                "content": """分析SQL执行错误并生成修复后的SQL：

原始SQL：
{{original_sql}}

错误信息：
{{error_message}}

语义上下文：
{{semantic_context}}

请分析错误原因并生成修复后的SQL语句。

请以JSON格式返回：
{
  "errorType": "syntax_error" | "field_not_found" | "table_not_found" | "type_mismatch" | "permission_denied",
  "errorAnalysis": "错误分析",
  "fixedSQL": "修复后的SQL语句",
  "changes": ["修改说明列表"],
  "confidence": 0.0-1.0
}"""
            }
        }


class FewShotManager:
    """Few-Shot样本管理器"""
    
    def __init__(self, samples_path: Optional[str] = None):
        self.samples_path = samples_path or "backend/config/few_shot_samples.json"
        self.samples: Dict[PromptType, List[Dict[str, Any]]] = {}
        
        # 加载样本
        self._load_samples()
        
        logger.info(f"Few-shot manager initialized with samples for {len(self.samples)} prompt types")
    
    def _load_samples(self) -> None:
        """加载Few-Shot样本"""
        try:
            if os.path.exists(self.samples_path):
                with open(self.samples_path, 'r', encoding='utf-8') as f:
                    samples_data = json.load(f)
                
                for prompt_type_str, samples_list in samples_data.items():
                    try:
                        prompt_type = PromptType(prompt_type_str)
                        self.samples[prompt_type] = samples_list
                    except ValueError:
                        logger.warning(f"Unknown prompt type in samples: {prompt_type_str}")
            else:
                # 创建默认样本文件
                self._create_default_samples()
        
        except Exception as e:
            logger.error(f"Error loading few-shot samples: {str(e)}")
    
    def _create_default_samples(self) -> None:
        """创建默认样本文件"""
        default_samples = {
            "sql_generation": [
                {
                    "input": "查询所有用户的姓名和邮箱",
                    "output": "SELECT name, email FROM users;",
                    "score": 1.0
                },
                {
                    "input": "统计每个部门的员工数量",
                    "output": "SELECT department, COUNT(*) as employee_count FROM employees GROUP BY department;",
                    "score": 1.0
                }
            ],
            "intent_recognition": [
                {
                    "input": "显示销售额最高的产品",
                    "output": '{"intent": "query", "confidence": 0.9, "reasoning": "用户想要查询具体的销售数据"}',
                    "score": 1.0
                }
            ]
        }
        
        os.makedirs(os.path.dirname(self.samples_path), exist_ok=True)
        with open(self.samples_path, 'w', encoding='utf-8') as f:
            json.dump(default_samples, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Created default few-shot samples at {self.samples_path}")
    
    def get_samples(self, prompt_type: PromptType, max_samples: int = 3) -> List[Dict[str, Any]]:
        """获取指定类型的样本"""
        samples = self.samples.get(prompt_type, [])
        
        # 按评分排序，返回最佳样本
        sorted_samples = sorted(samples, key=lambda x: x.get('score', 0), reverse=True)
        return sorted_samples[:max_samples]
    
    def add_sample(self, prompt_type: PromptType, input_text: str, output_text: str, score: float = 1.0) -> None:
        """添加新样本"""
        if prompt_type not in self.samples:
            self.samples[prompt_type] = []
        
        sample = {
            "input": input_text,
            "output": output_text,
            "score": score,
            "created_at": str(datetime.now())
        }
        
        self.samples[prompt_type].append(sample)
        
        # 保存到文件
        self._save_samples()
        
        logger.info(f"Added new sample for {prompt_type.value}")
    
    def _save_samples(self) -> None:
        """保存样本到文件"""
        try:
            samples_data = {
                prompt_type.value: samples 
                for prompt_type, samples in self.samples.items()
            }
            
            with open(self.samples_path, 'w', encoding='utf-8') as f:
                json.dump(samples_data, f, ensure_ascii=False, indent=2)
        
        except Exception as e:
            logger.error(f"Error saving few-shot samples: {str(e)}")


# 全局实例
prompt_manager = PromptManager()
few_shot_manager = FewShotManager()


# 导出主要类和函数
__all__ = [
    "PromptManager",
    "FewShotManager", 
    "PromptType",
    "PromptTemplate",
    "PromptRenderer",
    "prompt_manager",
    "few_shot_manager"
]