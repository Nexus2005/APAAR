from __future__ import annotations

import json

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.core.db import get_db
from app.models import AuditLog, Institution, User
from app.services.audit import verify_chain

router = APIRouter(prefix="/audit", tags=["audit"])


def _row(entry: AuditLog) -> dict:
    return {
        "seq": entry.seq,
        "actor": entry.actor_name,
        "action": entry.action,
        "resource": entry.resource,
        "detail": json.loads(entry.detail_json or "{}"),
        "at": entry.at.isoformat(),
        "prev_hash": entry.prev_hash,
        "hash": entry.hash,
    }


@router.get("")
def list_audit(
    limit: int = 100,
    user: User = Depends(require_roles("central_reviewer", "sysadmin", "institution_admin")),
    db: Session = Depends(get_db),
) -> dict:
    entries = list(
        db.scalars(select(AuditLog).order_by(AuditLog.seq.desc()).limit(min(limit, 500)))
    )
    if user.role == "institution_admin":
        institution = db.get(Institution, user.institution_id or 0)
        if institution:
            entries = [
                entry
                for entry in entries
                if institution.aicte_code in entry.detail_json
                or f"institution:{institution.id}" in entry.resource
                or entry.actor_id == user.id
            ]
    return {"entries": [_row(entry) for entry in entries], "simulated": True}


@router.get("/verify")
def verify(
    user: User = Depends(require_roles("central_reviewer", "sysadmin", "institution_admin")),
    db: Session = Depends(get_db),
) -> dict:
    result = verify_chain(db)
    return {**result, "simulated": True}
