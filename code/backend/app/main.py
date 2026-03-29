from __future__ import annotations

import json as _json
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


class _ContentSizeLimitMiddleware:
    """Pure ASGI middleware that enforces a maximum request body size.

    Wraps the ASGI ``receive`` callable to count bytes from ``http.request``
    messages so chunked / streaming bodies (Transfer-Encoding: chunked) are
    bounded alongside Content-Length-declared bodies — no buffering required.

    When the cumulative body size exceeds *max_bytes* the middleware signals
    end-of-body to the downstream app so it stops reading, then intercepts the
    first ``http.response.start`` message from the downstream app and replaces
    the entire response with HTTP 413 before any bytes reach the client.
    """

    def __init__(self, app, max_bytes: int = _MAX_BODY_BYTES) -> None:
        self._app = app
        self._max_bytes = max_bytes

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return

        # Fast path: Content-Length header present — reject immediately without
        # touching the receive channel.
        for name, value in scope.get("headers", []):
            if name == b"content-length":
                try:
                    if int(value) > self._max_bytes:
                        await self._reject(send)
                        return
                except ValueError:
                    pass
                break

        total = 0
        limit_exceeded = False

        async def limited_receive():
            nonlocal total, limit_exceeded
            message = await receive()
            if message["type"] == "http.request":
                total += len(message.get("body", b""))
                if total > self._max_bytes:
                    limit_exceeded = True
                    # Signal end-of-body so the downstream app stops reading
                    # instead of blocking on the next receive() call.
                    return {"type": "http.request", "body": b"", "more_body": False}
            return message

        _413_sent = False

        async def guarded_send(message) -> None:
            nonlocal _413_sent
            if limit_exceeded:
                if not _413_sent and message["type"] == "http.response.start":
                    _413_sent = True
                    await self._reject(send)
                # Swallow subsequent sends so the downstream app's response
                # (which may be based on a truncated body) is never forwarded.
                return
            await send(message)

        await self._app(scope, limited_receive, guarded_send)

    @staticmethod
    async def _reject(send) -> None:
        body = b'{"detail":"Request body too large"}'
        await send(
            {
                "type": "http.response.start",
                "status": 413,
                "headers": [
                    [b"content-type", b"application/json"],
                    [b"content-length", str(len(body)).encode()],
                ],
            }
        )
        await send({"type": "http.response.body", "body": body})

# ---------------------------------------------------------------------------
# CSRF protection middleware (double-submit cookie pattern)
# ---------------------------------------------------------------------------

class _CSRFMiddleware(BaseHTTPMiddleware):
    """Validate that mutating requests carry a non-empty X-CSRF-Token header.

    Security model — custom-header CSRF protection:
    The browser's Same-Origin Policy (SOP) prevents cross-origin JavaScript
    from adding *custom* headers to a cross-origin request without a successful
    CORS preflight that the server explicitly approves.  Because the backend
    CORS policy only allows known frontend origins, any request bearing the
    X-CSRF-Token header must have originated from allowed JS.  The header
    *value* does not need to match a secret — its mere non-empty presence is
    the proof-of-intent token.

    Why NOT the double-submit cookie pattern (previous implementation):
    The old approach set a "csrf_token" cookie from the Railway backend domain
    and required the frontend to read it via document.cookie.  In production
    the frontend (Vercel) and backend (Railway) are on different domains;
    browsers do not expose cross-domain cookies to JavaScript, so getCsrfToken()
    always returned "" and every mutating request received a 403.

    Disabled entirely in dev mode — no overhead for local development or tests.
    /login, /logout, and /health are exempt (cookie-less clients need login).
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
        csrf_header = request.headers.get("X-CSRF-Token", "").strip()
        if not csrf_header:
            return JSONResponse(
                status_code=403,
                content={"detail": "CSRF validation failed"},
            )
        return await call_next(request)


# ---------------------------------------------------------------------------
# HSTS middleware (production only)
# ---------------------------------------------------------------------------

class _HSTSMiddleware(BaseHTTPMiddleware):
    """Add security headers on every response.

    In non-dev environments:
    - Strict-Transport-Security (HSTS)
    - X-Content-Type-Options: nosniff
    - X-Frame-Options: DENY
    - Referrer-Policy: strict-origin-when-cross-origin
    """

    async def dispatch(self, request: StarletteRequest, call_next):
        response = await call_next(request)
        from .core.config import get_settings as _gs
        if _gs().app_env != "dev":
            response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["X-Frame-Options"] = "DENY"
            response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
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


app = FastAPI(
    title="Ambient AI Productivity Dashboard",
    lifespan=lifespan,
    # Disable automatic trailing-slash redirects. FastAPI's default redirect
    # builds the Location URL using the *internal* HTTP scheme (Railway
    # terminates TLS at the edge and forwards HTTP internally), which produces
    # an `http://` Location header — a protocol downgrade. Setting
    # redirect_slashes=False avoids the redirect entirely; the generated
    # TypeScript client and all API routes already use canonical paths.
    redirect_slashes=False,
)

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
