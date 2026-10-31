from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import current_user, require_roles
from app.core.db import get_db
from app.models import ConsentRequest, User
from app.schemas import ConsentCreateRequest, ConsentDecision
from app.services.audit import append_audit
from app.services.consent import ALLOWED_FIELDS, create_request, decide, read_shared, request_payload

router = APIRouter(prefix="/consent", tags=["consent"])


@router.get("/fields")
def allowed_fields() -> dict:
    return {
        "fields": [{"key": key, "label": label} for key, label in ALLOWED_FIELDS.items()],
        "never_shared": ["APAAR", "name", "date of birth", "phone", "email"],
        "simulated": True,
    }


@router.post("/requests")
def create_consent_request(
    payload: ConsentCreateRequest,
    user: User = Depends(require_roles("verifier")),
    db: Session = Depends(get_db),
) -> dict:
    try:
        request = create_request(db, user, payload.enrolment_ref, payload.fields, payload.purpose)
    except (ValueError, LookupError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    append_audit(
        db,
        action="consent.requested",
        resource=f"consent:{request.id}",
        actor=user,
        detail={"fields": payload.fields, "purpose": payload.purpose, "simulated": True},
    )
    db.commit()
    return {"request": request_payload(db, request), "simulated": True}


@router.get("/requests/mine")
def my_requests(
    user: User = Depends(current_user), db: Session = Depends(get_db)
) -> dict:
    if user.role == "student":
        if user.person_id is None:
            raise HTTPException(status_code=400, detail="This student account is not linked to a record.")
        rows = list(
            db.scalars(
                select(ConsentRequest)
                .where(ConsentRequest.subject_person_id == user.person_id)
                .order_by(ConsentRequest.id.desc())
            )
        )
        return {
            "requests": [request_payload(db, r) for r in rows],
            "role": "student",
            "person_linked": True,
            "simulated": True,
        }
    if user.role == "verifier":
        rows = list(
            db.scalars(
                select(ConsentRequest)
                .where(ConsentRequest.verifier_id == user.id)
                .order_by(ConsentRequest.id.desc())
            )
        )
        return {
            "requests": [request_payload(db, r) for r in rows],
            "role": "verifier",
            "simulated": True,
        }
    raise HTTPException(status_code=403, detail="Consent inbox is only for students and verifiers.")


@router.post("/requests/{request_id}/decision")
def consent_decision(
    request_id: int,
    payload: ConsentDecision,
    user: User = Depends(require_roles("student")),
    db: Session = Depends(get_db),
) -> dict:
    if user.person_id is None:
        raise HTTPException(status_code=400, detail="This student account is not linked to a record.")
    try:
        request, token = decide(db, request_id, user.person_id, payload.approve)
    except (ValueError, LookupError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    append_audit(
        db,
        action="consent.approved" if payload.approve else "consent.denied",
        resource=f"consent:{request.id}",
        actor=user,
        detail={"fields": request.fields, "simulated": True},
    )
    db.commit()
    return {
        "request": request_payload(db, request),
        "share_token": token,
        "share_note": (
            "Share this one-time link with the verifier. It expires automatically."
            if token
            else "No data will be shared."
        ),
        "simulated": True,
    }


@router.get("/share/{token}")
def read_share(
    token: str,
    user: User = Depends(require_roles("verifier")),
    db: Session = Depends(get_db),
) -> dict:
    try:
        payload = read_shared(db, token, user)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except TimeoutError as exc:
        raise HTTPException(status_code=410, detail=str(exc)) from exc
    append_audit(
        db,
        action="consent.consumed",
        resource=f"consent:{payload['consent_request_id']}",
        actor=user,
        detail={"purpose": payload["purpose"], "simulated": True},
    )
    db.commit()
    return {**payload, "simulated": True}
