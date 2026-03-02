import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

from sqlalchemy import desc, func
from app.core.database import get_db_session
from app.models.db_models import (
    User, Camera, FaceHistory, Alert, Log,
    SystemConfig as SystemConfigModel,
)


class DatabaseDataStore:
    """
    数据库数据存储 - 使用 MySQL + SQLAlchemy
    保持与原 MockDataStore 相同的接口
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    # ========== 用户相关 ==========
    def get_user(self, username: str) -> Optional[Dict]:
        session = get_db_session()
        try:
            user = session.query(User).filter(User.username == username).first()
            return user.to_dict() if user else None
        finally:
            session.close()

    def get_user_by_id(self, user_id: int) -> Optional[Dict]:
        session = get_db_session()
        try:
            user = session.query(User).filter(User.id == user_id).first()
            return user.to_dict() if user else None
        finally:
            session.close()

    def get_all_users(self) -> List[Dict]:
        session = get_db_session()
        try:
            users = session.query(User).all()
            return [u.to_dict() for u in users]
        finally:
            session.close()

    def create_user(self, user_data: Dict) -> Dict:
        session = get_db_session()
        try:
            user = User(
                username=user_data["username"],
                name=user_data.get("name", ""),
                email=user_data.get("email", ""),
                role=user_data.get("role", "user"),
                status=user_data.get("status", "active"),
                password=user_data.get("password", ""),
                created_at=datetime.now(),
            )
            session.add(user)
            session.commit()
            session.refresh(user)
            return user.to_dict()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def update_user(self, username: str, user_data: Dict) -> Optional[Dict]:
        session = get_db_session()
        try:
            user = session.query(User).filter(User.username == username).first()
            if not user:
                return None
            for key, value in user_data.items():
                if hasattr(user, key) and key not in ("id", "username"):
                    setattr(user, key, value)
            user.updated_at = datetime.now()
            session.commit()
            session.refresh(user)
            return user.to_dict()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def delete_user(self, username: str) -> bool:
        session = get_db_session()
        try:
            user = session.query(User).filter(User.username == username).first()
            if not user:
                return False
            session.delete(user)
            session.commit()
            return True
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    # ========== 摄像头相关 ==========
    def get_camera(self, camera_id: str) -> Optional[Dict]:
        session = get_db_session()
        try:
            camera = session.query(Camera).filter(Camera.id == camera_id).first()
            return camera.to_dict() if camera else None
        finally:
            session.close()

    def get_all_cameras(self) -> List[Dict]:
        session = get_db_session()
        try:
            cameras = session.query(Camera).all()
            return [c.to_dict() for c in cameras]
        finally:
            session.close()

    def create_camera(self, camera_data: Dict) -> Dict:
        session = get_db_session()
        try:
            camera_id = str(uuid.uuid4())[:8]
            camera = Camera(
                id=camera_id,
                name=camera_data.get("name", ""),
                type=camera_data.get("type", "usb"),
                ip=camera_data.get("ip"),
                location=camera_data.get("location", ""),
                status="offline",
                resolution=camera_data.get("resolution", "640x480"),
                fps=camera_data.get("fps", 30),
                created_at=datetime.now(),
            )
            session.add(camera)
            session.commit()
            session.refresh(camera)
            return camera.to_dict()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def update_camera(self, camera_id: str, camera_data: Dict) -> Optional[Dict]:
        session = get_db_session()
        try:
            camera = session.query(Camera).filter(Camera.id == camera_id).first()
            if not camera:
                return None
            for key, value in camera_data.items():
                if hasattr(camera, key) and key != "id":
                    setattr(camera, key, value)
            camera.updated_at = datetime.now()
            session.commit()
            session.refresh(camera)
            return camera.to_dict()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def delete_camera(self, camera_id: str) -> bool:
        session = get_db_session()
        try:
            camera = session.query(Camera).filter(Camera.id == camera_id).first()
            if not camera:
                return False
            session.delete(camera)
            session.commit()
            return True
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    # ========== 人脸历史相关 ==========
    def add_face_detection(self, detection_data: Dict):
        session = get_db_session()
        try:
            expressions = detection_data.get("expressions", {})
            if isinstance(expressions, dict):
                expressions_json = expressions
            else:
                expressions_json = {}

            face = FaceHistory(
                id=detection_data.get("id", str(uuid.uuid4())[:8]),
                camera_id=detection_data.get("camera_id"),
                expressions=expressions_json,
                dominant_emotion=detection_data.get("dominant_emotion"),
                confidence=detection_data.get("confidence"),
                timestamp=detection_data.get("timestamp", datetime.now()),
                valence=detection_data.get("valence", 0),
                arousal=detection_data.get("arousal", 0),
                pleasure=detection_data.get("pleasure", 0),
                pad_arousal=detection_data.get("pad_arousal", 0),
                dominance=detection_data.get("dominance", 0),
            )
            session.add(face)
            session.commit()
        except Exception:
            session.rollback()
        finally:
            session.close()

    def get_face_history(self, start_date: Optional[datetime] = None,
                         end_date: Optional[datetime] = None,
                         emotion: Optional[str] = None,
                         device: Optional[str] = None,
                         page: int = 1, page_size: int = 10) -> tuple:
        session = get_db_session()
        try:
            query = session.query(FaceHistory)

            if start_date:
                query = query.filter(FaceHistory.timestamp >= start_date)
            if end_date:
                query = query.filter(FaceHistory.timestamp <= end_date)
            if emotion:
                query = query.filter(FaceHistory.dominant_emotion == emotion)
            if device:
                query = query.filter(FaceHistory.camera_id == device)

            total = query.count()
            query = query.order_by(desc(FaceHistory.timestamp))
            offset = (page - 1) * page_size
            records = query.offset(offset).limit(page_size).all()

            return [r.to_dict() for r in records], total
        finally:
            session.close()

    def get_emotion_distribution(self, minutes: int = 5) -> Dict[str, int]:
        """获取情绪分布统计"""
        session = get_db_session()
        try:
            cutoff_time = datetime.now() - timedelta(minutes=minutes)
            results = (
                session.query(FaceHistory.dominant_emotion, func.count(FaceHistory.id))
                .filter(FaceHistory.timestamp >= cutoff_time)
                .group_by(FaceHistory.dominant_emotion)
                .all()
            )

            distribution = {emotion: count for emotion, count in results}

            if not distribution:
                distribution = {
                    "happy": 0, "sad": 0, "angry": 0, "neutral": 0,
                    "fearful": 0, "surprised": 0, "disgusted": 0,
                }

            return distribution
        finally:
            session.close()

    def save_inference_result(self, inference_frame):
        """保存推理结果 (含离散+2D+3D情绪数据)"""
        for face in inference_frame.faces:
            self.add_face_detection({
                "id": face.face_id,
                "camera_id": face.camera_id,
                "expressions": face.expressions,
                "dominant_emotion": face.dominant_emotion,
                "confidence": face.confidence,
                "timestamp": datetime.now(),
                "valence": getattr(face, 'valence', 0.0),
                "arousal": getattr(face, 'arousal', 0.0),
                "pleasure": getattr(face, 'pleasure', 0.0),
                "pad_arousal": getattr(face, 'pad_arousal', 0.0),
                "dominance": getattr(face, 'dominance', 0.0),
            })

    # ========== 告警相关 ==========
    def get_alerts(self, status: Optional[str] = None,
                   alert_type: Optional[str] = None,
                   page: int = 1, page_size: int = 10) -> tuple:
        session = get_db_session()
        try:
            query = session.query(Alert)

            if status:
                query = query.filter(Alert.status == status)
            if alert_type:
                query = query.filter(Alert.type == alert_type)

            total = query.count()
            query = query.order_by(desc(Alert.time))
            offset = (page - 1) * page_size
            records = query.offset(offset).limit(page_size).all()

            return [r.to_dict() for r in records], total
        finally:
            session.close()

    def get_alert(self, alert_id: str) -> Optional[Dict]:
        session = get_db_session()
        try:
            alert = session.query(Alert).filter(Alert.id == alert_id).first()
            return alert.to_dict() if alert else None
        finally:
            session.close()

    def create_alert(self, alert_data: Dict) -> Dict:
        session = get_db_session()
        try:
            alert_id = str(uuid.uuid4())[:8]
            alert = Alert(
                id=alert_id,
                title=alert_data.get("title", ""),
                description=alert_data.get("description", ""),
                device=alert_data.get("device"),
                level=alert_data.get("level", "info"),
                type=alert_data.get("type", "system"),
                status="pending",
                time=datetime.now(),
            )
            session.add(alert)
            session.commit()
            session.refresh(alert)
            return alert.to_dict()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def update_alert(self, alert_id: str, alert_data: Dict) -> Optional[Dict]:
        session = get_db_session()
        try:
            alert = session.query(Alert).filter(Alert.id == alert_id).first()
            if not alert:
                return None
            for key, value in alert_data.items():
                if hasattr(alert, key) and key != "id":
                    setattr(alert, key, value)
            session.commit()
            session.refresh(alert)
            return alert.to_dict()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    # ========== 日志相关 ==========
    def add_log(self, log_data: Dict):
        session = get_db_session()
        try:
            log = Log(
                id=str(uuid.uuid4())[:8],
                date=log_data.get("date"),
                time=log_data.get("time"),
                type=log_data.get("type", "system"),
                operator=log_data.get("operator"),
                content=log_data.get("content", ""),
                ip=log_data.get("ip", ""),
                created_at=datetime.now(),
            )
            session.add(log)
            session.commit()
        except Exception:
            session.rollback()
        finally:
            session.close()

    def get_logs(self, log_type: Optional[str] = None,
                 date: Optional[str] = None,
                 search: Optional[str] = None,
                 page: int = 1, page_size: int = 10) -> tuple:
        session = get_db_session()
        try:
            query = session.query(Log)

            if log_type:
                query = query.filter(Log.type == log_type)
            if date:
                query = query.filter(Log.date == date)
            if search:
                query = query.filter(Log.content.like(f"%{search}%"))

            total = query.count()
            query = query.order_by(desc(Log.created_at))
            offset = (page - 1) * page_size
            records = query.offset(offset).limit(page_size).all()

            return [r.to_dict() for r in records], total
        finally:
            session.close()

    def clear_logs(self):
        session = get_db_session()
        try:
            session.query(Log).delete()
            session.commit()
        except Exception:
            session.rollback()
        finally:
            session.close()

    # ========== 系统配置相关 ==========
    def get_config(self) -> Dict:
        session = get_db_session()
        try:
            configs = session.query(SystemConfigModel).all()
            result = {}
            for config in configs:
                result[config.config_key] = config.config_value
            return result
        finally:
            session.close()

    def update_config(self, config_data: Dict) -> Dict:
        session = get_db_session()
        try:
            for key, value in config_data.items():
                config = session.query(SystemConfigModel).filter(
                    SystemConfigModel.config_key == key
                ).first()
                if config:
                    config.config_value = value
                    config.updated_at = datetime.now()
                else:
                    config = SystemConfigModel(
                        config_key=key,
                        config_value=value,
                    )
                    session.add(config)
            session.commit()
            return self.get_config()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    # ========== 统计数据 ==========
    def get_stats(self) -> Dict:
        """获取系统统计数据"""
        session = get_db_session()
        try:
            online_cameras = session.query(Camera).filter(Camera.status == "online").count()

            today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            today_recognition = session.query(FaceHistory).filter(
                FaceHistory.timestamp >= today
            ).count()
            today_alerts = session.query(Alert).filter(
                Alert.time >= today, Alert.status == "pending"
            ).count()

            # 当前活跃人脸数（最近30秒的识别记录）
            recent_cutoff = datetime.now() - timedelta(seconds=30)
            current_faces = session.query(FaceHistory).filter(
                FaceHistory.timestamp >= recent_cutoff
            ).count()

            return {
                "online_devices": online_cameras,
                "current_faces": current_faces,
                "today_recognition": today_recognition,
                "today_alerts": today_alerts,
                "cpu_usage": self._get_cpu_usage(),
                "memory_usage": self._get_memory_usage(),
                "uptime": self._get_uptime(),
                "emotion_distribution": self.get_emotion_distribution(),
            }
        finally:
            session.close()

    def _get_cpu_usage(self):
        try:
            import psutil
            return psutil.cpu_percent(interval=0.1)
        except Exception:
            return 0

    def _get_memory_usage(self):
        try:
            import psutil
            return psutil.virtual_memory().percent
        except Exception:
            return 0

    def _get_uptime(self):
        try:
            import psutil
            import time
            return int(time.time() - psutil.boot_time())
        except Exception:
            return 0

    # ========== 兼容属性 ==========
    @property
    def cameras(self) -> Dict[str, Any]:
        """兼容旧代码中直接访问 data_store.cameras 的地方"""
        session = get_db_session()
        try:
            cameras = session.query(Camera).all()
            return {c.id: c.to_dict() for c in cameras}
        finally:
            session.close()

    @property
    def users(self) -> Dict[str, Any]:
        """兼容旧代码中直接访问 data_store.users 的地方"""
        session = get_db_session()
        try:
            users = session.query(User).all()
            return {u.username: u.to_dict() for u in users}
        finally:
            session.close()

    @property
    def face_history(self) -> List[Dict]:
        """兼容旧代码中直接访问 data_store.face_history 的地方"""
        session = get_db_session()
        try:
            records = session.query(FaceHistory).order_by(
                desc(FaceHistory.timestamp)
            ).limit(1000).all()
            return [r.to_dict() for r in records]
        finally:
            session.close()

    @property
    def alerts(self) -> List[Dict]:
        """兼容旧代码中直接访问 data_store.alerts 的地方"""
        session = get_db_session()
        try:
            records = session.query(Alert).order_by(desc(Alert.time)).all()
            return [r.to_dict() for r in records]
        finally:
            session.close()


# 全局数据存储实例
data_store = DatabaseDataStore()
