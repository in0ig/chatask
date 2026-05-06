"""
SQL生成服务

任务 5.4.1 的核心实现
基于云端Qwen模型实现SQL生成，注入完整的五模块语义上下文
"""

import logging
import time
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum
from datetime import datetime

from src.services.ai_model_service import AIModelService, ModelType
from src.services.semantic_context_aggregator import SemanticContextAggregator
from src.services.prompt_template_manager import enhanced_prompt_manager
from src.services.sql_security_validator import SQLSecurityValidator

logger = logging.getLogger(__name__)


class SQLDialect(Enum):
    """SQL方言类型"""
    MYSQL = "mysql"
    SQLSERVER = "sqlserver"
    POSTGRESQL = "postgresql"


@dataclass
class SQLGenerationRequest:
    """SQL生成请求"""
    user_question: str
    table_ids: Optional[List[str]] = None
    data_source_id: Optional[str] = None
    sql_dialect: SQLDialect = SQLDialect.MYSQL
    include_explanation: bool = True
    max_rows: Optional[int] = 1000


@dataclass
class SQLGenerationResult:
    """SQL生成结果"""
    sql: str
    explanation: str
    estimated_rows: int
    execution_plan: str
    confidence: float
    generation_time: float
    semantic_context_used: Dict[str, Any]
    validation_result: Optional[Dict[str, Any]] = None


class SQLGeneratorService:
    """SQL生成服务"""
    
    def __init__(self):
        """初始化SQL生成服务"""
        # 创建默认配置用于测试
        default_config = {
            'qwen_cloud': {
                'api_key': 'test_key',
                'base_url': 'https://dashscope.aliyuncs.com/api/v1',
                'model_name': 'qwen-turbo',
                'max_tokens': 2000,
                'temperature': 0.1
            }
        }
        
        try:
            self.ai_service = AIModelService(default_config)
        except Exception as e:
            logger.warning(f"AI服务初始化失败，将在运行时处理: {str(e)}")
            self.ai_service = None
            
        self.semantic_aggregator = SemanticContextAggregator()
        self.sql_validator = SQLSecurityValidator(strict_mode=False)  # 开发模式：跳过表存在性检查
        
        # 统计信息
        self.generation_stats = {
            "total_generations": 0,
            "successful_generations": 0,
            "failed_generations": 0,
            "average_generation_time": 0.0,
            "average_confidence": 0.0,
            "syntax_correctness_rate": 0.0,
            "semantic_accuracy_rate": 0.0
        }
    
    async def generate_sql(
        self,
        request: SQLGenerationRequest
    ) -> SQLGenerationResult:
        """
        生成SQL查询
        
        Args:
            request: SQL生成请求
            
        Returns:
            SQLGenerationResult: SQL生成结果
        """
        start_time = time.time()
        
        try:
            logger.info(f"开始SQL生成，用户问题: {request.user_question[:100]}...")
            
            # 1. 获取完整的五模块语义上下文
            semantic_context = await self._get_semantic_context(request)
            
            # 2. 构建SQL生成Prompt
            prompt = await self._build_sql_generation_prompt(request, semantic_context)
            
            # 3. 调用Qwen模型生成SQL
            sql_response = await self._generate_sql_with_qwen(prompt, request)
            
            # 4. 提取和验证SQL
            sql = self._extract_sql_from_response(sql_response)
            validation_result = await self._validate_sql(sql, request)
            
            # 5. 解析生成结果
            result = self._parse_generation_result(
                sql, sql_response, semantic_context, validation_result, start_time
            )
            
            # 6. 更新统计信息
            self._update_generation_stats(result, True)
            
            logger.info(f"SQL生成完成，耗时: {result.generation_time:.2f}s")
            return result
            
        except Exception as e:
            logger.error(f"SQL生成失败: {str(e)}", exc_info=True)
            self._update_generation_stats(None, False)
            
            # 返回错误结果
            return SQLGenerationResult(
                sql="",
                explanation=f"SQL生成失败: {str(e)}",
                estimated_rows=0,
                execution_plan="",
                confidence=0.0,
                generation_time=time.time() - start_time,
                semantic_context_used={},
                validation_result={"is_valid": False, "error": str(e)}
            )
    
    async def _get_semantic_context(
        self,
        request: SQLGenerationRequest
    ) -> Dict[str, Any]:
        """获取完整的五模块语义上下文"""
        try:
            # 使用语义上下文聚合器获取完整上下文
            aggregation_result = await self.semantic_aggregator.aggregate_semantic_context(
                user_question=request.user_question,
                table_ids=request.table_ids,
                include_global=True
            )
            
            return {
                "enhanced_context": aggregation_result.enhanced_context,
                "modules_used": aggregation_result.modules_used,
                "total_tokens_used": aggregation_result.total_tokens_used,
                "relevance_scores": aggregation_result.relevance_scores
            }
            
        except Exception as e:
            logger.error(f"获取语义上下文失败: {str(e)}")
            return {
                "enhanced_context": f"用户问题: {request.user_question}",
                "modules_used": [],
                "total_tokens_used": 0,
                "relevance_scores": {}
            }
    
    async def _build_sql_generation_prompt(
        self,
        request: SQLGenerationRequest,
        semantic_context: Dict[str, Any]
    ) -> str:
        """构建SQL生成Prompt"""
        try:
            # 使用Prompt模板管理器
            prompt_variables = {
                "user_question": request.user_question,
                "semantic_context": semantic_context["enhanced_context"],
                "sql_dialect": request.sql_dialect.value,
                "max_rows": request.max_rows or 1000,
                "include_explanation": request.include_explanation
            }
            
            # 尝试使用模板管理器
            try:
                prompt = enhanced_prompt_manager.getPrompt("sql_generation", prompt_variables)
            except Exception:
                # 降级到基础Prompt
                prompt = self._build_basic_sql_prompt(request, semantic_context)
            
            return prompt
            
        except Exception as e:
            logger.error(f"构建SQL生成Prompt失败: {str(e)}")
            return self._build_basic_sql_prompt(request, semantic_context)
    
    def _build_basic_sql_prompt(
        self,
        request: SQLGenerationRequest,
        semantic_context: Dict[str, Any]
    ) -> str:
        """构建基础SQL生成Prompt"""
        dialect_syntax = self._get_dialect_syntax(request.sql_dialect)
        
        prompt = f"""
你是一个专业的SQL查询生成专家。请根据用户问题和提供的语义上下文生成准确的SQL查询。

用户问题：{request.user_question}

语义上下文：
{semantic_context["enhanced_context"]}

数据库类型：{request.sql_dialect.value}
SQL语法要求：
{dialect_syntax}

请生成符合以下要求的SQL查询：
1. 语法正确，符合{request.sql_dialect.value}数据库规范
2. 字段名和表名准确，避免字段幻觉
3. 查询逻辑符合用户需求
4. 包含必要的WHERE条件和GROUP BY子句
5. 结果集大小合理（建议添加LIMIT {request.max_rows}）
6. 使用正确的SQL方言语法

请以JSON格式返回结果：
{{
    "sql": "生成的SQL语句",
    "explanation": "SQL逻辑说明",
    "estimated_rows": "预估结果行数",
    "execution_plan": "执行计划说明",
    "confidence": 0.95
}}
"""
        return prompt
    
    def _get_dialect_syntax(self, dialect: SQLDialect) -> str:
        """获取SQL方言语法说明"""
        syntax_map = {
            SQLDialect.MYSQL: """
- 使用 LIMIT n 限制结果数量
- 使用反引号 ` 包裹标识符
- 支持 DATE_FORMAT() 函数
- 字符串连接使用 CONCAT()
""",
            SQLDialect.SQLSERVER: """
- 使用 TOP n 限制结果数量
- 使用方括号 [] 包裹标识符
- 支持 FORMAT() 函数
- 字符串连接使用 + 运算符
""",
            SQLDialect.POSTGRESQL: """
- 使用 LIMIT n 限制结果数量
- 使用双引号 " 包裹标识符
- 支持 TO_CHAR() 函数
- 字符串连接使用 || 运算符
"""
        }
        return syntax_map.get(dialect, syntax_map[SQLDialect.MYSQL])
    
    async def _generate_sql_with_qwen(
        self,
        prompt: str,
        request: SQLGenerationRequest
    ) -> str:
        """使用Qwen模型生成SQL"""
        try:
            if self.ai_service is None:
                raise Exception("AI服务未初始化")
            
            # 调用Qwen模型
            response = await self.ai_service.generate_sql(
                prompt=prompt,
                temperature=0.1,  # 使用较低温度确保结果稳定
                max_tokens=2000
            )
            
            return response.content
            
        except Exception as e:
            logger.error(f"Qwen模型调用失败: {str(e)}")
            raise Exception(f"SQL生成失败: {str(e)}")
    
    def _extract_sql_from_response(self, response: str) -> str:
        """从模型响应中提取SQL"""
        import re
        import json
        
        try:
            # 尝试解析JSON响应
            response_data = json.loads(response)
            if "sql" in response_data:
                return response_data["sql"].strip()
        except json.JSONDecodeError:
            pass
        
        # 尝试从Markdown代码块中提取
        patterns = [
            r'```sql\s*(.*?)\s*```',  # SQL代码块
            r'```\s*(SELECT.*?)\s*```',  # 通用代码块中的SELECT
            r'(SELECT\s+.*?(?:;|$))',  # 直接的SELECT语句
        ]
        
        for pattern in patterns:
            match = re.search(pattern, response, re.DOTALL | re.IGNORECASE)
            if match:
                sql = match.group(1).strip()
                # 清理SQL
                sql = re.sub(r'\s+', ' ', sql)
                if not sql.endswith(';'):
                    sql += ';'
                return sql
        
        raise Exception("无法从模型响应中提取有效的SQL语句")
    
    async def _validate_sql(
        self,
        sql: str,
        request: SQLGenerationRequest
    ) -> Dict[str, Any]:
        """验证SQL语法和安全性"""
        try:
            # 使用SQL安全验证器
            validation_result = self.sql_validator.validate_sql(sql)
            
            return {
                "is_valid": validation_result.is_valid,
                "security_level": validation_result.security_level.value,
                "violations": [
                    {
                        "level": v.level.value,
                        "type": v.type,
                        "message": v.message
                    }
                    for v in validation_result.violations
                ],
                "complexity": {
                    "score": validation_result.complexity.complexity_score,
                    "estimated_cost": validation_result.complexity.estimated_cost
                }
            }
            
        except Exception as e:
            logger.error(f"SQL验证失败: {str(e)}")
            return {
                "is_valid": False,
                "error": str(e)
            }
    
    def _parse_generation_result(
        self,
        sql: str,
        response: str,
        semantic_context: Dict[str, Any],
        validation_result: Dict[str, Any],
        start_time: float
    ) -> SQLGenerationResult:
        """解析生成结果"""
        import json
        
        # 尝试从响应中提取额外信息
        explanation = ""
        estimated_rows = 0
        execution_plan = ""
        confidence = 0.8
        
        try:
            response_data = json.loads(response)
            explanation = response_data.get("explanation", "")
            estimated_rows = int(response_data.get("estimated_rows", 0))
            execution_plan = response_data.get("execution_plan", "")
            confidence = float(response_data.get("confidence", 0.8))
        except (json.JSONDecodeError, ValueError):
            explanation = "SQL查询已生成"
            estimated_rows = 100
            execution_plan = "标准查询执行计划"
        
        generation_time = time.time() - start_time
        
        return SQLGenerationResult(
            sql=sql,
            explanation=explanation,
            estimated_rows=estimated_rows,
            execution_plan=execution_plan,
            confidence=confidence,
            generation_time=generation_time,
            semantic_context_used=semantic_context,
            validation_result=validation_result
        )
    
    def _update_generation_stats(
        self,
        result: Optional[SQLGenerationResult],
        success: bool
    ):
        """更新生成统计信息"""
        self.generation_stats["total_generations"] += 1
        
        if success and result:
            self.generation_stats["successful_generations"] += 1
            
            # 更新平均生成时间
            total_time = (
                self.generation_stats["average_generation_time"] * 
                (self.generation_stats["successful_generations"] - 1) + 
                result.generation_time
            )
            self.generation_stats["average_generation_time"] = (
                total_time / self.generation_stats["successful_generations"]
            )
            
            # 更新平均置信度
            total_confidence = (
                self.generation_stats["average_confidence"] * 
                (self.generation_stats["successful_generations"] - 1) + 
                result.confidence
            )
            self.generation_stats["average_confidence"] = (
                total_confidence / self.generation_stats["successful_generations"]
            )
            
            # 更新语法正确率
            if result.validation_result and result.validation_result.get("is_valid"):
                correct_count = int(
                    self.generation_stats["syntax_correctness_rate"] * 
                    (self.generation_stats["successful_generations"] - 1)
                ) + 1
                self.generation_stats["syntax_correctness_rate"] = (
                    correct_count / self.generation_stats["successful_generations"]
                )
        else:
            self.generation_stats["failed_generations"] += 1
    
    def get_generation_statistics(self) -> Dict[str, Any]:
        """获取生成统计信息"""
        return {
            "total_generations": self.generation_stats["total_generations"],
            "successful_generations": self.generation_stats["successful_generations"],
            "failed_generations": self.generation_stats["failed_generations"],
            "success_rate": (
                self.generation_stats["successful_generations"] / 
                max(self.generation_stats["total_generations"], 1)
            ),
            "average_generation_time": self.generation_stats["average_generation_time"],
            "average_confidence": self.generation_stats["average_confidence"],
            "syntax_correctness_rate": self.generation_stats["syntax_correctness_rate"],
            "semantic_accuracy_rate": self.generation_stats["semantic_accuracy_rate"]
        }
