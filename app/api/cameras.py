from typing import Optional
from fastapi import APIRouter, Depends, Query
from app.schemas import ResponseModel, CameraCreate, CameraUpdate, PaginatedResponse
from app.schemas.common import PaginationParams
from app.api.deps import get_current_active_user, get_current_admin_user
from app.services.data_store import data_store
from app.services.video_stream import video_manager
from datetime import datetime

router = APIRouter()


@router.get("/list", response_model=ResponseModel)
async def get_cameras(
    current_user: dict = Depends(get_current_active_user)
):
    """获取摄像头列表"""
    cameras = data_store.get_all_cameras()
    return ResponseModel(data=cameras)


@router.get("/{camera_id}", response_model=ResponseModel)
async def get_camera(
    camera_id: str,
    current_user: dict = Depends(get_current_active_user)
):
    """获取摄像头详情"""
    camera = data_store.get_camera(camera_id)
    if not camera:
        return ResponseModel(code=404, message="摄像头不存在")
    return ResponseModel(data=camera)


@router.post("", response_model=ResponseModel)
async def create_camera(
    camera_data: CameraCreate,
    current_user: dict = Depends(get_current_admin_user)
):
    """创建摄像头"""
    camera_dict = camera_data.model_dump()
    new_camera = data_store.create_camera(camera_dict)
    return ResponseModel(data={"id": new_camera["id"]}, message="创建成功")


@router.put("/{camera_id}", response_model=ResponseModel)
async def update_camera(
    camera_id: str,
    camera_data: CameraUpdate,
    current_user: dict = Depends(get_current_admin_user)
):
    """更新摄像头"""
    camera = data_store.get_camera(camera_id)
    if not camera:
        return ResponseModel(code=404, message="摄像头不存在")
    
    update_dict = {k: v for k, v in camera_data.model_dump().items() if v is not None}
    data_store.update_camera(camera_id, update_dict)
    return ResponseModel(message="更新成功")


@router.delete("/{camera_id}", response_model=ResponseModel)
async def delete_camera(
    camera_id: str,
    current_user: dict = Depends(get_current_admin_user)
):
    """删除摄像头"""
    camera = data_store.get_camera(camera_id)
    if not camera:
        return ResponseModel(code=404, message="摄像头不存在")
    
    # 停止相关视频流
    video_manager.stop_stream(camera_id)
    
    data_store.delete_camera(camera_id)
    return ResponseModel(message="删除成功")


@router.post("/{camera_id}/toggle", response_model=ResponseModel)
async def toggle_camera(
    camera_id: str,
    current_user: dict = Depends(get_current_admin_user)
):
    """切换摄像头状态"""
    camera = data_store.get_camera(camera_id)
    if not camera:
        return ResponseModel(code=404, message="摄像头不存在")
    
    current_status = camera.get("status", "offline")
    new_status = "online" if current_status == "offline" else "offline"
    
    data_store.update_camera(camera_id, {
        "status": new_status,
        "last_seen": datetime.now() if new_status == "online" else camera.get("last_seen")
    })
    
    # 如果切换到online，启动视频流
    if new_status == "online":
        # 创建或启动视频流
        stream = video_manager.get_stream(camera_id)
        if not stream:
            # 创建新的视频流，使用笔记本内置摄像头
            source = 0 if camera.get("type") == "usb" else camera.get("ip", 0)
            video_manager.create_stream(source=source, name=camera.get("name"))
        video_manager.start_stream(camera_id)
    else:
        # 停止视频流
        video_manager.stop_stream(camera_id)
    
    return ResponseModel(data={"status": new_status})