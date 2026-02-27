"""
HSEmotion ONNX 情绪识别器
基于 HSE-asavchenko/face-emotion-recognition 项目
多任务模型: 同时输出离散情绪分类 + Valence-Arousal 连续值

模型下载地址:
  https://github.com/HSE-asavchenko/face-emotion-recognition
  在 models/affectnet_emotions/ 目录下载 enet_b0_8_va_mtl.onnx

支持输出:
  1. 离散情绪: 8类 (Anger, Contempt, Disgust, Fear, Happiness, Neutral, Sadness, Surprise)
  2. 二维情感: Valence (效价) + Arousal (唤醒度)
  3. 三维情感: Pleasure (愉悦度) + Arousal (唤醒度) + Dominance (支配度)
"""
import cv2
import numpy as np
import os
from typing import Dict, Optional, Tuple
from dataclasses import dataclass


@dataclass
class HSEmotionResult:
    """HSEmotion 完整情绪识别结果"""
    # 离散情绪
    emotion: str                    # 主导情绪
    confidence: float               # 主导情绪置信度
    all_emotions: Dict[str, float]  # 所有情绪的概率分布

    # 二维情感模型 (Valence-Arousal)
    valence: float   # 效价: -1(消极) ~ +1(积极)
    arousal: float   # 唤醒度: -1(平静) ~ +1(兴奋)

    # 三维情感模型 (PAD: Pleasure-Arousal-Dominance)
    pleasure: float   # 愉悦度: -1 ~ +1
    pad_arousal: float  # 唤醒度: -1 ~ +1
    dominance: float  # 支配度: -1 ~ +1


class HSEmotionRecognizer:
    """
    HSEmotion 多任务情绪识别器
    使用 EfficientNet-B0 骨干网络，同时预测离散情绪和连续VA值
    """

    # 8类情绪标签 (AffectNet 顺序)
    EMOTION_LABELS = [
        "angry",      # Anger     - 0
        "contempt",   # Contempt  - 1
        "disgusted",  # Disgust   - 2
        "fearful",    # Fear      - 3
        "happy",      # Happiness - 4
        "neutral",    # Neutral   - 5
        "sad",        # Sadness   - 6
        "surprised",  # Surprise  - 7
    ]

    # 情绪中文映射
    EMOTION_CN = {
        "angry":     "愤怒",
        "contempt":  "蔑视",
        "disgusted": "厌恶",
        "fearful":   "恐惧",
        "happy":     "开心",
        "neutral":   "平静",
        "sad":       "悲伤",
        "surprised": "惊讶",
    }

    # Russell-Mehrabian PAD 情绪坐标映射
    # 用于从离散情绪概率加权计算 Dominance (支配度)
    EMOTION_PAD = {
        "angry":     {"pleasure": -0.51, "arousal":  0.59, "dominance":  0.25},
        "contempt":  {"pleasure": -0.45, "arousal":  0.20, "dominance":  0.30},
        "disgusted": {"pleasure": -0.60, "arousal":  0.35, "dominance":  0.11},
        "fearful":   {"pleasure": -0.64, "arousal":  0.60, "dominance": -0.43},
        "happy":     {"pleasure":  0.81, "arousal":  0.51, "dominance":  0.46},
        "neutral":   {"pleasure":  0.00, "arousal":  0.00, "dominance":  0.00},
        "sad":       {"pleasure": -0.63, "arousal": -0.27, "dominance": -0.33},
        "surprised": {"pleasure":  0.40, "arousal":  0.67, "dominance": -0.13},
    }

    def __init__(self, model_path: str = None):
        if model_path is None:
            # 模型路径: backend/app/models/enet_b0_8_va_mtl.onnx
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            model_path = os.path.join(base_dir, "models", "enet_b0_8_va_mtl.onnx")

        self.model_path = model_path
        self.session = None
        self.input_name = None
        self.input_shape = None

        # EfficientNet-B0 输入尺寸
        self.input_size = (224, 224)

        # ImageNet 归一化参数
        self.mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
        self.std = np.array([0.229, 0.224, 0.225], dtype=np.float32)

    def load_model(self) -> bool:
        """加载 ONNX 模型"""
        if not os.path.exists(self.model_path):
            print(f"HSEmotion 模型文件不存在: {self.model_path}")
            print("\n请下载模型文件:")
            print("1. 访问: https://github.com/HSE-asavchenko/face-emotion-recognition")
            print("2. 下载 models/affectnet_emotions/enet_b0_8_va_mtl.onnx")
            print(f"3. 放到: {os.path.dirname(self.model_path)}")
            print("\n临时使用模拟模式...")
            return False

        try:
            import onnxruntime as ort

            providers = ['CPUExecutionProvider']
            self.session = ort.InferenceSession(self.model_path, providers=providers)

            self.input_name = self.session.get_inputs()[0].name
            self.input_shape = self.session.get_inputs()[0].shape

            # 获取输出信息
            outputs = self.session.get_outputs()
            output_names = [o.name for o in outputs]
            output_shapes = [o.shape for o in outputs]

            print(f"HSEmotion 模型加载成功")
            print(f"  输入: {self.input_name} {self.input_shape}")
            print(f"  输出: {list(zip(output_names, output_shapes))}")
            print(f"  功能: 8类离散情绪 + Valence-Arousal 连续值")
            return True

        except ImportError:
            print("需要安装 onnxruntime: pip install onnxruntime")
            return False
        except Exception as e:
            print(f"HSEmotion 模型加载失败: {e}")
            return False

    def preprocess(self, face_img: np.ndarray) -> np.ndarray:
        """
        预处理人脸图像

        Args:
            face_img: 人脸区域图像 (BGR 格式)

        Returns:
            预处理后的输入张量 [1, 3, 224, 224]
        """
        # BGR -> RGB
        if len(face_img.shape) == 3 and face_img.shape[2] == 3:
            rgb = cv2.cvtColor(face_img, cv2.COLOR_BGR2RGB)
        else:
            rgb = cv2.cvtColor(face_img, cv2.COLOR_GRAY2RGB)

        # 调整大小到 224x224
        resized = cv2.resize(rgb, self.input_size, interpolation=cv2.INTER_LINEAR)

        # 归一化到 [0, 1] 并用 ImageNet 均值/标准差标准化
        normalized = resized.astype(np.float32) / 255.0
        normalized = (normalized - self.mean) / self.std

        # HWC -> CHW
        transposed = np.transpose(normalized, (2, 0, 1))

        # 添加 batch 维度
        input_tensor = np.expand_dims(transposed, axis=0)

        return input_tensor

    def recognize(self, face_img: np.ndarray) -> HSEmotionResult:
        """
        识别情绪 (离散 + 连续)

        Args:
            face_img: 人脸区域图像

        Returns:
            完整情绪识别结果 (离散 + 2D + 3D)
        """
        if self.session is None:
            return self._mock_recognize(face_img)

        try:
            # 预处理
            input_tensor = self.preprocess(face_img)

            # 推理
            outputs = self.session.run(None, {self.input_name: input_tensor})

            # 解析输出
            # enet_b0_8_va_mtl 输出: [1, 10] (8 emotions + 2 VA)
            raw_output = outputs[0][0]

            # 分离情绪logits和VA值
            emotion_logits = raw_output[:8]
            valence = float(np.clip(raw_output[8], -1, 1))
            arousal = float(np.clip(raw_output[9], -1, 1))

            # Softmax 得到情绪概率
            exp_logits = np.exp(emotion_logits - np.max(emotion_logits))
            probabilities = exp_logits / np.sum(exp_logits)

            # 构建离散情绪结果
            all_emotions = {}
            for label, prob in zip(self.EMOTION_LABELS, probabilities):
                all_emotions[label] = float(prob)

            # 主导情绪
            max_idx = np.argmax(probabilities)
            dominant_emotion = self.EMOTION_LABELS[max_idx]
            confidence = float(probabilities[max_idx])

            # 计算 Dominance (支配度) - 使用情绪概率加权的 PAD 映射
            dominance = self._compute_dominance(all_emotions)

            return HSEmotionResult(
                emotion=dominant_emotion,
                confidence=confidence,
                all_emotions=all_emotions,
                valence=valence,
                arousal=arousal,
                pleasure=valence,           # Pleasure ≈ Valence
                pad_arousal=arousal,         # PAD-Arousal = Arousal
                dominance=dominance,
            )

        except Exception as e:
            print(f"HSEmotion 识别失败: {e}")
            import traceback
            traceback.print_exc()
            return self._mock_recognize(face_img)

    def _compute_dominance(self, all_emotions: Dict[str, float]) -> float:
        """
        使用 Russell-Mehrabian PAD 映射, 从离散情绪概率加权计算 Dominance

        Args:
            all_emotions: 情绪概率字典

        Returns:
            dominance 值 [-1, 1]
        """
        dominance = 0.0
        for emotion, prob in all_emotions.items():
            if emotion in self.EMOTION_PAD:
                dominance += prob * self.EMOTION_PAD[emotion]["dominance"]

        return float(np.clip(dominance, -1, 1))

    def _mock_recognize(self, face_img: np.ndarray) -> HSEmotionResult:
        """
        模拟情绪识别 (当模型不可用时)
        基于图像亮度和对比度特征生成模拟结果
        """
        # 转灰度
        if len(face_img.shape) == 3:
            gray = cv2.cvtColor(face_img, cv2.COLOR_BGR2GRAY)
        else:
            gray = face_img

        # 图像特征
        brightness = np.mean(gray) / 255.0
        contrast = np.std(gray) / 255.0

        # 模拟离散情绪概率
        happy_prob = brightness * 0.7 + 0.1
        sad_prob = (1 - brightness) * 0.5 + 0.05
        surprised_prob = contrast * 0.5 + 0.05
        neutral_prob = 0.25
        angry_prob = (1 - brightness) * 0.3 + 0.05
        fearful_prob = contrast * 0.3 + 0.05
        disgusted_prob = 0.08
        contempt_prob = 0.05

        total = (happy_prob + sad_prob + surprised_prob + neutral_prob +
                 angry_prob + fearful_prob + disgusted_prob + contempt_prob)

        all_emotions = {
            "angry":     angry_prob / total,
            "contempt":  contempt_prob / total,
            "disgusted": disgusted_prob / total,
            "fearful":   fearful_prob / total,
            "happy":     happy_prob / total,
            "neutral":   neutral_prob / total,
            "sad":       sad_prob / total,
            "surprised": surprised_prob / total,
        }

        dominant_emotion = max(all_emotions, key=all_emotions.get)
        confidence = all_emotions[dominant_emotion]

        # 模拟 VA 值 (基于图像特征)
        valence = float(np.clip(brightness * 2 - 1, -1, 1))
        arousal = float(np.clip(contrast * 2 - 0.3, -1, 1))

        # 计算 dominance
        dominance = self._compute_dominance(all_emotions)

        return HSEmotionResult(
            emotion=dominant_emotion,
            confidence=confidence,
            all_emotions=all_emotions,
            valence=valence,
            arousal=arousal,
            pleasure=valence,
            pad_arousal=arousal,
            dominance=dominance,
        )

    def get_model_info(self) -> Dict:
        """获取模型信息"""
        return {
            "model_name": "HSEmotion (EfficientNet-B0 Multi-Task)",
            "model_file": "enet_b0_8_va_mtl.onnx",
            "is_loaded": self.session is not None,
            "input_size": f"{self.input_size[0]}x{self.input_size[1]}",
            "emotions": self.EMOTION_LABELS,
            "supports_discrete": True,
            "supports_valence_arousal": True,
            "supports_pad": True,
            "source": "https://github.com/HSE-asavchenko/face-emotion-recognition",
        }


# 全局识别器实例
hsemotion_recognizer = HSEmotionRecognizer()
