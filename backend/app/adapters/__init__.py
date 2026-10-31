from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Protocol

from sqlalchemy.orm import Session

from app.models import MockApaarRegistry


@dataclass
class IdentityResult:
    found: bool
    status: str
    name: str | None = None
    dob: date | None = None
    simulated: bool = True
    provider: str = "mock_apaar"


class IdentityProvider(Protocol):
    def lookup(self, apaar_id: str) -> IdentityResult: ...


class MockAPAARProvider:
    """SIMULATED identity provider backed by local synthetic registry rows only."""

    def __init__(self, db: Session):
        self.db = db

    def lookup(self, apaar_id: str) -> IdentityResult:
        row = self.db.get(MockApaarRegistry, apaar_id)
        if not row:
            return IdentityResult(found=False, status="not_found", provider="mock_apaar")
        return IdentityResult(
            found=True,
            status=row.status,
            name=row.name,
            dob=row.dob,
            simulated=True,
            provider="mock_apaar",
        )


class GovernmentAPAARProvider:
    def lookup(self, apaar_id: str) -> IdentityResult:  # pragma: no cover
        raise NotImplementedError("Awaiting authorised access to a real APAAR/ABC API.")


def get_identity_provider(db: Session) -> IdentityProvider:
    return MockAPAARProvider(db)
