from typing import Optional
from fastapi import APIRouter, Depends, Query
from datetime import datetime, timedelta
from app.schemas import ResponseModel
from app.api.deps import get_current_active_user
from app.services.data_store import data_store
import random

router = APIRouter()


@router.get("/summary", response_model=ResponseModel)
async def get_report_summary(
    reportType: str = "daily",
    startDate: Optional[str] = None,
    endDate: Optional[str] = None,
    device: Optional[str] = None,
    current_user: dict = Depends(get_current_active_user)
):
    """获取报表摘要"""
    # 模拟数据
    return ResponseModel(data={
        "total": random.randint(100, 1000),
        "accuracy": round(random.uniform(0.85, 0.98), 4),
        "alerts": random.randint(0, 20),
        "dominantEmotion": random.choice(["happy", "neutral", "sad"])
    })


@router.get("/emotion-distribution", response_model=ResponseModel)
async def get_emotion_distribution(
    startDate: Optional[str] = None,
    endDate: Optional[str] = None,
    device: Optional[str] = None,
    current_user: dict = Depends(get_current_active_user)
):
    """获取情绪分布"""
    emotions = ["happy", "sad", "angry", "fear", "surprise", "neutral"]
    distribution = []
    
    for emotion in emotions:
        count = random.randint(10, 100)
        distribution.append({
            "emotion": emotion,
            "count": count,
            "pct": round(count / 500 * 100, 2)
        })
    
    return ResponseModel(data=distribution)


@router.get("/hourly", response_model=ResponseModel)
async def get_hourly_stats(
    date: Optional[str] = None,
    device: Optional[str] = None,
    current_user: dict = Depends(get_current_active_user)
):
    """获取每小时统计"""
    hourly_data = []
    for hour in range(24):
        hourly_data.append({
            "hour": str(hour),
            "count": random.randint(0, 50)
        })
    return ResponseModel(data=hourly_data)


@router.get("/trend", response_model=ResponseModel)
async def get_trend_data(
    days: int = Query(7, ge=1, le=30),
    device: Optional[str] = None,
    current_user: dict = Depends(get_current_active_user)
):
    """获取趋势数据"""
    dates = []
    total = []
    alerts = []
    
    for i in range(days):
        date = (datetime.now() - timedelta(days=days-i-1)).strftime("%Y-%m-%d")
        dates.append(date)
        total.append(random.randint(50, 200))
        alerts.append(random.randint(0, 10))
    
    return ResponseModel(data={
        "dates": dates,
        "total": total,
        "alerts": alerts
    })


@router.get("/export-pdf")
async def export_pdf_report(
    reportType: str = "daily",
    startDate: Optional[str] = None,
    endDate: Optional[str] = None,
    device: Optional[str] = None,
    current_user: dict = Depends(get_current_active_user)
):
    """导出PDF报表"""
    # 简化处理，返回模拟数据
    return ResponseModel(data={
        "message": "PDF导出功能开发中",
        "reportType": reportType,
        "generated_at": datetime.now()
    })