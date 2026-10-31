"""Explainable anomaly scoring. It only prioritises institutions for human review."""

from __future__ import annotations

import json
from collections import Counter
from datetime import date, timedelta

import numpy as np
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.config import load_rules
from app.models import (
    AnomalyScore,
    Enrolment,
    Finding,
    FindingEvent,
    Institution,
    IntakeApproval,
    Person,
    Programme,
)


def _features(db: Session, institutions: list[Institution], rules: dict) -> dict[int, dict]:
    window_end = date.fromisoformat(str(rules["admission_window"]["end"]))
    week_start = window_end - timedelta(days=6)
    data: dict[int, dict] = {}
    for institution in institutions:
        enrolments = list(
            db.scalars(
                select(Enrolment).where(
                    Enrolment.institution_id == institution.id,
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
        phone_counts: Counter = Counter(
            p.phone_hmac for p in persons.values() if p.phone_hmac
        )
        shared_students = sum(
            1 for p in persons.values() if p.phone_hmac and phone_counts[p.phone_hmac] > 3
        )
        shared_groups = sum(1 for count in phone_counts.values() if count > 3)
        total = len(enrolments)
        last_week = sum(1 for e in enrolments if e.admission_date >= week_start)
        special = sum(1 for e in enrolments if e.seat_category != "regular")
        missing = sum(
            1 for e in enrolments if (persons.get(e.person_id) and not persons[e.person_id].apaar_hmac)
        )
        programme_ids = {
            p.id for p in db.scalars(select(Programme).where(Programme.institution_id == institution.id))
        }
        approved = sum(
            a.approved_intake
            for a in db.scalars(select(IntakeApproval).where(IntakeApproval.programme_id.in_(programme_ids or {0})))
        )
        regular = sum(1 for e in enrolments if e.seat_category == "regular")
        data[institution.id] = {
            "total_admissions": total,
            "last_week_share_pct": round(last_week / total * 100, 1) if total else 0.0,
            "intake_utilisation_pct": round(regular / approved * 100, 1) if approved else 0.0,
            "special_category_share_pct": round(special / total * 100, 1) if total else 0.0,
            "shared_phone_students": shared_students,
            "shared_phone_groups": shared_groups,
            "missing_apaar_share_pct": round(missing / total * 100, 1) if total else 0.0,
            "approved_intake": approved,
            "regular_admitted": regular,
        }
    return data


def _reason_candidates(features: dict, peers: dict) -> list[tuple[float, str]]:
    def pct(key: str) -> float:
        return float(features.get(key, 0))

    def med(key: str) -> float:
        return float(peers.get(key, 0))

    templates = [
        (
            "last_week_share_pct",
            lambda v, p: (
                f"{v}% of admissions were dated in the final week of the window; "
                f"peer median {p}%."
            ),
        ),
        (
            "intake_utilisation_pct",
            lambda v, p: (
                f"Regular admissions use {v}% of approved intake; peer median {p}%."
            ),
        ),
        (
            "special_category_share_pct",
            lambda v, p: (
                f"{v}% of admissions use NRI/FN/OCI/supernumerary seats; peer median {p}%."
            ),
        ),
        (
            "shared_phone_students",
            lambda v, p: (
                f"{v} students share a phone number with more than three others; "
                f"peer median {p}."
            ),
        ),
        (
            "missing_apaar_share_pct",
            lambda v, p: (
                f"{v}% of admitted students have no APAAR; peer median {p}%."
            ),
        ),
    ]
    scored = []
    for key, template in templates:
        value = pct(key)
        median = med(key)
        deviation = abs(value - median) / (abs(median) + 5)
        if value == 0 and median == 0:
            deviation = 0.0
        scored.append((deviation, template(value, median)))
    scored.sort(key=lambda item: item[0], reverse=True)
    return scored


def recompute(db: Session) -> dict:
    rules = load_rules()
    institutions = list(db.scalars(select(Institution).where(Institution.status == "active")))
    if not institutions:
        return {"institutions": 0, "flagged": 0}
    features = _features(db, institutions, rules)
    keys = [
        "last_week_share_pct",
        "intake_utilisation_pct",
        "special_category_share_pct",
        "shared_phone_students",
        "missing_apaar_share_pct",
    ]
    peer_medians = {
        key: round(float(np.median([features[i.id][key] for i in institutions])), 1)
        for key in keys
    }
    matrix = np.array([[features[i.id][key] for key in keys] for i in institutions], dtype=float)

    if len(institutions) >= int(rules.get("anomaly", {}).get("min_institutions", 8)):
        from sklearn.ensemble import IsolationForest

        model = IsolationForest(
            random_state=42,
            contamination=float(rules.get("anomaly", {}).get("contamination", 0.1)),
        )
        model.fit(matrix)
        decision = model.decision_function(matrix)
        predictions = model.predict(matrix)
        method = "isolation_forest"
    else:
        # Deterministic fallback: robust z-score across peers.
        med = np.median(matrix, axis=0)
        mad = np.median(np.abs(matrix - med), axis=0) + 1e-6
        z = np.abs((matrix - med) / mad).mean(axis=1)
        decision = -z
        predictions = np.where(z > 2.5, -1, 1)
        method = "robust_zscore"

    order = np.argsort(decision)  # most anomalous first
    rank_by_index = {int(idx): rank + 1 for rank, idx in enumerate(order)}
    ordered_scores = [-float(decision[idx]) for idx in order]
    low, high = min(ordered_scores), max(ordered_scores)
    db.execute(
        delete(AnomalyScore).where(AnomalyScore.academic_year == str(rules.get("academic_year")))
    )
    flagged_ids: list[int] = []
    for position, institution in enumerate(institutions):
        feature = features[institution.id]
        score_raw = -float(decision[position])
        score = 100.0 if high == low else round((score_raw - low) / (high - low) * 100, 1)
        candidates = _reason_candidates(feature, peer_medians)
        reasons = [text for deviation, text in candidates if deviation > 0][:3]
        if not reasons:
            reasons = [text for _dev, text in candidates][:2]
        strong_signal = (
            feature["last_week_share_pct"] >= 30
            or feature["shared_phone_students"] >= 3
            or feature["special_category_share_pct"] >= 25
        )
        flagged = bool(predictions[position] == -1) or strong_signal
        payload = {
            "features": feature,
            "peer_medians": peer_medians,
            "method": method,
            "reasons": reasons[:3],
        }
        db.add(
            AnomalyScore(
                institution_id=institution.id,
                academic_year=str(rules.get("academic_year")),
                score=score,
                rank=rank_by_index[position],
                flagged=flagged,
                features_json=json.dumps(payload, sort_keys=True),
                reasons_json=json.dumps(reasons[:3]),
            )
        )
        if flagged:
            flagged_ids.append(institution.id)
            _upsert_finding(db, institution, feature, peer_medians, reasons[:3], score, rank_by_index[position])
        else:
            _clear_finding(db, institution.id)

    db.flush()
    return {"institutions": len(institutions), "flagged": len(flagged_ids), "method": method}


def _upsert_finding(
    db: Session,
    institution: Institution,
    feature: dict,
    peer_medians: dict,
    reasons: list[str],
    score: float,
    rank: int,
) -> None:
    key = f"institution:{institution.id}:year:2026-27"
    existing = db.scalars(
        select(Finding).where(
            Finding.rule_code == "ANOMALY_INSTITUTION", Finding.subject_key == key
        )
    ).first()
    evidence = {
        "institution_code": institution.aicte_code,
        "institution_name": institution.name,
        "priority_score": score,
        "rank": rank,
        "features": feature,
        "peer_medians": peer_medians,
        "reasons": reasons,
        "ranking_method": "IsolationForest — prioritisation only, not a finding of fraud",
    }
    explanation = (
        "Ranked for review because " + " ".join(reasons)
        + " This score prioritises human review; it does not accuse the institution."
    )
    if existing:
        existing.subject_json = json.dumps(evidence, default=str)
        existing.explanation = explanation
        return
    finding = Finding(
        rule_code="ANOMALY_INSTITUTION",
        severity="risk",
        institution_id=institution.id,
        subject_key=key,
        subject_json=json.dumps(evidence, default=str),
        explanation=explanation,
        recommended_action=(
            "Read the reasons, compare with peer institutions, and ask for a human "
            "explanation before any action."
        ),
        policy_assumption="IsolationForest contamination and feature definitions are prototype assumptions.",
        status="open",
    )
    db.add(finding)
    db.flush()
    db.add(
        FindingEvent(
            finding_id=finding.id,
            action="created",
            comment="Ranked by the anomaly scorer for human review. Never an automatic penalty.",
            actor_name="anomaly-engine",
        )
    )


def _clear_finding(db: Session, institution_id: int) -> None:
    finding = db.scalars(
        select(Finding).where(
            Finding.rule_code == "ANOMALY_INSTITUTION",
            Finding.institution_id == institution_id,
            Finding.status.in_(["open", "in_review"]),
        )
    ).first()
    if finding:
        finding.status = "resolved"
        db.add(
            FindingEvent(
                finding_id=finding.id,
                action="auto_resolved",
                comment="Auto-resolved: the institution is no longer ranked for review.",
                actor_name="anomaly-engine",
            )
        )


def anomaly_payload(score_row: AnomalyScore, institution: Institution) -> dict:
    evidence = json.loads(score_row.features_json or "{}")
    return {
        "institution_id": institution.id,
        "institution_code": institution.aicte_code,
        "institution_name": institution.name,
        "state": institution.state,
        "score": score_row.score,
        "rank": score_row.rank,
        "flagged": score_row.flagged,
        "features": evidence.get("features", {}),
        "peer_medians": evidence.get("peer_medians", {}),
        "reasons": json.loads(score_row.reasons_json or "[]"),
        "method": evidence.get("method", "isolation_forest"),
    }
