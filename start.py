#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
情绪识别管理系统后端启动脚本
一键启动后端服务
"""

import sys
import os

# 添加依赖包路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'deps', 'Lib', 'site-packages'))

# 添加用户 site-packages 路径（用于 onnxruntime 等用户安装的包）
import site
user_site = site.getusersitepackages()
if user_site and os.path.exists(user_site):
    sys.path.insert(0, user_site)

import subprocess
import argparse


def check_dependencies():
    """检查依赖是否已安装"""
    try:
        import fastapi
        import uvicorn
        import cv2
        import numpy
        print("✓ 依赖检查通过")
        return True
    except ImportError as e:
        print(f"✗ 缺少依赖: {e}")
        print("请先安装依赖: pip install -r requirements.txt")
        return False


def install_dependencies():
    """安装依赖"""
    print("正在安装依赖...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✓ 依赖安装完成")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ 依赖安装失败: {e}")
        return False


def start_server(host="0.0.0.0", port=8000, reload=True):
    """启动服务器"""
    import uvicorn
    
    print(f"\n{'='*50}")
    print(f"启动情绪识别管理系统后端")
    print(f"{'='*50}")
    print(f"服务地址: http://{host}:{port}")
    print(f"API文档: http://{host}:{port}/docs")
    print(f"WebSocket: ws://{host}:{port}/ws/face")
    print(f"{'='*50}\n")
    
    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info"
    )


def main():
    parser = argparse.ArgumentParser(description="情绪识别管理系统后端启动脚本")
    parser.add_argument("--host", default="0.0.0.0", help="服务器地址 (默认: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8000, help="服务器端口 (默认: 8000)")
    parser.add_argument("--no-reload", action="store_true", help="禁用自动重载")
    parser.add_argument("--install", action="store_true", help="安装依赖")
    
    args = parser.parse_args()
    
    # 如果指定了安装依赖
    if args.install:
        if not install_dependencies():
            sys.exit(1)
    
    # 检查依赖
    if not check_dependencies():
        response = input("是否现在安装依赖? (y/n): ")
        if response.lower() == 'y':
            if not install_dependencies():
                sys.exit(1)
        else:
            sys.exit(1)
    
    # 启动服务器
    start_server(
        host=args.host,
        port=args.port,
        reload=not args.no_reload
    )


if __name__ == "__main__":
    main()