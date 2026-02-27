import json
import os
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import asdict
import random


class MockDataStore:
    """
    模拟数据存储 - 用于开发测试
    后续可以替换为真实的数据库(MySQL/Redis)
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        # 内存存储
        self.users: Dict[str, Any] = {}
        self.cameras: Dict[str, Any] = {}
        self.face_history: List[Dict] = []
        self.alerts: List[Dict] = []
        self.logs: List[Dict] = []
        self.system_config: Dict = {}
        
        # 初始化默认数据
        self._init_default_data()
        self._initialized = True
    
    def _init_default_data(self):
        """初始化默认数据"""
        # 默认管理员用户
        self.users["admin"] = {
            "id": 1,
            "username": "admin",
            "name": "管理员",
            "email": "admin@example.com",
            "role": "admin",
            "status": "active",
            "password": "admin123",  # 明文存储仅用于测试
            "created_at": datetime.now(),
            "updated_at": None
        }
        
        # 默认摄像头配置
        self.system_config = {
            "video": {
                "cameraId": "0",
                "resolution": "640x480",
                "fps": 30,
                "duration": 60
            },
            "recognition": {
                "modelType": "cnn_lstm",
                "delayThreshold": 200,
                "accuracyThreshold": 0.85,
                "emotionChangeThreshold": 0.1
            },
            "storage": {
                "path": "./data",
                "period": 30,
                "autoBackup": True,
                "backupFrequency": "daily"
            },
            "permission": {
                "role": "admin",
                "permissions": ["read", "write", "delete", "config"]
            }
        }
        
        # 生成一些模拟的摄像头数据
        for i in range(3):
            camera_id = f"cam_{i+1}"
            self.cameras[camera_id] = {
                "id": camera_id,
                "name": f"摄像头 {i+1}",
                "type": "usb" if i == 0 else "ip",
                "ip": f"192.168.1.{100+i}" if i > 0 else None,
                "location": f"位置 {i+1}",
                "status": "online" if i == 0 else "offline",
                "resolution": "640x480",
                "fps": 30,
                "last_seen": datetime.now() if i == 0 else None,
                "created_at": datetime.now(),
                "updated_at": None
            }
        
        # 生成一些模拟的历史数据
        emotions = ["happy", "sad", "angry", "fearful", "surprised", "neutral", "disgusted", "contempt"]
        for i in range(100):
            dominant = random.choice(emotions)
            self.face_history.append({
                "id": f"face_{i}",
                "camera_id": random.choice(list(self.cameras.keys())),
                "expressions": {
                    "happy": random.random(),
                    "sad": random.random(),
                    "angry": random.random(),
                    "neutral": random.random(),
                    "fearful": random.random(),
                    "surprised": random.random(),
                    "disgusted": random.random(),
                    "contempt": random.random() * 0.3,
                },
                "dominant_emotion": dominant,
                "confidence": random.uniform(0.8, 0.99),
                "timestamp": datetime.now() - timedelta(minutes=random.randint(0, 1440)),
                # 二维情感
                "valence": round(random.uniform(-1, 1), 4),
                "arousal": round(random.uniform(-1, 1), 4),
                # 三维情感
                "pleasure": round(random.uniform(-1, 1), 4),
                "pad_arousal": round(random.uniform(-1, 1), 4),
                "dominance": round(random.uniform(-1, 1), 4),
            })
        
        # 生成一些模拟告警
        for i in range(20):
            self.alerts.append({
                "id": f"alert_{i}",
                "title": f"告警 {i+1}",
                "description": f"这是告警 {i+1} 的描述",
                "device": random.choice(list(self.cameras.keys())),
                "level": random.choice(["info", "warning", "danger"]),
                "type": random.choice(["system", "emotion", "device"]),
                "status": random.choice(["pending", "handled", "ignored"]),
                "time": datetime.now() - timedelta(hours=random.randint(0, 48)),
                "handled_by": None,
                "handle_note": None,
                "handled_at": None
            })
        
        # 生成一些模拟日志
        log_types = ["operation", "error", "system"]
        for i in range(50):
            self.logs.append({
                "id": f"log_{i}",
                "date": (datetime.now() - timedelta(days=random.randint(0, 7))).strftime("%Y-%m-%d"),
                "time": datetime.now().strftime("%H:%M:%S"),
                "type": random.choice(log_types),
                "operator": random.choice(["admin", "user1", "user2", None]),
                "content": f"日志记录 {i+1}",
                "ip": f"192.168.1.{random.randint(1, 255)}",
                "created_at": datetime.now() - timedelta(hours=random.randint(0, 168))
            })
    
    # ========== 用户相关 ==========
    def get_user(self, username: str) -> Optional[Dict]:
        return self.users.get(username)
    
    def get_user_by_id(self, user_id: int) -> Optional[Dict]:
        for user in self.users.values():
            if user["id"] == user_id:
                return user
        return None
    
    def get_all_users(self) -> List[Dict]:
        return list(self.users.values())
    
    def create_user(self, user_data: Dict) -> Dict:
        user_id = len(self.users) + 1
        user_data["id"] = user_id
        user_data["created_at"] = datetime.now()
        user_data["updated_at"] = None
        self.users[user_data["username"]] = user_data
        return user_data
    
    def update_user(self, username: str, user_data: Dict) -> Optional[Dict]:
        if username not in self.users:
            return None
        self.users[username].update(user_data)
        self.users[username]["updated_at"] = datetime.now()
        return self.users[username]
    
    def delete_user(self, username: str) -> bool:
        if username in self.users:
            del self.users[username]
            return True
        return False
    
    # ========== 摄像头相关 ==========
    def get_camera(self, camera_id: str) -> Optional[Dict]:
        return self.cameras.get(camera_id)
    
    def get_all_cameras(self) -> List[Dict]:
        return list(self.cameras.values())
    
    def create_camera(self, camera_data: Dict) -> Dict:
        camera_id = str(uuid.uuid4())[:8]
        camera_data["id"] = camera_id
        camera_data["status"] = "offline"
        camera_data["last_seen"] = None
        camera_data["created_at"] = datetime.now()
        camera_data["updated_at"] = None
        self.cameras[camera_id] = camera_data
        return camera_data
    
    def update_camera(self, camera_id: str, camera_data: Dict) -> Optional[Dict]:
        if camera_id not in self.cameras:
            return None
        self.cameras[camera_id].update(camera_data)
        self.cameras[camera_id]["updated_at"] = datetime.now()
        return self.cameras[camera_id]
    
    def delete_camera(self, camera_id: str) -> bool:
        if camera_id in self.cameras:
            del self.cameras[camera_id]
            return True
        return False
    
    # ========== 人脸历史相关 ==========
    def add_face_detection(self, detection_data: Dict):
        self.face_history.append(detection_data)
        # 只保留最近1000条记录
        if len(self.face_history) > 1000:
            self.face_history = self.face_history[-1000:]
    
    def get_face_history(self, start_date: Optional[datetime] = None, 
                        end_date: Optional[datetime] = None,
                        emotion: Optional[str] = None,
                        device: Optional[str] = None,
                        page: int = 1, page_size: int = 10) -> tuple:
        results = self.face_history
        
        if start_date:
            results = [r for r in results if r["timestamp"] >= start_date]
        if end_date:
            results = [r for r in results if r["timestamp"] <= end_date]
        if emotion:
            results = [r for r in results if r["dominant_emotion"] == emotion]
        if device:
            results = [r for r in results if r["camera_id"] == device]
        
        # 按时间倒序
        results = sorted(results, key=lambda x: x["timestamp"], reverse=True)
        
        total = len(results)
        start = (page - 1) * page_size
        end = start + page_size
        return results[start:end], total
    
    def get_emotion_distribution(self, minutes: int = 5) -> Dict[str, int]:
        """获取情绪分布统计"""
        distribution = {}
        cutoff_time = datetime.now() - timedelta(minutes=minutes)
        
        for record in self.face_history:
            if record["timestamp"] >= cutoff_time:
                emotion = record["dominant_emotion"]
                distribution[emotion] = distribution.get(emotion, 0) + 1
        
        # 如果没有数据，返回默认值
        if not distribution:
            distribution = {
                "happy": 0,
                "sad": 0,
                "angry": 0,
                "neutral": 0,
                "fearful": 0,
                "surprised": 0,
                "disgusted": 0
            }
        
        return distribution
    
    def save_inference_result(self, inference_frame):
        """保存推理结果 (含离散+2D+3D情绪数据)"""
        # 保存每个人脸数据
        for face in inference_frame.faces:
            self.add_face_detection({
                "id": face.face_id,
                "camera_id": face.camera_id,
                "expressions": face.expressions,
                "dominant_emotion": face.dominant_emotion,
                "confidence": face.confidence,
                "timestamp": datetime.now(),
                # 二维情感 (Valence-Arousal)
                "valence": getattr(face, 'valence', 0.0),
                "arousal": getattr(face, 'arousal', 0.0),
                # 三维情感 (PAD)
                "pleasure": getattr(face, 'pleasure', 0.0),
                "pad_arousal": getattr(face, 'pad_arousal', 0.0),
                "dominance": getattr(face, 'dominance', 0.0),
            })
    
    # ========== 告警相关 ==========
    def get_alerts(self, status: Optional[str] = None, 
                   alert_type: Optional[str] = None,
                   page: int = 1, page_size: int = 10) -> tuple:
        results = self.alerts
        
        if status:
            results = [r for r in results if r["status"] == status]
        if alert_type:
            results = [r for r in results if r["type"] == alert_type]
        
        # 按时间倒序
        results = sorted(results, key=lambda x: x["time"], reverse=True)
        
        total = len(results)
        start = (page - 1) * page_size
        end = start + page_size
        return results[start:end], total
    
    def get_alert(self, alert_id: str) -> Optional[Dict]:
        for alert in self.alerts:
            if alert["id"] == alert_id:
                return alert
        return None
    
    def create_alert(self, alert_data: Dict) -> Dict:
        alert_id = str(uuid.uuid4())[:8]
        alert_data["id"] = alert_id
        alert_data["time"] = datetime.now()
        alert_data["status"] = "pending"
        self.alerts.append(alert_data)
        return alert_data
    
    def update_alert(self, alert_id: str, alert_data: Dict) -> Optional[Dict]:
        for alert in self.alerts:
            if alert["id"] == alert_id:
                alert.update(alert_data)
                if alert_data.get("status") in ["handled", "ignored"]:
                    alert["handled_at"] = datetime.now()
                return alert
        return None
    
    # ========== 日志相关 ==========
    def add_log(self, log_data: Dict):
        log_data["id"] = str(uuid.uuid4())[:8]
        log_data["created_at"] = datetime.now()
        self.logs.append(log_data)
    
    def get_logs(self, log_type: Optional[str] = None,
                 date: Optional[str] = None,
                 search: Optional[str] = None,
                 page: int = 1, page_size: int = 10) -> tuple:
        results = self.logs
        
        if log_type:
            results = [r for r in results if r["type"] == log_type]
        if date:
            results = [r for r in results if r["date"] == date]
        if search:
            results = [r for r in results if search.lower() in r["content"].lower()]
        
        # 按时间倒序
        results = sorted(results, key=lambda x: x["created_at"], reverse=True)
        
        total = len(results)
        start = (page - 1) * page_size
        end = start + page_size
        return results[start:end], total
    
    def clear_logs(self):
        self.logs.clear()
    
    # ========== 系统配置相关 ==========
    def get_config(self) -> Dict:
        return self.system_config
    
    def update_config(self, config_data: Dict) -> Dict:
        self.system_config.update(config_data)
        return self.system_config
    
    # ========== 统计数据 ==========
    def get_stats(self) -> Dict:
        """获取系统统计数据"""
        online_cameras = sum(1 for c in self.cameras.values() if c["status"] == "online")
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_recognition = sum(1 for r in self.face_history if r["timestamp"] >= today)
        today_alerts = sum(1 for a in self.alerts if a["time"] >= today and a["status"] == "pending")
        
        return {
            "online_devices": online_cameras,
            "current_faces": random.randint(0, 5),  # 模拟当前人脸数
            "today_recognition": today_recognition,
            "today_alerts": today_alerts,
            "cpu_usage": random.uniform(20, 60),
            "memory_usage": random.uniform(30, 70),
            "uptime": 3600,  # 模拟运行1小时
            "emotion_distribution": self.get_emotion_distribution()
        }


# 全局数据存储实例
data_store = MockDataStore()