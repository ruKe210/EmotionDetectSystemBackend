import psutil
import time
from fastapi import APIRouter, Depends
from datetime import datetime
from app.schemas import ResponseModel
from app.api.deps import get_current_active_user
from app.services.data_store import data_store
from app.services.video_stream import video_manager
from app.services.face_detection import face_detector
from app.services.emotion_recognition import emotion_recognizer

router = APIRouter()

# 系统启动时间
SYSTEM_START_TIME = time.time()


@router.get("/status", response_model=ResponseModel)
async def get_system_status(
    current_user: dict = Depends(get_current_active_user)
):
    """获取系统状态"""
    # 获取CPU和内存使用率
    cpu_usage = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    
    # 获取在线连接数（模拟）
    active_connections = len(video_manager.get_all_streams())
    
    return ResponseModel(data={
        "isOnline": True,
        "cpuUsage": cpu_usage,
        "memoryUsage": memory.percent,
        "diskUsage": disk.percent,
        "uptime": int(time.time() - SYSTEM_START_TIME),
        "activeConnections": active_connections
    })


@router.get("/health", response_model=ResponseModel)
async def get_health_status(
    current_user: dict = Depends(get_current_active_user)
):
    """获取健康状态"""
    # 检查各项服务状态
    cpu_usage = psutil.cpu_percent(interval=0.5)
    memory = psutil.virtual_memory()
    
    # 判断健康状态
    if cpu_usage > 90 or memory.percent > 90:
        status = "danger"
    elif cpu_usage > 70 or memory.percent > 70:
        status = "warning"
    else:
        status = "healthy"
    
    return ResponseModel(data={
        "status": status,
        "services": {
            "api": "running",
            "video_stream": "running" if video_manager.get_all_streams() else "standby",
            "face_detection": "loaded" if face_detector.is_loaded else "not_loaded",
            "emotion_recognition": "loaded" if emotion_recognizer.is_loaded else "not_loaded"
        },
        "checked_at": datetime.now()
    })