from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.db import get_db
from app.core.security import new_csrf_token, sign_session, verify_password
from app.models import Institution, User
from app.schemas import LoginRequest

router = APIRouter(prefix="/auth", tags=["auth"])

DEMO_ACCOUNTS = [
    {"email": "admin.syn-mh-001@demo.apaar-setu.invalid", "label": "College admin", "role": "institution_admin"},
    {
        "email": "operator.syn-mh-002@demo.apaar-setu.invalid",
        "label": "College operator (other college)",
        "role": "institution_operator",
    },
    {"email": "reviewer@aicte.demo.apaar-setu.invalid", "label": "AICTE reviewer", "role": "central_reviewer"},
    {"email": "verifier@bank.demo.apaar-setu.invalid", "label": "Verifier (bank)", "role": "verifier"},
    {"email": "student@demo.apaar-setu.invalid", "label": "Demo student", "role": "student"},
    {"email": "sysadmin@demo.apaar-setu.invalid", "label": "Policy administrator", "role": "sysadmin"},
]


def user_payload(db: Session, user: User) -> dict:
    institution = db.get(Institution, user.institution_id) if user.institution_id else None
    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "role": user.role,
        "institution": (
            {
                "id": institution.id,
                "code": institution.aicte_code,
                "name": institution.name,
                "short_name": institution.short_name,
                "state": institution.state,
            }
            if institution
            else None
        ),
        "person_id": user.person_id,
    }


@router.post("/login")
def login(payload: LoginRequest, response: Response, db: Session = Depends(get_db)) -> dict:
    user = db.scalars(select(User).where(User.email == payload.email.strip().lower())).first()
    if user is None or not user.active or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Email or password is incorrect.")
    settings = get_settings()
    token = sign_session({"uid": user.id, "role": user.role})
    csrf = new_csrf_token()
    response.set_cookie(
        settings.cookie_name,
        token,
        httponly=True,
        samesite="lax",
        secure=settings.app_env == "production",
        max_age=settings.session_ttl_seconds,
        path="/",
    )
    response.set_cookie(
        settings.csrf_cookie,
        csrf,
        httponly=False,
        samesite="lax",
        secure=settings.app_env == "production",
        max_age=settings.session_ttl_seconds,
        path="/",
    )
    from app.services.audit import append_audit

    append_audit(
        db,
        action="auth.login",
        resource=f"user:{user.id}",
        actor=user,
        detail={"role": user.role},
    )
    db.commit()
    return {"user": user_payload(db, user), "csrf_token": csrf, "demo_accounts": DEMO_ACCOUNTS}


@router.post("/logout")
def logout(request: Request, response: Response, db: Session = Depends(get_db)) -> dict:
    settings = get_settings()
    from app.core.security import read_session

    payload = read_session(request.cookies.get(settings.cookie_name))
    if payload:
        user = db.get(User, int(payload.get("uid", 0)))
        if user:
            from app.services.audit import append_audit

            append_audit(db, action="auth.logout", resource=f"user:{user.id}", actor=user)
            db.commit()
    response.delete_cookie(settings.cookie_name, path="/")
    response.delete_cookie(settings.csrf_cookie, path="/")
    return {"ok": True}


@router.get("/me")
def me(request: Request, db: Session = Depends(get_db)) -> dict:
    from app.api.deps import current_user

    user = current_user(request, db)
    csrf = request.cookies.get(get_settings().csrf_cookie) or new_csrf_token()
    return {
        "user": user_payload(db, user),
        "csrf_token": csrf,
        "demo_mode": get_settings().demo_mode,
        "demo_accounts": DEMO_ACCOUNTS if get_settings().demo_mode else [],
        "simulated": True,
    }


@router.get("/demo-accounts")
def demo_accounts() -> dict:
    if not get_settings().demo_mode:
        return {"accounts": []}
    return {"accounts": DEMO_ACCOUNTS, "password": "demo1234"}
