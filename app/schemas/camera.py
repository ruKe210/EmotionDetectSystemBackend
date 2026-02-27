from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class CameraBase(BaseModel):
    name: str
    type: str = "usb"  # usb, ip, file
    ip: Optional[str] = None
    location: Optional[str] = None
    resolution: str = "640x480"
    fps: int = 30


class CameraCreate(CameraBase):
    pass


class CameraUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    ip: Optional[str] = None
    location: Optional[str] = None
    status: Optional[str] = None
    resolution: Optional[str] = None
    fps: Optional[int] = None


class Camera(CameraBase):
    id: str
    status: str = "offline"  # online, offline, error
    last_seen: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True