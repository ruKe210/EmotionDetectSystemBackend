"""
局域网摄像头扫描 & 添加工具
用法: python scan_cameras.py
功能:
  1. 自动获取本机局域网网段
  2. 扫描开放 554 (RTSP) 端口的设备
  3. 让用户输入账号密码
  4. 测试 RTSP 连接
  5. 成功后保存到数据库
"""
import socket
import struct
import threading
import time
import sys
import cv2
from concurrent.futures import ThreadPoolExecutor, as_completed


def get_local_ip():
    """获取本机局域网 IP"""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip


def get_subnet(ip):
    """从 IP 获取 /24 网段前缀，如 192.168.8."""
    parts = ip.split(".")
    return f"{parts[0]}.{parts[1]}.{parts[2]}."


def check_rtsp_port(ip, port=554, timeout=0.5):
    """检测指定 IP 的 RTSP 端口是否开放"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((ip, port))
        sock.close()
        return result == 0
    except Exception:
        return False


def scan_network(subnet, port=554):
    """扫描整个 /24 网段，返回开放 RTSP 端口的 IP 列表"""
    found = []
    total = 254

    print(f"\n正在扫描网段 {subnet}0/24 的 {port} 端口...")
    print(f"{'=' * 50}")

    with ThreadPoolExecutor(max_workers=50) as executor:
        futures = {}
        for i in range(1, 255):
            ip = f"{subnet}{i}"
            futures[executor.submit(check_rtsp_port, ip, port)] = ip

        done_count = 0
        for future in as_completed(futures):
            done_count += 1
            ip = futures[future]
            # 进度条
            progress = done_count / total
            bar = "█" * int(progress * 30) + "░" * (30 - int(progress * 30))
            print(f"\r  [{bar}] {done_count}/{total}", end="", flush=True)

            if future.result():
                found.append(ip)

    print(f"\n{'=' * 50}")
    return found


# 常见摄像头品牌的 RTSP 路径模板
RTSP_PATHS = [
    "/stream1",              # 海康 主码流
    "/stream2",              # 海康 子码流
    "/cam/realmonitor?channel=1&subtype=0",  # 大华 主码流
    "/cam/realmonitor?channel=1&subtype=1",  # 大华 子码流
    "/live/ch00_0",          # 中维
    "/h264/ch1/main/av_stream",  # 海康老款
    "/Streaming/Channels/101",   # 海康 ISAPI
    "/1",                    # 通用
    "/",                     # 通用
]


def test_rtsp_connection(ip, username, password, port=554):
    """尝试多种 RTSP 路径，返回第一个能连通的完整 URL"""
    print(f"\n正在测试 {ip} 的 RTSP 连接...")

    for path in RTSP_PATHS:
        url = f"rtsp://{username}:{password}@{ip}:{port}{path}"
        display_url = f"rtsp://{username}:****@{ip}:{port}{path}"
        print(f"  尝试: {display_url} ... ", end="", flush=True)

        cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)

        # 设置超时：最多等 5 秒
        start = time.time()
        while not cap.isOpened() and time.time() - start < 5:
            time.sleep(0.1)

        if cap.isOpened():
            ret, frame = cap.read()
            if ret and frame is not None:
                w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                cap.release()
                print(f"成功! ({w}x{h})")
                return url, path, w, h
            cap.release()
            print("已连接但无画面")
        else:
            cap.release()
            print("失败")

    return None, None, 0, 0


def preview_camera(url, title="摄像头预览"):
    """弹窗预览摄像头画面"""
    print(f"\n正在打开预览窗口... 按 Q 退出预览")
    cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
    if not cap.isOpened():
        print("无法打开预览")
        return

    cv2.namedWindow(title, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(title, 960, 540)

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        cv2.putText(frame, "Preview - Press Q to close", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.imshow(title, frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()


def save_to_database(name, ip, rtsp_url, width, height):
    """保存摄像头信息到数据库"""
    try:
        # 动态导入，避免未安装依赖时脚本无法启动
        sys.path.insert(0, ".")
        from app.core.database import get_db_session
        from app.models.db_models import Camera
        import uuid
        from datetime import datetime

        session = get_db_session()
        try:
            camera_id = str(uuid.uuid4())[:8]
            camera = Camera(
                id=camera_id,
                name=name,
                type="rtsp",
                ip=ip,
                location="",
                status="online",
                resolution=f"{width}x{height}",
                fps=25,
                rtsp_url=rtsp_url,
                created_at=datetime.now(),
            )
            session.add(camera)
            session.commit()
            print(f"\n已保存到数据库，摄像头 ID: {camera_id}")
            return camera_id
        except Exception as e:
            session.rollback()
            print(f"\n保存失败: {e}")
            print("提示: Camera 表可能缺少 rtsp_url 字段，需要先执行数据库迁移")
            return None
        finally:
            session.close()
    except ImportError as e:
        print(f"\n无法导入数据库模块: {e}")
        print("请在 EmotionDetectSystemBackend 目录下运行此脚本")
        return None


def main():
    print("=" * 50)
    print("  局域网摄像头扫描 & 添加工具")
    print("=" * 50)

    # 1. 获取本机 IP
    local_ip = get_local_ip()
    subnet = get_subnet(local_ip)
    print(f"\n本机 IP: {local_ip}")
    print(f"扫描网段: {subnet}0/24")

    # 2. 扫描
    found_ips = scan_network(subnet)

    if not found_ips:
        print("\n未发现开放 RTSP 端口的设备")
        print("可能原因:")
        print("  - 摄像头未开启 RTSP 服务")
        print("  - 摄像头使用了非标准端口")
        print("  - 防火墙阻止了扫描")

        manual = input("\n是否手动输入 IP? (y/n): ").strip().lower()
        if manual == "y":
            ip = input("请输入摄像头 IP: ").strip()
            found_ips = [ip]
        else:
            return

    # 3. 展示结果
    # 过滤掉本机 IP
    found_ips = [ip for ip in found_ips if ip != local_ip]

    print(f"\n发现 {len(found_ips)} 个可能的摄像头设备:")
    for i, ip in enumerate(found_ips, 1):
        print(f"  [{i}] {ip}")

    # 4. 选择设备
    if len(found_ips) == 1:
        selected_ip = found_ips[0]
        print(f"\n自动选择: {selected_ip}")
    else:
        choice = input(f"\n选择设备 (1-{len(found_ips)}): ").strip()
        try:
            selected_ip = found_ips[int(choice) - 1]
        except (ValueError, IndexError):
            print("无效选择")
            return

    # 5. 输入凭据
    print(f"\n为 {selected_ip} 配置连接信息:")
    username = input("  用户名 (默认 admin): ").strip() or "admin"
    password = input("  密码: ").strip()

    if not password:
        print("密码不能为空")
        return

    # 6. 测试连接
    url, path, w, h = test_rtsp_connection(selected_ip, username, password)

    if not url:
        print("\n所有 RTSP 路径均连接失败")
        print("可能原因:")
        print("  - 用户名或密码错误")
        print("  - 摄像头使用了非标准 RTSP 路径")
        custom = input("\n是否手动输入完整 RTSP URL? (y/n): ").strip().lower()
        if custom == "y":
            url = input("请输入完整 RTSP URL: ").strip()
            cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
            if cap.isOpened():
                ret, frame = cap.read()
                if ret:
                    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                    print(f"连接成功! ({w}x{h})")
                else:
                    print("连接失败")
                    return
                cap.release()
            else:
                print("连接失败")
                return
        else:
            return

    # 7. 预览
    do_preview = input("\n是否预览画面? (y/n): ").strip().lower()
    if do_preview == "y":
        preview_camera(url, f"预览 - {selected_ip}")

    # 8. 保存
    do_save = input("\n是否保存到数据库? (y/n): ").strip().lower()
    if do_save == "y":
        name = input(f"  摄像头名称 (默认 '网络摄像头-{selected_ip}'): ").strip()
        name = name or f"网络摄像头-{selected_ip}"
        save_to_database(name, selected_ip, url, w, h)

    print("\n完成!")
    # 打印最终的 RTSP URL（隐藏密码）
    safe_url = url.replace(password, "****")
    print(f"RTSP URL: {safe_url}")


if __name__ == "__main__":
    main()
