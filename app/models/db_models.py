from sqlalchemy import Column, Integer, String, DateTime, Double, Text, JSON, func
from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    email = Column(String(100))
    role = Column(String(20), nullable=False, default="user")
    status = Column(String(20), nullable=False, default="active")
    password = Column(String(255), nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "name": self.name,
            "email": self.email,
            "role": self.role,
            "status": self.status,
            "password": self.password,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class Camera(Base):
    __tablename__ = "cameras"

    id = Column(String(50), primary_key=True)
    name = Column(String(100), nullable=False)
    type = Column(String(20), nullable=False, default="usb")
    ip = Column(String(50))
    location = Column(String(200))
    status = Column(String(20), nullable=False, default="offline")
    resolution = Column(String(20), default="640x480")
    fps = Column(Integer, default=30)
    rtsp_url = Column(String(500))
    rtsp_username = Column(String(100))
    rtsp_password = Column(String(255))
    source_index = Column(Integer, default=0)
    last_seen = Column(DateTime)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "ip": self.ip,
            "location": self.location,
            "status": self.status,
            "resolution": self.resolution,
            "fps": self.fps,
            "rtsp_url": self.rtsp_url,
            "rtsp_username": self.rtsp_username,
            "source_index": self.source_index,
            "last_seen": self.last_seen,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class FaceHistory(Base):
    __tablename__ = "face_history"

    id = Column(String(50), primary_key=True)
    camera_id = Column(String(50))
    expressions = Column(JSON)
    dominant_emotion = Column(String(30))
    confidence = Column(Double)
    timestamp = Column(DateTime, nullable=False, server_default=func.now())
    valence = Column(Double, default=0)
    arousal = Column(Double, default=0)
    pleasure = Column(Double, default=0)
    pad_arousal = Column(Double, default=0)
    dominance = Column(Double, default=0)

    def to_dict(self):
        return {
            "id": self.id,
            "camera_id": self.camera_id,
            "expressions": self.expressions,
            "dominant_emotion": self.dominant_emotion,
            "confidence": self.confidence,
            "timestamp": self.timestamp,
            "valence": self.valence,
            "arousal": self.arousal,
            "pleasure": self.pleasure,
            "pad_arousal": self.pad_arousal,
            "dominance": self.dominance,
        }


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(String(50), primary_key=True)
    title = Column(String(200), nullable=False)
    description = Column(Text)
    device = Column(String(50))
    level = Column(String(20), nullable=False, default="info")
    type = Column(String(30), nullable=False, default="system")
    status = Column(String(20), nullable=False, default="pending")
    time = Column(DateTime, nullable=False, server_default=func.now())
    handled_by = Column(String(50))
    handle_note = Column(Text)
    handled_at = Column(DateTime)

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "device": self.device,
            "level": self.level,
            "type": self.type,
            "status": self.status,
            "time": self.time,
            "handled_by": self.handled_by,
            "handle_note": self.handle_note,
            "handled_at": self.handled_at,
        }


class Log(Base):
    __tablename__ = "logs"

    id = Column(String(50), primary_key=True)
    date = Column(String(20))
    time = Column(String(20))
    type = Column(String(30), nullable=False, default="system")
    operator = Column(String(50))
    content = Column(Text)
    ip = Column(String(50))
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    def to_dict(self):
        return {
            "id": self.id,
            "date": self.date,
            "time": self.time,
            "type": self.type,
            "operator": self.operator,
            "content": self.content,
            "ip": self.ip,
            "created_at": self.created_at,
        }


class SystemConfig(Base):
    __tablename__ = "system_config"

    id = Column(Integer, primary_key=True, autoincrement=True)
    config_key = Column(String(50), unique=True, nullable=False)
    config_value = Column(JSON, nullable=False)
    updated_at = Column(DateTime, onupdate=func.now(), server_default=func.now())
