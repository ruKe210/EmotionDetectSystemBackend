from typing import Optional
from fastapi import APIRouter, Depends, Query
from datetime import datetime, timedelta
from sqlalchemy import func

from app.schemas import ResponseModel
from app.api.deps import get_current_active_user
from app.core.database import get_db_session
from app.models.db_models import FaceHistory, Alert

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
    session = get_db_session()
    try:
        # 根据报表类型确定时间范围
        if startDate:
            start_dt = datetime.fromisoformat(startDate.replace('Z', '+00:00'))
        else:
            if reportType == "daily":
                start_dt = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            elif reportType == "weekly":
                start_dt = datetime.now() - timedelta(days=7)
            else:
                start_dt = datetime.now() - timedelta(days=30)

        if endDate:
            end_dt = datetime.fromisoformat(endDate.replace('Z', '+00:00'))
        else:
            end_dt = datetime.now()

        query = session.query(FaceHistory).filter(
            FaceHistory.timestamp >= start_dt,
            FaceHistory.timestamp <= end_dt,
        )
        if device:
            query = query.filter(FaceHistory.camera_id == device)

        total = query.count()

        # 计算平均置信度
        avg_confidence = session.query(func.avg(FaceHistory.confidence)).filter(
            FaceHistory.timestamp >= start_dt,
            FaceHistory.timestamp <= end_dt,
        ).scalar() or 0

        # 告警数
        alert_query = session.query(Alert).filter(
            Alert.time >= start_dt,
            Alert.time <= end_dt,
        )
        alert_count = alert_query.count()

        # 最常见情绪
        dominant = session.query(
            FaceHistory.dominant_emotion, func.count(FaceHistory.id)
        ).filter(
            FaceHistory.timestamp >= start_dt,
            FaceHistory.timestamp <= end_dt,
        ).group_by(FaceHistory.dominant_emotion).order_by(
            func.count(FaceHistory.id).desc()
        ).first()

        dominant_emotion = dominant[0] if dominant else "neutral"

        return ResponseModel(data={
            "total": total,
            "accuracy": round(float(avg_confidence), 4),
            "alerts": alert_count,
            "dominantEmotion": dominant_emotion,
        })
    finally:
        session.close()


@router.get("/emotion-distribution", response_model=ResponseModel)
async def get_emotion_distribution(
    startDate: Optional[str] = None,
    endDate: Optional[str] = None,
    device: Optional[str] = None,
    current_user: dict = Depends(get_current_active_user)
):
    """获取情绪分布"""
    session = get_db_session()
    try:
        query = session.query(
            FaceHistory.dominant_emotion,
            func.count(FaceHistory.id).label("count"),
        )

        if startDate:
            start_dt = datetime.fromisoformat(startDate.replace('Z', '+00:00'))
            query = query.filter(FaceHistory.timestamp >= start_dt)
        if endDate:
            end_dt = datetime.fromisoformat(endDate.replace('Z', '+00:00'))
            query = query.filter(FaceHistory.timestamp <= end_dt)
        if device:
            query = query.filter(FaceHistory.camera_id == device)

        results = query.group_by(FaceHistory.dominant_emotion).all()

        total_count = sum(r[1] for r in results) or 1
        distribution = []
        for emotion, count in results:
            distribution.append({
                "emotion": emotion,
                "count": count,
                "pct": round(count / total_count * 100, 2),
            })

        return ResponseModel(data=distribution)
    finally:
        session.close()


@router.get("/hourly", response_model=ResponseModel)
async def get_hourly_stats(
    date: Optional[str] = None,
    device: Optional[str] = None,
    current_user: dict = Depends(get_current_active_user)
):
    """获取每小时统计"""
    session = get_db_session()
    try:
        if date:
            target_date = datetime.strptime(date, "%Y-%m-%d").date()
        else:
            target_date = datetime.now().date()

        start_dt = datetime.combine(target_date, datetime.min.time())
        end_dt = start_dt + timedelta(days=1)

        query = session.query(
            func.hour(FaceHistory.timestamp).label("hour"),
            func.count(FaceHistory.id).label("count"),
        ).filter(
            FaceHistory.timestamp >= start_dt,
            FaceHistory.timestamp < end_dt,
        )

        if device:
            query = query.filter(FaceHistory.camera_id == device)

        results = query.group_by(func.hour(FaceHistory.timestamp)).all()
        hour_map = {int(r[0]): r[1] for r in results}

        hourly_data = []
        for hour in range(24):
            hourly_data.append({
                "hour": str(hour),
                "count": hour_map.get(hour, 0),
            })

        return ResponseModel(data=hourly_data)
    finally:
        session.close()


@router.get("/trend", response_model=ResponseModel)
async def get_trend_data(
    days: int = Query(7, ge=1, le=30),
    device: Optional[str] = None,
    current_user: dict = Depends(get_current_active_user)
):
    """获取趋势数据"""
    session = get_db_session()
    try:
        dates = []
        total = []
        alerts_list = []

        for i in range(days):
            day = datetime.now() - timedelta(days=days - i - 1)
            day_str = day.strftime("%Y-%m-%d")
            day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
            day_end = day_start + timedelta(days=1)

            face_query = session.query(func.count(FaceHistory.id)).filter(
                FaceHistory.timestamp >= day_start,
                FaceHistory.timestamp < day_end,
            )
            if device:
                face_query = face_query.filter(FaceHistory.camera_id == device)
            face_count = face_query.scalar() or 0

            alert_count = session.query(func.count(Alert.id)).filter(
                Alert.time >= day_start,
                Alert.time < day_end,
            ).scalar() or 0

            dates.append(day_str)
            total.append(face_count)
            alerts_list.append(alert_count)

        return ResponseModel(data={
            "dates": dates,
            "total": total,
            "alerts": alerts_list,
        })
    finally:
        session.close()


@router.get("/export-pdf")
async def export_pdf_report(
    reportType: str = "daily",
    startDate: Optional[str] = None,
    endDate: Optional[str] = None,
    device: Optional[str] = None,
    current_user: dict = Depends(get_current_active_user)
):
    """导出PDF报表"""
    return ResponseModel(data={
        "message": "PDF导出功能开发中",
        "reportType": reportType,
        "generated_at": datetime.now(),
    })
