"""
意图澄清Schema定义

定义意图澄清相关的数据模型。
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


class ClarificationQuestionSchema(BaseModel):
    """澄清问题Schema"""
    question: str = Field(..., description="澄清问题内容")
    options: List[str] = Field(default_factory=list, description="选项列表")
    question_type: str = Field(default="single_choice", description="问题类型")
    reasoning: str = Field(default="", description="提问理由")
    importance: float = Field(default=0.5, ge=0.0, le=1.0, description="重要性评分")


class ClarificationResultSchema(BaseModel):
    """澄清结果Schema"""
    clarification_needed: bool = Field(..., description="是否需要澄清")
    questions: List[ClarificationQuestionSchema] = Field(default_factory=list, description="澄清问题列表")
    summary: str = Field(..., description="理解总结")
    confidence: float = Field(..., ge=0.0, le=1.0, description="置信度")
    reasoning: str = Field(..., description="分析理由")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")


class ClarificationSessionSchema(BaseModel):
    """澄清会话Schema"""
    session_id: str = Field(..., description="会话ID")
    original_question: str = Field(..., description="原始问题")
    table_selection: Dict[str, Any] = Field(..., description="表选择结果")
    clarification_result: Optional[ClarificationResultSchema] = Field(None, description="澄清结果")
    user_responses: List[Dict[str, Any]] = Field(default_factory=list, description="用户响应")
    status: str = Field(default="pending", description="会话状态")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")
    
    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "clarification_1234567890",
                "original_question": "查询销售数据",
                "table_selection": {
                    "selected_tables": [
                        {
                            "table_name": "sales",
                            "relevance_score": 0.9,
                            "reasoning": "包含销售相关字段"
                        }
                    ]
                },
                "clarification_result": {
                    "clarification_needed": True,
                    "questions": [
                        {
                            "question": "请确认时间范围",
                            "options": ["今天", "本周", "本月"],
                            "question_type": "single_choice",
                            "reasoning": "问题中未明确时间范围",
                            "importance": 0.8
                        }
                    ],
                    "summary": "理解您想查询销售数据",
                    "confidence": 0.85,
                    "reasoning": "需要确认时间范围"
                },
                "user_responses": [],
                "status": "pending",
                "created_at": "2024-01-01T00:00:00",
                "updated_at": "2024-01-01T00:00:00"
            }
        }


class UserResponseSchema(BaseModel):
    """用户响应Schema"""
    question_index: int = Field(..., description="问题索引")
    answer: Any = Field(..., description="用户答案")
    timestamp: datetime = Field(default_factory=datetime.now, description="响应时间")


class ClarificationStatisticsSchema(BaseModel):
    """澄清统计Schema"""
    total_clarifications: int = Field(default=0, description="总澄清次数")
    clarification_needed_count: int = Field(default=0, description="需要澄清次数")
    user_confirmed_count: int = Field(default=0, description="用户确认次数")
    user_modified_count: int = Field(default=0, description="用户修改次数")
    user_rejected_count: int = Field(default=0, description="用户拒绝次数")
    avg_questions_per_clarification: float = Field(default=0.0, description="平均问题数")
    avg_response_time_ms: float = Field(default=0.0, description="平均响应时间(毫秒)")
    active_sessions: int = Field(default=0, description="活跃会话数")
    clarification_rate: float = Field(default=0.0, ge=0.0, le=1.0, description="澄清率")
    confirmation_rate: float = Field(default=0.0, ge=0.0, le=1.0, description="确认率")
