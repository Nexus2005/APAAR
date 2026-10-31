from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


class Institution(Base):
    __tablename__ = "institutions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    aicte_code: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200))
    short_name: Mapped[str] = mapped_column(String(60))
    state: Mapped[str] = mapped_column(String(80), index=True)
    region: Mapped[str] = mapped_column(String(80))
    city: Mapped[str] = mapped_column(String(80))
    status: Mapped[str] = mapped_column(String(20), default="active")
    public_key: Mapped[str] = mapped_column(Text, default="")
    private_key_enc: Mapped[str] = mapped_column(Text, default="")

    programmes: Mapped[list[Programme]] = relationship(back_populates="institution")


class Programme(Base):
    __tablename__ = "programmes"
    __table_args__ = (UniqueConstraint("institution_id", "code", name="uq_programme_inst_code"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    institution_id: Mapped[int] = mapped_column(ForeignKey("institutions.id"), index=True)
    code: Mapped[str] = mapped_column(String(24))
    name: Mapped[str] = mapped_column(String(160))
    level: Mapped[str] = mapped_column(String(24), default="UG")
    discipline_group: Mapped[str] = mapped_column(String(60))
    shift: Mapped[str] = mapped_column(String(12), default="1")
    duration_years: Mapped[int] = mapped_column(Integer, default=4)

    institution: Mapped[Institution] = relationship(back_populates="programmes")
    approvals: Mapped[list[IntakeApproval]] = relationship(back_populates="programme")


class IntakeApproval(Base):
    __tablename__ = "intake_approvals"
    __table_args__ = (
        UniqueConstraint("programme_id", "academic_year", name="uq_intake_programme_year"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    programme_id: Mapped[int] = mapped_column(ForeignKey("programmes.id"), index=True)
    academic_year: Mapped[str] = mapped_column(String(12), default="2026-27")
    approved_intake: Mapped[int] = mapped_column(Integer, default=60)
    rule_version_id: Mapped[int | None] = mapped_column(ForeignKey("rule_versions.id"))

    programme: Mapped[Programme] = relationship(back_populates="approvals")


class RuleVersion(Base):
    __tablename__ = "rule_versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    effective_from: Mapped[date] = mapped_column(Date)
    config_json: Mapped[str] = mapped_column(Text)
    created_by: Mapped[str] = mapped_column(String(120), default="system")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    note: Mapped[str] = mapped_column(String(240), default="")

    @property
    def config(self) -> dict:
        import json

        return json.loads(self.config_json)
