from __future__ import annotations

import json
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import load_rules
from app.models import RuleVersion


def get_active_rule_version(db: Session, on: date | None = None) -> RuleVersion:
    """Return the newest rule version effective on/before `on`; create v1 if absent."""
    on = on or date.today()
    version = db.scalars(
        select(RuleVersion)
        .where(RuleVersion.effective_from <= on, RuleVersion.active.is_(True))
        .order_by(RuleVersion.effective_from.desc(), RuleVersion.version.desc())
        .limit(1)
    ).first()
    if version:
        return version
    config = load_rules()
    version = RuleVersion(
        version=int(config.get("version", 1)),
        effective_from=date.fromisoformat(str(config.get("effective_from", "2026-06-01"))),
        config_json=json.dumps(config, sort_keys=True),
        created_by="system",
        note="Seeded from config/rules.yaml",
    )
    db.add(version)
    db.flush()
    return version


def seat_category_config(rules: dict, category: str) -> dict:
    return (rules.get("intake", {}).get("seat_categories", {}) or {}).get(category, {}) or {}
