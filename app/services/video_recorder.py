"""
视频录制服务 - 每分钟生成一段视频文件
"""
import cv2
import os
import uuid
import threading
import time
from datetime import datetime
from typing import Dict, Optional

from app.core.config import settings
from app.core.database import get_db_session
from app.models.db_models import VideoRecord


# 录制文件存储目录
RECORD_DIR = os.path.join(settings.DATA_STORAGE_PATH, "recordings")
os.makedirs(RECORD_DIR, exist_ok=True)

def _segment_duration_seconds() -> int:
    # 允许通过设置页动态修改分段时长，最小 10 秒
    return max(10, int(getattr(settings, "VIDEO_RECORD_SEGMENT_SECONDS", 60)))


class CameraRecorder:
    """单个摄像头的录制器"""

    def __init__(self, camera_id: str, camera_name: str, fps: int = 10):
        self.camera_id = camera_id
        self.camera_name = camera_name
        self.fps = fps
        self.writer: Optional[cv2.VideoWriter] = None
        self.current_record_id: Optional[str] = None
        self.current_file: Optional[str] = None
        self.segment_start: Optional[float] = None
        self.frame_count = 0
        self.first_frame_ts: Optional[float] = None
        self.last_frame_ts: Optional[float] = None
        self.width = 0
        self.height = 0
        self.lock = threading.Lock()

    def write_frame(self, frame):
        """写入一帧（由推理引擎调用）"""
        with self.lock:
            now = time.time()

            # 需要开新段
            if self.writer is None or (now - self.segment_start >= _segment_duration_seconds()):
                self._finish_segment()
                self._start_segment(frame)

            if self.writer is not None:
                self.writer.write(frame)
                self.frame_count += 1
                if self.first_frame_ts is None:
                    self.first_frame_ts = now
                self.last_frame_ts = now

    def _start_segment(self, frame):
        """开始新的录制段"""
        h, w = frame.shape[:2]
        self.width = w
        self.height = h

        record_id = str(uuid.uuid4())[:12]
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_name = f"{self.camera_id}_{ts}.webm"
        file_path = os.path.join(RECORD_DIR, file_name)

        # VP8 + WebM，浏览器原生支持
        fourcc = cv2.VideoWriter_fourcc(*'VP80')
        self.writer = cv2.VideoWriter(file_path, fourcc, self.fps, (w, h))

        if not self.writer.isOpened():
            # 回退到 H.264 MP4
            file_name = f"{self.camera_id}_{ts}.mp4"
            file_path = os.path.join(RECORD_DIR, file_name)
            fourcc = cv2.VideoWriter_fourcc(*'avc1')
            self.writer = cv2.VideoWriter(file_path, fourcc, self.fps, (w, h))

        if not self.writer.isOpened():
            # 最后回退到 mp4v
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            self.writer = cv2.VideoWriter(file_path, fourcc, self.fps, (w, h))

        if not self.writer.isOpened():
            print(f"[录制] 无法创建视频文件: {file_path}")
            self.writer = None
            return

        self.current_record_id = record_id
        self.current_file = file_path
        self.segment_start = time.time()
        self.frame_count = 0
        self.first_frame_ts = None
        self.last_frame_ts = None

        # 写入数据库
        session = get_db_session()
        try:
            record = VideoRecord(
                id=record_id,
                camera_id=self.camera_id,
                camera_name=self.camera_name,
                file_path=file_path,
                file_name=file_name,
                start_time=datetime.now(),
                fps=self.fps,
                resolution=f"{w}x{h}",
                status="recording",
            )
            session.add(record)
            session.commit()
        except Exception as e:
            session.rollback()
            print(f"[录制] 数据库写入失败: {e}")
        finally:
            session.close()

    def _finish_segment(self):
        """结束当前录制段"""
        if self.writer is not None:
            segment_real_duration = 0.0
            if self.first_frame_ts is not None and self.last_frame_ts is not None:
                segment_real_duration = max(0.0, self.last_frame_ts - self.first_frame_ts)
            adaptive_fps = self.fps
            if segment_real_duration > 0 and self.frame_count > 1:
                # 用实际到帧频率估算下一段录制 FPS，避免回放倍速
                estimated = self.frame_count / segment_real_duration
                adaptive_fps = max(1, min(int(getattr(settings, "VIDEO_FPS", 10)), int(round(estimated))))

            self.writer.release()
            self.writer = None

            # 更新数据库
            if self.current_record_id:
                session = get_db_session()
                try:
                    record = session.query(VideoRecord).filter(
                        VideoRecord.id == self.current_record_id
                    ).first()
                    if record:
                        record.end_time = datetime.now()
                        record.duration = int(time.time() - self.segment_start)
                        record.status = "completed"
                        record.fps = self.fps
                        try:
                            record.file_size = os.path.getsize(self.current_file)
                        except Exception:
                            pass
                        session.commit()
                except Exception as e:
                    session.rollback()
                    print(f"[录制] 更新记录失败: {e}")
                finally:
                    session.close()

            self.current_record_id = None
            self.current_file = None
            self.first_frame_ts = None
            self.last_frame_ts = None
            self.frame_count = 0
            self.fps = adaptive_fps

    def stop(self):
        """停止录制"""
        with self.lock:
            self._finish_segment()


class VideoRecorderManager:
    """视频录制管理器"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._recorders: Dict[str, CameraRecorder] = {}
        return cls._instance

    def get_recorder(self, camera_id: str, camera_name: str = "") -> CameraRecorder:
        fps = max(1, int(getattr(settings, "VIDEO_FPS", 10)))
        if camera_id not in self._recorders:
            self._recorders[camera_id] = CameraRecorder(camera_id, camera_name, fps=fps)
        recorder = self._recorders[camera_id]
        recorder.fps = fps
        return recorder

    def write_frame(self, camera_id: str, frame, camera_name: str = ""):
        recorder = self.get_recorder(camera_id, camera_name)
        recorder.write_frame(frame)

    def stop_all(self):
        for recorder in self._recorders.values():
            recorder.stop()
        self._recorders.clear()

    def stop_camera(self, camera_id: str):
        if camera_id in self._recorders:
            self._recorders[camera_id].stop()
            del self._recorders[camera_id]


video_recorder = VideoRecorderManager()
