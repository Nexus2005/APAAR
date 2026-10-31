from __future__ import annotations

from collections.abc import Callable

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.db import get_db
from app.core.security import read_session
from app.models import Institution, User

INSTITUTION_ROLES = {"institution_operator", "institution_admin"}


def current_user(request: Request, db: Session = Depends(get_db)) -> User:
    token = request.cookies.get(get_settings().cookie_name)
    payload = read_session(token)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not signed in.")
    user = db.get(User, int(payload.get("uid", 0)))
    if user is None or not user.active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session is no longer valid.")
    return user


def require_roles(*roles: str) -> Callable:
    def dependency(user: User = Depends(current_user)) -> User:
        if roles and user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Your role is not allowed to perform this action.",
            )
        return user

    return dependency


def ensure_institution_access(user: User, institution_id: int | None) -> None:
    if user.role in {"central_reviewer", "sysadmin"}:
        return
    if user.role in INSTITUTION_ROLES:
        if institution_id is None or user.institution_id != institution_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only access your own institution.",
            )
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed for this role.")


def institution_for_user(db: Session, user: User) -> Institution:
    if user.institution_id is None:
        raise HTTPException(status_code=400, detail="This account is not attached to an institution.")
    ensure_institution_access(user, user.institution_id)
    institution = db.get(Institution, user.institution_id)
    if institution is None:
        raise HTTPException(status_code=404, detail="Institution not found.")
    return institution
