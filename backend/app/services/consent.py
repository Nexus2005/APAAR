"""Consent-gated verification. The verifier can only receive allow-listed fields."""

from __future__ import annotations

import hashlib
import json
import secrets
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import load_rules
from app.models import (
    AccessLog,
    ConsentRequest,
    Enrolment,
    Institution,
    Person,
    Programme,
    ShareToken,
    User,
)

ALLOWED_FIELDS = {
    "enrolled": "Whether the student is enrolled",
    "programme": "Programme name",
    "programme_code": "Programme code",
    "academic_year": "Academic year",
    "institution": "Institution name",
    "enrolment_status": "Enrolment status",
}
FORBIDDEN_FIELDS = {"apaar", "apaar_id", "dob", "name", "date_of_birth", "phone", "email"}


def _ttl_minutes() -> int:
    return int(load_rules().get("privacy", {}).get("consent_ttl_minutes", 15))


def create_request(
    db: Session,
    verifier: User,
    enrolment_ref: str,
    fields: list[str],
    purpose: str,
) -> ConsentRequest:
    if not purpose.strip():
        raise ValueError("A purpose is required.")
    requested = [f for f in fields if f]
    bad = set(requested) & FORBIDDEN_FIELDS
    if bad:
        raise ValueError("These fields can never be shared: " + ", ".join(sorted(bad)))
    unknown = set(requested) - set(ALLOWED_FIELDS)
    if unknown or not requested:
        raise ValueError("Request at least one allow-listed field.")
    enrolment = db.scalars(
        select(Enrolment).where(Enrolment.enrolment_ref == enrolment_ref)
    ).first()
    if enrolment is None:
        raise LookupError("Enrolment reference not found.")
    request = ConsentRequest(
        verifier_id=verifier.id,
        verifier_name=verifier.name,
        subject_person_id=enrolment.person_id,
        fields=json.dumps(requested),
        purpose=purpose.strip()[:240],
        status="pending",
        expires_at=datetime.utcnow() + timedelta(minutes=_ttl_minutes()),
    )
    db.add(request)
    db.flush()
    return request


def decide(db: Session, request_id: int, person_id: int, approve: bool) -> tuple[ConsentRequest, str | None]:
    request = db.get(ConsentRequest, request_id)
    if request is None or request.subject_person_id != person_id:
        raise LookupError("Consent request not found for this student.")
    if request.status != "pending":
        raise ValueError("This request has already been decided.")
    if datetime.utcnow() > request.expires_at:
        request.status = "expired"
        db.flush()
        raise ValueError("This request has expired.")
    request.status = "approved" if approve else "denied"
    request.decided_at = datetime.utcnow()
    raw_token = None
    if approve:
        raw_token = secrets.token_urlsafe(32)
        db.add(
            ShareToken(
                consent_request_id=request.id,
                token_hash=hashlib.sha256(raw_token.encode()).hexdigest(),
                expires_at=request.expires_at,
            )
        )
    db.flush()
    return request, raw_token


def read_shared(db: Session, token: str, verifier: User | None = None) -> dict:
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    share = db.scalars(select(ShareToken).where(ShareToken.token_hash == token_hash)).first()
    if share is None:
        raise LookupError("Share token not found.")
    request = db.get(ConsentRequest, share.consent_request_id)
    if request is None or request.status != "approved":
        raise PermissionError("Consent was not granted.")
    now = datetime.utcnow()
    if now > share.expires_at or now > request.expires_at:
        raise TimeoutError("This consent link has expired.")
    if verifier is not None and request.verifier_id != verifier.id:
        raise PermissionError("This consent link belongs to a different verifier.")

    enrolment = db.scalars(
        select(Enrolment).where(Enrolment.person_id == request.subject_person_id)
    ).first()
    person = db.get(Person, request.subject_person_id)
    programme = db.get(Programme, enrolment.programme_id) if enrolment else None
    institution = db.get(Institution, enrolment.institution_id) if enrolment else None
    fields = json.loads(request.fields)
    values = {
        "enrolled": bool(enrolment and enrolment.status != "withdrawn"),
        "programme": programme.name if programme else None,
        "programme_code": programme.code if programme else None,
        "academic_year": enrolment.academic_year if enrolment else None,
        "institution": institution.name if institution else None,
        "enrolment_status": enrolment.status if enrolment else None,
    }
    share.used_count += 1
    db.add(
        AccessLog(
            verifier_id=request.verifier_id,
            person_id=request.subject_person_id,
            purpose=request.purpose,
            outcome="granted",
        )
    )
    db.flush()
    return {
        "consent_request_id": request.id,
        "purpose": request.purpose,
        "student_reference": person.temp_id if person and not person.apaar_hmac else "verified student",
        "fields": {f: values[f] for f in fields if f in values},
        "shared_at": now.isoformat(),
        "expires_at": share.expires_at.isoformat(),
        "note": "Only fields approved by the student are shown. APAAR, name and DOB are never shared.",
    }


def request_payload(db: Session, request: ConsentRequest) -> dict:
    person = db.get(Person, request.subject_person_id)
    return {
        "id": request.id,
        "verifier_name": request.verifier_name,
        "fields": json.loads(request.fields),
        "purpose": request.purpose,
        "status": request.status,
        "created_at": request.created_at.isoformat(),
        "decided_at": request.decided_at.isoformat() if request.decided_at else None,
        "expires_at": request.expires_at.isoformat(),
        "student_display": person.name_display if person else None,
    }
