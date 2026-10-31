#!/usr/bin/env python
"""Generate deterministic synthetic admission files + ground truth.

Every person, institution and identifier here is fictional and marked SYNTHETIC.
Usage: python scripts/generate_synthetic.py --seed 42 [--out data/synthetic]
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import re
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ACADEMIC_YEAR = "2026-27"
WINDOW_START = date(2026, 6, 1)
WINDOW_END = date(2026, 11, 30)

STATES = ["Maharashtra", "Karnataka", "Tamil Nadu", "Uttar Pradesh"]

INSTITUTIONS = [
    ("SYN-MH-001", "Sahyadri Institute of Technology", "SIT Pune", "Maharashtra", "West", "Pune"),
    ("SYN-MH-002", "Deccan College of Engineering", "DCE Mumbai", "Maharashtra", "West", "Mumbai"),
    ("SYN-MH-003", "Vidarbha Technical University", "VTU Nagpur", "Maharashtra", "West", "Nagpur"),
    ("SYN-KA-004", "Cauvery Institute of Science & Technology", "CIST Bengaluru", "Karnataka", "South", "Bengaluru"),
    ("SYN-KA-005", "Malnad School of Engineering", "MSE Mysuru", "Karnataka", "South", "Mysuru"),
    ("SYN-KA-006", "Karavali Institute of Technology", "KIT Mangaluru", "Karnataka", "South", "Mangaluru"),
    ("SYN-TN-007", "Marina College of Engineering", "MCE Chennai", "Tamil Nadu", "South", "Chennai"),
    ("SYN-TN-008", "Kovai Institute of Technology", "KIT Coimbatore", "Tamil Nadu", "South", "Coimbatore"),
    ("SYN-TN-009", "Vaigai Technical Campus", "VTC Madurai", "Tamil Nadu", "South", "Madurai"),
    ("SYN-UP-010", "Gomti Institute of Technology", "GIT Lucknow", "Uttar Pradesh", "North", "Lucknow"),
    ("SYN-UP-011", "Yamuna College of Engineering", "YCE Noida", "Uttar Pradesh", "North", "Noida"),
    ("SYN-UP-012", "Ganga Technical Institute", "GTI Kanpur", "Uttar Pradesh", "North", "Kanpur"),
]

PROGRAMMES = [
    ("CSE", "B.Tech Computer Science & Engineering", "UG", "Engineering", "1", 4),
    ("ECE", "B.Tech Electronics & Communication", "UG", "Engineering", "1", 4),
    ("MEC", "B.Tech Mechanical Engineering", "UG", "Engineering", "1", 4),
    ("CIV", "B.Tech Civil Engineering", "UG", "Engineering", "1", 4),
    ("AIML", "B.Tech Artificial Intelligence & ML", "UG", "Engineering", "1", 4),
    ("MBA", "Master of Business Administration", "PG", "Management", "1", 2),
    ("MCA", "Master of Computer Applications", "PG", "Computer Applications", "1", 2),
]

# Every variant has 14 columns in canonical order; only the labels change.
HEADER_VARIANTS = [
    ["Student Name", "Date of Birth", "APAAR ID", "APAAR Status", "Programme", "Seat Category",
     "Admission Date", "Mode of Admission", "Gender", "Mobile", "Email", "Nationality",
     "Qualifying Exam %", "Remarks"],
    ["Name of Candidate", "DOB", "APAAR No", "APAAR Status", "Course", "Quota", "Date of Admission",
     "Admission Mode", "Sex", "Contact No", "E Mail", "Country", "Marks", "Remarks"],
    ["Stu. Name", "D.O.B", "Student APAAR Id", "Id Status", "Program", "Seat Type", "Admission Dt",
     "Mode", "Gender", "Phone", "Email Id", "Nationality", "Percentage", "Remarks"],
    ["Candidate Name", "Birth Date", "Student APAAR", "APAAR Consent Status", "Programme Name",
     "Admission Category", "Admitted On", "Admission Mode", "Student Gender", "Mobile No",
     "Student Email", "Nationality", "Qualifying Exam Percentage", "Remarks"],
    ["Full Name", "Date Birth", "APAAR Identifier", "APAAR Status", "Branch", "Seat", "DOA", "Mode",
     "Sex", "Contact", "Email", "Country", "Exam Percentage", "Remarks"],
]

FIELD_ORDER = ["name", "dob", "apaar_id", "apaar_status", "programme", "seat_category",
               "admission_date", "admission_mode", "gender", "phone", "email", "nationality",
               "qualifying_exam_pct", "remarks"]


def norm_name(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip()).lower()


def make_registry_id(rng: random.Random) -> str:
    first = rng.choice([2, 3, 4, 5, 6, 7, 8, 9])
    return str(first) + "".join(str(rng.randint(0, 9)) for _ in range(11))


def transliterate(name: str, rng: random.Random) -> str:
    swaps = {
        "Mohammed": "Muhammad", "Muhammad": "Mohammed", "Vikram": "Vikram", "Priya": "Priya",
    }
    first, *rest = name.split()
    first = swaps.get(first, first)
    variant = rng.choice(["swap", "initial", "spaces", "none"])
    if variant == "swap" and rest:
        return " ".join([*rest, first])
    if variant == "initial" and rest:
        return f"{first[0]}. {' '.join(rest)}"
    if variant == "spaces":
        return "  " + name.replace(" ", "  ") + " "
    return name


def build_programmes(rng: random.Random) -> dict[str, list[dict]]:
    programmes: dict[str, list[dict]] = {}
    for idx, (code, *_rest) in enumerate(INSTITUTIONS):
        count = 3 if idx % 3 else 2
        chosen = PROGRAMMES[: 3 + (idx % 4)]
        picks = rng.sample(chosen, count)
        programmes[code] = []
        for pcode, pname, level, discipline, shift, duration in picks:
            approved = rng.choice([54, 60, 66, 72])
            programmes[code].append(
                {
                    "code": pcode,
                    "name": pname,
                    "level": level,
                    "discipline_group": discipline,
                    "shift": shift,
                    "duration_years": duration,
                    "approved_intake": approved,
                }
            )
    return programmes


def admission_date(rng: random.Random, spike: bool) -> date:
    if spike:
        return WINDOW_END - timedelta(days=rng.randint(0, 6))
    start = WINDOW_START + timedelta(days=rng.randint(0, 60))
    return start + timedelta(days=rng.randint(0, 100))


def generate(seed: int = 42, out_dir: Path | None = None) -> dict:
    from faker import Faker

    out_dir = out_dir or (ROOT / "data" / "synthetic")
    out_dir.mkdir(parents=True, exist_ok=True)
    rng = random.Random(seed)
    fake = Faker("en_IN")
    Faker.seed(seed)

    programmes = build_programmes(rng)
    anomaly_codes = {INSTITUTIONS[2][0], INSTITUTIONS[7][0], INSTITUTIONS[11][0]}
    # distinct patterns so each seeded anomaly is explainable on its own:
    # spike = final-week uploads, shared phones, category skew
    spike_codes = {INSTITUTIONS[2][0]}
    shared_phone_codes = {INSTITUTIONS[7][0]}
    skew_codes = {INSTITUTIONS[11][0]}

    files = []
    registry: dict[str, dict] = {}
    stats = {
        "malformed_apaar": 0,
        "missing_apaar": 0,
        "pending_declined": 0,
        "unknown_apaar": 0,
        "in_file_duplicates": 0,
        "cross_institution_pairs": 0,
        "whitelisted_pairs": 0,
        "category_inconsistencies": 0,
        "implausible_dates": 0,
    }
    over_intake = []
    supernumerary_breach = []
    anomalous = []

    cross_pairs: list[dict] = []
    written_rows: list[dict] = []
    all_rows_by_inst: dict[str, list[dict]] = {code: [] for code, *_ in INSTITUTIONS}

    # ---- base student generation -------------------------------------------------
    for inst_index, (code, *_rest) in enumerate(INSTITUTIONS):
        inst_programmes = programmes[code]
        rows: list[dict] = []
        # target over-intake programmes: institution 0 (first), 4 (second), 9 (first)
        over_targets = {}
        if inst_index == 0:
            over_targets[inst_programmes[0]["code"]] = 7
        if inst_index == 4 and len(inst_programmes) > 1:
            over_targets[inst_programmes[1]["code"]] = 11
        if inst_index == 9:
            over_targets[inst_programmes[0]["code"]] = 5

        sn_targets = {}
        if inst_index == 1:
            sn_targets[inst_programmes[0]["code"]] = 8
        if inst_index == 6 and len(inst_programmes) > 1:
            sn_targets[inst_programmes[1]["code"]] = 8

        for prog in inst_programmes:
            approved = prog["approved_intake"]
            regular = max(18, int(approved * 0.55) + rng.randint(-4, 5))
            if prog["code"] in over_targets:
                regular = approved + over_targets[prog["code"]]
                over_intake.append(
                    {
                        "institution_code": code,
                        "programme_code": prog["code"],
                        "approved_intake": approved,
                        "regular_admitted": regular,
                        "excess": regular - approved,
                    }
                )
            for _ in range(regular):
                rows.append(make_student(rng, fake, code, prog, "regular", spike_codes, shared_phone_codes, skew_codes))
            sn_count = 2 + rng.randint(0, 2)
            if prog["code"] in sn_targets:
                sn_count = sn_targets[prog["code"]]
                supernumerary_breach.append(
                    {
                        "institution_code": code,
                        "programme_code": prog["code"],
                        "approved_intake": approved,
                        "cap_pct_assumed": 10,
                        "cap_seats": int(approved * 0.10),
                        "admitted": sn_count,
                        "excess": sn_count - int(approved * 0.10),
                    }
                )
            for _ in range(sn_count):
                rows.append(make_student(rng, fake, code, prog, "supernumerary", spike_codes, shared_phone_codes, skew_codes))
            if skew_codes and code in skew_codes:
                for _ in range(9):
                    rows.append(make_student(rng, fake, code, prog, "fn", spike_codes, shared_phone_codes, skew_codes))
                for _ in range(6):
                    rows.append(make_student(rng, fake, code, prog, "nri", spike_codes, shared_phone_codes, skew_codes))

        # shared phones for the shared-phone anomaly institution
        if code in shared_phone_codes:
            shared = [f"9{rng.randint(100000000, 999999999)}" for _ in range(4)]
            for row in rows[:30]:
                row["phone"] = shared[row["_seq"] % 4]
                row["_shared_phone"] = True

        all_rows_by_inst[code] = rows

    # ---- seeded row problems -----------------------------------------------------
    malformed_targets = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]
    malformed_per_inst = {code: 0 for code in all_rows_by_inst}
    remaining = 150
    for i, code in enumerate(INSTITUTIONS):
        take = remaining // (12 - i)
        malformed_per_inst[code[0]] = take
        remaining -= take

    def base_rows(rows: list[dict]) -> list[dict]:
        return [r for r in rows if r.get("_flag") in (None, "shared_phone")]

    for code, rows in all_rows_by_inst.items():
        for i in range(malformed_per_inst[code]):
            row = base_rows(rows)[(i * 7 + 3) % len(base_rows(rows))]
            candidate = row.copy()
            candidate["_seq"] = 900000 + i * 13
            candidate["apaar_id"] = rng.choice(
                ["AP-12345", "12345", "1234567890123", "ABCD12345678", "XYZ-998877"]
            )
            candidate["_flag"] = "malformed"
            rows.append(candidate)
            stats["malformed_apaar"] += 1

    # missing / pending APAAR: 60 rows; 40 marked pending or declined
    for idx, code in enumerate(all_rows_by_inst):
        rows = all_rows_by_inst[code]
        for j in range(5):
            row = base_rows(rows)[(j * 11 + 2) % len(base_rows(rows))]
            candidate = row.copy()
            candidate["_seq"] = 910000 + idx * 100 + j
            candidate["apaar_id"] = ""
            # 40 of the 60 missing-APAAR rows use the pending/declined lane.
            flagged = j < (4 if idx < 8 else 2)
            candidate["apaar_status"] = (
                "declined" if flagged and (idx + j) % 5 == 0 else "pending" if flagged else ""
            )
            candidate["_flag"] = "missing"
            rows.append(candidate)
            stats["missing_apaar"] += 1
            if candidate["apaar_status"]:
                stats["pending_declined"] += 1

    # valid-format identifiers missing from the simulated registry
    for code in all_rows_by_inst:
        rows = all_rows_by_inst[code]
        if code in {INSTITUTIONS[i][0] for i in range(10)}:
            row = rows[1].copy()
            row["_seq"] = 920000 + len(code) * 10
            row["apaar_id"] = make_registry_id(rng)
            row["_flag"] = "unknown"
            rows.append(row)
            stats["unknown_apaar"] += 1

    # in-file duplicates: 40 (unique per file to keep ground truth exact)
    for idx, code in enumerate(all_rows_by_inst):
        rows = all_rows_by_inst[code]
        for j in range(4 if idx < 4 else 3):
            source = base_rows(rows)[(j * 17 + 5) % len(base_rows(rows))]
            if not source.get("apaar_id"):
                source = next(r for r in base_rows(rows) if r.get("apaar_id"))
            duplicate = source.copy()
            duplicate["_seq"] = 930000 + idx * 100 + j
            duplicate["_flag"] = "in_file_duplicate"
            duplicate["_dup_of"] = str(source["_seq"])
            rows.append(duplicate)
            stats["in_file_duplicates"] += 1

    # category inconsistencies
    inconsistency_specs = [
        ("fn", "India"), ("nri", "India"), ("oci", "India"), ("fn", "India"), ("nri", "India"),
        ("oci", "India"), ("fn", "India"), ("nri", "India"), ("oci", "India"), ("fn", "India"),
    ]
    for i, (category, nationality) in enumerate(inconsistency_specs):
        code = INSTITUTIONS[i % 12][0]
        rows = all_rows_by_inst[code]
        row = base_rows(rows)[(i * 23 + 7) % len(base_rows(rows))].copy()
        row["_seq"] = 940000 + i
        row["apaar_id"] = make_registry_id(rng)
        row["seat_category"] = category
        row["nationality"] = nationality
        row["_flag"] = "category_inconsistency"
        rows.append(row)
        stats["category_inconsistencies"] += 1

    # implausible dates (too young)
    for i in range(25):
        code = INSTITUTIONS[i % 12][0]
        rows = all_rows_by_inst[code]
        row = base_rows(rows)[(i * 29 + 9) % len(base_rows(rows))].copy()
        row["_seq"] = 950000 + i
        row["apaar_id"] = make_registry_id(rng)
        row["dob"] = date(2014 + (i % 3), 1 + (i % 12), 1 + (i % 27))
        row["_flag"] = "implausible_date"
        rows.append(row)
        stats["implausible_dates"] += 1

    # cross-institution dual enrolments (35, of which 5 whitelisted)
    over_pairs = {(item["institution_code"], item["programme_code"]) for item in over_intake}
    for i in range(35):
        src_code = INSTITUTIONS[i % 12][0]
        dst_code = INSTITUTIONS[(i + 5) % 12][0]
        src_rows = [r for r in all_rows_by_inst[src_code] if r.get("apaar_id") and r.get("_flag") in (None, "shared_phone")]
        if not src_rows:
            continue
        source = src_rows[(i * 3 + 1) % len(src_rows)]
        dst_progs = programmes[dst_code]
        # keep the seeded over-intake excess exact: avoid adding shadow rows to those programmes
        eligible = [p for p in dst_progs if (dst_code, p["code"]) not in over_pairs]
        dst_prog = eligible[i % len(eligible)] if eligible else dst_progs[i % len(dst_progs)]
        # a fresh enrolment row that reuses the identifier at a second college
        shadow = source.copy()
        shadow["_seq"] = 960000 + i
        shadow["programme_code"] = dst_prog["code"]
        shadow["_programme_obj"] = dst_prog
        shadow["admission_date"] = source["admission_date"]
        shadow["_flag"] = "cross_institution"
        shadow["_legit"] = i < 5
        if i < 5:
            shadow["remarks"] = "Approved dual degree (institution whitelist)"
        all_rows_by_inst[dst_code].append(shadow)
        cross_pairs.append(
            {
                "apaar_id": source["apaar_id"],
                "institution_a": src_code,
                "institution_b": dst_code,
                "whitelisted": i < 5,
            }
        )
        stats["cross_institution_pairs"] += 1
        if i < 5:
            stats["whitelisted_pairs"] += 1

    # fuzzy duplicates: same name/dob with no APAAR at a second college (8 pairs)
    fuzzy_pairs = []
    for i in range(8):
        src_code = INSTITUTIONS[(i + 2) % 12][0]
        dst_code = INSTITUTIONS[(i + 7) % 12][0]
        src_rows = [
            r for r in all_rows_by_inst[src_code]
            if r.get("apaar_id") and r.get("_flag") in (None, "shared_phone")
        ]
        source = src_rows[(i * 13 + 4) % len(src_rows)]
        dst_progs = programmes[dst_code]
        eligible = [p for p in dst_progs if (dst_code, p["code"]) not in over_pairs]
        dst_prog = eligible[i % len(eligible)] if eligible else dst_progs[i % len(dst_progs)]
        shadow = source.copy()
        shadow["_seq"] = 970000 + i
        shadow["apaar_id"] = ""
        shadow["apaar_status"] = "pending"
        shadow["programme_code"] = dst_prog["code"]
        shadow["_programme_obj"] = dst_prog
        shadow["name"] = source["name"].title() + " "
        shadow["_flag"] = "fuzzy_duplicate"
        shadow["_fuzzy_of"] = source["_seq"]
        shadow["remarks"] = ""
        all_rows_by_inst[dst_code].append(shadow)
        fuzzy_pairs.append({"name": source["name"], "institution_a": src_code, "institution_b": dst_code})
    stats["fuzzy_duplicates"] = len(fuzzy_pairs)

    # ---- assign identity + write files ------------------------------------------
    total_written = 0
    unknown_ids = {
        row["apaar_id"]
        for rows in all_rows_by_inst.values()
        for row in rows
        if row.get("_flag") == "unknown"
    }
    for idx, (code, name, short, state, region, city) in enumerate(INSTITUTIONS):
        rows = all_rows_by_inst[code]
        for row in rows:
            row.setdefault("institution_code", code)
            if not row.get("apaar_id"):
                row["apaar_id"] = ""
            if (
                row.get("apaar_id")
                and row["apaar_id"] not in unknown_ids
                and re.match(r"^\d{12}$", row["apaar_id"])
            ):
                if row["apaar_id"] not in registry:
                    registry[row["apaar_id"]] = {
                        "apaar_id": row["apaar_id"],
                        "name": row["name"],
                        "dob": row["dob"].isoformat(),
                        "status": "active",
                    }
        total_written += len(rows)

        variant = HEADER_VARIANTS[idx % len(HEADER_VARIANTS)]
        suffix = ".xlsx" if idx in (3, 8) else ".csv"
        filename = f"{code}_admissions_{ACADEMIC_YEAR}{suffix}"
        path = out_dir / filename
        write_file(path, variant, rows)
        files.append(
            {
                "institution_code": code,
                "institution_name": name,
                "filename": filename,
                "rows": len(rows),
                "format": "xlsx" if suffix == ".xlsx" else "csv",
                "headers": variant,
            }
        )

    # registry tweaks: inactive + mismatched names/dob
    sorted_ids = sorted(registry)
    for apaar in sorted_ids[:12]:
        registry[apaar]["status"] = "inactive"
    for apaar in sorted_ids[12:27]:
        registry[apaar]["name"] = fake.name()
        registry[apaar]["_name_mismatch"] = True
    for apaar in sorted_ids[27:39]:
        registry[apaar]["dob"] = date(1990, 1, 1).isoformat()
        registry[apaar]["_dob_mismatch"] = True

    # Derive expected counters from the written files with the same documented rules
    # the engine implements (invalid APAAR -> rejected, repeated APAAR -> counted once).
    counts, derived = derive_counts(files, out_dir)
    over_intake = []
    supernumerary_breach = []
    for (inst_code, prog_code), categories in sorted(counts.items()):
        prog = next(p for p in programmes[inst_code] if p["code"] == prog_code)
        regular = categories.get("regular", 0)
        sn = categories.get("supernumerary", 0)
        if regular > prog["approved_intake"]:
            over_intake.append(
                {
                    "institution_code": inst_code,
                    "programme_code": prog_code,
                    "approved_intake": prog["approved_intake"],
                    "regular_admitted": regular,
                    "excess": regular - prog["approved_intake"],
                }
            )
        cap_seats = int(prog["approved_intake"] * 0.10)
        if sn > cap_seats:
            supernumerary_breach.append(
                {
                    "institution_code": inst_code,
                    "programme_code": prog_code,
                    "approved_intake": prog["approved_intake"],
                    "cap_pct_assumed": 10,
                    "cap_seats": cap_seats,
                    "admitted": sn,
                    "excess": sn - cap_seats,
                }
            )

    (out_dir / "mock_registry.json").write_text(
        json.dumps(sorted(registry.values(), key=lambda r: r["apaar_id"]), indent=2),
        encoding="utf-8",
    )

    programmes_out = []
    for code, items in programmes.items():
        for item in items:
            programmes_out.append({"institution_code": code, **item})

    anomalous = sorted(c for c in anomaly_codes)
    ground_truth = {
        "seed": seed,
        "academic_year": ACADEMIC_YEAR,
        "note": "All data is SYNTHETIC and generated for a prototype. Not official.",
        "totals": {
            "institutions": len(INSTITUTIONS),
            "programmes": len(programmes_out),
            "rows_written": total_written,
            "expected_rejected_rows": derived["rejected"],
            "expected_accepted_rows": derived["accepted"],
            "expected_enrolments": derived["enrolments"],
            "expected_repeated_rows": derived["repeated"],
        },
        "seeded": {
            **stats,
            "cross_institution_flaggable_pairs": stats["cross_institution_pairs"]
            - stats["whitelisted_pairs"],
            "over_intake": over_intake,
            "supernumerary_breach": supernumerary_breach,
            "anomalous_institutions": anomalous,
            "shared_phone_institution": sorted(shared_phone_codes),
            "category_skew_institution": sorted(skew_codes),
        },
        "cross_pairs": cross_pairs,
        "fuzzy_pairs": fuzzy_pairs,
        "files": files,
        "institutions": [
            {"code": c, "name": n, "short_name": s, "state": st, "region": r, "city": ci}
            for c, n, s, st, r, ci in INSTITUTIONS
        ],
        "programmes": programmes_out,
        "identities": {
            "registry_size": len(registry),
            "inactive": len(sorted_ids[:12]),
            "unknown_valid_format": len(unknown_ids),
            "name_mismatch": len(sorted_ids[12:27]),
            "dob_mismatch": len(sorted_ids[27:39]),
        },
    }
    (out_dir.parent / "ground_truth.json").write_text(
        json.dumps(ground_truth, indent=2, sort_keys=True), encoding="utf-8"
    )
    return ground_truth


def make_student(rng, fake, code, prog, category, anomaly_codes, shared_phone_codes, skew_codes) -> dict:
    admission = admission_date(rng, code in anomaly_codes)
    name = fake.name()
    dob = date(2004 + rng.randint(0, 4), 1 + rng.randint(0, 11), 1 + rng.randint(0, 27))
    nationality = "India"
    if category == "fn":
        nationality = rng.choice(["Nepal", "Bhutan", "Sri Lanka", "Kenya"])
    if category in {"nri", "oci"}:
        nationality = rng.choice(["UAE", "USA", "Singapore", "Oman"])
    row = {
        "_seq": len(fake.name()) * 0 + rng.randint(100000, 899999),
        "_institution": code,
        "_programme_obj": prog,
        "name": transliterate(name, rng),
        "dob": dob,
        "apaar_id": make_registry_id(rng),
        "apaar_status": "provided",
        "programme_code": prog["code"],
        "seat_category": category,
        "admission_date": admission,
        "admission_mode": rng.choice(["counselling", "institute_level", "management"]),
        "gender": rng.choice(["M", "F"]),
        "phone": f"9{rng.randint(100000000, 999999999)}",
        "email": f"synthetic.{rng.randint(1000, 9999)}@example.invalid",
        "nationality": nationality,
        "qualifying_exam_pct": round(rng.uniform(45, 98), 1),
        "_flag": None,
    }
    return row


def write_file(path: Path, headers: list[str], rows: list[dict]) -> None:
    if path.suffix == ".xlsx":
        from datetime import datetime as dt

        from openpyxl import Workbook

        wb = Workbook()
        wb.properties.creator = "APAAR-Setu synthetic generator"
        wb.properties.lastModifiedBy = "APAAR-Setu synthetic generator"
        wb.properties.created = dt(2026, 1, 1, 0, 0, 0)
        wb.properties.modified = dt(2026, 1, 1, 0, 0, 0)
        ws = wb.active
        ws.append(headers)
        for row in rows:
            ws.append(row_values(row))
        wb.save(path)
        normalize_xlsx_zip(path)
        return
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(headers)
        for row in rows:
            writer.writerow(row_values(row))


def normalize_xlsx_zip(path: Path) -> None:
    """Give every zip member a fixed timestamp so repeated runs are byte-identical."""
    import zipfile

    with zipfile.ZipFile(path) as source:
        members = [(info.filename, source.read(info.filename)) for info in source.infolist()]
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as target:
        for name, data in members:
            if name == "docProps/core.xml":
                text = data.decode("utf-8")
                text = re.sub(
                    r"<dcterms:modified[^>]*>.*?</dcterms:modified>",
                    '<dcterms:modified xmlns:dcterms="http://purl.org/dc/terms/" '
                    'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
                    'xsi:type="dcterms:W3CDTF">2026-01-01T00:00:00Z</dcterms:modified>',
                    text,
                )
                data = text.encode("utf-8")
            info = zipfile.ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o600 << 16
            target.writestr(info, data)


def row_values(row: dict) -> list:
    programme_label = row["_programme_obj"]["code"]
    values = {
        "name": row["name"],
        "dob": row["dob"].isoformat(),
        "apaar_id": row.get("apaar_id", ""),
        "apaar_status": row.get("apaar_status", ""),
        "programme": programme_label,
        "seat_category": row["seat_category"],
        "admission_date": row["admission_date"].isoformat(),
        "admission_mode": row["admission_mode"],
        "gender": row["gender"],
        "phone": row["phone"],
        "email": row["email"],
        "nationality": row["nationality"],
        "qualifying_exam_pct": row["qualifying_exam_pct"],
        "remarks": row.get("remarks", ""),
    }
    return [values[field] for field in FIELD_ORDER]


def read_written_rows(path: Path) -> list[list]:
    if path.suffix == ".xlsx":
        from openpyxl import load_workbook

        wb = load_workbook(path, read_only=True, data_only=True)
        ws = wb.active
        rows = [list(r) for r in ws.iter_rows(values_only=True)]
        return rows[1:]
    with path.open(encoding="utf-8", newline="") as fh:
        rows = list(csv.reader(fh))
    return rows[1:]


def derive_counts(files: list[dict], out_dir: Path) -> tuple[dict, dict]:
    """Independent expected counts computed from the files, not from engine output."""
    counts: dict[tuple[str, str], dict[str, int]] = {}
    rejected = accepted = enrolments = repeated = 0
    for meta in files:
        seen: set[str] = set()
        for row in read_written_rows(out_dir / meta["filename"]):
            apaar = re.sub(r"[\s-]", "", str(row[2] or ""))
            if apaar and not re.match(r"^\d{12}$", apaar):
                rejected += 1
                continue
            accepted += 1
            if apaar and apaar in seen:
                repeated += 1
                continue
            if apaar:
                seen.add(apaar)
            enrolments += 1
            programme = str(row[4] or "").strip()
            category = str(row[5] or "").strip().lower() or "regular"
            bucket = counts.setdefault((meta["institution_code"], programme), {})
            bucket[category] = bucket.get(category, 0) + 1
    return counts, {
        "rejected": rejected,
        "accepted": accepted,
        "enrolments": enrolments,
        "repeated": repeated,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out", default=str(ROOT / "data" / "synthetic"))
    args = parser.parse_args()
    truth = generate(args.seed, Path(args.out))
    print(json.dumps(truth["totals"], indent=2))
    print(json.dumps(truth["seeded"]["over_intake"], indent=2))


if __name__ == "__main__":
    main()
