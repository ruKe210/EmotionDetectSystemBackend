import numpy as np
from typing import Dict, Optional
from dataclasses import dataclass
import time
import random


@dataclass
class DiscreteEmotion:
    """离散情绪结果"""
    emotion: str  # happy, sad, angry, fear, surprise, neutral
    confidence: float


@dataclass
class ContinuousEmotion:
    """连续情绪结果 (PAD模型)"""
    pleasure: float   # P: -1 to 1 (愉悦度)
    arousal: float    # A: -1 to 1 (唤醒度)
    dominance: float  # D: -1 to 1 (支配度)


@dataclass
class EmotionRecognitionResult:
    """情绪识别结果"""
    discrete: DiscreteEmotion
    continuous: ContinuousEmotion
    all_emotions: Dict[str, float]  # 所有情绪的概率分布
    processing_time: float  # 处理时间(ms)


class EmotionRecognizer:
    """
    情绪识别器 - 预留接口
    后续可以接入CNN+LSTM等深度学习模型
    """
    
    # 离散情绪类别
    EMOTIONS = ["happy", "sad", "angry", "fear", "surprise", "neutral"]
    
    def __init__(self):
        self.is_loaded = False
        self.model = None
        self.device = "cpu"
        
    def load_model(self, model_path: Optional[str] = None):
        """
        加载情绪识别模型
        后续实现：加载CNN+LSTM模型
        """
        # TODO: 实现模型加载
        # 例如：
        # import torch
        # self.model = torch.load(model_path)
        # self.model.eval()
        self.is_loaded = True
        print("情绪识别模型加载完成（模拟）")
        
    def recognize(self, face_image: np.ndarray) -> EmotionRecognitionResult:
        """
        识别情绪
        
        Args:
            face_image: 人脸图像 (RGB格式)
            
        Returns:
            情绪识别结果
        """
        if not self.is_loaded:
            self.load_model()
        
        start_time = time.time()
        
        # TODO: 实现真实的情绪识别逻辑
        # 目前返回模拟数据
        result = self._mock_recognize(face_image)
        
        processing_time = (time.time() - start_time) * 1000  # 转换为毫秒
        result.processing_time = processing_time
        
        return result
    
    def _mock_recognize(self, face_image: np.ndarray) -> EmotionRecognitionResult:
        """模拟情绪识别 - 用于测试"""
        # 生成随机情绪概率
        emotions_prob = {}
        total = 0
        for emotion in self.EMOTIONS:
            prob = random.random()
            emotions_prob[emotion] = prob
            total += prob
        
        # 归一化
        for emotion in emotions_prob:
            emotions_prob[emotion] /= total
        
        # 找出主导情绪
        dominant_emotion = max(emotions_prob, key=emotions_prob.get)
        
        # 生成连续情绪值 (PAD)
        continuous = ContinuousEmotion(
            pleasure=random.uniform(-1, 1),
            arousal=random.uniform(-1, 1),
            dominance=random.uniform(-1, 1)
        )
        
        discrete = DiscreteEmotion(
            emotion=dominant_emotion,
            confidence=emotions_prob[dominant_emotion]
        )
        
        return EmotionRecognitionResult(
            discrete=discrete,
            continuous=continuous,
            all_emotions=emotions_prob,
            processing_time=0
        )
    
    def recognize_batch(self, face_images: list) -> list:
        """
        批量识别情绪
        
        Args:
            face_images: 人脸图像列表
            
        Returns:
            情绪识别结果列表
        """
        results = []
        for face_img in face_images:
            result = self.recognize(face_img)
            results.append(result)
        return results
    
    def get_model_info(self) -> Dict:
        """获取模型信息"""
        return {
            "model_name": "CNN+LSTM（预留）",
            "is_loaded": self.is_loaded,
            "device": self.device,
            "emotions": self.EMOTIONS,
            "supports_discrete": True,
            "supports_continuous": True
        }


# 全局情绪识别器实例
emotion_recognizer = EmotionRecognizer()