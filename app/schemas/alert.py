from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class AlertBase(BaseModel):
    title: str
    description: Optional[str] = None
    device: str
    level: str = "info"  # info, warning, danger
    type: str = "system"  # system, emotion, device


class AlertCreate(AlertBase):
    pass


class AlertUpdate(BaseModel):
    status: Optional[str] = None  # pending, handled, ignored
    handled_by: Optional[str] = None
    handle_note: Optional[str] = None


class Alert(AlertBase):
    id: str
    status: str = "pending"
    time: datetime
    handled_by: Optional[str] = None
    handle_note: Optional[str] = None
    handled_at: Optional[datetime] = None

    class Config:
        from_attributes = True