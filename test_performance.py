"""
性能测试脚本 - 验证数据库优化效果
"""
import time
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from app.services.data_store import data_store
from datetime import datetime


def test_batch_write_performance():
    """测试批量写入性能"""
    print("=" * 60)
    print("数据库批量写入性能测试")
    print("=" * 60)
    
    # 模拟人脸数据
    test_data = {
        "id": f"test_face_{int(time.time())}",
        "camera_id": "test_camera",
        "expressions": {
            "happy": 0.8,
            "sad": 0.1,
            "neutral": 0.1
        },
        "dominant_emotion": "happy",
        "confidence": 0.85,
        "timestamp": datetime.now(),
        "valence": 0.7,
        "arousal": 0.5,
        "pleasure": 0.7,
        "pad_arousal": 0.5,
        "dominance": 0.6
    }
    
    # 测试1：单条写入速度
    print("\n[测试1] 单条数据加入队列速度")
    start = time.time()
    for i in range(100):
        test_data["id"] = f"test_face_{i}"
        data_store.add_face_detection(test_data)
    elapsed = time.time() - start
    print(f"✓ 100条数据加入队列耗时: {elapsed*1000:.2f}ms")
    print(f"✓ 平均每条: {elapsed*10:.2f}ms")
    print(f"✓ 理论 FPS: {100/elapsed:.1f}")
    
    # 测试2：队列状态
    print("\n[测试2] 队列状态")
    queue_size = data_store._face_queue.qsize()
    print(f"✓ 当前队列大小: {queue_size}")
    print(f"✓ 队列最大容量: {data_store._face_queue.maxsize}")
    print(f"✓ 批量写入线程运行: {data_store._writer_running}")
    
    # 等待批量写入
    print("\n[测试3] 等待批量写入...")
    print(f"等待 {data_store._batch_interval + 1} 秒...")
    time.sleep(data_store._batch_interval + 1)
    
    queue_size_after = data_store._face_queue.qsize()
    print(f"✓ 写入后队列大小: {queue_size_after}")
    print(f"✓ 已写入数据量: {queue_size - queue_size_after}")
    
    # 测试3：配置参数
    print("\n[测试4] 配置参数")
    print(f"✓ 批量大小: {data_store._batch_size}")
    print(f"✓ 批量间隔: {data_store._batch_interval}秒")
    print(f"✓ 队列容量: {data_store._face_queue.maxsize}")
    
    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)
    
    # 性能评估
    print("\n[性能评估]")
    if elapsed * 10 < 1:  # 每条 < 1ms
        print("✅ 优秀：队列操作非常快，不会阻塞推理")
    elif elapsed * 10 < 5:  # 每条 < 5ms
        print("✅ 良好：队列操作较快，影响很小")
    else:
        print("⚠️  警告：队列操作较慢，可能影响性能")
    
    print("\n[建议]")
    print("1. 启动后端服务: python start.py")
    print("2. 观察日志中的批量写入信息")
    print("3. 前端测试人脸识别速度")
    print("4. 如果速度仍慢，检查数据库连接和网络")


def test_database_connection():
    """测试数据库连接"""
    print("\n" + "=" * 60)
    print("数据库连接测试")
    print("=" * 60)
    
    try:
        from app.core.database import get_db_session
        
        print("\n[测试] 创建数据库会话...")
        start = time.time()
        session = get_db_session()
        elapsed = time.time() - start
        print(f"✓ 会话创建耗时: {elapsed*1000:.2f}ms")
        
        print("\n[测试] 执行简单查询...")
        start = time.time()
        result = session.execute("SELECT 1").fetchone()
        elapsed = time.time() - start
        print(f"✓ 查询耗时: {elapsed*1000:.2f}ms")
        print(f"✓ 查询结果: {result}")
        
        session.close()
        print("✓ 数据库连接正常")
        
    except Exception as e:
        print(f"❌ 数据库连接失败: {e}")
        print("\n请检查:")
        print("1. MySQL 服务是否启动")
        print("2. 数据库配置是否正确 (config.py)")
        print("3. 数据库用户权限")


if __name__ == "__main__":
    print("\n🚀 开始性能测试...\n")
    
    # 测试数据库连接
    test_database_connection()
    
    # 测试批量写入
    test_batch_write_performance()
    
    print("\n✅ 所有测试完成！\n")
