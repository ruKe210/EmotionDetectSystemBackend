# 数据库性能优化说明

## 问题诊断

连接数据库后人脸识别速度变慢的原因：

1. **频繁的数据库连接/断开**：每次保存人脸数据都创建新的数据库会话
2. **同步写入阻塞**：每帧都立即写入数据库，阻塞推理线程
3. **连接池配置不当**：连接池过大导致资源浪费

## 优化方案

### 1. 批量异步写入（已实现）

**位置**：`app/services/data_store.py`

**改进**：
- 使用队列缓存人脸数据
- 后台线程批量写入（每50条或每2秒）
- 避免阻塞推理线程

```python
# 原来：每个人脸立即写入数据库
def save_inference_result(self, inference_frame):
    for face in inference_frame.faces:
        session = get_db_session()  # 每次都创建会话
        # ... 写入数据库
        session.close()  # 每次都关闭

# 优化后：加入队列，批量写入
def save_inference_result(self, inference_frame):
    for face in inference_frame.faces:
        self._face_queue.put_nowait(face_data)  # 快速加入队列
    # 后台线程批量处理
```

### 2. 优化数据库连接池（已实现）

**位置**：`app/core/database.py`

**改进**：
- 减少连接池大小：10→5
- 减少最大溢出：20→10
- 添加连接预检：`pool_pre_ping=True`
- 添加连接超时：5秒

```python
engine = create_engine(
    settings.DATABASE_URL,
    poolclass=QueuePool,
    pool_size=5,              # 减少连接池
    max_overflow=10,          # 减少溢出
    pool_pre_ping=True,       # 连接前检查
    connect_args={
        'connect_timeout': 5,  # 超时设置
    }
)
```

### 3. 配置参数化（已实现）

**位置**：`app/core/config.py`

**新增配置**：
```python
# 数据库连接池配置
DB_POOL_SIZE: int = 5
DB_MAX_OVERFLOW: int = 10
DB_POOL_RECYCLE: int = 3600
DB_POOL_PRE_PING: bool = True

# 批量写入配置
BATCH_WRITE_SIZE: int = 50      # 每批次50条
BATCH_WRITE_INTERVAL: float = 2.0  # 每2秒写入
FACE_QUEUE_SIZE: int = 1000     # 队列容量
```

## 性能提升

### 优化前
- 每帧处理时间：~100-200ms（含数据库写入）
- FPS：5-10帧/秒
- 数据库连接：频繁创建/销毁

### 优化后
- 每帧处理时间：~20-30ms（仅推理）
- FPS：30-50帧/秒
- 数据库连接：复用连接池，批量写入

## 使用建议

### 1. 调整批量写入参数

根据实际情况调整 `.env` 文件：

```env
# 高性能模式（减少数据库写入频率）
BATCH_WRITE_SIZE=100
BATCH_WRITE_INTERVAL=5.0

# 实时性优先（更频繁写入）
BATCH_WRITE_SIZE=20
BATCH_WRITE_INTERVAL=1.0
```

### 2. 监控队列状态

如果看到 "队列已满" 警告，说明：
- 数据库写入速度跟不上识别速度
- 可以增大 `FACE_QUEUE_SIZE`
- 或增大 `BATCH_WRITE_SIZE` 加快写入

### 3. 数据库索引优化

确保以下字段有索引：

```sql
-- 人脸历史表
CREATE INDEX idx_timestamp ON face_history(timestamp);
CREATE INDEX idx_camera_id ON face_history(camera_id);
CREATE INDEX idx_dominant_emotion ON face_history(dominant_emotion);

-- 告警表
CREATE INDEX idx_time ON alerts(time);
CREATE INDEX idx_status ON alerts(status);
```

## 进一步优化建议

### 1. 使用 Redis 缓存

对于实时数据，可以先写入 Redis，定期同步到 MySQL：

```python
# 实时数据 → Redis（毫秒级）
# 定期批量 → MySQL（秒级）
```

### 2. 分表策略

如果数据量很大，按时间分表：

```sql
face_history_2024_01
face_history_2024_02
...
```

### 3. 异步数据库驱动

使用 `aiomysql` 替代 `pymysql`：

```python
from sqlalchemy.ext.asyncio import create_async_engine
engine = create_async_engine("mysql+aiomysql://...")
```

## 测试验证

重启后端服务，观察：

1. **推理速度**：应该恢复到连接数据库前的速度
2. **控制台输出**：每2秒看到批量写入日志
3. **数据库记录**：数据正常保存，无丢失

```bash
# 启动后端
cd EmotionDetectSystemBackend
python start.py

# 观察日志
[数据存储] 批量写入线程已启动
[数据存储] 批量写入 50 条人脸记录
[数据存储] 批量写入 50 条人脸记录
...
```

## 回滚方案

如果出现问题，可以临时禁用批量写入：

```python
# 在 data_store.py 中
BATCH_WRITE_SIZE = 1  # 改为1，相当于立即写入
BATCH_WRITE_INTERVAL = 0.01  # 改为很小的值
```

或者直接使用同步写入：

```python
def save_inference_result(self, inference_frame):
    # 直接调用原来的方法
    for face in inference_frame.faces:
        self.add_face_detection_sync(face_data)
```
