"""
WebSocket管理器 - 连接推理引擎和前端
"""
import asyncio
import json
import base64
import cv2
import numpy as np
import time
from typing import Dict, List, Set
from fastapi import WebSocket, WebSocketDisconnect
from datetime import datetime

from app.services.inference_engine import inference_engine, InferenceFrame
from app.services.data_store import data_store


class WebSocketManager:
    """WebSocket连接管理器"""
    
    def __init__(self):
        # 存储活跃的WebSocket连接
        self.active_connections: Dict[str, List[WebSocket]] = {
            "face": [],      # 人脸识别结果
            "stats": [],     # 统计数据
            "alerts": [],    # 告警信息
            "video": [],     # 视频流
        }
        self.is_running = False
        self.broadcast_task = None
        
        # 注册推理引擎回调
        inference_engine.register_callback(self._on_inference_result)
        inference_engine.register_frame_callback(self._on_frame_ready)
        
        # 缓存最新数据
        self.latest_face_data = {}
        self.latest_stats = {}
        self.video_frames = {}  # camera_id -> frame_base64
        
        # 情绪分布缓存（避免在 async 循环中阻塞查询 DB）
        self._emotion_dist_cache = {}
        self._emotion_dist_last_update = 0
        self._emotion_dist_interval = 5.0  # 每 5 秒更新一次
        
    async def connect(self, websocket: WebSocket, channel: str):
        """建立WebSocket连接"""
        await websocket.accept()
        if channel in self.active_connections:
            self.active_connections[channel].append(websocket)
        print(f"WebSocket连接已建立: {channel}, 当前连接数: {len(self.active_connections[channel])}")
    
    def disconnect(self, websocket: WebSocket, channel: str):
        """断开WebSocket连接"""
        if channel in self.active_connections:
            if websocket in self.active_connections[channel]:
                self.active_connections[channel].remove(websocket)
        print(f"WebSocket连接已断开: {channel}, 当前连接数: {len(self.active_connections[channel])}")
    
    async def broadcast(self, message: dict, channel: str):
        """广播消息到指定频道"""
        if channel not in self.active_connections:
            return
        
        # 转换datetime为字符串
        message_json = json.dumps(message, default=str)
        
        # 发送到该频道的所有连接
        disconnected = []
        for connection in self.active_connections[channel]:
            try:
                await connection.send_text(message_json)
            except Exception as e:
                print(f"发送消息失败: {e}")
                disconnected.append(connection)
        
        # 清理断开的连接
        for conn in disconnected:
            self.disconnect(conn, channel)
    
    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """发送个人消息"""
        message_json = json.dumps(message, default=str)
        await websocket.send_text(message_json)
    
    def _on_inference_result(self, inference_frame: InferenceFrame):
        """推理结果回调 - 由推理引擎调用"""
        # 更新最新人脸数据
        self.latest_face_data[inference_frame.camera_id] = {
            "camera_id": inference_frame.camera_id,
            "timestamp": inference_frame.timestamp,
            "faces": [face.to_dict() for face in inference_frame.faces]
        }
        
        # 更新统计
        self.latest_stats = {
            "timestamp": datetime.now().isoformat(),
            "total_frames": inference_engine.stats["total_frames"],
            "total_faces": inference_engine.stats["total_faces"],
            "fps": inference_engine.stats["fps"],
            "inference_time_ms": inference_engine.stats["inference_time_ms"],
            "active_cameras": len(inference_engine.active_cameras)
        }
    
    def _on_frame_ready(self, inference_frame: InferenceFrame):
        """帧准备好回调 - 由推理引擎调用"""
        if inference_frame.frame_base64:
            self.video_frames[inference_frame.camera_id] = inference_frame.frame_base64
    
    def start_broadcast_loop(self):
        """启动广播循环（在主事件循环中创建任务）"""
        if self.is_running:
            return
        self.is_running = True

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.get_event_loop()
        self.broadcast_task = loop.create_task(self._broadcast_loop())
    
    async def _broadcast_loop(self):
        """广播循环 - 定期发送数据（不阻塞事件循环）"""
        while self.is_running:
            try:
                # 发送实时人脸数据
                if self.active_connections["face"] and self.latest_face_data:
                    for camera_id, data in self.latest_face_data.items():
                        message = {
                            "type": "face",
                            "timestamp": datetime.now().isoformat(),
                            "data": data
                        }
                        await self.broadcast(message, "face")
                
                # 发送统计数据（情绪分布用缓存，不阻塞）
                if self.active_connections["stats"] and self.latest_stats:
                    now = time.time()
                    if now - self._emotion_dist_last_update >= self._emotion_dist_interval:
                        try:
                            self._emotion_dist_cache = await asyncio.to_thread(
                                data_store.get_emotion_distribution, 5
                            )
                            self._emotion_dist_last_update = now
                        except Exception as e:
                            print(f"[WS] 获取情绪分布失败: {e}")

                    stats_message = {
                        "type": "stats",
                        "timestamp": datetime.now().isoformat(),
                        "data": {
                            **self.latest_stats,
                            "emotion_distribution": self._emotion_dist_cache
                        }
                    }
                    await self.broadcast(stats_message, "stats")
                
                # 发送视频流
                if self.active_connections["video"] and self.video_frames:
                    for camera_id, frame_base64 in self.video_frames.items():
                        message = {
                            "type": "video",
                            "camera_id": camera_id,
                            "timestamp": datetime.now().isoformat(),
                            "frame": frame_base64
                        }
                        await self.broadcast(message, "video")
                
                await asyncio.sleep(0.05)  # 每50ms发送一次 (20 FPS)
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"广播循环错误: {e}")
                await asyncio.sleep(0.5)
    
    def stop(self):
        """停止广播循环"""
        self.is_running = False
        if self.broadcast_task:
            self.broadcast_task.cancel()
            self.broadcast_task = None
        # 注销回调
        inference_engine.unregister_callback(self._on_inference_result)
        inference_engine.unregister_frame_callback(self._on_frame_ready)


# 全局WebSocket管理器
websocket_manager = WebSocketManager()
