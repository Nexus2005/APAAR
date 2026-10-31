from __future__ import annotations

import csv
import io

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import institution_for_user, require_roles
from app.core.db import get_db
from app.models import AnomalyScore, Enrolment, Finding, Institution, Person, Programme, User
from app.schemas import CopilotQuery
from app.services.anomaly import anomaly_payload
from app.services.copilot import run_copilot
from app.services.dashboard import central_dashboard, institution_dashboard, safe_csv_value

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard/institution")
def get_institution_dashboard(
    institution_id: int | None = None,
    user: User = Depends(require_roles("institution_operator", "institution_admin", "central_reviewer", "sysadmin")),
    db: Session = Depends(get_db),
) -> dict:
    if user.role in {"institution_operator", "institution_admin"}:
        institution = institution_for_user(db, user)
    else:
        if institution_id is None:
            institution = db.scalars(select(Institution).order_by(Institution.id)).first()
        else:
            institution = db.get(Institution, institution_id)
        if institution is None:
            raise HTTPException(status_code=404, detail="Institution not found.")
    payload = institution_dashboard(db, institution)
    payload["simulated"] = True
    return payload


@router.get("/dashboard/central")
def get_central_dashboard(
    user: User = Depends(require_roles("central_reviewer", "sysadmin")),
    db: Session = Depends(get_db),
) -> dict:
    payload = central_dashboard(db)
    payload["simulated"] = True
    return payload


@router.get("/anomalies")
def get_anomalies(
    user: User = Depends(require_roles("central_reviewer", "sysadmin")),
    db: Session = Depends(get_db),
) -> dict:
    scores = list(db.scalars(select(AnomalyScore).order_by(AnomalyScore.rank)))
    score_institution_ids = [s.institution_id for s in scores] or [0]
    institutions = {
        i.id: i
        for i in db.scalars(select(Institution).where(Institution.id.in_(score_institution_ids)))
    }
    payload = [
        anomaly_payload(score, institutions[score.institution_id])
        for score in scores
        if score.institution_id in institutions
    ]
    return {"anomalies": payload, "simulated": True}


@router.get("/reports/enrolment.csv")
def enrolment_report(
    user: User = Depends(require_roles("central_reviewer", "sysadmin", "institution_admin")),
    db: Session = Depends(get_db),
) -> Response:
    query = select(Enrolment)
    if user.role == "institution_admin":
        query = query.where(Enrolment.institution_id == (user.institution_id or -1))
    rows = list(db.scalars(query.limit(20000)))
    person_ids = {r.person_id for r in rows}
    persons = {p.id: p for p in db.scalars(select(Person).where(Person.id.in_(person_ids or {0})))}
    programmes = {
        p.id: p
        for p in db.scalars(select(Programme).where(Programme.id.in_({r.programme_id for r in rows} or {0})))
    }
    institutions = {
        i.id: i
        for i in db.scalars(select(Institution).where(Institution.id.in_({r.institution_id for r in rows} or {0})))
    }
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        ["enrolment_ref", "institution_code", "programme_code", "academic_year", "seat_category",
         "admission_date", "status", "apaar_state", "synthetic"]
    )
    for row in rows:
        person = persons.get(row.person_id)
        programme = programmes.get(row.programme_id)
        institution = institutions.get(row.institution_id)
        writer.writerow(
            [
                safe_csv_value(row.enrolment_ref),
                safe_csv_value(institution.aicte_code if institution else ""),
                safe_csv_value(programme.code if programme else ""),
                safe_csv_value(row.academic_year),
                safe_csv_value(row.seat_category),
                safe_csv_value(row.admission_date.isoformat()),
                safe_csv_value(row.status),
                safe_csv_value(
                    "linked" if person and person.apaar_hmac else (person.apaar_status if person else "unknown")
                ),
                "SYNTHETIC",
            ]
        )
    return Response(
        content=buffer.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="enrolment-report.csv"'},
    )


@router.get("/reports/data-quality.csv")
def data_quality_report(
    user: User = Depends(require_roles("central_reviewer", "sysadmin")),
    db: Session = Depends(get_db),
) -> Response:
    findings = list(db.scalars(select(Finding)))
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["finding_ref", "rule_code", "severity", "status", "institution_id", "explanation", "synthetic"])
    for f in findings:
        writer.writerow(
            [
                safe_csv_value(f"FND-{f.id:05d}"),
                safe_csv_value(f.rule_code),
                safe_csv_value(f.severity),
                safe_csv_value(f.status),
                f.institution_id,
                safe_csv_value(f.explanation),
                "SYNTHETIC",
            ]
        )
    return Response(
        content=buffer.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="data-quality-report.csv"'},
    )


@router.post("/copilot/query")
def copilot_query(
    payload: CopilotQuery,
    user: User = Depends(require_roles("central_reviewer", "sysadmin")),
    db: Session = Depends(get_db),
) -> dict:
    return run_copilot(db, payload.question)
