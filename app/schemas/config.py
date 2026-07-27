from pydantic import BaseModel
from typing import List


class VideoConfig(BaseModel):
    cameraId: str = "0"
    resolution: str = "640x480"
    fps: int = 30
    duration: int = 10  # 视频分段时长（分钟）


class RecognitionConfig(BaseModel):
    modelType: str = "discrete"
    delayThreshold: int = 200  # 延迟阈值（ms）
    accuracyThreshold: float = 0.85
    emotionChangeThreshold: float = 0.2


class StorageConfig(BaseModel):
    path: str = "data/storage"
    period: int = 30  # 保存天数
    autoBackup: bool = True
    backupFrequency: str = "weekly"  # daily, weekly, monthly


class PermissionConfig(BaseModel):
    role: str = "admin"
    permissions: List[str] = ["read", "write", "delete", "config"]


class AIConfig(BaseModel):
    apiKey: str = ""
    baseUrl: str = "https://ark.cn-beijing.volces.com/api/v3"
    model: str = ""


class SystemConfig(BaseModel):
    video: VideoConfig = VideoConfig()
    recognition: RecognitionConfig = RecognitionConfig()
    storage: StorageConfig = StorageConfig()
    permission: PermissionConfig = PermissionConfig()
    ai: AIConfig = AIConfig()