import json
from typing import Dict, Any, Optional
import logging
from src.qwen_integration import QwenIntegration
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SQLGeneratorQwen:
    def __init__(self):
        """
        使用 Qwen 大模型直接生成 SQL 查询
        
        本实现作为 SQLGenerator 的备选方案，提供更灵活的自然语言到 SQL 转换能力
        """
        # 从环境变量读取配置
        self.model_type = os.getenv('MODEL_TYPE', 'local').lower()
        self.api_key = os.getenv('QWEN_API_KEY', '')
        self.model_name = os.getenv('QWEN_MODEL_NAME', 'qwen-agent')
        
        # 验证配置
        if self.model_type not in ['local', 'cloud']:
            logger.warning(f"Invalid MODEL_TYPE '{self.model_type}', defaulting to 'local'")
            self.model_type = 'local'
        
        if self.model_type == 'cloud' and not self.api_key:
            logger.error("QWEN_API_KEY is required when MODEL_TYPE is 'cloud', switching to local mode")
            self.model_type = 'local'  # 降级到本地模式而不是抛出异常
            self.api_key = ''
        
        # 初始化Qwen集成
        self.qwen = QwenIntegration()
        
        # 缓存机制，避免重复查询
        self.cache = {}
        
        logger.info(f"SQLGeneratorQwen initialized with model_type='{self.model_type}', model_name='{self.model_name}'")
        
    def generate_sql(self, text: str, table_name: str = "sales_data") -> str:
        """
        使用 Qwen 大模型直接生成 SQL 查询
        
        Args:
            text: 自然语言查询
            table_name: 数据表名
            
        Returns:
            生成的SQL查询语句
        """
        # 缓存键
        cache_key = f"{text}|{table_name}"
        
        # 检查缓存
        if cache_key in self.cache:
            logger.info(f"Cache hit for: {text}")
            return self.cache[cache_key]
        
        try:
            # 1. 使用 Qwen 解析查询意图
            nlu_result = self.qwen.parse_query(text)
            
            # 2. 构建提示词
            prompt = self._build_prompt(text, nlu_result, table_name)
            
            # 3. 调用 Qwen 模型生成 SQL（模拟）
            # 在实际部署中，这里会调用 Qwen API
            sql = self._call_qwen_model(prompt)
            
            # 4. 缓存结果
            self.cache[cache_key] = sql
            
            logger.info(f"Generated SQL via Qwen: {text} -> {sql}")
            
            return sql
            
        except Exception as e:
            logger.error(f"Error generating SQL with Qwen for '{text}': {str(e)}")
            # 降级到规则引擎
            from sql_generator import SQLGenerator
            fallback_generator = SQLGenerator()
            fallback_sql = fallback_generator.generate_sql(nlu_result, table_name)
            
            logger.info(f"Falling back to rule-based generator: {fallback_sql}")
            return fallback_sql
    
    def _build_prompt(self, text: str, nlu_result: Dict[str, Any], table_name: str) -> str:
        """
        构建给 Qwen 的提示词
        """
        entities = nlu_result.get('entities', {})
        time_range = nlu_result.get('time_range', {})
        
        # 构建数据库模式描述
        schema_info = f"""
        数据库表名: {table_name}
        可能的字段包括：
        - 销售额 (数值型)
        - 产品 (字符串型)
        - 地区 (字符串型)
        - 时间 (日期型)
        - 客户 (字符串型)
        - 渠道 (字符串型)
        - 成本 (数值型)
        - 利润 (数值型)
        """
        
        prompt = f"""
        你是一个专业的 SQL 生成助手，将自然语言查询转换为 MySQL 查询语句。
        
        {schema_info}
        
        查询要求：
        1. 仅生成 SQL 语句，不要包含任何解释
        2. 使用标准 SQL 语法
        3. 使用 {table_name} 表
        4. 如果查询涉及时间范围，请使用 WHERE 子句过滤
        5. 如果查询要求排序，请使用 ORDER BY
        6. 如果查询要求前 N 个结果，请使用 LIMIT
        7. 如果查询要求聚合，请使用 SUM、AVG、COUNT 等函数
        
        自然语言查询：{text}
        
        请直接返回 SQL 语句：
        """
        
        return prompt.strip()
    
    def _call_qwen_model(self, prompt: str) -> str:
        """
        模拟调用 Qwen 模型
        
        在实际部署中，这里会调用 Qwen API
        """
        # 模拟 Qwen 模型的响应
        # 在真实环境中，这会是一个 API 调用
        
        # 这里使用一个简单的规则来生成合理的 SQL，
        # 但在实际中，这将是 Qwen 模型的输出
        
        # 简单的模式匹配来生成示例 SQL
        if '销售额' in prompt and ('最高' in prompt or '最多' in prompt):
            return "SELECT 产品, SUM(销售额) as total_sales FROM sales_data GROUP BY 产品 ORDER BY total_sales DESC LIMIT 1"
        
        if '销售额' in prompt and ('平均' in prompt or '均值' in prompt):
            return "SELECT AVG(销售额) as avg_sales FROM sales_data"
        
        if '销售额' in prompt and ('增长' in prompt or '变化' in prompt):
            return "SELECT 月份, SUM(销售额) as monthly_sales FROM sales_data GROUP BY 月份 ORDER BY 月份 ASC"
        
        # 默认查询
        return "SELECT * FROM sales_data LIMIT 10"
    
    def get_model_info(self) -> Dict[str, Any]:
        """
        获取模型信息
        """
        return {
            "model_name": self.model_name,
            "version": "1.0",
            "capabilities": ["direct_sql_generation", "natural_language_understanding"],
            "language": "zh-CN"
        }
    
    def clear_cache(self):
        """
        清除缓存
        """
        self.cache.clear()
        logger.info("SQL generation cache cleared")