from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import json
from app.websocket.manager import websocket_manager

router = APIRouter()


async def _ws_loop(websocket: WebSocket, channel: str):
    """通用 WebSocket 循环：接收消息、响应 ping、处理断连"""
    await websocket_manager.connect(websocket, channel)
    try:
        while True:
            raw = await websocket.receive_text()
            # 响应客户端心跳
            try:
                msg = json.loads(raw)
                if msg.get("type") == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))
            except (json.JSONDecodeError, TypeError):
                pass
    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket, channel)
    except Exception:
        websocket_manager.disconnect(websocket, channel)


@router.websocket("/ws/face")
async def websocket_face(websocket: WebSocket):
    """WebSocket端点 - 实时人脸数据"""
    await _ws_loop(websocket, "face")


@router.websocket("/ws/stats")
async def websocket_stats(websocket: WebSocket):
    """WebSocket端点 - 实时统计数据"""
    await _ws_loop(websocket, "stats")


@router.websocket("/ws/alerts")
async def websocket_alerts(websocket: WebSocket):
    """WebSocket端点 - 实时告警"""
    await _ws_loop(websocket, "alerts")


@router.websocket("/ws/video")
async def websocket_video(websocket: WebSocket):
    """WebSocket端点 - 视频流"""
    await _ws_loop(websocket, "video")
