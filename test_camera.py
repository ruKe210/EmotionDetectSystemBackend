#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
本地摄像头测试脚本 - 直接显示人脸检测和情绪识别结果
"""

import sys

import cv2
import numpy as np
import time

from app.services.yolo_face_detector import yolo_face_detector
from app.services.hsemotion_recognizer import hsemotion_recognizer


def get_emotion_color(emotion: str) -> tuple:
    """获取情绪对应的颜色 (BGR格式)"""
    colors = {
        "neutral": (128, 128, 128),    # 灰色
        "happy": (0, 255, 0),          # 绿色
        "sad": (255, 0, 0),            # 蓝色
        "angry": (0, 0, 255),          # 红色
        "fearful": (0, 255, 255),      # 黄色
        "disgusted": (255, 0, 255),    # 紫色
        "surprised": (255, 255, 0),    # 青色
        "contempt": (128, 0, 128),     # 深紫色
    }
    return colors.get(emotion, (0, 255, 0))


def get_emotion_cn(emotion: str) -> str:
    """情绪中文映射"""
    emotion_map = {
        "neutral": "平静",
        "happy": "开心",
        "sad": "悲伤",
        "angry": "愤怒",
        "fearful": "恐惧",
        "disgusted": "厌恶",
        "surprised": "惊讶",
        "contempt": "蔑视",
    }
    return emotion_map[emotion]


def main():
    print("=" * 60)
    print("本地摄像头测试 - 人脸检测与情绪识别")
    print("=" * 60)
    
    # 1. 加载模型
    print("\n[1/3] 加载模型...")
    
    if not yolo_face_detector.load_model():
        print("✗ 人脸检测模型加载失败")
        return
    print("✓ 人脸检测模型加载成功")
    
    if not hsemotion_recognizer.load_model():
        print("✗ 情绪识别模型加载失败")
        return
    print("✓ 情绪识别模型加载成功")
    
    # 2. 打开摄像头
    print("\n[2/3] 打开摄像头...")
    
    # 尝试 DirectShow 后端
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    if not cap.isOpened():
        print("✗ 无法打开摄像头")
        return
    
    print("✓ 摄像头已打开 (DirectShow)")
    
    # 3. 开始检测
    print("\n[3/3] 开始检测 (按 'q' 退出)...")
    print("=" * 60)
    
    frame_count = 0
    last_time = time.time()
    fps = 0
    
    try:
        while True:
            # 读取帧
            ret, frame = cap.read()
            if not ret or frame is None:
                print("✗ 无法读取帧")
                break
            
            # 计算FPS
            frame_count += 1
            current_time = time.time()
            if current_time - last_time >= 1.0:
                fps = frame_count
                frame_count = 0
                last_time = current_time
            
            # 人脸检测
            faces = yolo_face_detector.detect(frame)
            
            # 对每个人脸进行情绪识别并画框
            for i, face in enumerate(faces):
                x, y, w, h = face.x, face.y, face.width, face.height
                
                # 确保坐标在有效范围内
                x = max(0, x)
                y = max(0, y)
                w = min(w, frame.shape[1] - x)
                h = min(h, frame.shape[0] - y)
                
                # 裁剪人脸区域
                face_img = frame[y:y+h, x:x+w]
                if face_img.size == 0:
                    continue
                
                # 情绪识别
                result = hsemotion_recognizer.recognize(face_img)
                emotion = result.emotion
                confidence = result.confidence
                valence = result.valence
                arousal = result.arousal
                
                # 获取颜色
                color = get_emotion_color(emotion)
                
                # 画人脸框
                cv2.rectangle(frame, (x, y), (x+w, y+h), color, 2)
                
                # 画标签背景
                print(f"emotion: {emotion}, confidence: {confidence:.2f}, valence: {valence:.2f}, arousal: {arousal:.2f}") 
                label = f"{get_emotion_cn(emotion)} {confidence:.2f}"
                
                # 计算文字尺寸
                (text_w, text_h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
                
                # 画背景矩形
                cv2.rectangle(frame, (x, y-text_h-10), (x+text_w+10, y), color, -1)
                
                # 写文字
                cv2.putText(frame, label, (x+5, y-5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                
                # 打印调试信息（每30帧打印一次）
                if frame_count % 30 == 0:
                    print(f"[检测] 人脸 {i+1}: 位置=({x},{y},{w},{h}), "
                          f"情绪={emotion}, 置信度={confidence:.2f}")
            
            # 显示FPS和人脸数
            cv2.putText(frame, f"FPS: {fps}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.putText(frame, f"Faces: {len(faces)}", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
            # 显示画面
            cv2.imshow("Face Detection & Emotion Recognition", frame)
            
            # 按 'q' 退出
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
                
    except Exception as e:
        print(f"\n✗ 发生错误: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # 释放资源
        cap.release()
        cv2.destroyAllWindows()
        print("\n✓ 测试结束")


if __name__ == "__main__":
    main()
