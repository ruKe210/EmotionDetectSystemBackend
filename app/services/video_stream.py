import cv2
import asyncio
import threading
import time
import uuid
import os
from typing import Dict, Optional, Callable, List, Union
from datetime import datetime
import numpy as np
from app.core.config import settings


class VideoStream:
    """单个视频流管理器 - 支持 USB 和 RTSP"""
    
    def __init__(self, camera_id: str, source: Union[int, str], name: str = ""):
        self.camera_id = camera_id
        self.source = source  # 整数=USB索引, 字符串=RTSP URL
        self.name = name or f"Camera_{camera_id}"
        self.cap: Optional[cv2.VideoCapture] = None
        self.is_running = False
        self.is_paused = False
        self.frame: Optional[np.ndarray] = None
        self.fps = 0
        self.frame_count = 0
        self.start_time = None
        self.lock = threading.Lock()
        self.thread: Optional[threading.Thread] = None
        self.callbacks: List[Callable] = []
        self.last_frame_time = 0
        self.frame_interval = 1.0 / settings.VIDEO_FPS
        self.is_rtsp = isinstance(source, str) and "rtsp://" in source
        
    def add_callback(self, callback: Callable):
        """添加帧处理回调函数"""
        self.callbacks.append(callback)
        
    def remove_callback(self, callback: Callable):
        """移除帧处理回调函数"""
        if callback in self.callbacks:
            self.callbacks.remove(callback)
    
    def start(self) -> bool:
        """启动视频流"""
        if self.is_running:
            return True
        
        if self.is_rtsp:
            # RTSP 低延迟配置
            os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = (
                "rtsp_transport;udp|"
                "fflags;nobuffer|"
                "flags;low_delay|"
                "framedrop;1|"
                "max_delay;500000|"
                "analyzeduration;500000|"
                "probesize;32768"
            )
            self.cap = cv2.VideoCapture(self.source, cv2.CAP_FFMPEG)
            if self.cap.isOpened():
                self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        elif isinstance(self.source, int):
            # USB 摄像头：Windows 用 DirectShow
            self.cap = cv2.VideoCapture(self.source, cv2.CAP_DSHOW)
            if not self.cap.isOpened():
                self.cap = cv2.VideoCapture(self.source)
        else:
            self.cap = cv2.VideoCapture(self.source)
            
        if not self.cap.isOpened():
            print(f"无法打开视频源: {self.source}")
            return False
            
        # USB 摄像头设置分辨率，RTSP 由摄像头端决定
        if not self.is_rtsp:
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, settings.VIDEO_WIDTH)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, settings.VIDEO_HEIGHT)
            self.cap.set(cv2.CAP_PROP_FPS, settings.VIDEO_FPS)
        
        # 先读取一帧测试
        ret, test_frame = self.cap.read()
        if not ret or test_frame is None:
            print(f"视频源 {self.source} 无法读取帧")
            self.cap.release()
            return False
        
        print(f"视频源 {self.source} 测试成功，帧尺寸: {test_frame.shape}")
        
        self.is_running = True
        self.start_time = time.time()
        self.thread = threading.Thread(target=self._capture_loop)
        self.thread.daemon = True
        self.thread.start()
        
        print(f"视频流 {self.camera_id} 已启动")
        return True
    
    def _capture_loop(self):
        """视频捕获循环"""
        while self.is_running:
            if self.is_paused:
                time.sleep(0.01)
                continue
                
            current_time = time.time()
            elapsed = current_time - self.last_frame_time
            
            # 控制帧率
            if elapsed < self.frame_interval:
                time.sleep(self.frame_interval - elapsed)
                
            ret, frame = self.cap.read()
            if not ret:
                if self.is_rtsp:
                    # RTSP 断线重连
                    print(f"视频流 {self.camera_id} RTSP 断线，尝试重连...")
                    self.cap.release()
                    time.sleep(1)
                    os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = (
                        "rtsp_transport;udp|fflags;nobuffer|flags;low_delay|"
                        "framedrop;1|max_delay;500000|analyzeduration;500000|probesize;32768"
                    )
                    self.cap = cv2.VideoCapture(self.source, cv2.CAP_FFMPEG)
                    if self.cap.isOpened():
                        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                    continue
                elif isinstance(self.source, str):
                    self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    continue
                else:
                    print(f"视频流 {self.camera_id} 读取失败")
                    break
            
            with self.lock:
                self.frame = frame.copy()
                self.frame_count += 1
                
            self.last_frame_time = time.time()
            
            # 计算实际FPS
            if self.frame_count % 30 == 0 and self.start_time:
                self.fps = self.frame_count / (time.time() - self.start_time)
            
            # 调用回调函数处理帧
            for callback in self.callbacks:
                try:
                    callback(self.camera_id, frame)
                except Exception as e:
                    print(f"回调函数执行错误: {e}")
    
    def get_frame(self) -> Optional[np.ndarray]:
        """获取当前帧"""
        with self.lock:
            return self.frame.copy() if self.frame is not None else None
    
    def pause(self):
        """暂停视频流"""
        self.is_paused = True
        print(f"视频流 {self.camera_id} 已暂停")
    
    def resume(self):
        """恢复视频流"""
        self.is_paused = False
        print(f"视频流 {self.camera_id} 已恢复")
    
    def stop(self):
        """停止视频流"""
        self.is_running = False
        if self.thread:
            self.thread.join(timeout=2)
        if self.cap:
            self.cap.release()
        print(f"视频流 {self.camera_id} 已停止")
    
    def get_status(self) -> dict:
        """获取视频流状态"""
        return {
            "camera_id": self.camera_id,
            "name": self.name,
            "is_running": self.is_running,
            "is_paused": self.is_paused,
            "fps": round(self.fps, 2),
            "frame_count": self.frame_count,
            "resolution": f"{settings.VIDEO_WIDTH}x{settings.VIDEO_HEIGHT}",
            "uptime": time.time() - self.start_time if self.start_time else 0
        }


class VideoStreamManager:
    """视频流管理器 - 管理多个视频流"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self.streams: Dict[str, VideoStream] = {}
        self._initialized = True
    
    def create_stream(self, source: Union[int, str] = 0, name: str = "", camera_id: str = "") -> str:
        """创建新的视频流"""
        if not camera_id:
            camera_id = str(uuid.uuid4())[:8]
        
        # 如果已存在同 ID 的流，先停掉
        if camera_id in self.streams:
            self.streams[camera_id].stop()
            del self.streams[camera_id]
        
        stream = VideoStream(camera_id, source, name)
        self.streams[camera_id] = stream
        return camera_id
    
    def start_stream(self, camera_id: str) -> bool:
        """启动指定视频流"""
        if camera_id not in self.streams:
            return False
        return self.streams[camera_id].start()
    
    def stop_stream(self, camera_id: str):
        """停止指定视频流"""
        if camera_id in self.streams:
            self.streams[camera_id].stop()
    
    def remove_stream(self, camera_id: str):
        """移除视频流"""
        if camera_id in self.streams:
            self.streams[camera_id].stop()
            del self.streams[camera_id]
    
    def get_stream(self, camera_id: str) -> Optional[VideoStream]:
        """获取视频流对象"""
        return self.streams.get(camera_id)
    
    def get_all_streams(self) -> Dict[str, VideoStream]:
        """获取所有视频流"""
        return self.streams
    
    def get_stream_status(self, camera_id: str) -> Optional[dict]:
        """获取指定视频流状态"""
        if camera_id in self.streams:
            return self.streams[camera_id].get_status()
        return None
    
    def get_all_status(self) -> List[dict]:
        """获取所有视频流状态"""
        return [stream.get_status() for stream in self.streams.values()]
    
    def stop_all(self):
        """停止所有视频流"""
        for stream in self.streams.values():
            stream.stop()
        self.streams.clear()
    
    def add_frame_callback(self, camera_id: str, callback: Callable):
        """为指定视频流添加帧处理回调"""
        if camera_id in self.streams:
            self.streams[camera_id].add_callback(callback)
    
    def remove_frame_callback(self, camera_id: str, callback: Callable):
        """移除帧处理回调"""
        if camera_id in self.streams:
            self.streams[camera_id].remove_callback(callback)


# 全局视频流管理器实例
video_manager = VideoStreamManager()