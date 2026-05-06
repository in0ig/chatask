"""
AI模型服务 - 混合云+端架构
支持云端Qwen模型和本地OpenAI模型的统一调用
"""

import asyncio
import json
import re
import time
from typing import Dict, Any, Optional, List, AsyncIterator
from dataclasses import dataclass
from enum import Enum
import logging
from abc import ABC, abstractmethod

import httpx
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)


class ModelType(Enum):
    """模型类型枚举"""
    QWEN_CLOUD = "qwen_cloud"  # 云端Qwen模型
    OPENAI_LOCAL = "openai_local"  # 本地OpenAI模型


@dataclass
class ModelResponse:
    """模型响应数据结构"""
    content: str
    model_type: ModelType
    tokens_used: int
    response_time: float
    metadata: Dict[str, Any] = None


@dataclass
class TokenUsage:
    """Token使用量统计"""
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost_estimate: float = 0.0


class AIModelError(Exception):
    """AI模型调用异常"""
    def __init__(self, message: str, model_type: ModelType, retry_count: int = 0):
        super().__init__(message)
        self.model_type = model_type
        self.retry_count = retry_count


class BaseModelAdapter(ABC):
    """模型适配器基类"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.retry_count = config.get('retry_count', 3)
        self.retry_delay = config.get('retry_delay', 1.0)
        
    @abstractmethod
    async def generate(self, prompt: str, **kwargs) -> ModelResponse:
        """生成响应"""
        pass
    
    @abstractmethod
    async def generate_stream(self, prompt: str, **kwargs) -> AsyncIterator[str]:
        """流式生成响应"""
        pass
    
    async def _retry_with_backoff(self, operation, max_retries: int = None):
        """带退避的重试机制"""
        max_retries = max_retries or self.retry_count
        
        for attempt in range(max_retries + 1):
            try:
                return await operation()
            except Exception as e:
                if attempt == max_retries:
                    raise AIModelError(
                        f"Failed after {max_retries} retries: {str(e)}",
                        self.model_type,
                        attempt
                    )
                
                # 指数退避
                delay = self.retry_delay * (2 ** attempt)
                logger.warning(f"Attempt {attempt + 1} failed, retrying in {delay}s: {str(e)}")
                await asyncio.sleep(delay)


class QwenCloudAdapter(BaseModelAdapter):
    """阿里云Qwen模型适配器"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.model_type = ModelType.QWEN_CLOUD
        self.api_key = config['api_key']
        self.base_url = config.get('base_url', 'https://dashscope.aliyuncs.com/api/v1')
        self.model_name = config.get('model_name', 'qwen-turbo')
        self.max_tokens = config.get('max_tokens', 2000)
        self.temperature = config.get('temperature', 0.1)
        
        # Token使用量监控
        self.token_usage_stats = {
            'total_requests': 0,
            'total_tokens': 0,
            'total_cost': 0.0,
            'daily_usage': {}
        }
        
        # HTTP客户端
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(60.0),
            headers={
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }
        )
    
    async def generate(self, prompt: str, **kwargs) -> ModelResponse:
        """生成响应"""
        start_time = time.time()
        
        async def _generate():
            # 确保prompt不包含业务数据，仅包含Schema和问题
            sanitized_prompt = self._sanitize_prompt(prompt)
            
            # 检查是否使用兼容模式（OpenAI 格式）
            is_compatible_mode = 'compatible-mode' in self.base_url
            
            if is_compatible_mode:
                # 兼容模式：使用 OpenAI 格式
                payload = {
                    'model': self.model_name,
                    'messages': [
                        {'role': 'user', 'content': sanitized_prompt}
                    ],
                    'max_tokens': kwargs.get('max_tokens', self.max_tokens),
                    'temperature': kwargs.get('temperature', self.temperature),
                    'stream': False
                }
                endpoint = f'{self.base_url}/chat/completions'
            else:
                # 原生模式：使用 DashScope 格式
                payload = {
                    'model': self.model_name,
                    'input': {
                        'messages': [
                            {'role': 'user', 'content': sanitized_prompt}
                        ]
                    },
                    'parameters': {
                        'max_tokens': kwargs.get('max_tokens', self.max_tokens),
                        'temperature': kwargs.get('temperature', self.temperature),
                        'result_format': 'message'
                    }
                }
                endpoint = f'{self.base_url}/services/aigc/text-generation/generation'
            
            response = await self.client.post(endpoint, json=payload)
            response.raise_for_status()
            
            result = response.json()
            
            # 根据模式解析响应
            if is_compatible_mode:
                # OpenAI 兼容模式响应格式
                if 'choices' not in result or not result['choices']:
                    raise AIModelError(
                        f"Qwen API error: No choices in response - {result}",
                        self.model_type
                    )
                content = result['choices'][0]['message']['content']
                usage = result.get('usage', {})
                token_usage = TokenUsage(
                    prompt_tokens=usage.get('prompt_tokens', 0),
                    completion_tokens=usage.get('completion_tokens', 0),
                    total_tokens=usage.get('total_tokens', 0),
                    cost_estimate=self._calculate_cost(usage.get('total_tokens', 0))
                )
            else:
                # DashScope 原生模式响应格式
                if 'output' not in result:
                    raise AIModelError(
                        f"Qwen API error: Invalid response format - {result}",
                        self.model_type
                    )
                output = result['output']
                if 'choices' not in output or not output['choices']:
                    raise AIModelError(
                        f"Qwen API error: No choices in response - {result}",
                        self.model_type
                    )
                content = output['choices'][0]['message']['content']
                usage = result.get('usage', {})
                token_usage = TokenUsage(
                    prompt_tokens=usage.get('input_tokens', 0),
                    completion_tokens=usage.get('output_tokens', 0),
                    total_tokens=usage.get('total_tokens', 0),
                    cost_estimate=self._calculate_cost(usage.get('total_tokens', 0))
                )
            
            # 更新Token使用量统计
            self._update_token_stats(token_usage)
            
            return ModelResponse(
                content=content,
                model_type=self.model_type,
                tokens_used=token_usage.total_tokens,
                response_time=time.time() - start_time,
                metadata={'usage': token_usage}
            )
        
        return await self._retry_with_backoff(_generate)
    
    async def generate_stream(self, prompt: str, **kwargs):
        """流式生成响应"""
        # 确保prompt不包含业务数据
        sanitized_prompt = self._sanitize_prompt(prompt)
        
        # 检查是否使用兼容模式
        is_compatible_mode = 'compatible-mode' in self.base_url
        
        if is_compatible_mode:
            # 兼容模式：使用 OpenAI 格式
            payload = {
                'model': self.model_name,
                'messages': [
                    {'role': 'user', 'content': sanitized_prompt}
                ],
                'max_tokens': kwargs.get('max_tokens', self.max_tokens),
                'temperature': kwargs.get('temperature', self.temperature),
                'stream': True
            }
            endpoint = f'{self.base_url}/chat/completions'
        else:
            # 原生模式：使用 DashScope 格式
            payload = {
                'model': self.model_name,
                'input': {
                    'messages': [
                        {'role': 'user', 'content': sanitized_prompt}
                    ]
                },
                'parameters': {
                    'max_tokens': kwargs.get('max_tokens', self.max_tokens),
                    'temperature': kwargs.get('temperature', self.temperature),
                    'incremental_output': True
                }
            }
            endpoint = f'{self.base_url}/services/aigc/text-generation/generation'
        
        async with self.client.stream('POST', endpoint, json=payload) as response:
            response.raise_for_status()
            
            async for line in response.aiter_lines():
                if line.strip():
                    # 跳过 SSE 的 "data: " 前缀
                    if line.startswith('data: '):
                        line = line[6:]
                    
                    # 跳过 [DONE] 标记
                    if line == '[DONE]':
                        break
                    
                    try:
                        data = json.loads(line)
                        
                        if is_compatible_mode:
                            # OpenAI 兼容模式
                            if 'choices' in data and data['choices']:
                                delta = data['choices'][0].get('delta', {})
                                if 'content' in delta:
                                    yield delta['content']
                        else:
                            # DashScope 原生模式
                            if 'output' in data:
                                output = data['output']
                                # 流式响应使用 text 字段
                                if 'text' in output:
                                    yield output['text']
                                # 非流式响应使用 choices 字段
                                elif 'choices' in output and output['choices']:
                                    content = output['choices'][0]['message']['content']
                                    yield content
                    except json.JSONDecodeError:
                        continue
    
    def _sanitize_prompt(self, prompt: str) -> str:
        """清洗prompt，确保不包含业务数据"""
        # 检查是否包含可能的业务数据模式
        sensitive_patterns = [
            r'\b\d{4}-\d{2}-\d{2}\b',  # 日期
            r'\b\d+\.\d+\b',  # 数值
            r"'[^']*'",  # 字符串值
            r'"[^"]*"',  # 双引号字符串值
        ]
        
        # 如果发现敏感数据，记录警告
        for pattern in sensitive_patterns:
            if re.search(pattern, prompt):
                logger.warning(f"Potential sensitive data detected in prompt: {pattern}")
        
        # 返回原始prompt（在实际实现中，这里应该有更严格的数据清洗逻辑）
        return prompt
    
    def _calculate_cost(self, total_tokens: int) -> float:
        """计算Token使用成本"""
        # Qwen模型的定价（示例价格，实际价格请参考官方文档）
        cost_per_1k_tokens = 0.002  # $0.002 per 1K tokens
        return (total_tokens / 1000) * cost_per_1k_tokens
    
    def _update_token_stats(self, usage: TokenUsage):
        """更新Token使用量统计"""
        today = time.strftime('%Y-%m-%d')
        
        self.token_usage_stats['total_requests'] += 1
        self.token_usage_stats['total_tokens'] += usage.total_tokens
        self.token_usage_stats['total_cost'] += usage.cost_estimate
        
        if today not in self.token_usage_stats['daily_usage']:
            self.token_usage_stats['daily_usage'][today] = {
                'requests': 0,
                'tokens': 0,
                'cost': 0.0
            }
        
        daily = self.token_usage_stats['daily_usage'][today]
        daily['requests'] += 1
        daily['tokens'] += usage.total_tokens
        daily['cost'] += usage.cost_estimate
    
    def get_token_usage_stats(self) -> Dict[str, Any]:
        """获取Token使用量统计"""
        return self.token_usage_stats.copy()
    
    def extract_sql_from_response(self, response: str) -> Optional[str]:
        """从模型响应中提取SQL语句"""
        # 正则表达式提取SQL
        patterns = [
            r'```sql\s*(.*?)\s*```',  # Markdown SQL代码块
            r'```\s*(SELECT.*?;?)\s*```',  # 通用代码块中的SELECT语句
            r'(SELECT\s+.*?(?:;|$))',  # 直接的SELECT语句
            r'(INSERT\s+.*?(?:;|$))',  # INSERT语句
            r'(UPDATE\s+.*?(?:;|$))',  # UPDATE语句
            r'(DELETE\s+.*?(?:;|$))',  # DELETE语句
        ]
        
        for pattern in patterns:
            match = re.search(pattern, response, re.DOTALL | re.IGNORECASE)
            if match:
                sql = match.group(1).strip()
                # 清理SQL语句
                sql = re.sub(r'\s+', ' ', sql)  # 规范化空白字符
                sql = sql.rstrip(';') + ';'  # 确保以分号结尾
                return sql
        
        return None
    
    async def close(self):
        """关闭HTTP客户端"""
        await self.client.aclose()


class OpenAILocalAdapter(BaseModelAdapter):
    """本地OpenAI模型适配器 - 专门负责数据分析和追问"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.model_type = ModelType.OPENAI_LOCAL
        
        self.api_key = config.get('api_key', 'none')
        self.base_url = config.get('base_url', 'http://localhost:11434/v1')
        self.model_name = config.get('model_name', 'qwen3.5')
        self.max_tokens = config.get('max_tokens', None)  # None = 不限制，让模型自行决定
        self.temperature = config.get('temperature', 0.7)
        # Qwen3 思考模型控制：false = 禁用 thinking，直接输出答案（推荐）
        self.enable_thinking = config.get('enable_thinking', False)
        
        # 判断是否为 OpenAI 兼容接口（内网模型 / Ollama 等都走兼容模式）
        self._is_compatible = 'compatible-mode' in self.base_url or '/v1' in self.base_url
        
        # 性能优化配置
        self.max_concurrent_requests = config.get('max_concurrent_requests', 5)
        self.request_timeout = config.get('request_timeout', 60)
        self.audit_logging = config.get('audit_logging', True)
        
        self._active_requests = 0
        self._request_semaphore = asyncio.Semaphore(self.max_concurrent_requests)
        
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(self.request_timeout),
            headers={
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }
        )
        
        self.processing_stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'avg_response_time': 0.0,
            'data_analysis_count': 0,
            'followup_questions_count': 0
        }
    
    def _build_payload(self, messages: list, stream: bool = False, **kwargs) -> tuple:
        """根据接口类型构建请求 payload 和 endpoint"""
        if self._is_compatible:
            # OpenAI 兼容格式（内网 Qwen3.5 / Ollama 等）
            payload = {
                'model': self.model_name,
                'messages': messages,
                'temperature': kwargs.get('temperature', self.temperature),
                'stream': stream,
                # Qwen3 思考模型：通过 chat_template_kwargs 禁用 thinking 模式
                'chat_template_kwargs': {
                    'enable_thinking': self.enable_thinking
                },
            }
            # 只有明确配置了 max_tokens 时才传（不传则让模型自行决定）
            max_tokens = kwargs.get('max_tokens', self.max_tokens)
            if max_tokens:
                payload['max_tokens'] = max_tokens
            endpoint = f'{self.base_url}/chat/completions'
        else:
            # DashScope 原生格式
            payload = {
                'model': self.model_name,
                'input': {'messages': messages},
                'parameters': {
                    'max_tokens': kwargs.get('max_tokens', self.max_tokens),
                    'temperature': kwargs.get('temperature', self.temperature),
                    'result_format': 'message',
                    **(({'incremental_output': True}) if stream else {})
                }
            }
            endpoint = f'{self.base_url}/services/aigc/text-generation/generation'
        return payload, endpoint
    
    def _parse_response(self, result: dict) -> str:
        """解析响应内容"""
        if self._is_compatible:
            if 'choices' not in result or not result['choices']:
                raise AIModelError(f"Local model API error: No choices - {result}", self.model_type)
            message = result['choices'][0]['message']
            content = message.get('content')
            if content is None:
                raise AIModelError(
                    f"Local model returned null content. "
                    f"If using Qwen3, ensure enable_thinking=False is set. "
                    f"reasoning_content length: {len(message.get('reasoning_content') or '')}",
                    self.model_type
                )
            return content
        else:
            if 'output' not in result or 'choices' not in result.get('output', {}):
                raise AIModelError(f"Local model API error: Invalid format - {result}", self.model_type)
            return result['output']['choices'][0]['message']['content']
    
    def _parse_stream_chunk(self, data: dict) -> Optional[str]:
        """解析流式响应块"""
        if self._is_compatible:
            if 'choices' in data and data['choices']:
                delta = data['choices'][0].get('delta', {})
                # 只取 content，忽略 reasoning_content（thinking 模式已禁用）
                return delta.get('content')
        else:
            if 'output' in data:
                output = data['output']
                if 'text' in output:
                    return output['text']
                elif 'choices' in output and output['choices']:
                    return output['choices'][0]['message'].get('content')
        return None

    async def generate(self, prompt: str, **kwargs) -> ModelResponse:
        """生成响应"""
        start_time = time.time()
        
        async with self._request_semaphore:
            self._active_requests += 1
            self.processing_stats['total_requests'] += 1
            
            try:
                async def _generate():
                    if self.audit_logging:
                        logger.info(f"Local model processing request: {prompt[:100]}...")
                    
                    messages = [{'role': 'user', 'content': prompt}]
                    payload, endpoint = self._build_payload(messages, stream=False, **kwargs)
                    
                    response = await self.client.post(endpoint, json=payload)
                    response.raise_for_status()
                    
                    result = response.json()
                    content = self._parse_response(result)
                    usage = result.get('usage', {})
                    
                    self.processing_stats['successful_requests'] += 1
                    self.processing_stats['data_analysis_count'] += 1
                    
                    response_time = time.time() - start_time
                    self._update_avg_response_time(response_time)
                    
                    return ModelResponse(
                        content=content,
                        model_type=self.model_type,
                        tokens_used=usage.get('total_tokens', 0),
                        response_time=response_time,
                        metadata={'usage': usage, 'data_analysis': True}
                    )
                
                return await self._retry_with_backoff(_generate)
                
            except Exception as e:
                self.processing_stats['failed_requests'] += 1
                logger.error(f"Local model generation failed: {str(e)}")
                raise
            finally:
                self._active_requests -= 1
    
    async def generate_stream(self, prompt: str, **kwargs):
        """流式生成响应"""
        async with self._request_semaphore:
            self._active_requests += 1
            
            try:
                if self.audit_logging:
                    logger.info(f"Local model streaming request: {prompt[:100]}...")
                
                messages = [{'role': 'user', 'content': prompt}]
                payload, endpoint = self._build_payload(messages, stream=True, **kwargs)
                
                async with self.client.stream('POST', endpoint, json=payload) as response:
                    response.raise_for_status()
                    
                    async for line in response.aiter_lines():
                        if line.strip():
                            if line.startswith('data: '):
                                line = line[6:]
                            if line == '[DONE]':
                                break
                            try:
                                data = json.loads(line)
                                chunk = self._parse_stream_chunk(data)
                                if chunk:
                                    yield chunk
                            except json.JSONDecodeError:
                                continue
                                
                self.processing_stats['successful_requests'] += 1
                self.processing_stats['followup_questions_count'] += 1
                
            except Exception as e:
                self.processing_stats['failed_requests'] += 1
                logger.error(f"Local model streaming failed: {str(e)}")
                raise
            finally:
                self._active_requests -= 1
    
    async def analyze_query_result(self, query_result: Dict[str, Any], user_question: str, **kwargs) -> ModelResponse:
        """分析查询结果并生成洞察"""
        analysis_prompt = self._build_analysis_prompt(query_result, user_question)
        return await self.generate(analysis_prompt, **kwargs)
    
    async def handle_followup_question(self, followup_question: str, current_data: Dict[str, Any], 
                                     previous_data: List[Dict[str, Any]] = None, **kwargs) -> ModelResponse:
        """处理追问问题"""
        followup_prompt = self._build_followup_prompt(followup_question, current_data, previous_data)
        return await self.generate(followup_prompt, **kwargs)
    
    def _build_analysis_prompt(self, query_result: Dict[str, Any], user_question: str) -> str:
        """构建数据分析专用的prompt"""
        data = query_result.get('data', [])
        columns = query_result.get('columns', [])
        
        # 数据摘要
        data_summary = f"数据包含 {len(data)} 行记录，{len(columns)} 个字段。"
        if columns:
            data_summary += f"\n字段名称：{', '.join(columns)}"
        
        # 数据样本（前5行）
        sample_data = ""
        if data:
            sample_data = "\n数据样本（前5行）：\n"
            for i, row in enumerate(data[:5]):
                sample_data += f"第{i+1}行：{dict(zip(columns, row)) if columns else row}\n"
        
        prompt = f"""
用户问题：{user_question}

查询结果分析：
{data_summary}
{sample_data}

请基于以上查询结果，提供以下分析：
1. 数据概览和关键发现
2. 趋势分析（如果适用）
3. 异常值或特殊模式识别
4. 业务洞察和建议
5. 可能的后续分析方向

请用中文回答，保持专业和易懂。
"""
        return prompt
    
    def _build_followup_prompt(self, followup_question: str, current_data: Dict[str, Any], 
                              previous_data: List[Dict[str, Any]] = None) -> str:
        """构建追问专用的prompt"""
        current_summary = self._summarize_data(current_data)
        
        prompt = f"""
追问问题：{followup_question}

当前数据：
{current_summary}
"""
        
        # 如果有历史数据，添加对比分析
        if previous_data:
            prompt += "\n历史数据对比：\n"
            for i, prev_data in enumerate(previous_data[-3:]):  # 最多对比最近3次查询
                prev_summary = self._summarize_data(prev_data)
                prompt += f"历史查询{i+1}：\n{prev_summary}\n"
        
        prompt += """
请基于以上数据回答追问问题，如果有历史数据，请进行对比分析。
回答要求：
1. 直接回答用户的追问
2. 提供数据支撑
3. 如有对比数据，指出变化趋势
4. 给出专业的分析结论

请用中文回答。
"""
        return prompt
    
    def _summarize_data(self, data_dict: Dict[str, Any]) -> str:
        """数据摘要"""
        if not data_dict:
            return "无数据"
        
        data = data_dict.get('data', [])
        columns = data_dict.get('columns', [])
        
        summary = f"包含 {len(data)} 行记录"
        if columns:
            summary += f"，字段：{', '.join(columns)}"
        
        # 添加数据样本
        if data:
            summary += f"\n样本数据：{data[0] if len(data) > 0 else '无'}"
        
        return summary
    
    def _update_avg_response_time(self, response_time: float):
        """更新平均响应时间"""
        current_avg = self.processing_stats['avg_response_time']
        total_requests = self.processing_stats['total_requests']
        
        if total_requests == 1:
            self.processing_stats['avg_response_time'] = response_time
        else:
            # 计算移动平均
            self.processing_stats['avg_response_time'] = (
                (current_avg * (total_requests - 1) + response_time) / total_requests
            )
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """获取处理统计信息"""
        stats = self.processing_stats.copy()
        stats['active_requests'] = self._active_requests
        stats['success_rate'] = (
            stats['successful_requests'] / stats['total_requests'] 
            if stats['total_requests'] > 0 else 0.0
        )
        return stats
    
    async def close(self):
        """关闭HTTP客户端"""
        await self.client.aclose()


class AIModelService:
    """AI模型服务 - 统一管理云端和本地模型"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.adapters: Dict[ModelType, BaseModelAdapter] = {}
        
        # 初始化云端Qwen模型适配器
        if 'qwen_cloud' in config:
            self.adapters[ModelType.QWEN_CLOUD] = QwenCloudAdapter(config['qwen_cloud'])
        
        # 初始化本地OpenAI模型适配器
        if 'openai_local' in config:
            self.adapters[ModelType.OPENAI_LOCAL] = OpenAILocalAdapter(config['openai_local'])
        
        # 加载模型路由配置
        self._model_routing = config.get('model_routing', {})
        self._default_route = self._model_routing.get('default', 'cloud')
        self._stage_routes = self._model_routing.get('stages', {})
        logger.info(f"🔀 模型路由: default={self._default_route}, stages={self._stage_routes}")
    
    # ── 模型路由方法 ──────────────────────────────────────────────
    
    def _resolve_route(self, stage: str) -> str:
        """解析某阶段应使用 cloud 还是 local，返回 'cloud' 或 'local'"""
        return self._stage_routes.get(stage, self._default_route)
    
    async def call_model(self, prompt: str = "", stage: str = "intent_recognition", session_id: str = None, **kwargs) -> Dict[str, Any]:
        """根据配置路由调用对应模型（非流式）"""
        route = self._resolve_route(stage)
        logger.info(f"🔀 阶段 [{stage}] 路由到 [{route}] 模型")
        if route == "local":
            return await self.call_local_model(prompt, session_id=session_id, **kwargs)
        return await self.call_cloud_model(prompt, session_id=session_id, **kwargs)
    
    async def call_model_stream(self, prompt: str = "", stage: str = "intent_recognition", session_id: str = None, **kwargs):
        """根据配置路由调用对应模型（流式）"""
        route = self._resolve_route(stage)
        logger.info(f"🔀 阶段 [{stage}] 流式路由到 [{route}] 模型")
        if route == "local":
            async for chunk in self.call_local_model_stream(prompt, session_id=session_id, **kwargs):
                yield chunk
        else:
            async for chunk in self.call_cloud_model_stream(prompt, session_id=session_id, **kwargs):
                yield chunk
    
    # ── 原有方法 ──────────────────────────────────────────────────
    
    async def generate_sql(self, prompt: str, **kwargs) -> ModelResponse:
        """使用云端Qwen模型生成SQL"""
        if ModelType.QWEN_CLOUD not in self.adapters:
            raise AIModelError("Qwen cloud model not configured", ModelType.QWEN_CLOUD)
        
        adapter = self.adapters[ModelType.QWEN_CLOUD]
        response = await adapter.generate(prompt, **kwargs)
        
        # 尝试提取SQL
        if hasattr(adapter, 'extract_sql_from_response'):
            sql = adapter.extract_sql_from_response(response.content)
            if sql:
                response.metadata = response.metadata or {}
                response.metadata['extracted_sql'] = sql
        
        return response
    
    async def analyze_data_locally(self, prompt: str, **kwargs) -> ModelResponse:
        """使用本地OpenAI模型分析数据"""
        if ModelType.OPENAI_LOCAL not in self.adapters:
            raise AIModelError("OpenAI local model not configured", ModelType.OPENAI_LOCAL)
        
        adapter = self.adapters[ModelType.OPENAI_LOCAL]
        return await adapter.generate(prompt, **kwargs)
    
    async def analyze_query_result_locally(self, query_result: Dict[str, Any], user_question: str, **kwargs) -> ModelResponse:
        """使用本地模型分析查询结果"""
        if ModelType.OPENAI_LOCAL not in self.adapters:
            raise AIModelError("OpenAI local model not configured", ModelType.OPENAI_LOCAL)
        
        adapter = self.adapters[ModelType.OPENAI_LOCAL]
        if hasattr(adapter, 'analyze_query_result'):
            return await adapter.analyze_query_result(query_result, user_question, **kwargs)
        else:
            # 降级到普通generate方法
            prompt = f"分析以下查询结果：\n用户问题：{user_question}\n查询结果：{query_result}"
            return await adapter.generate(prompt, **kwargs)
    
    async def handle_followup_question_locally(self, followup_question: str, current_data: Dict[str, Any], 
                                             previous_data: List[Dict[str, Any]] = None, **kwargs) -> ModelResponse:
        """使用本地模型处理追问问题"""
        if ModelType.OPENAI_LOCAL not in self.adapters:
            raise AIModelError("OpenAI local model not configured", ModelType.OPENAI_LOCAL)
        
        adapter = self.adapters[ModelType.OPENAI_LOCAL]
        if hasattr(adapter, 'handle_followup_question'):
            return await adapter.handle_followup_question(followup_question, current_data, previous_data, **kwargs)
        else:
            # 降级到普通generate方法
            prompt = f"追问：{followup_question}\n当前数据：{current_data}"
            if previous_data:
                prompt += f"\n历史数据：{previous_data}"
            return await adapter.generate(prompt, **kwargs)
    
    async def call_cloud_model(self, prompt: str, session_id: str = None, model_type: str = "qwen", **kwargs) -> Dict[str, Any]:
        """调用云端模型（兼容方法）"""
        try:
            # 详细日志：记录调用信息
            logger.info("=" * 80)
            logger.info(f"🤖 调用云端模型")
            logger.info(f"📝 会话ID: {session_id}")
            logger.info(f"🎯 模型类型: {model_type}")
            logger.info(f"📊 Prompt 长度: {len(prompt)} 字符")
            logger.info("-" * 80)
            logger.info(f"📄 完整 Prompt:\n{prompt}")
            logger.info("-" * 80)
            
            # 调用模型
            response = await self.generate_sql(prompt, **kwargs)
            
            # 详细日志：记录响应信息
            logger.info(f"✅ 模型响应成功")
            logger.info(f"🎯 使用模型: {response.model_type.value}")
            logger.info(f"🔢 Token 使用: {response.tokens_used}")
            logger.info(f"⏱️  响应时间: {response.response_time:.2f}秒")
            logger.info(f"📝 响应内容长度: {len(response.content)} 字符")
            logger.info("-" * 80)
            logger.info(f"📄 完整响应:\n{response.content}")
            logger.info("=" * 80)
            
            return {
                "success": True,
                "content": response.content,
                "model_type": response.model_type.value,
                "tokens_used": response.tokens_used,
                "response_time": response.response_time
            }
        except Exception as e:
            logger.error("=" * 80)
            logger.error(f"❌ 云端模型调用失败")
            logger.error(f"📝 会话ID: {session_id}")
            logger.error(f"🎯 模型类型: {model_type}")
            logger.error(f"❌ 错误信息: {str(e)}")
            logger.error("=" * 80)
            return {
                "success": False,
                "error": str(e)
            }
    
    async def call_local_model(self, prompt: str, session_id: str = None, **kwargs) -> Dict[str, Any]:
        """调用本地模型（兼容方法）"""
        try:
            # 详细日志：记录调用信息
            logger.info("=" * 80)
            logger.info(f"🏠 调用本地模型")
            logger.info(f"📝 会话ID: {session_id}")
            logger.info(f"📊 Prompt 长度: {len(prompt)} 字符")
            logger.info("-" * 80)
            logger.info(f"📄 完整 Prompt:\n{prompt}")
            logger.info("-" * 80)
            
            # 调用模型
            response = await self.analyze_data_locally(prompt, **kwargs)
            
            # 详细日志：记录响应信息
            logger.info(f"✅ 本地模型响应成功")
            logger.info(f"🎯 使用模型: {response.model_type.value}")
            logger.info(f"🔢 Token 使用: {response.tokens_used}")
            logger.info(f"⏱️  响应时间: {response.response_time:.2f}秒")
            logger.info(f"📝 响应内容长度: {len(response.content)} 字符")
            logger.info("-" * 80)
            logger.info(f"📄 完整响应:\n{response.content}")
            logger.info("=" * 80)
            
            return {
                "success": True,
                "content": response.content,
                "model_type": response.model_type.value,
                "tokens_used": response.tokens_used,
                "response_time": response.response_time
            }
        except Exception as e:
            logger.error("=" * 80)
            logger.error(f"❌ 本地模型调用失败")
            logger.error(f"📝 会话ID: {session_id}")
            logger.error(f"❌ 错误信息: {str(e)}")
            logger.error("=" * 80)
            return {
                "success": False,
                "error": str(e)
            }
    
    async def call_cloud_model_stream(self, prompt: str, session_id: str = None, **kwargs) -> AsyncIterator[str]:
        """
        流式调用云端模型（Qwen）
        
        Args:
            prompt: 输入提示词
            session_id: 会话ID（可选）
            **kwargs: 其他参数
            
        Yields:
            str: 内容块
            
        Raises:
            AIModelError: 当云端模型未配置或调用失败时
        """
        if ModelType.QWEN_CLOUD not in self.adapters:
            raise AIModelError("Qwen cloud model not configured", ModelType.QWEN_CLOUD)
        
        adapter = self.adapters[ModelType.QWEN_CLOUD]
        accumulated_content = ""
        chunk_count = 0
        start_time = time.time()
        
        try:
            # 详细日志：记录流式调用开始
            logger.info("=" * 80)
            logger.info(f"🌊 开始流式调用云端模型")
            logger.info(f"📝 会话ID: {session_id}")
            logger.info(f"📊 Prompt 长度: {len(prompt)} 字符")
            logger.info("-" * 80)
            logger.info(f"📄 完整 Prompt:\n{prompt}")
            logger.info("-" * 80)
            
            # 流式生成内容
            async for chunk in adapter.generate_stream(prompt, **kwargs):
                accumulated_content += chunk
                chunk_count += 1
                
                # 记录每个块的接收
                logger.debug(f"📦 接收块 #{chunk_count}: {len(chunk)} 字符")
                
                yield chunk
            
            # 详细日志：记录流式调用完成
            elapsed_time = time.time() - start_time
            logger.info(f"✅ 流式调用完成")
            logger.info(f"📦 总块数: {chunk_count}")
            logger.info(f"📝 累积内容长度: {len(accumulated_content)} 字符")
            logger.info(f"⏱️  总耗时: {elapsed_time:.2f}秒")
            logger.info("-" * 80)
            logger.info(f"📄 完整累积内容:\n{accumulated_content}")
            logger.info("=" * 80)
            
        except Exception as e:
            elapsed_time = time.time() - start_time
            logger.error("=" * 80)
            logger.error(f"❌ 云端模型流式调用失败")
            logger.error(f"📝 会话ID: {session_id}")
            logger.error(f"📦 已接收块数: {chunk_count}")
            logger.error(f"📝 已累积内容长度: {len(accumulated_content)} 字符")
            logger.error(f"⏱️  失败前耗时: {elapsed_time:.2f}秒")
            logger.error(f"❌ 错误信息: {str(e)}")
            logger.error("=" * 80)
            
            # 如果有累积内容，返回它
            if accumulated_content:
                logger.warning(f"⚠️  返回已累积的内容: {len(accumulated_content)} 字符")
                yield accumulated_content
            
            raise AIModelError(
                f"Cloud model streaming failed: {str(e)}",
                ModelType.QWEN_CLOUD
            )
    
    async def call_local_model_stream(self, prompt: str, session_id: str = None, **kwargs) -> AsyncIterator[str]:
        """
        流式调用本地模型（OpenAI/Qwen）
        
        Args:
            prompt: 输入提示词
            session_id: 会话ID（可选）
            **kwargs: 其他参数
            
        Yields:
            str: 内容块
            
        Raises:
            AIModelError: 当本地模型未配置或调用失败时
        """
        if ModelType.OPENAI_LOCAL not in self.adapters:
            raise AIModelError("OpenAI local model not configured", ModelType.OPENAI_LOCAL)
        
        adapter = self.adapters[ModelType.OPENAI_LOCAL]
        accumulated_content = ""
        chunk_count = 0
        start_time = time.time()
        
        try:
            # 详细日志：记录流式调用开始
            logger.info("=" * 80)
            logger.info(f"🌊 开始流式调用本地模型")
            logger.info(f"📝 会话ID: {session_id}")
            logger.info(f"📊 Prompt 长度: {len(prompt)} 字符")
            logger.info("-" * 80)
            logger.info(f"📄 完整 Prompt:\n{prompt}")
            logger.info("-" * 80)
            
            # 流式生成内容
            async for chunk in adapter.generate_stream(prompt, **kwargs):
                accumulated_content += chunk
                chunk_count += 1
                
                # 记录每个块的接收
                logger.debug(f"📦 接收块 #{chunk_count}: {len(chunk)} 字符")
                
                yield chunk
            
            # 详细日志：记录流式调用完成
            elapsed_time = time.time() - start_time
            logger.info(f"✅ 流式调用完成")
            logger.info(f"📦 总块数: {chunk_count}")
            logger.info(f"📝 累积内容长度: {len(accumulated_content)} 字符")
            logger.info(f"⏱️  总耗时: {elapsed_time:.2f}秒")
            logger.info("-" * 80)
            logger.info(f"📄 完整累积内容:\n{accumulated_content}")
            logger.info("=" * 80)
            
        except Exception as e:
            elapsed_time = time.time() - start_time
            logger.error("=" * 80)
            logger.error(f"❌ 本地模型流式调用失败")
            logger.error(f"📝 会话ID: {session_id}")
            logger.error(f"📦 已接收块数: {chunk_count}")
            logger.error(f"📝 已累积内容长度: {len(accumulated_content)} 字符")
            logger.error(f"⏱️  失败前耗时: {elapsed_time:.2f}秒")
            logger.error(f"❌ 错误信息: {str(e)}")
            logger.error("=" * 80)
            
            # 如果有累积内容，返回它
            if accumulated_content:
                logger.warning(f"⚠️  返回已累积的内容: {len(accumulated_content)} 字符")
                yield accumulated_content
            
            raise AIModelError(
                f"Local model streaming failed: {str(e)}",
                ModelType.OPENAI_LOCAL
            )
    
    async def generate_stream(self, model_type: ModelType, prompt: str, **kwargs):
        """流式生成响应"""
        if model_type not in self.adapters:
            raise AIModelError(f"Model {model_type} not configured", model_type)
        
        adapter = self.adapters[model_type]
        async for chunk in adapter.generate_stream(prompt, **kwargs):
            yield chunk
    
    def get_token_usage_stats(self, model_type: ModelType = ModelType.QWEN_CLOUD) -> Dict[str, Any]:
        """获取Token使用量统计"""
        if model_type not in self.adapters:
            return {}
        
        adapter = self.adapters[model_type]
        if hasattr(adapter, 'get_token_usage_stats'):
            return adapter.get_token_usage_stats()
        
        return {}
    
    async def close(self):
        """关闭所有适配器"""
        for adapter in self.adapters.values():
            if hasattr(adapter, 'close'):
                await adapter.close()


# 全局AI模型服务实例
_ai_service: Optional[AIModelService] = None


def get_ai_service() -> AIModelService:
    """获取AI模型服务实例"""
    global _ai_service
    if _ai_service is None:
        raise RuntimeError("AI model service not initialized")
    return _ai_service


def init_ai_service(config: Dict[str, Any]) -> AIModelService:
    """初始化AI模型服务"""
    global _ai_service
    _ai_service = AIModelService(config)
    return _ai_service