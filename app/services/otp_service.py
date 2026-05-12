import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status

from app.config import settings
from app.database.collections import OTP_CHALLENGES_COLLECTION
from app.database.mongodb import get_database
from app.models.otp_model import create_otp_challenge_document
from app.services.sms_service import send_sms_otp
from app.utils.validators import is_valid_phone


def normalize_identifier(identifier: str) -> str:
    value = identifier.strip()
    if "@" in value:
        return value.lower()
    
    # Handle phone number normalization
    if value.isdigit():
        if len(value) == 10:
            return f"+91{value}"
        if len(value) == 12 and value.startswith("91"):
            return f"+{value}"
    
    return value


def is_phone_identifier(identifier: str) -> bool:
    return identifier.startswith("+")


def validate_identifier(identifier: str) -> str:
    normalized = normalize_identifier(identifier)
    if is_phone_identifier(normalized) and not is_valid_phone(normalized):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Phone number must use E.164 format, for example +919876543210",
        )
    return normalized


def _hash_otp(identifier: str, code: str, purpose: str) -> str:
    raw = f"{identifier}:{purpose}:{code}:{settings.JWT_SECRET_KEY}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _generate_code() -> str:
    upper_bound = 10**settings.OTP_LENGTH
    return str(secrets.randbelow(upper_bound)).zfill(settings.OTP_LENGTH)


async def create_otp_challenge(identifier: str, purpose: str) -> dict:
    normalized = validate_identifier(identifier)
    code = _generate_code()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.OTP_EXPIRE_MINUTES)

    db = get_database()
    await db[OTP_CHALLENGES_COLLECTION].update_many(
        {"identifier": normalized, "purpose": purpose, "used": False},
        {"$set": {"used": True}},
    )
    await db[OTP_CHALLENGES_COLLECTION].insert_one(
        create_otp_challenge_document(
            identifier=normalized,
            code_hash=_hash_otp(normalized, code, purpose),
            purpose=purpose,
            expires_at=expires_at,
        )
    )

    delivery = None
    if is_phone_identifier(normalized):
        delivery = send_sms_otp(normalized, code)

    data = {
        "identifier": normalized,
        "purpose": purpose,
        "expires_at": expires_at,
    }
    if delivery:
        data["delivery"] = delivery
    if settings.RETURN_OTP_IN_RESPONSE:
        data["otp"] = code
    return data


async def verify_otp_challenge(identifier: str, code: str, purpose: str) -> str:
    normalized = validate_identifier(identifier)
    db = get_database()
    challenge = await db[OTP_CHALLENGES_COLLECTION].find_one(
        {
            "identifier": normalized,
            "purpose": purpose,
            "code_hash": _hash_otp(normalized, code, purpose),
            "used": False,
            "expires_at": {"$gt": datetime.now(timezone.utc)},
        }
    )
    if not challenge:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired OTP",
        )

    await db[OTP_CHALLENGES_COLLECTION].update_one(
        {"_id": challenge["_id"]},
        {"$set": {"used": True}},
    )
    return normalized
