"""
推理引擎 - 后端持续运行的情绪识别服务
支持输出:
  1. 离散情绪 (8类)
  2. 二维情感 (Valence-Arousal)
  3. 三维情感 (PAD: Pleasure-Arousal-Dominance)
"""
import cv2
import numpy as np
import threading
import time
import asyncio
from typing import Dict, List, Callable, Optional
from datetime import datetime
from dataclasses import dataclass, asdict
import json

from app.services.video_stream import video_manager, VideoStream
from app.services.face_detection import face_detector
from app.services.emotion_recognition import emotion_recognizer
from app.services.yolo_face_detector import yolo_face_detector, FaceBox
from app.services.onnx_emotion_recognizer import onnx_emotion_recognizer
from app.services.opencv_emotion_recognizer import opencv_emotion_recognizer
from app.services.hsemotion_recognizer import hsemotion_recognizer
from app.services.data_store import data_store
from app.services.performance_monitor import performance_monitor


@dataclass
class FaceResult:
    """人脸检测结果 (含离散+连续情绪)"""
    face_id: str
    camera_id: str
    box: Dict[str, int]  # x, y, width, height
    confidence: float
    expressions: Dict[str, float]    # 离散情绪概率
    dominant_emotion: str
    emotion_confidence: float
    # 二维情感模型 (Valence-Arousal)
    valence: float       # 效价: -1 ~ +1
    arousal: float       # 唤醒度: -1 ~ +1
    # 三维情感模型 (PAD)
    pleasure: float      # 愉悦度: -1 ~ +1
    pad_arousal: float   # 唤醒度: -1 ~ +1
    dominance: float     # 支配度: -1 ~ +1
    timestamp: str

    def to_dict(self):
        return asdict(self)


@dataclass
class InferenceFrame:
    """推理帧数据"""
    camera_id: str
    frame_id: int
    timestamp: str
    faces: List[FaceResult]
    frame_base64: Optional[str] = None  # 可选的图像数据


class InferenceEngine:
    """
    推理引擎 - 持续运行的后台服务
    1. 从视频流获取帧
    2. 人脸检测
    3. 情绪识别 (离散 + 2D VA + 3D PAD)
    4. 数据存储
    5. 推送结果
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._initialized = True
        self.is_running = False
        self.inference_thread: Optional[threading.Thread] = None
        self.callbacks: List[Callable] = []
        self.frame_callbacks: List[Callable] = []
        self.inference_interval = 0.1  # 100ms 推理一次 (10 FPS)
        self.active_cameras: Dict[str, str] = {}  # camera_id -> stream_id

        # 当前使用的情绪识别器类型
        self.emotion_recognizer_type = "mock"

        # 统计信息
        self.stats = {
            "total_frames": 0,
            "total_faces": 0,
            "inference_time_ms": 0,
            "fps": 0
        }

    def register_callback(self, callback: Callable):
        """注册结果回调函数"""
        self.callbacks.append(callback)

    def unregister_callback(self, callback: Callable):
        """注销回调函数"""
        if callback in self.callbacks:
            self.callbacks.remove(callback)

    def register_frame_callback(self, callback: Callable):
        """注册帧回调（用于视频流推送）"""
        self.frame_callbacks.append(callback)

    def unregister_frame_callback(self, callback: Callable):
        """注销帧回调"""
        if callback in self.frame_callbacks:
            self.frame_callbacks.remove(callback)

    def start(self):
        """启动推理引擎"""
        if self.is_running:
            print("推理引擎已在运行")
            return

        # 加载模型
        print("正在加载推理模型...")

        # 尝试加载 YOLOv8-face ONNX 模型 (人脸检测)
        yolo_loaded = yolo_face_detector.load_model()
        if not yolo_loaded:
            print("YOLOv8-face 模型未加载，使用备用检测器")
            face_detector.load_model()

        # 尝试加载情绪识别模型 (优先级: HSEmotion > OpenCV DNN > ONNX > 备用)
        hsemotion_loaded = hsemotion_recognizer.load_model()
        if hsemotion_loaded:
            self.emotion_recognizer_type = "hsemotion"
            print("使用 HSEmotion 多任务模型 (离散情绪 + Valence-Arousal)")
        else:
            opencv_emotion_loaded = opencv_emotion_recognizer.load_model()
            if opencv_emotion_loaded:
                self.emotion_recognizer_type = "opencv"
                print("使用 OpenCV DNN 情绪模型 (仅离散情绪)")
            else:
                onnx_emotion_loaded = onnx_emotion_recognizer.load_model()
                if onnx_emotion_loaded:
                    self.emotion_recognizer_type = "onnx"
                    print("使用 ONNX 情绪模型 (仅离散情绪)")
                else:
                    self.emotion_recognizer_type = "mock"
                    emotion_recognizer.load_model()
                    print("使用模拟情绪识别器")

        self.is_running = True
        self.inference_thread = threading.Thread(target=self._inference_loop)
        self.inference_thread.daemon = True
        self.inference_thread.start()

        print(f"推理引擎已启动 (情绪识别器: {self.emotion_recognizer_type})")

    def stop(self):
        """停止推理引擎"""
        self.is_running = False
        if self.inference_thread:
            self.inference_thread.join(timeout=2)
        print("推理引擎已停止")

    def add_camera(self, source = 0, name: str = "默认摄像头", camera_id: str = "") -> str:
        """添加摄像头 (source: int=USB索引, str=RTSP URL)"""
        print(f"正在添加摄像头: {name}, source={source}")

        # 创建视频流
        cid = video_manager.create_stream(source, name, camera_id=camera_id)
        print(f"视频流已创建: {cid}")

        # 启动视频流
        if video_manager.start_stream(cid):
            self.active_cameras[cid] = cid
            print(f"摄像头 {name} ({cid}) 已添加并启动")

            # 等待几帧确保摄像头正常工作
            time.sleep(0.5)
            stream = video_manager.get_stream(cid)
            if stream:
                frame = stream.get_frame()
                if frame is not None:
                    print(f"摄像头 {cid} 可以正常读取帧，尺寸: {frame.shape}")
                else:
                    print(f"摄像头 {cid} 无法读取帧")

            return cid
        else:
            print(f"摄像头 {name} 启动失败")
            return None

    def remove_camera(self, camera_id: str):
        """移除摄像头"""
        if camera_id in self.active_cameras:
            from app.services.video_recorder import video_recorder
            video_recorder.stop_camera(camera_id)
            video_manager.remove_stream(camera_id)
            del self.active_cameras[camera_id]
            print(f"摄像头 {camera_id} 已移除")

    def _inference_loop(self):
        """推理主循环"""
        last_time = time.time()
        frame_count = 0
        
        # 降低日志噪声：关闭高频推理循环调试日志

        while self.is_running:
            loop_start = time.time()
            
            # 调试：打印活跃摄像头数量
            # if frame_count % 100 == 0:
            #     print(f"[推理循环] 活跃摄像头数: {len(self.active_cameras)}, IDs: {list(self.active_cameras.keys())}")

            # 对每个活跃摄像头进行推理
            for camera_id in list(self.active_cameras.keys()):
                self._process_camera(camera_id)

            # 计算FPS
            frame_count += 1
            current_time = time.time()
            if current_time - last_time >= 1.0:
                self.stats["fps"] = frame_count
                performance_monitor.record_fps(frame_count)
                frame_count = 0
                last_time = current_time

            # 控制推理频率
            elapsed = time.time() - loop_start
            if elapsed < self.inference_interval:
                time.sleep(self.inference_interval - elapsed)

    def _process_camera(self, camera_id: str):
        """处理单个摄像头的帧"""
        stream = video_manager.get_stream(camera_id)
        if not stream:
            performance_monitor.record_camera_cycle(camera_id, False)
            return

        frame = stream.get_frame()
        if frame is None:
            performance_monitor.record_camera_cycle(camera_id, False)
            return

        success = False
        inference_start = time.time()
        try:
            if yolo_face_detector.session is not None:
                detections = yolo_face_detector.detect(frame)
            else:
                detections = face_detector.detect(frame)

            faces_results = []
            for i, detection in enumerate(detections):
                if hasattr(detection, "box"):
                    box = detection.box
                else:
                    box = detection
                face_img = frame[box.y : box.y + box.height, box.x : box.x + box.width]

                if face_img.size == 0:
                    continue

                face_result = self._recognize_emotion(face_img, detection, i, camera_id)
                if face_result:
                    faces_results.append(face_result)
                    self._draw_face_info(frame, face_result)

                    from app.services.emotion_alert import emotion_alert

                    emotion_alert.process_face(
                        face_id=face_result.face_id,
                        camera_id=camera_id,
                        dominant_emotion=face_result.dominant_emotion,
                        confidence=face_result.emotion_confidence,
                        frame=face_img.copy(),
                    )

            inference_time = (time.time() - inference_start) * 1000
            self.stats["total_frames"] += 1
            self.stats["total_faces"] += len(faces_results)
            self.stats["inference_time_ms"] = inference_time
            performance_monitor.record_inference(
                inference_time, fps=None, camera_id=camera_id
            )

            from app.services.video_recorder import video_recorder

            stream_obj = video_manager.get_stream(camera_id)
            cam_name = stream_obj.name if stream_obj else camera_id
            video_recorder.write_frame(camera_id, frame, cam_name)

            inference_frame = InferenceFrame(
                camera_id=camera_id,
                frame_id=self.stats["total_frames"],
                timestamp=datetime.now().isoformat(),
                faces=faces_results,
            )

            data_store.save_inference_result(inference_frame)

            if self.frame_callbacks:
                _, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
                import base64

                inference_frame.frame_base64 = base64.b64encode(buffer).decode("utf-8")

            self._trigger_callbacks(inference_frame)
            success = True
        except Exception as e:
            print(f"处理摄像头 {camera_id} 时出错: {e}")
        finally:
            performance_monitor.record_camera_cycle(camera_id, success)

    def _recognize_emotion(self, face_img, detection, index, camera_id) -> Optional[FaceResult]:
        """
        对单个人脸进行情绪识别, 返回包含离散+2D+3D结果的 FaceResult
        """
        face_id = detection.face_id if hasattr(detection, 'face_id') else f"face_{index}"
        det_confidence = detection.confidence if hasattr(detection, 'confidence') else 0.9
        # YOLO返回的是FaceBox对象，face_detector返回的是FaceDetectionResult对象
        if hasattr(detection, 'box'):
            box = detection.box
        else:
            box = detection  # FaceBox对象本身

        # 默认 VA/PAD 值
        valence = 0.0
        arousal = 0.0
        pleasure = 0.0
        pad_arousal = 0.0
        dominance = 0.0

        if self.emotion_recognizer_type == "hsemotion":
            # HSEmotion: 直接输出 离散+VA, 计算 PAD
            result = hsemotion_recognizer.recognize(face_img)
            expressions = result.all_emotions
            dominant_emotion = result.emotion
            emotion_confidence = result.confidence
            valence = result.valence
            arousal = result.arousal
            pleasure = result.pleasure
            pad_arousal = result.pad_arousal
            dominance = result.dominance
            
            # 关闭高频识别结果日志

        elif self.emotion_recognizer_type == "opencv":
            result = opencv_emotion_recognizer.recognize(face_img)
            expressions = result.all_emotions
            dominant_emotion = result.emotion
            emotion_confidence = result.confidence
            # OpenCV 模型只有离散情绪, 用 PAD 映射计算 VA
            valence, arousal, dominance = self._compute_va_pad_from_discrete(expressions)
            pleasure = valence
            pad_arousal = arousal

        elif self.emotion_recognizer_type == "onnx":
            result = onnx_emotion_recognizer.recognize(face_img)
            expressions = result.all_emotions
            dominant_emotion = result.emotion
            emotion_confidence = result.confidence
            valence, arousal, dominance = self._compute_va_pad_from_discrete(expressions)
            pleasure = valence
            pad_arousal = arousal

        else:
            # Mock
            result = emotion_recognizer.recognize(face_img)
            expressions = result.all_emotions
            dominant_emotion = result.discrete.emotion
            emotion_confidence = result.discrete.confidence
            valence = result.continuous.pleasure
            arousal = result.continuous.arousal
            dominance = result.continuous.dominance
            pleasure = valence
            pad_arousal = arousal

        return FaceResult(
            face_id=face_id,
            camera_id=camera_id,
            box={
                "x": box.x,
                "y": box.y,
                "width": box.width,
                "height": box.height
            },
            confidence=det_confidence,
            expressions=expressions,
            dominant_emotion=dominant_emotion,
            emotion_confidence=emotion_confidence,
            valence=round(valence, 4),
            arousal=round(arousal, 4),
            pleasure=round(pleasure, 4),
            pad_arousal=round(pad_arousal, 4),
            dominance=round(dominance, 4),
            timestamp=datetime.now().isoformat()
        )

    def _compute_va_pad_from_discrete(self, expressions: Dict[str, float]):
        """
        当模型只有离散情绪输出时, 用 Russell-Mehrabian PAD 映射
        从情绪概率加权计算 Valence, Arousal, Dominance
        """
        PAD = hsemotion_recognizer.EMOTION_PAD

        valence = 0.0
        arousal = 0.0
        dominance = 0.0

        for emotion, prob in expressions.items():
            if emotion in PAD:
                valence += prob * PAD[emotion]["pleasure"]
                arousal += prob * PAD[emotion]["arousal"]
                dominance += prob * PAD[emotion]["dominance"]

        return (
            float(np.clip(valence, -1, 1)),
            float(np.clip(arousal, -1, 1)),
            float(np.clip(dominance, -1, 1))
        )

    def _draw_face_info(self, frame: np.ndarray, face: FaceResult):
        """在帧上绘制人脸信息 (含情绪 + VA)"""
        box = face.box

        # 确保坐标在有效范围内
        x = max(0, box["x"])
        y = max(0, box["y"])
        width = min(box["width"], frame.shape[1] - x)
        height = min(box["height"], frame.shape[0] - y)

        # 绘制人脸框
        color = self._get_emotion_color(face.dominant_emotion)
        cv2.rectangle(frame, (x, y), (x + width, y + height), color, 2)

        # 绘制情绪标签
        label = f"{face.dominant_emotion} {face.emotion_confidence:.2f}"
        cv2.putText(frame, label, (x, y - 10),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

        # 绘制 VA 值
        va_label = f"V:{face.valence:+.2f} A:{face.arousal:+.2f}"
        cv2.putText(frame, va_label,
                   (x, y + height + 18),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 1)

    def _get_emotion_color(self, emotion: str) -> tuple:
        """获取情绪对应的颜色"""
        colors = {
            "happy": (0, 255, 0),
            "sad": (255, 0, 0),
            "angry": (0, 0, 255),
            "neutral": (128, 128, 128),
            "fearful": (0, 255, 255),
            "surprised": (255, 255, 0),
            "disgusted": (255, 0, 255),
            "contempt": (180, 130, 70),
        }
        return colors.get(emotion, (255, 255, 255))

    def _trigger_callbacks(self, inference_frame: InferenceFrame):
        """触发所有回调函数"""
        for callback in self.callbacks:
            try:
                callback(inference_frame)
            except Exception as e:
                print(f"回调函数执行错误: {e}")

        for callback in self.frame_callbacks:
            try:
                callback(inference_frame)
            except Exception as e:
                print(f"帧回调执行错误: {e}")

    def get_stats(self) -> dict:
        """获取统计信息"""
        return self.stats.copy()

    def get_active_cameras(self) -> List[dict]:
        """获取活跃摄像头列表"""
        cameras = []
        for camera_id in self.active_cameras:
            stream = video_manager.get_stream(camera_id)
            if stream:
                cameras.append(stream.get_status())
        return cameras


# 全局推理引擎实例
inference_engine = InferenceEngine()
