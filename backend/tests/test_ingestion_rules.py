from __future__ import annotations

import json
import re
from pathlib import Path

from sqlalchemy import select

from app.core.config import load_rules
from app.core.db import SessionLocal
from app.models import (
    AnomalyScore,
    DuplicateLink,
    Enrolment,
    Finding,
    Institution,
    Programme,
    RowResult,
    UploadBatch,
)
from app.services.ingestion import preview
from app.services.mapping import alias_config
from tests.conftest import auth

ROOT = Path(__file__).resolve().parents[2]
FILE = ROOT / "data" / "synthetic" / "SYN-MH-001_admissions_2026-27.csv"
GT = json.loads((ROOT / "data" / "ground_truth.json").read_text(encoding="utf-8"))


def test_mapping_maps_all_required_fields():
    result = preview(FILE.name, FILE.read_bytes())
    required = [key for key, meta in alias_config().items() if meta.get("required")]
    mapped = result["suggested_mapping"]
    for field in required:
        assert mapped[field]["source_column"], f"{field} was not mapped"
        assert mapped[field]["confidence"] >= 0.9


def test_preview_masks_apaar(roles):
    session = roles["admin"]
    first_apaar = FILE.read_text(encoding="utf-8").splitlines()[1].split(",")[2]
    response = session["client"].post(
        "/api/v1/uploads/preview",
        files={"file": (FILE.name, FILE.read_bytes(), "text/csv")},
        headers=auth(session),
    )
    assert response.status_code == 200
    assert first_apaar not in response.text
    assert "XXXX-XXXX-" in response.text


def test_reupload_is_idempotent(roles):
    session = roles["admin"]
    result = preview(FILE.name, FILE.read_bytes())
    response = session["client"].post(
        "/api/v1/uploads",
        files={"file": (FILE.name, FILE.read_bytes(), "text/csv")},
        data={"mapping": json.dumps(result["suggested_mapping"])},
        headers=auth(session),
    )
    assert response.status_code == 200
    assert response.json()["duplicate_upload"] is True
    with SessionLocal() as db:
        institution = db.scalars(select(Institution).where(Institution.aicte_code == "SYN-MH-001")).one()
        batches = list(db.scalars(select(UploadBatch).where(UploadBatch.institution_id == institution.id)))
        assert len(batches) == 1


def test_rejected_row_counts_match_ground_truth():
    with SessionLocal() as db:
        codes: dict[str, int] = {}
        for row in db.scalars(select(RowResult).where(RowResult.status == "rejected")):
            for code in json.loads(row.error_codes or "[]"):
                codes[code] = codes.get(code, 0) + 1
        assert codes.get("APAAR_FORMAT", 0) == GT["seeded"]["malformed_apaar"] == 150
        assert sum(codes.values()) == GT["totals"]["expected_rejected_rows"]
        assert codes.get("REQUIRED_FIELD_MISSING", 0) == 0


def test_intake_findings_match_seeded_excess():
    with SessionLocal() as db:
        actual = set()
        for finding in db.scalars(select(Finding).where(Finding.rule_code == "INTAKE_EXCEEDED")):
            evidence = json.loads(finding.subject_json)
            institution = db.get(Institution, finding.institution_id)
            actual.add((institution.aicte_code, evidence["programme_code"], evidence["excess"]))
    expected = {
        (row["institution_code"], row["programme_code"], row["excess"])
        for row in GT["seeded"]["over_intake"]
    }
    assert actual == expected


def test_special_categories_not_counted_against_regular_intake():
    with SessionLocal() as db:
        finding = db.scalars(select(Finding).where(Finding.rule_code == "INTAKE_EXCEEDED").limit(1)).first()
        evidence = json.loads(finding.subject_json)
        institution = db.get(Institution, finding.institution_id)
        regular = 0
        for enrolment in db.scalars(select(Enrolment).where(Enrolment.institution_id == institution.id)):
            programme = db.get(Programme, enrolment.programme_id)
            if programme.code == evidence["programme_code"] and enrolment.seat_category == "regular":
                regular += 1
        assert regular == evidence["regular_admitted"]


def test_null_cap_never_invents_a_number():
    rules = load_rules()
    assert rules["intake"]["seat_categories"]["tfw"]["cap_pct_of_approved"] is None
    with SessionLocal() as db:
        for finding in db.scalars(select(Finding).where(Finding.rule_code == "SEAT_CAP_NOT_CONFIGURED")):
            evidence = json.loads(finding.subject_json)
            assert evidence["configured_cap"] is None
            assert not re.search(r"cap of \d+", finding.explanation)


def test_duplicate_links_and_whitelist():
    with SessionLocal() as db:
        links = list(db.scalars(select(DuplicateLink)))
        exact = [link for link in links if link.match_type == "exact_apaar"]
        whitelisted = [link for link in exact if link.whitelisted_reason]
    assert len(exact) == 35
    assert len(whitelisted) == 5
    assert any(link.match_type == "fuzzy" for link in links)


def _numbers_in(value) -> set[float]:
    found: set[float] = set()
    if isinstance(value, dict):
        for nested in value.values():
            found |= _numbers_in(nested)
    elif isinstance(value, (int, float)) and not isinstance(value, bool):
        found.add(round(float(value), 1))
    return found


def test_anomaly_reasons_are_backed_by_stored_features():
    with SessionLocal() as db:
        scores = list(db.scalars(select(AnomalyScore).where(AnomalyScore.flagged.is_(True))))
        assert len(scores) >= 3
        seeded = {"SYN-MH-003", "SYN-TN-008", "SYN-UP-012"}
        institutions = {i.id: i for i in db.scalars(select(Institution))}
        assert seeded <= {institutions[s.institution_id].aicte_code for s in scores}
        for score in scores:
            reasons = json.loads(score.reasons_json)
            assert len(reasons) >= 2
            allowed = _numbers_in(json.loads(score.features_json))
            for number in re.findall(r"\d+(?:\.\d+)?", " ".join(reasons)):
                assert round(float(number), 1) in allowed


def test_dashboards_match_sql_counts(roles):
    with SessionLocal() as db:
        total = len(list(db.scalars(select(Enrolment).where(Enrolment.status != "withdrawn"))))
    response = roles["reviewer"]["client"].get("/api/v1/dashboard/central")
    assert response.status_code == 200
    assert response.json()["kpis"]["enrolments"] == total


def test_llm_is_off_and_product_still_works(roles):
    session = roles["reviewer"]
    assert session["client"].get("/api/v1/meta").json()["llm_provider"] == "none"
    copilot = session["client"].post(
        "/api/v1/copilot/query",
        json={"question": "which colleges are over intake"},
        headers=auth(session),
    )
    assert copilot.status_code == 200
    assert copilot.json()["tool"] == "colleges_over_intake"
    assert copilot.json()["llm_used"] is False
