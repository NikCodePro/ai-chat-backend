from typing import Generic, TypeVar

from pydantic import BaseModel


T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    success: bool = True
    message: str
    data: T | None = None


def success_response(message: str, data=None) -> dict:
    return {
        "success": True,
        "message": message,
        "data": data,
    }
