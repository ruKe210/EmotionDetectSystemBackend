from typing import Optional
from fastapi import APIRouter, Depends, Query
from datetime import datetime, timedelta
from app.schemas import ResponseModel, PaginatedResponse
from app.api.deps import get_current_active_user
from app.services.data_store import data_store
import random

router = APIRouter()


@router.get("/stats", response_model=ResponseModel)
async def get_face_stats(
    current_user: dict = Depends(get_current_active_user)
):
    """获取人脸统计信息"""
    stats = data_store.get_stats()
    return ResponseModel(data=stats)


@router.get("/realtime", response_model=ResponseModel)
async def get_realtime_faces(
    current_user: dict = Depends(get_current_active_user)
):
    """获取实时人脸数据 (含离散+2D+3D情绪)"""
    num_faces = random.randint(0, 5)
    faces = []

    for i in range(num_faces):
        # 生成随机情绪概率
        expressions = {
            "happy": random.random(),
            "sad": random.random(),
            "angry": random.random(),
            "neutral": random.random(),
            "fearful": random.random(),
            "surprised": random.random(),
            "disgusted": random.random(),
            "contempt": random.random() * 0.3
        }

        total = sum(expressions.values())
        expressions = {k: round(v/total, 4) for k, v in expressions.items()}

        valence = round(random.uniform(-1, 1), 4)
        arousal = round(random.uniform(-1, 1), 4)

        face = {
            "id": f"face_{i}_{int(datetime.now().timestamp())}",
            "camera_id": random.choice(list(data_store.cameras.keys())),
            "box": {
                "x": random.randint(50, 400),
                "y": random.randint(50, 300),
                "width": random.randint(80, 150),
                "height": random.randint(100, 180)
            },
            "expressions": expressions,
            "confidence": round(random.uniform(0.85, 0.99), 4),
            "timestamp": datetime.now(),
            # 二维情感
            "valence": valence,
            "arousal": arousal,
            # 三维情感
            "pleasure": valence,
            "pad_arousal": arousal,
            "dominance": round(random.uniform(-1, 1), 4),
        }
        faces.append(face)

    return ResponseModel(data={
        "faces": faces,
        "timestamp": datetime.now()
    })


@router.get("/history", response_model=ResponseModel[PaginatedResponse])
async def get_face_history(
    startDate: Optional[str] = None,
    endDate: Optional[str] = None,
    emotion: Optional[str] = None,
    device: Optional[str] = None,
    page: int = Query(1, ge=1),
    pageSize: int = Query(10, ge=1, le=100),
    current_user: dict = Depends(get_current_active_user)
):
    """获取人脸历史记录"""
    start_dt = None
    end_dt = None

    if startDate:
        start_dt = datetime.fromisoformat(startDate.replace('Z', '+00:00'))
    if endDate:
        end_dt = datetime.fromisoformat(endDate.replace('Z', '+00:00'))

    history, total = data_store.get_face_history(
        start_date=start_dt,
        end_date=end_dt,
        emotion=emotion,
        device=device,
        page=page,
        page_size=pageSize
    )

    return ResponseModel(data=PaginatedResponse.create(history, total, page, pageSize))


@router.get("/export")
async def export_face_data(
    startDate: Optional[str] = None,
    endDate: Optional[str] = None,
    format: str = "json",
    current_user: dict = Depends(get_current_active_user)
):
    """导出人脸数据"""
    start_dt = None
    end_dt = None

    if startDate:
        start_dt = datetime.fromisoformat(startDate.replace('Z', '+00:00'))
    if endDate:
        end_dt = datetime.fromisoformat(endDate.replace('Z', '+00:00'))

    history, total = data_store.get_face_history(
        start_date=start_dt,
        end_date=end_dt,
        page=1,
        page_size=1000
    )

    return ResponseModel(data={
        "total": total,
        "format": format,
        "data": history
    })


@router.get("/{face_id}", response_model=ResponseModel)
async def get_face_detail(
    face_id: str,
    current_user: dict = Depends(get_current_active_user)
):
    """获取人脸详情"""
    for record in data_store.face_history:
        if record["id"] == face_id:
            return ResponseModel(data=record)

    return ResponseModel(code=404, message="人脸记录不存在")
