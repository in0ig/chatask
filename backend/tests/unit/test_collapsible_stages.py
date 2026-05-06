"""
测试可折叠阶段功能

验证 WebSocket 消息格式支持可折叠阶段
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from src.services.websocket_stream_service import (
    WebSocketStreamService,
    StreamMessageType,
    StreamMessage
)


class TestCollapsibleStages:
    """测试可折叠阶段功能"""
    
    @pytest.fixture
    def service(self):
        """创建 WebSocket 服务实例"""
        return WebSocketStreamService()
    
    @pytest.fixture
    def mock_websocket(self):
        """创建模拟的 WebSocket 连接"""
        ws = AsyncMock()
        ws.accept = AsyncMock()
        ws.send_text = AsyncMock()
        return ws
    
    @pytest.mark.asyncio
    async def test_stream_message_has_stage_fields(self):
        """测试 StreamMessage 包含阶段相关字段"""
        message = StreamMessage(
            id="msg_1",
            session_id="session_1",
            type=StreamMessageType.STAGE_START,
            content="开始意图识别",
            stage_id="stage_1",
            stage_name="意图识别",
            stage_status="in_progress",
            collapsible=True,
            collapsed=False
        )
        
        # 验证字段存在
        assert message.stage_id == "stage_1"
        assert message.stage_name == "意图识别"
        assert message.stage_status == "in_progress"
        assert message.collapsible is True
        assert message.collapsed is False
        
        # 验证转换为字典
        message_dict = message.to_dict()
        assert message_dict["stage_id"] == "stage_1"
        assert message_dict["stage_name"] == "意图识别"
        assert message_dict["stage_status"] == "in_progress"
        assert message_dict["collapsible"] is True
        assert message_dict["collapsed"] is False
    
    @pytest.mark.asyncio
    async def test_send_stage_start(self, service, mock_websocket):
        """测试发送阶段开始消息"""
        session_id = "test_session"
        
        # 建立连接
        connection_id = await service.connect(mock_websocket, session_id)
        
        # 发送阶段开始消息
        await service.send_stage_start(
            session_id=session_id,
            stage_id="stage_1",
            stage_name="意图识别",
            content="正在识别用户意图...",
            metadata={"step": 1}
        )
        
        # 验证消息已发送
        assert mock_websocket.send_text.called
        
        # 获取发送的消息
        call_args = mock_websocket.send_text.call_args_list[-1]
        sent_message = call_args[0][0]
        
        # 验证消息内容
        import json
        message_data = json.loads(sent_message)
        assert message_data["type"] == "stage_start"
        assert message_data["stage_id"] == "stage_1"
        assert message_data["stage_name"] == "意图识别"
        assert message_data["stage_status"] == "in_progress"
        assert message_data["collapsible"] is True
        assert message_data["collapsed"] is False
        assert message_data["content"] == "正在识别用户意图..."
    
    @pytest.mark.asyncio
    async def test_send_stage_update(self, service, mock_websocket):
        """测试发送阶段更新消息"""
        session_id = "test_session"
        
        # 建立连接
        connection_id = await service.connect(mock_websocket, session_id)
        
        # 发送阶段更新消息
        await service.send_stage_update(
            session_id=session_id,
            stage_id="stage_1",
            content="已识别意图：查询销售数据",
            metadata={"intent": "query_sales"}
        )
        
        # 验证消息已发送
        assert mock_websocket.send_text.called
        
        # 获取发送的消息
        call_args = mock_websocket.send_text.call_args_list[-1]
        sent_message = call_args[0][0]
        
        # 验证消息内容
        import json
        message_data = json.loads(sent_message)
        assert message_data["type"] == "stage_update"
        assert message_data["stage_id"] == "stage_1"
        assert message_data["stage_status"] == "in_progress"
        assert message_data["content"] == "已识别意图：查询销售数据"
    
    @pytest.mark.asyncio
    async def test_send_stage_complete(self, service, mock_websocket):
        """测试发送阶段完成消息"""
        session_id = "test_session"
        
        # 建立连接
        connection_id = await service.connect(mock_websocket, session_id)
        
        # 发送阶段完成消息
        await service.send_stage_complete(
            session_id=session_id,
            stage_id="stage_1",
            stage_name="意图识别",
            content="意图识别完成",
            metadata={"duration": 1.5}
        )
        
        # 验证消息已发送
        assert mock_websocket.send_text.called
        
        # 获取发送的消息
        call_args = mock_websocket.send_text.call_args_list[-1]
        sent_message = call_args[0][0]
        
        # 验证消息内容
        import json
        message_data = json.loads(sent_message)
        assert message_data["type"] == "stage_complete"
        assert message_data["stage_id"] == "stage_1"
        assert message_data["stage_name"] == "意图识别"
        assert message_data["stage_status"] == "completed"
        assert message_data["collapsible"] is True
        assert message_data["collapsed"] is True  # 已完成的阶段默认折叠
        assert message_data["content"] == "意图识别完成"
    
    @pytest.mark.asyncio
    async def test_stage_workflow(self, service, mock_websocket):
        """测试完整的阶段工作流"""
        session_id = "test_session"
        
        # 建立连接
        connection_id = await service.connect(mock_websocket, session_id)
        
        # 1. 开始阶段
        await service.send_stage_start(
            session_id=session_id,
            stage_id="stage_sql",
            stage_name="SQL 生成",
            content="开始生成 SQL 查询..."
        )
        
        # 2. 更新阶段进度
        await service.send_stage_update(
            session_id=session_id,
            stage_id="stage_sql",
            content="正在分析表结构..."
        )
        
        await service.send_stage_update(
            session_id=session_id,
            stage_id="stage_sql",
            content="正在构建 SQL 语句..."
        )
        
        # 3. 完成阶段
        await service.send_stage_complete(
            session_id=session_id,
            stage_id="stage_sql",
            stage_name="SQL 生成",
            content="SQL 生成完成",
            metadata={"sql": "SELECT * FROM sales"}
        )
        
        # 验证所有消息都已发送
        assert mock_websocket.send_text.call_count >= 4
    
    @pytest.mark.asyncio
    async def test_multiple_stages(self, service, mock_websocket):
        """测试多个阶段"""
        session_id = "test_session"
        
        # 建立连接
        connection_id = await service.connect(mock_websocket, session_id)
        
        # 阶段 1: 意图识别
        await service.send_stage_start(
            session_id=session_id,
            stage_id="stage_1",
            stage_name="意图识别",
            content="识别用户意图..."
        )
        await service.send_stage_complete(
            session_id=session_id,
            stage_id="stage_1",
            stage_name="意图识别",
            content="意图识别完成"
        )
        
        # 阶段 2: 智能选表
        await service.send_stage_start(
            session_id=session_id,
            stage_id="stage_2",
            stage_name="智能选表",
            content="选择相关数据表..."
        )
        await service.send_stage_complete(
            session_id=session_id,
            stage_id="stage_2",
            stage_name="智能选表",
            content="选表完成"
        )
        
        # 阶段 3: SQL 生成
        await service.send_stage_start(
            session_id=session_id,
            stage_id="stage_3",
            stage_name="SQL 生成",
            content="生成 SQL 查询..."
        )
        await service.send_stage_complete(
            session_id=session_id,
            stage_id="stage_3",
            stage_name="SQL 生成",
            content="SQL 生成完成"
        )
        
        # 验证所有消息都已发送
        assert mock_websocket.send_text.call_count >= 6
    
    def test_stage_message_types_exist(self):
        """测试阶段消息类型存在"""
        assert hasattr(StreamMessageType, 'STAGE_START')
        assert hasattr(StreamMessageType, 'STAGE_UPDATE')
        assert hasattr(StreamMessageType, 'STAGE_COMPLETE')
        
        assert StreamMessageType.STAGE_START.value == "stage_start"
        assert StreamMessageType.STAGE_UPDATE.value == "stage_update"
        assert StreamMessageType.STAGE_COMPLETE.value == "stage_complete"
