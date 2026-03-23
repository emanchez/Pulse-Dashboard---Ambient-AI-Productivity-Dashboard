from __future__ import annotations

import json as _json
import secrets
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request as StarletteRequest
import logging

from .core.config import get_settings
from .core.limiter import limiter
from .db.base import Base
from .db.session import engine


# ---------------------------------------------------------------------------
# Request body size limiting middleware (S-13)
# ---------------------------------------------------------------------------

_MAX_BODY_BYTES = 512 * 1024  # 512 KB


class _ContentSizeLimitMiddleware(BaseHTTPMiddleware):
    """Middleware that rejects HTTP requests whose body exceeds *max_bytes*.

    Uses Content-Length as a fast-path check (avoids buffering). For requests
    that lack Content-Length, buffers the body via request.body() and checks
    the total size before passing the request to the next handler.
    """

    def __init__(self, app, max_bytes: int = _MAX_BODY_BYTES) -> None:
        super().__init__(app)
        self._max_bytes = max_bytes

    async def dispatch(self, request: StarletteRequest, call_next):
        # Fast path: Content-Length header check
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                if int(content_length) > self._max_bytes:
                    return JSONResponse(
                        status_code=413,
                        content={"detail": "Request body too large"},
                    )
            except ValueError:
                pass

        # Slow path: buffer body for requests without Content-Length
        # Only applies to methods that typically have a body
        if request.method in ("POST", "PUT", "PATCH"):
            if not content_length:
                body = await request.body()
                if len(body) > self._max_bytes:
                    return JSONResponse(
                        status_code=413,
                        content={"detail": "Request body too large"},
                    )

        return await call_next(request)

# ---------------------------------------------------------------------------
# CSRF protection middleware (double-submit cookie pattern)
# ---------------------------------------------------------------------------

class _CSRFMiddleware(BaseHTTPMiddleware):
    """Validate X-CSRF-Token header against the csrf_token cookie on mutating
    requests.  Disabled in dev mode so the test suite and ``make dev`` work
    without any CSRF overhead.

    /login, /logout, and /health are exempt — the CSRF cookie doesn't exist
    until after the first successful login.
    """

    _SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS", "TRACE"})
    _EXEMPT_PATHS = frozenset({"/login", "/logout", "/health"})

    async def dispatch(self, request: StarletteRequest, call_next):
        from .core.config import get_settings as _gs
        _s = _gs()
        if _s.app_env == "dev" or request.method in self._SAFE_METHODS:
            return await call_next(request)
        if request.url.path in self._EXEMPT_PATHS:
            return await call_next(request)
        csrf_cookie = request.cookies.get("csrf_token")
        csrf_header = request.headers.get("X-CSRF-Token")
        if not csrf_cookie or not csrf_header or not secrets.compare_digest(csrf_cookie, csrf_header):
            return JSONResponse(
                status_code=403,
                content={"detail": "CSRF validation failed"},
            )
        return await call_next(request)


# ---------------------------------------------------------------------------
# HSTS middleware (production only)
# ---------------------------------------------------------------------------

class _HSTSMiddleware(BaseHTTPMiddleware):
    """Add Strict-Transport-Security header on every response in non-dev environments."""

    async def dispatch(self, request: StarletteRequest, call_next):
        response = await call_next(request)
        from .core.config import get_settings as _gs
        if _gs().app_env != "dev":
            response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
        return response


settings = get_settings()

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup guard: prevent accidental deployment with the default dev secret.
    if settings.jwt_secret == "dev-secret-change-me" and settings.app_env != "dev":
        raise RuntimeError(
            "JWT_SECRET must be changed from the default value in non-dev environments. "
            "Set the JWT_SECRET environment variable to a strong random secret."
        )

    # Startup guard: LLM API key required when AI is enabled in non-dev mode.
    settings.validate_llm_config()

    # Startup guard: SQLite must not be used in production.
    settings.validate_database_config()

    # Ensure all registered models have their tables created (idempotent).
    # Only runs in dev mode — in non-dev environments use Alembic migrations.
    # See: code/backend/alembic/ and `alembic upgrade head`.
    if settings.app_env == "dev":
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("DB tables verified/created via create_all (dev mode)")
    else:
        logger.info(
            "Skipping create_all in %s mode — use `alembic upgrade head` for schema changes",
            settings.app_env,
        )
        # Verify database connectivity at startup — surfaces misconfigured DATABASE_URL early.
        from sqlalchemy import text as _text
        try:
            async with engine.connect() as conn:
                await conn.execute(_text("SELECT 1"))
            logger.info("Database connection verified (%s)", settings.app_env)
        except Exception as _e:
            logger.error("Database connection failed at startup: %s", _e)
            raise
    yield


app = FastAPI(title="Ambient AI Productivity Dashboard", lifespan=lifespan)

# ── Rate limiting (S-6, S-7) ──────────────────────────────────────────────
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# ── Sanitized 422 responses (S-14) ────────────────────────────────────────
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: StarletteRequest, exc: RequestValidationError):
    """In prod, hide internal field names; in dev, return full Pydantic error."""
    if settings.app_env != "dev":
        return JSONResponse(status_code=422, content={"detail": "Validation error"})
    # Use jsonable_encoder so Pydantic v2 Url objects in exc.errors() serialize correctly.
    return JSONResponse(status_code=422, content={"detail": jsonable_encoder(exc.errors())})


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"status": "ok"}


# include routers (let import errors surface during startup)
from .api import auth as auth_router
from .api import tasks as tasks_router
from .api import stats as stats_router
from .api import sessions as sessions_router
from .api import reports as reports_router
from .api import system_states as system_states_router
from .middlewares.action_log import ActionLogMiddleware
from .models.session_log import SessionLog as _SessionLog  # noqa: F401 — register with Base.metadata
from .models.manual_report import ManualReport as _ManualReport  # noqa: F401 — register with Base.metadata
from .models.system_state import SystemState as _SystemState  # noqa: F401 — register with Base.metadata
from .models.ai_usage import AIUsageLog as _AIUsageLog  # noqa: F401 — register with Base.metadata
from .models.synthesis import SynthesisReport as _SynthesisReport  # noqa: F401 — register with Base.metadata

app.include_router(auth_router.router)
app.include_router(tasks_router.router)
app.include_router(stats_router.router)
app.include_router(sessions_router.router, prefix="/sessions")
app.include_router(reports_router.router)
app.include_router(system_states_router.router)

from .api import ai as ai_router
app.include_router(ai_router.router)
app.add_middleware(ActionLogMiddleware)
# SlowAPIMiddleware enforces the default_limits=["200 per minute"] global cap (S-7).
# _ContentSizeLimitMiddleware is outermost (added last) so it intercepts oversized
# requests before they reach CORS or routing (S-13).
app.add_middleware(_CSRFMiddleware)
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(_HSTSMiddleware)
app.add_middleware(_ContentSizeLimitMiddleware, max_bytes=_MAX_BODY_BYTES)
logger.info("Routers and middleware wired")
