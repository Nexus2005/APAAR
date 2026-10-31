"""Time-aware duplicate detection. Exact APAAR first, then blocked fuzzy matching.

Never auto-rejects. A human reviewer sees both records side by side.
"""

from __future__ import annotations

import itertools
import json

from rapidfuzz import fuzz
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import load_rules
from app.core.crypto import mask_apaar
from app.models import DuplicateLink, Enrolment, Finding, FindingEvent, Institution, Person, Programme


def _programme(db: Session, enrolment: Enrolment) -> Programme | None:
    return db.get(Programme, enrolment.programme_id)


def _institution(db: Session, enrolment: Enrolment) -> Institution | None:
    return db.get(Institution, enrolment.institution_id)


def mask_apaar_by_person(person: Person | None) -> str:
    if person is None or not person.apaar_hmac:
        return "not provided"
    from app.core.crypto import decrypt_identifier

    return mask_apaar(decrypt_identifier(person.apaar_enc))


def _side(db: Session, enrolment: Enrolment, person: Person) -> dict:
    programme = _programme(db, enrolment)
    institution = _institution(db, enrolment)
    return {
        "enrolment_ref": enrolment.enrolment_ref,
        "institution": institution.short_name if institution else "?",
        "institution_code": institution.aicte_code if institution else "?",
        "programme": programme.code if programme else "?",
        "programme_name": programme.name if programme else "?",
        "academic_year": enrolment.academic_year,
        "admission_date": enrolment.admission_date.isoformat(),
        "seat_category": enrolment.seat_category,
        "student": person.name_display,
        "dob": person.dob.isoformat(),
        "apaar_masked": mask_apaar_by_person(person),
        "status": enrolment.status,
    }


def _whitelist_reason(a: Enrolment, b: Enrolment, rules: dict) -> str | None:
    configured = rules.get("duplicates", {}).get("whitelist_pairs", [])
    remarks = f"{a.remarks} {b.remarks}".lower()
    if "approved_dual_degree" in configured and ("dual degree" in remarks or "dual-degree" in remarks):
        return "approved_dual_degree"
    return None


def _link_exists(db: Session, a: int, b: int) -> DuplicateLink | None:
    return db.scalars(
        select(DuplicateLink).where(
            ((DuplicateLink.enrolment_a == a) & (DuplicateLink.enrolment_b == b))
            | ((DuplicateLink.enrolment_a == b) & (DuplicateLink.enrolment_b == a))
        )
    ).first()


def _raise_cross_finding(
    db: Session, link: DuplicateLink, institution: Institution, side_a: dict, side_b: dict
) -> None:
    key = f"link:{link.id}"
    if db.scalars(
        select(Finding).where(
            Finding.rule_code == "DUP_CROSS_INSTITUTION", Finding.subject_key == key
        )
    ).first():
        return
    finding = Finding(
        rule_code="DUP_CROSS_INSTITUTION",
        severity="risk",
        institution_id=institution.id,
        enrolment_id=link.enrolment_a,
        subject_key=key,
        subject_json=json.dumps(
            {"match_type": link.match_type, "score": link.score, "a": side_a, "b": side_b},
            default=str,
        ),
        explanation=(
            f"The same student reference is admitted at {side_a['institution']} "
            f"({side_a['programme']}) and {side_b['institution']} ({side_b['programme']}) "
            f"for {side_a['academic_year']}. Match type: {link.match_type}."
        ),
        recommended_action=(
            "Review both admissions with the student and institutions. This is a review "
            "signal, never an automatic penalty."
        ),
        policy_assumption=(
            "Matching uses a keyed identifier fingerprint; fuzzy matches also compare name "
            "and date of birth. Legitimate dual degrees must be whitelisted."
        ),
        status="open",
    )
    db.add(finding)
    db.flush()
    db.add(
        FindingEvent(
            finding_id=finding.id,
            action="created",
            comment="Raised by the duplicate detector for human review.",
            actor_name="duplicate-engine",
        )
    )


def detect_exact(db: Session) -> dict:
    rules = load_rules()
    persons = list(db.scalars(select(Person).where(Person.apaar_hmac.is_not(None))))
    created = 0
    links = 0
    for person in persons:
        enrolments = list(
            db.scalars(
                select(Enrolment).where(
                    Enrolment.person_id == person.id,
                    Enrolment.status.in_(["admitted", "verified"]),
                )
            )
        )
        for a, b in itertools.combinations(enrolments, 2):
            if a.institution_id == b.institution_id:
                continue
            if a.academic_year != b.academic_year:
                continue
            if _link_exists(db, a.id, b.id):
                continue
            reason = _whitelist_reason(a, b, rules)
            side_a = _side(db, a, person)
            side_b = _side(db, b, person)
            link = DuplicateLink(
                enrolment_a=a.id,
                enrolment_b=b.id,
                match_type="exact_apaar",
                score=100.0,
                evidence_json=json.dumps({"a": side_a, "b": side_b}, default=str),
                whitelisted_reason=reason,
            )
            db.add(link)
            db.flush()
            links += 1
            if reason is None:
                institution = db.get(Institution, a.institution_id)
                if institution:
                    _raise_cross_finding(db, link, institution, side_a, side_b)
                    created += 1
    db.flush()
    return {"links": links, "findings": created}


def detect_fuzzy(db: Session) -> dict:
    rules = load_rules()
    threshold = float(rules.get("fuzzy", {}).get("name_threshold", 90))
    require_dob = bool(rules.get("fuzzy", {}).get("require_dob_match", True))
    # Block every person, but only keep pairs where at least one side has no usable
    # identifier (a pending/declined or missing APAAR). Comparing only missing-ID people
    # to each other would never find a missing-ID row against a clean record.
    persons = list(db.scalars(select(Person)))
    blocks: dict[tuple, list[Person]] = {}
    for person in persons:
        blocks.setdefault((person.dob.isoformat(), person.name_norm[:3]), []).append(person)

    # Enrolments already covered by an exact-identifier match must not be reported
    # again by the fuzzy layer; that would double-count the same underlying duplicate.
    exact_covered: set[int] = set()
    for link in db.scalars(select(DuplicateLink).where(DuplicateLink.match_type == "exact_apaar")):
        exact_covered.update({link.enrolment_a, link.enrolment_b})

    links = 0
    findings = 0
    for group in blocks.values():
        if len(group) < 2:
            continue
        for a, b in itertools.combinations(group, 2):
            if a.id == b.id:
                continue
            a_missing = not a.apaar_hmac or a.apaar_status in {"pending", "declined"}
            b_missing = not b.apaar_hmac or b.apaar_status in {"pending", "declined"}
            if not (a_missing or b_missing):
                continue
            if require_dob and a.dob != b.dob:
                continue
            score = float(fuzz.token_sort_ratio(a.name_norm, b.name_norm))
            if score < threshold:
                continue
            enrolments_a = list(db.scalars(select(Enrolment).where(Enrolment.person_id == a.id)))
            enrolments_b = list(db.scalars(select(Enrolment).where(Enrolment.person_id == b.id)))
            for ea in enrolments_a:
                for eb in enrolments_b:
                    if ea.institution_id == eb.institution_id:
                        continue
                    if ea.id in exact_covered or eb.id in exact_covered:
                        continue
                    if _link_exists(db, ea.id, eb.id):
                        continue
                    side_a = _side(db, ea, a)
                    side_b = _side(db, eb, b)
                    link = DuplicateLink(
                        enrolment_a=ea.id,
                        enrolment_b=eb.id,
                        match_type="fuzzy",
                        score=round(score, 1),
                        evidence_json=json.dumps(
                            {"a": side_a, "b": side_b, "name_score": round(score, 1)}, default=str
                        ),
                        whitelisted_reason=_whitelist_reason(ea, eb, rules),
                    )
                    db.add(link)
                    db.flush()
                    links += 1
                    if link.whitelisted_reason is None:
                        institution = db.get(Institution, ea.institution_id)
                        if institution:
                            _raise_cross_finding(db, link, institution, side_a, side_b)
                            findings += 1
    db.flush()
    return {"links": links, "findings": findings}


def duplicate_payload(db: Session, link: DuplicateLink) -> dict:
    evidence = json.loads(link.evidence_json or "{}")
    return {
        "id": link.id,
        "match_type": link.match_type,
        "score": link.score,
        "whitelisted_reason": link.whitelisted_reason,
        "a": evidence.get("a"),
        "b": evidence.get("b"),
        "created_at": link.created_at.isoformat(),
    }
