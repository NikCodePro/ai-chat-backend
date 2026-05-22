from fastapi import APIRouter, Depends

from app.dependencies import get_current_user
from app.schemas.auth_schema import (
    GoogleAuthRequest,
    LoginRequest,
    LogoutRequest,
    RefreshTokenRequest,
    RequestOtpRequest,
    SignupCompleteRequest,
    SignupInitiateRequest,
    SignupVerifyRequest,
    ChangePasswordRequest,
    ForgotPasswordInitiateRequest,
    ForgotPasswordVerifyRequest,
    ForgotPasswordResetRequest,
)
from app.schemas.response_schema import success_response
from app.schemas.user_schema import serialize_user
from app.services.auth_service import (
    complete_signup,
    google_sign_in,
    initiate_signup,
    login_user,
    logout_user,
    refresh_access_token,
    request_otp,
    verify_signup_otp,
    change_password,
    initiate_forgot_password,
    verify_forgot_password_otp,
    reset_password,
)


router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/signup/initiate")
async def signup_initiate(payload: SignupInitiateRequest):
    data = await initiate_signup(payload.identifier)
    return success_response("OTP sent successfully", data)


@router.post("/signup/verify")
async def signup_verify(payload: SignupVerifyRequest):
    data = await verify_signup_otp(payload.identifier, payload.code)
    return success_response("OTP verified successfully", data)


@router.post("/signup/complete")
async def signup_complete(payload: SignupCompleteRequest):
    data = await complete_signup(payload)
    return success_response("Registration successful", data)


@router.post("/forgot-password/initiate")
async def forgot_password_initiate_route(payload: ForgotPasswordInitiateRequest):
    data = await initiate_forgot_password(payload.identifier)
    return success_response("OTP sent successfully", data)


@router.post("/forgot-password/verify")
async def forgot_password_verify_route(payload: ForgotPasswordVerifyRequest):
    data = await verify_forgot_password_otp(payload.identifier, payload.code)
    return success_response("OTP verified successfully", data)


@router.post("/forgot-password/reset")
async def forgot_password_reset_route(payload: ForgotPasswordResetRequest):
    data = await reset_password(payload)
    return success_response("Password reset successful", data)


@router.post("/request-otp")
async def get_otp(payload: RequestOtpRequest):
    data = await request_otp(payload.identifier, payload.purpose)
    return success_response("OTP sent successfully", data)


@router.post("/login")
async def login(payload: LoginRequest):
    data = await login_user(payload)
    return success_response("Login successful", data)


@router.post("/google")
async def continue_with_google(payload: GoogleAuthRequest):
    data = await google_sign_in(payload.id_token)
    return success_response("Google sign-in successful", data)


@router.post("/refresh")
async def refresh(payload: RefreshTokenRequest):
    data = await refresh_access_token(payload.refresh_token)
    return success_response("Access token refreshed", data)


@router.post("/logout")
async def logout(payload: LogoutRequest):
    await logout_user(payload.refresh_token)
    return success_response("Logout successful", {})


@router.get("/me")
async def get_me(current_user=Depends(get_current_user)):
    return success_response("Current user fetched", serialize_user(current_user))


@router.post("/change-password")
async def change_user_password(payload: ChangePasswordRequest, current_user=Depends(get_current_user)):
    await change_password(str(current_user["_id"]), payload.current_password, payload.new_password)
    return success_response("Password updated successfully", None)
