from pydantic import BaseModel
from typing import Optional, List


class VideoConfig(BaseModel):
    cameraId: str = "0"
    resolution: str = "640x480"
    fps: int = 30
    duration: int = 60  # 采集时长（分钟）


class RecognitionConfig(BaseModel):
    modelType: str = "cnn_lstm"
    delayThreshold: int = 200  # 延迟阈值（ms）
    accuracyThreshold: float = 0.85
    emotionChangeThreshold: float = 0.1


class StorageConfig(BaseModel):
    path: str = "./data"
    period: int = 30  # 保存天数
    autoBackup: bool = True
    backupFrequency: str = "daily"  # daily, weekly, monthly


class PermissionConfig(BaseModel):
    role: str = "admin"
    permissions: List[str] = ["read", "write", "delete", "config"]


class SystemConfig(BaseModel):
    video: VideoConfig = VideoConfig()
    recognition: RecognitionConfig = RecognitionConfig()
    storage: StorageConfig = StorageConfig()
    permission: PermissionConfig = PermissionConfig()