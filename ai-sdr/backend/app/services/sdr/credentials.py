import json
from typing import Optional
from app.utils.crypto import encrypt_value, decrypt_value


def encrypt_sdr_credentials(data: dict) -> str:
    return encrypt_value(json.dumps(data))


def decrypt_sdr_credentials(encrypted: str) -> Optional[dict]:
    if not encrypted:
        return None
    try:
        raw = decrypt_value(encrypted)
        return json.loads(raw)
    except Exception:
        return None


def get_email_credentials(encrypted: str) -> Optional[dict]:
    creds = decrypt_sdr_credentials(encrypted)
    if creds and creds.get("provider") in ("gmail", "smtp"):
        return creds
    return None


def get_linkedin_credentials(encrypted: str) -> Optional[dict]:
    creds = decrypt_sdr_credentials(encrypted)
    if creds and creds.get("email") and creds.get("password"):
        return creds
    return None


def has_email_configured(encrypted: str) -> bool:
    return get_email_credentials(encrypted) is not None


def has_linkedin_configured(encrypted: str) -> bool:
    return get_linkedin_credentials(encrypted) is not None


def get_email_sender(encrypted: str) -> Optional[str]:
    creds = get_email_credentials(encrypted)
    if creds:
        return creds.get("sender_email") or creds.get("username", "")
    return None
