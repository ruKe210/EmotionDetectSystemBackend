# EmotionDetectSystemBackend 后端说明

基于 FastAPI 的情绪识别后端，提供实时识别、告警、报表统计、智能分析与 WebSocket 推送能力。

## 1. 主要功能

- 摄像头管理与推理引擎调度
- 人脸历史记录存储与统计
- 告警生成与处理（含处理备注）
- 报表接口（摘要、情绪分布、时段频次、趋势）
- 智能分析接口（火山方舟 OpenAI 兼容）
- WebSocket 实时推送
- 告警截图与录制文件静态挂载

## 2. 技术栈

- FastAPI
- SQLAlchemy
- Pydantic / pydantic-settings
- OpenAI Python SDK（对接 ARK）
- OpenCV / ONNX Runtime
- Uvicorn

## 3. 目录结构（核心）

```text
app/
├── api/                 # REST API 路由
├── core/                # 配置、数据库等核心模块
├── models/              # ORM 模型
├── schemas/             # Pydantic 模型
├── services/            # 推理、告警、业务服务
├── websocket/           # WebSocket 路由与管理
└── main.py              # 应用入口
```

## 4. 环境准备

- Python 3.10+（建议）
- MySQL（默认库名：`emotion_detect`）

安装依赖：

```bash
cd EmotionDetectSystemBackend
pip install -r requirements.txt
```

## 5. 启动方式

方式一（推荐）：

```bash
python start.py
```

方式二：

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

服务地址：

- API 文档：`http://localhost:8000/docs`
- 健康检查：`http://localhost:8000/health`

## 6. 关键配置

配置类在 `app/core/config.py`，同时支持读取后端根目录 `.env`。

重点配置项：

- `DB_HOST / DB_PORT / DB_USER / DB_PASSWORD / DB_NAME`
- `CORS_ORIGINS`（推荐 JSON 数组格式）
- `ARK_API_KEY`
- `ARK_BASE_URL`（当前要求不带 `chat/completions`）
- `ARK_MODEL`

## 7. 报表相关接口

前缀：`/api/reports`

- `GET /summary`：摘要统计
- `GET /emotion-distribution`：情绪占比
- `GET /hourly`：时段识别频次
- `GET /trend`：趋势统计
- `GET /intelligent-analysis`：智能分析文本

统一查询参数：

- `reportType`：`daily | weekly | monthly | custom`
- `startDate`：开始日期（日报/周报/月报/自定义均可）
- `endDate`：结束日期（自定义常用）
- `device`：设备 ID（可选）

## 8. 智能分析（ARK）说明

后端实现要点：

- 仅在接口调用时触发（由前端导出按钮触发）
- AI 请求放入 `asyncio.to_thread`，避免阻塞主事件循环
- 支持候选模型回退策略
- 会打印调试日志（POST URL、模型、脱敏 Key、脱敏 curl）

排查建议：

1. 先运行 `test_ark_api_connectivity.py` 验证 key、base_url、model
2. 再调用 `/api/reports/intelligent-analysis`
3. 对照后端日志确认实际生效配置

## 9. 静态资源挂载

由 `app/main.py` 挂载：

- `/recordings` -> `data/storage/recordings`
- `/alert_images` -> `data/storage/alert_images`

## 10. 常见问题

### 10.1 智能分析提示未启用

- 检查 `ARK_API_KEY` 是否为空
- 确认 `.env` 位于后端根目录且格式正确

### 10.2 CORS 配置报错

- `pydantic-settings` 建议使用 JSON 数组格式，例如：
  `["http://localhost:3000","http://127.0.0.1:3000","http://localhost:5173","http://127.0.0.1:5173"]`

### 10.3 前端能打开但接口失败

- 确认前端代理与后端端口一致
- 确认登录 token 有效
- 检查数据库连接是否正常

## 11. 说明

仓库中保留了部分历史文档（如性能、数据库优化说明），用于记录阶段性优化，不影响本 README 的主流程。
