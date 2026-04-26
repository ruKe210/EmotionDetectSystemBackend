from io import BytesIO
from calendar import monthrange
from typing import Optional, Tuple
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from datetime import datetime, timedelta
from sqlalchemy import func
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

from app.schemas import ResponseModel
from app.api.deps import get_current_active_user
from app.core.database import get_db_session
from app.models.db_models import FaceHistory, Alert

router = APIRouter()


def _parse_date(value: str) -> datetime:
    return datetime.strptime(value, "%Y-%m-%d")


def _resolve_time_range(
    report_type: str,
    start_date: Optional[str],
    end_date: Optional[str],
) -> Tuple[datetime, datetime]:
    """统一解析日报/周报/月报/自定义时段的时间范围。"""
    now = datetime.now()
    report_type = report_type or "daily"

    if report_type == "custom":
        if start_date:
            start_dt = _parse_date(start_date)
        else:
            start_dt = now.replace(hour=0, minute=0, second=0, microsecond=0)

        if end_date:
            end_dt = _parse_date(end_date) + timedelta(days=1)
        else:
            end_dt = now
        return start_dt, end_dt

    if report_type == "weekly":
        base = _parse_date(start_date) if start_date else now
        week_start = (base - timedelta(days=base.weekday())).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        return week_start, week_start + timedelta(days=7)

    if report_type == "monthly":
        if start_date:
            if len(start_date) == 7:  # YYYY-MM
                base = datetime.strptime(start_date, "%Y-%m")
            else:
                base = _parse_date(start_date)
        else:
            base = now
        month_start = base.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        _, days = monthrange(month_start.year, month_start.month)
        return month_start, month_start + timedelta(days=days)

    # daily（默认）
    base = _parse_date(start_date) if start_date else now
    day_start = base.replace(hour=0, minute=0, second=0, microsecond=0)
    return day_start, day_start + timedelta(days=1)


def _apply_face_filters(query, start_dt: datetime, end_dt: datetime, device: Optional[str]):
    query = query.filter(FaceHistory.timestamp >= start_dt, FaceHistory.timestamp < end_dt)
    if device:
        query = query.filter(FaceHistory.camera_id == device)
    return query


def _apply_alert_filters(query, start_dt: datetime, end_dt: datetime, device: Optional[str]):
    query = query.filter(Alert.time >= start_dt, Alert.time < end_dt)
    if device:
        query = query.filter(Alert.device == device)
    return query


def _build_summary(session, start_dt: datetime, end_dt: datetime, device: Optional[str]):
    face_base = _apply_face_filters(session.query(FaceHistory), start_dt, end_dt, device)
    total = face_base.count()

    avg_confidence = (
        _apply_face_filters(
            session.query(func.avg(FaceHistory.confidence)),
            start_dt,
            end_dt,
            device,
        ).scalar()
        or 0
    )

    alert_count = _apply_alert_filters(
        session.query(func.count(Alert.id)),
        start_dt,
        end_dt,
        device,
    ).scalar() or 0

    dominant = _apply_face_filters(
        session.query(FaceHistory.dominant_emotion, func.count(FaceHistory.id)),
        start_dt,
        end_dt,
        device,
    ).group_by(FaceHistory.dominant_emotion).order_by(func.count(FaceHistory.id).desc()).first()

    dominant_emotion = dominant[0] if dominant else "neutral"
    return {
        "total": total,
        "accuracy": round(float(avg_confidence), 4),
        "alerts": alert_count,
        "dominantEmotion": dominant_emotion,
    }


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
        start_dt, end_dt = _resolve_time_range(reportType, startDate, endDate)
        return ResponseModel(data=_build_summary(session, start_dt, end_dt, device))
    finally:
        session.close()


@router.get("/emotion-distribution", response_model=ResponseModel)
async def get_emotion_distribution(
    reportType: str = "daily",
    startDate: Optional[str] = None,
    endDate: Optional[str] = None,
    device: Optional[str] = None,
    current_user: dict = Depends(get_current_active_user)
):
    """获取情绪分布"""
    session = get_db_session()
    try:
        start_dt, end_dt = _resolve_time_range(reportType, startDate, endDate)
        query = session.query(
            FaceHistory.dominant_emotion,
            func.count(FaceHistory.id).label("count"),
        )

        query = _apply_face_filters(query, start_dt, end_dt, device)

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
    reportType: str = "daily",
    startDate: Optional[str] = None,
    endDate: Optional[str] = None,
    date: Optional[str] = None,
    device: Optional[str] = None,
    current_user: dict = Depends(get_current_active_user)
):
    """获取每小时统计"""
    session = get_db_session()
    try:
        if date:  # 兼容旧参数
            start_dt, end_dt = _resolve_time_range("daily", date, None)
        else:
            start_dt, end_dt = _resolve_time_range(reportType, startDate, endDate)

        query = session.query(
            func.hour(FaceHistory.timestamp).label("hour"),
            func.count(FaceHistory.id).label("count"),
        )
        query = _apply_face_filters(query, start_dt, end_dt, device)

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
    reportType: str = "daily",
    startDate: Optional[str] = None,
    endDate: Optional[str] = None,
    days: int = Query(7, ge=1, le=30),
    device: Optional[str] = None,
    current_user: dict = Depends(get_current_active_user)
):
    """获取趋势数据"""
    session = get_db_session()
    try:
        if startDate or endDate or reportType in {"daily", "weekly", "monthly", "custom"}:
            start_dt, end_dt = _resolve_time_range(reportType, startDate, endDate)
            total_days = max((end_dt.date() - start_dt.date()).days, 1)
            total_days = min(total_days, 62)
        else:
            end_dt = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
            start_dt = end_dt - timedelta(days=days)
            total_days = days

        dates = []
        total = []
        alerts_list = []

        for i in range(total_days):
            day = start_dt + timedelta(days=i)
            day_str = day.strftime("%Y-%m-%d")
            day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
            day_end = day_start + timedelta(days=1)

            face_query = _apply_face_filters(
                session.query(func.count(FaceHistory.id)),
                day_start,
                day_end,
                device,
            )
            face_count = face_query.scalar() or 0

            alert_count = _apply_alert_filters(
                session.query(func.count(Alert.id)),
                day_start,
                day_end,
                device,
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
    session = get_db_session()
    try:
        start_dt, end_dt = _resolve_time_range(reportType, startDate, endDate)
        summary = _build_summary(session, start_dt, end_dt, device)

        emotion_rows = _apply_face_filters(
            session.query(FaceHistory.dominant_emotion, func.count(FaceHistory.id).label("count")),
            start_dt,
            end_dt,
            device,
        ).group_by(FaceHistory.dominant_emotion).order_by(func.count(FaceHistory.id).desc()).all()

        total_emotions = sum(r[1] for r in emotion_rows) or 1

        output = BytesIO()
        doc = SimpleDocTemplate(output, pagesize=A4)
        styles = getSampleStyleSheet()
        elements = []

        elements.append(Paragraph("Emotion Detection Report", styles["Title"]))
        elements.append(Spacer(1, 8))
        elements.append(
            Paragraph(
                f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | "
                f"Range: {start_dt.strftime('%Y-%m-%d')} ~ {(end_dt - timedelta(days=1)).strftime('%Y-%m-%d')}",
                styles["Normal"],
            )
        )
        if device:
            elements.append(Paragraph(f"Device: {device}", styles["Normal"]))
        elements.append(Spacer(1, 12))

        summary_table = Table(
            [
                ["Metric", "Value"],
                ["Total Detections", str(summary["total"])],
                ["Average Confidence", f'{summary["accuracy"] * 100:.2f}%'],
                ["Alert Count", str(summary["alerts"])],
                ["Dominant Emotion", summary["dominantEmotion"]],
            ],
            colWidths=[180, 280],
        )
        summary_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e9eefc")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#2d3436")),
                    ("GRID", (0, 0), (-1, -1), 1, colors.HexColor("#dfe6e9")),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ]
            )
        )
        elements.append(summary_table)
        elements.append(Spacer(1, 14))

        distribution_data = [["Emotion", "Count", "Percent"]]
        for emotion, count in emotion_rows:
            distribution_data.append([emotion or "unknown", str(count), f"{count / total_emotions * 100:.2f}%"])
        if len(distribution_data) == 1:
            distribution_data.append(["-", "0", "0.00%"])

        distribution_table = Table(distribution_data, colWidths=[180, 120, 160])
        distribution_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f6f8ff")),
                    ("GRID", (0, 0), (-1, -1), 1, colors.HexColor("#dfe6e9")),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
                ]
            )
        )
        elements.append(Paragraph("Emotion Distribution", styles["Heading3"]))
        elements.append(distribution_table)

        doc.build(elements)
        output.seek(0)
        filename = f"emotion_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        return StreamingResponse(
            output,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    finally:
        session.close()
