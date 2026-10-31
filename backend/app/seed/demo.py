"""Seed a deterministic, fully synthetic demo database through the real pipeline."""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import PROJECT_ROOT, load_rules
from app.core.crypto import encrypt_text
from app.core.security import hash_password
from app.models import (
    ConsentRequest,
    Enrolment,
    Institution,
    IntakeApproval,
    MockApaarRegistry,
    Person,
    Programme,
    RuleVersion,
    User,
)
from app.services.anomaly import recompute
from app.services.audit import append_audit
from app.services.credentials import generate_institution_keys, issue_credential
from app.services.duplicates import detect_exact, detect_fuzzy
from app.services.findings_engine import refresh_institution
from app.services.ingestion import ingest, preview
from app.services.mapping import parse_date

DEMO_PASSWORD = "demo1234"
DATA_DIR = PROJECT_ROOT / "data" / "synthetic"
GT_PATH = PROJECT_ROOT / "data" / "ground_truth.json"


def ensure_synthetic_data() -> dict:
    if not GT_PATH.exists() or not DATA_DIR.exists():
        sys.path.insert(0, str(PROJECT_ROOT))
        from scripts.generate_synthetic import generate

        generate(42, DATA_DIR)
    return json.loads(GT_PATH.read_text(encoding="utf-8"))


def _user(
    db: Session,
    email: str,
    name: str,
    role: str,
    institution_id: int | None = None,
    person_id: int | None = None,
) -> User:
    existing = db.scalars(select(User).where(User.email == email)).first()
    if existing:
        return existing
    user = User(
        email=email,
        name=name,
        password_hash=hash_password(DEMO_PASSWORD),
        role=role,
        institution_id=institution_id,
        person_id=person_id,
    )
    db.add(user)
    db.flush()
    return user


def seed_demo(db: Session, force: bool = False) -> dict:
    if db.scalars(select(Institution).limit(1)).first() and not force:
        return {"seeded": False, "reason": "database already contains institutions"}

    ground_truth = ensure_synthetic_data()
    rules = load_rules()
    version = db.scalars(select(RuleVersion).where(RuleVersion.version == rules["version"])).first()
    if version is None:
        version = RuleVersion(
            version=int(rules["version"]),
            effective_from=parse_date(rules["effective_from"]),
            config_json=json.dumps(rules, sort_keys=True),
            created_by="seed",
            note="Seeded from config/rules.yaml (all values assumptions unless marked)",
        )
        db.add(version)
        db.flush()

    institutions: dict[str, Institution] = {}
    for meta in ground_truth["institutions"]:
        public_key, private_key = generate_institution_keys()
        institution = Institution(
            aicte_code=meta["code"],
            name=meta["name"],
            short_name=meta["short_name"],
            state=meta["state"],
            region=meta["region"],
            city=meta["city"],
            status="active",
            public_key=public_key,
            private_key_enc=encrypt_text(private_key),
        )
        db.add(institution)
        db.flush()
        institutions[meta["code"]] = institution
        append_audit(
            db,
            action="institution.created",
            resource=f"institution:{institution.id}",
            detail={"code": institution.aicte_code, "simulated": True},
            actor_name="seed",
        )

    programmes: dict[tuple[str, str], Programme] = {}
    for meta in ground_truth["programmes"]:
        institution = institutions[meta["institution_code"]]
        programme = Programme(
            institution_id=institution.id,
            code=meta["code"],
            name=meta["name"],
            level=meta["level"],
            discipline_group=meta["discipline_group"],
            shift=meta["shift"],
            duration_years=meta["duration_years"],
        )
        db.add(programme)
        db.flush()
        db.add(
            IntakeApproval(
                programme_id=programme.id,
                academic_year=ground_truth["academic_year"],
                approved_intake=meta["approved_intake"],
                rule_version_id=version.id,
            )
        )
        programmes[(meta["institution_code"], meta["code"])] = programme
    db.flush()

    operators: dict[str, User] = {}
    for code, institution in institutions.items():
        operators[code] = _user(
            db,
            f"operator.{code.lower()}@demo.apaar-setu.invalid",
            f"Operator — {institution.short_name}",
            "institution_operator",
            institution.id,
        )
    admin = _user(
        db,
        "admin.syn-mh-001@demo.apaar-setu.invalid",
        "Dr. Ananya Kulkarni",
        "institution_admin",
        institutions["SYN-MH-001"].id,
    )
    _reviewer = _user(
        db, "reviewer@aicte.demo.apaar-setu.invalid", "R. Menon (AICTE reviewer)", "central_reviewer"
    )
    verifier = _user(
        db, "verifier@bank.demo.apaar-setu.invalid", "K. Iyer (verifier, Demo Bank)", "verifier"
    )
    sysadmin = _user(db, "sysadmin@demo.apaar-setu.invalid", "Policy administrator", "sysadmin")
    db.flush()

    registry = json.loads((DATA_DIR / "mock_registry.json").read_text(encoding="utf-8"))
    for entry in registry:
        db.add(
            MockApaarRegistry(
                apaar_id=entry["apaar_id"],
                name=entry["name"],
                dob=parse_date(entry["dob"]),
                status=entry["status"],
                simulated=True,
            )
        )
    db.flush()

    # Ingest every seeded file through the real upload pipeline.
    for file_meta in ground_truth["files"]:
        institution = institutions[file_meta["institution_code"]]
        path: Path = DATA_DIR / file_meta["filename"]
        data = path.read_bytes()
        preview_payload = preview(file_meta["filename"], data)
        mapping = preview_payload["suggested_mapping"]
        _batch, _duplicate = ingest(
            db,
            user=operators[file_meta["institution_code"]],
            institution=institution,
            filename=file_meta["filename"],
            data=data,
            mapping=mapping,
        )
        refresh_institution(db, institution.id)
        db.commit()

    detect_exact(db)
    detect_fuzzy(db)
    recompute(db)
    db.commit()

    # Demo student linked to a real seeded enrolment.
    student_person = db.scalars(
        select(Person)
        .join(Enrolment, Enrolment.person_id == Person.id)
        .where(
            Enrolment.institution_id == institutions["SYN-MH-001"].id,
            Person.apaar_hmac.is_not(None),
            Enrolment.status == "admitted",
        )
        .limit(1)
    ).first()
    _student = _user(
        db,
        "student@demo.apaar-setu.invalid",
        f"{student_person.name_display} (demo student)" if student_person else "Demo student",
        "student",
        institutions["SYN-MH-001"].id,
        student_person.id if student_person else None,
    )
    db.flush()

    # Two verifiable records that can be demonstrated end to end.
    if student_person:
        enrolments = list(
            db.scalars(
                select(Enrolment).where(
                    Enrolment.institution_id == institutions["SYN-MH-001"].id,
                    Enrolment.status == "admitted",
                    Enrolment.person_id == student_person.id,
                )
            )
        )
        for enrolment in enrolments[:1]:
            credential = issue_credential(db, enrolment, institutions["SYN-MH-001"])
            append_audit(
                db,
                action="credential.issued",
                resource=f"credential:{credential.credential_id}",
                actor=admin,
                detail={"enrolment_ref": enrolment.enrolment_ref, "simulated": True},
            )
        other = db.scalars(
            select(Enrolment)
            .where(
                Enrolment.institution_id == institutions["SYN-MH-001"].id,
                Enrolment.status == "admitted",
            )
            .order_by(Enrolment.id)
            .limit(2)
        ).all()
        for enrolment in other:
            if enrolment.person_id == student_person.id:
                continue
            credential = issue_credential(db, enrolment, institutions["SYN-MH-001"])
            append_audit(
                db,
                action="credential.issued",
                resource=f"credential:{credential.credential_id}",
                actor=admin,
                detail={"enrolment_ref": enrolment.enrolment_ref, "simulated": True},
            )
            break

    if student_person:
        db.add(
            ConsentRequest(
                verifier_id=verifier.id,
                verifier_name=verifier.name,
                subject_person_id=student_person.id,
                fields=json.dumps(["enrolled", "programme", "academic_year", "institution"]),
                purpose="Employment eligibility check (demo)",
                status="pending",
                expires_at=datetime(2026, 12, 31, 23, 59),
            )
        )
    append_audit(
        db,
        action="demo.seeded",
        resource="system",
        detail={
            "institutions": len(institutions),
            "programmes": len(programmes),
            "uploads": len(ground_truth["files"]),
            "simulated": True,
        },
        actor=sysadmin,
    )
    db.commit()

    return {
        "seeded": True,
        "institutions": len(institutions),
        "programmes": len(programmes),
        "users": 6 + len(operators),
        "rows": ground_truth["totals"]["rows_written"],
        "password": DEMO_PASSWORD,
    }


def seed_cli() -> None:  # pragma: no cover
    from app.core.db import Base, SessionLocal, engine

    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        result = seed_demo(db, force=True)
        print(json.dumps(result, indent=2))


if __name__ == "__main__":  # pragma: no cover
    seed_cli()
