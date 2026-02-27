from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class DiscreteEmotion(BaseModel):
    emotion: str  # happy, sad, angry, fearful, surprised, disgusted, neutral, contempt
    confidence: float


class ContinuousEmotion2D(BaseModel):
    """二维情感模型 (Valence-Arousal)"""
    valence: float  # 效价: -1(消极) ~ +1(积极)
    arousal: float  # 唤醒度: -1(平静) ~ +1(兴奋)


class ContinuousEmotion3D(BaseModel):
    """三维情感模型 (PAD: Pleasure-Arousal-Dominance)"""
    pleasure: float   # 愉悦度: -1 ~ +1
    arousal: float    # 唤醒度: -1 ~ +1
    dominance: float  # 支配度: -1 ~ +1


class EmotionResult(BaseModel):
    face_id: str
    camera_id: str
    discrete: DiscreteEmotion
    continuous_2d: ContinuousEmotion2D
    continuous_3d: ContinuousEmotion3D
    all_emotions: dict  # 所有情绪的概率
    timestamp: datetime
    processing_time: float  # 处理时间(ms)
