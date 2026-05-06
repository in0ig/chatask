"""
Token 管理服务

负责处理本地模型和阿里云模型的 Token 计数、限制检查和使用统计。
"""

import tiktoken
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ModelType(str, Enum):
    LOCAL = "local"
    ALIBABA = "alibaba"

class Message:
    """消息对象定义"""
    def __init__(self, role: str, content: str):
        self.role = role
        self.content = content

class TokenManager:
    """
    Token 管理服务
    
    负责计算不同模型的 Token 数量、检查 Token 限制、统计 Token 使用情况
    """
    
    def __init__(self):
        # 初始化 tiktoken 编码器（使用 gpt-4 模型的编码器）
        try:
            self.encoding = tiktoken.get_encoding("cl100k_base")
        except Exception as e:
            logger.error(f"初始化 tiktoken 编码器失败: {e}")
            raise RuntimeError("无法初始化 Token 计数器")
        
        # Token 限制配置
        self.model_limits = {
            ModelType.LOCAL: {
                "hard_limit": 32000,      # 硬性限制
                "summary_threshold": 15000, # 触发总结的阈值
            },
            ModelType.ALIBABA: {
                "hard_limit": 1000000,    # 硬性限制
                "summary_threshold": 800000, # 触发总结的阈值
            }
        }
        
        # Token 使用统计（内存中，生产环境应使用数据库）
        # 格式: {session_id: {model_type: {"input": total_input, "output": total_output, "history": []}}}
        self.token_usage_stats: Dict[str, Dict[str, Any]] = {}
    
    def count_text_tokens(self, text: str, model_type: ModelType) -> int:
        """
        计算文本的 Token 数量
        
        Args:
            text (str): 要计算的文本
            model_type (ModelType): 模型类型
            
        Returns:
            int: Token 数量
        """
        if not text:
            return 0
        
        if model_type == ModelType.LOCAL:
            # 使用 tiktoken 计算本地模型 Token
            return len(self.encoding.encode(text))
        
        elif model_type == ModelType.ALIBABA:
            # 对于阿里云模型，这里应该调用阿里云 API 的 Token 计数接口
            # 由于我们没有实际的 API 实现，这里使用一个近似算法
            # 实际实现中应替换为真实的阿里云 API 调用
            # 阿里云模型通常使用与 GPT 类似的编码器，这里使用相同算法作为占位
            return len(self.encoding.encode(text))
        
        else:
            raise ValueError(f"不支持的模型类型: {model_type}")
    
    def count_messages_tokens(self, messages: List[Message], model_type: ModelType) -> int:
        """
        计算消息列表的 Token 数量
        
        Args:
            messages (List[Message]): 消息列表
            model_type (ModelType): 模型类型
            
        Returns:
            int: 总 Token 数量
        """
        if not messages:
            return 0
        
        total_tokens = 0
        
        for message in messages:
            # 每条消息的 token 数量包括 role 和 content
            # 对于 GPT 模型，每个消息大约有 4 个额外的 token 用于格式
            # 这里我们简单计算 content 的 token 数量
            content_tokens = self.count_text_tokens(message.content, model_type)
            total_tokens += content_tokens
        
        # 为消息列表添加一些额外的开销（如消息分隔符等）
        # 实际实现中可能需要根据具体模型调整
        total_tokens += len(messages) * 4  # 每条消息约 4 个额外 token
        
        return total_tokens
    
    def check_token_limit(self, session_id: str, model_type: ModelType) -> Dict[str, Any]:
        """
        检查 Token 限制
        
        Args:
            session_id (str): 会话 ID
            model_type (ModelType): 模型类型
            
        Returns:
            Dict[str, Any]: 包含检查结果的字典
        """
        if model_type not in self.model_limits:
            raise ValueError(f"不支持的模型类型: {model_type}")
        
        limits = self.model_limits[model_type]
        
        # 获取当前会话的 Token 使用情况
        session_stats = self.token_usage_stats.get(session_id, {}).get(model_type, {"input": 0, "output": 0})
        total_tokens = session_stats["input"] + session_stats["output"]
        
        result = {
            "session_id": session_id,
            "model_type": model_type,
            "total_tokens": total_tokens,
            "hard_limit": limits["hard_limit"],
            "summary_threshold": limits["summary_threshold"],
            "is_within_hard_limit": total_tokens <= limits["hard_limit"],
            "is_within_summary_threshold": total_tokens <= limits["summary_threshold"],
            "is_over_hard_limit": total_tokens > limits["hard_limit"],
            "is_over_summary_threshold": total_tokens > limits["summary_threshold"],
            "remaining_tokens": limits["hard_limit"] - total_tokens,
            "remaining_for_summary": limits["summary_threshold"] - total_tokens
        }
        
        return result
    
    def get_token_usage_stats(self, session_id: str) -> Dict[str, Any]:
        """
        获取 Token 使用统计信息
        
        Args:
            session_id (str): 会话 ID
            
        Returns:
            Dict[str, Any]: Token 使用统计信息
        """
        if session_id not in self.token_usage_stats:
            return {
                "session_id": session_id,
                "total_input_tokens": 0,
                "total_output_tokens": 0,
                "total_tokens": 0,
                "model_stats": {}
            }
        
        session_stats = self.token_usage_stats[session_id]
        
        total_input = 0
        total_output = 0
        model_stats = {}
        
        for model_type, stats in session_stats.items():
            input_tokens = stats.get("input", 0)
            output_tokens = stats.get("output", 0)
            total_input += input_tokens
            total_output += output_tokens
            
            model_stats[model_type] = {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": input_tokens + output_tokens
            }
        
        return {
            "session_id": session_id,
            "total_input_tokens": total_input,
            "total_output_tokens": total_output,
            "total_tokens": total_input + total_output,
            "model_stats": model_stats
        }
    
    def update_token_usage(self, session_id: str, model_type: ModelType, input_tokens: int, output_tokens: int) -> None:
        """
        更新 Token 使用情况
        
        Args:
            session_id (str): 会话 ID
            model_type (ModelType): 模型类型
            input_tokens (int): 输入 Token 数量
            output_tokens (int): 输出 Token 数量
            
        Returns:
            None
        """
        if session_id not in self.token_usage_stats:
            self.token_usage_stats[session_id] = {}
        
        if model_type not in self.token_usage_stats[session_id]:
            self.token_usage_stats[session_id][model_type] = {
                "input": 0,
                "output": 0,
                "history": []
            }
        
        # 更新统计信息
        self.token_usage_stats[session_id][model_type]["input"] += input_tokens
        self.token_usage_stats[session_id][model_type]["output"] += output_tokens
        
        # 记录历史（可选，用于调试）
        self.token_usage_stats[session_id][model_type]["history"].append({
            "timestamp": datetime.now().isoformat(),
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens
        })
        
        # 可选：将统计信息持久化到数据库
        # 这里只是示例，实际实现中应调用数据库服务
        logger.info(f"更新 Token 使用统计: session_id={session_id}, model_type={model_type}, "
                   f"input={input_tokens}, output={output_tokens}")
        
        # 在生产环境中，这里应该调用数据库服务来持久化数据
        # 例如：database_service.save_token_usage(session_id, model_type, input_tokens, output_tokens)
        
        # 记录总体统计
        total_input = self.token_usage_stats[session_id][model_type]["input"]
        total_output = self.token_usage_stats[session_id][model_type]["output"]
        logger.debug(f"会话 {session_id} 模型 {model_type} 总 Token 使用: 输入={total_input}, 输出={total_output}")

# 创建全局实例
# 在实际应用中，这应该通过依赖注入或单例模式管理
token_manager = TokenManager()