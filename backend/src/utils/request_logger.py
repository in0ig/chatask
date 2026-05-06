"""
请求日志工具
记录所有 API 请求、AI Prompt、响应等详细信息
"""
import logging
import json
from datetime import datetime
from typing import Any, Dict, Optional
from functools import wraps
import inspect

# 配置日志格式
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(levelname)s] - %(name)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger(__name__)


class RequestLogger:
    """请求日志记录器"""
    
    @staticmethod
    def log_api_request(endpoint: str, method: str, params: Dict = None, body: Dict = None):
        """记录 API 请求"""
        logger.info("=" * 80)
        logger.info(f"📥 API 请求")
        logger.info(f"端点: {method} {endpoint}")
        if params:
            logger.info(f"参数: {json.dumps(params, ensure_ascii=False, indent=2)}")
        if body:
            logger.info(f"请求体: {json.dumps(body, ensure_ascii=False, indent=2)}")
        logger.info("=" * 80)
    
    @staticmethod
    def log_api_response(endpoint: str, status_code: int, response: Any):
        """记录 API 响应"""
        logger.info("=" * 80)
        logger.info(f"📤 API 响应")
        logger.info(f"端点: {endpoint}")
        logger.info(f"状态码: {status_code}")
        if isinstance(response, dict):
            logger.info(f"响应: {json.dumps(response, ensure_ascii=False, indent=2)}")
        else:
            logger.info(f"响应: {response}")
        logger.info("=" * 80)
    
    @staticmethod
    def log_ai_prompt(prompt_type: str, prompt_content: str, context: Dict = None):
        """记录完整的 AI Prompt"""
        logger.info("=" * 80)
        logger.info(f"🤖 AI Prompt")
        logger.info(f"类型: {prompt_type}")
        logger.info(f"上下文: {json.dumps(context, ensure_ascii=False, indent=2) if context else 'None'}")
        logger.info("-" * 80)
        logger.info("完整 Prompt:")
        logger.info(prompt_content)
        logger.info("=" * 80)
    
    @staticmethod
    def log_ai_response(response_type: str, response_content: str, metadata: Dict = None):
        """记录 AI 响应"""
        logger.info("=" * 80)
        logger.info(f"🤖 AI 响应")
        logger.info(f"类型: {response_type}")
        if metadata:
            logger.info(f"元数据: {json.dumps(metadata, ensure_ascii=False, indent=2)}")
        logger.info("-" * 80)
        logger.info("响应内容:")
        logger.info(response_content)
        logger.info("=" * 80)
    
    @staticmethod
    def log_user_action(action: str, details: Dict = None):
        """记录用户操作"""
        logger.info("=" * 80)
        logger.info(f"👤 用户操作")
        logger.info(f"操作: {action}")
        if details:
            logger.info(f"详情: {json.dumps(details, ensure_ascii=False, indent=2)}")
        logger.info("=" * 80)
    
    @staticmethod
    def log_error(error_type: str, error_message: str, stack_trace: str = None):
        """记录错误"""
        logger.error("=" * 80)
        logger.error(f"❌ 错误")
        logger.error(f"类型: {error_type}")
        logger.error(f"消息: {error_message}")
        if stack_trace:
            logger.error(f"堆栈跟踪:\n{stack_trace}")
        logger.error("=" * 80)
    
    @staticmethod
    def log_database_query(query_type: str, query: str, params: Dict = None):
        """记录数据库查询"""
        logger.info("=" * 80)
        logger.info(f"🗄️ 数据库查询")
        logger.info(f"类型: {query_type}")
        logger.info(f"查询: {query}")
        if params:
            logger.info(f"参数: {json.dumps(params, ensure_ascii=False, indent=2)}")
        logger.info("=" * 80)


def log_api_call(endpoint_name: str = None):
    """
    API 调用日志装饰器
    自动记录函数的输入和输出
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # 获取端点名称
            name = endpoint_name or func.__name__
            
            # 记录请求
            RequestLogger.log_api_request(
                endpoint=name,
                method="ASYNC",
                params=kwargs
            )
            
            try:
                # 执行函数
                result = await func(*args, **kwargs)
                
                # 记录响应
                RequestLogger.log_api_response(
                    endpoint=name,
                    status_code=200,
                    response=result
                )
                
                return result
            except Exception as e:
                # 记录错误
                RequestLogger.log_error(
                    error_type=type(e).__name__,
                    error_message=str(e),
                    stack_trace=None
                )
                raise
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # 获取端点名称
            name = endpoint_name or func.__name__
            
            # 记录请求
            RequestLogger.log_api_request(
                endpoint=name,
                method="SYNC",
                params=kwargs
            )
            
            try:
                # 执行函数
                result = func(*args, **kwargs)
                
                # 记录响应
                RequestLogger.log_api_response(
                    endpoint=name,
                    status_code=200,
                    response=result
                )
                
                return result
            except Exception as e:
                # 记录错误
                RequestLogger.log_error(
                    error_type=type(e).__name__,
                    error_message=str(e),
                    stack_trace=None
                )
                raise
        
        # 根据函数类型返回对应的包装器
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


# 创建全局日志记录器实例
request_logger = RequestLogger()
