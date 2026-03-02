from pydantic_settings import BaseSettings
from typing import List
import os


class Settings(BaseSettings):
    # 应用配置
    APP_NAME: str = "情绪识别管理系统"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    
    # 服务器配置
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # 跨域配置
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]
    
    # JWT配置
    SECRET_KEY: str = "emotion-detect-secret-key-2024"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24小时
    
    # 视频流配置
    VIDEO_FPS: int = 30
    VIDEO_WIDTH: int = 640
    VIDEO_HEIGHT: int = 480
    MAX_STREAMS: int = 8  # 最大8路视频流
    
    # 人脸检测配置
    FACE_DETECTION_CONFIDENCE: float = 0.85
    MIN_FACE_SIZE: int = 32
    MAX_FACES_PER_FRAME: int = 10  # 最多检测10人
    
    # 情绪识别配置
    EMOTION_MODEL_PATH: str = "models/emotion_model.pth"
    DISCRETE_EMOTIONS: List[str] = ["happy", "sad", "angry", "fear", "surprise", "neutral"]
    
    # 数据库配置
    DB_HOST: str = "localhost"
    DB_PORT: int = 3306
    DB_USER: str = "root"
    DB_PASSWORD: str = "su15906477192"
    DB_NAME: str = "emotion_detect"

    @property
    def DATABASE_URL(self) -> str:
        return f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}?charset=utf8mb4"

    # 数据存储配置
    DATA_STORAGE_PATH: str = "data/storage"
    LOG_PATH: str = "data/logs"
    
    # 摄像头配置
    DEFAULT_CAMERA_ID: int = 0  # 默认使用笔记本内置摄像头
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()

# 确保目录存在
os.makedirs(settings.DATA_STORAGE_PATH, exist_ok=True)
os.makedirs(settings.LOG_PATH, exist_ok=True)