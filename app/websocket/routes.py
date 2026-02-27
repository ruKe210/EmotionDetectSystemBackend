from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.websocket.manager import websocket_manager

router = APIRouter()


@router.websocket("/ws/face")
async def websocket_face(websocket: WebSocket):
    """WebSocket端点 - 实时人脸数据"""
    await websocket_manager.connect(websocket, "face")
    try:
        while True:
            # 接收客户端消息（心跳等）
            data = await websocket.receive_text()
            # 可以处理客户端发送的命令
    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket, "face")


@router.websocket("/ws/stats")
async def websocket_stats(websocket: WebSocket):
    """WebSocket端点 - 实时统计数据"""
    await websocket_manager.connect(websocket, "stats")
    try:
        while True:
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket, "stats")


@router.websocket("/ws/alerts")
async def websocket_alerts(websocket: WebSocket):
    """WebSocket端点 - 实时告警"""
    await websocket_manager.connect(websocket, "alerts")
    try:
        while True:
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket, "alerts")


@router.websocket("/ws/video")
async def websocket_video(websocket: WebSocket):
    """WebSocket端点 - 视频流（使用推理引擎的帧）"""
    await websocket_manager.connect(websocket, "video")
    
    try:
        while True:
            # 保持连接，实际数据由 manager 广播
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket, "video")
    except Exception as e:
        print(f"视频流WebSocket错误: {e}")
        websocket_manager.disconnect(websocket, "video")


@router.websocket("/ws/video/{camera_id}")
async def websocket_video_camera(websocket: WebSocket, camera_id: str):
    """WebSocket端点 - 特定摄像头的视频流"""
    await websocket_manager.connect(websocket, "video")
    
    try:
        while True:
            # 保持连接，实际数据由 manager 广播
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket, "video")
    except Exception as e:
        print(f"视频流WebSocket错误: {e}")
        websocket_manager.disconnect(websocket, "video")
