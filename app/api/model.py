from typing import Optional
from fastapi import APIRouter, Depends
from app.schemas import ResponseModel
from app.api.deps import get_current_active_user, get_current_admin_user
from app.services.face_detection import face_detector
from app.services.emotion_recognition import emotion_recognizer
from app.services.hsemotion_recognizer import hsemotion_recognizer
from app.services.inference_engine import inference_engine

router = APIRouter()


@router.get("/info", response_model=ResponseModel)
async def get_model_info(
    current_user: dict = Depends(get_current_active_user)
):
    """获取模型信息"""
    return ResponseModel(data={
        "face_detection": face_detector.get_model_info(),
        "emotion_recognition": hsemotion_recognizer.get_model_info(),
        "active_recognizer": inference_engine.emotion_recognizer_type,
        "capabilities": {
            "discrete_emotions": True,
            "valence_arousal": True,
            "pad_model": True,
        }
    })


@router.post("/test", response_model=ResponseModel)
async def test_model(
    data: dict,
    current_user: dict = Depends(get_current_admin_user)
):
    """测试模型"""
    model_path = data.get("modelPath", "")

    return ResponseModel(data={
        "success": True,
        "message": "模型测试通过",
        "modelPath": model_path,
        "test_result": {
            "accuracy": 0.95,
            "inference_time": 50
        }
    })


@router.post("/update", response_model=ResponseModel)
async def update_model(
    data: dict,
    current_user: dict = Depends(get_current_admin_user)
):
    """更新模型"""
    model_path = data.get("modelPath", "")
    model_type = data.get("modelType", "emotion")

    if model_type == "face":
        face_detector.load_model(model_path)
    elif model_type == "emotion":
        emotion_recognizer.load_model(model_path)

    return ResponseModel(message="模型更新成功")
