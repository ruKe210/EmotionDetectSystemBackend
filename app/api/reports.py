from calendar import monthrange
import os
import asyncio
from typing import Optional, Tuple
from fastapi import APIRouter, Depends, Query
from datetime import datetime, timedelta
from sqlalchemy import func
from openai import OpenAI

from app.schemas import ResponseModel
from app.api.deps import get_current_active_user
from app.core.config import settings
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


def _build_analysis_context(session, start_dt: datetime, end_dt: datetime, device: Optional[str]):
    summary = _build_summary(session, start_dt, end_dt, device)

    emotion_rows = _apply_face_filters(
        session.query(FaceHistory.dominant_emotion, func.count(FaceHistory.id).label("count")),
        start_dt,
        end_dt,
        device,
    ).group_by(FaceHistory.dominant_emotion).order_by(func.count(FaceHistory.id).desc()).all()

    hourly_rows = _apply_face_filters(
        session.query(func.hour(FaceHistory.timestamp).label("hour"), func.count(FaceHistory.id).label("count")),
        start_dt,
        end_dt,
        device,
    ).group_by(func.hour(FaceHistory.timestamp)).all()

    emotion_distribution = []
    total_emotions = sum(r[1] for r in emotion_rows) or 1
    for emotion, count in emotion_rows:
        emotion_distribution.append(
            {
                "emotion": emotion or "unknown",
                "count": int(count),
                "pct": round(count / total_emotions * 100, 2),
            }
        )

    hourly_data = [{"hour": int(h), "count": int(c)} for h, c in hourly_rows]
    hourly_data.sort(key=lambda x: x["hour"])
    peak_hours = sorted(hourly_data, key=lambda x: x["count"], reverse=True)[:3]

    return {
        "time_range": {
            "start": start_dt.strftime("%Y-%m-%d"),
            "end": (end_dt - timedelta(days=1)).strftime("%Y-%m-%d"),
        },
        "device": device or "all",
        "summary": summary,
        "emotion_distribution": emotion_distribution,
        "hourly_data": hourly_data,
        "peak_hours": peak_hours,
    }


def _candidate_models(primary_model: str) -> list:
    """按优先级返回可尝试的方舟模型名。"""
    fallbacks = [
        "doubao-1-5-lite-32k-250115",
        "doubao-1.5-lite-4k",
        "doubao-1-5-lite-4k",
    ]
    ordered = [primary_model] + fallbacks
    deduped = []
    for m in ordered:
        if m and m not in deduped:
            deduped.append(m)
    return deduped


def _mask_key(key: str) -> str:
    if not key:
        return ""
    if len(key) <= 10:
        return key[:3] + "***"
    return f"{key[:8]}...{key[-6:]}"


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


@router.get("/intelligent-analysis", response_model=ResponseModel)
async def get_intelligent_analysis(
    reportType: str = "daily",
    startDate: Optional[str] = None,
    endDate: Optional[str] = None,
    device: Optional[str] = None,
    current_user: dict = Depends(get_current_active_user)
):
    """生成智能分析文本（供前端展示和PDF写入）"""
    session = get_db_session()
    try:
        start_dt, end_dt = _resolve_time_range(reportType, startDate, endDate)
        context_data = _build_analysis_context(session, start_dt, end_dt, device)

        api_key = settings.ARK_API_KEY or os.getenv("ARK_API_KEY", "")
        if not api_key:
            return ResponseModel(
                data={
                    "analysis": (
                        "智能分析未启用：请在后端 .env 中配置 ARK_API_KEY 后重试。\n"
                        f"当前统计：总识别 {context_data['summary']['total']} 次，"
                        f"告警 {context_data['summary']['alerts']} 次，"
                        f"主导情绪 {context_data['summary']['dominantEmotion']}。"
                    )
                }
            )

        try:
            base_url = (settings.ARK_BASE_URL or "").strip()
            post_url = base_url
            masked_key = _mask_key(api_key)
            print(f"[AI分析] POST URL: {post_url}")
            print(f"[AI分析] 当前模型: {settings.ARK_MODEL}")
            print(f"[AI分析] 当前Key(脱敏): {masked_key}")
            print(
                f"[AI分析] CURL(脱敏): curl {post_url} -H \"Content-Type: application/json\" "
                f"-H \"Authorization: Bearer {masked_key}\" -d '{{\"model\":\"{settings.ARK_MODEL}\",\"messages\":[...]}}'"
            )

            # 与 test_ark_api_connectivity.py 保持一致：直接使用 OpenAI 兼容调用
            client = OpenAI(api_key=api_key, base_url=base_url)
            prompt = (
                "请基于以下情绪识别统计数据输出正式中文分析，要求包含：\n"
                "1) 总体结论（1段）\n"
                "2) 风险点与异常时段（2-4条）\n"
                "3) 优化建议（2-4条）\n"
                "4) 适合写入报告正文的结论段（1段）\n\n"
                f"数据：{context_data}"
            )

            last_error = None
            used_model = None
            for model_name in _candidate_models(settings.ARK_MODEL):
                used_model = model_name
                try:
                    resp = await asyncio.to_thread(
                        client.chat.completions.create,
                        model=model_name,
                        messages=[
                            {"role": "system", "content": "你是一个数据分析助手，擅长把后端统计整理成正式中文报告文本。"},
                            {"role": "user", "content": prompt},
                        ],
                    )
                    content = (resp.choices[0].message.content or "").strip()
                    if content:
                        return ResponseModel(data={"analysis": content})
                    last_error = "模型返回空内容"
                except Exception as model_err:
                    last_error = str(model_err)
                    continue

            return ResponseModel(
                data={
                    "analysis": (
                        "智能分析调用失败：所有候选模型均不可用。\n"
                        f"最后尝试模型：{used_model}\n"
                        f"错误信息：{last_error}\n"
                        f"当前统计：总识别 {context_data['summary']['total']} 次，"
                        f"告警 {context_data['summary']['alerts']} 次，"
                        f"主导情绪 {context_data['summary']['dominantEmotion']}。"
                    )
                }
            )
        except Exception as e:
            return ResponseModel(
                data={
                    "analysis": (
                        "智能分析调用失败，请检查 ARK 配置或网络连通性。\n"
                        f"错误信息：{str(e)}\n"
                        f"当前统计：总识别 {context_data['summary']['total']} 次，"
                        f"告警 {context_data['summary']['alerts']} 次，"
                        f"主导情绪 {context_data['summary']['dominantEmotion']}。"
                    )
                }
            )
    finally:
        session.close()
