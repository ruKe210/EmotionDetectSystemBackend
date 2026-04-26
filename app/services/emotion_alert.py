"""
情绪告警引擎 - 检测持续消极情绪并生成告警
"""
import cv2
import os
import uuid
import time
import threading
from datetime import datetime
from typing import Dict
from app.core.config import settings
from app.core.database import get_db_session
from app.models.db_models import Alert

# 告警截图目录
ALERT_IMG_DIR = os.path.join(settings.DATA_STORAGE_PATH, "alert_images")
os.makedirs(ALERT_IMG_DIR, exist_ok=True)

# 消极情绪列表
NEGATIVE_EMOTIONS = {"sad", "angry", "fearful", "disgusted"}

# 告警阈值（秒）：连续多少秒消极情绪触发告警
ALERT_THRESHOLD = 10

# 同一人脸两次告警的最小间隔（秒），避免重复告警
ALERT_COOLDOWN = 60

EMOTION_NAMES = {
    "sad": "悲伤", "angry": "愤怒", "fearful": "恐惧",
    "disgusted": "厌恶", "happy": "开心", "neutral": "中性",
    "surprised": "惊讶", "contempt": "蔑视",
}


class FaceEmotionTracker:
    """单个人脸的情绪追踪"""
    def __init__(self):
        self.negative_start = None  # 消极情绪开始时间
        self.current_emotion = None
        self.last_alert_time = 0  # 上次告警时间


class EmotionAlertEngine:
    """情绪告警引擎"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._trackers: Dict[str, FaceEmotionTracker] = {}
            cls._instance._lock = threading.Lock()
        return cls._instance

    def process_face(self, face_id: str, camera_id: str, dominant_emotion: str,
                     confidence: float, frame=None):
        """处理一个人脸的情绪数据，判断是否需要告警"""
        with self._lock:
            if face_id not in self._trackers:
                self._trackers[face_id] = FaceEmotionTracker()

            tracker = self._trackers[face_id]
            now = time.time()

            is_negative = dominant_emotion in NEGATIVE_EMOTIONS

            if is_negative:
                if tracker.negative_start is None:
                    # 开始计时
                    tracker.negative_start = now
                    tracker.current_emotion = dominant_emotion

                duration = now - tracker.negative_start

                # 超过阈值且冷却期已过
                if duration >= ALERT_THRESHOLD and (now - tracker.last_alert_time) >= ALERT_COOLDOWN:
                    self._create_alert(
                        face_id=face_id,
                        camera_id=camera_id,
                        emotion=dominant_emotion,
                        duration=int(duration),
                        confidence=confidence,
                        frame=frame,
                    )
                    tracker.last_alert_time = now
                    tracker.negative_start = now  # 重置计时
            else:
                # 非消极情绪，重置计时
                tracker.negative_start = None
                tracker.current_emotion = None

    def _create_alert(self, face_id, camera_id, emotion, duration, confidence, frame):
        """创建告警记录 + 保存截图"""
        alert_id = str(uuid.uuid4())[:8]
        image_path = None

        # 保存人脸截图
        if frame is not None:
            try:
                img_name = f"{alert_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                img_path = os.path.join(ALERT_IMG_DIR, img_name)
                cv2.imwrite(img_path, frame)
                image_path = f"/alert_images/{img_name}"
            except Exception as e:
                print(f"[告警] 截图保存失败: {e}")

        emotion_name = EMOTION_NAMES.get(emotion, emotion)

        # 写入数据库
        session = get_db_session()
        try:
            alert = Alert(
                id=alert_id,
                title=f"检测到持续{emotion_name}情绪",
                description=f"人脸 {face_id} 在摄像头 {camera_id} 上持续表现{emotion_name}情绪超过 {duration} 秒，置信度 {confidence:.1%}",
                device=camera_id,
                face_image=image_path,
                emotion=emotion,
                duration=duration,
                level="warning" if duration < 30 else "danger",
                type="emotion",
                status="pending",
                time=datetime.now(),
            )
            session.add(alert)
            session.commit()
            print(f"[告警] 已创建: {emotion_name} 持续 {duration}s (ID: {alert_id})")
        except Exception as e:
            session.rollback()
            print(f"[告警] 数据库写入失败: {e}")
        finally:
            session.close()

    def cleanup_stale(self, max_age=300):
        """清理超过 5 分钟没更新的追踪器"""
        with self._lock:
            now = time.time()
            stale = [fid for fid, t in self._trackers.items()
                     if t.negative_start and now - t.negative_start > max_age]
            for fid in stale:
                del self._trackers[fid]


emotion_alert = EmotionAlertEngine()
