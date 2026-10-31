from __future__ import annotations

import os
import tempfile
from pathlib import Path

TEST_DB = Path(tempfile.gettempdir()) / "apaar_setu_pytest.db"
if TEST_DB.exists():
    TEST_DB.unlink()
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB.as_posix()}"
os.environ["APP_ENV"] = "test"
os.environ["DEMO_MODE"] = "true"
os.environ["SEED_ON_STARTUP"] = "true"
os.environ["LLM_PROVIDER"] = "none"
os.environ["PUBLIC_BASE_URL"] = "http://testserver"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

ACCOUNTS = {
    "admin": "admin.syn-mh-001@demo.apaar-setu.invalid",
    "operator_b": "operator.syn-mh-002@demo.apaar-setu.invalid",
    "reviewer": "reviewer@aicte.demo.apaar-setu.invalid",
    "verifier": "verifier@bank.demo.apaar-setu.invalid",
    "student": "student@demo.apaar-setu.invalid",
    "sysadmin": "sysadmin@demo.apaar-setu.invalid",
}


@pytest.fixture(scope="session")
def client():
    """One client whose lifespan seeds the isolated test database."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="session")
def roles(client):
    """A separate cookie jar and CSRF token per demo role."""
    sessions: dict[str, dict] = {}
    for role, email in ACCOUNTS.items():
        role_client = TestClient(app)
        response = role_client.post(
            "/api/v1/auth/login", json={"email": email, "password": "demo1234"}
        )
        assert response.status_code == 200, response.text
        sessions[role] = {
            "client": role_client,
            "csrf": response.json()["csrf_token"],
            "user": response.json()["user"],
        }
    return sessions


def auth(session: dict) -> dict:
    return {"X-CSRF-Token": session["csrf"]}
