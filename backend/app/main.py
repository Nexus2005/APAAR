from __future__ import annotations

import time
from collections import defaultdict
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api import audit, auth, consent, credentials, dashboard, duplicates, findings, institutions, uploads
from app.core.config import PROJECT_ROOT, get_settings
from app.core.db import Base, SessionLocal, engine
from app.core.security import csrf_matches
from app.services.audit import verify_chain

settings = get_settings()
FRONTEND_DIST = PROJECT_ROOT / "frontend" / "dist"
_login_attempts: dict[str, list[float]] = defaultdict(list)
_verify_attempts: dict[str, list[float]] = defaultdict(list)


def _rate_limited(bucket: dict[str, list[float]], key: str, limit: int, window: float = 60.0) -> bool:
    now = time.time()
    bucket[key] = [t for t in bucket[key] if now - t < window]
    if len(bucket[key]) >= limit:
        return True
    bucket[key].append(now)
    return False


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    if settings.seed_on_startup and settings.demo_mode:
        from sqlalchemy import select

        from app.models import Institution

        with SessionLocal() as db:
            if db.scalars(select(Institution).limit(1)).first() is None:
                from app.seed.demo import seed_demo

                seed_demo(db)
    yield


app = FastAPI(
    title="APAAR-Setu",
    description=(
        "Enrolment integrity prototype on SYNTHETIC data. Mock APAAR adapter only. "
        "Not an official AICTE or APAAR service."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", settings.public_base_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def security_middleware(request: Request, call_next):
    if (
        request.method in {"POST", "PUT", "PATCH", "DELETE"}
        and request.url.path.startswith("/api/v1")
        and not request.url.path.endswith("/auth/login")
        and request.cookies.get(settings.cookie_name)
    ):
        header = request.headers.get("X-CSRF-Token")
        cookie = request.cookies.get(settings.csrf_cookie)
        if not csrf_matches(cookie, header):
            return JSONResponse(
                status_code=403,
                content={"error": {"code": "CSRF_FAILED", "message": "Missing or invalid CSRF token."}},
            )
    if request.url.path in {"/api/v1/auth/login"}:
        client = request.client.host if request.client else "unknown"
        if _rate_limited(_login_attempts, client, limit=20):
            return JSONResponse(
                status_code=429,
                content={"error": {"code": "RATE_LIMITED", "message": "Too many login attempts. Wait a minute."}},
            )
    is_verify = request.url.path.startswith("/api/v1/verify/")
    is_qr = request.url.path.startswith("/api/v1/credentials/") and request.url.path.endswith("/qr.png")
    if is_verify or is_qr:
        client = request.client.host if request.client else "unknown"
        if _rate_limited(_verify_attempts, client, limit=120):
            return JSONResponse(
                status_code=429,
                content={"error": {"code": "RATE_LIMITED", "message": "Too many verification attempts."}},
            )

    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Cache-Control"] = "no-store" if request.url.path.startswith("/api/") else "no-cache"
    return response


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    message = exc.detail if isinstance(exc.detail, str) else "Request failed."
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": f"HTTP_{exc.status_code}",
                "message": message,
                "details": exc.detail if not isinstance(exc.detail, str) else {},
            }
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Some fields are invalid.",
                "details": exc.errors(),
            }
        },
    )


@app.get("/api/v1/health")
def health() -> dict:
    return {"status": "ok", "app": "APAAR-Setu", "simulated": True}


@app.get("/api/v1/audit-integrity")
def audit_integrity_public() -> dict:
    with SessionLocal() as db:
        return verify_chain(db)


for router in (
    auth.router,
    institutions.router,
    uploads.router,
    findings.router,
    dashboard.router,
    duplicates.router,
    credentials.router,
    consent.router,
    audit.router,
):
    app.include_router(router, prefix="/api/v1")

if (FRONTEND_DIST / "assets").exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")


@app.get("/{full_path:path}", include_in_schema=False)
def spa(full_path: str):
    if full_path.startswith("api/"):
        return JSONResponse(status_code=404, content={"error": {"code": "NOT_FOUND", "message": "Unknown API route."}})
    candidate = FRONTEND_DIST / full_path
    if full_path and candidate.is_file():
        return FileResponse(candidate)
    index = FRONTEND_DIST / "index.html"
    if index.exists():
        return FileResponse(index)
    return JSONResponse(
        status_code=200,
        content={
            "app": "APAAR-Setu",
            "message": "Frontend not built. Run `npm --prefix frontend run dev` or build it.",
            "api": "/api/v1/health",
        },
    )
