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

# TODO(deploy): S-3 — Enforce HTTPS. Deploy behind nginx/Caddy with TLS termination.
#               Set Strict-Transport-Security header. Configure the `Secure` cookie flag.

# TODO(deploy): S-8 — Add CSRF protection when httpOnly cookie auth is active (S-2).
#               Use the double-submit cookie or synchronizer token pattern.

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
    # This covers newly added models (e.g. session_logs) without requiring
    # a manual migration step in development.
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("DB tables verified/created via create_all")
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


# TODO(deploy): S-5 — Set FRONTEND_CORS_ORIGINS env var to the production domain.
#               get_cors_origins() raises ValueError if localhost/127.0.0.1 remains in non-dev config.
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
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(_ContentSizeLimitMiddleware, max_bytes=_MAX_BODY_BYTES)
logger.info("Routers and middleware wired")
