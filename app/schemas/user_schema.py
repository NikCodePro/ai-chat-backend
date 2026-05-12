from datetime import datetime

from pydantic import BaseModel, EmailStr


class UserResponse(BaseModel):
    id: str
    name: str
    username: str
    email: EmailStr | None = None
    phone: str | None = None
    auth_provider: str = "password"
    email_verified: bool = False
    phone_verified: bool = False
    created_at: datetime


def serialize_user(user: dict) -> UserResponse:
    return UserResponse(
        id=str(user["_id"]),
        name=user["name"],
        username=user["username"],
        email=user.get("email"),
        phone=user.get("phone"),
        auth_provider=user.get("auth_provider", "password"),
        email_verified=user.get("email_verified", False),
        phone_verified=user.get("phone_verified", False),
        created_at=user["created_at"],
    )
