"""
多轮对话处理服务（简化版）

实现核心功能，不处理所有边界情况
同步实现，使用现有服务的实际方法
"""

from typing import Dict, Any, List
import logging

from src.services.token_manager import token_manager
from src.services.multi_turn_handler import multi_turn_handler
from src.services.context_summarizer import ContextSummarizer

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MultiTurnConversationProcessor:
    """
    多轮对话处理服务（简化版）
    
    实现核心功能，不处理所有边界情况
    同步实现，使用现有服务的实际方法
    """
    
    def __init__(self):
        """初始化服务"""
        self.context_summarizer = ContextSummarizer()
    
    def handle_user_input(self, user_input: str, session_id: str) -> Dict:
        """处理用户输入"""
        # 1. 识别意图
        intent = self.intent_recognition(user_input)
        
        # 2. 根据意图执行相应流程
        if intent == 'query':
            result = self.query_flow(user_input, session_id)
        elif intent == 'interpretation':
            result = self.interpretation_flow(user_input, session_id)
        elif intent == 'report':
            result = self.report_flow(user_input, session_id)
        else:
            # 默认处理为查询
            result = self.query_flow(user_input, session_id)
        
        # 3. 保存消息
        self.save_message(user_input, result, session_id)
        
        return result
    
    def intent_recognition(self, user_input: str) -> str:
        """识别意图"""
        user_input_lower = user_input.lower()
        
        # 检查是否包含报告相关关键词
        if any(keyword in user_input_lower for keyword in ['报表', '统计', '汇总', '图表']):
            return 'report'
        
        # 检查是否包含解读相关关键词
        if any(keyword in user_input_lower for keyword in ['解释', '说明', '为什么', '原因', '解读']):
            return 'interpretation'
        
        # 特别处理'分析'和'趋势'，它们可能在报告或解读中出现
        if '分析' in user_input_lower and '趋势' in user_input_lower:
            return 'interpretation'
        
        # 如果包含'分析'但不包含'趋势'，默认为查询
        if '分析' in user_input_lower:
            return 'query'
        
        # 如果包含'趋势'但不包含'分析'，默认为查询
        if '趋势' in user_input_lower:
            return 'query'
        
        # 默认为查询
        return 'query'
    
    def query_flow(self, user_input: str, session_id: str) -> Dict:
        """查询流程"""
        # 返回模拟的查询结果
        return {
            "type": "query",
            "response": f"正在分析您的查询：{user_input[:50]}...",
            "data": {},
            "chart_type": "table"
        }
    
    def interpretation_flow(self, user_input: str, session_id: str) -> Dict:
        """解读流程"""
        # 返回模拟的解读结果
        return {
            "type": "interpretation",
            "response": f"解读您的查询：{user_input[:50]}...",
            "insights": ["根据您的查询，数据呈现趋势性变化"],
            "suggestions": ["建议进一步分析时间维度"]
        }
    
    def report_flow(self, user_input: str, session_id: str) -> Dict:
        """报告流程"""
        # 返回模拟的报告结果
        return {
            "type": "report",
            "response": f"生成报告：{user_input[:50]}...",
            "summary": "数据摘要",
            "charts": ["bar", "line"],
            "tables": ["sales_data"]
        }
    
    def save_message(self, user_input: str, result: Dict, session_id: str) -> None:
        """保存消息"""
        # 保存用户消息
        multi_turn_handler.add_message(session_id, {
            "role": "user",
            "content": user_input,
            "parent_message_id": None
        })
        
        # 保存助手消息
        assistant_content = result.get("response", "")
        if "insights" in result:
            assistant_content += "\n\n洞察：" + ", ".join(result["insights"])
        if "suggestions" in result:
            assistant_content += "\n\n建议：" + ", ".join(result["suggestions"])
        if "summary" in result:
            assistant_content += "\n\n摘要：" + result["summary"]
        
        multi_turn_handler.add_message(session_id, {
            "role": "assistant",
            "content": assistant_content,
            "parent_message_id": None
        })
        
        # 检查是否需要总结上下文
        if self.context_summarizer.should_summarize(session_id, "local"):
            # 这里不实际生成总结，只触发检查
            # 在真实实现中，这里会调用 summarize_context 和 save_summary
            pass
        
        # 记录日志
        logger.info(f"Saved message for session {session_id}, intent: {result.get('type', 'query')}")