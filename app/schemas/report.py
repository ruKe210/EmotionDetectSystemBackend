from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


class ReportSummary(BaseModel):
    total: int
    accuracy: float
    alerts: int
    dominantEmotion: str


class EmotionDistribution(BaseModel):
    emotion: str
    count: int
    pct: float


class HourlyStats(BaseModel):
    hour: str
    count: int


class TrendData(BaseModel):
    dates: List[str]
    total: List[int]
    alerts: List[int]


class ReportQuery(BaseModel):
    reportType: str = "daily"  # daily, weekly, monthly
    startDate: Optional[str] = None
    endDate: Optional[str] = None
    device: Optional[str] = None