# Open questions and assumptions log
Agents append here. Format: `date | phase | assumption/question | where used | who must confirm`.

2026-10-31 | 1 | Official problem statement text is still pending (`docs/00-problem-statement.md` contains placeholders). Built to the team blueprint instead. | whole build | team / policy handbook
2026-10-31 | 1 | APAAR format assumed 12 digits (`^[0-9]{12}$`). | row validation, mock registry | AICTE/ABC handbook
2026-10-31 | 1 | Admission window assumed 2026-06-01 → 2026-11-30. | `LATE_ADMISSION`, anomaly features | AICTE APH
2026-10-31 | 1 | Approved intake values are synthetic seed data, not AICTE figures. | intake counters, dashboards | team
2026-10-31 | 1 | Supernumerary cap assumed 10% of approved intake; NRI/OCI/FN caps assumed 5% each; TFW left `null` on purpose. All are `status: assumption`. | seat cap findings, UI chips | AICTE APH
2026-10-31 | 2 | Demo corpus uses 12 institutions / 1,652 rows instead of the ~6,000-row design target, to keep the full pipeline seed fast. | `data/synthetic`, evaluation | team
2026-10-31 | 2 | Identity lookups are served only by `mock_apaar_registry`; no real APAAR/ABC/DigiLocker endpoint was invented. | `APAAR_*` findings, verification narrative | team / government access
2026-10-31 | 3 | "Same programme + academic year" is the key for same-institution duplicates; legitimate dual degrees are detected from an institution remarks field containing "dual degree" and whitelisted. | duplicate detection | AICTE policy
2026-10-31 | 4 | IsolationForest contamination 0.1 and the feature list are prototype assumptions; with fewer than 8 institutions the engine falls back to a robust z-score. | anomaly queue | team
2026-10-31 | 4 | Fuzzy matching compares DOB and blocked name similarity (≥ 90) and suppresses pairs already covered by an exact identifier match. | duplicate detection | team
2026-10-31 | 5 | Copilot uses five fixed, parameterised tools and a keyword router; it returns `llm_used: false` and never generates statistics. | AICTE console | team
2026-10-31 | 6 | Credentials are described as "VC-style signed records" only; no W3C conformance is claimed. No name/DOB/APAAR is embedded. | certificates, verify page | team
2026-10-31 | 6 | Consent share tokens are single-purpose, expire with the request (default 15 minutes), and are shown once to the student. | consent flow | team / legal review
2026-10-31 | UI | No usable Lottie JSON files were present in the repository (only Meteocons weather configs), so SVG illustrations + CSS motion are used. | landing, empty states | team / design
2026-10-31 | 7 | The optional ERP connector and LLM providers are not built; `LLM_PROVIDER=none` is the tested default. | whole product | team
