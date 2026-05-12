from datetime import datetime, timezone

from fastapi import HTTPException, status
from pymongo.errors import DuplicateKeyError

from app.database.collections import REFRESH_TOKENS_COLLECTION
from app.database.mongodb import get_database
from app.models.token_model import create_refresh_token_document
from app.models.user_model import create_user_document
from app.schemas.auth_schema import (
    LoginRequest,
    RegisterRequest,
    SignupCompleteRequest,
)
from app.schemas.user_schema import serialize_user
from app.services.google_service import verify_google_id_token
from app.services.jwt_service import (
    create_access_token,
    create_refresh_token,
    create_signup_token,
    verify_refresh_token,
    verify_signup_token,
)
from app.services.otp_service import (
    create_otp_challenge,
    normalize_identifier,
    validate_identifier,
    verify_otp_challenge,
)
from app.services.password_service import hash_password, verify_password
from app.services.user_service import (
    create_user,
    get_user_by_email,
    get_user_by_id,
    get_user_by_identifier,
    get_user_by_phone,
    get_user_by_username,
    mark_identifier_verified,
    update_user,
)


async def initiate_signup(identifier: str) -> dict:
    normalized = validate_identifier(identifier)
    user = await get_user_by_identifier(normalized)

    # If user exists and is verified, they should login instead
    if user:
        is_verified = user.get("email_verified") if "@" in normalized else user.get("phone_verified")
        if is_verified:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Account is already registered and verified. Please login.",
            )

    otp_data = await create_otp_challenge(normalized, "signup")
    return {
        "message": f"OTP sent to {normalized}",
        "identifier": normalized,
        "expires_at": otp_data["expires_at"],
    }


async def verify_signup_otp(identifier: str, code: str) -> dict:
    normalized = await verify_otp_challenge(identifier, code, "signup")

    # Generate a short-lived signup token that allows completing the registration
    signup_token = create_signup_token(normalized)

    return {
        "message": "OTP verified successfully",
        "signup_token": signup_token,
        "identifier": normalized,
    }


async def complete_signup(payload: SignupCompleteRequest) -> dict:
    # 1. Verify the signup token
    token_data = verify_signup_token(payload.signup_token)
    identifier = token_data["identifier"]

    # 2. Check if username is already taken
    existing_username = await get_user_by_username(payload.username)
    if existing_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username is already taken",
        )

    # 3. Check if user already exists (just in case)
    existing_user = await get_user_by_identifier(identifier)
    if existing_user:
        update_data = {
            "name": payload.name,
            "username": payload.username,
            "password": hash_password(payload.password),
            "email_verified": "@" in identifier,
            "phone_verified": "@" not in identifier,
            "updated_at": datetime.now(timezone.utc),
        }
        user = await update_user(str(existing_user["_id"]), update_data)
    else:
        email = identifier if "@" in identifier else None
        phone = identifier if "@" not in identifier else None

        user_document = create_user_document(
            name=payload.name,
            username=payload.username,
            hashed_password=hash_password(payload.password),
            email=email,
            phone=phone,
        )
        # Ensure verification flags are set correctly
        if email:
            user_document["email_verified"] = True
        if phone:
            user_document["phone_verified"] = True

        user = await create_user(user_document)

    return await _build_auth_response(user)


async def login_user(payload: LoginRequest) -> dict:
    identifier = normalize_identifier(payload.identifier)
    user = await get_user_by_identifier(identifier)
    if not user or not verify_password(payload.password, user["password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid identifier or password",
        )

    # If the user is not verified, they must verify their email/phone first
    if not _is_verified_for_login(user):
        otp = await create_otp_challenge(identifier, "signup")
        return {
            "verification_required": True,
            "message": "Please verify your account to continue.",
            "otp": otp if settings.RETURN_OTP_IN_RESPONSE else None,
        }

    # Log in immediately (No 2FA as per user request)
    return await _build_auth_response(user)


async def request_otp(identifier: str, purpose: str) -> dict:
    normalized = validate_identifier(identifier)
    return await create_otp_challenge(normalized, purpose)


async def google_sign_in(google_id_token: str) -> dict:
    payload = verify_google_id_token(google_id_token)
    email = payload["email"].lower()
    user = await get_user_by_email(email)

    if not user:
        user_document = create_user_document(
            name=payload.get("name") or email.split("@")[0],
            email=email,
            auth_provider="google",
            google_sub=payload.get("sub"),
        )
        user = await create_user(user_document)
    else:
        db = get_database()
        await db[USERS_COLLECTION].update_one(
            {"_id": user["_id"]},
            {
                "$set": {
                    "email_verified": True,
                    "google_sub": payload.get("sub"),
                }
            },
        )
        user = await get_user_by_email(email)

    return await _build_auth_response(user)


async def refresh_access_token(refresh_token: str) -> dict:
    payload = verify_refresh_token(refresh_token)
    db = get_database()
    stored_token = await db[REFRESH_TOKENS_COLLECTION].find_one(
        {
            "refresh_token": refresh_token,
            "expires_at": {"$gt": datetime.now(timezone.utc)},
        }
    )
    if not stored_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token is revoked or expired",
        )

    user = await get_user_by_id(payload["user_id"])
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User no longer exists",
        )

    access_token = create_access_token(
        str(user["_id"]),
        user.get("email") or user.get("phone"),
    )
    return {"access_token": access_token, "token_type": "bearer"}


async def logout_user(refresh_token: str) -> None:
    db = get_database()
    await db[REFRESH_TOKENS_COLLECTION].delete_one({"refresh_token": refresh_token})


async def _build_auth_response(user: dict) -> dict:
    access_token = create_access_token(
        str(user["_id"]),
        user.get("email") or user.get("phone"),
    )
    refresh_token, expires_at = create_refresh_token(str(user["_id"]))

    db = get_database()
    await db[REFRESH_TOKENS_COLLECTION].insert_one(
        create_refresh_token_document(
            user_id=str(user["_id"]),
            refresh_token=refresh_token,
            expires_at=expires_at,
        )
    )

    return {
        "user": serialize_user(user),
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


def _is_verified_for_login(user: dict) -> bool:
    if user.get("email") and user.get("email_verified"):
        return True
    if user.get("phone") and user.get("phone_verified"):
        return True
    return False
