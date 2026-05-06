"""
意图识别服务 - 基于云端Qwen模型的智能意图识别
"""

import json
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum

from .ai_model_service import get_ai_service, ModelType, AIModelError
from .prompt_manager import prompt_manager, PromptType

logger = logging.getLogger(__name__)


class IntentType(Enum):
    """意图类型枚举"""
    QUERY = "query"  # 智能问数
    REPORT = "report"  # 生成报告
    UNKNOWN = "unknown"  # 未知意图


@dataclass
class IntentResult:
    """意图识别结果"""
    intent: IntentType
    confidence: float
    reasoning: str
    original_question: str
    metadata: Dict[str, Any] = None


class IntentRecognitionError(Exception):
    """意图识别异常"""
    def __init__(self, message: str, original_question: str = None):
        super().__init__(message)
        self.original_question = original_question


class IntentRecognitionService:
    """意图识别服务"""
    
    def __init__(self):
        self.ai_service = get_ai_service()
        self.prompt_manager = prompt_manager
        
        # 意图识别配置
        self.confidence_threshold = 0.7  # 置信度阈值
        self.max_retries = 3  # 最大重试次数
        
        # 统计信息
        self.stats = {
            'total_requests': 0,
            'successful_recognitions': 0,
            'failed_recognitions': 0,
            'query_intents': 0,
            'report_intents': 0,
            'unknown_intents': 0,
            'avg_confidence': 0.0,
            'avg_response_time': 0.0
        }
    
    async def identify_intent(self, user_question: str, context: Dict[str, Any] = None) -> IntentResult:
        """
        识别用户问题的意图
        
        Args:
            user_question: 用户问题
            context: 上下文信息（可选）
            
        Returns:
            IntentResult: 意图识别结果
            
        Raises:
            IntentRecognitionError: 意图识别失败
        """
        if not user_question or not user_question.strip():
            raise IntentRecognitionError("用户问题不能为空")
        
        user_question = user_question.strip()
        self.stats['total_requests'] += 1
        
        try:
            # 构建意图识别prompt
            prompt = self._build_intent_prompt(user_question, context)
            
            # 调用云端Qwen模型
            response = await self.ai_service.generate_sql(prompt, temperature=0.1)
            
            # 解析意图识别结果
            intent_result = self._parse_intent_response(response.content, user_question)
            
            # 更新统计信息
            self._update_stats(intent_result, response.response_time)
            
            logger.info(f"Intent identified: {intent_result.intent.value} (confidence: {intent_result.confidence:.2f}) for question: {user_question[:100]}...")
            
            return intent_result
            
        except Exception as e:
            self.stats['failed_recognitions'] += 1
            logger.error(f"Intent recognition failed for question '{user_question[:100]}...': {str(e)}")
            
            if isinstance(e, IntentRecognitionError):
                raise
            else:
                raise IntentRecognitionError(f"意图识别失败: {str(e)}", user_question)
    
    def _build_intent_prompt(self, user_question: str, context: Dict[str, Any] = None) -> str:
        """构建意图识别prompt"""
        try:
            # 格式化历史对话上下文
            history_context = self._format_history_context(context.get('history_messages', []) if context else [])
            
            # 使用prompt管理器获取模板
            prompt = self.prompt_manager.render_prompt(PromptType.INTENT_RECOGNITION, {
                'user_question': user_question,
                'history_context': history_context
            })
            
            # 如果有其他上下文信息，添加到prompt中
            if context:
                context_info = self._format_context(context)
                if context_info:
                    prompt += f"\n\n上下文信息：\n{context_info}"
            
            return prompt
            
        except Exception as e:
            logger.error(f"Failed to build intent prompt: {str(e)}")
            # 降级到硬编码prompt
            return self._get_fallback_prompt(user_question)
    
    def _format_history_context(self, history_messages: List[Dict[str, Any]]) -> str:
        """格式化历史对话上下文"""
        if not history_messages:
            return "无历史对话"
        
        formatted = []
        # 最近3轮对话（6条消息）
        for msg in history_messages[-6:]:
            role = "用户" if msg['role'] == 'user' else "AI助手"
            content = msg.get('content', '')
            if content:
                # 限制每条消息长度为200字符
                formatted.append(f"{role}: {content[:200]}")
        
        return "\n".join(formatted) if formatted else "无历史对话"
    
    def _format_context(self, context: Dict[str, Any]) -> str:
        """格式化上下文信息"""
        context_parts = []
        
        # 对话历史
        if 'conversation_history' in context:
            history = context['conversation_history']
            if history:
                context_parts.append(f"对话历史：最近{len(history)}轮对话")
        
        # 用户偏好
        if 'user_preferences' in context:
            prefs = context['user_preferences']
            if prefs:
                context_parts.append(f"用户偏好：{', '.join(prefs.keys())}")
        
        # 当前会话状态
        if 'session_state' in context:
            state = context['session_state']
            if state:
                context_parts.append(f"会话状态：{state}")
        
        return '\n'.join(context_parts)
    
    def _get_fallback_prompt(self, user_question: str) -> str:
        """获取降级prompt（硬编码）"""
        return f"""
请分析用户的问题，判断用户的意图类型：

用户问题：{user_question}

请从以下两种意图中选择一种：
1. 智能问数：用户想要查询具体的数据，获取数值、统计结果等
2. 生成报告：用户想要生成综合性的分析报告或总结

请以JSON格式返回结果：
{{
  "intent": "query" | "report",
  "confidence": 0.0-1.0,
  "reasoning": "判断理由"
}}
"""
    
    def _parse_intent_response(self, response_content: str, original_question: str) -> IntentResult:
        """解析意图识别响应"""
        try:
            # 尝试提取JSON
            json_match = self._extract_json_from_response(response_content)
            if not json_match:
                raise IntentRecognitionError(f"无法从响应中提取JSON: {response_content}")
            
            result_data = json.loads(json_match)
            
            # 验证必需字段
            if 'intent' not in result_data:
                raise IntentRecognitionError("响应中缺少intent字段")
            
            # 解析意图类型
            intent_str = result_data['intent'].lower()
            if intent_str == 'query':
                intent = IntentType.QUERY
            elif intent_str == 'report':
                intent = IntentType.REPORT
            else:
                intent = IntentType.UNKNOWN
            
            # 解析置信度
            confidence = float(result_data.get('confidence', 0.0))
            if confidence < 0.0 or confidence > 1.0:
                logger.warning(f"Invalid confidence value: {confidence}, clamping to [0.0, 1.0]")
                confidence = max(0.0, min(1.0, confidence))
            
            # 解析推理过程
            reasoning = result_data.get('reasoning', '未提供推理过程')
            
            # 检查置信度阈值
            if confidence < self.confidence_threshold:
                logger.warning(f"Low confidence intent recognition: {confidence:.2f} < {self.confidence_threshold}")
                intent = IntentType.UNKNOWN
            
            return IntentResult(
                intent=intent,
                confidence=confidence,
                reasoning=reasoning,
                original_question=original_question,
                metadata={
                    'raw_response': response_content,
                    'parsed_data': result_data
                }
            )
            
        except json.JSONDecodeError as e:
            raise IntentRecognitionError(f"JSON解析失败: {str(e)}")
        except Exception as e:
            raise IntentRecognitionError(f"响应解析失败: {str(e)}")
    
    def _extract_json_from_response(self, response: str) -> Optional[str]:
        """从响应中提取JSON"""
        import re
        
        # 尝试多种JSON提取模式
        patterns = [
            r'```json\s*(.*?)\s*```',  # Markdown JSON代码块
            r'```\s*(\{.*?\})\s*```',  # 通用代码块
            r'(\{[^{}]*"intent"[^{}]*\})',  # 包含intent的JSON对象
            r'(\{.*?\})',  # 任何JSON对象
        ]
        
        for pattern in patterns:
            match = re.search(pattern, response, re.DOTALL | re.IGNORECASE)
            if match:
                json_str = match.group(1).strip()
                # 验证是否为有效JSON
                try:
                    json.loads(json_str)
                    return json_str
                except json.JSONDecodeError:
                    continue
        
        return None
    
    def _update_stats(self, intent_result: IntentResult, response_time: float):
        """更新统计信息"""
        self.stats['successful_recognitions'] += 1
        
        # 更新意图类型统计
        if intent_result.intent == IntentType.QUERY:
            self.stats['query_intents'] += 1
        elif intent_result.intent == IntentType.REPORT:
            self.stats['report_intents'] += 1
        else:
            self.stats['unknown_intents'] += 1
        
        # 更新平均置信度
        total_successful = self.stats['successful_recognitions']
        current_avg_confidence = self.stats['avg_confidence']
        self.stats['avg_confidence'] = (
            (current_avg_confidence * (total_successful - 1) + intent_result.confidence) / total_successful
        )
        
        # 更新平均响应时间
        current_avg_time = self.stats['avg_response_time']
        self.stats['avg_response_time'] = (
            (current_avg_time * (total_successful - 1) + response_time) / total_successful
        )
    
    def get_intent_statistics(self) -> Dict[str, Any]:
        """获取意图识别统计信息"""
        stats = self.stats.copy()
        
        # 计算成功率
        total_requests = stats['total_requests']
        if total_requests > 0:
            stats['success_rate'] = stats['successful_recognitions'] / total_requests
            stats['failure_rate'] = stats['failed_recognitions'] / total_requests
        else:
            stats['success_rate'] = 0.0
            stats['failure_rate'] = 0.0
        
        # 计算意图分布
        successful = stats['successful_recognitions']
        if successful > 0:
            stats['intent_distribution'] = {
                'query': stats['query_intents'] / successful,
                'report': stats['report_intents'] / successful,
                'unknown': stats['unknown_intents'] / successful
            }
        else:
            stats['intent_distribution'] = {
                'query': 0.0,
                'report': 0.0,
                'unknown': 0.0
            }
        
        return stats
    
    def reset_statistics(self):
        """重置统计信息"""
        self.stats = {
            'total_requests': 0,
            'successful_recognitions': 0,
            'failed_recognitions': 0,
            'query_intents': 0,
            'report_intents': 0,
            'unknown_intents': 0,
            'avg_confidence': 0.0,
            'avg_response_time': 0.0
        }
        logger.info("Intent recognition statistics reset")


# 全局意图识别服务实例
_intent_service: Optional[IntentRecognitionService] = None


def get_intent_service() -> IntentRecognitionService:
    """获取意图识别服务实例"""
    global _intent_service
    if _intent_service is None:
        _intent_service = IntentRecognitionService()
    return _intent_service


def init_intent_service() -> IntentRecognitionService:
    """初始化意图识别服务"""
    global _intent_service
    _intent_service = IntentRecognitionService()
    return _intent_service