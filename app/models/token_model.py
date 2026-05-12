from datetime import datetime, timezone


def create_refresh_token_document(
    user_id: str,
    refresh_token: str,
    expires_at: datetime,
) -> dict:
    return {
        "user_id": user_id,
        "refresh_token": refresh_token,
        "expires_at": expires_at,
        "created_at": datetime.now(timezone.utc),
    }
