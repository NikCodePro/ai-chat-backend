from datetime import datetime, timezone


def create_otp_challenge_document(
    identifier: str,
    code_hash: str,
    purpose: str,
    expires_at: datetime,
) -> dict:
    return {
        "identifier": identifier,
        "code_hash": code_hash,
        "purpose": purpose,
        "expires_at": expires_at,
        "used": False,
        "created_at": datetime.now(timezone.utc),
    }
