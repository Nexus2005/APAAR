"""Password hashing, signed session cookies and CSRF helpers."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from urllib.parse import quote

from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, VerifyMismatchError

from app.core.config import get_settings

_hasher = PasswordHasher(time_cost=2, memory_cost=19456, parallelism=1)


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except (VerifyMismatchError, VerificationError, ValueError):
        return False


def _b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def _unb64(raw: str) -> bytes:
    return base64.urlsafe_b64decode(raw + "=" * (-len(raw) % 4))


def sign_session(payload: dict, ttl_seconds: int | None = None) -> str:
    settings = get_settings()
    body = {
        **payload,
        "exp": int(time.time()) + (ttl_seconds or settings.session_ttl_seconds),
    }
    encoded = _b64(json.dumps(body, separators=(",", ":"), sort_keys=True).encode())
    signature = _b64(
        hmac.new(settings.session_secret.encode(), encoded.encode(), hashlib.sha256).digest()
    )
    return f"{encoded}.{signature}"


def read_session(token: str | None) -> dict | None:
    if not token or "." not in token:
        return None
    settings = get_settings()
    encoded, signature = token.rsplit(".", 1)
    expected = _b64(
        hmac.new(settings.session_secret.encode(), encoded.encode(), hashlib.sha256).digest()
    )
    if not hmac.compare_digest(signature, expected):
        return None
    try:
        payload = json.loads(_unb64(encoded))
    except (ValueError, json.JSONDecodeError):
        return None
    if int(payload.get("exp", 0)) < int(time.time()):
        return None
    return payload


def new_csrf_token() -> str:
    return secrets.token_urlsafe(24)


def csrf_matches(cookie_token: str | None, header_token: str | None) -> bool:
    return bool(cookie_token) and bool(header_token) and hmac.compare_digest(
        cookie_token, header_token
    )


def cookie_value(token: str) -> str:
    return quote(token, safe="")
