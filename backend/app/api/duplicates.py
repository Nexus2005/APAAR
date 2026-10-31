from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import current_user
from app.core.db import get_db
from app.models import DuplicateLink, Institution, User
from app.services.duplicates import duplicate_payload

router = APIRouter(prefix="/duplicates", tags=["duplicates"])


@router.get("")
def list_duplicates(
    institution_id: int | None = None,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    if user.role in {"verifier", "student"}:
        raise HTTPException(status_code=403, detail="This role cannot read duplicate evidence.")
    links = list(
        db.scalars(select(DuplicateLink).order_by(DuplicateLink.match_type, DuplicateLink.id.desc()))
    )
    payload = [duplicate_payload(db, link) for link in links]
    if user.role in {"institution_operator", "institution_admin"}:
        institution = db.get(Institution, user.institution_id or 0)
        if institution is None:
            return {"duplicates": [], "count": 0}
        payload = [
            item
            for item in payload
            if institution.aicte_code in {item["a"]["institution_code"], item["b"]["institution_code"]}
        ]
    elif institution_id:
        institution = db.get(Institution, institution_id)
        payload = [
            item
            for item in payload
            if institution
            and institution.aicte_code in {item["a"]["institution_code"], item["b"]["institution_code"]}
        ]
    return {
        "duplicates": payload,
        "count": len(payload),
        "whitelisted": sum(1 for item in payload if item["whitelisted_reason"]),
        "simulated": True,
    }
