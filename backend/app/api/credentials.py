from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import current_user, ensure_institution_access, institution_for_user, require_roles
from app.core.crypto import decrypt_identifier, mask_apaar
from app.core.db import get_db
from app.models import Credential, Enrolment, Institution, Person, Programme, User
from app.schemas import IssueCredentialRequest, RevokeCredentialRequest
from app.services.audit import append_audit
from app.services.credentials import issue_credential, qr_png, qr_svg, revoke_credential, verify_credential

router = APIRouter(tags=["credentials"])


def _credential_row(db: Session, credential: Credential) -> dict:
    enrolment = db.get(Enrolment, credential.enrolment_id)
    person = db.get(Person, enrolment.person_id) if enrolment else None
    institution = db.get(Institution, credential.issuer_institution_id)
    return {
        "credential_id": credential.credential_id,
        "enrolment_ref": enrolment.enrolment_ref if enrolment else None,
        "student": person.name_display if person else None,
        "apaar_masked": mask_apaar(decrypt_identifier(person.apaar_enc)) if person and person.apaar_hmac else None,
        "status": credential.status,
        "issued_at": credential.issued_at.isoformat(),
        "revoked_at": credential.revoked_at.isoformat() if credential.revoked_at else None,
        "revoke_reason": credential.revoke_reason,
        "institution": institution.short_name if institution else None,
        "verify_path": f"/verify/{credential.credential_id}",
    }


@router.get("/credentials")
def list_credentials(
    user: User = Depends(current_user), db: Session = Depends(get_db)
) -> dict:
    if user.role == "verifier":
        raise HTTPException(status_code=403, detail="Verifiers use consent, not the credential list.")
    query = select(Credential).order_by(Credential.id.desc())
    if user.role in {"institution_operator", "institution_admin"}:
        query = query.where(Credential.issuer_institution_id == (user.institution_id or -1))
    credentials = list(db.scalars(query))
    return {
        "credentials": [_credential_row(db, c) for c in credentials],
        "simulated": True,
    }


@router.get("/credentials/issuable")
def issuable_enrolments(
    user: User = Depends(require_roles("institution_admin")),
    db: Session = Depends(get_db),
) -> dict:
    institution = institution_for_user(db, user)
    existing = {
        c.enrolment_id for c in db.scalars(select(Credential).where(Credential.issuer_institution_id == institution.id))
    }
    rows = list(
        db.scalars(
            select(Enrolment).where(
                Enrolment.institution_id == institution.id,
                Enrolment.status.in_(["admitted", "verified"]),
            )
        )
    )
    persons = {p.id: p for p in db.scalars(select(Person).where(Person.id.in_({r.person_id for r in rows} or {0})))}
    programmes = {
        p.id: p for p in db.scalars(select(Programme).where(Programme.id.in_({r.programme_id for r in rows} or {0})))
    }
    return {
        "enrolments": [
            {
                "id": row.id,
                "enrolment_ref": row.enrolment_ref,
                "student": persons[row.person_id].name_display if row.person_id in persons else "—",
                "programme": programmes[row.programme_id].name if row.programme_id in programmes else "—",
                "academic_year": row.academic_year,
                "status": row.status,
                "has_credential": row.id in existing,
            }
            for row in rows[:200]
        ],
        "simulated": True,
    }


@router.post("/credentials/issue")
def issue(
    payload: IssueCredentialRequest,
    user: User = Depends(require_roles("institution_admin")),
    db: Session = Depends(get_db),
) -> dict:
    enrolment = db.get(Enrolment, payload.enrolment_id)
    if enrolment is None:
        raise HTTPException(status_code=404, detail="Enrolment not found.")
    ensure_institution_access(user, enrolment.institution_id)
    institution = db.get(Institution, enrolment.institution_id)
    if institution is None:
        raise HTTPException(status_code=404, detail="Institution not found.")
    existing = db.scalars(
        select(Credential).where(
            Credential.enrolment_id == enrolment.id, Credential.status == "valid"
        )
    ).first()
    if existing:
        return {"credential": _credential_row(db, existing), "already_issued": True}
    credential = issue_credential(db, enrolment, institution)
    append_audit(
        db,
        action="credential.issued",
        resource=f"credential:{credential.credential_id}",
        actor=user,
        detail={"enrolment_ref": enrolment.enrolment_ref, "simulated": True},
    )
    db.commit()
    return {"credential": _credential_row(db, credential), "already_issued": False, "simulated": True}


@router.post("/credentials/{credential_id}/revoke")
def revoke(
    credential_id: str,
    payload: RevokeCredentialRequest,
    user: User = Depends(require_roles("institution_admin", "sysadmin")),
    db: Session = Depends(get_db),
) -> dict:
    credential = db.scalars(select(Credential).where(Credential.credential_id == credential_id)).first()
    if credential is None:
        raise HTTPException(status_code=404, detail="Credential not found.")
    if user.role != "sysadmin":
        ensure_institution_access(user, credential.issuer_institution_id)
    try:
        revoke_credential(db, credential_id, payload.reason)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    append_audit(
        db,
        action="credential.revoked",
        resource=f"credential:{credential_id}",
        actor=user,
        detail={"reason": payload.reason, "simulated": True},
    )
    db.commit()
    return {"credential": _credential_row(db, credential), "simulated": True}


@router.get("/credentials/{credential_id}/qr.png")
def credential_qr_png(
    credential_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)
) -> Response:
    credential = db.scalars(select(Credential).where(Credential.credential_id == credential_id)).first()
    if credential is None:
        raise HTTPException(status_code=404, detail="Credential not found.")
    if user.role in {"institution_operator", "institution_admin"}:
        ensure_institution_access(user, credential.issuer_institution_id)
    return Response(content=qr_png(credential_id), media_type="image/png")


@router.get("/credentials/{credential_id}/qr.svg")
def credential_qr_svg(
    credential_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)
) -> Response:
    credential = db.scalars(select(Credential).where(Credential.credential_id == credential_id)).first()
    if credential is None:
        raise HTTPException(status_code=404, detail="Credential not found.")
    return Response(content=qr_svg(credential_id), media_type="image/svg+xml")


@router.get("/verify/{credential_id}")
def public_verify(credential_id: str, db: Session = Depends(get_db)) -> dict:
    return verify_credential(db, credential_id)
