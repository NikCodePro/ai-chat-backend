from datetime import datetime, timedelta, timezone
from uuid import uuid4

import jwt
from fastapi import HTTPException, status

from app.config import settings


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def create_access_token(user_id: str, identifier: str) -> str:
    expires_at = _utc_now() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "user_id": user_id,
        "identifier": identifier,
        "exp": expires_at,
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(user_id: str) -> tuple[str, datetime]:
    issued_at = _utc_now()
    expires_at = issued_at + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    payload = {
        "jti": uuid4().hex,
        "user_id": user_id,
        "type": "refresh",
        "iat": issued_at,
        "exp": expires_at,
    }
    token = jwt.encode(
        payload,
        settings.JWT_REFRESH_SECRET,
        algorithm=settings.JWT_ALGORITHM,
    )
    return token, expires_at


def create_signup_token(identifier: str) -> str:
    expires_at = _utc_now() + timedelta(minutes=15)  # Signup token valid for 15 mins
    payload = {
        "identifier": identifier,
        "type": "signup",
        "exp": expires_at,
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def verify_access_token(token: str) -> dict:
    try:
        return jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Access token has expired",
        ) from exc
    except jwt.InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid access token",
        ) from exc


def verify_refresh_token(token: str) -> dict:
    try:
        payload = jwt.decode(
            token,
            settings.JWT_REFRESH_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
        )
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token has expired",
        ) from exc
    except jwt.InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        ) from exc

    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token type",
        )
    return payload


def verify_signup_token(token: str) -> dict:
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Signup session has expired. Please verify again.",
        ) from exc
    except jwt.InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid signup session token",
        ) from exc

    if payload.get("type") != "signup":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
        )
    return payload
