from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class LogEntry(BaseModel):
    id: str
    date: str
    time: str
    type: str  # operation, error, system
    operator: Optional[str] = None
    content: str
    ip: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class LogQuery(BaseModel):
    type: Optional[str] = None
    date: Optional[str] = None
    search: Optional[str] = None
    page: int = 1
    pageSize: int = 10