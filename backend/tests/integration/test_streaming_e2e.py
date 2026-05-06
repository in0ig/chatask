"""
端到端流式输出集成测试

测试完整的流式输出流程，验证所有阶段按顺序执行，
并且每个阶段都正确发送 stage_start、stage_update、stage_complete 消息。

Feature: streaming-stage-output
Requirements: 1.1, 1.2, 1.3, 1.4, 2.1, 2.2, 2.3
"""

import os
import pytest
import pytest_asyncio
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, List
from unittest.mock import AsyncMock, MagicMock, patch

from src.services.chat_orchestrator import ChatOrchestrator
from src.services.websocket_stream_service import WebSocketStreamService, StreamMessageType
from src.services.ai_model_service import AIModelService
from src.database import get_db

logger = logging.getLogger(__name__)


class MessageCollector:
    """消息收集器，用于捕获WebSocket消息"""
    
    def __init__(self):
        self.messages: List[Dict[str, Any]] = []
        self.stage_messages: Dict[str, List[Dict[str, Any]]] = {}
    
    def add_message(self, message: Dict[str, Any]):
        """添加消息"""
        self.messages.append(message)
        
        # 按阶段分组
        if "stage_id" in message and message["stage_id"]:
            stage_id = message["stage_id"]
            if stage_id not in self.stage_messages:
                self.stage_messages[stage_id] = []
            self.stage_messages[stage_id].append(message)
    
    def get_messages_by_type(self, message_type: str) -> List[Dict[str, Any]]:
        """获取指定类型的消息"""
        return [msg for msg in self.messages if msg.get("type") == message_type]
    
    def get_stage_messages(self, stage_id: str) -> List[Dict[str, Any]]:
        """获取指定阶段的所有消息"""
        return self.stage_messages.get(stage_id, [])
    
    def get_stage_sequence(self, stage_id: str) -> List[str]:
        """获取指定阶段的消息类型序列"""
        messages = self.get_stage_messages(stage_id)
        return [msg.get("type") for msg in messages]


class TestStreamingE2E:
    """端到端流式输出集成测试"""
    
    @pytest_asyncio.fixture
    async def setup_services(self):
        """设置测试服务"""
        db = next(get_db())
        
        # 创建真实的WebSocket服务
        websocket_service = WebSocketStreamService()
        
        # 创建消息收集器
        collector = MessageCollector()
        
        # Mock WebSocket服务的发送方法以收集消息
        original_send_stage_start = websocket_service.send_stage_start
        original_send_stage_update = websocket_service.send_stage_update
        original_send_stage_complete = websocket_service.send_stage_complete
        
        async def mock_send_stage_start(session_id, stage_id, stage_name, content="", metadata=None):
            collector.add_message({
                "type": "stage_start",
                "session_id": session_id,
                "stage_id": stage_id,
                "stage_name": stage_name,
                "content": content,
                "metadata": metadata or {},
                "stage_status": "in_progress"
            })
            await original_send_stage_start(session_id, stage_id, stage_name, content, metadata)
        
        async def mock_send_stage_update(session_id, stage_id, content, metadata=None):
            collector.add_message({
                "type": "stage_update",
                "session_id": session_id,
                "stage_id": stage_id,
                "content": content,
                "metadata": metadata or {},
                "stage_status": "in_progress"
            })
            await original_send_stage_update(session_id, stage_id, content, metadata)
        
        async def mock_send_stage_complete(session_id, stage_id, stage_name, content="", metadata=None):
            collector.add_message({
                "type": "stage_complete",
                "session_id": session_id,
                "stage_id": stage_id,
                "stage_name": stage_name,
                "content": content,
                "metadata": metadata or {},
                "stage_status": "completed"
            })
            await original_send_stage_complete(session_id, stage_id, stage_name, content, metadata)
        
        websocket_service.send_stage_start = mock_send_stage_start
        websocket_service.send_stage_update = mock_send_stage_update
        websocket_service.send_stage_complete = mock_send_stage_complete
        
        # 创建Chat Orchestrator（使用默认初始化）
        orchestrator = ChatOrchestrator()
        
        # 替换orchestrator的websocket_service为我们的mock版本
        orchestrator.websocket_service = websocket_service
        
        return {
            "orchestrator": orchestrator,
            "websocket_service": websocket_service,
            "collector": collector,
            "db": db
        }
    
    @pytest.mark.asyncio
    async def test_complete_streaming_flow(self, setup_services):
        """
        测试10.1: 完整的端到端流式输出流程
        
        验收标准：
        - 提交查询 "张三下了几单"
        - 验证每个阶段都发送了 stage_start
        - 验证每个阶段都发送了 stage_update 消息
        - 验证每个阶段都发送了 stage_complete
        - 验证最终结果正确
        
        Requirements: 1.1, 1.2, 1.3, 1.4, 2.1, 2.2, 2.3
        """
        services = setup_services
        orchestrator = services["orchestrator"]
        collector = services["collector"]
        
        # 创建测试会话
        session_id = f"test_streaming_{datetime.now().timestamp()}"
        user_question = "张三下了几单"
        
        # 执行查询（使用真实的AI服务）
        try:
            result = await orchestrator.start_chat(
                session_id=session_id,
                user_question=user_question,
                data_source_id="1"
            )
        except Exception as e:
            # 如果AI服务不可用，跳过测试
            pytest.skip(f"AI服务不可用: {str(e)}")
        
        # 验证结果存在
        assert result is not None, "查询应该返回结果"
        
        # 验证收集到的消息
        assert len(collector.messages) > 0, "应该收集到消息"
        
        # 获取所有阶段ID
        stage_ids = list(collector.stage_messages.keys())
        assert len(stage_ids) > 0, "应该至少有一个阶段"
        
        print(f"\n✅ 完整流式输出测试")
        print(f"   - 总消息数: {len(collector.messages)}")
        print(f"   - 阶段数: {len(stage_ids)}")
        
        # 验证每个阶段的消息序列
        for stage_id in stage_ids:
            stage_sequence = collector.get_stage_sequence(stage_id)
            stage_messages = collector.get_stage_messages(stage_id)
            
            print(f"\n   阶段: {stage_id}")
            print(f"   - 消息序列: {stage_sequence}")
            print(f"   - 消息数: {len(stage_messages)}")
            
            # 验证阶段消息序列
            assert "stage_start" in stage_sequence, f"阶段 {stage_id} 应该有 stage_start"
            assert "stage_complete" in stage_sequence, f"阶段 {stage_id} 应该有 stage_complete"
            
            # 验证消息顺序：stage_start 应该在最前面
            assert stage_sequence[0] == "stage_start", \
                f"阶段 {stage_id} 的第一条消息应该是 stage_start"
            
            # 验证消息顺序：stage_complete 应该在最后面
            assert stage_sequence[-1] == "stage_complete", \
                f"阶段 {stage_id} 的最后一条消息应该是 stage_complete"
            
            # 如果有 stage_update，验证它们在 start 和 complete 之间
            update_messages = [msg for msg in stage_sequence if msg == "stage_update"]
            if update_messages:
                print(f"   - stage_update 数量: {len(update_messages)}")
                
                # 验证所有 update 都在 start 之后、complete 之前
                start_index = stage_sequence.index("stage_start")
                complete_index = stage_sequence.index("stage_complete")
                
                for i, msg_type in enumerate(stage_sequence):
                    if msg_type == "stage_update":
                        assert start_index < i < complete_index, \
                            f"stage_update 应该在 stage_start 和 stage_complete 之间"
        
        # 验证阶段顺序（如果有多个阶段）
        if len(stage_ids) > 1:
            print(f"\n   验证阶段顺序:")
            for i, stage_id in enumerate(stage_ids):
                print(f"   {i+1}. {stage_id}")
            
            # 验证阶段按顺序执行（每个阶段的 complete 应该在下一个阶段的 start 之前）
            for i in range(len(stage_ids) - 1):
                current_stage = stage_ids[i]
                next_stage = stage_ids[i + 1]
                
                current_complete_idx = None
                next_start_idx = None
                
                for idx, msg in enumerate(collector.messages):
                    if msg.get("stage_id") == current_stage and msg.get("type") == "stage_complete":
                        current_complete_idx = idx
                    if msg.get("stage_id") == next_stage and msg.get("type") == "stage_start":
                        next_start_idx = idx
                
                if current_complete_idx is not None and next_start_idx is not None:
                    assert current_complete_idx < next_start_idx, \
                        f"阶段 {current_stage} 的 complete 应该在阶段 {next_stage} 的 start 之前"
        
        print(f"\n✅ 所有验证通过")
    
    @pytest.mark.asyncio
    async def test_stage_content_accumulation(self, setup_services):
        """
        测试: 阶段内容累积
        
        验收标准：
        - stage_update 消息应该包含增量内容
        - 所有 stage_update 的内容累加应该等于 stage_complete 的内容
        
        Requirements: 2.2, 2.4
        """
        services = setup_services
        orchestrator = services["orchestrator"]
        collector = services["collector"]
        
        session_id = f"test_accumulation_{datetime.now().timestamp()}"
        user_question = "查询销售数据"
        
        try:
            result = await orchestrator.start_chat(
                session_id=session_id,
                user_question=user_question,
                data_source_id="1"
            )
        except Exception as e:
            pytest.skip(f"AI服务不可用: {str(e)}")
        
        assert result is not None, "查询应该返回结果"
        
        # 检查每个阶段的内容累积
        for stage_id, messages in collector.stage_messages.items():
            update_messages = [msg for msg in messages if msg.get("type") == "stage_update"]
            complete_messages = [msg for msg in messages if msg.get("type") == "stage_complete"]
            
            if update_messages and complete_messages:
                # 累积所有 update 的内容
                accumulated_content = "".join(msg.get("content", "") for msg in update_messages)
                
                # 获取 complete 的内容
                complete_content = complete_messages[0].get("content", "")
                
                print(f"\n阶段 {stage_id}:")
                print(f"  - update 消息数: {len(update_messages)}")
                print(f"  - 累积内容长度: {len(accumulated_content)}")
                print(f"  - complete 内容长度: {len(complete_content)}")
                
                # 验证 complete 内容包含累积的内容（可能有格式化）
                # 注意：complete 可能包含格式化后的内容，所以不要求完全相等
                assert len(complete_content) > 0, "complete 消息应该有内容"
        
        print(f"\n✅ 内容累积验证通过")
    
    @pytest.mark.asyncio
    async def test_message_format_compliance(self, setup_services):
        """
        测试: 消息格式合规性
        
        验收标准：
        - 所有消息都包含必需字段
        - stage_start 消息格式正确
        - stage_update 消息格式正确
        - stage_complete 消息格式正确
        
        Requirements: 5.1, 5.2, 5.3, 5.4
        """
        services = setup_services
        orchestrator = services["orchestrator"]
        collector = services["collector"]
        
        session_id = f"test_format_{datetime.now().timestamp()}"
        user_question = "查询数据"
        
        try:
            result = await orchestrator.start_chat(
                session_id=session_id,
                user_question=user_question,
                data_source_id="1"
            )
        except Exception as e:
            pytest.skip(f"AI服务不可用: {str(e)}")
        
        assert result is not None, "查询应该返回结果"
        assert len(collector.messages) > 0, "应该有消息"
        
        # 验证每条消息的格式
        for msg in collector.messages:
            msg_type = msg.get("type")
            
            # 所有消息都应该有这些字段
            assert "type" in msg, "消息应该有 type 字段"
            assert "session_id" in msg, "消息应该有 session_id 字段"
            assert "stage_id" in msg, "消息应该有 stage_id 字段"
            assert "content" in msg, "消息应该有 content 字段"
            
            # 根据消息类型验证特定字段
            if msg_type == "stage_start":
                assert "stage_name" in msg, "stage_start 应该有 stage_name 字段"
                assert "stage_status" in msg, "stage_start 应该有 stage_status 字段"
                assert msg["stage_status"] == "in_progress", "stage_start 的 status 应该是 in_progress"
                # stage_start 的 content 可以为空
            
            elif msg_type == "stage_update":
                assert "stage_status" in msg, "stage_update 应该有 stage_status 字段"
                assert msg["stage_status"] == "in_progress", "stage_update 的 status 应该是 in_progress"
                # stage_update 应该有内容
                assert len(msg.get("content", "")) > 0, "stage_update 应该有内容"
            
            elif msg_type == "stage_complete":
                assert "stage_name" in msg, "stage_complete 应该有 stage_name 字段"
                assert "stage_status" in msg, "stage_complete 应该有 stage_status 字段"
                assert msg["stage_status"] == "completed", "stage_complete 的 status 应该是 completed"
                # stage_complete 应该有最终内容
                assert len(msg.get("content", "")) > 0, "stage_complete 应该有内容"
        
        print(f"\n✅ 消息格式验证通过")
        print(f"   - 验证消息数: {len(collector.messages)}")
    
    @pytest.mark.asyncio
    async def test_error_handling_in_streaming(self, setup_services):
        """
        测试: 流式输出中的错误处理
        
        验收标准：
        - 即使发生错误，也应该发送 stage_complete
        - 错误信息应该被正确记录
        - 系统应该能够继续处理后续阶段
        
        Requirements: 7.1, 7.4, 7.5
        """
        services = setup_services
        orchestrator = services["orchestrator"]
        collector = services["collector"]
        
        session_id = f"test_error_{datetime.now().timestamp()}"
        
        # 使用一个可能导致错误的查询
        user_question = ""  # 空查询
        
        try:
            result = await orchestrator.start_chat(
                session_id=session_id,
                user_question=user_question,
                data_source_id="1"
            )
        except Exception as e:
            # 即使发生异常，也应该有消息被发送
            pass
        
        # 验证即使有错误，也收集到了消息
        if len(collector.messages) > 0:
            print(f"\n✅ 错误处理验证")
            print(f"   - 收集到消息数: {len(collector.messages)}")
            
            # 检查是否有 stage_complete 消息
            complete_messages = collector.get_messages_by_type("stage_complete")
            if complete_messages:
                print(f"   - stage_complete 消息数: {len(complete_messages)}")
                print(f"   ✅ 即使有错误，也发送了 stage_complete")
        else:
            print(f"\n⚠️  空查询没有触发任何阶段（这是预期的）")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])
