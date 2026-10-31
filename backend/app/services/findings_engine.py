"""Deterministic rule engine -> findings.

Rules only flag. Nothing here rejects a college or a student, and no machine
learning decides a compliance outcome.
"""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import date

from rapidfuzz import fuzz
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.adapters import get_identity_provider
from app.core.crypto import mask_apaar
from app.models import (
    Enrolment,
    Finding,
    FindingEvent,
    Institution,
    IntakeApproval,
    Person,
    Programme,
    RowResult,
    UploadBatch,
)
from app.services.rules_config import get_active_rule_version

MANAGED_RULES = {
    "APAAR_MISSING",
    "APAAR_NOT_FOUND",
    "APAAR_INACTIVE",
    "IDENTITY_MISMATCH",
    "DUP_IN_FILE",
    "DUP_SAME_INSTITUTION",
    "CATEGORY_INCONSISTENT",
    "DATE_IMPLAUSIBLE",
    "LATE_ADMISSION",
    "INTAKE_EXCEEDED",
    "SEAT_CAP_EXCEEDED",
    "SEAT_CAP_NOT_CONFIGURED",
}

RULE_META = {
    "APAAR_MISSING": (
        "warning",
        "APAAR not provided",
        "The row has no APAAR and is not marked pending or declined.",
        "Without an identifier the record can be counted but not linked to a verified student.",
        "Ask the student to share APAAR, or mark the record as pending/declined.",
    ),
    "APAAR_NOT_FOUND": (
        "warning",
        "APAAR not found in the simulated registry",
        "The identifier was looked up in the mock registry only.",
        "The prototype cannot confirm identity against a real ABC/APAAR service.",
        "Verify the identifier with the student and re-upload; this is SIMULATED.",
    ),
    "APAAR_INACTIVE": (
        "warning",
        "APAAR inactive in the simulated registry",
        "The mock registry returns status 'inactive' for this identifier.",
        "An inactive identifier may indicate a stale or non-current record.",
        "Ask the student to confirm their identifier status.",
    ),
    "IDENTITY_MISMATCH": (
        "warning",
        "Name or date of birth differs from the registry",
        "Fuzzy name comparison and date-of-birth equality against the mock registry.",
        "A mismatch may be a transliteration variant or an incorrect record.",
        "Check the admission form against the student's documents.",
    ),
    "DUP_IN_FILE": (
        "warning",
        "Same APAAR appears twice in one upload",
        "The identifier repeats inside the same file; the enrolment was counted once.",
        "Duplicate rows inflate totals and hide data-entry mistakes.",
        "Remove the repeated row or confirm it is a correction.",
    ),
    "DUP_SAME_INSTITUTION": (
        "warning",
        "Same student already enrolled in this programme",
        "An existing enrolment for the same person, programme and year was found.",
        "Repeated enrolment in one programme may inflate intake usage.",
        "Confirm whether this is a transfer, correction, or a second seat.",
    ),
    "CATEGORY_INCONSISTENT": (
        "warning",
        "Seat category conflicts with nationality",
        "NRI/OCI/FN seats were declared with Indian nationality, or a "
        "foreign-national seat has an unexpected combination.",
        "Category counts feed cap checks and must reflect the actual quota claimed.",
        "Verify the category evidence and correct the row if needed.",
    ),
    "DATE_IMPLAUSIBLE": (
        "warning",
        "Implausible date of birth",
        "Age at admission falls outside 15-60 years.",
        "A wrong date of birth breaks identity matching and duplicate detection.",
        "Correct the date and re-upload the row.",
    ),
    "LATE_ADMISSION": (
        "warning",
        "Admission outside the configured window",
        "The admission date is outside the versioned admission window.",
        "Late admissions may fall outside the approved cycle.",
        "Confirm the admission date or record an approved exception.",
    ),
    "INTAKE_EXCEEDED": (
        "blocker",
        "Regular admissions exceed approved intake",
        "Regular-seat admissions are counted against the approved intake for this programme and year.",
        "Admitting beyond approved intake is a regulatory compliance question for human review.",
        "Review the intake evidence and respond with a comment; do not auto-reject records.",
    ),
    "SEAT_CAP_EXCEEDED": (
        "risk",
        "Seat category cap exceeded",
        "The category count exceeds the configured percentage of approved intake.",
        "Supernumerary and reserved-category seats have separate ceilings.",
        "Review the category allocations and the policy assumption used.",
    ),
    "SEAT_CAP_NOT_CONFIGURED": (
        "info",
        "Seat-category cap not configured",
        "The policy file has no confirmed cap for this category.",
        "The engine never guesses a regulatory number; an unset cap cannot be checked.",
        "A human must add a confirmed cap to config/rules.yaml.",
    ),
}

SEVERITY_RANK = {"blocker": 0, "risk": 1, "warning": 2, "info": 3}


def finding_ref(finding: Finding) -> str:
    return f"FND-{finding.id:05d}"


def _upsert(
    db: Session,
    *,
    rule_code: str,
    institution_id: int,
    subject_key: str,
    enrolment_id: int | None,
    evidence: dict,
    explanation: str,
    recommended_action: str,
    policy_assumption: str | None,
) -> Finding | None:
    severity = RULE_META[rule_code][0]
    existing = db.scalars(
        select(Finding).where(
            Finding.rule_code == rule_code,
            Finding.institution_id == institution_id,
            Finding.subject_key == subject_key,
        )
    ).first()
    if existing:
        if existing.status in {"open", "in_review"}:
            existing.subject_json = json.dumps(evidence, default=str)
            existing.explanation = explanation
            existing.policy_assumption = policy_assumption
            return existing
        return None
    finding = Finding(
        rule_code=rule_code,
        severity=severity,
        institution_id=institution_id,
        enrolment_id=enrolment_id,
        subject_key=subject_key,
        subject_json=json.dumps(evidence, default=str),
        explanation=explanation,
        recommended_action=recommended_action,
        policy_assumption=policy_assumption,
        status="open",
    )
    db.add(finding)
    db.flush()
    db.add(
        FindingEvent(
            finding_id=finding.id,
            action="created",
            comment="Raised by the deterministic rule engine. A human decides what happens next.",
            actor_name="rule-engine",
        )
    )
    return finding


def refresh_institution(db: Session, institution_id: int) -> dict:
    rules_version = get_active_rule_version(db)
    rules = rules_version.config
    window_start = date.fromisoformat(str(rules["admission_window"]["start"]))
    window_end = date.fromisoformat(str(rules["admission_window"]["end"]))
    seat_config = rules.get("intake", {}).get("seat_categories", {})
    provider = get_identity_provider(db)

    institution = db.get(Institution, institution_id)
    if institution is None:
        return {"raised": 0}

    programmes = list(
        db.scalars(select(Programme).where(Programme.institution_id == institution_id))
    )
    approvals = {
        (a.programme_id, a.academic_year): a
        for a in db.scalars(
            select(IntakeApproval).join(Programme).where(
                Programme.institution_id == institution_id
            )
        )
    }
    enrolments = list(
        db.scalars(
            select(Enrolment).where(
                Enrolment.institution_id == institution_id,
                Enrolment.status != "withdrawn",
            )
        )
    )
    persons = {
        p.id: p
        for p in db.scalars(
            select(Person).where(Person.id.in_([e.person_id for e in enrolments] or [0]))
        )
    }
    active_keys: dict[str, set[str]] = defaultdict(set)
    raised = 0

    # ------------- per-enrolment rules -------------
    for enrolment in enrolments:
        person = persons.get(enrolment.person_id)
        programme = next((p for p in programmes if p.id == enrolment.programme_id), None)
        if not person or not programme:
            continue
        base = {
            "enrolment_ref": enrolment.enrolment_ref,
            "student": person.name_display,
            "programme": f"{programme.code} — {programme.name}",
            "seat_category": enrolment.seat_category,
            "admission_date": enrolment.admission_date.isoformat(),
        }

        identity = provider.lookup(_decrypt_or_none(person)) if person.apaar_hmac else None

        if not person.apaar_hmac and person.apaar_status not in {"pending", "declined"}:
            key = f"person:{person.id}"
            active_keys["APAAR_MISSING"].add(key)
            if _upsert(
                db,
                rule_code="APAAR_MISSING",
                institution_id=institution_id,
                subject_key=key,
                enrolment_id=enrolment.id,
                evidence={
                    **base,
                    "masked_person_ref": person.temp_id or f"person:{person.id}",
                    "apaar_status": person.apaar_status,
                },
                explanation=(
                    f"{person.name_display} ({programme.code}) has no APAAR and is not marked "
                    "pending or declined. The row was counted using a temporary reference."
                ),
                recommended_action=RULE_META["APAAR_MISSING"][4],
                policy_assumption=None,
            ):
                raised += 1

        if identity is not None:
            if not identity.found:
                key = f"person:{person.id}"
                active_keys["APAAR_NOT_FOUND"].add(key)
                if _upsert(
                    db,
                    rule_code="APAAR_NOT_FOUND",
                    institution_id=institution_id,
                    subject_key=key,
                    enrolment_id=enrolment.id,
                    evidence={**base, "provider": "mock_apaar", "simulated": True},
                    explanation=(
                        f"The APAAR for {person.name_display} was not found in the simulated "
                        "registry. This is a mock lookup, not an official APAAR verification."
                    ),
                    recommended_action=RULE_META["APAAR_NOT_FOUND"][4],
                    policy_assumption="Identity lookups use SIMULATED provider data.",
                ):
                    raised += 1
            else:
                if identity.status == "inactive":
                    key = f"person:{person.id}"
                    active_keys["APAAR_INACTIVE"].add(key)
                    if _upsert(
                        db,
                        rule_code="APAAR_INACTIVE",
                        institution_id=institution_id,
                        subject_key=key,
                        enrolment_id=enrolment.id,
                        evidence={
                            **base,
                            "registry_status": identity.status,
                            "provider": "mock_apaar",
                            "simulated": True,
                        },
                        explanation=(
                            f"The simulated registry marks this APAAR as inactive for "
                            f"{person.name_display}."
                        ),
                        recommended_action=RULE_META["APAAR_INACTIVE"][4],
                        policy_assumption="Identity lookups use SIMULATED provider data.",
                    ):
                        raised += 1

                name_score = fuzz.token_sort_ratio(person.name_norm, (identity.name or "").lower())
                dob_match = identity.dob == person.dob
                if name_score < 90 or not dob_match:
                    key = f"person:{person.id}"
                    active_keys["IDENTITY_MISMATCH"].add(key)
                    if _upsert(
                        db,
                        rule_code="IDENTITY_MISMATCH",
                        institution_id=institution_id,
                        subject_key=key,
                        enrolment_id=enrolment.id,
                        evidence={
                            **base,
                            "name_similarity": round(name_score, 1),
                            "dob_match": dob_match,
                            "provider": "mock_apaar",
                            "simulated": True,
                        },
                        explanation=(
                            f"Name similarity {round(name_score, 1)}/100 and date of birth "
                            f"{'match' if dob_match else 'does not match'} the simulated registry "
                            f"record for {person.name_display}."
                        ),
                        recommended_action=RULE_META["IDENTITY_MISMATCH"][4],
                        policy_assumption="Identity lookups use SIMULATED provider data.",
                    ):
                        raised += 1

        age = (enrolment.admission_date - person.dob).days / 365.25
        if age < 15 or age > 60:
            key = f"enrolment:{enrolment.id}"
            active_keys["DATE_IMPLAUSIBLE"].add(key)
            if _upsert(
                db,
                rule_code="DATE_IMPLAUSIBLE",
                institution_id=institution_id,
                subject_key=key,
                enrolment_id=enrolment.id,
                evidence={
                    **base,
                    "age_at_admission": round(age, 1),
                    "reason": "below 15 years" if age < 15 else "above 60 years",
                },
                explanation=(
                    f"Age at admission is {round(age, 1)} years for {person.name_display}, "
                    "outside the configured plausible range."
                ),
                recommended_action=RULE_META["DATE_IMPLAUSIBLE"][4],
                policy_assumption="Plausible age range 15-60 is a prototype assumption.",
            ):
                raised += 1

        if not (window_start <= enrolment.admission_date <= window_end):
            key = f"enrolment:{enrolment.id}"
            active_keys["LATE_ADMISSION"].add(key)
            if _upsert(
                db,
                rule_code="LATE_ADMISSION",
                institution_id=institution_id,
                subject_key=key,
                enrolment_id=enrolment.id,
                evidence={
                    **base,
                    "window_start": window_start.isoformat(),
                    "window_end": window_end.isoformat(),
                },
                explanation=(
                    f"Admission date {enrolment.admission_date.isoformat()} is outside the "
                    f"{window_start.isoformat()} to {window_end.isoformat()} window "
                    "(policy version "
                    f"{rules_version.version})."
                ),
                recommended_action=RULE_META["LATE_ADMISSION"][4],
                policy_assumption=f"Admission window is an assumption (rules v{rules_version.version}).",
            ):
                raised += 1

        if enrolment.seat_category in {"fn", "nri", "oci"} and enrolment.nationality == "India":
            key = f"enrolment:{enrolment.id}"
            active_keys["CATEGORY_INCONSISTENT"].add(key)
            if _upsert(
                db,
                rule_code="CATEGORY_INCONSISTENT",
                institution_id=institution_id,
                subject_key=key,
                enrolment_id=enrolment.id,
                evidence={
                    **base,
                    "nationality": enrolment.nationality,
                    "category": enrolment.seat_category,
                },
                explanation=(
                    f"A {enrolment.seat_category.upper()} seat was declared with nationality "
                    f"'{enrolment.nationality}'. Category and nationality disagree."
                ),
                recommended_action=RULE_META["CATEGORY_INCONSISTENT"][4],
                policy_assumption=None,
            ):
                raised += 1

        # same institution, same programme + year, same person
        siblings = [
            e
            for e in enrolments
            if e.person_id == enrolment.person_id
            and e.programme_id == enrolment.programme_id
            and e.academic_year == enrolment.academic_year
            and e.id != enrolment.id
        ]
        if siblings:
            key = f"person:{person.id}:programme:{programme.id}:year:{enrolment.academic_year}"
            active_keys["DUP_SAME_INSTITUTION"].add(key)
            if _upsert(
                db,
                rule_code="DUP_SAME_INSTITUTION",
                institution_id=institution_id,
                subject_key=key,
                enrolment_id=enrolment.id,
                evidence={
                    **base,
                    "matching_enrolments": len(siblings) + 1,
                    "programme_code": programme.code,
                },
                explanation=(
                    f"{person.name_display} has {len(siblings) + 1} enrolments in "
                    f"{programme.code} for {enrolment.academic_year} at this institution."
                ),
                recommended_action=RULE_META["DUP_SAME_INSTITUTION"][4],
                policy_assumption=None,
            ):
                raised += 1

    # ------------- in-file duplicates -------------
    batches = list(
        db.scalars(select(UploadBatch).where(UploadBatch.institution_id == institution_id))
    )
    batch_ids = [b.id for b in batches]
    rows = (
        list(db.scalars(select(RowResult).where(RowResult.batch_id.in_(batch_ids or [0]))))
        if batch_ids
        else []
    )
    for row in rows:
        codes = json.loads(row.error_codes or "[]")
        if "DUP_IN_FILE" not in codes:
            continue
        key = f"row:{row.batch_id}:{row.row_number}"
        active_keys["DUP_IN_FILE"].add(key)
        if _upsert(
            db,
            rule_code="DUP_IN_FILE",
            institution_id=institution_id,
            subject_key=key,
            enrolment_id=None,
            evidence={
                "row_number": row.row_number,
                "batch_id": row.batch_id,
                "detail": json.loads(row.error_detail or "[]"),
            },
            explanation=(
                f"Row {row.row_number} repeats an APAAR already present earlier in the same "
                "file. The duplicate was not counted as a second enrolment."
            ),
            recommended_action=RULE_META["DUP_IN_FILE"][4],
            policy_assumption=None,
        ):
            raised += 1

    # ------------- intake counters -------------
    counts: dict[tuple[int, str, str], int] = defaultdict(int)
    for e in enrolments:
        counts[(e.programme_id, e.academic_year, e.seat_category)] += 1

    for programme in programmes:
        for year in {e.academic_year for e in enrolments if e.programme_id == programme.id}:
            approval = approvals.get((programme.id, year))
            if approval is None:
                continue
            approved = approval.approved_intake
            regular = counts.get((programme.id, year, "regular"), 0)
            key = f"programme:{programme.id}:year:{year}"
            if regular > approved:
                active_keys["INTAKE_EXCEEDED"].add(key)
                if _upsert(
                    db,
                    rule_code="INTAKE_EXCEEDED",
                    institution_id=institution_id,
                    subject_key=key,
                    enrolment_id=None,
                    evidence={
                        "programme_code": programme.code,
                        "programme_name": programme.name,
                        "academic_year": year,
                        "approved_intake": approved,
                        "regular_admitted": regular,
                        "excess": regular - approved,
                        "capacity_used_pct": round(regular / approved * 100, 1),
                        "counts_basis": "regular seats only; supernumerary/NRI/OCI/FN excluded",
                    },
                    explanation=(
                        f"{programme.code} admitted {regular} regular students against an "
                        f"approved intake of {approved} — {regular - approved} above approval. "
                        "Supernumerary, NRI, OCI and FN seats are counted separately."
                    ),
                    recommended_action=RULE_META["INTAKE_EXCEEDED"][4],
                    policy_assumption=(
                        "Approved intake values are synthetic seed data; the counting rule is a "
                        "documented prototype assumption."
                    ),
                ):
                    raised += 1

            for category, meta in seat_config.items():
                if category == "regular":
                    continue
                count = counts.get((programme.id, year, category), 0)
                if count == 0:
                    continue
                cap_pct = meta.get("cap_pct_of_approved")
                cap_key = f"programme:{programme.id}:year:{year}:category:{category}"
                if cap_pct is None:
                    active_keys["SEAT_CAP_NOT_CONFIGURED"].add(cap_key)
                    if _upsert(
                        db,
                        rule_code="SEAT_CAP_NOT_CONFIGURED",
                        institution_id=institution_id,
                        subject_key=cap_key,
                        enrolment_id=None,
                        evidence={
                            "programme_code": programme.code,
                            "academic_year": year,
                            "category": category,
                            "category_label": meta.get("label", category),
                            "admitted": count,
                            "configured_cap": None,
                        },
                        explanation=(
                            f"No confirmed cap is configured for {meta.get('label', category)} "
                            f"seats in {programme.code}. The engine will not invent a number; "
                            f"{count} admissions are recorded without a cap check."
                        ),
                        recommended_action=RULE_META["SEAT_CAP_NOT_CONFIGURED"][4],
                        policy_assumption=f"{meta.get('label', category)} cap status: "
                        f"{meta.get('status', 'assumption')}.",
                    ):
                        raised += 1
                else:
                    cap_seats = int(approved * float(cap_pct) / 100)
                    if count > cap_seats:
                        active_keys["SEAT_CAP_EXCEEDED"].add(cap_key)
                        if _upsert(
                            db,
                            rule_code="SEAT_CAP_EXCEEDED",
                            institution_id=institution_id,
                            subject_key=cap_key,
                            enrolment_id=None,
                            evidence={
                                "programme_code": programme.code,
                                "academic_year": year,
                                "category": category,
                                "category_label": meta.get("label", category),
                                "configured_cap": cap_seats,
                                "cap_pct_of_approved": cap_pct,
                                "approved_intake": approved,
                                "admitted": count,
                                "excess": count - cap_seats,
                            },
                            explanation=(
                                f"{programme.code} admitted {count} {meta.get('label', category)} "
                                f"students against a configured cap of {cap_seats} "
                                f"({cap_pct}% of {approved}). Assumption status: "
                                f"{meta.get('status', 'assumption')}."
                            ),
                            recommended_action=RULE_META["SEAT_CAP_EXCEEDED"][4],
                            policy_assumption=(
                                f"Cap {cap_pct}% of approved intake is status "
                                f"'{meta.get('status', 'assumption')}' — "
                                f"{meta.get('source', 'source not recorded')}."
                            ),
                        ):
                            raised += 1

    # ------------- auto-resolve conditions that no longer hold -------------
    existing = list(
        db.scalars(
            select(Finding).where(
                Finding.institution_id == institution_id,
                Finding.rule_code.in_(MANAGED_RULES),
                Finding.status.in_(["open", "in_review"]),
            )
        )
    )
    auto_resolved = 0
    for finding in existing:
        if finding.subject_key not in active_keys[finding.rule_code]:
            finding.status = "resolved"
            db.add(
                FindingEvent(
                    finding_id=finding.id,
                    action="auto_resolved",
                    comment="Auto-resolved: the condition no longer holds after re-validation.",
                    actor_name="rule-engine",
                )
            )
            auto_resolved += 1

    db.flush()
    return {"raised": raised, "auto_resolved": auto_resolved, "active": sum(len(v) for v in active_keys.values())}


def _decrypt_or_none(person: Person) -> str:
    """The mock provider needs a plain identifier; decrypted only in memory."""
    from app.core.crypto import decrypt_identifier

    return decrypt_identifier(person.apaar_enc) or ""


def finding_payload(finding: Finding, institution: Institution | None = None) -> dict:
    meta = RULE_META.get(finding.rule_code, ("info", finding.rule_code, "", "", ""))
    return {
        "id": finding.id,
        "ref": finding_ref(finding),
        "rule_code": finding.rule_code,
        "severity": finding.severity,
        "title": meta[1],
        "what_checks": meta[2],
        "why_matters": meta[3],
        "institution_id": finding.institution_id,
        "institution_name": institution.name if institution else None,
        "institution_code": institution.aicte_code if institution else None,
        "enrolment_id": finding.enrolment_id,
        "evidence": json.loads(finding.subject_json or "{}"),
        "explanation": finding.explanation,
        "recommended_action": finding.recommended_action,
        "policy_assumption": finding.policy_assumption,
        "status": finding.status,
        "created_at": finding.created_at.isoformat(),
        "updated_at": finding.updated_at.isoformat(),
    }


def mask_evidence(evidence: dict) -> dict:
    """Defensive: never leak a full identifier even if one reached storage."""
    clean = {}
    for key, value in evidence.items():
        if isinstance(value, str) and len(value) == 12 and value.isdigit():
            clean[key] = mask_apaar(value)
        else:
            clean[key] = value
    return clean
