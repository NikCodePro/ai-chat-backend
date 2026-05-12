from fastapi import HTTPException, status
from google.auth.transport import requests
from google.oauth2 import id_token

from app.config import settings


def verify_google_id_token(token: str) -> dict:
    if not settings.GOOGLE_CLIENT_ID or settings.GOOGLE_CLIENT_ID.startswith("your_"):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="GOOGLE_CLIENT_ID is not configured",
        )

    try:
        payload = id_token.verify_oauth2_token(
            token,
            requests.Request(),
            settings.GOOGLE_CLIENT_ID,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Google ID token",
        ) from exc

    if not payload.get("email_verified"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Google email is not verified",
        )
    return payload
