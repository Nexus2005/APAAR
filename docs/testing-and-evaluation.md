# Testing and evaluation — measured results

All numbers below were produced on **31 October 2026** on the development machine
(Windows, Python 3.11.9, Node 24, SQLite for the local demo; the Docker image targets
Python 3.12 + PostgreSQL 16). They describe a **synthetic prototype**, not the real
APAAR/AICTE estate.

Reproduce:

```bash
make generate            # deterministic synthetic files + ground truth
make seed                # reset data/app.db and ingest every file through the real pipeline
make test                # pytest (backend) + vitest (frontend)
make evaluate            # scripts/evaluate.py --stage all
python scripts/benchmark_ingest.py   # 5,000-row ingestion timing
```

The raw evaluation output used for this document is generated to stdout only — do not copy
numbers from slides unless they appear here with this command.

## 1. Deterministic synthetic data

`python scripts/generate_synthetic.py --seed 42` twice produces **byte-identical** CSV,
XLSX and `ground_truth.json` output (verified with `diff -r` and asserted by
`tests/test_synthetic.py::test_generation_is_byte_identical_twice`).

| Measure | Value |
|---|---|
| Institutions | 12 (4 states) |
| Programmes | 32 |
| Rows written | 1,652 |
| Accepted rows | 1,502 |
| Rejected rows (malformed APAAR) | 150 |
| Repeated-APAAR rows (counted once) | 40 |
| Enrolments created | 1,462 |

Design deviation: the phase plan suggested ~6,000 students. The demo uses 1,652 rows so the
full seed (12 files → validation → findings → duplicates → anomaly → credentials) completes
quickly on a laptop. The pipeline is row-count agnostic; the benchmark below exercises 5,000 rows.

## 2. Column mapping (`evaluate.py --stage mapping`)

| Measure | Value |
|---|---|
| Required fields | name, dob, programme, seat_category, admission_date |
| Files evaluated | 12 (CSV + 2 XLSX, five header styles) |
| Mean required-field mapping accuracy | **100.0%** |
| Per-file accuracy | 100.0% on all 12 files |

Confidence comes from the alias dictionary plus RapidFuzz; the uploaded file is never mapped
silently — an operator confirms every field in the wizard.

## 3. Row validation and rules (`--stage rules`)

| Measure | Expected | Measured |
|---|---|---|
| Rejected rows | 150 | **150** |
| `APAAR_FORMAT` rejections | 150 | **150** |
| `REQUIRED_FIELD_MISSING` rejections | 0 | **0** |
| `INTAKE_EXCEEDED` precision | 100% | **100.0%** |
| `INTAKE_EXCEEDED` recall | 100% | **100.0%** |
| Supernumerary cap breach set | 2 programmes | **exact match** |
| `CATEGORY_INCONSISTENT` findings | 10 | **10** |
| `DATE_IMPLAUSIBLE` findings | 25 | **25** |
| `DUP_IN_FILE` findings | 40 | **40** |
| `APAAR_MISSING` findings | 20 (of 60 missing; 40 in the pending/declined lane) | **20** |
| `APAAR_NOT_FOUND` findings | 10 | **10** |
| `APAAR_INACTIVE` findings | 12 | **12** |
| `IDENTITY_MISMATCH` findings | 27 registry name/DOB mismatches | **28** (one additional name-similarity mismatch) |

Exact intake findings (institution / programme / approved / regular / excess):

| Institution | Programme | Approved | Regular | Excess |
|---|---|---|---|---|
| SYN-MH-001 | MEC | 54 | 70 | 16 |
| SYN-KA-005 | MEC | 72 | 84 | 12 |
| SYN-UP-010 | ECE | 54 | 66 | 12 |

Special categories (supernumerary/NRI/OCI/FN) are **not** counted against regular intake; the
SUPERNUMERARY cap (10% assumption) is checked separately. A `null` cap emits
`SEAT_CAP_NOT_CONFIGURED` and never a number (tested).

## 4. Duplicate detection (`--stage duplicates`)

| Measure | Expected | Measured |
|---|---|---|
| Exact cross-institution links | 35 | **35** |
| Whitelisted legitimate pairs | 5 | **5** |
| Exact-match recall | 100% | **100.0%** |
| Fuzzy links (name ≥ 90 + matching DOB) | 8 | **8** |
| Total duplicate findings (30 exact + 8 fuzzy) | — | **38** |

Two potential fuzzy links were suppressed because both records were already covered by an
exact identifier match. Nothing is auto-rejected; links are review evidence with both records
side by side.

## 5. Anomaly prioritisation (`--stage anomaly`)

| Measure | Value |
|---|---|
| Method | IsolationForest (contamination 0.1, random_state 42), 12 institutions |
| Seeded institutions in top 5 | **3 of 3** (`SYN-TN-008`, `SYN-MH-003`, `SYN-UP-012`) |
| Institutions flagged for review | 4 (the three seeded + `SYN-KA-005`, which uses 85.9% of intake) |
| Reasons per flagged institution | 3 each |
| Reasons containing a number absent from stored features | **0** |
| Reasons ≥ 2 (invariant) | **true** |

The scorer only ranks. The fourth flag is an over-intake college with a genuinely high
utilisation feature; the UI calls this “prioritised for review”, never fraud.

## 6. Trust layer (pytest)

`tests/test_trust.py` proves:

- valid credential → `VALID`; stored claim mutated → `TAMPERED`; revoked → `REVOKED`; unknown id → `NOT_FOUND`;
- credential payload contains no APAAR value, no student name key and no DOB;
- consent shares only the approved allow-list fields, and never name/DOB/APAAR;
- denied consent returns no token/data;
- expired share token returns HTTP 410;
- editing one audit row makes `/audit/verify` report the broken sequence; restoring it returns the chain to valid.

## 7. RBAC / isolation / CSRF (pytest)

- operator of SYN-MH-002 cannot read SYN-MH-001 intake (403/404);
- reviewer sees all 12 institutions; verifier cannot browse enrolments (403);
- unauthenticated `/dashboard/institution` → 401;
- writes without a matching CSRF header → 403;
- an empty comment on a finding action → 422;
- start review → resolve writes history and an audit entry.

## 8. Test totals (actual run)

```text
cd backend && PYTHONPATH=. python -m pytest
31 passed, 1 warning

cd frontend && npm test
Test Files  1 passed (1)
Tests       4 passed (4)

cd backend && PYTHONPATH=. python -m ruff check app tests
All checks passed!

cd frontend && npx tsc -b
(exit 0)

cd frontend && npm run build
✓ built
```

## 9. Ingestion benchmark

`python scripts/benchmark_ingest.py` runs a throwaway SQLite database (it never touches the demo DB).
Measured on 31 Oct 2026:

```json
{
  "rows": 5000,
  "accepted": 5000,
  "rejected": 0,
  "seconds": 4.03,
  "rows_per_second": 1242.2,
  "scope": "parse + validate + person/enrolment writes + audit (SQLite, local laptop)"
}
```

The benchmark covers parsing, mapping, validation, person/enrolment writes and the audit entry —
**4.03 s for 5,000 rows**, inside the 10 s phase target on this machine. Findings, duplicate
matching and anomaly recomputation run after ingestion and are not included in that timer.
PostgreSQL latency will differ; re-run the script on the target machine before quoting a number.

## 10. Environment note

`docker compose config` validates, but the Docker image was **not built** on the development
machine because the Docker Desktop daemon was not running (`failed to connect to the docker API`).
The local uvicorn + built SPA path was verified instead. Run `docker compose up --build` on a
machine with a running daemon before claiming a Docker deployment.

## 11. What is NOT claimed

- No measurement against real AICTE/APAAR data exists. All evaluation is against seeded ground truth.
- Identity lookups are SIMULATED (`mock_apaar_registry`) and labelled everywhere.
- No W3C VC conformance claim; records are “VC-style signed records”.
- The anomaly model is prioritisation only; it does not establish misconduct.
- The ERP connector and LLM layer are not built (optional Phase 7); `LLM_PROVIDER=none` is the default and every tested path works without an LLM.
