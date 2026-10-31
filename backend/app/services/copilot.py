"""Deterministic, tool-based copilot.

The router chooses one of a fixed list of parameterised query functions. No free-form
SQL is generated, and no statistic is produced by a language model.
"""

from __future__ import annotations

import json
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AnomalyScore, DuplicateLink, Enrolment, Finding, Institution
from app.services.dashboard import _intake_table

STATES = ["Maharashtra", "Karnataka", "Tamil Nadu", "Uttar Pradesh"]


def _state_in(question: str) -> str | None:
    lower = question.lower()
    for state in STATES:
        if state.lower() in lower:
            return state
    return None


def colleges_over_intake(db: Session, state: str | None = None) -> list[dict]:
    institutions = list(db.scalars(select(Institution)))
    rows = []
    for institution in institutions:
        if state and institution.state != state:
            continue
        for row in _intake_table(db, institution.id):
            if row["approved_intake"] and row["regular_admitted"] > row["approved_intake"]:
                rows.append(
                    {
                        "institution_code": institution.aicte_code,
                        "institution": institution.name,
                        "state": institution.state,
                        "programme": row["programme_code"],
                        "approved_intake": row["approved_intake"],
                        "regular_admitted": row["regular_admitted"],
                        "excess": row["regular_admitted"] - row["approved_intake"],
                    }
                )
    return sorted(rows, key=lambda r: r["excess"], reverse=True)


def top_anomalies(db: Session, n: int = 5, state: str | None = None) -> list[dict]:
    scores = list(db.scalars(select(AnomalyScore).order_by(AnomalyScore.rank)))
    institutions = {i.id: i for i in db.scalars(select(Institution))}
    rows = []
    for score in scores:
        institution = institutions.get(score.institution_id)
        if institution is None:
            continue
        if state and institution.state != state:
            continue
        rows.append(
            {
                "institution_code": institution.aicte_code,
                "institution": institution.name,
                "state": institution.state,
                "rank": score.rank,
                "score": score.score,
                "reasons": json.loads(score.reasons_json or "[]"),
            }
        )
        if len(rows) >= n:
            break
    return rows


def duplicates_summary(db: Session, institution_code: str | None = None) -> list[dict]:
    links = list(db.scalars(select(DuplicateLink)))
    institutions = {i.id: i for i in db.scalars(select(Institution))}
    rows = []
    for link in links:
        a = db.get(Enrolment, link.enrolment_a)
        b = db.get(Enrolment, link.enrolment_b)
        if not a or not b:
            continue
        if institution_code and institution_code not in {
            institutions[a.institution_id].aicte_code,
            institutions[b.institution_id].aicte_code,
        }:
            continue
        rows.append(
            {
                "link_id": link.id,
                "match_type": link.match_type,
                "score": link.score,
                "institution_a": institutions[a.institution_id].aicte_code,
                "institution_b": institutions[b.institution_id].aicte_code,
                "whitelisted": link.whitelisted_reason,
            }
        )
    return rows


def data_quality_by_state(db: Session) -> list[dict]:
    institutions = list(db.scalars(select(Institution)))
    findings = list(db.scalars(select(Finding)))
    rows = {}
    for institution in institutions:
        entry = rows.setdefault(
            institution.state,
            {"state": institution.state, "open_findings": 0, "blockers": 0, "warnings": 0},
        )
        for finding in findings:
            if finding.institution_id == institution.id and finding.status in {"open", "in_review"}:
                entry["open_findings"] += 1
                if finding.severity == "blocker":
                    entry["blockers"] += 1
                elif finding.severity in {"warning", "risk"}:
                    entry["warnings"] += 1
    return sorted(rows.values(), key=lambda r: r["open_findings"], reverse=True)


def compare_years(db: Session, metric: str | None = None, state: str | None = None) -> dict:
    years = list(db.scalars(select(Enrolment.academic_year).distinct()))
    if len(years) < 2:
        return {
            "available": False,
            "message": (
                "Only one academic year is seeded, so a year-on-year comparison would be "
                "invented. It is not shown."
            ),
            "years": years,
        }
    return {"available": True, "years": years}


def run_copilot(db: Session, question: str) -> dict:
    lower = question.lower()
    state = _state_in(question)
    if any(word in lower for word in ["anomal", "priority", "prioriti", "suspicious", "risk"]):
        tool = "top_anomalies"
        rows = top_anomalies(db, 5, state)
        answer = (
            f"{len(rows)} institution(s) are ranked for review"
            + (f" in {state}" if state else "")
            + ". These are prioritisation signals, not findings of fraud."
        )
    elif any(word in lower for word in ["duplicate", "dual", "two colleges", "cross"]):
        tool = "duplicates_summary"
        rows = duplicates_summary(db)
        whitelisted = sum(1 for r in rows if r["whitelisted"])
        answer = (
            f"{len(rows)} duplicate link(s) were found; {whitelisted} are whitelisted legitimate pairs. "
            "Every non-whitelisted link needs human review."
        )
    elif any(word in lower for word in ["quality", "missing", "error", "data quality"]):
        tool = "data_quality_by_state"
        rows = data_quality_by_state(db)
        total = sum(r["open_findings"] for r in rows)
        answer = f"{total} open findings are distributed across {len(rows)} state(s)."
    elif any(word in lower for word in ["year", "compare", "growth"]):
        tool = "compare_years"
        result = compare_years(db)
        rows = [result]
        answer = result["message"]
    elif any(word in lower for word in ["intake", "over", "exceed", "seat"]):
        tool = "colleges_over_intake"
        rows = colleges_over_intake(db, state)
        answer = (
            f"{len(rows)} programme(s) are above approved intake"
            + (f" in {state}" if state else "")
            + ". Regular seats only; NRI/OCI/FN/supernumerary are counted separately."
        )
    else:
        return {
            "answer": (
                "I can answer only from these fixed tools: colleges over intake, top anomalies, "
                "duplicate summary, data quality by state, and year comparison. I cannot run free SQL."
            ),
            "tool": None,
            "rows": [],
            "citations": [],
            "llm_used": False,
            "simulated": True,
        }

    citations = [
        f"{tool}:{row.get('institution_code') or row.get('link_id') or row.get('state')}"
        for row in rows[:5]
    ]
    return {
        "answer": answer,
        "tool": tool,
        "parameters": {"state": state},
        "rows": rows[:20],
        "citations": citations,
        "llm_used": False,
        "generated_at": datetime.utcnow().isoformat(),
        "simulated": True,
    }
