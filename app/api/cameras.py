import socket
import os
import cv2
import time
from typing import Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from app.schemas import ResponseModel, CameraCreate, CameraUpdate
from app.api.deps import get_current_active_user, get_current_admin_user
from app.services.data_store import data_store
from app.services.video_stream import video_manager
from app.services.inference_engine import inference_engine
from datetime import datetime

router = APIRouter()


@router.get("/list", response_model=ResponseModel)
async def get_cameras(current_user: dict = Depends(get_current_active_user)):
    """获取摄像头列表"""
    cameras = data_store.get_all_cameras()
    return ResponseModel(data=cameras)


@router.get("/{camera_id}", response_model=ResponseModel)
async def get_camera(camera_id: str, current_user: dict = Depends(get_current_active_user)):
    """获取摄像头详情"""
    camera = data_store.get_camera(camera_id)
    if not camera:
        return ResponseModel(code=404, message="摄像头不存在")
    return ResponseModel(data=camera)


@router.post("", response_model=ResponseModel)
async def create_camera(camera_data: CameraCreate, current_user: dict = Depends(get_current_admin_user)):
    """创建摄像头"""
    camera_dict = camera_data.model_dump()

    # 如果是 RTSP 类型，自动拼接 URL
    if camera_dict.get("type") == "rtsp" and not camera_dict.get("rtsp_url"):
        ip = camera_dict.get("ip", "")
        username = camera_dict.get("rtsp_username", "admin")
        password = camera_dict.get("rtsp_password", "")
        camera_dict["rtsp_url"] = f"rtsp://{username}:{password}@{ip}:554/stream1"

    new_camera = data_store.create_camera(camera_dict)
    return ResponseModel(data={"id": new_camera["id"]}, message="创建成功")


@router.put("/{camera_id}", response_model=ResponseModel)
async def update_camera(camera_id: str, camera_data: CameraUpdate, current_user: dict = Depends(get_current_admin_user)):
    """更新摄像头"""
    camera = data_store.get_camera(camera_id)
    if not camera:
        return ResponseModel(code=404, message="摄像头不存在")
    update_dict = {k: v for k, v in camera_data.model_dump().items() if v is not None}
    data_store.update_camera(camera_id, update_dict)
    return ResponseModel(message="更新成功")


@router.delete("/{camera_id}", response_model=ResponseModel)
async def delete_camera(camera_id: str, current_user: dict = Depends(get_current_admin_user)):
    """删除摄像头"""
    camera = data_store.get_camera(camera_id)
    if not camera:
        return ResponseModel(code=404, message="摄像头不存在")
    inference_engine.remove_camera(camera_id)
    data_store.delete_camera(camera_id)
    return ResponseModel(message="删除成功")


@router.post("/{camera_id}/toggle", response_model=ResponseModel)
async def toggle_camera(camera_id: str, current_user: dict = Depends(get_current_admin_user)):
    """切换摄像头状态 — 启动/停止推理"""
    camera = data_store.get_camera(camera_id)
    if not camera:
        return ResponseModel(code=404, message="摄像头不存在")

    current_status = camera.get("status", "offline")
    new_status = "online" if current_status == "offline" else "offline"

    if new_status == "online":
        # 根据类型确定 source
        if camera.get("type") == "rtsp":
            source = camera.get("rtsp_url", "")
        else:
            source = camera.get("source_index", 0)

        cid = inference_engine.add_camera(
            source=source,
            name=camera.get("name", ""),
            camera_id=camera_id,
        )
        if not cid:
            return ResponseModel(code=500, message="摄像头启动失败")
    else:
        inference_engine.remove_camera(camera_id)

    data_store.update_camera(camera_id, {
        "status": new_status,
        "last_seen": datetime.now() if new_status == "online" else camera.get("last_seen"),
    })

    return ResponseModel(data={"status": new_status})


# ========== 局域网扫描 ==========

def _check_port(ip: str, port: int = 554, timeout: float = 0.5) -> bool:
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((ip, port))
        sock.close()
        return result == 0
    except Exception:
        return False


@router.get("/scan/network", response_model=ResponseModel)
async def scan_network(current_user: dict = Depends(get_current_admin_user)):
    """扫描 192.168.9.0/24 中开放 RTSP 端口(554) 的设备"""
    # 获取本机 IP
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
    except Exception:
        local_ip = "127.0.0.1"
    finally:
        s.close()

    # 按需求固定仅扫描 192.168.9.xxx 段
    subnet = "192.168.9."

    found = []
    with ThreadPoolExecutor(max_workers=50) as executor:
        futures = {}
        for i in range(1, 255):
            ip = f"{subnet}{i}"
            futures[executor.submit(_check_port, ip, 554)] = ip
        for future in as_completed(futures):
            ip = futures[future]
            if future.result() and ip != local_ip:
                found.append(ip)

    return ResponseModel(data={"local_ip": local_ip, "subnet": "192.168.9.0/24", "devices": found})


class RtspTestRequest(BaseModel):
    ip: str
    username: str = "admin"
    password: str = ""
    port: int = 554


RTSP_PATHS = [
    "/stream1", "/stream2",
    "/cam/realmonitor?channel=1&subtype=0",
    "/h264/ch1/main/av_stream",
    "/Streaming/Channels/101",
    "/1", "/",
]


@router.post("/scan/test", response_model=ResponseModel)
async def test_rtsp(req: RtspTestRequest, current_user: dict = Depends(get_current_admin_user)):
    """测试 RTSP 连接，自动尝试多种路径"""
    os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = (
        "rtsp_transport;udp|fflags;nobuffer|flags;low_delay|"
        "framedrop;1|max_delay;500000|analyzeduration;500000|probesize;32768"
    )

    for path in RTSP_PATHS:
        url = f"rtsp://{req.username}:{req.password}@{req.ip}:{req.port}{path}"
        cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
        start = time.time()
        while not cap.isOpened() and time.time() - start < 3:
            time.sleep(0.1)
        if cap.isOpened():
            ret, frame = cap.read()
            if ret and frame is not None:
                w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                cap.release()
                return ResponseModel(data={
                    "success": True,
                    "rtsp_url": url,
                    "path": path,
                    "resolution": f"{w}x{h}",
                })
            cap.release()
        else:
            cap.release()

    return ResponseModel(code=400, message="所有 RTSP 路径均连接失败，请检查账号密码")
