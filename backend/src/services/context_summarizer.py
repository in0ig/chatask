"""
上下文总结服务

实现本地模型和阿里云模型的上下文总结逻辑，包括总结触发、总结生成和总结保存。
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
import logging

from src.services.token_manager import TokenManager
from src.models.session_model import SessionModel
from src.services.session_service import SessionService

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_model_api_client(model_type: str):
    """
    获取模型API客户端
    
    Args:
        model_type: 模型类型 ('local' 或 'aliyun')
        
    Returns:
        模型API客户端对象
    """
    # 这是一个占位符实现，实际应该根据模型类型返回相应的API客户端
    # 在生产环境中，这里应该调用实际的模型API
    class MockModelClient:
        def generate_summary(self, prompt: str) -> str:
            # 返回一个模拟的总结
            return f"[模型总结] 基于提供的对话历史生成的总结"
    
    return MockModelClient()


class ContextSummarizer:
    """
    上下文总结服务类
    
    负责管理对话上下文的自动总结，根据模型类型和token数量触发总结逻辑
    """
    
    def __init__(self):
        self.token_manager = TokenManager()
        self.session_service = SessionService()
        
    def should_summarize(self, session_id: str, model_type: str) -> bool:
        """
        判断是否需要触发上下文总结
        
        Args:
            session_id: 会话ID
            model_type: 模型类型 ('local' 或 'aliyun')
            
        Returns:
            bool: 是否需要总结
        """
        try:
            # 获取当前会话的对话历史
            session = self.session_service.get_session(session_id)
            if not session or not session.conversation:
                return False
            
            # 计算当前对话的token数量
            # 将对话消息转换为Message对象列表
            from src.services.token_manager import Message, ModelType
            messages = [Message(msg.get('role', 'user'), msg.get('content', '')) for msg in session.conversation]
            
            # 根据模型类型确定使用的ModelType
            if model_type == 'local':
                model_enum = ModelType.LOCAL
                threshold = 15000
            elif model_type == 'aliyun':
                model_enum = ModelType.ALIBABA
                threshold = 800000
            else:
                logger.warning(f"未知的模型类型: {model_type}")
                return False
            
            # 计算token数量
            token_count = self.token_manager.count_messages_tokens(messages, model_enum)
            
            # 判断是否超过阈值
            should_summarize = token_count > threshold
            
            if should_summarize:
                logger.info(f"会话 {session_id} 的token数 {token_count} 超过阈值 {threshold}，需要总结")
            
            return should_summarize
            
        except Exception as e:
            logger.error(f"检查总结触发条件时出错: {str(e)}")
            return False
    
    def summarize_context(self, session_id: str, model_type: str, messages: List[Dict[str, Any]]) -> str:
        """
        生成上下文总结
        
        Args:
            session_id: 会话ID
            model_type: 模型类型 ('local' 或 'aliyun')
            messages: 对话消息列表
            
        Returns:
            str: 生成的总结文本
        """
        try:
            # 根据模型类型确定保留的消息数量
            if model_type == 'local':
                # 本地模型：保留最近3-5条完整消息
                recent_count = 4  # 中间值
            else:  # aliyun
                # 阿里云模型：保留最近10-20条消息
                recent_count = 15  # 中间值
            
            # 提取最近的消息
            recent_messages = messages[-recent_count:] if len(messages) >= recent_count else messages
            
            # 构建总结提示
            prompt = self._build_summary_prompt(messages, recent_messages, model_type)
            
            # 调用模型API生成总结
            # 这里需要根据实际的模型API实现
            model_client = get_model_api_client(model_type)
            summary = model_client.generate_summary(prompt)
            
            logger.info(f"生成会话 {session_id} 的上下文总结: {len(summary)} 字符")
            
            return summary
            
        except Exception as e:
            logger.error(f"生成上下文总结时出错: {str(e)}")
            # 返回一个默认的总结作为降级处理
            return f"[上下文总结失败: {str(e)}]"
    
    def _build_summary_prompt(self, all_messages: List[Dict[str, Any]], recent_messages: List[Dict[str, Any]], model_type: str) -> str:
        """
        构建用于生成总结的提示词
        """
        # 构建对话历史摘要
        conversation_summary = ""
        for msg in all_messages[:-len(recent_messages)]:  # 排除最近保留的消息
            role = msg.get('role', 'unknown')
            content = msg.get('content', '')
            conversation_summary += f"{role}: {content}\n"
        
        # 构建提示词
        if model_type == 'local':
            prompt = f"""
            你是一个智能数据分析助手的上下文总结引擎。
            请根据以下对话历史，生成一个简洁的总结，帮助保持对话的连贯性。
            
            对话历史（需要总结的部分）：
            {conversation_summary}
            
            最近保留的对话（用于保持上下文）：
            {self._format_recent_messages(recent_messages)}
            
            请生成一个不超过200字的总结，概括对话的主要主题、用户意图和关键信息。
            总结应包含：
            1. 用户的核心查询目的
            2. 已经分析过的数据主题
            3. 重要的上下文信息
            4. 用户可能的后续问题方向
            
            输出格式：纯文本，不要使用Markdown或其他格式。
            """.strip()
        else:  # aliyun
            prompt = f"""
            你是一个智能数据分析助手的上下文总结引擎。
            请根据以下对话历史，生成一个简洁的总结，帮助保持对话的连贯性。
            
            对话历史（需要总结的部分）：
            {conversation_summary}
            
            最近保留的对话（用于保持上下文）：
            {self._format_recent_messages(recent_messages)}
            
            请生成一个不超过500字的总结，概括对话的主要主题、用户意图和关键信息。
            总结应包含：
            1. 用户的核心查询目的
            2. 已经分析过的数据主题
            3. 重要的上下文信息
            4. 用户可能的后续问题方向
            
            输出格式：纯文本，不要使用Markdown或其他格式。
            """.strip()
        
        return prompt
    
    def _format_recent_messages(self, messages: List[Dict[str, Any]]) -> str:
        """
        格式化最近的消息用于提示词
        """
        formatted = ""
        for msg in messages:
            role = msg.get('role', 'unknown')
            content = msg.get('content', '')
            formatted += f"{role}: {content}\n"
        return formatted
    
    def save_summary(self, session_id: str, model_type: str, summary: str) -> None:
        """
        保存总结到数据库
        
        Args:
            session_id: 会话ID
            model_type: 模型类型
            summary: 生成的总结文本
        """
        try:
            # 更新会话的总结信息
            self.session_service.save_summary(session_id, model_type, summary)
            
            logger.info(f"已保存会话 {session_id} 的上下文总结")
            
        except Exception as e:
            logger.error(f"保存上下文总结时出错: {str(e)}")
            raise
    
    def get_summary(self, session_id: str, model_type: str) -> Optional[str]:
        """
        获取会话的总结
        
        Args:
            session_id: 会话ID
            model_type: 模型类型
            
        Returns:
            Optional[str]: 总结文本，如果没有则返回None
        """
        try:
            summary = self.session_service.get_summary(session_id, model_type)
            return summary
            
        except Exception as e:
            logger.error(f"获取上下文总结时出错: {str(e)}")
            return None
    
    def update_context_after_summary(self, session_id: str, model_type: str, summary: str, recent_messages: List[Dict[str, Any]]) -> None:
        """
        在总结后更新会话上下文
        
        Args:
            session_id: 会话ID
            model_type: 模型类型
            summary: 生成的总结文本
            recent_messages: 保留的最近消息列表
        """
        try:
            # 构建新的对话历史：总结 + 最近的消息
            new_conversation = [
                {"role": "system", "content": f"[上下文总结] {summary}"},
                *recent_messages
            ]
            
            # 更新会话的对话历史
            self.session_service.update_conversation(session_id, new_conversation)
            
            # 记录总结事件
            self.session_service.log_summary_event(session_id, model_type, len(summary))
            
            logger.info(f"会话 {session_id} 的上下文已成功更新，包含总结和{len(recent_messages)}条最近消息")
            
        except Exception as e:
            logger.error(f"更新上下文时出错: {str(e)}")
            raise