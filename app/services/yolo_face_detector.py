"""
YOLOv8-face ONNX 人脸检测器
需要模型文件: backend/models/yolov8n-face.onnx
下载地址: https://github.com/akanametov/yolov8-face/releases
"""
import cv2
import numpy as np
import os
from typing import List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class FaceBox:
    """人脸框数据"""
    x: int
    y: int
    width: int
    height: int
    confidence: float
    face_id: str = ""


class YOLOFaceDetector:
    """
    YOLOv8-face ONNX 人脸检测器
    """
    
    def __init__(self, model_path: str = None):
        if model_path is None:
            # 默认模型路径
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            model_path = os.path.join(base_dir, "models", "yolov8n-face.onnx")
        
        self.model_path = model_path
        self.session = None
        self.input_name = None
        self.input_shape = None
        self.conf_threshold = 0.5
        self.iou_threshold = 0.45
        
        # YOLOv8-face 类别（只有人脸一个类别）
        self.classes = ['face']
        
    def load_model(self) -> bool:
        """加载 ONNX 模型"""
        if not os.path.exists(self.model_path):
            print(f"模型文件不存在: {self.model_path}")
            print("请下载模型文件:")
            print("1. 访问: https://github.com/akanametov/yolov8-face/releases")
            print("2. 下载 yolov8n-face.onnx")
            print(f"3. 放到: {self.model_path}")
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
            
            print(f"YOLOv8-face 模型加载成功")
            print(f"输入形状: {self.input_shape}")
            return True
            
        except Exception as e:
            print(f"加载模型失败: {e}")
            return False
    
    def preprocess(self, frame: np.ndarray) -> np.ndarray:
        """预处理图像"""
        # YOLOv8 使用 640x640 输入
        input_size = 640
        
        # 获取原始尺寸
        self.orig_h, self.orig_w = frame.shape[:2]
        
        # 计算缩放比例
        ratio = min(input_size / self.orig_w, input_size / self.orig_h)
        new_w = int(self.orig_w * ratio)
        new_h = int(self.orig_h * ratio)
        
        # 缩放图像
        resized = cv2.resize(frame, (new_w, new_h))
        
        # 创建 640x640 的画布，用灰色填充
        padded = np.full((input_size, input_size, 3), 114, dtype=np.uint8)
        
        # 将缩放后的图像放到画布中央
        x_offset = (input_size - new_w) // 2
        y_offset = (input_size - new_h) // 2
        padded[y_offset:y_offset + new_h, x_offset:x_offset + new_w] = resized
        
        # 记录填充信息，用于后处理
        self.ratio = ratio
        self.x_offset = x_offset
        self.y_offset = y_offset
        
        # 归一化并调整维度 (H, W, C) -> (C, H, W)
        padded = padded.astype(np.float32) / 255.0
        padded = np.transpose(padded, (2, 0, 1))
        padded = np.expand_dims(padded, axis=0)
        
        return padded
    
    def postprocess(self, outputs: np.ndarray) -> List[FaceBox]:
        """后处理检测结果"""
        # 根据实际输出形状 (1, 300, 21) 调整解析逻辑
        # YOLOv8-face 输出格式: [batch, num_boxes, box_info]
        # box_info 包含: x1, y1, x2, y2, conf, class_probs...
        
        # 关闭高频 YOLO 后处理调试日志
        
        # 尝试不同的解析方式
        if len(outputs.shape) == 3 and outputs.shape[2] == 21:
            # [batch, num_boxes, 21] 格式
            predictions = outputs[0]  # [300, 21]
            
            # YOLOv8-face 输出的是 xyxy 格式（左上角和右下角坐标）
            # 前4个值是: x1, y1, x2, y2
            # 第5个值是置信度
            boxes_xyxy = predictions[:, :4]  # [300, 4]
            scores = predictions[:, 4]       # [300]
            
        elif len(outputs.shape) == 3 and outputs.shape[1] == 5:
            # 标准格式 [batch, 5, num_anchors]
            predictions = np.squeeze(outputs).T  # [8400, 5]
            boxes = predictions[:, :4]
            scores = predictions[:, 4]
            # 将 xywh 转换为 xyxy
            boxes_xyxy = np.zeros_like(boxes)
            cx, cy, w, h = boxes[:, 0], boxes[:, 1], boxes[:, 2], boxes[:, 3]
            boxes_xyxy[:, 0] = cx - w / 2  # x1
            boxes_xyxy[:, 1] = cy - h / 2  # y1
            boxes_xyxy[:, 2] = cx + w / 2  # x2
            boxes_xyxy[:, 3] = cy + h / 2  # y2
        else:
            print(f"YOLO 输出格式异常: {outputs.shape}")
            return []
        
        # 过滤低置信度
        
        mask = scores > self.conf_threshold
        filtered_boxes_xyxy = boxes_xyxy[mask]
        filtered_scores = scores[mask]
        
        if len(filtered_boxes_xyxy) == 0:
            return []
        
        # 转换为原图坐标
        # 减去填充偏移量，然后除以缩放比例
        boxes_xyxy_orig = np.zeros_like(filtered_boxes_xyxy)
        boxes_xyxy_orig[:, 0] = (filtered_boxes_xyxy[:, 0] - self.x_offset) / self.ratio  # x1
        boxes_xyxy_orig[:, 1] = (filtered_boxes_xyxy[:, 1] - self.y_offset) / self.ratio  # y1
        boxes_xyxy_orig[:, 2] = (filtered_boxes_xyxy[:, 2] - self.x_offset) / self.ratio  # x2
        boxes_xyxy_orig[:, 3] = (filtered_boxes_xyxy[:, 3] - self.y_offset) / self.ratio  # y2
        
        
        # NMS 非极大值抑制
        indices = cv2.dnn.NMSBoxes(
            boxes_xyxy_orig.tolist(),
            filtered_scores.tolist(),
            self.conf_threshold,
            self.iou_threshold
        )
        
        faces = []
        if len(indices) > 0:
            indices = indices.flatten() if hasattr(indices, 'flatten') else indices
            
            for i, idx in enumerate(indices):
                box = boxes_xyxy_orig[idx]
                x1, y1, x2, y2 = box.astype(int)
                
                # 确保坐标在图像范围内
                x1 = max(0, x1)
                y1 = max(0, y1)
                x2 = min(self.orig_w, x2)
                y2 = min(self.orig_h, y2)
                
                face = FaceBox(
                    x=x1,
                    y=y1,
                    width=x2 - x1,
                    height=y2 - y1,
                    confidence=float(filtered_scores[idx]),
                    face_id=f"face_{i}"
                )
                faces.append(face)
        
        return faces
    
    def detect(self, frame: np.ndarray) -> List[FaceBox]:
        """
        检测人脸
        
        Args:
            frame: 输入图像 (BGR 格式)
            
        Returns:
            人脸框列表
        """
        if self.session is None:
            print("模型未加载，请先调用 load_model()")
            return []
        
        try:
            # 预处理
            input_tensor = self.preprocess(frame)
            
            # 推理
            outputs = self.session.run(None, {self.input_name: input_tensor})
            
            # 后处理
            faces = self.postprocess(outputs[0])
            
            return faces
            
        except Exception as e:
            print(f"检测失败: {e}")
            return []
    
    def draw_boxes(self, frame: np.ndarray, faces: List[FaceBox]) -> np.ndarray:
        """在图像上绘制人脸框"""
        result = frame.copy()
        
        for face in faces:
            # 绘制矩形框
            cv2.rectangle(
                result,
                (face.x, face.y),
                (face.x + face.width, face.y + face.height),
                (0, 255, 0),
                2
            )
            
            # 绘制置信度
            label = f"{face.confidence:.2f}"
            cv2.putText(
                result,
                label,
                (face.x, face.y - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (0, 255, 0),
                2
            )
        
        return result


# 全局检测器实例
yolo_face_detector = YOLOFaceDetector()
