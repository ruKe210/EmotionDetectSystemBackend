"""
OpenCV DNN 情绪识别器
使用公开的 Caffe 模型，支持 7 类情绪识别
模型来源: https://github.com/petercunha/EmotionRecognition
"""
import cv2
import numpy as np
import os
from typing import Dict
from dataclasses import dataclass


@dataclass
class EmotionResult:
    """情绪识别结果"""
    emotion: str  # 主导情绪
    confidence: float  # 置信度
    all_emotions: Dict[str, float]  # 所有情绪的概率


class OpenCVEmotionRecognizer:
    """
    OpenCV DNN 情绪识别器
    使用 Caffe 模型，无需 ONNX Runtime
    """
    
    # 7 类情绪标签（与模型训练时一致）
    EMOTION_LABELS = [
        "angry",      # 愤怒 - 0
        "disgusted",  # 厌恶 - 1
        "fearful",    # 恐惧 - 2
        "happy",      # 开心 - 3
        "sad",        # 悲伤 - 4
        "surprised",  # 惊讶 - 5
        "neutral"     # 平静 - 6
    ]
    
    # 情绪中文映射
    EMOTION_CN = {
        "happy": "开心",
        "sad": "悲伤",
        "angry": "愤怒",
        "fearful": "恐惧",
        "surprised": "惊讶",
        "disgusted": "厌恶",
        "neutral": "平静"
    }
    
    def __init__(self, prototxt_path: str = None, model_path: str = None):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        models_dir = os.path.join(base_dir, "models")
        
        if prototxt_path is None:
            prototxt_path = os.path.join(models_dir, "emotion_deploy.prototxt")
        if model_path is None:
            model_path = os.path.join(models_dir, "emotion.caffemodel")
        
        self.prototxt_path = prototxt_path
        self.model_path = model_path
        self.net = None
        
        # 输入尺寸
        self.input_size = (48, 48)  # 模型使用 48x48 灰度图
        
    def load_model(self) -> bool:
        """加载 Caffe 模型"""
        if not os.path.exists(self.prototxt_path) or not os.path.exists(self.model_path):
            print(f"模型文件不存在:")
            print(f"  prototxt: {self.prototxt_path}")
            print(f"  caffemodel: {self.model_path}")
            print("\n请下载模型文件:")
            print("1. 访问: https://github.com/petercunha/EmotionRecognition")
            print("2. 下载 emotion_deploy.prototxt 和 emotion.caffemodel")
            print(f"3. 放到: {os.path.dirname(self.prototxt_path)}")
            print("\n临时使用模拟模式...")
            return False
        
        try:
            # 加载 Caffe 模型
            self.net = cv2.dnn.readNetFromCaffe(
                self.prototxt_path,
                self.model_path
            )
            
            # 使用 CPU 推理
            self.net.setPreferableBackend(cv2.dnn.DNN_BACKEND_DEFAULT)
            self.net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)
            
            print(f"OpenCV DNN 情绪识别模型加载成功")
            return True
            
        except Exception as e:
            print(f"加载模型失败: {e}")
            return False
    
    def preprocess(self, face_img: np.ndarray) -> np.ndarray:
        """
        预处理人脸图像
        
        Args:
            face_img: 人脸区域图像 (BGR 格式)
            
        Returns:
            blob 格式的输入
        """
        # 转换为灰度图
        if len(face_img.shape) == 3:
            gray = cv2.cvtColor(face_img, cv2.COLOR_BGR2GRAY)
        else:
            gray = face_img
        
        # 调整大小为 48x48
        resized = cv2.resize(gray, self.input_size)
        
        # 创建 blob
        # 参数: (图像, 缩放因子, 目标尺寸, 均值, 是否交换 R B 通道, 是否裁剪)
        blob = cv2.dnn.blobFromImage(
            resized,
            scalefactor=1.0 / 255.0,
            size=self.input_size,
            mean=(0, 0, 0),
            swapRB=False,
            crop=False
        )
        
        return blob
    
    def recognize(self, face_img: np.ndarray) -> EmotionResult:
        """
        识别情绪
        
        Args:
            face_img: 人脸区域图像
            
        Returns:
            情绪识别结果
        """
        if self.net is None:
            # 模拟模式
            return self._mock_recognize(face_img)
        
        try:
            # 预处理
            blob = self.preprocess(face_img)
            
            # 设置输入
            self.net.setInput(blob)
            
            # 推理
            outputs = self.net.forward()
            
            # 获取概率
            probabilities = outputs[0]
            
            # Softmax（如果输出不是概率）
            exp_probs = np.exp(probabilities - np.max(probabilities))
            probabilities = exp_probs / np.sum(exp_probs)
            
            # 构建结果
            all_emotions = {
                label: float(prob) 
                for label, prob in zip(self.EMOTION_LABELS, probabilities)
            }
            
            # 获取主导情绪
            max_idx = np.argmax(probabilities)
            dominant_emotion = self.EMOTION_LABELS[max_idx]
            confidence = float(probabilities[max_idx])
            
            return EmotionResult(
                emotion=dominant_emotion,
                confidence=confidence,
                all_emotions=all_emotions
            )
            
        except Exception as e:
            print(f"识别失败: {e}")
            return self._mock_recognize(face_img)
    
    def _mock_recognize(self, face_img: np.ndarray) -> EmotionResult:
        """
        模拟情绪识别（用于没有模型时测试）
        """
        # 转换为灰度图
        if len(face_img.shape) == 3:
            gray = cv2.cvtColor(face_img, cv2.COLOR_BGR2GRAY)
        else:
            gray = face_img
        
        # 计算图像特征
        brightness = np.mean(gray) / 255.0
        contrast = np.std(gray) / 255.0
        
        # 基于特征生成模拟概率
        happy_prob = brightness * 0.7 + 0.1
        sad_prob = (1 - brightness) * 0.6 + 0.1
        surprised_prob = contrast * 0.6 + 0.1
        neutral_prob = 0.3
        angry_prob = 0.1
        fearful_prob = 0.1
        disgusted_prob = 0.1
        
        # 归一化
        total = sum([happy_prob, sad_prob, surprised_prob, neutral_prob, 
                     angry_prob, fearful_prob, disgusted_prob])
        
        all_emotions = {
            "happy": happy_prob / total,
            "sad": sad_prob / total,
            "surprised": surprised_prob / total,
            "neutral": neutral_prob / total,
            "angry": angry_prob / total,
            "fearful": fearful_prob / total,
            "disgusted": disgusted_prob / total
        }
        
        # 获取主导情绪
        dominant_emotion = max(all_emotions, key=all_emotions.get)
        confidence = all_emotions[dominant_emotion]
        
        return EmotionResult(
            emotion=dominant_emotion,
            confidence=confidence,
            all_emotions=all_emotions
        )


# 全局识别器实例
opencv_emotion_recognizer = OpenCVEmotionRecognizer()
