from __future__ import annotations

import json
import re
from datetime import datetime, timedelta

from sqlalchemy import select

from app.core.db import SessionLocal
from app.models import AuditLog, ConsentRequest, Credential, Enrolment, Person, ShareToken, User
from tests.conftest import auth

FORBIDDEN_KEYS = {"apaar", "apaar_id", "name", "dob", "date_of_birth", "phone", "email"}


def test_valid_then_tampered_then_revoked_credential(roles):
    with SessionLocal() as db:
        credential = db.scalars(select(Credential).limit(1)).first()
        credential_id = credential.credential_id
        original = credential.payload_json
        payload_text = json.dumps(json.loads(original)).lower()
        assert '"apaar' not in payload_text
        assert '"dob' not in payload_text
        assert not re.search(r"\d{12}", payload_text)  # no identifier value embedded

    admin = roles["admin"]["client"]
    valid = admin.get(f"/api/v1/verify/{credential_id}")
    assert valid.status_code == 200
    assert valid.json()["status"] == "VALID"

    with SessionLocal() as db:
        credential = db.scalars(select(Credential).where(Credential.credential_id == credential_id)).one()
        tampered = json.loads(credential.payload_json)
        tampered["claims"]["programme"] = "TAMPERED DEMO"
        credential.payload_json = json.dumps(tampered, sort_keys=True)
        db.commit()
    assert admin.get(f"/api/v1/verify/{credential_id}").json()["status"] == "TAMPERED"

    with SessionLocal() as db:
        credential = db.scalars(select(Credential).where(Credential.credential_id == credential_id)).one()
        credential.payload_json = original
        db.commit()
    assert admin.get(f"/api/v1/verify/{credential_id}").json()["status"] == "VALID"

    revoke = admin.post(
        f"/api/v1/credentials/{credential_id}/revoke",
        json={"reason": "demo revocation for test"},
        headers=auth(roles["admin"]),
    )
    assert revoke.status_code == 200
    assert admin.get(f"/api/v1/verify/{credential_id}").json()["status"] == "REVOKED"

    with SessionLocal() as db:
        credential = db.scalars(select(Credential).where(Credential.credential_id == credential_id)).one()
        credential.status = "valid"
        credential.revoked_at = None
        credential.revoke_reason = None
        db.commit()


def test_unknown_credential_is_not_found(roles):
    response = roles["admin"]["client"].get("/api/v1/verify/cred_does_not_exist")
    assert response.status_code == 200
    assert response.json()["status"] == "NOT_FOUND"


def test_credential_report_has_signature_and_simulated_flag(roles):
    with SessionLocal() as db:
        credential = db.scalars(select(Credential).limit(1)).one()
    body = roles["admin"]["client"].get(f"/api/v1/verify/{credential.credential_id}").json()
    assert body["signature_valid"] is True
    assert body["simulated"] is True


def test_consent_flow_shares_only_allow_listed_fields(roles):
    verifier = roles["verifier"]
    student_session = roles["student"]
    with SessionLocal() as db:
        student = db.scalars(select(User).where(User.role == "student")).one()
        enrolment = db.scalars(select(Enrolment).where(Enrolment.person_id == student.person_id).limit(1)).one()
        ref = enrolment.enrolment_ref
        person = db.get(Person, student.person_id)

    created = verifier["client"].post(
        "/api/v1/consent/requests",
        json={"enrolment_ref": ref, "fields": ["enrolled", "programme"], "purpose": "test purpose"},
        headers=auth(verifier),
    )
    assert created.status_code == 200
    request_id = created.json()["request"]["id"]

    inbox = student_session["client"].get("/api/v1/consent/requests/mine")
    assert any(item["id"] == request_id for item in inbox.json()["requests"])

    decision = student_session["client"].post(
        f"/api/v1/consent/requests/{request_id}/decision",
        json={"approve": True},
        headers=auth(student_session),
    )
    assert decision.status_code == 200
    token = decision.json()["share_token"]
    assert token

    shared = verifier["client"].get(f"/api/v1/consent/share/{token}")
    assert shared.status_code == 200
    fields = shared.json()["fields"]
    assert set(fields) == {"enrolled", "programme"}
    assert not FORBIDDEN_KEYS & set(fields)
    assert person.name_display not in json.dumps(fields)

    with SessionLocal() as db:
        share = db.scalars(select(ShareToken).order_by(ShareToken.id.desc()).limit(1)).first()
        share.expires_at = datetime.utcnow() - timedelta(minutes=1)
        db.commit()
    assert verifier["client"].get(f"/api/v1/consent/share/{token}").status_code == 410


def test_denied_consent_shares_nothing(roles):
    verifier = roles["verifier"]
    student_session = roles["student"]
    with SessionLocal() as db:
        student = db.scalars(select(User).where(User.role == "student")).one()
        enrolment = db.scalars(select(Enrolment).where(Enrolment.person_id == student.person_id).limit(1)).one()
        ref = enrolment.enrolment_ref
    created = verifier["client"].post(
        "/api/v1/consent/requests",
        json={"enrolment_ref": ref, "fields": ["enrolled"], "purpose": "denied test"},
        headers=auth(verifier),
    )
    request_id = created.json()["request"]["id"]
    decision = student_session["client"].post(
        f"/api/v1/consent/requests/{request_id}/decision",
        json={"approve": False},
        headers=auth(student_session),
    )
    assert decision.status_code == 200
    assert decision.json()["share_token"] is None
    with SessionLocal() as db:
        assert db.get(ConsentRequest, request_id).status == "denied"


def test_forbidden_consent_fields_cannot_be_requested(roles):
    verifier = roles["verifier"]
    with SessionLocal() as db:
        student = db.scalars(select(User).where(User.role == "student")).one()
        ref = db.scalars(select(Enrolment).where(Enrolment.person_id == student.person_id).limit(1)).one().enrolment_ref
    response = verifier["client"].post(
        "/api/v1/consent/requests",
        json={"enrolment_ref": ref, "fields": ["dob", "apaar"], "purpose": "bad request"},
        headers=auth(verifier),
    )
    assert response.status_code == 400


def test_audit_chain_detects_tampering(roles):
    reviewer = roles["reviewer"]["client"]
    assert reviewer.get("/api/v1/audit/verify").json()["valid"] is True
    with SessionLocal() as db:
        entry = db.scalars(select(AuditLog).order_by(AuditLog.seq.desc()).limit(1)).one()
        original = entry.detail_json
        entry.detail_json = json.dumps({"tampered": True})
        db.commit()
        broken_seq = entry.seq
    result = reviewer.get("/api/v1/audit/verify").json()
    assert result["valid"] is False
    assert result["broken_seq"] == broken_seq
    with SessionLocal() as db:
        entry = db.scalars(select(AuditLog).where(AuditLog.seq == broken_seq)).one()
        entry.detail_json = original
        db.commit()
    assert reviewer.get("/api/v1/audit/verify").json()["valid"] is True
