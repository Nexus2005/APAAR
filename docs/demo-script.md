# Demo script — 6 minutes

Everything here runs offline with `LLM_PROVIDER=none` on synthetic data. The ribbon always says
**SIMULATED — NOT OFFICIAL APAAR VERIFICATION**.

## Before you start

```bash
make generate && make seed      # 12 institutions, 32 programmes, 1,652 messy rows
make dev-backend                # http://localhost:8000
make dev-frontend               # http://localhost:5173
```

Demo password for every role: `demo1234`.

## Minutes 0–1 · The college console

1. Open `/` and point at the disclaimer ribbon.
2. Sign in as **College admin** (`admin.syn-mh-001@demo.apaar-setu.invalid`).
3. Land on the college dashboard. Read the KPIs: students admitted, open findings, APAAR
   readiness, seats left.
4. Point at the two programmes with **Over** intake chips, then at the amber assumption chips
   for seat caps. Say: “The number comes from versioned config, not code.”

## Minutes 1–2 · Upload and mapping

5. Go to **Upload data**. Explain that the 12 seeded files use five different header styles.
6. Upload `data/synthetic/SYN-MH-001_admissions_2026-27.csv`.
7. Step 2 shows the mapping with confidence. Change one dropdown to show it is human-confirmed.
8. Process the file. If it was already seeded, show that re-upload is **idempotent**; otherwise
   show accepted/rejected counts and download the error CSV. `APAAR_FORMAT` rows are rejected
   with a message that explicitly says the format check does not prove authenticity.

## Minutes 2–3.5 · Findings and review

9. Open **Findings**. Filter to `INTAKE_EXCEEDED`. Open the MEC finding.
10. Walk through: rule, evidence (approved 54, regular 70, excess 16), why it matters, the policy
    assumption, recommended action, and the history.
11. Start review, add a comment, then resolve with a different comment. Emphasise: every
    transition requires a human comment and writes to the audit chain.
12. Show **Duplicates** side by side (35 exact links, 5 whitelisted dual degrees, 8 fuzzy).

## Minutes 3.5–4.5 · AICTE console

13. Sign in as **AICTE reviewer** (`reviewer@aicte.demo.apaar-setu.invalid`).
14. State the four KPIs and the state utilisation chart.
15. Open **Anomaly queue**. For `SYN-TN-008` read the reasons: final-week share, shared phones.
    Say: “Model ranks; humans decide. Every number in this sentence is stored in the feature JSON.”
16. Ask the copilot: “Which colleges are above intake in Maharashtra?” Point at `tool:` and
    `llm: not used` in the answer footer.

## Minutes 4.5–5.5 · Certificate, QR, consent, audit

17. As **College admin**, open **Certificates**. Issue one for an admitted student, open the QR.
    Note the QR encodes only the verify URL.
18. Open the verify link in a new tab → **VALID**. Revoke it with a reason → refresh → **REVOKED**.
19. Sign in as **Student** (`student@demo.apaar-setu.invalid`). There is a pending verifier request.
    Approve it and copy the one-time token.
20. Sign in as **Verifier** (`verifier@bank.demo.apaar-setu.invalid`), paste the token, and show
    only the approved fields (enrolled, programme, year, institution). No name, DOB or APAAR.
21. Open **Audit trail**. Show “Chain intact”. Optionally run `python scripts/tamper_demo.py --target audit`
    in a terminal, refresh, and show the broken sequence.

## Minutes 5.5–6 · Close

22. Summarise the differentiators: pending/declined lane counted against intake, separate seat
    counters from versioned config, evidence-first human review, signed QR + revoke, consent,
    hash-chained audit, and measured evaluation with honest numbers.
23. State limitations: synthetic data, mock identity provider, no ERP/LLM in the MVP, not an
    official AICTE/APAAR service.

## Backup paths

- If the frontend is not running, use the FastAPI-served build at `http://localhost:8000/`
  after `make build`, or `curl` the documented endpoints.
- If a credential was revoked during rehearsal, reseed with `make seed`.
- Never demo a number that is not in `docs/testing-and-evaluation.md`.
