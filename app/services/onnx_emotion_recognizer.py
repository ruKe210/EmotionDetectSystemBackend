"""
ONNX 情绪识别器
需要模型文件: backend/models/emotion_mobilenet.onnx
支持 7 类情绪: 开心、悲伤、愤怒、恐惧、惊讶、厌恶、平静
"""
import cv2
import numpy as np
import os
from typing import Dict, Tuple
from dataclasses import dataclass


@dataclass
class EmotionResult:
    """情绪识别结果"""
    emotion: str  # 主导情绪
    confidence: float  # 置信度
    all_emotions: Dict[str, float]  # 所有情绪的概率


class ONNXEmotionRecognizer:
    """
    ONNX 情绪识别器
    基于 MobileNet 或类似的轻量级网络
    """
    
    # 7 类情绪标签
    EMOTION_LABELS = [
        "happy",      # 开心
        "sad",        # 悲伤
        "angry",      # 愤怒
        "fearful",    # 恐惧
        "surprised",  # 惊讶
        "disgusted",  # 厌恶
        "neutral"     # 平静
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
    
    def __init__(self, model_path: str = None):
        if model_path is None:
            # 默认模型路径
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            model_path = os.path.join(base_dir, "models", "emotion_mobilenet.onnx")
        
        self.model_path = model_path
        self.session = None
        self.input_name = None
        self.input_shape = None
        
        # 输入尺寸（根据模型调整）
        self.input_size = (96, 112)  # 宽 x 高
        
    def load_model(self) -> bool:
        """加载 ONNX 模型"""
        if not os.path.exists(self.model_path):
            print(f"模型文件不存在: {self.model_path}")
            print("请下载或训练情绪识别模型:")
            print("1. 使用参考方案训练模型并导出为 ONNX")
            print("2. 或下载预训练模型")
            print(f"3. 放到: {self.model_path}")
            print("\n临时使用模拟模式...")
            return False
        
        try:
            # 创建 ONNX Runtime 会话
            import onnxruntime as ort
            
            # 使用 CPU 推理
            providers = ['CPUExecutionProvider']
            self.session = ort.InferenceSession(self.model_path, providers=providers)
            
            # 获取输入信息
            self.input_name = self.session.get_inputs()[0].name
            self.input_shape = self.session.get_inputs()[0].shape
            
            print(f"情绪识别模型加载成功")
            print(f"输入形状: {self.input_shape}")
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
            预处理后的张量
        """
        # 调整大小
        resized = cv2.resize(face_img, self.input_size)
        
        # 转换为 RGB（如果模型需要）
        rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
        
        # 归一化到 [0, 1]
        normalized = rgb.astype(np.float32) / 255.0
        
        # 标准化（使用 ImageNet 均值和标准差）
        mean = np.array([0.485, 0.456, 0.406])
        std = np.array([0.229, 0.224, 0.225])
        normalized = (normalized - mean) / std
        
        # 调整维度 (H, W, C) -> (C, H, W)
        transposed = np.transpose(normalized, (2, 0, 1))
        
        # 添加 batch 维度
        input_tensor = np.expand_dims(transposed, axis=0)
        
        return input_tensor
    
    def recognize(self, face_img: np.ndarray) -> EmotionResult:
        """
        识别情绪
        
        Args:
            face_img: 人脸区域图像
            
        Returns:
            情绪识别结果
        """
        if self.session is None:
            # 模拟模式：返回随机结果
            return self._mock_recognize(face_img)
        
        try:
            # 预处理
            input_tensor = self.preprocess(face_img)
            
            # 推理
            outputs = self.session.run(None, {self.input_name: input_tensor})
            
            # 解析输出
            logits = outputs[0][0]  # 假设输出是 logits
            
            # Softmax 转换为概率
            exp_logits = np.exp(logits - np.max(logits))
            probabilities = exp_logits / np.sum(exp_logits)
            
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
        
        基于简单的图像特征分析：
        - 亮度 -> 开心/悲伤
        - 对比度 -> 惊讶/平静
        """
        # 转换为灰度图
        gray = cv2.cvtColor(face_img, cv2.COLOR_BGR2GRAY)
        
        # 计算图像特征
        brightness = np.mean(gray) / 255.0
        contrast = np.std(gray) / 255.0
        
        # 基于特征生成模拟概率
        # 亮度高 -> 开心概率高
        # 对比度高 -> 惊讶概率高
        # 亮度低 -> 悲伤概率高
        
        happy_prob = brightness * 0.7 + 0.1
        sad_prob = (1 - brightness) * 0.6 + 0.1
        surprised_prob = contrast * 0.6 + 0.1
        neutral_prob = 0.3
        angry_prob = 0.1
        fearful_prob = 0.1
        disgusted_prob = 0.1
        
        # 归一化
        total = happy_prob + sad_prob + surprised_prob + neutral_prob + angry_prob + fearful_prob + disgusted_prob
        
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
onnx_emotion_recognizer = ONNXEmotionRecognizer()
