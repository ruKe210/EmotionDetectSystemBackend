# 模型文件说明

## 所需模型文件

### 1. YOLOv8-face ONNX 模型（可选）

**文件名**: `yolov8n-face.onnx`

**用途**: 高精度人脸检测

**下载方式**:

#### 方式一：从 GitHub 下载
1. 访问: https://github.com/akanametov/yolov8-face/releases
2. 下载 `yolov8n-face.onnx`
3. 放到此目录

#### 方式二：使用 Python 下载
```python
import urllib.request
url = "https://github.com/akanametov/yolov8-face/releases/download/v0.0.1/yolov8n-face.onnx"
urllib.request.urlretrieve(url, "yolov8n-face.onnx")
```

**如果没有此模型**: 系统会自动使用 OpenCV DNN 人脸检测器（已内置）

---

### 2. 情绪识别模型（推荐）

**文件名**: 
- `emotion_deploy.prototxt`
- `emotion.caffemodel`

**用途**: 7类情绪识别

**情绪类别**:
1. angry - 愤怒
2. disgusted - 厌恶
3. fearful - 恐惧
4. happy - 开心
5. sad - 悲伤
6. surprised - 惊讶
7. neutral - 平静

**下载方式**:

#### 推荐方案：从 GitHub 下载（最容易获取）

**步骤 1**: 访问项目仓库
```
https://github.com/petercunha/EmotionRecognition
```

**步骤 2**: 下载模型文件
在仓库的 `models/` 目录下找到：
- `emotion_deploy.prototxt`
- `emotion.caffemodel`

**步骤 3**: 放到此目录
```
backend/app/models/
├── emotion_deploy.prototxt
├── emotion.caffemodel
└── README.md
```

#### 备用下载链接

如果 GitHub 访问慢，可以从以下镜像下载：

**CSDN 资源**:
- 搜索 "emotion recognition caffe model"
- 或访问: https://download.csdn.net/

**百度网盘**（可能需要搜索）:
- 搜索关键词: "FER2013 emotion caffemodel"

---

## 模型输入输出规范

### YOLOv8-face
- **输入**: `(1, 3, 640, 640)` - RGB 图像，归一化到 [0, 1]
- **输出**: `(1, 5, 8400)` - 5 = 4(box) + 1(confidence)

### OpenCV DNN 情绪识别 (Caffe)
- **输入**: `(1, 1, 48, 48)` - 灰度图，归一化到 [0, 1]
- **输出**: `(1, 7)` - 7类情绪的概率分布

---

## 当前状态

如果没有模型文件，系统将使用**模拟模式**：
- 人脸检测：使用 OpenCV DNN（已内置，无需下载）
- 情绪识别：基于图像亮度/对比度的简单模拟

**建议**: 下载情绪识别模型以获得更好的识别效果！

---

## 快速开始

### 最简单的方案（推荐）

只需要下载**情绪识别模型**即可：

1. 访问 https://github.com/petercunha/EmotionRecognition
2. 下载 `emotion_deploy.prototxt` 和 `emotion.caffemodel`
3. 放到 `backend/app/models/` 目录
4. 重启后端服务

### 进阶方案（高精度）

同时下载两个模型：
1. YOLOv8-face: https://github.com/akanametov/yolov8-face/releases
2. 情绪识别: https://github.com/petercunha/EmotionRecognition

---

## 验证模型

放置模型后，启动后端服务，查看日志：
```
✓ YOLOv8-face 模型加载成功  # 如果使用 YOLO
或
YOLOv8-face 模型未加载，使用备用检测器  # 使用 OpenCV DNN

✓ OpenCV DNN 情绪识别模型加载成功  # 情绪识别模型加载成功
```

如果看到以上信息，说明模型已正确加载！
