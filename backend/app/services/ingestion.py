"""Upload preview and synchronous ingestion.

A failed row never fails the batch. Raw APAAR IDs are never returned or logged:
API responses use masked values and the DB stores HMAC + encrypted forms.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import load_rules
from app.core.crypto import (
    apaar_fingerprint,
    encrypt_identifier,
    hmac_value,
    mask_apaar,
    normalise_apaar,
)
from app.models import Enrolment, Institution, Person, Programme, RowResult, UploadBatch, User
from app.services.audit import append_audit
from app.services.mapping import (
    alias_config,
    mapping_is_complete,
    parse_date,
    parse_float,
    read_table,
    suggest_mapping,
)

REQUIRED = ["name", "dob", "programme", "seat_category", "admission_date"]
APAAR_FIELDS = {"apaar_id", "apaar_status"}


def _mask_sample(headers: list[str], rows: list[list], mapping: dict) -> list[dict]:
    apaar_col = (mapping.get("apaar_id") or {}).get("source_column")
    index = headers.index(apaar_col) if apaar_col in headers else -1
    out = []
    for row in rows[:10]:
        cells = []
        for i, cell in enumerate(row):
            value = "" if cell is None else str(cell)
            if i == index and value:
                value = mask_apaar(value)
            cells.append(value)
        out.append(cells)
    return out


def preview(filename: str, data: bytes) -> dict:
    headers, rows = read_table(filename, data)
    if not headers:
        raise ValueError("The file has no header row.")
    mapping = suggest_mapping(headers)
    unmapped = mapping.pop("_unmapped", [])
    required_meta = alias_config()
    return {
        "filename": filename,
        "headers": headers,
        "row_count": len(rows),
        "suggested_mapping": mapping,
        "unmapped_columns": unmapped,
        "fields": [
            {
                "key": key,
                "label": meta["label"],
                "required": bool(meta.get("required")),
            }
            for key, meta in required_meta.items()
        ],
        "sample_rows": _mask_sample(headers, rows, mapping),
        "simulated": True,
    }


def _extract(row: list, headers: list[str], mapping: dict) -> dict:
    idx = {h: i for i, h in enumerate(headers)}
    out: dict = {}
    for field, spec in mapping.items():
        if field.startswith("_") or not isinstance(spec, dict):
            continue
        column = spec.get("source_column")
        if column and column in idx:
            value = row[idx[column]] if idx[column] < len(row) else None
            out[field] = value
    return out


def _resolve_programme(
    programmes: list[Programme], value: object
) -> Programme | None:
    key = str(value or "").strip().lower()
    if not key:
        return None
    for prog in programmes:
        if prog.code.lower() == key:
            return prog
    for prog in programmes:
        if key in prog.name.lower() or prog.name.lower() in key:
            return prog
    from rapidfuzz import fuzz

    best = None
    best_score = 0.0
    for prog in programmes:
        score = fuzz.token_set_ratio(key, prog.name.lower())
        if score > best_score:
            best, best_score = prog, score
    return best if best_score >= 82 else None


def _temp_id(institution: Institution, batch_id: int, row_number: int) -> str:
    return f"TMP-{institution.aicte_code.split('-')[-1]}-{batch_id:03d}-{row_number:04d}"


def _row_errors(canonical: dict) -> tuple[list[dict], dict]:
    errors: list[dict] = []
    clean: dict = {}
    missing = [f for f in REQUIRED if not str(canonical.get(f, "") or "").strip()]
    if missing:
        errors.append(
            {
                "code": "REQUIRED_FIELD_MISSING",
                "fields": missing,
                "message": "Missing required value(s): " + ", ".join(missing),
            }
        )
    name = str(canonical.get("name") or "").strip()
    clean["name"] = name
    dob_raw = canonical.get("dob")
    dob = parse_date(dob_raw)
    if not dob and str(dob_raw or "").strip():
        errors.append(
            {"code": "REQUIRED_FIELD_MISSING", "fields": ["dob"], "message": "Date of birth could not be read."}
        )
    clean["dob"] = dob
    adm_raw = canonical.get("admission_date")
    admission = parse_date(adm_raw)
    if not admission and str(adm_raw or "").strip():
        errors.append(
            {
                "code": "REQUIRED_FIELD_MISSING",
                "fields": ["admission_date"],
                "message": "Admission date could not be read.",
            }
        )
    clean["admission_date"] = admission
    clean["programme"] = str(canonical.get("programme") or "").strip()
    clean["seat_category"] = str(canonical.get("seat_category") or "").strip().lower() or "regular"
    return errors, clean


def ingest(
    db: Session,
    *,
    user: User,
    institution: Institution,
    filename: str,
    data: bytes,
    mapping: dict,
    source: str = "csv",
) -> tuple[UploadBatch, bool]:
    rules = load_rules()
    complete, missing = mapping_is_complete(mapping)
    if not complete:
        raise ValueError("Column mapping is incomplete: " + ", ".join(missing))
    if len(data) > int(rules.get("uploads", {}).get("max_bytes", 5_242_880)):
        raise ValueError("File exceeds the 5 MB upload limit.")

    sha = hashlib.sha256(data).hexdigest()
    existing = db.scalars(
        select(UploadBatch).where(
            UploadBatch.institution_id == institution.id, UploadBatch.file_sha256 == sha
        )
    ).first()
    if existing:
        return existing, True

    headers, rows = read_table(filename, data)
    if not headers:
        raise ValueError("The file has no header row.")
    if len(rows) > int(rules.get("uploads", {}).get("max_rows", 20_000)):
        raise ValueError("File exceeds the 20,000 row limit.")

    batch = UploadBatch(
        batch_ref=f"UP-{date.today().strftime('%Y%m%d')}-{sha[:6].upper()}",
        institution_id=institution.id,
        filename=filename[:240],
        file_sha256=sha,
        uploaded_by=user.id,
        mapping_json=json.dumps(mapping),
        total_rows=len(rows),
    )
    db.add(batch)
    db.flush()

    programmes = list(
        db.scalars(select(Programme).where(Programme.institution_id == institution.id))
    )
    apaar_regex = re.compile(str(rules["apaar"]["format_regex"]))
    seen: dict[str, int] = {}
    accepted = rejected = 0
    duplicates: list[dict] = []

    for offset, raw in enumerate(rows):
        row_number = offset + 2
        canonical = _extract(raw, headers, mapping)
        errors, clean = _row_errors(canonical)

        programme = _resolve_programme(programmes, clean.get("programme"))
        if not programme:
            errors.append(
                {
                    "code": "PROGRAMME_NOT_FOUND",
                    "fields": ["programme"],
                    "message": f"No programme matches '{clean.get('programme')}'.",
                }
            )

        raw_apaar = normalise_apaar(str(canonical.get("apaar_id") or ""))
        status = str(canonical.get("apaar_status") or "").strip().lower()
        apaar_status = status if status in {"pending", "declined"} else "provided"
        fingerprint = None
        if raw_apaar:
            if not apaar_regex.match(raw_apaar):
                errors.append(
                    {
                        "code": "APAAR_FORMAT",
                        "fields": ["apaar_id"],
                        "message": "APAAR must match the configured format. This check does not prove authenticity.",
                    }
                )
            else:
                fingerprint = apaar_fingerprint(raw_apaar)

        masked_row = {
            "name": clean.get("name", ""),
            "dob": clean.get("dob").isoformat() if clean.get("dob") else "",
            "apaar": mask_apaar(raw_apaar) if raw_apaar else "(not provided)",
            "apaar_status": apaar_status,
            "programme": clean.get("programme", ""),
            "seat_category": clean.get("seat_category", ""),
            "admission_date": clean.get("admission_date").isoformat()
            if clean.get("admission_date")
            else "",
        }

        if errors:
            rejected += 1
            db.add(
                RowResult(
                    batch_id=batch.id,
                    row_number=row_number,
                    status="rejected",
                    error_codes=json.dumps([e["code"] for e in errors]),
                    error_detail=json.dumps(errors),
                    raw_masked_json=json.dumps(masked_row),
                )
            )
            continue

        assert programme and clean["dob"] and clean["admission_date"]

        duplicate_of = seen.get(fingerprint) if fingerprint else None
        if fingerprint:
            seen.setdefault(fingerprint, row_number)
        if duplicate_of:
            accepted += 1
            duplicates.append(
                {
                    "row_number": row_number,
                    "duplicate_of_row": duplicate_of,
                    "apaar_masked": mask_apaar(raw_apaar),
                }
            )
            db.add(
                RowResult(
                    batch_id=batch.id,
                    row_number=row_number,
                    status="accepted",
                    error_codes=json.dumps(["DUP_IN_FILE"]),
                    error_detail=json.dumps(
                        [
                            {
                                "code": "DUP_IN_FILE",
                                "message": f"Same APAAR as row {duplicate_of}; counted once.",
                            }
                        ]
                    ),
                    raw_masked_json=json.dumps(masked_row),
                )
            )
            continue

        person = None
        if fingerprint:
            person = db.scalars(select(Person).where(Person.apaar_hmac == fingerprint)).first()
        if person is None:
            person = Person(
                apaar_enc=encrypt_identifier(raw_apaar) if raw_apaar else None,
                apaar_hmac=fingerprint,
                temp_id=None
                if fingerprint
                else _temp_id(institution, batch.id, row_number),
                name_norm=" ".join(clean["name"].lower().split()),
                name_display=clean["name"],
                dob=clean["dob"],
                gender=str(canonical.get("gender") or "U").strip()[:16] or "U",
                phone_hmac=hmac_value(str(canonical.get("phone"))) if canonical.get("phone") else None,
                email_hmac=hmac_value(str(canonical.get("email"))) if canonical.get("email") else None,
                apaar_status=apaar_status,
                nationality=str(canonical.get("nationality") or "India").strip()[:32] or "India",
            )
            db.add(person)
            db.flush()
        else:
            if apaar_status in {"pending", "declined"}:
                person.apaar_status = apaar_status
            if not person.temp_id and not person.apaar_hmac:
                person.temp_id = _temp_id(institution, batch.id, row_number)

        enrolment = Enrolment(
            enrolment_ref=f"ENR-{rules.get('academic_year', '2026-27')[:4]}-{batch.id:04d}{row_number:04d}",
            person_id=person.id,
            institution_id=institution.id,
            programme_id=programme.id,
            academic_year=str(rules.get("academic_year", "2026-27")),
            seat_category=clean["seat_category"],
            admission_date=clean["admission_date"],
            admission_mode=str(canonical.get("admission_mode") or "counselling")[:24],
            status="admitted",
            batch_id=batch.id,
            source=source,
            nationality=person.nationality,
            qualifying_exam_pct=parse_float(canonical.get("qualifying_exam_pct")),
            remarks=str(canonical.get("remarks") or "")[:240],
        )
        db.add(enrolment)
        accepted += 1
        db.add(
            RowResult(
                batch_id=batch.id,
                row_number=row_number,
                status="accepted",
                error_codes=json.dumps(
                    ["APAAR_PENDING_LANE"]
                    if apaar_status in {"pending", "declined"}
                    else []
                ),
                error_detail=json.dumps([]),
                raw_masked_json=json.dumps(masked_row),
            )
        )

    batch.accepted_rows = accepted
    batch.rejected_rows = rejected
    batch.status = "completed"
    append_audit(
        db,
        action="upload.completed",
        resource=f"upload_batch:{batch.id}",
        actor=user,
        detail={
            "institution": institution.aicte_code,
            "filename": filename,
            "rows": len(rows),
            "accepted": accepted,
            "rejected": rejected,
            "file_sha256": sha,
        },
    )
    db.flush()
    return batch, False


def single_record(
    db: Session, user: User, institution: Institution, payload: dict
) -> Enrolment:
    """Create one enrolment from a form, reusing the same validation rules."""
    headers = list(alias_config().keys())
    mapping = {key: {"source_column": key} for key in headers}
    import csv
    import io

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(headers)
    writer.writerow([payload.get(key, "") for key in headers])
    batch, _ = ingest(
        db,
        user=user,
        institution=institution,
        filename="single-record-form.csv",
        data=buffer.getvalue().encode(),
        mapping=mapping,
        source="form",
    )
    if batch.rejected_rows:
        raise ValueError("The record did not pass validation. Download the error details.")
    row = db.scalars(
        select(Enrolment).where(Enrolment.batch_id == batch.id).order_by(Enrolment.id.desc())
    ).first()
    if row is None:
        raise ValueError("The record looked like a duplicate and was not stored twice.")
    return row
