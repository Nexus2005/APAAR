#!/usr/bin/env python
"""Measure the prototype against the seeded ground truth.

Only prints numbers produced by this run. No pre-filled metric is read from docs.
Usage:
  python scripts/evaluate.py --stage mapping|rules|duplicates|anomaly|all
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT))

from sqlalchemy import select  # noqa: E402

from app.core.db import SessionLocal  # noqa: E402
from app.models import (  # noqa: E402
    AnomalyScore,
    DuplicateLink,
    Enrolment,
    Finding,
    Institution,
    RowResult,
    UploadBatch,
)
from app.services.ingestion import preview  # noqa: E402
from app.services.mapping import alias_config  # noqa: E402

GT = json.loads((ROOT / "data" / "ground_truth.json").read_text(encoding="utf-8"))


def mapping_stage() -> dict:
    fields = alias_config()
    required = [key for key, meta in fields.items() if meta.get("required")]
    per_file = []
    for meta in GT["files"]:
        path = ROOT / "data" / "synthetic" / meta["filename"]
        result = preview(meta["filename"], path.read_bytes())
        mapped = result["suggested_mapping"]
        correct = sum(1 for key in required if (mapped.get(key) or {}).get("source_column"))
        per_file.append(
            {
                "file": meta["filename"],
                "required_fields": len(required),
                "correctly_mapped": correct,
                "accuracy_pct": round(correct / len(required) * 100, 1),
            }
        )
    mean = round(sum(item["accuracy_pct"] for item in per_file) / len(per_file), 1)
    return {
        "stage": "mapping",
        "required_fields": required,
        "mean_required_field_accuracy_pct": mean,
        "files": per_file,
    }


def rules_stage() -> dict:
    with SessionLocal() as db:
        rejected: dict[str, int] = {}
        for row in db.scalars(select(RowResult).where(RowResult.status == "rejected")):
            for code in json.loads(row.error_codes or "[]"):
                rejected[code] = rejected.get(code, 0) + 1
        accepted = db.scalar(select(UploadBatch.accepted_rows).where(UploadBatch.id == 1))
        total_rejected = sum(
            1 for row in db.scalars(select(RowResult).where(RowResult.status == "rejected"))
        )

        actual_over: set[tuple] = set()
        for finding in db.scalars(select(Finding).where(Finding.rule_code == "INTAKE_EXCEEDED")):
            evidence = json.loads(finding.subject_json)
            institution = db.get(Institution, finding.institution_id)
            actual_over.add(
                (
                    institution.aicte_code,
                    evidence["programme_code"],
                    evidence["excess"],
                )
            )
        expected_over = {
            (item["institution_code"], item["programme_code"], item["excess"])
            for item in GT["seeded"]["over_intake"]
        }
        intake_hits = expected_over & actual_over
        intake_precision = round(len(intake_hits) / max(len(actual_over), 1) * 100, 1)
        intake_recall = round(len(intake_hits) / max(len(expected_over), 1) * 100, 1)

        actual_sn: set[tuple] = set()
        for finding in db.scalars(select(Finding).where(Finding.rule_code == "SEAT_CAP_EXCEEDED")):
            evidence = json.loads(finding.subject_json)
            if evidence.get("category") == "supernumerary":
                institution = db.get(Institution, finding.institution_id)
                actual_sn.add(
                    (institution.aicte_code, evidence["programme_code"], evidence["excess"])
                )
        expected_sn = {
            (item["institution_code"], item["programme_code"], item["excess"])
            for item in GT["seeded"]["supernumerary_breach"]
        }

        rule_counts = {}
        for finding in db.scalars(select(Finding)):
            rule_counts[finding.rule_code] = rule_counts.get(finding.rule_code, 0) + 1

        return {
            "stage": "rules",
            "rejected_rows": total_rejected,
            "expected_rejected_rows": GT["totals"]["expected_rejected_rows"],
            "rejected_by_code": rejected,
            "expected_malformed_apaar": GT["seeded"]["malformed_apaar"],
            "expected_missing_apaar": GT["seeded"]["missing_apaar"],
            "expected_pending_declined": GT["seeded"]["pending_declined"],
            "finding_counts": rule_counts,
            "intake_exceeded": {
                "expected": sorted(map(list, expected_over)),
                "actual": sorted(map(list, actual_over)),
                "precision_pct": intake_precision,
                "recall_pct": intake_recall,
            },
            "supernumerary_breach": {
                "expected": sorted(map(list, expected_sn)),
                "actual": sorted(map(list, actual_sn)),
                "matched": expected_sn == actual_sn,
            },
            "category_inconsistency_seeded": GT["seeded"]["category_inconsistencies"],
            "category_inconsistency_findings": rule_counts.get("CATEGORY_INCONSISTENT", 0),
        }


def duplicates_stage() -> dict:
    with SessionLocal() as db:
        links = list(db.scalars(select(DuplicateLink)))
        exact = [link for link in links if link.match_type == "exact_apaar"]
        fuzzy = [link for link in links if link.match_type == "fuzzy"]
        whitelisted = [link for link in exact if link.whitelisted_reason]
        cross_findings = list(
            db.scalars(select(Finding).where(Finding.rule_code == "DUP_CROSS_INSTITUTION"))
        )
        expected = GT["seeded"]["cross_institution_pairs"]
        expected_flagged = GT["seeded"]["cross_institution_flaggable_pairs"]
        return {
            "stage": "duplicates",
            "exact_links": len(exact),
            "whitelisted_exact_links": len(whitelisted),
            "expected_pairs": expected,
            "expected_whitelisted": GT["seeded"]["whitelisted_pairs"],
            "cross_institution_findings": len(cross_findings),
            "expected_flaggable": expected_flagged,
            "fuzzy_links": len(fuzzy),
            "expected_fuzzy_pairs": GT["seeded"].get("fuzzy_duplicates", 0),
            "exact_recall_pct": round(len(exact) / max(expected, 1) * 100, 1),
            "whitelist_match": len(whitelisted) == GT["seeded"]["whitelisted_pairs"],
        }


def anomaly_stage() -> dict:
    with SessionLocal() as db:
        scores = list(db.scalars(select(AnomalyScore).order_by(AnomalyScore.rank)))
        institutions = {i.id: i for i in db.scalars(select(Institution))}
        seeded = set(GT["seeded"]["anomalous_institutions"])
        top5 = [institutions[s.institution_id].aicte_code for s in scores[:5]]
        flagged = [s for s in scores if s.flagged]
        reason_checks = []
        for score in scores:
            if not score.flagged:
                continue
            reasons = json.loads(score.reasons_json or "[]")
            payload = json.loads(score.features_json or "{}")
            numbers = set()

            def collect(value):
                if isinstance(value, dict):
                    for nested in value.values():
                        collect(nested)
                elif isinstance(value, list):
                    for nested in value:
                        collect(nested)
                elif isinstance(value, (int, float)) and not isinstance(value, bool):
                    numbers.add(round(float(value), 1))

            collect(payload)
            reason_numbers = [round(float(n), 1) for n in re.findall(r"\d+(?:\.\d+)?", " ".join(reasons))]
            missing = [n for n in reason_numbers if n not in numbers]
            reason_checks.append(
                {
                    "institution": institutions[score.institution_id].aicte_code,
                    "reasons": len(reasons),
                    "numbers_not_in_features": missing,
                }
            )
        return {
            "stage": "anomaly",
            "method": json.loads(scores[0].features_json)["method"] if scores else None,
            "seeded_institutions": sorted(seeded),
            "top_5": top5,
            "seeded_in_top_5": [code for code in top5 if code in seeded],
            "flagged": [institutions[s.institution_id].aicte_code for s in flagged],
            "reason_checks": reason_checks,
            "all_flagged_have_two_reasons": all(c["reasons"] >= 2 for c in reason_checks),
            "no_invented_numbers": all(not c["numbers_not_in_features"] for c in reason_checks),
        }


def dashboard_stage() -> dict:
    with SessionLocal() as db:
        total = len(list(db.scalars(select(Enrolment).where(Enrolment.status != "withdrawn"))))
        return {"stage": "dashboard", "enrolments_sql": total}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", default="all", choices=["mapping", "rules", "duplicates", "anomaly", "all"])
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    stages = {
        "mapping": mapping_stage,
        "rules": rules_stage,
        "duplicates": duplicates_stage,
        "anomaly": anomaly_stage,
    }
    selected = stages if args.stage == "all" else {args.stage: stages[args.stage]}
    results = {}
    for name, function in selected.items():
        try:
            results[name] = function()
        except Exception as exc:  # noqa: BLE001 - evaluation must report, not crash silently
            results[name] = {"stage": name, "error": f"{type(exc).__name__}: {exc}"}

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        for name, payload in results.items():
            print(f"\n=== {name.upper()} ===")
            print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
