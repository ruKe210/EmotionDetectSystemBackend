from fastapi import APIRouter, Depends
from app.schemas import ResponseModel, SystemConfig
from app.api.deps import get_current_active_user, get_current_admin_user
from app.services.data_store import data_store
from datetime import datetime

router = APIRouter()


@router.get("", response_model=ResponseModel)
async def get_config(
    current_user: dict = Depends(get_current_active_user)
):
    """获取系统配置"""
    config = data_store.get_config()
    return ResponseModel(data=config)


@router.post("", response_model=ResponseModel)
async def update_config(
    config_data: SystemConfig,
    current_user: dict = Depends(get_current_admin_user)
):
    """更新系统配置"""
    update_dict = config_data.model_dump()
    data_store.update_config(update_dict)
    
    # 记录操作日志
    data_store.add_log({
        "date": datetime.now().strftime("%Y-%m-%d"),
        "time": datetime.now().strftime("%H:%M:%S"),
        "type": "operation",
        "operator": current_user["username"],
        "content": "更新系统配置",
        "ip": "127.0.0.1"
    })
    
    return ResponseModel(message="配置保存成功")