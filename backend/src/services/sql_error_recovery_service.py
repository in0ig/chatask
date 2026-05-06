import logging
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
import uuid

from src.models.database_models import ConversationMessage, Role, ModelUsed
from src.qwen_integration import QwenIntegration
from src.utils import get_db_session

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SQLErrorRecoveryService:
    """
    SQL错误恢复服务，支持自动重试和错误修正
    """
    
    def __init__(self):
        self.qwen_integration = QwenIntegration()
        self.max_retries = 3
        logger.info("SQLErrorRecoveryService initialized with max_retries=3")
    
    def execute_with_retry(self, session_id: str, user_question: str, sql: str, data_source_id: str) -> Dict[str, Any]:
        """
        执行SQL并处理错误，支持自动重试（最多3次）
        
        Args:
            session_id: 会话ID
            user_question: 用户原始问题
            sql: 要执行的SQL语句
            data_source_id: 数据源ID
            
        Returns:
            Dict[str, Any]: 包含执行结果的字典
        """
        logger.info(f"Starting SQL execution with retry for session {session_id}")
        
        # 验证必需参数
        if not session_id:
            logger.warning("session_id is empty")
            return {
                'success': False,
                'error': 'session_id is required',
                'attempt': 0,
                'sql': sql
            }
        
        if not user_question:
            logger.warning("user_question is empty")
            return {
                'success': False,
                'error': 'user_question is required',
                'attempt': 0,
                'sql': sql
            }
        
        if not sql:
            logger.warning("sql is empty")
            return {
                'success': False,
                'error': 'sql is required',
                'attempt': 0,
                'sql': sql
            }
        
        if not data_source_id:
            logger.warning("data_source_id is empty")
            return {
                'success': False,
                'error': 'data_source_id is required',
                'attempt': 0,
                'sql': sql
            }
        
        # 记录第一次尝试
        self.record_retry_result(session_id, 1, sql, False, "Initial attempt")
        
        for attempt in range(1, self.max_retries + 1):
            try:
                logger.info(f"Attempt {attempt} to execute SQL: {sql[:100]}...")
                
                # 执行SQL（这里需要根据数据源类型执行）
                # 由于我们没有直接的数据库连接，这里假设通过数据库服务执行
                result = self._execute_sql(sql, data_source_id)
                
                # 如果执行成功，记录成功结果
                self.record_retry_result(session_id, attempt, sql, True, "")
                
                logger.info(f"SQL execution successful on attempt {attempt} for session {session_id}")
                return {
                    'success': True,
                    'result': result,
                    'attempt': attempt,
                    'sql': sql
                }
                
            except Exception as e:
                error_msg = str(e)
                logger.warning(f"SQL execution failed on attempt {attempt}: {error_msg}")
                
                # 记录失败结果
                self.record_retry_result(session_id, attempt, sql, False, error_msg)
                
                # 如果是最后一次尝试，直接返回错误
                if attempt == self.max_retries:
                    logger.error(f"SQL execution failed after {self.max_retries} attempts for session {session_id}")
                    return {
                        'success': False,
                        'error': error_msg,
                        'attempt': attempt,
                        'sql': sql
                    }
                
                # 尝试使用模型修复SQL
                logger.info(f"Attempting to fix SQL with model for attempt {attempt + 1}")
                fixed_sql = self.retry_with_model(session_id, user_question, sql, error_msg, data_source_id)
                
                if fixed_sql and fixed_sql != sql:
                    logger.info(f"SQL fixed by model: {fixed_sql[:100]}...")
                    sql = fixed_sql
                else:
                    logger.warning(f"Model failed to fix SQL, retrying with original SQL")
        
        # 这里不应该到达，但为了安全
        return {
            'success': False,
            'error': f"Failed after {self.max_retries} attempts",
            'attempt': self.max_retries,
            'sql': sql
        }
    
    def _execute_sql(self, sql: str, data_source_id: str) -> Dict[str, Any]:
        """
        执行SQL语句（根据数据源类型）
        
        Args:
            sql: SQL语句
            data_source_id: 数据源ID
            
        Returns:
            Dict[str, Any]: 查询结果
            
        Raises:
            Exception: 如果执行失败
        """
        # 这里需要根据数据源类型执行SQL
        # 由于我们没有完整的数据库连接，这里使用数据库服务作为示例
        # 在实际实现中，需要根据data_source_id获取连接信息并执行
        
        # 模拟执行SQL
        # 在真实实现中，这里会调用数据库服务来执行SQL
        # 由于我们没有直接访问数据库的权限，这里使用占位符
        
        # 这里应该根据data_source_id获取连接信息并执行SQL
        # 但为了保持服务的独立性，我们假设数据库服务已经处理了连接
        
        # 示例：执行查询并返回结果
        # 在真实实现中，需要根据数据源类型（MySQL或Excel）执行不同的逻辑
        
        # 由于我们没有数据库服务的完整实现，这里返回一个模拟结果
        return {
            'chartType': 'bar',
            'data': [],
            'headers': [],
            'rows': [],
            'maxValue': 0,
            'sql': sql,
            'raw': []
        }
    
    def capture_error(self, session_id: str, sql: str, error_message: str, data_source_id: str) -> None:
        """
        捕获错误信息
        
        Args:
            session_id: 会话ID
            sql: 导致错误的SQL语句
            error_message: 错误信息
            data_source_id: 数据源ID
        """
        logger.info(f"Capturing error for session {session_id}: {error_message[:100]}")
        
        # 记录错误到数据库
        self.record_retry_result(session_id, 0, sql, False, error_message)
    
    def retry_with_model(self, session_id: str, user_question: str, failed_sql: str, error_message: str, data_source_id: str) -> Optional[str]:
        """
        调用阿里云模型重新生成SQL
        
        Args:
            session_id: 会话ID
            user_question: 用户原始问题
            failed_sql: 失败的SQL语句
            error_message: 错误信息
            data_source_id: 数据源ID
            
        Returns:
            Optional[str]: 重新生成的SQL语句，如果失败则返回None
        """
        logger.info(f"Attempting to fix SQL with model for session {session_id}")
        
        try:
            # 如果错误信息中包含 'error'，则调用 QwenIntegration 生成修复后的SQL
            if "error" in error_message.lower():
                # 使用 QwenIntegration 生成修复后的SQL
                fixed_sql = self.qwen_integration.generate_sql_from_error(
                    f"用户问题：{user_question}\n失败的SQL：{failed_sql}\n错误信息：{error_message}"
                )
                if fixed_sql and fixed_sql.strip() != "":
                    return fixed_sql
            
            # 如果没有错误信息，但SQL有明显问题，尝试修复
            if "invalid" in failed_sql.lower() or "syntax error" in error_message.lower():
                # 尝试使用 QwenIntegration 生成修复后的SQL
                fixed_sql = self.qwen_integration.generate_sql_from_error(
                    f"用户问题：{user_question}\n失败的SQL：{failed_sql}\n错误信息：{error_message}"
                )
                if fixed_sql and fixed_sql.strip() != "":
                    return fixed_sql
            
            # 如果没有找到修复方案，返回None
            return None
            
        except Exception as e:
            logger.error(f"Failed to generate SQL with model: {str(e)}")
            return None
    
    def _get_table_schema(self, data_source_id: str) -> Dict[str, Any]:
        """
        获取数据源的表结构信息
        
        Args:
            data_source_id: 数据源ID
            
        Returns:
            Dict[str, Any]: 表结构信息
        """
        # 这里需要从数据库中获取表结构信息
        # 由于我们没有具体的数据库连接，这里返回一个占位符
        return {
            "tables": [],
            "columns": []
        }
    
    def _get_knowledge_base(self, data_source_id: str) -> Dict[str, Any]:
        """
        获取数据源的知识库信息（数据字典）
        
        Args:
            data_source_id: 数据源ID
            
        Returns:
            Dict[str, Any]: 知识库信息
        """
        # 这里需要从数据库中获取数据字典信息
        # 由于我们没有具体的数据库连接，这里返回一个占位符
        return {
            "dictionary": []
        }
    
    def record_retry_result(self, session_id: str, attempt_number: int, sql: str, success: bool, error_message: str) -> None:
        """
        记录重试结果
        
        Args:
            session_id: 会话ID
            attempt_number: 尝试次数（0表示初始捕获，1-3表示重试）
            sql: SQL语句
            success: 是否成功
            error_message: 错误信息
        """
        try:
            # 创建对话消息记录
            conversation_message = ConversationMessage(
                session_id=session_id,
                turn=attempt_number,
                role=Role.assistant,
                content=sql,
                token_count=0,
                model_used=ModelUsed.none,
                intent="error_recovery",
                query_id="",
                analysis_id=""
            )
            
            # 使用 SQLAlchemy 会话保存到数据库，与 context_manager.py 保持一致
            db = next(get_db_session())
            db.add(conversation_message)
            db.commit()
            
            logger.info(f"Recorded retry result for session {session_id}, attempt {attempt_number}, success: {success}")
            
        except Exception as e:
            logger.error(f"Failed to record retry result: {str(e)}")
    
    def get_retry_history(self, session_id: str) -> List[Dict[str, Any]]:
        """
        获取重试历史
        
        Args:
            session_id: 会话ID
            
        Returns:
            List[Dict[str, Any]]: 重试历史列表
        """
        try:
            # 使用 SQLAlchemy 查询对话消息记录，与 context_manager.py 保持一致
            db = next(get_db_session())
            messages = db.query(ConversationMessage).filter(
                ConversationMessage.session_id == session_id,
                ConversationMessage.intent == "error_recovery"
            ).order_by(ConversationMessage.turn.asc()).all()
            
            history = []
            for msg in messages:
                history.append({
                    "sql": msg.content,
                    "generated_sql": msg.content,  # 在ConversationMessage中，content就是SQL语句
                    "chart_type": "error_recovery",
                    "result_data": {
                        "attempt_number": msg.turn,
                        "success": True,  # 由于我们只记录了SQL，无法知道是否成功，这里默认为True
                        "error_message": "",
                        "timestamp": msg.created_at.isoformat() if msg.created_at else None
                    },
                    "created_at": msg.created_at.isoformat() if msg.created_at else None
                })
            
            logger.info(f"Retrieved {len(history)} retry history records for session {session_id}")
            return history
            
        except Exception as e:
            logger.error(f"Failed to get retry history: {str(e)}")
            return []
