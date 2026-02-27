from datetime import timedelta
from fastapi import APIRouter, HTTPException, status
from app.core.security import verify_password, create_access_token
from app.schemas import ResponseModel, UserLogin
from app.services.data_store import data_store

router = APIRouter()


@router.post("/login")
async def login(login_data: UserLogin):
    """用户登录"""
    user = data_store.get_user(login_data.username)
    
    if not user or user["password"] != login_data.password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误"
        )
    
    if user["status"] != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户已被禁用"
        )
    
    # 创建访问令牌
    access_token = create_access_token(
        data={"sub": user["username"], "user_id": user["id"]}
    )
    
    return ResponseModel(data={
        "token": access_token,
        "user": {
            "id": user["id"],
            "username": user["username"],
            "name": user["name"],
            "email": user["email"],
            "role": user["role"]
        }
    })


@router.post("/logout")
async def logout():
    """用户登出"""
    # 由于使用JWT，服务端不需要特殊处理
    return ResponseModel(message="登出成功")


@router.post("/refresh")
async def refresh_token():
    """刷新令牌"""
    # 简化处理，实际应该验证旧token
    return ResponseModel(data={"token": "new_token"})