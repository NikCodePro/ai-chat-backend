from urllib.parse import quote

import requests
from fastapi import HTTPException, status

from app.config import settings


def is_two_factor_configured() -> bool:
    return bool(settings.TWO_FACTOR_API_KEY) and not settings.TWO_FACTOR_API_KEY.startswith("your_")


def send_sms_otp(phone: str, otp_code: str) -> dict:
    if not is_two_factor_configured():
        if settings.RETURN_OTP_IN_RESPONSE:
            return {
                "channel": "sms",
                "provider": "2factor",
                "sent": False,
                "reason": "TWO_FACTOR_API_KEY is not configured",
            }
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="TWO_FACTOR_API_KEY is not configured",
        )

    phone_number = phone.lstrip("+")
    # 2Factor.in standard SMS OTP URL: https://2factor.in/API/V1/{api_key}/SMS/{phone_number}/{otp}/{template_name}
    url = (
        "https://2factor.in/API/V1/"
        f"{quote(settings.TWO_FACTOR_API_KEY)}/SMS/{quote(phone_number)}/{quote(otp_code)}"
    )
    
    if settings.TWO_FACTOR_TEMPLATE:
        url += f"/{quote(settings.TWO_FACTOR_TEMPLATE)}"

    try:
        # 2Factor API typically uses GET for these URL-based requests
        response = requests.get(
            url,
            timeout=settings.TWO_FACTOR_SMS_TIMEOUT_SECONDS,
        )
    except requests.RequestException as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Unable to send OTP SMS",
        ) from exc

    if not response.ok:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"2Factor OTP SMS request failed with status {response.status_code}",
        )

    provider_payload = _safe_json(response)
    if provider_payload.get("Status") == "Error":
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=provider_payload.get("Details") or "2Factor OTP SMS request failed",
        )

    return {
        "channel": "sms",
        "provider": "2factor",
        "sent": True,
        "provider_response": provider_payload,
    }


def _safe_json(response: requests.Response) -> dict:
    try:
        payload = response.json()
    except ValueError:
        return {"raw": response.text}
    return payload if isinstance(payload, dict) else {"raw": payload}
