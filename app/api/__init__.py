from fastapi import FastAPI
from app.api import auth, users, cameras, face, alerts, logs, config, reports, system, model


def register_router(app: FastAPI):
    """注册所有路由"""
    # 认证相关
    app.include_router(auth.router, prefix="/api/auth", tags=["认证"])
    
    # 用户管理
    app.include_router(users.router, prefix="/api/users", tags=["用户管理"])
    
    # 摄像头管理
    app.include_router(cameras.router, prefix="/api/camera", tags=["摄像头管理"])
    
    # 人脸识别
    app.include_router(face.router, prefix="/api/face", tags=["人脸识别"])
    
    # 告警管理
    app.include_router(alerts.router, prefix="/api/alerts", tags=["告警管理"])
    
    # 日志管理
    app.include_router(logs.router, prefix="/api/logs", tags=["日志管理"])
    
    # 系统配置
    app.include_router(config.router, prefix="/api/config", tags=["系统配置"])
    
    # 报表统计
    app.include_router(reports.router, prefix="/api/reports", tags=["报表统计"])
    
    # 系统状态
    app.include_router(system.router, prefix="/api/system", tags=["系统状态"])
    
    # 模型管理
    app.include_router(model.router, prefix="/api/model", tags=["模型管理"])