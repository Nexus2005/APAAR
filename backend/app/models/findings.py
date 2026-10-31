from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class Finding(Base):
    __tablename__ = "findings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    rule_code: Mapped[str] = mapped_column(String(48), index=True)
    severity: Mapped[str] = mapped_column(String(16), index=True)
    institution_id: Mapped[int] = mapped_column(ForeignKey("institutions.id"), index=True)
    enrolment_id: Mapped[int | None] = mapped_column(
        ForeignKey("enrolments.id"), nullable=True, index=True
    )
    subject_key: Mapped[str] = mapped_column(String(160), default="")
    subject_json: Mapped[str] = mapped_column(Text, default="{}")
    explanation: Mapped[str] = mapped_column(Text, default="")
    recommended_action: Mapped[str] = mapped_column(Text, default="")
    policy_assumption: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="open", index=True)
    assigned_to: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    @property
    def evidence(self) -> dict:
        import json

        return json.loads(self.subject_json or "{}")


class FindingEvent(Base):
    __tablename__ = "finding_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    finding_id: Mapped[int] = mapped_column(ForeignKey("findings.id"), index=True)
    action: Mapped[str] = mapped_column(String(40))
    comment: Mapped[str] = mapped_column(Text)
    actor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    actor_name: Mapped[str] = mapped_column(String(120), default="system")
    at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class DuplicateLink(Base):
    __tablename__ = "duplicate_links"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    enrolment_a: Mapped[int] = mapped_column(ForeignKey("enrolments.id"), index=True)
    enrolment_b: Mapped[int] = mapped_column(ForeignKey("enrolments.id"), index=True)
    match_type: Mapped[str] = mapped_column(String(24))
    score: Mapped[float] = mapped_column(Float, default=100.0)
    evidence_json: Mapped[str] = mapped_column(Text, default="{}")
    whitelisted_reason: Mapped[str | None] = mapped_column(String(80), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class AnomalyScore(Base):
    __tablename__ = "anomaly_scores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    institution_id: Mapped[int] = mapped_column(ForeignKey("institutions.id"), index=True)
    academic_year: Mapped[str] = mapped_column(String(12), default="2026-27")
    score: Mapped[float] = mapped_column(Float, default=0.0)
    rank: Mapped[int] = mapped_column(Integer, default=0)
    flagged: Mapped[bool] = mapped_column(default=False)
    features_json: Mapped[str] = mapped_column(Text, default="{}")
    reasons_json: Mapped[str] = mapped_column(Text, default="[]")
    computed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
