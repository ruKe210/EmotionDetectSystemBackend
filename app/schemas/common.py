from typing import Generic, TypeVar, Optional, List
from pydantic import BaseModel

T = TypeVar('T')


class ResponseModel(BaseModel, Generic[T]):
    code: int = 200
    message: str = "操作成功"
    data: Optional[T] = None


class PaginationParams(BaseModel):
    page: int = 1
    pageSize: int = 10


class PaginatedResponse(BaseModel, Generic[T]):
    list: List[T]
    total: int
    page: int
    pageSize: int
    totalPages: int

    @classmethod
    def create(cls, items: List[T], total: int, page: int, pageSize: int):
        return cls(
            list=items,
            total=total,
            page=page,
            pageSize=pageSize,
            totalPages=(total + pageSize - 1) // pageSize
        )