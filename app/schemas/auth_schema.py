from typing import Literal

from pydantic import BaseModel, EmailStr, Field, model_validator

from app.schemas.user_schema import UserResponse


class RegisterRequest(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    username: str = Field(min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_]+$")
    email: EmailStr | None = None
    phone: str | None = Field(default=None, examples=["+919876543210"])
    password: str = Field(min_length=8, max_length=128)

    @model_validator(mode="after")
    def validate_identifier(self):
        if not self.email and not self.phone:
            raise ValueError("Email or phone is required")
        return self


class LoginRequest(BaseModel):
    identifier: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=1, max_length=128)


class RequestOtpRequest(BaseModel):
    identifier: str = Field(min_length=3, max_length=255)
    purpose: Literal["signup", "password_reset"] = "signup"


class VerifyOtpRequest(BaseModel):
    identifier: str = Field(min_length=3, max_length=255)
    code: str = Field(min_length=4, max_length=10)
    purpose: Literal["signup", "password_reset"] = "signup"


class SignupInitiateRequest(BaseModel):
    identifier: str = Field(min_length=3, max_length=255)


class SignupVerifyRequest(BaseModel):
    identifier: str = Field(min_length=3, max_length=255)
    code: str = Field(min_length=4, max_length=10)


class SignupCompleteRequest(BaseModel):
    signup_token: str
    name: str = Field(min_length=2, max_length=100)
    username: str = Field(min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_]+$")
    password: str = Field(min_length=8, max_length=128)


class SignupTokenResponse(BaseModel):
    signup_token: str
    identifier: str




class GoogleAuthRequest(BaseModel):
    id_token: str = Field(min_length=1)


class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(min_length=1)


class LogoutRequest(BaseModel):
    refresh_token: str = Field(min_length=1)


class AuthTokens(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class AuthResponseData(AuthTokens):
    user: UserResponse
