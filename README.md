# 情绪识别管理系统后端

基于机器视觉的情绪识别管理系统后端服务，使用 FastAPI 框架开发。

## 功能特性

- **视频流管理**: 支持多路视频流（最多8路），可调用笔记本内置摄像头
- **人脸检测**: 预留 MTCNN 等算法接口，当前使用模拟数据
- **情绪识别**: 预留 CNN+LSTM 模型接口，支持离散+连续情绪识别
- **实时推送**: WebSocket 实时推送人脸检测、统计数据、告警信息
- **数据存储**: 模拟数据存储，预留数据库接口
- **RESTful API**: 完整的 API 接口，支持用户、摄像头、告警、日志等管理

## 项目结构

```
backend/
├── app/
│   ├── api/                    # API路由
│   │   ├── __init__.py
│   │   ├── auth.py            # 认证接口
│   │   ├── users.py           # 用户管理
│   │   ├── cameras.py         # 摄像头管理
│   │   ├── face.py            # 人脸识别
│   │   ├── alerts.py          # 告警管理
│   │   ├── logs.py            # 日志管理
│   │   ├── config.py          # 系统配置
│   │   ├── reports.py         # 报表统计
│   │   ├── system.py          # 系统状态
│   │   ├── model.py           # 模型管理
│   │   └── deps.py            # 依赖注入
│   ├── core/                   # 核心配置
│   │   ├── config.py          # 应用配置
│   │   └── security.py        # 安全相关
│   ├── schemas/                # 数据模型
│   │   ├── common.py
│   │   ├── user.py
│   │   ├── camera.py
│   │   ├── face.py
│   │   ├── emotion.py
│   │   ├── alert.py
│   │   ├── log.py
│   │   ├── config.py
│   │   └── report.py
│   ├── services/               # 业务逻辑
│   │   ├── video_stream.py    # 视频流管理
│   │   ├── face_detection.py  # 人脸检测
│   │   ├── emotion_recognition.py  # 情绪识别
│   │   └── data_store.py      # 数据存储
│   ├── websocket/              # WebSocket
│   │   ├── manager.py         # 连接管理
│   │   └── routes.py          # 路由定义
│   └── main.py                 # 应用入口
├── start.py                    # 启动脚本
├── requirements.txt            # 依赖列表
├── .env.example               # 环境变量示例
└── README.md                  # 项目说明
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

或者使用启动脚本自动安装：

```bash
python start.py --install
```

### 2. 启动服务

```bash
# 使用启动脚本
python start.py

# 或者使用 uvicorn 直接启动
uvicorn app.main:app --reload
```

### 3. 访问服务

- API文档: http://localhost:8000/docs
- 健康检查: http://localhost:8000/health
- WebSocket: ws://localhost:8000/ws/face

## API 接口列表

### 认证接口
- `POST /api/auth/login` - 用户登录
- `POST /api/auth/logout` - 用户登出
- `POST /api/auth/refresh` - 刷新令牌

### 用户管理
- `GET /api/users` - 获取用户列表
- `POST /api/users` - 创建用户
- `PUT /api/users/{id}` - 更新用户
- `DELETE /api/users/{id}` - 删除用户
- `PUT /api/users/{id}/status` - 更新用户状态

### 摄像头管理
- `GET /api/camera/list` - 获取摄像头列表
- `GET /api/camera/{id}` - 获取摄像头详情
- `POST /api/camera` - 创建摄像头
- `PUT /api/camera/{id}` - 更新摄像头
- `DELETE /api/camera/{id}` - 删除摄像头
- `POST /api/camera/{id}/toggle` - 切换摄像头状态

### 人脸识别
- `GET /api/face/stats` - 获取统计信息
- `GET /api/face/realtime` - 获取实时人脸数据
- `GET /api/face/history` - 获取历史记录
- `GET /api/face/export` - 导出数据

### 告警管理
- `GET /api/alerts` - 获取告警列表
- `GET /api/alerts/{id}` - 获取告警详情
- `POST /api/alerts/{id}/handle` - 处理告警
- `POST /api/alerts/{id}/ignore` - 忽略告警
- `POST /api/alerts/batch/handle` - 批量处理

### 日志管理
- `GET /api/logs` - 获取日志列表
- `GET /api/logs/export` - 导出日志
- `POST /api/logs/clear` - 清空日志

### 系统配置
- `GET /api/config` - 获取配置
- `POST /api/config` - 更新配置

### 报表统计
- `GET /api/reports/summary` - 获取摘要
- `GET /api/reports/emotion-distribution` - 情绪分布
- `GET /api/reports/hourly` - 每小时统计
- `GET /api/reports/trend` - 趋势数据

### 系统状态
- `GET /api/system/status` - 系统状态
- `GET /api/system/health` - 健康检查

### 模型管理
- `GET /api/model/info` - 模型信息
- `POST /api/model/test` - 测试模型
- `POST /api/model/update` - 更新模型

## WebSocket 接口

- `ws://localhost:8000/ws/face` - 实时人脸数据
- `ws://localhost:8000/ws/stats` - 实时统计数据
- `ws://localhost:8000/ws/alerts` - 实时告警
- `ws://localhost:8000/ws/video/{camera_id}` - 视频流

## 默认账号

- 用户名: `admin`
- 密码: `admin123`

## 后续开发

### 接入真实的人脸检测模型

修改 `app/services/face_detection.py`：

```python
def load_model(self, model_path: Optional[str] = None):
    from mtcnn import MTCNN
    self.model = MTCNN()
    self.is_loaded = True

def detect(self, frame: np.ndarray) -> List[FaceDetectionResult]:
    # 使用真实模型进行检测
    results = self.model.detect_faces(frame)
    # ... 处理检测结果
```

### 接入真实的情绪识别模型

修改 `app/services/emotion_recognition.py`：

```python
def load_model(self, model_path: Optional[str] = None):
    import torch
    self.model = torch.load(model_path)
    self.model.eval()
    self.is_loaded = True

def recognize(self, face_image: np.ndarray) -> EmotionRecognitionResult:
    # 使用真实模型进行识别
    with torch.no_grad():
        output = self.model(face_image)
    # ... 处理识别结果
```

### 接入真实数据库

修改 `app/services/data_store.py`，将 MockDataStore 替换为真实的数据库操作：

```python
# 使用 SQLAlchemy 或 Tortoise-ORM
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

class DatabaseStore:
    def __init__(self):
        self.engine = create_engine("mysql://user:password@localhost/dbname")
        # ...
```

## 技术栈

- **框架**: FastAPI
- **服务器**: Uvicorn
- **视频处理**: OpenCV
- **认证**: JWT
- **实时通信**: WebSocket

## 许可证

MIT License