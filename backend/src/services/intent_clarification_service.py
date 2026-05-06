"""
意图澄清服务

基于云端Qwen模型实现智能的意图澄清问题生成，支持多轮对话流程管理。
包含澄清结果处理、意图更新、历史记录和效果评估功能。
"""

from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
import json
import logging

logger = logging.getLogger(__name__)


class ClarificationStatus(Enum):
    """澄清状态枚举"""
    PENDING = "pending"  # 等待用户响应
    CONFIRMED = "confirmed"  # 用户确认
    MODIFIED = "modified"  # 用户修改
    REJECTED = "rejected"  # 用户拒绝
    COMPLETED = "completed"  # 澄清完成


class IntentUpdateType(Enum):
    """意图更新类型枚举"""
    TABLE_SELECTION = "table_selection"  # 表选择更新
    TIME_RANGE = "time_range"  # 时间范围更新
    AGGREGATION = "aggregation"  # 聚合方式更新
    FILTER_CONDITION = "filter_condition"  # 过滤条件更新
    FIELD_SELECTION = "field_selection"  # 字段选择更新
    CUSTOM = "custom"  # 自定义更新


@dataclass
class ClarificationQuestion:
    """澄清问题数据类"""
    question: str
    options: List[str] = field(default_factory=list)
    question_type: str = "single_choice"  # single_choice, multiple_choice, text_input
    reasoning: str = ""
    importance: float = 0.5  # 0.0-1.0


@dataclass
class ClarificationResult:
    """澄清结果数据类"""
    clarification_needed: bool
    questions: List[ClarificationQuestion]
    summary: str
    confidence: float
    reasoning: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class IntentUpdate:
    """意图更新数据类"""
    update_type: IntentUpdateType
    original_value: Any
    updated_value: Any
    reasoning: str
    confidence: float
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class ClarificationFeedback:
    """澄清反馈数据类"""
    question_id: int
    user_response: Any
    response_type: str  # single_choice, multiple_choice, text_input
    confidence: float
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class ClarificationHistory:
    """澄清历史记录数据类"""
    session_id: str
    round_number: int
    clarification_result: ClarificationResult
    user_feedbacks: List[ClarificationFeedback]
    intent_updates: List[IntentUpdate]
    effectiveness_score: float  # 0.0-1.0
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class ClarificationSession:
    """澄清会话数据类"""
    session_id: str
    original_question: str
    table_selection: Dict[str, Any]
    clarification_result: Optional[ClarificationResult] = None
    user_responses: List[Dict[str, Any]] = field(default_factory=list)
    status: ClarificationStatus = ClarificationStatus.PENDING
    intent_updates: List[IntentUpdate] = field(default_factory=list)
    clarification_history: List[ClarificationHistory] = field(default_factory=list)
    current_round: int = 1
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


class IntentClarificationService:
    """意图澄清服务"""
    
    def __init__(self, ai_model_service=None, prompt_manager=None):
        """
        初始化意图澄清服务
        
        Args:
            ai_model_service: AI模型服务实例
            prompt_manager: Prompt管理器实例
        """
        self.ai_model_service = ai_model_service
        self.prompt_manager = prompt_manager
        
        # 会话管理
        self.sessions: Dict[str, ClarificationSession] = {}
        
        # 统计信息
        self.stats = {
            "total_clarifications": 0,
            "clarification_needed_count": 0,
            "user_confirmed_count": 0,
            "user_modified_count": 0,
            "user_rejected_count": 0,
            "avg_questions_per_clarification": 0.0,
            "avg_response_time_ms": 0.0,
            "total_intent_updates": 0,
            "avg_effectiveness_score": 0.0,
            "multi_round_clarifications": 0
        }
        
        logger.info("IntentClarificationService initialized")
    
    async def generate_clarification(
        self,
        original_question: str,
        table_selection: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> ClarificationResult:
        """
        生成意图澄清问题
        
        Args:
            original_question: 用户原始问题
            table_selection: 智能选表结果
            context: 额外上下文信息
            
        Returns:
            ClarificationResult: 澄清结果
        """
        start_time = datetime.now()
        
        try:
            # 构建澄清prompt
            prompt = self._build_clarification_prompt(
                original_question,
                table_selection,
                context or {}
            )
            
            # 调用AI模型生成澄清问题
            if self.ai_model_service:
                response = await self.ai_model_service.generate(
                    prompt=prompt,
                    model_type="qwen",
                    temperature=0.7,
                    max_tokens=1000
                )
                
                # 解析AI响应
                clarification_result = self._parse_clarification_response(response)
            else:
                # 降级策略：使用规则生成澄清问题
                clarification_result = self._generate_rule_based_clarification(
                    original_question,
                    table_selection
                )
            
            # 更新统计信息
            self._update_stats(clarification_result, start_time)
            
            logger.info(
                f"Generated clarification for question: {original_question[:50]}... "
                f"Needed: {clarification_result.clarification_needed}, "
                f"Questions: {len(clarification_result.questions)}"
            )
            
            return clarification_result
            
        except Exception as e:
            logger.error(f"Error generating clarification: {str(e)}")
            # 返回默认结果
            return ClarificationResult(
                clarification_needed=False,
                questions=[],
                summary=f"理解您的问题：{original_question}",
                confidence=0.5,
                reasoning="生成澄清问题时出错，跳过澄清步骤"
            )
    
    def _build_clarification_prompt(
        self,
        original_question: str,
        table_selection: Dict[str, Any],
        context: Dict[str, Any]
    ) -> str:
        """构建澄清问题生成的prompt"""
        
        # 格式化选中的表信息
        selected_tables_info = self._format_selected_tables(table_selection)
        
        # 使用prompt管理器获取模板
        if self.prompt_manager:
            return self.prompt_manager.get_prompt(
                "intent_clarification",
                {
                    "user_message": original_question,
                    "selected_tables": selected_tables_info,
                    "context": json.dumps(context, ensure_ascii=False, indent=2)
                }
            )
        
        # 默认prompt模板
        return f"""
基于用户问题和选择的数据表，生成意图澄清问题：

用户原始问题：{original_question}

选择的数据表：
{selected_tables_info}

额外上下文：
{json.dumps(context, ensure_ascii=False, indent=2)}

请分析可能的歧义点和需要确认的细节，生成澄清问题。

请以JSON格式返回：
{{
  "clarification_needed": true/false,
  "questions": [
    {{
      "question": "澄清问题",
      "options": ["选项1", "选项2", "选项3"],
      "question_type": "single_choice" | "multiple_choice" | "text_input",
      "reasoning": "为什么需要这个澄清",
      "importance": 0.0-1.0
    }}
  ],
  "summary": "理解总结：我理解您想要...",
  "confidence": 0.0-1.0,
  "reasoning": "整体分析理由"
}}
"""
    
    def _format_selected_tables(self, table_selection: Dict[str, Any]) -> str:
        """格式化选中的表信息"""
        if not table_selection or "selected_tables" not in table_selection:
            return "无选中的表"
        
        tables = table_selection["selected_tables"]
        formatted = []
        
        for table in tables:
            table_info = f"- {table.get('table_name', 'Unknown')}"
            if "relevant_fields" in table:
                fields = ", ".join(table["relevant_fields"])
                table_info += f" (相关字段: {fields})"
            if "reasoning" in table:
                table_info += f"\n  理由: {table['reasoning']}"
            formatted.append(table_info)
        
        return "\n".join(formatted)
    
    def _parse_clarification_response(self, response: str) -> ClarificationResult:
        """解析AI模型的澄清响应"""
        try:
            # 尝试提取JSON
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
            else:
                data = json.loads(response)
            
            # 解析问题列表
            questions = []
            for q_data in data.get("questions", []):
                questions.append(ClarificationQuestion(
                    question=q_data.get("question", ""),
                    options=q_data.get("options", []),
                    question_type=q_data.get("question_type", "single_choice"),
                    reasoning=q_data.get("reasoning", ""),
                    importance=q_data.get("importance", 0.5)
                ))
            
            return ClarificationResult(
                clarification_needed=data.get("clarification_needed", False),
                questions=questions,
                summary=data.get("summary", ""),
                confidence=data.get("confidence", 0.5),
                reasoning=data.get("reasoning", "")
            )
            
        except Exception as e:
            logger.error(f"Error parsing clarification response: {str(e)}")
            # 返回默认结果
            return ClarificationResult(
                clarification_needed=False,
                questions=[],
                summary="无法解析澄清结果",
                confidence=0.0,
                reasoning=f"解析错误: {str(e)}"
            )
    
    def _generate_rule_based_clarification(
        self,
        original_question: str,
        table_selection: Dict[str, Any]
    ) -> ClarificationResult:
        """基于规则生成澄清问题（降级策略）"""
        
        questions = []
        
        # 检查是否有多个候选表
        selected_tables = table_selection.get("selected_tables", [])
        if len(selected_tables) > 1:
            table_names = [t.get("table_name", "") for t in selected_tables]
            questions.append(ClarificationQuestion(
                question=f"您想查询哪些表的数据？",
                options=table_names,
                question_type="multiple_choice",
                reasoning="检测到多个相关表",
                importance=0.8
            ))
        
        # 检查时间范围
        if any(keyword in original_question.lower() for keyword in ["最近", "今天", "本月", "本年"]):
            questions.append(ClarificationQuestion(
                question="请确认时间范围",
                options=["今天", "本周", "本月", "本年", "自定义"],
                question_type="single_choice",
                reasoning="问题中包含时间相关词汇",
                importance=0.7
            ))
        
        # 检查聚合类型
        if any(keyword in original_question for keyword in ["总", "平均", "最大", "最小"]):
            questions.append(ClarificationQuestion(
                question="请确认统计方式",
                options=["求和", "平均值", "最大值", "最小值", "计数"],
                question_type="single_choice",
                reasoning="问题中包含聚合统计词汇",
                importance=0.6
            ))
        
        clarification_needed = len(questions) > 0
        
        return ClarificationResult(
            clarification_needed=clarification_needed,
            questions=questions,
            summary=f"理解您的问题：{original_question}",
            confidence=0.6,
            reasoning="基于规则生成的澄清问题"
        )
    
    def create_session(
        self,
        session_id: str,
        original_question: str,
        table_selection: Dict[str, Any],
        clarification_result: ClarificationResult
    ) -> ClarificationSession:
        """
        创建澄清会话
        
        Args:
            session_id: 会话ID
            original_question: 原始问题
            table_selection: 表选择结果
            clarification_result: 澄清结果
            
        Returns:
            ClarificationSession: 澄清会话
        """
        session = ClarificationSession(
            session_id=session_id,
            original_question=original_question,
            table_selection=table_selection,
            clarification_result=clarification_result
        )
        
        self.sessions[session_id] = session
        logger.info(f"Created clarification session: {session_id}")
        
        return session
    
    def process_clarification_feedback(
        self,
        session_id: str,
        user_feedbacks: List[Dict[str, Any]]
    ) -> Tuple[List[ClarificationFeedback], List[IntentUpdate]]:
        """
        处理用户澄清反馈，生成结构化反馈和意图更新
        
        Args:
            session_id: 会话ID
            user_feedbacks: 用户反馈列表
            
        Returns:
            Tuple[List[ClarificationFeedback], List[IntentUpdate]]: 反馈列表和意图更新列表
        """
        session = self.sessions.get(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")
        
        feedbacks = []
        intent_updates = []
        
        # 处理每个用户反馈
        for idx, feedback_data in enumerate(user_feedbacks):
            # 创建结构化反馈
            feedback = ClarificationFeedback(
                question_id=idx,
                user_response=feedback_data.get("response"),
                response_type=feedback_data.get("type", "single_choice"),
                confidence=feedback_data.get("confidence", 1.0)
            )
            feedbacks.append(feedback)
            
            # 根据反馈生成意图更新
            updates = self._generate_intent_updates_from_feedback(
                session,
                feedback,
                idx
            )
            intent_updates.extend(updates)
        
        logger.info(
            f"Processed {len(feedbacks)} feedbacks, "
            f"generated {len(intent_updates)} intent updates for session: {session_id}"
        )
        
        return feedbacks, intent_updates
    
    def _generate_intent_updates_from_feedback(
        self,
        session: ClarificationSession,
        feedback: ClarificationFeedback,
        question_idx: int
    ) -> List[IntentUpdate]:
        """根据用户反馈生成意图更新"""
        updates = []
        
        if not session.clarification_result or question_idx >= len(session.clarification_result.questions):
            return updates
        
        question = session.clarification_result.questions[question_idx]
        
        # 根据问题类型推断更新类型
        update_type = self._infer_update_type(question.question, feedback.user_response)
        
        # 获取原始值
        original_value = self._extract_original_value(session, update_type)
        
        # 创建意图更新
        update = IntentUpdate(
            update_type=update_type,
            original_value=original_value,
            updated_value=feedback.user_response,
            reasoning=f"基于用户对问题 '{question.question}' 的回答",
            confidence=feedback.confidence
        )
        updates.append(update)
        
        return updates
    
    def _infer_update_type(self, question: str, response: Any) -> IntentUpdateType:
        """推断意图更新类型"""
        question_lower = question.lower()
        
        if "表" in question or "table" in question_lower:
            return IntentUpdateType.TABLE_SELECTION
        elif "时间" in question or "日期" in question or "time" in question_lower:
            return IntentUpdateType.TIME_RANGE
        elif "统计" in question or "聚合" in question or "aggregat" in question_lower:
            return IntentUpdateType.AGGREGATION
        elif "条件" in question or "筛选" in question or "filter" in question_lower:
            return IntentUpdateType.FILTER_CONDITION
        elif "字段" in question or "列" in question or "field" in question_lower:
            return IntentUpdateType.FIELD_SELECTION
        else:
            return IntentUpdateType.CUSTOM
    
    def _extract_original_value(
        self,
        session: ClarificationSession,
        update_type: IntentUpdateType
    ) -> Any:
        """提取原始值"""
        if update_type == IntentUpdateType.TABLE_SELECTION:
            return session.table_selection.get("selected_tables", [])
        elif update_type == IntentUpdateType.TIME_RANGE:
            return session.table_selection.get("time_range")
        elif update_type == IntentUpdateType.AGGREGATION:
            return session.table_selection.get("aggregation_type")
        elif update_type == IntentUpdateType.FILTER_CONDITION:
            return session.table_selection.get("filters", [])
        elif update_type == IntentUpdateType.FIELD_SELECTION:
            return session.table_selection.get("selected_fields", [])
        else:
            return None
    
    def update_intent(
        self,
        session_id: str,
        intent_updates: List[IntentUpdate]
    ) -> Dict[str, Any]:
        """
        更新意图
        
        Args:
            session_id: 会话ID
            intent_updates: 意图更新列表
            
        Returns:
            Dict: 更新后的意图
        """
        session = self.sessions.get(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")
        
        # 应用意图更新
        updated_intent = self._apply_intent_updates(session, intent_updates)
        
        # 保存更新到会话
        session.intent_updates.extend(intent_updates)
        session.updated_at = datetime.now()
        
        # 更新统计
        self.stats["total_intent_updates"] += len(intent_updates)
        
        logger.info(
            f"Applied {len(intent_updates)} intent updates for session: {session_id}"
        )
        
        return updated_intent
    
    def _apply_intent_updates(
        self,
        session: ClarificationSession,
        intent_updates: List[IntentUpdate]
    ) -> Dict[str, Any]:
        """应用意图更新到表选择结果"""
        updated_intent = session.table_selection.copy()
        
        for update in intent_updates:
            if update.update_type == IntentUpdateType.TABLE_SELECTION:
                updated_intent["selected_tables"] = update.updated_value
            elif update.update_type == IntentUpdateType.TIME_RANGE:
                updated_intent["time_range"] = update.updated_value
            elif update.update_type == IntentUpdateType.AGGREGATION:
                updated_intent["aggregation_type"] = update.updated_value
            elif update.update_type == IntentUpdateType.FILTER_CONDITION:
                updated_intent["filters"] = update.updated_value
            elif update.update_type == IntentUpdateType.FIELD_SELECTION:
                updated_intent["selected_fields"] = update.updated_value
            elif update.update_type == IntentUpdateType.CUSTOM:
                # 自定义更新，存储在metadata中
                if "custom_updates" not in updated_intent:
                    updated_intent["custom_updates"] = []
                updated_intent["custom_updates"].append({
                    "value": update.updated_value,
                    "reasoning": update.reasoning
                })
        
        return updated_intent
    
    def confirm_clarification(
        self,
        session_id: str,
        user_responses: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        确认澄清结果
        
        Args:
            session_id: 会话ID
            user_responses: 用户响应列表
            
        Returns:
            Dict: 确认结果，包含意图更新
        """
        session = self.sessions.get(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")
        
        # 处理反馈并生成意图更新
        feedbacks, intent_updates = self.process_clarification_feedback(
            session_id,
            user_responses
        )
        
        # 更新意图
        updated_intent = self.update_intent(session_id, intent_updates)
        
        # 记录澄清历史
        effectiveness_score = self._evaluate_clarification_effectiveness(
            session,
            feedbacks,
            intent_updates
        )
        
        history = ClarificationHistory(
            session_id=session_id,
            round_number=session.current_round,
            clarification_result=session.clarification_result,
            user_feedbacks=feedbacks,
            intent_updates=intent_updates,
            effectiveness_score=effectiveness_score
        )
        session.clarification_history.append(history)
        
        # 更新会话状态
        session.user_responses = user_responses
        session.status = ClarificationStatus.CONFIRMED
        session.updated_at = datetime.now()
        
        # 更新统计
        self.stats["user_confirmed_count"] += 1
        self._update_effectiveness_stats(effectiveness_score)
        
        logger.info(
            f"Confirmed clarification for session: {session_id}, "
            f"effectiveness: {effectiveness_score:.2f}"
        )
        
        return {
            "session_id": session_id,
            "status": "confirmed",
            "responses": user_responses,
            "intent_updates": [
                {
                    "type": u.update_type.value,
                    "original_value": u.original_value,
                    "updated_value": u.updated_value,
                    "reasoning": u.reasoning,
                    "confidence": u.confidence
                }
                for u in intent_updates
            ],
            "updated_intent": updated_intent,
            "effectiveness_score": effectiveness_score
        }
    
    def modify_clarification(
        self,
        session_id: str,
        modifications: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        修改澄清内容
        
        Args:
            session_id: 会话ID
            modifications: 修改内容
            
        Returns:
            Dict: 修改结果，包含新的澄清问题
        """
        session = self.sessions.get(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")
        
        # 记录修改
        session.user_responses.append({
            "type": "modification",
            "content": modifications,
            "timestamp": datetime.now().isoformat()
        })
        session.status = ClarificationStatus.MODIFIED
        session.updated_at = datetime.now()
        session.current_round += 1
        
        # 更新统计
        self.stats["user_modified_count"] += 1
        self.stats["multi_round_clarifications"] += 1
        
        logger.info(
            f"Modified clarification for session: {session_id}, "
            f"round: {session.current_round}"
        )
        
        return {
            "session_id": session_id,
            "status": "modified",
            "modifications": modifications,
            "current_round": session.current_round,
            "message": "请重新生成澄清问题"
        }
    
    def _evaluate_clarification_effectiveness(
        self,
        session: ClarificationSession,
        feedbacks: List[ClarificationFeedback],
        intent_updates: List[IntentUpdate]
    ) -> float:
        """
        评估澄清效果
        
        Args:
            session: 澄清会话
            feedbacks: 用户反馈列表
            intent_updates: 意图更新列表
            
        Returns:
            float: 效果评分 (0.0-1.0)
        """
        if not feedbacks:
            return 0.0
        
        # 计算反馈置信度平均值
        avg_feedback_confidence = sum(f.confidence for f in feedbacks) / len(feedbacks)
        
        # 计算意图更新置信度平均值
        avg_update_confidence = (
            sum(u.confidence for u in intent_updates) / len(intent_updates)
            if intent_updates else 0.5
        )
        
        # 计算问题覆盖率（用户回答的问题数 / 总问题数）
        total_questions = len(session.clarification_result.questions) if session.clarification_result else 1
        coverage_rate = len(feedbacks) / total_questions
        
        # 综合评分
        effectiveness = (
            avg_feedback_confidence * 0.4 +
            avg_update_confidence * 0.4 +
            coverage_rate * 0.2
        )
        
        return min(1.0, max(0.0, effectiveness))
    
    def _update_effectiveness_stats(self, effectiveness_score: float):
        """更新效果统计"""
        total_confirmed = self.stats["user_confirmed_count"]
        if total_confirmed > 0:
            total_score = self.stats["avg_effectiveness_score"] * (total_confirmed - 1)
            total_score += effectiveness_score
            self.stats["avg_effectiveness_score"] = total_score / total_confirmed
    
    def get_clarification_history(
        self,
        session_id: str
    ) -> List[Dict[str, Any]]:
        """
        获取澄清历史记录
        
        Args:
            session_id: 会话ID
            
        Returns:
            List[Dict]: 澄清历史列表
        """
        session = self.sessions.get(session_id)
        if not session:
            return []
        
        history_list = []
        for history in session.clarification_history:
            history_list.append({
                "round_number": history.round_number,
                "clarification_result": {
                    "clarification_needed": history.clarification_result.clarification_needed,
                    "questions": [
                        {
                            "question": q.question,
                            "options": q.options,
                            "question_type": q.question_type,
                            "importance": q.importance
                        }
                        for q in history.clarification_result.questions
                    ],
                    "summary": history.clarification_result.summary,
                    "confidence": history.clarification_result.confidence
                },
                "user_feedbacks": [
                    {
                        "question_id": f.question_id,
                        "user_response": f.user_response,
                        "response_type": f.response_type,
                        "confidence": f.confidence,
                        "timestamp": f.timestamp.isoformat()
                    }
                    for f in history.user_feedbacks
                ],
                "intent_updates": [
                    {
                        "type": u.update_type.value,
                        "original_value": u.original_value,
                        "updated_value": u.updated_value,
                        "reasoning": u.reasoning,
                        "confidence": u.confidence,
                        "timestamp": u.timestamp.isoformat()
                    }
                    for u in history.intent_updates
                ],
                "effectiveness_score": history.effectiveness_score,
                "timestamp": history.timestamp.isoformat()
            })
        
        return history_list
    
    def rollback_to_round(
        self,
        session_id: str,
        round_number: int
    ) -> Dict[str, Any]:
        """
        回溯到指定轮次
        
        Args:
            session_id: 会话ID
            round_number: 轮次编号
            
        Returns:
            Dict: 回溯结果
        """
        session = self.sessions.get(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")
        
        if round_number < 1 or round_number > len(session.clarification_history):
            raise ValueError(
                f"Invalid round number: {round_number}, "
                f"valid range: 1-{len(session.clarification_history)}"
            )
        
        # 获取目标轮次的历史记录
        target_history = session.clarification_history[round_number - 1]
        
        # 恢复到该轮次的状态
        session.clarification_result = target_history.clarification_result
        session.current_round = round_number
        session.updated_at = datetime.now()
        
        # 清除后续轮次的历史
        session.clarification_history = session.clarification_history[:round_number]
        
        # 重新应用该轮次的意图更新
        updated_intent = self._apply_intent_updates(session, target_history.intent_updates)
        
        logger.info(
            f"Rolled back session {session_id} to round {round_number}"
        )
        
        return {
            "session_id": session_id,
            "round_number": round_number,
            "clarification_result": {
                "clarification_needed": target_history.clarification_result.clarification_needed,
                "questions": [
                    {
                        "question": q.question,
                        "options": q.options,
                        "question_type": q.question_type
                    }
                    for q in target_history.clarification_result.questions
                ],
                "summary": target_history.clarification_result.summary
            },
            "updated_intent": updated_intent,
            "message": f"已回溯到第 {round_number} 轮澄清"
        }
    
    def optimize_clarification_strategy(
        self,
        session_id: str
    ) -> Dict[str, Any]:
        """
        优化澄清策略
        
        Args:
            session_id: 会话ID
            
        Returns:
            Dict: 优化建议
        """
        session = self.sessions.get(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")
        
        if not session.clarification_history:
            return {
                "session_id": session_id,
                "recommendations": [],
                "message": "暂无历史数据，无法提供优化建议"
            }
        
        recommendations = []
        
        # 分析历史效果
        avg_effectiveness = sum(
            h.effectiveness_score for h in session.clarification_history
        ) / len(session.clarification_history)
        
        if avg_effectiveness < 0.6:
            recommendations.append({
                "type": "low_effectiveness",
                "message": "澄清效果较低，建议简化问题或提供更明确的选项",
                "priority": "high"
            })
        
        # 分析多轮澄清
        if len(session.clarification_history) > 2:
            recommendations.append({
                "type": "too_many_rounds",
                "message": "澄清轮次过多，建议在首轮提出更全面的问题",
                "priority": "medium"
            })
        
        # 分析问题类型分布
        question_types = {}
        for history in session.clarification_history:
            for question in history.clarification_result.questions:
                question_types[question.question_type] = question_types.get(question.question_type, 0) + 1
        
        if question_types.get("text_input", 0) > question_types.get("single_choice", 0):
            recommendations.append({
                "type": "too_many_open_questions",
                "message": "开放式问题过多，建议使用更多选择题以提高效率",
                "priority": "low"
            })
        
        logger.info(
            f"Generated {len(recommendations)} optimization recommendations "
            f"for session: {session_id}"
        )
        
        return {
            "session_id": session_id,
            "avg_effectiveness": avg_effectiveness,
            "total_rounds": len(session.clarification_history),
            "recommendations": recommendations
        }
    
    def get_session(self, session_id: str) -> Optional[ClarificationSession]:
        """获取澄清会话"""
        return self.sessions.get(session_id)
    
    def get_session_history(self, session_id: str) -> List[Dict[str, Any]]:
        """获取会话历史"""
        session = self.sessions.get(session_id)
        if not session:
            return []
        
        return [
            {
                "original_question": session.original_question,
                "clarification_result": {
                    "clarification_needed": session.clarification_result.clarification_needed if session.clarification_result else False,
                    "questions": [
                        {
                            "question": q.question,
                            "options": q.options,
                            "question_type": q.question_type
                        }
                        for q in (session.clarification_result.questions if session.clarification_result else [])
                    ],
                    "summary": session.clarification_result.summary if session.clarification_result else ""
                },
                "user_responses": session.user_responses,
                "status": session.status,
                "created_at": session.created_at.isoformat(),
                "updated_at": session.updated_at.isoformat()
            }
        ]
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            **self.stats,
            "active_sessions": len(self.sessions),
            "clarification_rate": (
                self.stats["clarification_needed_count"] / self.stats["total_clarifications"]
                if self.stats["total_clarifications"] > 0 else 0.0
            ),
            "confirmation_rate": (
                self.stats["user_confirmed_count"] / self.stats["clarification_needed_count"]
                if self.stats["clarification_needed_count"] > 0 else 0.0
            ),
            "modification_rate": (
                self.stats["user_modified_count"] / self.stats["clarification_needed_count"]
                if self.stats["clarification_needed_count"] > 0 else 0.0
            ),
            "multi_round_rate": (
                self.stats["multi_round_clarifications"] / self.stats["total_clarifications"]
                if self.stats["total_clarifications"] > 0 else 0.0
            )
        }
    
    def _update_stats(self, result: ClarificationResult, start_time: datetime):
        """更新统计信息"""
        self.stats["total_clarifications"] += 1
        
        if result.clarification_needed:
            self.stats["clarification_needed_count"] += 1
        
        # 更新平均问题数
        total_questions = self.stats["avg_questions_per_clarification"] * (self.stats["total_clarifications"] - 1)
        total_questions += len(result.questions)
        self.stats["avg_questions_per_clarification"] = total_questions / self.stats["total_clarifications"]
        
        # 更新平均响应时间
        response_time_ms = (datetime.now() - start_time).total_seconds() * 1000
        total_time = self.stats["avg_response_time_ms"] * (self.stats["total_clarifications"] - 1)
        total_time += response_time_ms
        self.stats["avg_response_time_ms"] = total_time / self.stats["total_clarifications"]
