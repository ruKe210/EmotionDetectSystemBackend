"""
远程摄像头测试脚本（低延迟版）
用法: python remote_camera.py
"""
import cv2
import sys
import os
import time

RTSP_URL = "rtsp://admin:su15906477192@192.168.8.156:554/stream1"


def create_low_latency_capture(url):
    """创建低延迟的 RTSP 连接"""
    # 设置 FFMPEG 环境变量：使用 UDP + 减小缓冲
    os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = (
        "rtsp_transport;udp|"        # UDP 比 TCP 延迟低
        "fflags;nobuffer|"           # 禁用输入缓冲
        "flags;low_delay|"           # 低延迟标志
        "framedrop;1|"               # 允许丢帧
        "max_delay;500000|"          # 最大延迟 0.5 秒
        "analyzeduration;500000|"    # 减少分析时长
        "probesize;32768"            # 减小探测大小
    )

    cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)

    if cap.isOpened():
        # 减小 OpenCV 内部缓冲区到 1 帧
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    return cap


def main():
    print(f"正在连接: {RTSP_URL}")
    print("使用 UDP + 低延迟模式...")

    cap = create_low_latency_capture(RTSP_URL)

    if not cap.isOpened():
        print("连接失败，请检查地址和网络")
        sys.exit(1)

    ret, frame = cap.read()
    if not ret or frame is None:
        print("连接成功但无法读取画面")
        cap.release()
        sys.exit(1)

    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    print(f"连接成功! 分辨率: {w}x{h}")
    print("按 Q 键退出")

    window_name = "RTSP Low Latency"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(window_name, 960, 540)

    fps_count = 0
    fps_time = time.time()
    display_fps = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            print("画面中断，重连...")
            cap.release()
            cap = create_low_latency_capture(RTSP_URL)
            continue

        # 计算实际 FPS
        fps_count += 1
        now = time.time()
        if now - fps_time >= 1.0:
            display_fps = fps_count
            fps_count = 0
            fps_time = now

        # 显示信息
        cv2.putText(frame, f"RTSP UDP | {w}x{h} | {display_fps} FPS", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        cv2.imshow(window_name, frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()
    print("已退出")


if __name__ == "__main__":
    main()
