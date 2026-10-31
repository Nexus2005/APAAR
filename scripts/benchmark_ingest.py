#!/usr/bin/env python
"""Measure synchronous ingestion of a 5,000-row file.

Uses a throwaway SQLite database and does NOT touch the demo database.
The timer covers parsing, mapping, validation, person/enrolment writes and the audit
entry. Rule evaluation and duplicate detection are measured separately by evaluate.py.
"""

from __future__ import annotations

import csv
import io
import json
import os
import shutil
import tempfile
import time
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TMP = Path(tempfile.mkdtemp(prefix="apaar_bench_"))
os.environ["DATABASE_URL"] = f"sqlite:///{(TMP / 'bench.db').as_posix()}"
os.environ["SEED_ON_STARTUP"] = "false"

import sys  # noqa: E402

sys.path.insert(0, str(ROOT / "backend"))

from app.core.db import Base, SessionLocal, engine  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.models import Institution, Programme, User  # noqa: E402
from app.services.ingestion import ingest  # noqa: E402
from app.services.mapping import alias_config  # noqa: E402

HEADERS = [
    "Student Name",
    "Date of Birth",
    "APAAR ID",
    "APAAR Status",
    "Programme",
    "Seat Category",
    "Admission Date",
    "Mode of Admission",
    "Gender",
    "Mobile",
    "Email",
    "Nationality",
    "Qualifying Exam %",
    "Remarks",
]
ROWS = 5000


def build_file() -> bytes:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(HEADERS)
    for index in range(ROWS):
        writer.writerow(
            [
                f"Synthetic Student {index}",
                "2005-06-15",
                f"7{index:011d}",
                "provided",
                "CSE",
                "regular",
                date(2026, 7, 1 + (index % 28)).isoformat(),
                "counselling",
                "F" if index % 2 else "M",
                f"9{index % 1000000000:09d}",
                f"bench.{index}@example.invalid",
                "India",
                round(55 + (index % 40), 1),
                "",
            ]
        )
    return buffer.getvalue().encode()


def main() -> None:
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        institution = Institution(
            aicte_code="SYN-BENCH-999",
            name="Benchmark Institute (throwaway)",
            short_name="Benchmark",
            state="Maharashtra",
            region="West",
            city="Pune",
        )
        db.add(institution)
        db.flush()
        programme = Programme(
            institution_id=institution.id,
            code="CSE",
            name="B.Tech Computer Science & Engineering",
            level="UG",
            discipline_group="Engineering",
            duration_years=4,
        )
        db.add(programme)
        user = User(
            email="bench@example.invalid",
            name="Benchmark operator",
            password_hash=hash_password("demo1234"),
            role="institution_operator",
            institution_id=institution.id,
        )
        db.add(user)
        db.flush()

        data = build_file()
        mapping = {
            key: {"source_column": HEADERS[index]}
            for index, key in enumerate(alias_config().keys())
        }
        started = time.perf_counter()
        batch, duplicate = ingest(
            db,
            user=user,
            institution=institution,
            filename="benchmark-5000.csv",
            data=data,
            mapping=mapping,
        )
        db.commit()
        elapsed = time.perf_counter() - started
        print(
            json.dumps(
                {
                    "rows": batch.total_rows,
                    "accepted": batch.accepted_rows,
                    "rejected": batch.rejected_rows,
                    "seconds": round(elapsed, 2),
                    "rows_per_second": round(batch.total_rows / elapsed, 1),
                    "duplicate_upload": duplicate,
                    "scope": "parse + validate + person/enrolment writes + audit (SQLite, local laptop)",
                },
                indent=2,
            )
        )
    engine.dispose()
    shutil.rmtree(TMP, ignore_errors=True)


if __name__ == "__main__":
    main()
