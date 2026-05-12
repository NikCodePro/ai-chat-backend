import re


PASSWORD_PATTERN = re.compile(r"^(?=.*[A-Za-z])(?=.*\d).{8,}$")
PHONE_PATTERN = re.compile(r"^\+[1-9]\d{7,14}$")


def is_strong_password(password: str) -> bool:
    return bool(PASSWORD_PATTERN.match(password))


def is_valid_phone(phone: str) -> bool:
    return bool(PHONE_PATTERN.match(phone))
