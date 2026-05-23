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
        # Verify token signature and expiration, checking audience manually later
        payload = id_token.verify_oauth2_token(
            token,
            requests.Request(),
            audience=None,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid Google ID token signature or expiration: {str(exc)}",
        ) from exc

    # List of all valid Google Client IDs (Web, iOS, and Android)
    allowed_client_ids = {
        settings.GOOGLE_CLIENT_ID,
        "985688017742-ko0ptvnip8ms5ti8aakjf37hdqk1bgt4.apps.googleusercontent.com", # Web
        "985688017742-s8llh51e8657vstrg8amkpgtrb05qua5.apps.googleusercontent.com", # iOS
        "985688017742-9523bmh33nck51091cgilpmbmu44vied.apps.googleusercontent.com", # Android
    }
    # Filter out empty strings or None
    allowed_client_ids = {cid for cid in allowed_client_ids if cid}

    if payload.get("aud") not in allowed_client_ids:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Google ID token audience",
        )

    if not payload.get("email_verified"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Google email is not verified",
        )
    return payload
