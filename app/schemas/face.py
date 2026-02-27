from pydantic import BaseModel
from typing import List, Optional, Dict
from datetime import datetime


class FaceBox(BaseModel):
    x: int
    y: int
    width: int
    height: int


class FaceExpression(BaseModel):
    happy: float
    sad: float
    angry: float
    neutral: float
    fearful: float
    surprised: float
    disgusted: float
    contempt: float = 0.0


class FaceDetection(BaseModel):
    id: str
    camera_id: str
    box: FaceBox
    expressions: FaceExpression
    confidence: float
    timestamp: datetime
    face_image: Optional[str] = None  # base64 encoded image
    # 二维情感
    valence: float = 0.0
    arousal: float = 0.0
    # 三维情感
    pleasure: float = 0.0
    pad_arousal: float = 0.0
    dominance: float = 0.0


class FaceHistory(BaseModel):
    id: str
    camera_id: str
    expressions: FaceExpression
    dominant_emotion: str
    confidence: float
    timestamp: datetime
    # 二维情感
    valence: float = 0.0
    arousal: float = 0.0
    # 三维情感
    pleasure: float = 0.0
    pad_arousal: float = 0.0
    dominance: float = 0.0

    class Config:
        from_attributes = True


class FaceStats(BaseModel):
    online_devices: int
    current_faces: int
    today_recognition: int
    today_alerts: int
    cpu_usage: float
    memory_usage: float
    uptime: int  # seconds
    emotion_distribution: Dict[str, int]
