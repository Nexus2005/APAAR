from __future__ import annotations

from datetime import date

from sqlalchemy import Boolean, Date, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class MockApaarRegistry(Base):
    """SIMULATED provider data. Never a real APAAR/ABC/DigiLocker record."""

    __tablename__ = "mock_apaar_registry"

    apaar_id: Mapped[str] = mapped_column(String(24), primary_key=True)
    name: Mapped[str] = mapped_column(String(160))
    dob: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(16), default="active")
    simulated: Mapped[bool] = mapped_column(Boolean, default=True)
