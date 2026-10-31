from __future__ import annotations

from fastapi.testclient import TestClient

from app.core.db import SessionLocal
from app.main import app
from app.models import Institution, User
from tests.conftest import auth


def test_unauthenticated_me_is_rejected():
    with TestClient(app) as fresh:
        assert fresh.get("/api/v1/auth/me").status_code == 401


def test_login_and_role_payload():
    with TestClient(app) as fresh:
        response = fresh.post(
            "/api/v1/auth/login",
            json={"email": "admin.syn-mh-001@demo.apaar-setu.invalid", "password": "demo1234"},
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["user"]["role"] == "institution_admin"
        assert payload["user"]["institution"]["code"] == "SYN-MH-001"


def test_wrong_password_rejected():
    with TestClient(app) as fresh:
        response = fresh.post(
            "/api/v1/auth/login",
            json={"email": "admin.syn-mh-001@demo.apaar-setu.invalid", "password": "wrong"},
        )
        assert response.status_code == 401


def test_operator_is_isolated_to_own_institution(roles):
    session = roles["operator_b"]
    with SessionLocal() as db:
        other = db.query(Institution).filter(Institution.aicte_code == "SYN-MH-001").first()
    response = session["client"].get(f"/api/v1/institutions/{other.id}/intake")
    assert response.status_code in {403, 404}
    own = session["client"].get("/api/v1/dashboard/institution")
    assert own.status_code == 200
    assert own.json()["institution"]["aicte_code"] == "SYN-MH-002"


def test_reviewer_reads_all_institutions(roles):
    response = roles["reviewer"]["client"].get("/api/v1/institutions")
    assert response.status_code == 200
    assert len(response.json()["institutions"]) == 12


def test_verifier_cannot_browse_enrolments(roles):
    assert roles["verifier"]["client"].get("/api/v1/enrolments").status_code == 403


def test_csrf_required_for_writes(roles):
    client = roles["reviewer"]["client"]
    findings = client.get("/api/v1/findings?status=open").json()["findings"]
    response = client.post(
        f"/api/v1/findings/{findings[0]['id']}/actions",
        json={"action": "start_review", "comment": "missing csrf"},
        headers={"X-CSRF-Token": "wrong"},
    )
    assert response.status_code == 403


def test_unauthenticated_institution_access_denied():
    with TestClient(app) as fresh:
        assert fresh.get("/api/v1/dashboard/institution").status_code == 401


def test_student_person_linkage(roles):
    with SessionLocal() as db:
        student = db.query(User).filter(User.role == "student").first()
        assert student is not None and student.person_id is not None
    response = roles["student"]["client"].get("/api/v1/consent/requests/mine")
    assert response.status_code == 200
    assert response.json()["role"] == "student"


def test_action_comment_is_mandatory(roles):
    session = roles["reviewer"]
    findings = session["client"].get("/api/v1/findings?status=open").json()["findings"]
    response = session["client"].post(
        f"/api/v1/findings/{findings[0]['id']}/actions",
        json={"action": "start_review", "comment": ""},
        headers=auth(session),
    )
    assert response.status_code == 422


def test_start_review_then_resolve_writes_history(roles):
    session = roles["reviewer"]
    client = session["client"]
    findings = client.get("/api/v1/findings?status=open").json()["findings"]
    finding_id = findings[0]["id"]
    started = client.post(
        f"/api/v1/findings/{finding_id}/actions",
        json={"action": "start_review", "comment": "Opening the evidence for review."},
        headers=auth(session),
    )
    assert started.status_code == 200
    assert started.json()["finding"]["status"] == "in_review"
    resolved = client.post(
        f"/api/v1/findings/{finding_id}/actions",
        json={"action": "resolve", "comment": "Checked with the college; corrected in the next upload."},
        headers=auth(session),
    )
    assert resolved.status_code == 200
    detail = client.get(f"/api/v1/findings/{finding_id}").json()
    assert detail["status"] == "resolved"
    assert len(detail["history"]) >= 3
