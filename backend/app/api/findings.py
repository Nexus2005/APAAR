from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import current_user, ensure_institution_access
from app.core.db import get_db
from app.models import Finding, FindingEvent, Institution, User
from app.schemas import FindingAction
from app.services.audit import append_audit
from app.services.findings_engine import finding_payload

router = APIRouter(prefix="/findings", tags=["findings"])

TRANSITIONS = {
    "start_review": ({"open"}, "in_review"),
    "resolve": ({"open", "in_review", "escalated"}, "resolved"),
    "dismiss": ({"open", "in_review", "escalated"}, "dismissed"),
    "escalate": ({"open", "in_review"}, "escalated"),
    "reopen": ({"resolved", "dismissed"}, "open"),
    "comment": ({"open", "in_review", "resolved", "dismissed", "escalated"}, None),
}

ACTION_LABELS = {
    "start_review": "Review started",
    "resolve": "Resolved",
    "dismiss": "Dismissed",
    "escalate": "Escalated to AICTE",
    "reopen": "Reopened",
    "comment": "Comment added",
}


def _authorise(user: User, finding: Finding) -> None:
    if user.role == "central_reviewer":
        return
    if user.role in {"institution_admin", "institution_operator"}:
        ensure_institution_access(user, finding.institution_id)
        if user.role == "institution_operator" and finding.status not in {"open", "in_review"}:
            raise HTTPException(status_code=403, detail="Operators cannot act on closed findings.")
        return
    raise HTTPException(status_code=403, detail="Your role cannot act on findings.")


@router.get("")
def list_findings(
    status: str | None = None,
    rule: str | None = None,
    severity: str | None = None,
    institution_id: int | None = None,
    limit: int = 200,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    query = select(Finding).order_by(Finding.id.desc()).limit(min(limit, 500))
    if user.role in {"institution_operator", "institution_admin"}:
        query = query.where(Finding.institution_id == (user.institution_id or -1))
    elif user.role in {"verifier", "student"}:
        raise HTTPException(status_code=403, detail="This role cannot read findings.")
    elif institution_id:
        query = query.where(Finding.institution_id == institution_id)
    if status:
        query = query.where(Finding.status == status)
    if rule:
        query = query.where(Finding.rule_code == rule)
    if severity:
        query = query.where(Finding.severity == severity)
    rows = list(db.scalars(query))
    institution_ids = [r.institution_id for r in rows] or [0]
    institutions = {
        i.id: i for i in db.scalars(select(Institution).where(Institution.id.in_(institution_ids)))
    }
    return {
        "findings": [finding_payload(row, institutions.get(row.institution_id)) for row in rows],
        "count": len(rows),
        "simulated": True,
    }


@router.get("/{finding_id}")
def get_finding(
    finding_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)
) -> dict:
    finding = db.get(Finding, finding_id)
    if finding is None:
        raise HTTPException(status_code=404, detail="Finding not found.")
    if user.role in {"institution_operator", "institution_admin"}:
        ensure_institution_access(user, finding.institution_id)
    if user.role in {"verifier", "student"}:
        raise HTTPException(status_code=403, detail="This role cannot read findings.")
    institution = db.get(Institution, finding.institution_id)
    events = list(
        db.scalars(select(FindingEvent).where(FindingEvent.finding_id == finding.id).order_by(FindingEvent.id))
    )
    payload = finding_payload(finding, institution)
    payload["history"] = [
        {
            "action": event.action,
            "label": ACTION_LABELS.get(event.action, event.action),
            "comment": event.comment,
            "actor": event.actor_name,
            "at": event.at.isoformat(),
        }
        for event in events
    ]
    payload["allowed_actions"] = [
        name
        for name, (allowed_from, _) in TRANSITIONS.items()
        if finding.status in allowed_from and name != "comment"
    ]
    return payload


@router.post("/{finding_id}/actions")
def act_on_finding(
    finding_id: int,
    payload: FindingAction,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    finding = db.get(Finding, finding_id)
    if finding is None:
        raise HTTPException(status_code=404, detail="Finding not found.")
    _authorise(user, finding)
    action = payload.action.strip()
    if action not in TRANSITIONS:
        raise HTTPException(status_code=400, detail="Unknown action.")
    allowed_from, target = TRANSITIONS[action]
    if finding.status not in allowed_from:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot {action.replace('_', ' ')} a finding that is {finding.status}.",
        )
    comment = payload.comment.strip()
    if len(comment) < 3:
        raise HTTPException(status_code=400, detail="A comment is required for every action.")
    if target:
        finding.status = target
    db.add(
        FindingEvent(
            finding_id=finding.id,
            action=action,
            comment=comment,
            actor_id=user.id,
            actor_name=user.name,
        )
    )
    append_audit(
        db,
        action=f"finding.{action}",
        resource=f"finding:{finding.id}",
        actor=user,
        detail={"rule_code": finding.rule_code, "comment": comment, "new_status": finding.status},
    )
    db.commit()
    institution = db.get(Institution, finding.institution_id)
    return {"finding": finding_payload(finding, institution), "simulated": True}
