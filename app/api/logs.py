from typing import Optional
from fastapi import APIRouter, Depends, Query
from datetime import datetime
from app.schemas import ResponseModel, PaginatedResponse
from app.api.deps import get_current_active_user, get_current_admin_user
from app.services.data_store import data_store

router = APIRouter()


@router.get("", response_model=ResponseModel[PaginatedResponse])
async def get_logs(
    type: Optional[str] = None,
    date: Optional[str] = None,
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    pageSize: int = Query(10, ge=1, le=100),
    current_user: dict = Depends(get_current_active_user)
):
    """获取日志列表"""
    logs, total = data_store.get_logs(
        log_type=type,
        date=date,
        search=search,
        page=page,
        page_size=pageSize
    )
    return ResponseModel(data=PaginatedResponse.create(logs, total, page, pageSize))


@router.get("/export")
async def export_logs(
    type: Optional[str] = None,
    date: Optional[str] = None,
    format: str = "json",
    current_user: dict = Depends(get_current_active_user)
):
    """导出日志"""
    logs, total = data_store.get_logs(
        log_type=type,
        date=date,
        page=1,
        page_size=10000
    )
    return ResponseModel(data={
        "total": total,
        "format": format,
        "data": logs
    })


@router.post("/clear", response_model=ResponseModel)
async def clear_logs(
    current_user: dict = Depends(get_current_admin_user)
):
    """清空日志"""
    data_store.clear_logs()
    
    # 记录操作日志
    data_store.add_log({
        "date": datetime.now().strftime("%Y-%m-%d"),
        "time": datetime.now().strftime("%H:%M:%S"),
        "type": "operation",
        "operator": current_user["username"],
        "content": "清空系统日志",
        "ip": "127.0.0.1"
    })
    
    return ResponseModel(message="日志已清除")