from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import current_user, ensure_institution_access
from app.core.config import get_settings, load_rules
from app.core.db import get_db
from app.models import Enrolment, Institution, User
from app.services.dashboard import _intake_table

router = APIRouter(tags=["institutions"])


@router.get("/institutions")
def list_institutions(
    user: User = Depends(current_user), db: Session = Depends(get_db)
) -> dict:
    if user.role in {"institution_operator", "institution_admin"}:
        institutions = [db.get(Institution, user.institution_id)] if user.institution_id else []
    elif user.role in {"central_reviewer", "sysadmin"}:
        institutions = list(db.scalars(select(Institution).order_by(Institution.state, Institution.name)))
    else:
        raise HTTPException(status_code=403, detail="Not available for this role.")
    institutions = [i for i in institutions if i]
    counts = {
        i.id: db.scalar(select(Enrolment.id).where(Enrolment.institution_id == i.id).limit(1))
        for i in institutions
    }
    return {
        "institutions": [
            {
                "id": i.id,
                "aicte_code": i.aicte_code,
                "name": i.name,
                "short_name": i.short_name,
                "state": i.state,
                "region": i.region,
                "city": i.city,
                "status": i.status,
                "has_data": counts.get(i.id) is not None,
            }
            for i in institutions
        ],
        "simulated": True,
    }


@router.get("/institutions/{institution_id}/intake")
def institution_intake(
    institution_id: int,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    ensure_institution_access(user, institution_id)
    institution = db.get(Institution, institution_id)
    if institution is None:
        raise HTTPException(status_code=404, detail="Institution not found.")
    return {
        "institution": {"id": institution.id, "name": institution.name, "code": institution.aicte_code},
        "intake": _intake_table(db, institution.id),
        "simulated": True,
    }


@router.get("/meta")
def meta() -> dict:
    rules = load_rules()
    return {
        "app": "APAAR-Setu",
        "tagline": "Enrolment integrity, with humans in the loop",
        "simulated": True,
        "banner": "SIMULATED — NOT OFFICIAL APAAR VERIFICATION",
        "policy": {
            "version": rules.get("version"),
            "effective_from": str(rules.get("effective_from")),
            "seat_categories": rules.get("intake", {}).get("seat_categories", {}),
            "admission_window": rules.get("admission_window"),
        },
        "llm_provider": get_settings().llm_provider,
        "demo_mode": get_settings().demo_mode,
    }
