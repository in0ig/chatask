"""
WebSocket流式通信API

提供WebSocket端点和流式通信管理接口。
"""

import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, Depends, Query
from fastapi.responses import JSONResponse

from ..services.websocket_stream_service import (
    get_websocket_stream_service,
    StreamMessageType,
    ConnectionStatus
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/stream", tags=["WebSocket流式通信"])


@router.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """
    WebSocket连接端点
    
    Args:
        websocket: WebSocket连接对象
        session_id: 会话ID
    """
    connection_id = None
    
    try:
        # 建立连接
        websocket_service = get_websocket_stream_service()
        connection_id = await websocket_service.connect(websocket, session_id)
        logger.info(f"WebSocket连接建立成功: session_id={session_id}, connection_id={connection_id}")
        
        # 保持连接并处理消息
        while True:
            try:
                # 接收客户端消息
                data = await websocket.receive_text()
                logger.debug(f"收到客户端消息: session_id={session_id}, data={data}")
                
                # 这里可以添加客户端消息处理逻辑
                # 例如：处理客户端的心跳响应、状态更新等
                
            except WebSocketDisconnect:
                logger.info(f"客户端主动断开连接: session_id={session_id}")
                break
            except Exception as e:
                logger.error(f"处理WebSocket消息时出错: session_id={session_id}, error={str(e)}")
                await websocket_service.send_error_message(
                    session_id, 
                    f"消息处理错误: {str(e)}", 
                    "MESSAGE_PROCESSING_ERROR"
                )
                
    except Exception as e:
        logger.error(f"WebSocket连接错误: session_id={session_id}, error={str(e)}")
        if connection_id:
            websocket_service = get_websocket_stream_service()
            await websocket_service.send_error_message(
                session_id, 
                f"连接错误: {str(e)}", 
                "CONNECTION_ERROR"
            )
    finally:
        # 清理连接
        if connection_id:
            websocket_service = get_websocket_stream_service()
            await websocket_service.disconnect(connection_id, "连接结束")


@router.post("/send-message/{session_id}")
async def send_stream_message(
    session_id: str,
    message_type: str,
    content: str,
    metadata: Optional[Dict[str, Any]] = None,
    connection_id: Optional[str] = None
):
    """
    发送流式消息
    
    Args:
        session_id: 会话ID
        message_type: 消息类型 (thinking, result, chart, error, status)
        content: 消息内容
        metadata: 元数据（可选）
        connection_id: 指定连接ID（可选）
    """
    try:
        # 验证消息类型
        try:
            msg_type = StreamMessageType(message_type)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"无效的消息类型: {message_type}"
            )
        
        # 发送消息
        websocket_service = get_websocket_stream_service()
        success = await websocket_service.send_message(
            session_id=session_id,
            message_type=msg_type,
            content=content,
            metadata=metadata,
            connection_id=connection_id
        )
        
        if not success:
            raise HTTPException(
                status_code=404,
                detail=f"会话无活跃连接: {session_id}"
            )
        
        return {"success": True, "message": "消息发送成功"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"发送流式消息失败: session_id={session_id}, error={str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"发送消息失败: {str(e)}"
        )


@router.post("/send-thinking/{session_id}")
async def send_thinking_message(
    session_id: str,
    content: str,
    metadata: Optional[Dict[str, Any]] = None
):
    """
    发送思考过程消息（灰色显示）
    
    Args:
        session_id: 会话ID
        content: 思考内容
        metadata: 元数据（可选）
    """
    try:
        websocket_service = get_websocket_stream_service()
        await websocket_service.send_thinking_message(session_id, content, metadata)
        return {"success": True, "message": "思考消息发送成功"}
    except Exception as e:
        logger.error(f"发送思考消息失败: session_id={session_id}, error={str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"发送思考消息失败: {str(e)}"
        )


@router.post("/send-result/{session_id}")
async def send_result_message(
    session_id: str,
    content: str,
    metadata: Optional[Dict[str, Any]] = None
):
    """
    发送最终结果消息（黑色显示）
    
    Args:
        session_id: 会话ID
        content: 结果内容
        metadata: 元数据（可选）
    """
    try:
        websocket_service = get_websocket_stream_service()
        await websocket_service.send_result_message(session_id, content, metadata)
        return {"success": True, "message": "结果消息发送成功"}
    except Exception as e:
        logger.error(f"发送结果消息失败: session_id={session_id}, error={str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"发送结果消息失败: {str(e)}"
        )


@router.post("/send-chart/{session_id}")
async def send_chart_message(
    session_id: str,
    chart_data: Dict[str, Any]
):
    """
    发送图表消息
    
    Args:
        session_id: 会话ID
        chart_data: 图表数据
    """
    try:
        websocket_service = get_websocket_stream_service()
        await websocket_service.send_chart_message(session_id, chart_data)
        return {"success": True, "message": "图表消息发送成功"}
    except Exception as e:
        logger.error(f"发送图表消息失败: session_id={session_id}, error={str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"发送图表消息失败: {str(e)}"
        )


@router.post("/send-error/{session_id}")
async def send_error_message(
    session_id: str,
    error: str,
    error_code: Optional[str] = None
):
    """
    发送错误消息
    
    Args:
        session_id: 会话ID
        error: 错误信息
        error_code: 错误代码（可选）
    """
    try:
        websocket_service = get_websocket_stream_service()
        await websocket_service.send_error_message(session_id, error, error_code)
        return {"success": True, "message": "错误消息发送成功"}
    except Exception as e:
        logger.error(f"发送错误消息失败: session_id={session_id}, error={str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"发送错误消息失败: {str(e)}"
        )


@router.post("/send-status/{session_id}")
async def send_status_message(
    session_id: str,
    status: str,
    progress: Optional[float] = None
):
    """
    发送状态更新消息
    
    Args:
        session_id: 会话ID
        status: 状态信息
        progress: 进度（0.0-1.0，可选）
    """
    try:
        websocket_service = get_websocket_stream_service()
        await websocket_service.send_status_message(session_id, status, progress)
        return {"success": True, "message": "状态消息发送成功"}
    except Exception as e:
        logger.error(f"发送状态消息失败: session_id={session_id}, error={str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"发送状态消息失败: {str(e)}"
        )


@router.post("/resume-connection/{connection_id}")
async def resume_connection(connection_id: str):
    """
    恢复连接并发送待发送消息
    
    Args:
        connection_id: 连接ID
    """
    try:
        websocket_service = get_websocket_stream_service()
        success = await websocket_service.resume_connection(connection_id)
        
        if not success:
            raise HTTPException(
                status_code=404,
                detail=f"连接不存在或无法恢复: {connection_id}"
            )
        
        return {"success": True, "message": "连接恢复成功"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"恢复连接失败: connection_id={connection_id}, error={str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"恢复连接失败: {str(e)}"
        )


@router.get("/status/{session_id}")
async def get_connection_status(session_id: str):
    """
    获取会话连接状态
    
    Args:
        session_id: 会话ID
    """
    try:
        websocket_service = get_websocket_stream_service()
        status = websocket_service.get_connection_status(session_id)
        return status
    except Exception as e:
        logger.error(f"获取连接状态失败: session_id={session_id}, error={str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"获取连接状态失败: {str(e)}"
        )


@router.get("/status")
async def get_all_connections_status():
    """获取所有连接状态"""
    try:
        websocket_service = get_websocket_stream_service()
        status = websocket_service.get_all_connections_status()
        return status
    except Exception as e:
        logger.error(f"获取所有连接状态失败: error={str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"获取连接状态失败: {str(e)}"
        )


@router.get("/health")
async def health_check():
    """健康检查"""
    try:
        websocket_service = get_websocket_stream_service()
        status = websocket_service.get_all_connections_status()
        return {
            "status": "healthy",
            "service": "WebSocket流式通信服务",
            "total_connections": status["total_connections"],
            "total_sessions": status["total_sessions"],
            "timestamp": "2024-01-01T00:00:00Z"
        }
    except Exception as e:
        logger.error(f"健康检查失败: error={str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"健康检查失败: {str(e)}"
        )


@router.post("/send-stage-start/{session_id}")
async def send_stage_start(
    session_id: str,
    stage_id: str,
    stage_name: str,
    content: str = "",
    metadata: Optional[Dict[str, Any]] = None
):
    """
    发送阶段开始消息
    
    Args:
        session_id: 会话ID
        stage_id: 阶段ID
        stage_name: 阶段名称
        content: 阶段内容
        metadata: 元数据（可选）
    """
    try:
        websocket_service = get_websocket_stream_service()
        await websocket_service.send_stage_start(
            session_id, stage_id, stage_name, content, metadata
        )
        return {"success": True, "message": "阶段开始消息发送成功"}
    except Exception as e:
        logger.error(f"发送阶段开始消息失败: session_id={session_id}, error={str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"发送阶段开始消息失败: {str(e)}"
        )


@router.post("/send-stage-update/{session_id}")
async def send_stage_update(
    session_id: str,
    stage_id: str,
    content: str,
    metadata: Optional[Dict[str, Any]] = None
):
    """
    发送阶段更新消息
    
    Args:
        session_id: 会话ID
        stage_id: 阶段ID
        content: 更新内容
        metadata: 元数据（可选）
    """
    try:
        websocket_service = get_websocket_stream_service()
        await websocket_service.send_stage_update(
            session_id, stage_id, content, metadata
        )
        return {"success": True, "message": "阶段更新消息发送成功"}
    except Exception as e:
        logger.error(f"发送阶段更新消息失败: session_id={session_id}, error={str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"发送阶段更新消息失败: {str(e)}"
        )


@router.post("/send-stage-complete/{session_id}")
async def send_stage_complete(
    session_id: str,
    stage_id: str,
    stage_name: str,
    content: str = "",
    metadata: Optional[Dict[str, Any]] = None
):
    """
    发送阶段完成消息
    
    Args:
        session_id: 会话ID
        stage_id: 阶段ID
        stage_name: 阶段名称
        content: 完成内容
        metadata: 元数据（可选）
    """
    try:
        websocket_service = get_websocket_stream_service()
        await websocket_service.send_stage_complete(
            session_id, stage_id, stage_name, content, metadata
        )
        return {"success": True, "message": "阶段完成消息发送成功"}
    except Exception as e:
        logger.error(f"发送阶段完成消息失败: session_id={session_id}, error={str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"发送阶段完成消息失败: {str(e)}"
        )