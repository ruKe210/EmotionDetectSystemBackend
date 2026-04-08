import uvicorn
import asyncio
import threading
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from datetime import datetime

from app.core.config import settings
from app.api import register_router
from app.websocket.routes import router as websocket_router
from app.websocket.manager import websocket_manager
from app.services.inference_engine import inference_engine


def init_camera_thread():
    """在后台线程中初始化摄像头 — 从数据库加载已有摄像头"""
    import time
    time.sleep(2)  # 等待服务完全启动
    try:
        from app.services.data_store import data_store
        cameras = data_store.get_all_cameras()

        started = 0
        for cam in cameras:
            if cam.get("status") == "online":
                cam_type = cam.get("type", "usb")
                cam_id = cam.get("id", "")
                cam_name = cam.get("name", "摄像头")

                if cam_type == "rtsp":
                    source = cam.get("rtsp_url", "")
                else:
                    source = cam.get("source_index", 0)

                if source == "" or source is None:
                    continue

                print(f"\n[摄像头] 正在启动: {cam_name} ({cam_type}, id={cam_id})")
                result = inference_engine.add_camera(source=source, name=cam_name, camera_id=cam_id)
                if result:
                    print(f"[摄像头] ✓ {cam_name} 已启动")
                    started += 1
                else:
                    print(f"[摄像头] ✗ {cam_name} 启动失败")

        # 如果数据库里没有任何摄像头，尝试启动默认 USB 摄像头
        if started == 0 and len(cameras) == 0:
            print("\n[摄像头] 数据库无摄像头记录，尝试启动默认 USB 摄像头...")
            camera_id = inference_engine.add_camera(source=0, name="默认摄像头")
            if camera_id:
                print(f"[摄像头] ✓ 默认摄像头已启动: {camera_id}")
            else:
                print("[摄像头] ✗ 默认摄像头启动失败")

        print(f"\n[摄像头] 初始化完成，已启动 {started} 个摄像头")
    except Exception as e:
        print(f"[摄像头] ✗ 摄像头初始化错误: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时执行
    print("=" * 60)
    print("情绪识别管理系统后端启动中")
    print("=" * 60)
    
    # 1. 启动推理引擎（自动加载模型）
    print("\n[1/3] 正在启动推理引擎...")
    inference_engine.start()
    print("✓ 推理引擎已启动")
    
    # 2. 启动WebSocket广播服务
    print("\n[2/3] 启动WebSocket广播服务...")
    websocket_manager.start_broadcast_loop()
    print("✓ WebSocket服务已启动")
    
    # 3. 在后台线程中初始化摄像头（不阻塞启动）
    print("\n[3/3] 后台初始化摄像头...")
    camera_thread = threading.Thread(target=init_camera_thread)
    camera_thread.daemon = True
    camera_thread.start()
    
    print("\n" + "=" * 60)
    print("后端服务启动完成")
    print("=" * 60)
    print(f"API文档地址: http://{settings.HOST}:{settings.PORT}/docs")
    print(f"WebSocket地址: ws://{settings.HOST}:{settings.PORT}/ws/face")
    print(f"视频流地址: ws://{settings.HOST}:{settings.PORT}/ws/video")
    print("=" * 60 + "\n")
    
    yield
    
    # 关闭时执行
    print("\n" + "=" * 60)
    print("后端服务关闭中...")
    print("=" * 60)
    
    # 停止WebSocket广播
    websocket_manager.stop()
    
    # 停止推理引擎
    inference_engine.stop()
    
    # 停止视频录制
    from app.services.video_recorder import video_recorder
    video_recorder.stop_all()
    
    print("✓ 后端服务已关闭")
    print("=" * 60 + "\n")


# 创建FastAPI应用
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="基于机器视觉的情绪识别管理系统后端 - 服务端推理架构",
    lifespan=lifespan
)

# 配置跨域
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册API路由
register_router(app)

# 注册WebSocket路由
app.include_router(websocket_router)

# 挂载录制视频静态文件
import os
recordings_dir = os.path.join(settings.DATA_STORAGE_PATH, "recordings")
os.makedirs(recordings_dir, exist_ok=True)
app.mount("/recordings", StaticFiles(directory=recordings_dir), name="recordings")


@app.get("/")
async def root():
    """根路径"""
    return {
        "message": f"欢迎使用{settings.APP_NAME}",
        "version": settings.APP_VERSION,
        "architecture": "服务端推理 + WebSocket推送",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "inference_engine": "running" if inference_engine.is_running else "stopped",
        "active_cameras": len(inference_engine.active_cameras),
        "timestamp": datetime.now().isoformat()
    }


@app.get("/api/cameras")
async def get_cameras():
    """获取摄像头列表"""
    return {
        "code": 200,
        "message": "success",
        "data": inference_engine.get_active_cameras()
    }


@app.post("/api/cameras/{camera_id}/start")
async def start_camera(camera_id: str):
    """启动摄像头"""
    success = inference_engine.add_camera(source=0, name=camera_id)
    return {
        "code": 200 if success else 500,
        "message": "success" if success else "failed",
        "data": {"camera_id": success}
    }


@app.post("/api/cameras/{camera_id}/stop")
async def stop_camera(camera_id: str):
    """停止摄像头"""
    inference_engine.remove_camera(camera_id)
    return {
        "code": 200,
        "message": "success"
    }


@app.get("/api/stats")
async def get_stats():
    """获取推理统计信息"""
    return {
        "code": 200,
        "message": "success",
        "data": {
            "inference": inference_engine.get_stats(),
            "cameras": inference_engine.get_active_cameras()
        }
    }


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info"
    )
