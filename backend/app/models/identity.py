from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(160), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    password_hash: Mapped[str] = mapped_column(Text)
    role: Mapped[str] = mapped_column(String(40), index=True)
    institution_id: Mapped[int | None] = mapped_column(ForeignKey("institutions.id"), nullable=True)
    person_id: Mapped[int | None] = mapped_column(ForeignKey("persons.id"), nullable=True)
    active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Person(Base):
    """Identity is separate from enrolment. No unique APAAR across enrolments."""

    __tablename__ = "persons"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    apaar_enc: Mapped[str | None] = mapped_column(Text, nullable=True)
    apaar_hmac: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    temp_id: Mapped[str | None] = mapped_column(String(40), index=True, nullable=True)
    name_norm: Mapped[str] = mapped_column(String(160), index=True)
    name_display: Mapped[str] = mapped_column(String(160))
    dob: Mapped[date] = mapped_column(Date)
    gender: Mapped[str] = mapped_column(String(16), default="U")
    phone_hmac: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    email_hmac: Mapped[str | None] = mapped_column(String(64), nullable=True)
    apaar_status: Mapped[str] = mapped_column(String(16), default="provided")
    nationality: Mapped[str] = mapped_column(String(32), default="India")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
