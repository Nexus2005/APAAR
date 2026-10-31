from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class Credential(Base):
    __tablename__ = "credentials"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    credential_id: Mapped[str] = mapped_column(String(48), unique=True, index=True)
    enrolment_id: Mapped[int] = mapped_column(ForeignKey("enrolments.id"), index=True)
    issuer_institution_id: Mapped[int] = mapped_column(ForeignKey("institutions.id"))
    payload_json: Mapped[str] = mapped_column(Text)
    signature: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(16), default="valid")
    issued_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    revoke_reason: Mapped[str | None] = mapped_column(String(240), nullable=True)


class ConsentRequest(Base):
    __tablename__ = "consent_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    verifier_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    verifier_name: Mapped[str] = mapped_column(String(160), default="")
    subject_person_id: Mapped[int] = mapped_column(ForeignKey("persons.id"), index=True)
    fields: Mapped[str] = mapped_column(Text, default="[]")
    purpose: Mapped[str] = mapped_column(String(240))
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime)


class ShareToken(Base):
    __tablename__ = "share_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    consent_request_id: Mapped[int] = mapped_column(
        ForeignKey("consent_requests.id"), index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    used_count: Mapped[int] = mapped_column(Integer, default=0)


class AccessLog(Base):
    __tablename__ = "access_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    verifier_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    person_id: Mapped[int] = mapped_column(ForeignKey("persons.id"))
    purpose: Mapped[str] = mapped_column(String(240))
    outcome: Mapped[str] = mapped_column(String(24))
    at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    seq: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    actor_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    actor_name: Mapped[str] = mapped_column(String(120), default="system")
    action: Mapped[str] = mapped_column(String(80), index=True)
    resource: Mapped[str] = mapped_column(String(120))
    detail_json: Mapped[str] = mapped_column(Text, default="{}")
    at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    prev_hash: Mapped[str] = mapped_column(String(64))
    hash: Mapped[str] = mapped_column(String(64))
