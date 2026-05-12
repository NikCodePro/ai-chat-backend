from datetime import datetime, timezone

from bson import ObjectId


def create_user_document(
    name: str,
    username: str,
    hashed_password: str | None = None,
    email: str | None = None,
    phone: str | None = None,
    auth_provider: str = "password",
    google_sub: str | None = None,
) -> dict:
    document = {
        "_id": ObjectId(),
        "name": name,
        "username": username,
        "email": email.lower() if email else None,
        "phone": phone,
        "password": hashed_password,
        "auth_provider": auth_provider,
        "google_sub": google_sub,
        "email_verified": auth_provider == "google",
        "phone_verified": False,
        "created_at": datetime.now(timezone.utc),
    }
    return {key: value for key, value in document.items() if value is not None}
