"""
局域网摄像头扫描工具 - 最终稳定版
自动扫描所有局域网，无数据库，不存任何东西
"""
import socket
import time
import cv2
from concurrent.futures import ThreadPoolExecutor, as_completed

# 固定只扫描 192.168.9.xxx 网段
TARGET_SUBNET = "192.168.9."

# 检查端口
def check_port(ip, port=554, timeout=0.4):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        return s.connect_ex((ip, port)) == 0
    except:
        return False

# 验证真RTSP
def is_real_rtsp(ip):
    try:
        s = socket.socket()
        s.settimeout(1)
        s.connect((ip, 554))
        s.send(b"OPTIONS * RTSP/1.0\r\nCSeq:1\r\n\r\n")
        d = s.recv(256)
        s.close()
        return d.startswith(b"RTSP/")
    except:
        return False

# 批量扫描
def scan_all():
    subnets = [TARGET_SUBNET]
    print(f"📶 仅扫描局域网网段: {subnets}")
    found = []

    for subnet in subnets:
        print(f"\n🔍 正在扫描: {subnet}0/24")
        ips = [f"{subnet}{i}" for i in range(1,255)]
        with ThreadPoolExecutor(50) as e:
            tasks = {e.submit(check_port, ip):ip for ip in ips}
            for f in as_completed(tasks):
                ip = tasks[f]
                if f.result() and is_real_rtsp(ip):
                    found.append(ip)
    return found

# 测试连接
RTSP_PATHS = ["/stream1","/stream2","/Streaming/Channels/101","/1","/","/cam/realmonitor?channel=1&subtype=0"]
def test_rtsp(ip, user, pwd):
    for path in RTSP_PATHS:
        url = f"rtsp://{user}:{pwd}@{ip}:554{path}"
        cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
        if cap.isOpened():
            ret, frame = cap.read()
            if ret:
                w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                cap.release()
                return url, w, h
        cap.release()
    return None,0,0

# 预览
def preview(url):
    cap = cv2.VideoCapture(url)
    while True:
        ret, f = cap.read()
        if not ret: break
        cv2.imshow("预览 | Q退出", f)
        if cv2.waitKey(1)&0xFF == ord("q"):
            break
    cap.release()
    cv2.destroyAllWindows()

# 主程序
def main():
    print("="*50)
    print("    局域网摄像头扫描（无数据库·稳定版）")
    print("="*50)

    cams = scan_all()
    if not cams:
        print("\n❌ 自动扫描未找到，可手动输入IP")
        ip = input("请输入摄像头IP: ").strip()
        if not ip: return
        cams = [ip]

    print(f"\n✅ 找到设备: {cams}")
    ip = cams[0] if len(cams)==1 else cams[int(input("选择序号: "))-1]

    print(f"\n=== 连接 {ip} ===")
    user = input("用户名(默认admin): ").strip() or "admin"
    pwd = input("密码: ").strip()

    url, w, h = test_rtsp(ip, user, pwd)
    if not url:
        print("❌ 连接失败")
        return

    print(f"\n✅ 成功!")
    print(f"RTSP: {url.replace(pwd,'****')}")
    print(f"分辨率: {w}x{h}")

    if input("\n预览画面? (y/n): ").lower()=="y":
        preview(url)

if __name__ == "__main__":
    main()