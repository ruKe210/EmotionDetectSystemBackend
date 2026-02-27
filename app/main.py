import uvicorn
import asyncio
import threading
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from datetime import datetime

from app.core.config import settings
from app.api import register_router
from app.websocket.routes import router as websocket_router
from app.websocket.manager import websocket_manager
from app.services.inference_engine import inference_engine


def init_camera_thread():
    """在后台线程中初始化摄像头"""
    import time
    time.sleep(2)  # 等待服务完全启动
    try:
        print("\n[摄像头] 正在后台初始化摄像头...")
        camera_id = inference_engine.add_camera(source=0, name="默认摄像头")
        if camera_id:
            print(f"[摄像头] ✓ 摄像头已启动: {camera_id}")
        else:
            print("[摄像头] ✗ 摄像头启动失败，请检查设备")
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
