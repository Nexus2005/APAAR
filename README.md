# APAAR

> **Institutional Enrolment Integrity & Student Identity Attestation Platform**  
> *A robust, human-in-the-loop regulatory compliance and verification suite designed for higher education admission governance.*

[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-19.0-61DAFB.svg?logo=react&logoColor=black)](https://react.dev)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.6-3178C6.svg?logo=typescript&logoColor=white)](https://www.typescriptlang.org)
[![Tailwind CSS](https://img.shields.io/badge/TailwindCSS-4.0-38B2AC.svg?logo=tailwind-css&logoColor=white)](https://tailwindcss.com)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0-D71F00.svg)](https://www.sqlalchemy.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

---

> [!NOTE]
> **SIMULATED PROTOTYPE — SYNTHETIC DATA DEMONSTRATION**  
> This platform is an engineering demonstration evaluated on deterministic synthetic admission datasets. All personal identities, institutional intake quotas, and identity provider records are generated for simulation purposes. All external verification adapters operate under simulated conditions with zero exposure of actual PII.

---

## 📌 Executive Summary

Modern higher-education admissions require strict adherence to regulatory sanctions, sanctioned seat limits, category caps, and identity integrity. **APAAR-Setu** provides an end-to-end framework enabling institutions and central regulatory authorities to:

1. **Ingest & Validate Admission Batches:** Flexible schema mapping supporting heterogeneous spreadsheet headers (CSV/XLSX) with fuzzy column resolution and row-level validation.
2. **Deterministic Rules & Intake Compliance:** Real-time quota enforcement differentiating regular intake from supernumerary, NRI, OCI, FN, and TFW quotas.
3. **Cross-Institution Duplicate Resolution:** Detecting concurrent enrolments across multiple institutions via exact identifier fingerprints and blocked fuzzy identity matching.
4. **Explainable Anomaly Prioritisation:** Unsupervised outlier detection (`IsolationForest`) ranking institutions for human audit with mathematically traceable, plain-language justification.
5. **Privacy-Preserving Attestations:** Ed25519-signed QR enrolment credentials enabling offline authenticity checks without leaking student names, dates of birth, or identification numbers.
6. **Student-Controlled Consent Delegation:** Fine-grained authorization allowing students to share selective admission verification tokens with third parties.
7. **Tamper-Evident Audit Chain:** Append-only SHA-256 hash-chained ledger guaranteeing chronological integrity across all administrative operations.

---

## 📸 Platform Walkthrough & Screenshots

### 1. Landing & Role-Based Authentication
Modern landing portal outlining system architecture, regulatory boundaries, and role-based login interfaces for college administrators, operators, central reviewers, students, and third-party verifiers.

| Landing Portal | Multi-Role Authentication |
|---|---|
| ![Landing Portal](<images/Screenshot 2026-10-31 214155.png>) | ![Role Authentication](<images/Screenshot 2026-10-31 214214.png>) |

---

### 2. College Administration & Intake Governance
Institutional dashboard displaying admitted student metrics, compliance alerts, and program-by-program intake utilisation against approved regulatory quotas.

| Intake Metrics & Status | Programme Utilisation Drilldown |
|---|---|
| ![College Dashboard](<images/Screenshot 2026-10-31 214224.png>) | ![Programme Intake](<images/Screenshot 2026-10-31 214233.png>) |

---

### 3. Ingestion Pipeline & Schema Normalisation
Multi-step upload wizard handling multi-format files (CSV/XLSX) with alias matching, confidence scoring, manual confirmation, and batch error triage.

| Upload Wizard | Fuzzy Column Mapping | Batch Row Validation |
|---|---|---|
| ![Upload Wizard](<images/Screenshot 2026-10-31 214250.png>) | ![Column Mapping](<images/Screenshot 2026-10-31 214301.png>) | ![Row Validation](<images/Screenshot 2026-10-31 214311.png>) |

---

### 4. Regulatory Findings & Human Review Workflow
Actionable finding cards detailing rule codes, quantitative evidence, policy references, and audit-logged human resolution actions.

| Findings Queue | Finding Inspection & Resolution |
|---|---|
| ![Findings Queue](<images/Screenshot 2026-10-31 214321.png>) | ![Review Modal](<images/Screenshot 2026-10-31 214330.png>) |

---

### 5. Multi-Institution Duplicate Enrolment Resolution
Side-by-side comparative inspection highlighting simultaneous admissions across universities, with whitelist management for recognized dual-degree programs.

| Duplicate Pairs Overview | Side-by-Side Comparison |
|---|---|
| ![Duplicate Links](<images/Screenshot 2026-10-31 214339.png>) | ![Duplicate Comparison](<images/Screenshot 2026-10-31 214350.png>) |

---

### 6. Central Regulatory Review & Anomaly Detection
Central monitoring dashboard with state-wise analytics, unsupervised anomaly prioritisation, and an explainable breakdown of institutional divergence.

| Central Console | Anomaly Ranking Queue | Explainable Reasons |
|---|---|---|
| ![Central Console](<images/Screenshot 2026-10-31 214400.png>) | ![Anomaly Queue](<images/Screenshot 2026-10-31 214412.png>) | ![Anomaly Breakdown](<images/Screenshot 2026-10-31 214424.png>) |

| Audit Trail | Regulatory Intelligence Query |
|---|---|
| ![Audit Trail](<images/Screenshot 2026-10-31 214436.png>) | ![Query Assistant](<images/Screenshot 2026-10-31 214449.png>) |

---

### 7. Verifiable Credentials & Instant QR Verification
Ed25519 cryptographic credential signing for admitted students. QR codes link directly to tamper-evident verification endpoints supporting instant status updates and revocation.

| Credential Issuance | Public Verification (VALID) | Revocation State (REVOKED) |
|---|---|---|
| ![Credential Issue](<images/Screenshot 2026-10-31 214600.png>) | ![Verification Valid](<images/Screenshot 2026-10-31 214612.png>) | ![Verification Revoked](<images/Screenshot 2026-10-31 214624.png>) |

---

### 8. Student Privacy & Selective Consent Delegation
Students retain sovereign control over third-party verifier requests, generating time-bound, single-use tokens that reveal only authorized status attributes without sensitive identity data.

| Consent Requests | Verifier Token Entry | Verified Minimal Disclosure |
|---|---|---|
| ![Student Consent](<images/Screenshot 2026-10-31 214645.png>) | ![Verifier Portal](<images/Screenshot 2026-10-31 214709.png>) | ![Minimal Disclosure](<images/Screenshot 2026-10-31 214728.png>) |

---

### 9. Tamper-Evident Cryptographic Ledger
Append-only SHA-256 hash-chained log securing every administrative transition. Any retroactive record alteration is instantly detected and pinpointed.

| Intact Audit Chain | Tamper Detection Proof |
|---|---|
| ![Valid Chain](<images/Screenshot 2026-10-31 214737.png>) | ![Tamper Broken Sequence](<images/Screenshot 2026-10-31 214745.png>) |

| Policy Engine Configuration | System Architecture Summary |
|---|---|
| ![Policy Config](<images/Screenshot 2026-10-31 214753.png>) | ![Architecture Summary](<images/Screenshot 2026-10-31 214801.png>) |

---

## 🏗️ Repository Structure

```text
APAAR/
├── backend/
│   ├── app/
│   │   ├── adapters/        # Mock identity provider adapters (SIMULATED)
│   │   ├── api/             # FastAPI REST endpoints (v1 routes)
│   │   ├── core/            # Configuration, database session, crypto utilities
│   │   ├── models/          # SQLAlchemy 2.0 ORM schemas
│   │   ├── schemas/         # Pydantic v2 validation contracts
│   │   ├── seed/            # Deterministic synthetic data seeding pipeline
│   │   └── services/        # Ingestion, rules, duplicates, anomaly, credentials
│   ├── tests/               # Pytest suite (31 unit & integration tests)
│   └── pyproject.toml       # Python packaging and dependency declarations
├── frontend/
│   ├── src/
│   │   ├── components/      # Reusable UI component library (design system)
│   │   ├── lib/             # API client, auth context, utility formatters
│   │   ├── pages/           # Route views (Landing, Dashboards, Upload, Audit)
│   │   ├── App.tsx          # Router configuration and global provider layout
│   │   └── main.tsx         # Application entry point
│   ├── public/              # SVG illustrations, favicons, static assets
│   ├── package.json         # React 19, Vite, TanStack Query, Tailwind v4
│   └── vite.config.ts       # Vite configuration with API reverse proxy
├── config/
│   ├── rules.yaml           # Versioned regulatory policies and quotas
│   └── column_aliases.yaml  # Header dictionary for automated schema mapping
├── data/
│   ├── synthetic/           # Deterministic admission CSV/XLSX corpora
│   └── ground_truth.json    # Exact expected benchmark metrics
├── images/                  # Platform UI screenshots and visual references
├── docs/                    # Architecture blueprints, specifications, demo flow
├── scripts/
│   ├── generate_synthetic.py# Deterministic synthetic dataset generator
│   ├── evaluate.py          # Ground-truth evaluation script
│   ├── benchmark_ingest.py  # High-throughput ingestion benchmark
│   └── tamper_demo.py       # Cryptographic audit tamper demonstration
├── docker-compose.yml       # Production container orchestration
├── Dockerfile               # Multi-stage container build definition
├── Makefile                 # Command shortcuts for setup, testing, and dev
└── .env.example             # Environment configuration template
```

---

## 🚀 Quick Start Guide

### Prerequisites
- **Python**: 3.11 or 3.12
- **Node.js**: v20 or higher (v24 tested)
- **Git**

### Installation & Local Setup

```bash
# 1. Clone the repository
git clone https://github.com/Nexus2005/APAAR.git
cd APAAR

# 2. Setup Backend Dependencies
python -m pip install -r backend/requirements.txt

# 3. Setup Frontend Dependencies
cd frontend
npm install
cd ..

# 4. Generate Synthetic Datasets & Seed Local SQLite Database
python scripts/generate_synthetic.py --seed 42
cd backend
$env:PYTHONPATH="."          # On Windows PowerShell (or export PYTHONPATH=. on bash)
python -m app.seed.demo
cd ..

# 5. Launch Development Servers
# Terminal 1 - Backend (http://127.0.0.1:8000):
cd backend
python -m uvicorn app.main:app --reload --port 8000

# Terminal 2 - Frontend (http://localhost:5173):
cd frontend
npm run dev
```

### Docker Deployment
```bash
docker compose up --build
```
*Spins up a PostgreSQL 16 database and a FastAPI application serving the built production SPA at `http://localhost:8000`.*

---

## 👥 Demo Credentials & Test Accounts

All pre-seeded demo accounts share the uniform password: **`demo1234`**

| Role | Email Identifier | Functional Scope |
|---|---|---|
| **College Admin** | `admin.syn-mh-001@demo.apaar-setu.invalid` | Institution KPIs, intake management, batch uploads, credential issuance |
| **College Operator** | `operator.syn-mh-002@demo.apaar-setu.invalid` | Scoped operator access (multi-tenant isolation verification) |
| **Central Reviewer** | `reviewer@aicte.demo.apaar-setu.invalid` | Pan-institution oversight, anomaly queue, cross-college duplicate review |
| **Student** | `student@demo.apaar-setu.invalid` | Enrolment record portal, verifier consent approvals, one-time token access |
| **Third-Party Verifier** | `verifier@bank.demo.apaar-setu.invalid` | External verification portal using student consent tokens |
| **Policy Admin** | `sysadmin@demo.apaar-setu.invalid` | Versioned regulatory policy management and cryptographic audit inspections |

---

## 🧪 Quality Assurance & Benchmarks

```bash
# Execute Backend Pytest Suite
cd backend && python -m pytest

# Execute Frontend Vitest Suite
cd frontend && npm test

# Run Ground-Truth Evaluation
python scripts/evaluate.py --stage all

# Run Ingestion Benchmark (5,000 rows)
python scripts/benchmark_ingest.py
```

### Verified Benchmark Metrics
- **Schema Mapping Accuracy:** 100% across diverse spreadsheet header formats.
- **Intake Breach Recall:** 100% precision & recall identifying institutional over-admissions.
- **Cross-Institution Duplicate Recall:** 100% recall on seeded cross-enrolments.
- **High-Throughput Ingestion:** >1,200 rows/second on standard workstation hardware.
- **Cryptographic Trust Proofs:** Zero student PII exposed in credential payloads or audit chains.

---

## 🔐 Security & Privacy Architecture

- **Argon2id Password Hashing:** Modern memory-hard hashing for user authentication.
- **Strict Role-Based Access Control (RBAC):** Deny-by-default route enforcement with tenant-scoped isolation.
- **Keyed-HMAC Identifier Masking:** Student identification numbers are encrypted at rest and queried strictly via deterministic HMAC digests.
- **HttpOnly Cookie Sessions:** Secure session cookies paired with anti-CSRF token verification on state-modifying requests.
- **Parameterised Query Tools:** Natural language query routing dispatches to pre-compiled, parameterised queries to prevent SQL injection.

---

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
