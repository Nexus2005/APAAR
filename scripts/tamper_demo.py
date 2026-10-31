#!/usr/bin/env python
"""Demonstrate tamper detection: mutate one stored credential claim or audit entry.

This edits the DEMO database only. Never run it against production-like data.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from sqlalchemy import select  # noqa: E402

from app.core.db import SessionLocal  # noqa: E402
from app.models import AuditLog, Credential  # noqa: E402
from app.services.audit import verify_chain  # noqa: E402
from app.services.credentials import verify_credential  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", choices=["credential", "audit"], default="credential")
    args = parser.parse_args()

    with SessionLocal() as db:
        if args.target == "credential":
            credential = db.scalars(select(Credential).limit(1)).first()
            if credential is None:
                print("No credential found. Seed the demo database first.")
                return
            payload = json.loads(credential.payload_json)
            payload["claims"]["programme"] = "TAMPERED — DEMO"
            credential.payload_json = json.dumps(payload, sort_keys=True)
            db.commit()
            result = verify_credential(db, credential.credential_id)
            print(f"Credential {credential.credential_id} mutated.")
            print(f"Verification now reports: {result['status']} — {result['message']}")
        else:
            entry = db.scalars(select(AuditLog).order_by(AuditLog.seq.desc()).limit(1)).first()
            if entry is None:
                print("No audit entries found. Seed the demo database first.")
                return
            detail = json.loads(entry.detail_json)
            detail["tampered"] = True
            entry.detail_json = json.dumps(detail)
            db.commit()
            result = verify_chain(db)
            print(f"Audit entry #{entry.seq} mutated.")
            print(result)
            print("Re-run the seed or delete data/app.db to restore a clean demo.")


if __name__ == "__main__":
    main()
