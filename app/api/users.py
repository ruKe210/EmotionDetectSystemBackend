from typing import Optional
from fastapi import APIRouter, Depends, Query
from app.schemas import ResponseModel, UserCreate, UserUpdate, PaginatedResponse
from app.schemas.common import PaginationParams
from app.api.deps import get_current_admin_user, get_current_active_user
from app.services.data_store import data_store

router = APIRouter()


@router.get("", response_model=ResponseModel[PaginatedResponse])
async def get_users(
    page: int = Query(1, ge=1),
    pageSize: int = Query(10, ge=1, le=100),
    status: Optional[str] = None,
    search: Optional[str] = None,
    current_user: dict = Depends(get_current_admin_user)
):
    """获取用户列表"""
    users = data_store.get_all_users()
    
    # 过滤
    if status:
        users = [u for u in users if u["status"] == status]
    if search:
        users = [u for u in users if search.lower() in u["username"].lower() or 
                 search.lower() in u["name"].lower()]
    
    # 移除密码字段
    for user in users:
        user.pop("password", None)
    
    total = len(users)
    start = (page - 1) * pageSize
    end = start + pageSize
    paginated_users = users[start:end]
    
    return ResponseModel(data=PaginatedResponse.create(paginated_users, total, page, pageSize))


@router.post("", response_model=ResponseModel)
async def create_user(
    user_data: UserCreate,
    current_user: dict = Depends(get_current_admin_user)
):
    """创建用户"""
    # 检查用户名是否已存在
    if data_store.get_user(user_data.username):
        return ResponseModel(code=400, message="用户名已存在")
    
    user_dict = user_data.model_dump()
    new_user = data_store.create_user(user_dict)
    new_user.pop("password", None)
    
    return ResponseModel(data={"id": new_user["id"]}, message="创建成功")


@router.put("/{user_id}", response_model=ResponseModel)
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    current_user: dict = Depends(get_current_admin_user)
):
    """更新用户"""
    # 查找用户
    user = None
    username = None
    for uname, u in data_store.users.items():
        if u["id"] == user_id:
            user = u
            username = uname
            break
    
    if not user:
        return ResponseModel(code=404, message="用户不存在")
    
    update_dict = {k: v for k, v in user_data.model_dump().items() if v is not None}
    data_store.update_user(username, update_dict)
    
    return ResponseModel(message="更新成功")


@router.delete("/{user_id}", response_model=ResponseModel)
async def delete_user(
    user_id: int,
    current_user: dict = Depends(get_current_admin_user)
):
    """删除用户"""
    # 查找用户
    username = None
    for uname, u in data_store.users.items():
        if u["id"] == user_id:
            username = uname
            break
    
    if not username:
        return ResponseModel(code=404, message="用户不存在")
    
    if username == current_user["username"]:
        return ResponseModel(code=400, message="不能删除当前登录用户")
    
    data_store.delete_user(username)
    return ResponseModel(message="删除成功")


@router.put("/{user_id}/status", response_model=ResponseModel)
async def update_user_status(
    user_id: int,
    status: dict,
    current_user: dict = Depends(get_current_admin_user)
):
    """更新用户状态"""
    # 查找用户
    username = None
    for uname, u in data_store.users.items():
        if u["id"] == user_id:
            username = uname
            break
    
    if not username:
        return ResponseModel(code=404, message="用户不存在")
    
    data_store.update_user(username, {"status": status.get("status")})
    return ResponseModel(message="状态更新成功")