from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


class UploadBatch(Base):
    __tablename__ = "upload_batches"
    __table_args__ = (
        UniqueConstraint("institution_id", "file_sha256", name="uq_batch_inst_sha"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    batch_ref: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    institution_id: Mapped[int] = mapped_column(ForeignKey("institutions.id"), index=True)
    filename: Mapped[str] = mapped_column(String(240))
    file_sha256: Mapped[str] = mapped_column(String(64))
    uploaded_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    status: Mapped[str] = mapped_column(String(24), default="completed")
    mapping_json: Mapped[str] = mapped_column(Text, default="{}")
    total_rows: Mapped[int] = mapped_column(Integer, default=0)
    accepted_rows: Mapped[int] = mapped_column(Integer, default=0)
    rejected_rows: Mapped[int] = mapped_column(Integer, default=0)
    findings_raised: Mapped[int] = mapped_column(Integer, default=0)

    rows: Mapped[list[RowResult]] = relationship(back_populates="batch")


class RowResult(Base):
    __tablename__ = "row_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    batch_id: Mapped[int] = mapped_column(ForeignKey("upload_batches.id"), index=True)
    row_number: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(16))
    error_codes: Mapped[str] = mapped_column(Text, default="[]")
    error_detail: Mapped[str] = mapped_column(Text, default="")
    raw_masked_json: Mapped[str] = mapped_column(Text, default="{}")

    batch: Mapped[UploadBatch] = relationship(back_populates="rows")


class Enrolment(Base):
    __tablename__ = "enrolments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    enrolment_ref: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    person_id: Mapped[int] = mapped_column(ForeignKey("persons.id"), index=True)
    institution_id: Mapped[int] = mapped_column(ForeignKey("institutions.id"), index=True)
    programme_id: Mapped[int] = mapped_column(ForeignKey("programmes.id"), index=True)
    academic_year: Mapped[str] = mapped_column(String(12), default="2026-27")
    seat_category: Mapped[str] = mapped_column(String(24), default="regular")
    admission_date: Mapped[date] = mapped_column(Date)
    admission_mode: Mapped[str] = mapped_column(String(24), default="counselling")
    status: Mapped[str] = mapped_column(String(20), default="admitted")
    batch_id: Mapped[int | None] = mapped_column(ForeignKey("upload_batches.id"), nullable=True)
    source: Mapped[str] = mapped_column(String(16), default="csv")
    nationality: Mapped[str] = mapped_column(String(32), default="India")
    qualifying_exam_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    remarks: Mapped[str] = mapped_column(String(240), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class EnrolmentEvent(Base):
    __tablename__ = "enrolment_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    enrolment_id: Mapped[int] = mapped_column(ForeignKey("enrolments.id"), index=True)
    event_type: Mapped[str] = mapped_column(String(40))
    payload: Mapped[str] = mapped_column(Text, default="{}")
    actor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
