from pathlib import Path
from typing import Dict, Any
from fastapi import APIRouter, Depends
from app.schemas import ResponseModel, SystemConfig
from app.api.deps import get_current_active_user, get_current_admin_user
from app.services.data_store import data_store
from app.core.config import settings
from datetime import datetime

router = APIRouter()


def _get_default_config() -> Dict[str, Any]:
    return {
        "video": {
            "cameraId": str(settings.DEFAULT_CAMERA_ID),
            "resolution": f"{settings.VIDEO_WIDTH}x{settings.VIDEO_HEIGHT}",
            "fps": settings.VIDEO_FPS,
            "duration": max(1, int(settings.VIDEO_RECORD_SEGMENT_SECONDS / 60)),
        },
        "recognition": {
            "modelType": settings.RECOGNITION_MODEL_TYPE,
            "delayThreshold": settings.RECOGNITION_DELAY_THRESHOLD,
            "accuracyThreshold": settings.RECOGNITION_ACCURACY_THRESHOLD,
            "emotionChangeThreshold": settings.RECOGNITION_EMOTION_CHANGE_THRESHOLD,
        },
        "storage": {
            "path": settings.DATA_STORAGE_PATH,
            "period": settings.STORAGE_PERIOD_DAYS,
            "autoBackup": settings.STORAGE_AUTO_BACKUP,
            "backupFrequency": settings.STORAGE_BACKUP_FREQUENCY,
        },
        "permission": {
            "role": settings.PERMISSION_DEFAULT_ROLE,
            "permissions": [x.strip() for x in settings.PERMISSION_DEFAULT_ACTIONS.split(",") if x.strip()],
        },
        "ai": {
            "apiKey": settings.ARK_API_KEY,
            "baseUrl": settings.ARK_BASE_URL,
            "model": settings.ARK_MODEL,
        },
    }


def _deep_merge(base: Dict[str, Any], patch: Dict[str, Any]) -> Dict[str, Any]:
    result = dict(base)
    for key, value in patch.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _update_env_values(env_updates: Dict[str, str]):
    env_path = Path(settings.__class__.Config.env_file)
    env_path.parent.mkdir(parents=True, exist_ok=True)
    if not env_path.exists():
        env_path.write_text("", encoding="utf-8")

    lines = env_path.read_text(encoding="utf-8").splitlines()
    present_keys = set()
    output = []

    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            output.append(line)
            continue
        key = stripped.split("=", 1)[0].strip()
        if key in env_updates:
            output.append(f"{key}={env_updates[key]}")
            present_keys.add(key)
        else:
            output.append(line)

    for key, value in env_updates.items():
        if key not in present_keys:
            output.append(f"{key}={value}")

    env_path.write_text("\n".join(output) + "\n", encoding="utf-8")


def _to_env_updates(config: Dict[str, Any]) -> Dict[str, str]:
    video = config.get("video", {})
    recognition = config.get("recognition", {})
    storage = config.get("storage", {})
    permission = config.get("permission", {})
    ai = config.get("ai", {})

    resolution = str(video.get("resolution", "640x480"))
    width, height = 640, 480
    if "x" in resolution:
        parts = resolution.lower().split("x")
        try:
            width = int(parts[0])
            height = int(parts[1])
        except Exception:
            pass

    permissions = permission.get("permissions", [])
    if isinstance(permissions, list):
        permissions_str = ",".join(str(x) for x in permissions)
    else:
        permissions_str = str(permissions)

    return {
        "VIDEO_FPS": str(int(video.get("fps", settings.VIDEO_FPS))),
        "VIDEO_WIDTH": str(width),
        "VIDEO_HEIGHT": str(height),
        "VIDEO_RECORD_SEGMENT_SECONDS": str(int(video.get("duration", 1)) * 60),
        "RECOGNITION_MODEL_TYPE": str(recognition.get("modelType", settings.RECOGNITION_MODEL_TYPE)),
        "RECOGNITION_DELAY_THRESHOLD": str(int(recognition.get("delayThreshold", settings.RECOGNITION_DELAY_THRESHOLD))),
        "RECOGNITION_ACCURACY_THRESHOLD": str(float(recognition.get("accuracyThreshold", settings.RECOGNITION_ACCURACY_THRESHOLD))),
        "RECOGNITION_EMOTION_CHANGE_THRESHOLD": str(float(recognition.get("emotionChangeThreshold", settings.RECOGNITION_EMOTION_CHANGE_THRESHOLD))),
        "DATA_STORAGE_PATH": str(storage.get("path", settings.DATA_STORAGE_PATH)),
        "STORAGE_PERIOD_DAYS": str(int(storage.get("period", settings.STORAGE_PERIOD_DAYS))),
        "STORAGE_AUTO_BACKUP": str(bool(storage.get("autoBackup", settings.STORAGE_AUTO_BACKUP))).lower(),
        "STORAGE_BACKUP_FREQUENCY": str(storage.get("backupFrequency", settings.STORAGE_BACKUP_FREQUENCY)),
        "PERMISSION_DEFAULT_ROLE": str(permission.get("role", settings.PERMISSION_DEFAULT_ROLE)),
        "PERMISSION_DEFAULT_ACTIONS": permissions_str,
        "ARK_API_KEY": str(ai.get("apiKey", settings.ARK_API_KEY)),
        "ARK_BASE_URL": str(ai.get("baseUrl", settings.ARK_BASE_URL)),
        "ARK_MODEL": str(ai.get("model", settings.ARK_MODEL)),
    }


def _apply_runtime_config(config: Dict[str, Any]):
    env_updates = _to_env_updates(config)
    settings.VIDEO_FPS = int(env_updates["VIDEO_FPS"])
    settings.VIDEO_WIDTH = int(env_updates["VIDEO_WIDTH"])
    settings.VIDEO_HEIGHT = int(env_updates["VIDEO_HEIGHT"])
    settings.VIDEO_RECORD_SEGMENT_SECONDS = int(env_updates["VIDEO_RECORD_SEGMENT_SECONDS"])
    settings.RECOGNITION_MODEL_TYPE = env_updates["RECOGNITION_MODEL_TYPE"]
    settings.RECOGNITION_DELAY_THRESHOLD = int(env_updates["RECOGNITION_DELAY_THRESHOLD"])
    settings.RECOGNITION_ACCURACY_THRESHOLD = float(env_updates["RECOGNITION_ACCURACY_THRESHOLD"])
    settings.RECOGNITION_EMOTION_CHANGE_THRESHOLD = float(env_updates["RECOGNITION_EMOTION_CHANGE_THRESHOLD"])
    settings.DATA_STORAGE_PATH = env_updates["DATA_STORAGE_PATH"]
    settings.STORAGE_PERIOD_DAYS = int(env_updates["STORAGE_PERIOD_DAYS"])
    settings.STORAGE_AUTO_BACKUP = env_updates["STORAGE_AUTO_BACKUP"].lower() == "true"
    settings.STORAGE_BACKUP_FREQUENCY = env_updates["STORAGE_BACKUP_FREQUENCY"]
    settings.PERMISSION_DEFAULT_ROLE = env_updates["PERMISSION_DEFAULT_ROLE"]
    settings.PERMISSION_DEFAULT_ACTIONS = env_updates["PERMISSION_DEFAULT_ACTIONS"]
    settings.ARK_API_KEY = env_updates["ARK_API_KEY"]
    settings.ARK_BASE_URL = env_updates["ARK_BASE_URL"]
    settings.ARK_MODEL = env_updates["ARK_MODEL"]


@router.get("", response_model=ResponseModel)
async def get_config(
    current_user: dict = Depends(get_current_active_user)
):
    """获取系统配置"""
    db_config = data_store.get_config()
    config = _deep_merge(_get_default_config(), db_config)
    return ResponseModel(data=config)


@router.post("", response_model=ResponseModel)
async def update_config(
    config_data: SystemConfig,
    current_user: dict = Depends(get_current_admin_user)
):
    """更新系统配置"""
    update_dict = config_data.model_dump()
    data_store.update_config(update_dict)
    _apply_runtime_config(update_dict)
    _update_env_values(_to_env_updates(update_dict))
    
    # 记录操作日志
    data_store.add_log({
        "date": datetime.now().strftime("%Y-%m-%d"),
        "time": datetime.now().strftime("%H:%M:%S"),
        "type": "operation",
        "operator": current_user["username"],
        "content": "更新系统配置",
        "ip": "127.0.0.1"
    })
    
    return ResponseModel(message="配置保存成功，已同步到 .env")