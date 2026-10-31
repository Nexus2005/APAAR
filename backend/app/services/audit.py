"""Append-only hash-chained audit log.

hash = SHA256(prev_hash + canonical_json(entry)). No blockchain is used.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AuditLog, User

GENESIS = "0" * 64


def canonical_json(data: dict) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), default=str)


def _hash_entry(prev_hash: str, body: dict) -> str:
    return hashlib.sha256((prev_hash + canonical_json(body)).encode()).hexdigest()


def append_audit(
    db: Session,
    *,
    action: str,
    resource: str,
    detail: dict | None = None,
    actor: User | None = None,
    actor_name: str | None = None,
) -> AuditLog:
    last = db.scalars(select(AuditLog).order_by(AuditLog.seq.desc()).limit(1)).first()
    prev_hash = last.hash if last else GENESIS
    seq = (last.seq + 1) if last else 1
    at = datetime.utcnow()
    body = {
        "seq": seq,
        "actor_id": actor.id if actor else None,
        "actor_name": actor.name if actor else (actor_name or "system"),
        "action": action,
        "resource": resource,
        "detail": detail or {},
        "at": at.isoformat(),
    }
    entry = AuditLog(
        seq=seq,
        actor_id=actor.id if actor else None,
        actor_name=body["actor_name"],
        action=action,
        resource=resource,
        detail_json=json.dumps(detail or {}, default=str),
        at=at,
        prev_hash=prev_hash,
        hash=_hash_entry(prev_hash, body),
    )
    db.add(entry)
    db.flush()
    return entry


def verify_chain(db: Session) -> dict:
    entries = list(db.scalars(select(AuditLog).order_by(AuditLog.seq)))
    prev = GENESIS
    for entry in entries:
        body = {
            "seq": entry.seq,
            "actor_id": entry.actor_id,
            "actor_name": entry.actor_name,
            "action": entry.action,
            "resource": entry.resource,
            "detail": json.loads(entry.detail_json or "{}"),
            "at": entry.at.isoformat(),
        }
        expected = _hash_entry(prev, body)
        if entry.prev_hash != prev or entry.hash != expected:
            return {
                "valid": False,
                "entries": len(entries),
                "broken_seq": entry.seq,
                "message": f"Hash chain broken at sequence {entry.seq}.",
            }
        prev = entry.hash
    return {
        "valid": True,
        "entries": len(entries),
        "broken_seq": None,
        "message": "Every entry links to its predecessor.",
    }
