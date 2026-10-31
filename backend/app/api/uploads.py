from __future__ import annotations

import csv
import io
import json
from datetime import timedelta

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import current_user, institution_for_user, require_roles
from app.core.db import get_db
from app.models import Enrolment, Finding, Institution, Programme, RowResult, UploadBatch, User
from app.services.anomaly import recompute
from app.services.dashboard import safe_csv_value
from app.services.duplicates import detect_exact, detect_fuzzy
from app.services.findings_engine import refresh_institution
from app.services.ingestion import ingest, preview

router = APIRouter(tags=["uploads"])


def batch_payload(batch: UploadBatch, findings_raised: int = 0) -> dict:
    return {
        "id": batch.id,
        "ref": batch.batch_ref,
        "filename": batch.filename,
        "status": batch.status,
        "uploaded_at": batch.uploaded_at.isoformat(),
        "total_rows": batch.total_rows,
        "accepted_rows": batch.accepted_rows,
        "rejected_rows": batch.rejected_rows,
        "findings_raised": findings_raised,
        "mapping": json.loads(batch.mapping_json or "{}"),
    }


@router.post("/uploads/preview")
async def upload_preview(
    file: UploadFile = File(...),
    user: User = Depends(require_roles("institution_operator", "institution_admin")),
    db: Session = Depends(get_db),
) -> dict:
    institution = institution_for_user(db, user)
    data = await file.read()
    try:
        payload = preview(file.filename or "upload.csv", data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    payload["institution"] = {"id": institution.id, "code": institution.aicte_code, "name": institution.name}
    payload["simulated"] = True
    return payload


@router.post("/uploads")
async def upload_commit(
    file: UploadFile = File(...),
    mapping: str = Form(...),
    user: User = Depends(require_roles("institution_operator", "institution_admin")),
    db: Session = Depends(get_db),
) -> dict:
    institution = institution_for_user(db, user)
    data = await file.read()
    try:
        mapping_payload = json.loads(mapping)
        batch, was_duplicate = ingest(
            db,
            user=user,
            institution=institution,
            filename=file.filename or "upload.csv",
            data=data,
            mapping=mapping_payload,
        )
    except (ValueError, KeyError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if not was_duplicate:
        refresh_institution(db, institution.id)
        detect_exact(db)
        detect_fuzzy(db)
        recompute(db)
    db.commit()

    findings_raised = db.scalars(
        select(func.count(Finding.id)).where(
            Finding.institution_id == institution.id,
            Finding.created_at >= batch.uploaded_at - timedelta(seconds=5),
        )
    ).one()
    return {
        "batch": batch_payload(batch, int(findings_raised)),
        "duplicate_upload": was_duplicate,
        "simulated": True,
    }


@router.get("/uploads")
def list_uploads(
    user: User = Depends(current_user), db: Session = Depends(get_db)
) -> dict:
    if user.institution_id is None:
        raise HTTPException(status_code=403, detail="Institution account required.")
    institution = institution_for_user(db, user)
    batches = list(
        db.scalars(
            select(UploadBatch)
            .where(UploadBatch.institution_id == institution.id)
            .order_by(UploadBatch.uploaded_at.desc())
        )
    )
    return {"uploads": [batch_payload(b) for b in batches]}


@router.get("/uploads/{batch_id}")
def get_upload(
    batch_id: int,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    batch = db.get(UploadBatch, batch_id)
    if batch is None:
        raise HTTPException(status_code=404, detail="Upload not found.")
    if user.role in {"institution_operator", "institution_admin"} and batch.institution_id != user.institution_id:
        raise HTTPException(status_code=403, detail="You can only read your own uploads.")
    rows = list(
        db.scalars(
            select(RowResult)
            .where(RowResult.batch_id == batch.id)
            .order_by(RowResult.row_number)
            .limit(500)
        )
    )
    findings = db.scalars(
        select(func.count(Finding.id)).where(
            Finding.institution_id == batch.institution_id,
            Finding.created_at >= batch.uploaded_at - timedelta(seconds=5),
        )
    ).one()
    return {
        "batch": batch_payload(batch, int(findings)),
        "rows": [
            {
                "row_number": row.row_number,
                "status": row.status,
                "codes": json.loads(row.error_codes or "[]"),
                "errors": json.loads(row.error_detail or "[]"),
                "row": json.loads(row.raw_masked_json or "{}"),
            }
            for row in rows
        ],
        "simulated": True,
    }


@router.get("/uploads/{batch_id}/errors.csv")
def download_errors(
    batch_id: int,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> Response:
    batch = db.get(UploadBatch, batch_id)
    if batch is None:
        raise HTTPException(status_code=404, detail="Upload not found.")
    if user.role in {"institution_operator", "institution_admin"} and batch.institution_id != user.institution_id:
        raise HTTPException(status_code=403, detail="You can only read your own uploads.")
    rows = list(
        db.scalars(
            select(RowResult)
            .where(RowResult.batch_id == batch.id, RowResult.status == "rejected")
            .order_by(RowResult.row_number)
        )
    )
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["row_number", "error_codes", "details", "masked_row"])
    for row in rows:
        writer.writerow(
            [
                row.row_number,
                safe_csv_value("; ".join(json.loads(row.error_codes or "[]"))),
                safe_csv_value(row.error_detail),
                safe_csv_value(row.raw_masked_json),
            ]
        )
    return Response(
        content=buffer.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{batch.batch_ref}-errors.csv"'},
    )


@router.get("/enrolments")
def list_enrolments(
    institution_id: int | None = None,
    search: str | None = None,
    limit: int = 100,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    from app.core.crypto import decrypt_identifier, mask_apaar
    from app.models import Person

    query = select(Enrolment).order_by(Enrolment.id.desc()).limit(min(limit, 500))
    if user.role in {"institution_operator", "institution_admin"}:
        query = query.where(Enrolment.institution_id == (user.institution_id or -1))
    elif user.role == "verifier":
        raise HTTPException(status_code=403, detail="Verifiers cannot browse enrolments.")
    elif institution_id:
        query = query.where(Enrolment.institution_id == institution_id)

    rows = list(db.scalars(query))
    person_ids = {r.person_id for r in rows}
    persons = {
        p.id: p for p in db.scalars(select(Person).where(Person.id.in_(person_ids or {0})))
    }
    programme_ids = {r.programme_id for r in rows}
    programmes = {
        p.id: p for p in db.scalars(select(Programme).where(Programme.id.in_(programme_ids or {0})))
    }
    institution_ids = {r.institution_id for r in rows}
    institutions = {
        i.id: i for i in db.scalars(select(Institution).where(Institution.id.in_(institution_ids or {0})))
    }
    if search:
        needle = search.lower()
        rows = [
            r
            for r in rows
            if needle in (persons.get(r.person_id).name_display.lower() if persons.get(r.person_id) else "")
            or needle in r.enrolment_ref.lower()
        ]
    payload = []
    for row in rows:
        person = persons.get(row.person_id)
        programme = programmes.get(row.programme_id)
        institution = institutions.get(row.institution_id)
        payload.append(
            {
                "id": row.id,
                "enrolment_ref": row.enrolment_ref,
                "student": person.name_display if person else "—",
                "apaar_masked": (
                    mask_apaar(decrypt_identifier(person.apaar_enc))
                    if person and person.apaar_hmac
                    else (person.temp_id if person else "—")
                ),
                "apaar_status": person.apaar_status if person else "unknown",
                "programme": programme.name if programme else "—",
                "programme_code": programme.code if programme else "—",
                "institution": institution.short_name if institution else "—",
                "institution_code": institution.aicte_code if institution else "—",
                "academic_year": row.academic_year,
                "seat_category": row.seat_category,
                "admission_date": row.admission_date.isoformat(),
                "status": row.status,
            }
        )
    return {"enrolments": payload, "count": len(payload), "simulated": True}
