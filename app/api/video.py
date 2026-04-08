from typing import Optional
from fastapi import APIRouter, Depends, Query
from datetime import datetime, timedelta
from sqlalchemy import desc

from app.schemas import ResponseModel
from app.schemas.common import PaginatedResponse
from app.api.deps import get_current_active_user
from app.core.database import get_db_session
from app.models.db_models import VideoRecord, FaceHistory

router = APIRouter()


@router.get("/list", response_model=ResponseModel)
async def get_video_list(
    camera_id: Optional[str] = None,
    date: Optional[str] = None,
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(get_current_active_user),
):
    """获取录制视频列表"""
    session = get_db_session()
    try:
        query = session.query(VideoRecord).filter(
            VideoRecord.status.in_(["completed", "recording"])
        )

        if camera_id:
            query = query.filter(VideoRecord.camera_id == camera_id)
        if date:
            target = datetime.strptime(date, "%Y-%m-%d").date()
            start = datetime.combine(target, datetime.min.time())
            end = start + timedelta(days=1)
            query = query.filter(VideoRecord.start_time >= start, VideoRecord.start_time < end)

        total = query.count()
        records = query.order_by(desc(VideoRecord.start_time)).offset(
            (page - 1) * pageSize
        ).limit(pageSize).all()

        items = []
        for r in records:
            d = r.to_dict()
            d["url"] = f"/recordings/{r.file_name}"
            # 附带起止毫秒时间戳，供前端查询人脸数据
            d["start_ts"] = int(r.start_time.timestamp() * 1000) if r.start_time else 0
            d["end_ts"] = int(r.end_time.timestamp() * 1000) if r.end_time else 0
            items.append(d)

        return ResponseModel(data=PaginatedResponse.create(items, total, page, pageSize))
    finally:
        session.close()


@router.get("/faces", response_model=ResponseModel)
async def get_video_faces(
    camera_id: str = Query(...),
    start_ts: int = Query(..., description="视频起始毫秒时间戳"),
    end_ts: int = Query(..., description="视频结束毫秒时间戳"),
    current_user: dict = Depends(get_current_active_user),
):
    """获取视频时间段内的人脸检测数据（用于回放同步显示情绪）"""
    session = get_db_session()
    try:
        records = session.query(FaceHistory).filter(
            FaceHistory.camera_id == camera_id,
            FaceHistory.frame_timestamp >= start_ts,
            FaceHistory.frame_timestamp <= end_ts,
        ).order_by(FaceHistory.frame_timestamp, FaceHistory.face_index).all()

        # 按 frame_timestamp 分组
        frames = {}
        for r in records:
            ts = r.frame_timestamp
            if ts not in frames:
                frames[ts] = []
            frames[ts].append(r.to_dict())

        # 转成有序列表，方便前端按时间播放
        timeline = []
        for ts in sorted(frames.keys()):
            timeline.append({
                "timestamp": ts,
                "faces": frames[ts],
            })

        return ResponseModel(data={
            "total_faces": len(records),
            "frame_count": len(timeline),
            "timeline": timeline,
        })
    finally:
        session.close()
