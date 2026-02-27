from typing import Optional
from fastapi import APIRouter, Depends, Query
from datetime import datetime
from app.schemas import ResponseModel, AlertCreate, AlertUpdate, PaginatedResponse
from app.api.deps import get_current_active_user, get_current_admin_user
from app.services.data_store import data_store

router = APIRouter()


@router.get("", response_model=ResponseModel[PaginatedResponse])
async def get_alerts(
    status: Optional[str] = None,
    type: Optional[str] = None,
    page: int = Query(1, ge=1),
    pageSize: int = Query(10, ge=1, le=100),
    current_user: dict = Depends(get_current_active_user)
):
    """获取告警列表"""
    alerts, total = data_store.get_alerts(
        status=status,
        alert_type=type,
        page=page,
        page_size=pageSize
    )
    return ResponseModel(data=PaginatedResponse.create(alerts, total, page, pageSize))


@router.get("/{alert_id}", response_model=ResponseModel)
async def get_alert(
    alert_id: str,
    current_user: dict = Depends(get_current_active_user)
):
    """获取告警详情"""
    alert = data_store.get_alert(alert_id)
    if not alert:
        return ResponseModel(code=404, message="告警不存在")
    return ResponseModel(data=alert)


@router.post("/{alert_id}/handle", response_model=ResponseModel)
async def handle_alert(
    alert_id: str,
    current_user: dict = Depends(get_current_admin_user)
):
    """处理告警"""
    alert = data_store.get_alert(alert_id)
    if not alert:
        return ResponseModel(code=404, message="告警不存在")
    
    data_store.update_alert(alert_id, {
        "status": "handled",
        "handled_by": current_user["username"],
        "handled_at": datetime.now()
    })
    return ResponseModel(message="处理成功")


@router.post("/{alert_id}/ignore", response_model=ResponseModel)
async def ignore_alert(
    alert_id: str,
    current_user: dict = Depends(get_current_admin_user)
):
    """忽略告警"""
    alert = data_store.get_alert(alert_id)
    if not alert:
        return ResponseModel(code=404, message="告警不存在")
    
    data_store.update_alert(alert_id, {
        "status": "ignored",
        "handled_by": current_user["username"],
        "handled_at": datetime.now()
    })
    return ResponseModel(message="已忽略")


@router.post("/batch/handle", response_model=ResponseModel)
async def batch_handle_alerts(
    data: dict,
    current_user: dict = Depends(get_current_admin_user)
):
    """批量处理告警"""
    ids = data.get("ids", [])
    for alert_id in ids:
        alert = data_store.get_alert(alert_id)
        if alert:
            data_store.update_alert(alert_id, {
                "status": "handled",
                "handled_by": current_user["username"],
                "handled_at": datetime.now()
            })
    return ResponseModel(message="批量处理成功")