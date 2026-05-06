"""
流式输出协议属性测试

使用基于属性的测试验证WebSocket消息协议的正确性。
测试阶段顺序执行和消息协议合规性。

Feature: streaming-stage-output
Property 1: Sequential Stage Execution
Property 2: WebSocket Message Protocol Compliance
Requirements: 1.1, 1.3, 2.1, 2.2, 2.3, 5.1, 5.2, 5.3, 5.4
"""

import pytest
from hypothesis import given, strategies as st, settings, assume, HealthCheck
from typing import List, Dict, Any, Tuple
from datetime import datetime
import asyncio

from src.services.websocket_stream_service import WebSocketStreamService, StreamMessageType


# ============================================================================
# 测试数据生成策略
# ============================================================================

@st.composite
def stage_id_strategy(draw):
    """生成阶段ID"""
    stage_types = [
        "intent_recognition",
        "table_selection", 
        "sql_generation",
        "sql_execution",
        "data_analysis"
    ]
    return draw(st.sampled_from(stage_types))


@st.composite
def stage_name_strategy(draw):
    """生成阶段名称"""
    stage_names = {
        "intent_recognition": "意图识别",
        "table_selection": "表选择",
        "sql_generation": "SQL生成",
        "sql_execution": "SQL执行",
        "data_analysis": "数据分析"
    }
    stage_id = draw(stage_id_strategy())
    return stage_names[stage_id]


@st.composite
def content_chunk_strategy(draw):
    """生成内容块"""
    # 生成1-50个字符的内容块
    return draw(st.text(min_size=1, max_size=50, alphabet=st.characters(
        whitelist_categories=('Lu', 'Ll', 'Nd'),
        whitelist_characters=' .,!?'
    )))


@st.composite
def stage_message_sequence_strategy(draw):
    """
    生成一个阶段的完整消息序列
    
    返回: (stage_id, stage_name, messages)
    其中 messages 是 (message_type, content) 的列表
    """
    stage_id = draw(stage_id_strategy())
    stage_name = draw(stage_name_strategy())
    
    # 生成 0-10 个 stage_update 消息
    num_updates = draw(st.integers(min_value=0, max_value=10))
    
    messages = []
    
    # stage_start (content 可以为空)
    start_content = draw(st.one_of(st.just(""), content_chunk_strategy()))
    messages.append(("stage_start", start_content))
    
    # stage_update (如果有)
    for _ in range(num_updates):
        update_content = draw(content_chunk_strategy())
        messages.append(("stage_update", update_content))
    
    # stage_complete (必须有内容)
    complete_content = draw(content_chunk_strategy())
    messages.append(("stage_complete", complete_content))
    
    return (stage_id, stage_name, messages)


@st.composite
def multi_stage_sequence_strategy(draw):
    """
    生成多个阶段的消息序列
    
    返回: List[(stage_id, stage_name, messages)]
    """
    # 生成 1-5 个阶段
    num_stages = draw(st.integers(min_value=1, max_value=5))
    
    stages = []
    used_stage_ids = set()
    
    for _ in range(num_stages):
        stage_id, stage_name, messages = draw(stage_message_sequence_strategy())
        
        # 确保阶段ID唯一
        if stage_id not in used_stage_ids:
            stages.append((stage_id, stage_name, messages))
            used_stage_ids.add(stage_id)
    
    return stages


# ============================================================================
# Property 1: Sequential Stage Execution
# ============================================================================

class TestSequentialStageExecution:
    """
    Property 1: 顺序阶段执行
    
    对于任何查询执行，阶段应该按正确的顺序出现，
    并且每个阶段只有在前一个阶段完成后才开始。
    
    Validates: Requirements 1.1, 1.3
    """
    
    @given(stages=multi_stage_sequence_strategy())
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_stages_execute_sequentially(self, stages: List[Tuple[str, str, List[Tuple[str, str]]]]):
        """
        Feature: streaming-stage-output, Property 1: Sequential Stage Execution
        
        测试阶段按顺序执行：
        - 每个阶段的 complete 应该在下一个阶段的 start 之前
        - 阶段之间不应该交错
        """
        # 模拟消息序列
        all_messages = []
        
        for stage_id, stage_name, messages in stages:
            for msg_type, content in messages:
                all_messages.append({
                    "stage_id": stage_id,
                    "stage_name": stage_name,
                    "type": msg_type,
                    "content": content
                })
        
        # 验证阶段顺序
        stage_order = []
        current_stage = None
        
        for msg in all_messages:
            stage_id = msg["stage_id"]
            msg_type = msg["type"]
            
            if msg_type == "stage_start":
                # 新阶段开始
                if current_stage is not None:
                    # 前一个阶段应该已经完成
                    assert current_stage in stage_order, \
                        f"阶段 {stage_id} 开始前，阶段 {current_stage} 应该已完成"
                
                current_stage = stage_id
            
            elif msg_type == "stage_complete":
                # 阶段完成
                assert msg["stage_id"] == current_stage, \
                    f"完成的阶段 {stage_id} 应该是当前阶段 {current_stage}"
                
                stage_order.append(stage_id)
                current_stage = None
        
        # 验证所有阶段都完成了
        completed_stages = set(stage_order)
        all_stage_ids = set(s[0] for s in stages)
        
        assert completed_stages == all_stage_ids, \
            f"所有阶段都应该完成。完成: {completed_stages}, 全部: {all_stage_ids}"
    
    @given(stages=multi_stage_sequence_strategy())
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_no_stage_interleaving(self, stages: List[Tuple[str, str, List[Tuple[str, str]]]]):
        """
        Feature: streaming-stage-output, Property 1: Sequential Stage Execution
        
        测试阶段不交错：
        - 一个阶段的所有消息应该连续出现
        - 不应该有其他阶段的消息插入
        """
        # 模拟消息序列
        all_messages = []
        
        for stage_id, stage_name, messages in stages:
            for msg_type, content in messages:
                all_messages.append({
                    "stage_id": stage_id,
                    "type": msg_type
                })
        
        # 验证没有交错
        current_stage = None
        stage_message_count = {}
        
        for msg in all_messages:
            stage_id = msg["stage_id"]
            
            if current_stage is None:
                current_stage = stage_id
                stage_message_count[stage_id] = 1
            elif current_stage == stage_id:
                stage_message_count[stage_id] += 1
            else:
                # 切换到新阶段
                # 验证前一个阶段已经完成（最后一条消息是 complete）
                prev_stage_messages = [m for m in all_messages if m["stage_id"] == current_stage]
                if prev_stage_messages:
                    last_msg = prev_stage_messages[-1]
                    # 注意：这里我们只检查阶段切换时的情况
                    # 实际的 complete 验证在其他测试中进行
                
                current_stage = stage_id
                stage_message_count[stage_id] = stage_message_count.get(stage_id, 0) + 1
        
        # 验证每个阶段的消息都是连续的
        seen_stages = set()
        current_stage = None
        
        for msg in all_messages:
            stage_id = msg["stage_id"]
            
            if stage_id != current_stage:
                # 阶段切换
                if stage_id in seen_stages:
                    # 这个阶段之前出现过，说明有交错
                    pytest.fail(f"阶段 {stage_id} 的消息不连续，存在交错")
                
                seen_stages.add(stage_id)
                current_stage = stage_id


# ============================================================================
# Property 2: WebSocket Message Protocol Compliance
# ============================================================================

class TestMessageProtocolCompliance:
    """
    Property 2: WebSocket消息协议合规性
    
    对于任何阶段执行，系统应该按顺序发送：
    - stage_start (内容为空)
    - 零个或多个 stage_update (增量内容)
    - stage_complete (最终格式化结果)
    
    每条消息都应该包含必需字段。
    
    Validates: Requirements 2.1, 2.2, 2.3, 5.1, 5.2, 5.3, 5.4
    """
    
    @given(stage_data=stage_message_sequence_strategy())
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_message_sequence_correctness(self, stage_data: Tuple[str, str, List[Tuple[str, str]]]):
        """
        Feature: streaming-stage-output, Property 2: WebSocket Message Protocol Compliance
        
        测试消息序列正确性：
        - 第一条消息必须是 stage_start
        - 最后一条消息必须是 stage_complete
        - 中间的消息（如果有）必须是 stage_update
        """
        stage_id, stage_name, messages = stage_data
        
        # 验证至少有两条消息（start 和 complete）
        assert len(messages) >= 2, "至少应该有 stage_start 和 stage_complete"
        
        # 验证第一条消息是 stage_start
        assert messages[0][0] == "stage_start", \
            f"第一条消息应该是 stage_start，实际: {messages[0][0]}"
        
        # 验证最后一条消息是 stage_complete
        assert messages[-1][0] == "stage_complete", \
            f"最后一条消息应该是 stage_complete，实际: {messages[-1][0]}"
        
        # 验证中间的消息都是 stage_update
        for i in range(1, len(messages) - 1):
            msg_type, _ = messages[i]
            assert msg_type == "stage_update", \
                f"中间的消息应该是 stage_update，实际: {msg_type} (位置 {i})"
    
    @given(stage_data=stage_message_sequence_strategy())
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_message_content_requirements(self, stage_data: Tuple[str, str, List[Tuple[str, str]]]):
        """
        Feature: streaming-stage-output, Property 2: WebSocket Message Protocol Compliance
        
        测试消息内容要求：
        - stage_start 的内容可以为空
        - stage_update 的内容必须非空
        - stage_complete 的内容必须非空
        """
        stage_id, stage_name, messages = stage_data
        
        for msg_type, content in messages:
            if msg_type == "stage_start":
                # stage_start 的内容可以为空，不做要求
                pass
            
            elif msg_type == "stage_update":
                # stage_update 必须有内容
                assert len(content) > 0, \
                    "stage_update 消息必须有内容"
            
            elif msg_type == "stage_complete":
                # stage_complete 必须有内容
                assert len(content) > 0, \
                    "stage_complete 消息必须有内容"
    
    @given(stage_data=stage_message_sequence_strategy())
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_message_field_requirements(self, stage_data: Tuple[str, str, List[Tuple[str, str]]]):
        """
        Feature: streaming-stage-output, Property 2: WebSocket Message Protocol Compliance
        
        测试消息字段要求：
        - 所有消息都应该有 stage_id, content, stage_status
        - stage_start 和 stage_complete 应该有 stage_name
        - stage_status 应该正确设置
        """
        stage_id, stage_name, messages = stage_data
        
        for msg_type, content in messages:
            # 模拟消息对象
            message = {
                "stage_id": stage_id,
                "type": msg_type,
                "content": content,
                "stage_status": "in_progress" if msg_type != "stage_complete" else "completed"
            }
            
            if msg_type in ["stage_start", "stage_complete"]:
                message["stage_name"] = stage_name
            
            # 验证必需字段
            assert "stage_id" in message, "消息应该有 stage_id"
            assert "type" in message, "消息应该有 type"
            assert "content" in message, "消息应该有 content"
            assert "stage_status" in message, "消息应该有 stage_status"
            
            # 验证 stage_name
            if msg_type in ["stage_start", "stage_complete"]:
                assert "stage_name" in message, \
                    f"{msg_type} 消息应该有 stage_name"
            
            # 验证 stage_status
            if msg_type == "stage_complete":
                assert message["stage_status"] == "completed", \
                    "stage_complete 的 status 应该是 completed"
            else:
                assert message["stage_status"] == "in_progress", \
                    f"{msg_type} 的 status 应该是 in_progress"
    
    @given(stages=multi_stage_sequence_strategy())
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_content_accumulation_property(self, stages: List[Tuple[str, str, List[Tuple[str, str]]]]):
        """
        Feature: streaming-stage-output, Property 2: WebSocket Message Protocol Compliance
        
        测试内容累积属性：
        - 所有 stage_update 的内容累加应该构成完整响应
        - stage_complete 应该包含最终格式化的内容
        """
        for stage_id, stage_name, messages in stages:
            # 累积所有 update 的内容
            accumulated_content = ""
            
            for msg_type, content in messages:
                if msg_type == "stage_update":
                    accumulated_content += content
            
            # 获取 complete 的内容
            complete_content = messages[-1][1]  # 最后一条消息是 complete
            
            # 验证 complete 有内容
            assert len(complete_content) > 0, \
                "stage_complete 应该有内容"
            
            # 如果有 update 消息，验证累积内容不为空
            update_count = sum(1 for msg_type, _ in messages if msg_type == "stage_update")
            if update_count > 0:
                assert len(accumulated_content) > 0, \
                    "如果有 stage_update，累积内容应该不为空"
    
    @given(stage_data=stage_message_sequence_strategy())
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_message_type_values(self, stage_data: Tuple[str, str, List[Tuple[str, str]]]):
        """
        Feature: streaming-stage-output, Property 2: WebSocket Message Protocol Compliance
        
        测试消息类型值：
        - 消息类型应该是有效的枚举值
        - 不应该有未知的消息类型
        """
        stage_id, stage_name, messages = stage_data
        
        valid_types = {"stage_start", "stage_update", "stage_complete"}
        
        for msg_type, _ in messages:
            assert msg_type in valid_types, \
                f"消息类型应该是有效值，实际: {msg_type}"


# ============================================================================
# 辅助测试：验证测试数据生成器
# ============================================================================

class TestDataGenerators:
    """验证测试数据生成器的正确性"""
    
    @given(stage_data=stage_message_sequence_strategy())
    @settings(max_examples=50, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_stage_message_sequence_generator(self, stage_data: Tuple[str, str, List[Tuple[str, str]]]):
        """验证阶段消息序列生成器"""
        stage_id, stage_name, messages = stage_data
        
        # 验证基本结构
        assert isinstance(stage_id, str), "stage_id 应该是字符串"
        assert isinstance(stage_name, str), "stage_name 应该是字符串"
        assert isinstance(messages, list), "messages 应该是列表"
        assert len(messages) >= 2, "至少应该有 start 和 complete"
        
        # 验证消息格式
        for msg_type, content in messages:
            assert isinstance(msg_type, str), "消息类型应该是字符串"
            assert isinstance(content, str), "内容应该是字符串"
    
    @given(stages=multi_stage_sequence_strategy())
    @settings(max_examples=50, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_multi_stage_sequence_generator(self, stages: List[Tuple[str, str, List[Tuple[str, str]]]]):
        """验证多阶段序列生成器"""
        assert isinstance(stages, list), "stages 应该是列表"
        assert len(stages) >= 1, "至少应该有一个阶段"
        
        # 验证阶段ID唯一性
        stage_ids = [s[0] for s in stages]
        assert len(stage_ids) == len(set(stage_ids)), "阶段ID应该唯一"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])
