"""Application settings loaded from environment variables (no extra dependency)."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DB = f"sqlite:///{(PROJECT_ROOT / 'data' / 'app.db').as_posix()}"


def _bool(name: str, default: str = "false") -> bool:
    return os.getenv(name, default).strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    app_env: str = field(default_factory=lambda: os.getenv("APP_ENV", "development"))
    database_url: str = field(default_factory=lambda: os.getenv("DATABASE_URL", DEFAULT_DB))
    session_secret: str = field(
        default_factory=lambda: os.getenv("SESSION_SECRET", "dev-session-secret-change-me-please")
    )
    identifier_hmac_key: str = field(
        default_factory=lambda: os.getenv("IDENTIFIER_HMAC_KEY", "dev-hmac-key-change-me-0123456789")
    )
    identifier_encryption_key: str = field(
        default_factory=lambda: os.getenv("IDENTIFIER_ENCRYPTION_KEY", "dev-fernet-key-change-me")
    )
    public_base_url: str = field(
        default_factory=lambda: os.getenv("PUBLIC_BASE_URL", "http://localhost:8000")
    )
    llm_provider: str = field(default_factory=lambda: os.getenv("LLM_PROVIDER", "none"))
    demo_mode: bool = field(default_factory=lambda: _bool("DEMO_MODE", "true"))
    seed_on_startup: bool = field(default_factory=lambda: _bool("SEED_ON_STARTUP", "true"))
    session_ttl_seconds: int = 60 * 60 * 12
    cookie_name: str = "apaar_session"
    csrf_cookie: str = "apaar_csrf"


@lru_cache
def get_settings() -> Settings:
    return Settings()


def load_rules() -> dict:
    """Load the versioned policy file. Regulatory numbers live only here."""
    import yaml

    path = Path(os.getenv("RULES_PATH", PROJECT_ROOT / "config" / "rules.yaml"))
    with path.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)
