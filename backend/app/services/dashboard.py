from __future__ import annotations

from collections import defaultdict
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import load_rules
from app.models import (
    AnomalyScore,
    Enrolment,
    Finding,
    Institution,
    IntakeApproval,
    Person,
    Programme,
    RowResult,
    UploadBatch,
)
from app.services.anomaly import anomaly_payload
from app.services.findings_engine import finding_payload


def _intake_table(db: Session, institution_id: int) -> list[dict]:
    rules = load_rules()
    seat_categories = rules["intake"]["seat_categories"]
    programmes = list(
        db.scalars(select(Programme).where(Programme.institution_id == institution_id))
    )
    approvals = {
        (a.programme_id, a.academic_year): a
        for a in db.scalars(
            select(IntakeApproval).join(Programme).where(Programme.institution_id == institution_id)
        )
    }
    enrolments = list(
        db.scalars(
            select(Enrolment).where(
                Enrolment.institution_id == institution_id, Enrolment.status != "withdrawn"
            )
        )
    )
    counts: dict[tuple[int, str, str], int] = defaultdict(int)
    for e in enrolments:
        counts[(e.programme_id, e.academic_year, e.seat_category)] += 1

    rows = []
    for programme in programmes:
        for year in sorted({e.academic_year for e in enrolments if e.programme_id == programme.id}) or [
            rules.get("academic_year", "2026-27")
        ]:
            approval = approvals.get((programme.id, year))
            approved = approval.approved_intake if approval else 0
            regular = counts.get((programme.id, year, "regular"), 0)
            categories = {
                category: counts.get((programme.id, year, category), 0)
                for category in seat_categories
                if category != "regular"
            }
            headroom = approved - regular
            utilisation = round(regular / approved * 100, 1) if approved else 0.0
            if approved == 0:
                status = "unconfigured"
            elif regular > approved:
                status = "red"
            elif utilisation >= 90:
                status = "amber"
            else:
                status = "green"
            rows.append(
                {
                    "programme_id": programme.id,
                    "programme_code": programme.code,
                    "programme_name": programme.name,
                    "level": programme.level,
                    "academic_year": year,
                    "approved_intake": approved,
                    "regular_admitted": regular,
                    "seat_categories": categories,
                    "headroom": headroom,
                    "utilisation_pct": utilisation,
                    "status": status,
                }
            )
    return rows


def institution_dashboard(db: Session, institution: Institution) -> dict:
    rules = load_rules()
    enrolments = list(
        db.scalars(
            select(Enrolment).where(
                Enrolment.institution_id == institution.id, Enrolment.status != "withdrawn"
            )
        )
    )
    person_ids = {e.person_id for e in enrolments}
    persons = {
        p.id: p
        for p in db.scalars(select(Person).where(Person.id.in_(person_ids or {0})))
    }
    linked = sum(1 for e in enrolments if persons.get(e.person_id) and persons[e.person_id].apaar_hmac)
    pending = sum(
        1
        for e in enrolments
        if persons.get(e.person_id)
        and persons[e.person_id].apaar_status in {"pending", "declined"}
    )
    missing = sum(1 for e in enrolments if persons.get(e.person_id) and not persons[e.person_id].apaar_hmac)
    total = len(enrolments)

    findings = list(
        db.scalars(select(Finding).where(Finding.institution_id == institution.id))
    )
    open_findings = [f for f in findings if f.status in {"open", "in_review"}]
    severity_counts = defaultdict(int)
    for f in open_findings:
        severity_counts[f.severity] += 1

    intake = _intake_table(db, institution.id)
    seats_left = sum(row["headroom"] for row in intake)
    approved_total = sum(row["approved_intake"] for row in intake)
    admitted_regular = sum(row["regular_admitted"] for row in intake)

    uploads = list(
        db.scalars(
            select(UploadBatch)
            .where(UploadBatch.institution_id == institution.id)
            .order_by(UploadBatch.uploaded_at.desc())
            .limit(6)
        )
    )
    upload_rows = []
    for batch in uploads:
        pending_lane = db.scalars(
            select(func.count(RowResult.id)).where(
                RowResult.batch_id == batch.id,
                RowResult.error_codes.like("%APAAR_PENDING_LANE%"),
            )
        ).one()
        upload_rows.append(
            {
                "id": batch.id,
                "ref": batch.batch_ref,
                "filename": batch.filename,
                "uploaded_at": batch.uploaded_at.isoformat(),
                "total_rows": batch.total_rows,
                "accepted_rows": batch.accepted_rows,
                "rejected_rows": batch.rejected_rows,
                "pending_lane_rows": int(pending_lane),
                "status": batch.status,
            }
        )

    # admissions trend by month for the chart
    monthly: dict[str, int] = defaultdict(int)
    for e in enrolments:
        monthly[e.admission_date.strftime("%Y-%m")] += 1

    readiness = round(linked / total * 100, 1) if total else 0.0
    return {
        "institution": {
            "id": institution.id,
            "aicte_code": institution.aicte_code,
            "name": institution.name,
            "short_name": institution.short_name,
            "state": institution.state,
            "region": institution.region,
            "city": institution.city,
        },
        "kpis": {
            "total_admitted": total,
            "open_findings": len(open_findings),
            "severity_counts": dict(severity_counts),
            "apaar_readiness_pct": readiness,
            "apaar_linked": linked,
            "apaar_pending_declined": pending,
            "apaar_missing": missing,
            "seats_left": seats_left,
            "approved_intake": approved_total,
            "regular_admitted": admitted_regular,
            "utilisation_pct": round(admitted_regular / approved_total * 100, 1) if approved_total else 0.0,
        },
        "intake": intake,
        "uploads": upload_rows,
        "findings": [
            finding_payload(f, institution)
            for f in sorted(open_findings, key=lambda f: (f.severity, -f.id))[:6]
        ],
        "trend": [{"month": month, "admitted": count} for month, count in sorted(monthly.items())],
        "assumptions": {
            "policy_version": rules.get("version"),
            "seat_caps": {
                key: {
                    "cap_pct_of_approved": meta.get("cap_pct_of_approved"),
                    "status": meta.get("status"),
                }
                for key, meta in rules["intake"]["seat_categories"].items()
            },
        },
    }


def central_dashboard(db: Session) -> dict:
    rules = load_rules()
    institutions = list(db.scalars(select(Institution).where(Institution.status == "active")))
    enrolments = list(db.scalars(select(Enrolment).where(Enrolment.status != "withdrawn")))
    findings = list(db.scalars(select(Finding)))
    open_risk = [f for f in findings if f.status in {"open", "in_review"} and f.severity in {"risk", "blocker"}]

    per_institution: dict[int, dict] = {
        i.id: {
            "institution_id": i.id,
            "code": i.aicte_code,
            "name": i.name,
            "short_name": i.short_name,
            "state": i.state,
            "region": i.region,
            "enrolments": 0,
            "open_findings": 0,
            "risk_findings": 0,
        }
        for i in institutions
    }
    for e in enrolments:
        if e.institution_id in per_institution:
            per_institution[e.institution_id]["enrolments"] += 1
    for f in findings:
        if f.status in {"open", "in_review"} and f.institution_id in per_institution:
            per_institution[f.institution_id]["open_findings"] += 1
            if f.severity in {"risk", "blocker"}:
                per_institution[f.institution_id]["risk_findings"] += 1

    intake_by_inst: dict[int, list[dict]] = {}
    over_intake = []
    for institution in institutions:
        rows = _intake_table(db, institution.id)
        intake_by_inst[institution.id] = rows
        per_institution[institution.id]["approved_intake"] = sum(r["approved_intake"] for r in rows)
        per_institution[institution.id]["regular_admitted"] = sum(r["regular_admitted"] for r in rows)
        per_institution[institution.id]["utilisation_pct"] = (
            round(
                per_institution[institution.id]["regular_admitted"]
                / per_institution[institution.id]["approved_intake"]
                * 100,
                1,
            )
            if per_institution[institution.id]["approved_intake"]
            else 0.0
        )
        for row in rows:
            is_over = row["regular_admitted"] > row["approved_intake"]
            if is_over and row["approved_intake"]:
                over_intake.append(
                    {
                        **row,
                        "institution_code": institution.aicte_code,
                        "institution_name": institution.name,
                        "state": institution.state,
                    }
                )

    # readiness + anomaly join
    scores = list(
        db.scalars(select(AnomalyScore).where(AnomalyScore.academic_year == rules.get("academic_year")))
    )
    score_by_inst = {s.institution_id: s for s in scores}
    person_linked: dict[int, int] = defaultdict(int)
    person_total: dict[int, int] = defaultdict(int)
    for e in enrolments:
        person_total[e.institution_id] += 1
    persons = {
        p.id: p
        for p in db.scalars(
            select(Person).where(Person.id.in_([e.person_id for e in enrolments] or [0]))
        )
    }
    for e in enrolments:
        if persons.get(e.person_id) and persons[e.person_id].apaar_hmac:
            person_linked[e.institution_id] += 1

    rows = []
    for institution in institutions:
        info = per_institution[institution.id]
        score = score_by_inst.get(institution.id)
        rows.append(
            {
                **info,
                "readiness_pct": round(
                    person_linked[institution.id] / person_total[institution.id] * 100, 1
                )
                if person_total[institution.id]
                else 0.0,
                "anomaly_score": score.score if score else None,
                "anomaly_rank": score.rank if score else None,
                "anomaly_flagged": bool(score.flagged) if score else False,
            }
        )
    rows.sort(key=lambda r: (r["risk_findings"], r["anomaly_score"] or 0), reverse=True)

    anomalies = []
    for score in sorted(scores, key=lambda s: s.rank):
        institution = next((i for i in institutions if i.id == score.institution_id), None)
        if institution:
            anomalies.append(anomaly_payload(score, institution))

    by_state: dict[str, dict] = defaultdict(
        lambda: {
            "institutions": 0,
            "enrolments": 0,
            "approved_intake": 0,
            "regular_admitted": 0,
        }
    )
    for row in rows:
        state = by_state[row["state"]]
        state["institutions"] += 1
        state["enrolments"] += row["enrolments"]
        state["approved_intake"] += row.get("approved_intake", 0)
        state["regular_admitted"] += row.get("regular_admitted", 0)
    state_rows = []
    for state, values in sorted(by_state.items()):
        state_rows.append(
            {
                "state": state,
                **values,
                "utilisation_pct": round(
                    values["regular_admitted"] / values["approved_intake"] * 100, 1
                )
                if values["approved_intake"]
                else 0.0,
            }
        )

    escalated = [f for f in findings if f.status == "escalated"]
    return {
        "kpis": {
            "institutions": len(institutions),
            "enrolments": len(enrolments),
            "programmes_over_intake": len(over_intake),
            "open_risk_findings": len(open_risk),
            "escalated": len(escalated),
            "anomalies_flagged": sum(1 for s in scores if s.flagged),
        },
        "states": state_rows,
        "institutions": rows,
        "over_intake": over_intake,
        "anomalies": anomalies[:6],
        "escalations": [finding_payload(f) for f in escalated[:6]],
        "policy": {
            "version": rules.get("version"),
            "effective_from": str(rules.get("effective_from")),
            "seat_caps": rules["intake"]["seat_categories"],
        },
    }


def institution_trend(db: Session) -> list[dict]:
    rows = db.execute(
        select(Institution.state, func.count(Enrolment.id))
        .join(Enrolment, Enrolment.institution_id == Institution.id)
        .group_by(Institution.state)
    ).all()
    return [{"state": state, "enrolments": int(count)} for state, count in rows]


def safe_csv_value(value) -> str:
    """Neutralise spreadsheet formula injection on export."""
    if isinstance(value, Decimal):
        value = float(value)
    text = "" if value is None else str(value)
    if text[:1] in {"=", "+", "-", "@"}:
        return "'" + text
    return text
