"""Identifier protection: keyed HMAC for matching, Fernet for authorised display."""

from __future__ import annotations

import base64
import hashlib
import hmac
import re

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import get_settings


def normalise_apaar(value: str | None) -> str:
    return re.sub(r"[\s-]", "", (value or "")).strip()


def hmac_value(value: str) -> str:
    settings = get_settings()
    return hmac.new(
        settings.identifier_hmac_key.encode(),
        normalise_apaar(value).encode(),
        hashlib.sha256,
    ).hexdigest()


def apaar_fingerprint(value: str) -> str:
    return hmac_value(value)


def _fernet() -> Fernet:
    settings = get_settings()
    raw = settings.identifier_encryption_key
    try:
        return Fernet(raw.encode())
    except (ValueError, TypeError):
        digest = hashlib.sha256(raw.encode()).digest()
        return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_identifier(value: str) -> str:
    return _fernet().encrypt(normalise_apaar(value).encode()).decode()


def decrypt_identifier(token: str | None) -> str | None:
    if not token:
        return None
    try:
        return _fernet().decrypt(token.encode()).decode()
    except (InvalidToken, ValueError):
        return None


def encrypt_text(value: str) -> str:
    return _fernet().encrypt(value.encode()).decode()


def decrypt_text(token: str | None) -> str | None:
    if not token:
        return None
    try:
        return _fernet().decrypt(token.encode()).decode()
    except (InvalidToken, ValueError):
        return None


def mask_apaar(value: str | None) -> str:
    clean = normalise_apaar(value)
    if not clean:
        return "—"
    if len(clean) <= 4:
        return "X" * len(clean)
    return f"XXXX-XXXX-{clean[-4:]}"


def mask_id_fingerprint(fingerprint: str | None) -> str:
    if not fingerprint:
        return "—"
    return f"XXXX-XXXX-{fingerprint[-4:].upper()}"
